from pathlib import Path
import zipfile, json, hashlib
from PIL import Image, ImageOps, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
dest=ROOT/'work'/'data'
dest.mkdir(parents=True,exist_ok=True)
archive=Path(r'${DATASET_ARCHIVE}')
with zipfile.ZipFile(archive) as z:
    for i in z.infolist():
        target=(dest/i.filename).resolve()
        if not target.is_relative_to(dest.resolve()): raise ValueError(i.filename)
    z.extractall(dest)
files=list((dest/'koaltq_sample').iterdir())
print('FILES',[(x.name,x.stat().st_size) for x in files])
for p in files:
    if p.is_file():
        try: print('CONTENT',p.name,p.read_text(encoding='utf-8-sig')[:6500])
        except Exception: pass
records=[]
for p in sorted((dest/'koaltq_sample'/'images').iterdir()):
    try:
        with Image.open(p) as im:
            records.append({'file':p.name,'path':str(p),'size':list(im.size),'format':im.format,'frames':getattr(im,'n_frames',1),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    except Exception as e: records.append({'file':p.name,'error':str(e)})
(ROOT/'work'/'image_inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
good=[r for r in records if 'size' in r]
print('IMAGES',len(records),'VALID',len(good),'ERRORS',[r for r in records if 'error' in r])
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
for start in range(0,len(good),50):
    canvas=Image.new('RGB',(1200,1500),'#eeeeee'); d=ImageDraw.Draw(canvas)
    for j,r in enumerate(good[start:start+50]):
        im=Image.open(r['path']).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB')
        thumb=ImageOps.contain(im,(232,124)); x=(j%5)*240; y=(j//5)*150
        canvas.paste(thumb,(x+(240-thumb.width)//2,y))
        d.text((x+4,y+125),f'{start+j:03d} {r["file"][:12]} {r["size"]}',font=font,fill='black')
    canvas.save(ROOT/'work'/f'contact_{start//50}.jpg',quality=90)
