"""Florence worker, invoked by describe_image.py with its own Python environment."""
import argparse
import os
from pathlib import Path
import time
import traceback
from common import add_module_paths, prepare_image, utc_now, versions, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default='microsoft/Florence-2-base')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--hf-cache')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-new-tokens', type=int, default=256)
    parser.add_argument('--num-beams', type=int, default=3)
    parser.add_argument('--extra-module-path', action='append', default=[])
    args = parser.parse_args()
    result = {'status': 'error', 'created_at_utc': utc_now(), 'model': 'microsoft/Florence-2-base', 'variant': '0.23B pretrained, not base-ft', 'task': '<MORE_DETAILED_CAPTION>', 'device': args.device, 'weights_source': 'local directory' if Path(args.model).is_dir() else args.model, 'no_additional_training': True}
    try:
        add_module_paths(args.extra_module_path)
        if args.hf_cache:
            os.environ['HF_HOME'] = str(Path(args.hf_cache).expanduser().resolve())
        if args.offline:
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor
        torch.set_num_threads(args.threads)
        torch.manual_seed(0)
        device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda'):
            raise ValueError('This runner supports CPU or CUDA devices only')
        if device.type == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested, but this Python environment has no available CUDA device')
        dtype = torch.float16 if device.type == 'cuda' else torch.float32
        image, image_info = prepare_image(args.image, Path(args.output).parent / 'input.png')
        start = time.perf_counter()
        model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, local_files_only=args.offline, torch_dtype=dtype, attn_implementation='eager').eval().to(device)
        processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True, local_files_only=args.offline)
        result['load_seconds'] = time.perf_counter() - start
        if device.type == 'cuda':
            torch.cuda.reset_peak_memory_stats(device)
            torch.cuda.synchronize(device)
        start = time.perf_counter()
        inputs = processor(text=result['task'], images=image, return_tensors='pt').to(device, dtype)
        with torch.inference_mode():
            ids = model.generate(input_ids=inputs['input_ids'], pixel_values=inputs['pixel_values'], max_new_tokens=args.max_new_tokens, num_beams=args.num_beams, do_sample=False)
        raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
        parsed = processor.post_process_generation(raw, task=result['task'], image_size=image.size)
        if device.type == 'cuda':
            torch.cuda.synchronize(device)
            result['peak_gpu_allocated_mb'] = torch.cuda.max_memory_allocated(device) / 1024**2
        result.update(status='ok', seconds=time.perf_counter() - start, image=image_info, raw=raw, parsed=parsed, caption=parsed.get(result['task'], '') if isinstance(parsed, dict) else str(parsed), dtype=str(dtype), settings={'max_new_tokens': args.max_new_tokens, 'num_beams': args.num_beams, 'do_sample': False, 'attention': 'eager', 'threads': args.threads, 'offline': args.offline}, versions=versions(['torch', 'torchvision', 'transformers', 'Pillow', 'numpy', 'timm', 'einops', 'safetensors', 'huggingface-hub', 'tokenizers']))
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        traceback.print_exc()
    write_json(args.output, result)
    print(result['status'], flush=True)
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
