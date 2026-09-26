from pathlib import Path
import sys,json,os,time
R=Path(__file__).resolve().parents[1]
sys.path.append(str(R/'work/ocr_env/Lib/site-packages'))
sys.path.insert(0,r'${PATCHIONER_SOURCE}\local_app')
from PIL import Image
import runtime,torch,easyocr,numpy as np
r=next(x for x in json.loads((R/'work/image_inventory.json').read_text(encoding='utf-8')) if x['file'].endswith('.svg'))
im=Image.open(r['path']).convert('RGBA');white=Image.new('RGBA',im.size,'white');white.alpha_composite(im)
_,p=runtime.infer(white.convert('RGB'));p.update({'file':r['file'],'repair':'SVG rasterized preserving alpha then white composite'})
del runtime.MODEL;runtime.MODEL=None;torch.cuda.empty_cache()
reader=easyocr.Reader(['ko','en'],gpu=True,model_storage_directory=str(R/'work/models/easyocr'),verbose=False)
results={'patch':p}
for name,color,scale in [('easy','white',1),('easy_enhanced','#202020',512/im.width)]:
    bg=Image.new('RGBA',im.size,color);bg.alpha_composite(im);bg=bg.convert('RGB');bg=bg.resize((round(bg.width*scale),round(bg.height*scale)),Image.Resampling.LANCZOS)
    torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter()
    raw=reader.readtext(np.asarray(bg),detail=1,paragraph=False,batch_size=1,workers=0)
    torch.cuda.synchronize()
    results[name]={'file':r['file'],'seconds':time.perf_counter()-start,'peak_gpu_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,'lines':[{'box':(np.asarray(b)/scale).tolist(),'text':t,'confidence':float(c)} for b,t,c in raw],'repair':'alpha-preserving SVG rasterization','dark_background':color!='white','scale':scale}
    if name=='easy_enhanced':bg.save(R/'outputs/assets'/f'{Path(r["file"]).stem}_enhanced.png')
(R/'work/experiments/svg_repair.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
