from pathlib import Path
import os,json,time,sys
R=Path(__file__).resolve().parents[1]
sys.path.append(str(R/'work/vision_modules'))
os.environ['HF_HOME']=str(R/'work/models/huggingface')
from transformers import AutoModelForCausalLM,AutoProcessor
import torch
from PIL import Image,ImageOps
torch.set_num_threads(4);torch.manual_seed(0)
path=str(R/'work/models/florence2')
start=time.perf_counter()
model=AutoModelForCausalLM.from_pretrained(path,trust_remote_code=True,torch_dtype=torch.float16,attn_implementation='eager').eval().to('cuda')
processor=AutoProcessor.from_pretrained(path,trust_remote_code=True)
load=time.perf_counter()-start;print('LOADED',load,flush=True)
out=R/'work/experiments'
meta={'model':'microsoft/Florence-2-base','variant':'0.23B pretrained, not base-ft','device':'cuda float16 eager','load_seconds':load,'tasks':['<MORE_DETAILED_CAPTION>','<DENSE_REGION_CAPTION>'],'max_new_tokens':256,'num_beams':3,'do_sample':False,'input_policy':'first frame EXIF corrected, alpha on white; no alt/context/label','source':'https://huggingface.co/microsoft/Florence-2-base','conference':'CVPR2024; practical baseline outside2026 strict filter'}
(out/'florence_meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
items=json.loads((R/'work/subset.json').read_text(encoding='utf-8'))
with (out/'florence_subset.jsonl').open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        row={'file':r['file'],'stratum':r['stratum']}
        try:
            src=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');bg=Image.new('RGBA',src.size,'white');bg.alpha_composite(src);im=bg.convert('RGB')
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter();tasks={}
            for task in meta['tasks']:
                inputs=processor(text=task,images=im,return_tensors='pt').to('cuda',torch.float16)
                with torch.inference_mode(): ids=model.generate(input_ids=inputs['input_ids'],pixel_values=inputs['pixel_values'],max_new_tokens=256,num_beams=3,do_sample=False)
                text=processor.batch_decode(ids,skip_special_tokens=False)[0]
                tasks[task]={'raw':text,'parsed':processor.post_process_generation(text,task=task,image_size=im.size)}
            torch.cuda.synchronize();row.update({'seconds':time.perf_counter()-start,'peak_gpu_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,'tasks':tasks})
        except Exception as e:row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        print(i,r['file'],round(row.get('seconds',0),2),row.get('error',str(row.get('tasks',{}))[:200]),flush=True)
