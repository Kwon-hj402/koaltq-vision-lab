import json
from pathlib import Path
from PIL import Image, ImageOps
R=Path(__file__).resolve().parents[1]
inv=json.loads((R/'work/image_inventory.json').read_text(encoding='utf-8'))
good=[r for r in inv if 'size' in r]
groups={'photo':[7,44,62,72,197,230],'icon':[27,34,75,99,113,264],'logo':[5,12,21,51,110,279],'text_banner':[48,50,96,117,137,244],'mixed':[9,65,105,112,187,252],'layout':[4,17,19,67,77,160],'challenge':[29,36,139,173,267,293]}
rows=[]
for group,indices in groups.items():
    for i in indices:
        row=dict(good[i]);row.update({'contact_index':i,'stratum':group})
        rows.append(row)
(R/'work/subset.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
p=R/'outputs'/'assets';p.mkdir(parents=True,exist_ok=True)
for r in good:
    im=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im)
    bg.convert('RGB').save(p/(Path(r['file']).stem+'.png'))
print('Selected',len(rows),'strata',groups.keys())
