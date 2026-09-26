from pathlib import Path
import sys,json,time
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,r'${PATCHIONER_SOURCE}\local_app')
import runtime
from PIL import Image,ImageOps
items=json.loads((R/'work/subset.json').read_text(encoding='utf-8'))
fl={r['file']:r for r in map(json.loads,(R/'work/experiments/florence_subset.jsonl').read_text(encoding='utf-8').splitlines())}
with (R/'work/experiments/patch_regions.jsonl').open('w',encoding='utf-8') as f:
    for i,r in enumerate(items):
        row={'file':r['file'],'stratum':r['stratum']}
        try:
            im=ImageOps.exif_transpose(Image.open(r['path'])).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('RGB')
            d=fl[r['file']]['tasks']['<DENSE_REGION_CAPTION>']['parsed']['<DENSE_REGION_CAPTION>']
            boxes=[[0,0,im.width,im.height]]; labels=['full-frame Gaussian patch pooling']
            for b,label in zip(d.get('bboxes',[]),d.get('labels',[])):
                if len(boxes)>=4:break
                if b[2]-b[0]>2 and b[3]-b[1]>2: boxes.append(b);labels.append(label)
            _,result=runtime.infer(im,boxes)
            result['box_source']='first region = full frame; subsequent regions = first three valid Florence-2 dense-region predictions; no ground-truth or human boxes'
            result['florence_region_labels']=labels
            row.update(result)
        except Exception as e:row['error']=f'{type(e).__name__}: {e}'
        f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        print(i,r['file'],row.get('inference_seconds'),row.get('regions',row.get('error')),flush=True)
