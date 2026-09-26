from pathlib import Path
import os,sys,json,time,platform
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'work/ocr_env/Lib/site-packages'))
os.environ['EASYOCR_MODULE_PATH']=str(ROOT/'work/models/easyocr')
import easyocr,torch,numpy as np
from PIL import Image,ImageOps
torch.set_num_threads(4)
items=json.loads((ROOT/'work/image_inventory.json').read_text(encoding='utf-8'))
out=ROOT/'work/experiments';out.mkdir(exist_ok=True)
start=time.perf_counter();reader=easyocr.Reader(['ko','en'],gpu=True,model_storage_directory=str(ROOT/'work/models/easyocr'),verbose=False)
load=time.perf_counter()-start;print('LOADED',load,flush=True)
meta={'model':'EasyOCR1.7.2 CRAFT + korean_g2','version':easyocr.__version__,'torch':torch.__version__,'device':'cuda','load_seconds':load,'settings':{'languages':['ko','en'],'decoder':'greedy','paragraph':False,'canvas_size':2560,'mag_ratio':1,'text_threshold':0.7,'low_text':0.4,'link_threshold':0.4,'batch_size':1},'input_policy':'first frame EXIF corrected, alpha on white; native pixel size; no alt/context/label'}
(out/'easy_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
with (out/'easy_all.jsonl').open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        row={'index':i,'file':r['file']}
        try:
            im=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('RGB')
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter()
            result=reader.readtext(np.asarray(im),detail=1,paragraph=False,batch_size=1,workers=0)
            torch.cuda.synchronize()
            row.update({'seconds':time.perf_counter()-start,'peak_gpu_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,'size':list(im.size),'lines':[{'box':np.asarray(b).tolist(),'text':t,'confidence':float(c)} for b,t,c in result]})
        except Exception as e:row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        if i%10==0 or 'error' in row: print(i,r['file'],row.get('seconds'),len(row.get('lines',[])),row.get('error',''),flush=True)
print('DONE',len(items),flush=True)
