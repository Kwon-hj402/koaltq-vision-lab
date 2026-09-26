"""PP-OCRv5 Korean worker, invoked with a separate Paddle Python environment."""
import argparse
import json
import os
from pathlib import Path
import time
import traceback
from common import add_module_paths, prepare_image, utc_now, versions, write_json

DET_MODEL = 'PP-OCRv5_mobile_det'
REC_MODEL = 'korean_PP-OCRv5_mobile_rec'


def local_model(explicit, cache, name, offline):
    path = Path(explicit).expanduser().resolve() if explicit else None
    if path is None and cache:
        candidate = Path(cache).expanduser().resolve() / 'official_models' / name
        if candidate.is_dir():
            path = candidate
    if path is not None:
        if not path.is_dir() or not (path / 'inference.yml').is_file():
            raise ValueError(f'Expected an exported Paddle model directory with inference.yml: {path}')
        return str(path)
    if offline:
        raise ValueError(f'Offline mode needs --paddle-cache containing official_models/{name}, or an explicit model directory')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--cache')
    parser.add_argument('--det-model-dir')
    parser.add_argument('--rec-model-dir')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--extra-module-path', action='append', default=[])
    args = parser.parse_args()
    result = {'status': 'error', 'created_at_utc': utc_now(), 'detection_model': DET_MODEL, 'recognition_model': REC_MODEL, 'device': args.device, 'no_additional_training': True, 'coordinate_system': 'EXIF-corrected original image pixels', 'confidence_note': 'Recognizer scores are not calibrated probabilities that a phrase is correct.'}
    try:
        add_module_paths(args.extra_module_path)
        if args.cache:
            os.environ['PADDLE_PDX_CACHE_HOME'] = str(Path(args.cache).expanduser().resolve())
        os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
        os.environ['OMP_NUM_THREADS'] = str(args.threads)
        os.environ['MKL_NUM_THREADS'] = str(args.threads)
        if args.device == 'cpu':
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        det_dir = local_model(args.det_model_dir, args.cache, DET_MODEL, args.offline)
        rec_dir = local_model(args.rec_model_dir, args.cache, REC_MODEL, args.offline)
        import numpy as np
        from paddleocr import PaddleOCR
        image, image_info = prepare_image(args.image, Path(args.output).parent / 'input.png')
        settings = dict(text_detection_model_name=DET_MODEL, text_recognition_model_name=REC_MODEL, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, device=args.device, enable_mkldnn=False, cpu_threads=args.threads)
        if det_dir:
            settings['text_detection_model_dir'] = det_dir
        if rec_dir:
            settings['text_recognition_model_dir'] = rec_dir
        start = time.perf_counter()
        ocr = PaddleOCR(**settings)
        result['load_seconds'] = time.perf_counter() - start
        start = time.perf_counter()
        predicted = list(ocr.predict(np.ascontiguousarray(np.asarray(image)[:, :, ::-1])))
        result['seconds'] = time.perf_counter() - start
        lines, raw_results = [], []
        for prediction in predicted:
            raw = prediction.json
            if isinstance(raw, str):
                raw = json.loads(raw)
            raw_results.append(raw)
            data = raw.get('res', raw)
            texts, scores, boxes = data.get('rec_texts', []), data.get('rec_scores', []), data.get('rec_polys', [])
            if not (len(texts) == len(scores) == len(boxes)):
                raise ValueError('Text, confidence and polygon counts differ')
            base_id = len(lines)
            lines.extend({'id': base_id + i, 'text': text, 'confidence': float(score), 'box': box, 'view': 'whole'} for i, (text, score, box) in enumerate(zip(texts, scores, boxes)))
        result.update(status='ok', image=image_info, lines=lines, raw=raw_results, settings={'threads': args.threads, 'mkldnn': False, 'doc_orientation': False, 'doc_unwarping': False, 'textline_orientation': False, 'offline': args.offline, 'weights_source': 'explicit local model directories' if det_dir and rec_dir else 'official model names/cache', 'view': 'whole image; no upscaling, tiling or manual correction'}, versions=versions(['paddleocr', 'paddlepaddle', 'paddlex', 'Pillow', 'numpy', 'opencv-contrib-python']))
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        traceback.print_exc()
    write_json(args.output, result)
    print(result['status'], flush=True)
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
