from pathlib import Path
import os,json,time,platform,sys
ROOT=Path(__file__).resolve().parents[1]
os.environ['PADDLE_PDX_CACHE_HOME']=str(ROOT/'work/models/paddlex')
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']='True'
os.environ['HF_HOME']=str(ROOT/'work/models/huggingface')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
from paddleocr import PaddleOCR
import paddle,paddleocr,numpy as np
from PIL import Image,ImageOps
import psutil
out=ROOT/'work/experiments';out.mkdir(exist_ok=True)
full='--all' in sys.argv
items=json.loads((ROOT/('work/image_inventory.json' if full else 'work/subset.json')).read_text(encoding='utf-8'))
cache={r['file']:r for r in map(json.loads,(out/'paddle_subset.jsonl').read_text(encoding='utf-8').splitlines())} if full and (out/'paddle_subset.jsonl').exists() else {}
start=time.perf_counter()
ocr=PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det',text_recognition_model_name='korean_PP-OCRv5_mobile_rec',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu',enable_mkldnn=False,cpu_threads=4)
load=time.perf_counter()-start;print('LOADED',load,flush=True)
meta={'model':'PP-OCRv5 mobile detection + Korean mobile recognition','paddle':paddle.__version__,'paddleocr':paddleocr.__version__,'device':'CPU','cpu_threads':4,'load_seconds':load,'orientation':False,'unwarping':False,'mkldnn':False,'input_policy':'first frame EXIF corrected alpha on white; native size; no alt/context/label'}
(out/'paddle_meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
with (out/('paddle_all.jsonl' if full else 'paddle_subset.jsonl')).open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        if r['file'] in cache:
            row=dict(cache[r['file']],reused_subset_result=True)
            f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();continue
        row={'file':r['file'],'stratum':r.get('stratum'),'contact_index':r.get('contact_index')}
        try:
            im=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im)
            start=time.perf_counter();results=list(ocr.predict(np.asarray(bg.convert('RGB'))[:,:,::-1]))
            row['seconds']=time.perf_counter()-start;row['rss_mb']=psutil.Process().memory_info().rss/1024**2
            result=results[0].json
            if isinstance(result,str):result=json.loads(result)
            row['raw']=result
            d=result.get('res',result)
            row['lines']=[{'text':t,'confidence':float(c),'box':b} for t,c,b in zip(d.get('rec_texts',[]),d.get('rec_scores',[]),d.get('rec_polys',[]))]
        except Exception as e:row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        print(i,r['file'],row.get('seconds'),len(row.get('lines',[])),row.get('error',''),flush=True)
print('DONE',len(items),flush=True)
