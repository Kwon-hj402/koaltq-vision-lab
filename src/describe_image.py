"""Portable two-environment image evidence CLI; this orchestrator is stdlib-only."""
import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from common import utc_now, write_json


def python_path(value):
    found = shutil.which(value)
    if found:
        return str(Path(found).resolve())
    candidate = Path(value).expanduser().resolve()
    if candidate.is_file():
        return str(candidate)
    raise ValueError(f'Python executable not found: {value}')


def run_worker(python, worker, arguments, output, log, extra_paths):
    command = [python, str(Path(__file__).with_name(worker)), *arguments]
    for path in extra_paths:
        command.extend(['--extra-module-path', str(Path(path).expanduser().resolve())])
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    started = time.perf_counter()
    try:
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=env, check=False)
        if output.exists():
            result = json.loads(output.read_text(encoding='utf-8'))
        else:
            result = {'status': 'error', 'error': f'Worker exited {process.returncode} without a result; see {log.name}'}
        result['worker_exit_code'] = process.returncode
        if process.returncode != 0 and result.get('status') == 'ok':
            result.update(status='error', error='Worker returned a nonzero exit code; inspect the log')
    except Exception as exc:
        result = {'status': 'error', 'error': f'{type(exc).__name__}: {exc}'}
    result['worker_wall_seconds'] = time.perf_counter() - started
    write_json(output, result)
    return result


def render_html(evidence, directory):
    caption, ocr = evidence['caption'], evidence['ocr']
    text = caption.get('caption') or caption.get('error', '(빈 결과)')
    rows = []
    for line in ocr.get('lines', []):
        rows.append('<tr><td>' + escape(line['text']) + '</td><td>' + f"{line['confidence']:.4f}" + '</td><td><code>' + escape(json.dumps(line['box'])) + '</code></td></tr>')
    body = ''.join(rows) or '<tr><td colspan="3">' + escape(ocr.get('error', '검출된 문구 없음')) + '</td></tr>'
    preview = '<img src="input.png" alt="검토할 입력 이미지">' if (directory / 'input.png').exists() else ''
    html = f'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>단일 이미지 근거 추출 결과</title>
