"""Re-run four local pretrained components on one image, without metadata or labels.

This entry point reuses the environments and model cache configured in this workspace.
It does not install packages or send images to a remote API.
"""
from pathlib import Path
import sys,os,json,time,argparse,subprocess,datetime,html
ROOT=Path(__file__).resolve().parents[2]
LEGACY=Path(r'${PATCHIONER_RUNTIME}\venv\Scripts\python.exe')
PADDLE=ROOT/'work/paddle_env/Scripts/python.exe'
parser=argparse.ArgumentParser();parser.add_argument('--image');parser.add_argument('--worker',choices=['patch','easy','paddle','florence']);parser.add_argument('--target');args=parser.parse_args()
if not args.worker:
    image=Path(args.image) if args.image else ROOT/'work/data/koaltq_sample/images/026769b1356f3283.png'
    if not image.is_file():raise SystemExit('Image file not found: '+str(image))
    dest=ROOT/'outputs'/('retest_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));dest.mkdir()
    env=dict(os.environ,PYTHONIOENCODING='utf-8')
    for engine in ['patch','easy','paddle','florence']:
        print('Running',engine,flush=True)
        with (dest/(engine+'.log')).open('w',encoding='utf-8') as log:
            cp=subprocess.run([str(PADDLE if engine=='paddle' else LEGACY),str(Path(__file__)), '--worker',engine,'--image',str(image),'--target',str(dest)],stdout=log,stderr=subprocess.STDOUT,env=env)
        if cp.returncode:print('Failed:',engine,'see',dest/(engine+'.log'))
    from PIL import Image,ImageOps
    try:
        im=ImageOps.exif_transpose(Image.open(image)).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);bg.convert('RGB').save(dest/'input.png')
    except Exception:pass
    sections=[]
    for engine in ['patch','easy','paddle','florence']:
        p=dest/(engine+'.json');raw=p.read_text(encoding='utf-8') if p.exists() else 'Execution failed; inspect the log.'
        sections.append('<h2>'+engine+'</h2><pre>'+html.escape(raw)+'</pre>')
    body='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="../report.css"><title>단일 이미지 재실행</title><main><header><h1>단일 이미지 재실행</h1><p>원문 출력이며 정답 description이나 대회 품질판정 결과가 아닙니다.</p></header><img src="input.png" alt="재실행 입력" style="max-width:650px;width:100%">'+''.join(sections)+'</main></html>'
    (dest/'report.html').write_text(body,encoding='utf-8');print('REPORT:',dest/'report.html');sys.exit(0)
sys.path.append(str(ROOT/'work/ocr_env/Lib/site-packages'));sys.path.append(str(ROOT/'work/vision_modules'));sys.path.append(str(ROOT/'work/raster_modules'))
from PIL import Image,ImageOps
image=Path(args.image)
if image.suffix.lower()=='.svg':
    import io,resvg_py
    src=Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_path=str(image))))
else:src=Image.open(image)
src=ImageOps.exif_transpose(src).convert('RGBA');bg=Image.new('RGBA',src.size,'white');bg.alpha_composite(src);im=bg.convert('RGB');target=Path(args.target)
if args.worker=='patch':
    sys.path.insert(0,r'${PATCHIONER_SOURCE}\local_app')
    import runtime
    _,result=runtime.infer(im,[[0,0,im.width,im.height]])
    result['box_source']='single full-frame Gaussian patch pool for comparison'
elif args.worker=='easy':
    import easyocr,torch,numpy as np
    torch.set_num_threads(4);reader=easyocr.Reader(['ko','en'],gpu=True,model_storage_directory=str(ROOT/'work/models/easyocr'),download_enabled=False,verbose=False)
    torch.cuda.synchronize();start=time.perf_counter();raw=reader.readtext(np.asarray(im),detail=1,paragraph=False,batch_size=1,workers=0);torch.cuda.synchronize()
    result={'seconds':time.perf_counter()-start,'lines':[{'box':np.asarray(b).tolist(),'text':t,'confidence':float(c)} for b,t,c in raw]}
elif args.worker=='paddle':
    os.environ['PADDLE_PDX_CACHE_HOME']=str(ROOT/'work/models/paddlex');os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']='True';os.environ['HF_HOME']=str(ROOT/'work/models/huggingface')
    from paddleocr import PaddleOCR
    import numpy as np
    model=PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det',text_recognition_model_name='korean_PP-OCRv5_mobile_rec',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu',enable_mkldnn=False,cpu_threads=4)
    start=time.perf_counter();res=list(model.predict(np.asarray(im)[:,:,::-1]))[0].json
    if isinstance(res,str):res=json.loads(res)
    d=res.get('res',res);result={'seconds':time.perf_counter()-start,'lines':[{'text':t,'confidence':float(c),'box':b} for t,c,b in zip(d.get('rec_texts',[]),d.get('rec_scores',[]),d.get('rec_polys',[]))],'raw':res}
else:
    os.environ['HF_HOME']=str(ROOT/'work/models/huggingface')
    import torch
    from transformers import AutoModelForCausalLM,AutoProcessor
    torch.set_num_threads(4);path=str(ROOT/'work/models/florence2');model=AutoModelForCausalLM.from_pretrained(path,trust_remote_code=True,torch_dtype=torch.float16,attn_implementation='eager',local_files_only=True).to('cuda').eval();processor=AutoProcessor.from_pretrained(path,trust_remote_code=True,local_files_only=True)
    torch.cuda.synchronize();start=time.perf_counter();result={'tasks':{}}
    for task in ['<MORE_DETAILED_CAPTION>','<DENSE_REGION_CAPTION>']:
        inputs=processor(text=task,images=im,return_tensors='pt').to('cuda',torch.float16)
        with torch.inference_mode():ids=model.generate(input_ids=inputs['input_ids'],pixel_values=inputs['pixel_values'],max_new_tokens=256,num_beams=3,do_sample=False)
        raw=processor.batch_decode(ids,skip_special_tokens=False)[0];result['tasks'][task]={'raw':raw,'parsed':processor.post_process_generation(raw,task=task,image_size=im.size)}
    torch.cuda.synchronize();result['seconds']=time.perf_counter()-start
result['image_size']=list(im.size);result['metadata_used']=False;result['label_used']=False
(target/(args.worker+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
