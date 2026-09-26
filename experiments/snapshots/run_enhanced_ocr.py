from pathlib import Path
import os,sys,json,time,math,difflib,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'work/ocr_env/Lib/site-packages'))
os.environ['EASYOCR_MODULE_PATH']=str(ROOT/'work/models/easyocr')
import easyocr,torch,numpy as np
from PIL import Image,ImageOps
torch.set_num_threads(4)
reader=easyocr.Reader(['ko','en'],gpu=True,model_storage_directory=str(ROOT/'work/models/easyocr'),verbose=False)
items=json.loads((ROOT/'work/subset.json').read_text(encoding='utf-8'))
inv=json.loads((ROOT/'work/image_inventory.json').read_text(encoding='utf-8'))
selected={r['file'] for r in items}
for r in inv:
    a=np.asarray(Image.open(r['path']).convert('RGBA'))
    alpha=a[:,:,3]/255
    bright=float((a[:,:,:3].mean(axis=2)*alpha).sum()/max(alpha.sum(),1))
    if (np.mean(alpha<1)>0.05 and bright>180) or r['format'].startswith('SVG'):
        if r['file'] not in selected:items.append(dict(r,stratum='alpha_svg_diagnostic'))
out=ROOT/'work/experiments'
def norm(t):return re.sub(r'\s+','',t).lower()
def merge(lines):
    keep=[]
    for l in sorted(lines,key=lambda x:x['confidence'],reverse=True):
        b=np.array(l['box']);x1,y1=b.min(0);x2,y2=b.max(0);duplicate=False
        for k in keep:
            c=np.array(k['box']);a1,b1=c.min(0);a2,b2=c.max(0)
            inter=max(0,min(x2,a2)-max(x1,a1))*max(0,min(y2,b2)-max(y1,b1))
            small=min((x2-x1)*(y2-y1),(a2-a1)*(b2-b1))
            if inter/max(small,1)>.5 and difflib.SequenceMatcher(None,norm(l['text']),norm(k['text'])).ratio()>.5:duplicate=True;break
        if not duplicate:keep.append(l)
    return sorted(keep,key=lambda x:(round(min(p[1] for p in x['box'])/12),min(p[0] for p in x['box'])))
with (out/'easy_enhanced.jsonl').open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        row={'file':r['file'],'stratum':r['stratum'],'policy':'contrast-aware alpha; 8x capped upscale to max-side512 for small inputs; 1600px tiles with160px overlap for max-side>1800; whole+tile merge'}
        try:
            src=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');a=np.asarray(src);alpha=a[:,:,3]/255
            bright=float((a[:,:,:3].mean(axis=2)*alpha).sum()/max(alpha.sum(),1));dark=np.mean(alpha<1)>.05 and bright>180
            bg=Image.new('RGBA',src.size,'#202020' if dark else 'white');bg.alpha_composite(src);im=bg.convert('RGB')
            scale=min(8,512/max(im.size)) if max(im.size)<512 else 1
            whole=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
            views=[('whole',whole,0,0,scale)]
            if max(im.size)>1800:
                for y in range(0,im.height,1440):
                    for x in range(0,im.width,1440):
                        tile=im.crop((x,y,min(x+1600,im.width),min(y+1600,im.height)))
                        if min(tile.size)>=24:views.append((f'tile_{x}_{y}',tile,x,y,1))
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter();lines=[]
            for name,v,dx,dy,s in views:
                raw=reader.readtext(np.asarray(v),detail=1,paragraph=False,batch_size=1,workers=0)
                for b,t,c in raw:
                    box=np.asarray(b,dtype=float)/s;box[:,0]+=dx;box[:,1]+=dy
                    lines.append({'box':box.tolist(),'text':t,'confidence':float(c),'view':name})
            torch.cuda.synchronize();row.update({'seconds':time.perf_counter()-start,'peak_gpu_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,'dark_background':bool(dark),'scale':scale,'views':len(views),'raw_line_count':len(lines),'lines':merge(lines)})
        except Exception as e:row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        print(i,r['file'],len(row.get('lines',[])),round(row.get('seconds',0),2),row.get('error',''),flush=True)
