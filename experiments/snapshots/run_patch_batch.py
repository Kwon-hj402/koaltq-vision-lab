from pathlib import Path
import sys, json, time, hashlib, platform
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,r'${PATCHIONER_SOURCE}\local_app')
import runtime
from PIL import Image, ImageOps
import torch
out=ROOT/'work'/'experiments'; out.mkdir(exist_ok=True)
items=json.loads((ROOT/'work'/'image_inventory.json').read_text(encoding='utf-8'))
started=time.perf_counter(); model=runtime.load_model()
print('LOADED',runtime.LOAD_SECONDS,flush=True)
meta={'model':runtime.MODEL_ID,'device':runtime.DEVICE,'torch':torch.__version__,'python':platform.python_version(),'load_seconds':runtime.LOAD_SECONDS,'input_policy':'PIL first frame, EXIF corrected, RGBA composited on white; no alt/context/label given to model','full_image_transform':'518x518 full-image resize, no crop','seed':0,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S')}
(out/'patch_meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
with (out/'patch_all.jsonl').open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        row={'index':i,'file':r['file'],'sha256':r.get('sha256')}
        try:
            im=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA')
            bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im)
            _,result=runtime.infer(bg.convert('RGB'))
            row.update(result)
        except Exception as e: row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        if i%10==0 or 'error' in row: print(i,r['file'],row.get('whole_image',row.get('error')),flush=True)
print('DONE',len(items),'seconds',time.perf_counter()-started,flush=True)
