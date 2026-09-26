"""Small shared helpers; importing this module needs only the standard library."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.metadata
import json
import sys


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def add_module_paths(paths):
    for path in paths:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError(f'Extra module directory does not exist: {resolved}')
        sys.path.append(str(resolved))


def versions(names):
    found = {}
    for name in names:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def json_default(value):
    if hasattr(value, 'tolist'):
        return value.tolist()
    if hasattr(value, 'item'):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f'Cannot serialize {type(value).__name__}')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_default), encoding='utf-8')


def prepare_image(path, preview_path):
    from PIL import Image, ImageOps
    with Image.open(path) as source:
        source.seek(0)
        source_format = source.format
        im = ImageOps.exif_transpose(source).convert('RGBA')
    background = Image.new('RGBA', im.size, 'white')
    background.alpha_composite(im)
    image = background.convert('RGB')
    image.save(preview_path, format='PNG')
    return image, {'width': image.width, 'height': image.height, 'source_format': source_format, 'frame': 0, 'exif_corrected': True, 'alpha_background': 'white'}
