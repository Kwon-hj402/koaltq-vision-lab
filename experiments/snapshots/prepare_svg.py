from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[1]
sys.path.append(str(R/'work/raster_modules'))
import resvg_py
from PIL import Image
inv=json.loads((R/'work/image_inventory.json').read_text(encoding='utf-8'))
for row in inv:
    if row['file'].endswith('.svg'):
        src=R/'work/data/koaltq_sample/images'/row['file']; out=R/'work/data'/(src.stem+'_raster.png')
        out.write_bytes(resvg_py.svg_to_bytes(svg_path=str(src)))
        row.update({'path':str(out),'size':list(Image.open(out).size),'format':'SVG rasterized PNG','frames':1,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_path':str(src),'conversion':'resvg-py 0.5.0 intrinsic dimensions with alpha preserved'})
        row.pop('error',None)
(R/'work/image_inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2),encoding='utf-8')
print('SVG rasterized')
