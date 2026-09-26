"""Fixed preprocessing experiment on every image in subset.json; no labels used."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.environ['PADDLE_PDX_CACHE_HOME'] = str(ROOT / 'work/models/paddlex')
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['HF_HOME'] = str(ROOT / 'work/models/huggingface')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OMP_NUM_THREADS'] = '4'
os.environ['MKL_NUM_THREADS'] = '4'

import numpy as np
import paddle
import paddleocr
import psutil
from paddleocr import PaddleOCR
from PIL import Image, ImageOps

OUT = ROOT / 'work/experiments'
OUT.mkdir(exist_ok=True)
RESULT_PATH = OUT / 'paddle_enhanced.jsonl'
META_PATH = OUT / 'paddle_enhanced_meta.json'
INPUT_PATH = ROOT / 'work/subset.json'
POLICY = {
    'input': 'all 42 rows of subset.json, unchanged order; no labels, OCR outputs or references read',
    'frame': 'first frame; EXIF transpose; retain native resolution before fixed transforms',
    'alpha': 'fraction(alpha < 255) > 0.05 AND alpha-weighted mean RGB brightness > 180 => #202020; otherwise white',
    'small': 'maxside < 512 => nominal scale min(8, 512 / maxside); Lanczos, rounded dimensions',
    'large': 'maxside > 1800 => whole image plus native-resolution 1600px tiles, stride 1440px (160px overlap); edge tiles cropped to bounds',
    'merge': 'descending confidence; axis-aligned intersection / smaller-box area > 0.5 AND normalized text SequenceMatcher ratio > 0.5 => duplicate; keep highest confidence',
    'normalization_for_merge_only': 'Unicode NFC, remove whitespace, lowercase; raw text unchanged',
    'coordinates': 'inverse resize separately by actual x/y ratio, then add tile origin; EXIF-corrected original coordinates',
    'reading_order': 'approximate y-bands of 12 original pixels then x; not a validated document reading-order model',
}


def norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFC', text)).lower()


def bounds(box):
    p = np.asarray(box, dtype=float)
    return (*p.min(axis=0), *p.max(axis=0))


def merge(lines):
    kept = []
    for raw_line in sorted(lines, key=lambda line: line['confidence'], reverse=True):
        line = dict(raw_line)
        x1, y1, x2, y2 = bounds(line['box'])
        duplicate = None
        for candidate in kept:
            a1, b1, a2, b2 = bounds(candidate['box'])
            intersection = max(0, min(x2, a2) - max(x1, a1)) * max(0, min(y2, b2) - max(y1, b1))
            small = min((x2 - x1) * (y2 - y1), (a2 - a1) * (b2 - b1))
            if intersection / max(small, 1) > .5 and difflib.SequenceMatcher(None, norm(line['text']), norm(candidate['text'])).ratio() > .5:
                duplicate = candidate
                break
        if duplicate is None:
            line['merged_raw_line_ids'] = [line['raw_line_id']]
            kept.append(line)
        else:
            duplicate['merged_raw_line_ids'].append(line['raw_line_id'])
    return sorted(kept, key=lambda line: (round(min(p[1] for p in line['box']) / 12), min(p[0] for p in line['box'])))


def tile_origins(length):
    positions = [0]
    while positions[-1] + 1600 < length:
        positions.append(positions[-1] + 1440)
    return positions


def prepare(path):
    with Image.open(path) as source:
        source.seek(0)
        original = ImageOps.exif_transpose(source).convert('RGBA')
    pixels = np.asarray(original)
    alpha = pixels[:, :, 3].astype(float) / 255
    transparent_fraction = float(np.mean(alpha < 1))
    brightness = float((pixels[:, :, :3].mean(axis=2) * alpha).sum() / max(alpha.sum(), 1))
    dark = transparent_fraction > .05 and brightness > 180
    background = Image.new('RGBA', original.size, '#202020' if dark else 'white')
    background.alpha_composite(original)
    im = background.convert('RGB')
    nominal_scale = min(8, 512 / max(im.size)) if max(im.size) < 512 else 1
    whole = im.resize((round(im.width * nominal_scale), round(im.height * nominal_scale)), Image.Resampling.LANCZOS)
    views = [('whole', whole, 0, 0, whole.width / im.width, whole.height / im.height)]
    if max(im.size) > 1800:
        for y in tile_origins(im.height):
            for x in tile_origins(im.width):
                tile = im.crop((x, y, min(x + 1600, im.width), min(y + 1600, im.height)))
                views.append((f'tile_{x}_{y}', tile, x, y, 1, 1))
    info = {
        'original_size': list(im.size),
        'transparent_fraction': transparent_fraction,
        'foreground_mean_brightness': brightness,
        'dark_background': dark,
        'background': '#202020' if dark else '#ffffff',
        'scale': nominal_scale,
        'views': len(views),
    }
    return views, info


def save_meta(meta):
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    items = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    if len(items) != 42:
        raise ValueError(f'Expected the authorized 42-image subset, received {len(items)}')
    meta = {
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'loading',
        'model': 'PP-OCRv5 mobile detection + Korean mobile recognition',
        'detection_model': 'PP-OCRv5_mobile_det',
        'recognition_model': 'korean_PP-OCRv5_mobile_rec',
        'paddle': paddle.__version__,
        'paddleocr': paddleocr.__version__,
        'python': sys.version,
        'python_executable': sys.executable,
        'device': 'CPU',
        'cpu_threads': 4,
        'orientation': False,
        'unwarping': False,
        'mkldnn': False,
        'policy': POLICY,
        'input_sha256': hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'expected_images': len(items),
        'latency_isolated': False,
        'latency_note': 'Concurrent parent PaddleOCR CPU 4-thread all-image run and Florence GPU experiment; times are observational and not isolated benchmarks.',
    }
    save_meta(meta)
    paddle.set_device('cpu')
    started = time.perf_counter()
    try:
        ocr = PaddleOCR(
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='korean_PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device='cpu',
            enable_mkldnn=False,
            cpu_threads=4,
        )
    except Exception as exc:
        meta.update(status='load_failed', error=f'{type(exc).__name__}: {exc}')
        save_meta(meta)
        raise
    meta.update(status='running', load_seconds=time.perf_counter() - started)
    save_meta(meta)
    print('LOADED', round(meta['load_seconds'], 3), flush=True)
    run_start = time.perf_counter()
    completed = failed = partial = 0
    with RESULT_PATH.open('w', encoding='utf-8') as output:
        for i, item in enumerate(items):
            image_start = time.perf_counter()
            row = {'file': item['file'], 'stratum': item.get('stratum'), 'contact_index': item.get('contact_index'), 'raw_lines': [], 'view_results': [], 'lines': []}
            try:
                views, info = prepare(item['path'])
                row.update(info, preprocess_seconds=time.perf_counter() - image_start)
                inference_start = time.perf_counter()
                for name, view, dx, dy, sx, sy in views:
                    view_start = time.perf_counter()
                    view_result = {'view': name, 'size': list(view.size), 'origin': [dx, dy], 'scale_xy': [sx, sy]}
                    try:
                        predicted = list(ocr.predict(np.ascontiguousarray(np.asarray(view)[:, :, ::-1])))
                        raw_results = []
                        for prediction in predicted:
                            data = prediction.json
                            if isinstance(data, str):
                                data = json.loads(data)
                            raw_results.append(data)
                            result = data.get('res', data)
                            texts = result.get('rec_texts', [])
                            scores = result.get('rec_scores', [])
                            polygons = result.get('rec_polys', [])
                            if not (len(texts) == len(scores) == len(polygons)):
                                raise ValueError('PaddleOCR text/score/polygon lengths differ')
                            for text, score, polygon in zip(texts, scores, polygons):
                                box = np.asarray(polygon, dtype=float).copy()
                                box[:, 0] = box[:, 0] / sx + dx
                                box[:, 1] = box[:, 1] / sy + dy
                                row['raw_lines'].append({'raw_line_id': len(row['raw_lines']), 'box': box.tolist(), 'raw_box_in_view': polygon, 'text': text, 'raw_text': text, 'score': float(score), 'confidence': float(score), 'view': name})
                        view_result['raw'] = raw_results
                        view_result['status'] = 'ok'
                    except Exception as exc:
                        view_result.update(status='error', error=f'{type(exc).__name__}: {exc}')
                    view_result['seconds'] = time.perf_counter() - view_start
                    row['view_results'].append(view_result)
                row['seconds'] = time.perf_counter() - inference_start
                row['raw_line_count'] = len(row['raw_lines'])
                row['lines'] = merge(row['raw_lines'])
                row['view_error_count'] = sum(result['status'] == 'error' for result in row['view_results'])
                row['status'] = 'ok' if row['view_error_count'] == 0 else ('error' if row['view_error_count'] == len(views) else 'partial')
                if row['view_error_count']:
                    row['error'] = '; '.join(f"{v['view']}: {v['error']}" for v in row['view_results'] if v['status'] == 'error')
            except Exception as exc:
                row.update(status='error', error=f'{type(exc).__name__}: {exc}')
            row['total_seconds'] = time.perf_counter() - image_start
            row['rss_mb'] = psutil.Process().memory_info().rss / 1024**2
            output.write(json.dumps(row, ensure_ascii=False) + '\n')
            output.flush()
            completed += row['status'] == 'ok'
            failed += row['status'] == 'error'
            partial += row['status'] == 'partial'
            print(i + 1, '/', len(items), item['file'], row['status'], 'views', row.get('views', 0), 'lines', len(row['lines']), 'seconds', round(row.get('seconds', 0), 3), row.get('error', ''), flush=True)
    meta.update(status='complete', finished_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter() - run_start, written_images=completed + failed + partial, ok_images=completed, partial_images=partial, error_images=failed)
    save_meta(meta)
    print('DONE', completed + failed + partial, 'ok', completed, 'partial', partial, 'error', failed, flush=True)


if __name__ == '__main__':
    main()