<style>body{{max-width:1080px;margin:48px auto;padding:0 24px;color:#171717;background:#fff;font:16px/1.7 system-ui,sans-serif}}h1{{font-size:28px}}h2{{font-size:20px;margin-top:36px;border-bottom:1px solid #ccc;padding-bottom:8px}}small,.note{{color:#555}}img{{max-width:100%;max-height:650px;object-fit:contain;border:1px solid #ddd}}p{{white-space:pre-wrap}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;border-bottom:1px solid #ddd;padding:10px;vertical-align:top}}td:last-child{{max-width:360px;overflow-wrap:anywhere}}code{{font-size:12px}}a{{color:#174c89}}@media(max-width:650px){{body{{margin:24px auto}}table{{font-size:12px}}td,th{{padding:5px}}}}</style>
<h1>단일 이미지 근거 추출 결과</h1><small>{escape(evidence['input']['filename'])} · {escape(evidence['created_at_utc'])} · 실행 상태: {escape(evidence['status'])}</small>
<p class="note">기존 alt·정답·페이지 메타데이터를 입력하지 않았습니다. 아래 설명은 생성 모델의 원출력이며, 사실 검증 또는 최종 대체텍스트 판정 결과가 아닙니다.</p>{preview}
<h2>이미지 설명 — Florence-2-base</h2><p>{escape(str(text))}</p><small>상태: {escape(caption.get('status', 'unknown'))} · MORE_DETAILED_CAPTION · 생성 언어 및 내용 그대로 보존</small>
<h2>이미지 안의 문자 — PP-OCRv5 Korean</h2><p class="note">원문, 모델 점수, 원본 좌표의 폴리곤을 함께 저장했습니다. 점수는 문구 정답 확률이 아닙니다. 표 순서는 OCR이 반환한 순서입니다.</p><table><thead><tr><th>OCR 원문</th><th>점수</th><th>폴리곤 [x,y]</th></tr></thead><tbody>{body}</tbody></table>
<h2>검토 범위와 결과 파일</h2><p>OCR과 이미지 설명은 별도 근거입니다. 글과 그림의 대응, 누락·환각 검증, 페이지 맥락을 이용한 최종 alt 생성·판정, 웹 검색 에이전트는 구현하지 않았습니다. 추가 학습은 수행하지 않습니다.</p>
<p><a href="evidence.json">전체 근거 JSON</a> · <a href="caption.json">설명 원출력</a> · <a href="ocr.json">OCR 원출력</a> · <a href="caption.log">설명 로그</a> · <a href="ocr.log">OCR 로그</a></p></html>'''
    (directory / 'result.html').write_text(html, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Single image -> Korean OCR evidence + Florence-2 detailed caption, using separate Python environments.')
    parser.add_argument('image', help='Local raster image; first frame used for animations')
    parser.add_argument('--output', required=True, help='Empty directory for JSON, HTML, preview and logs')
    parser.add_argument('--florence-python', default=sys.executable)
    parser.add_argument('--paddle-python', default=sys.executable)
    parser.add_argument('--florence-model', default='microsoft/Florence-2-base', help='Public Hugging Face model ID or a local model directory')
    parser.add_argument('--hf-cache', help='Optional Hugging Face cache root (HF_HOME)')
    parser.add_argument('--paddle-cache', help='PaddleX cache root containing official_models/')
    parser.add_argument('--paddle-det-model-dir', help='Optional explicit PP-OCRv5_mobile_det export directory')
    parser.add_argument('--paddle-rec-model-dir', help='Optional explicit korean_PP-OCRv5_mobile_rec export directory')
    parser.add_argument('--caption-device', default='cpu', help='cpu, cuda or cuda:0; GPU requires a matching PyTorch build')
    parser.add_argument('--ocr-device', default='cpu', help='cpu or gpu:0; GPU requires paddlepaddle-gpu instead of the supplied CPU package')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-new-tokens', type=int, default=256)
    parser.add_argument('--num-beams', type=int, default=3)
    parser.add_argument('--extra-module-path', action='append', default=[], help='Additional module directory for the Florence worker; repeatable')
    parser.add_argument('--paddle-extra-module-path', action='append', default=[], help='Additional module directory for the Paddle worker; repeatable')
    parser.add_argument('--offline', action='store_true', help='Require cached/local weights; do not download models')
    parser.add_argument('--overwrite', action='store_true', help='Replace this runner\'s known result files in an existing directory')
    args = parser.parse_args()
    image = Path(args.image).expanduser().resolve()
    directory = Path(args.output).expanduser().resolve()
    if not image.is_file():
        parser.error(f'Input image not found: {image}')
    if min(args.threads, args.max_new_tokens, args.num_beams) < 1:
        parser.error('threads, max-new-tokens and num-beams must be positive')
    names = ('caption.json', 'ocr.json', 'evidence.json', 'result.html', 'input.png', 'caption.log', 'ocr.log')
    if image in [directory / name for name in names]:
        parser.error('Output would overwrite the input image; choose a different output directory')
    if directory.exists() and any(directory.iterdir()) and not args.overwrite:
        parser.error('Output directory is not empty. Choose a new directory or pass --overwrite.')
    try:
        florence_python, paddle_python = python_path(args.florence_python), python_path(args.paddle_python)
    except ValueError as exc:
        parser.error(str(exc))
    directory.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for name in names:
            path = directory / name
            if path.is_file():
                path.unlink()
    common = ['--image', str(image), '--threads', str(args.threads)]
    if args.offline:
        common.append('--offline')
    paddle_args = [*common, '--output', str(directory / 'ocr.json'), '--device', args.ocr_device]
    for option, value in [('--cache', args.paddle_cache), ('--det-model-dir', args.paddle_det_model_dir), ('--rec-model-dir', args.paddle_rec_model_dir)]:
        if value:
            paddle_args.extend([option, value])
    print('Running Korean OCR...', flush=True)
    ocr = run_worker(paddle_python, 'paddle_worker.py', paddle_args, directory / 'ocr.json', directory / 'ocr.log', args.paddle_extra_module_path)
    caption_args = [*common, '--output', str(directory / 'caption.json'), '--model', args.florence_model, '--device', args.caption_device, '--max-new-tokens', str(args.max_new_tokens), '--num-beams', str(args.num_beams)]
    if args.hf_cache:
        caption_args.extend(['--hf-cache', args.hf_cache])
    print('Running detailed image caption...', flush=True)
    caption = run_worker(florence_python, 'florence_worker.py', caption_args, directory / 'caption.json', directory / 'caption.log', args.extra_module_path)
    evidence = {'schema_version': '1.0', 'created_at_utc': utc_now(), 'status': 'ok' if ocr.get('status') == caption.get('status') == 'ok' else 'partial_or_failed', 'input': {'filename': image.name, 'sha256': hashlib.sha256(image.read_bytes()).hexdigest()}, 'input_policy': 'one local raster image; first frame; EXIF corrected; alpha on white; no alt, labels, metadata, external lookup or additional training', 'pipeline': 'PP-OCRv5 Korean and Florence-2-base run sequentially in separate environments; evidence preserved separately', 'ocr': ocr, 'caption': caption, 'final_alt': None, 'final_llm_judgement_implemented': False, 'limitations': ['Caption can omit details or hallucinate.', 'Korean transcription is provided by the explicit Korean OCR model, not guaranteed by Florence.', 'Whole-image baseline only; no enhanced tiling or reading-order reconstruction.', 'OCR confidence is not a calibrated correctness probability.', 'No page metadata, semantic cross-check, final alt generation, or browsing agent.']}
    write_json(directory / 'evidence.json', evidence)
    render_html(evidence, directory)
    print(f"Status: {evidence['status']}\nReport: {directory / 'result.html'}", flush=True)
    return 0 if evidence['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
