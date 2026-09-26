from pathlib import Path
import json,unicodedata,re,statistics,collections
R=Path(__file__).resolve().parents[1];E=R/'data'
def read(name):
    p=E/name
    return {r['file']:r for r in map(json.loads,filter(str.strip,p.read_text(encoding='utf-8').split('\n')))} if p.exists() else {}
def norm(s):return ''.join(c for c in unicodedata.normalize('NFC',s).casefold() if c.isalnum())
models={'easy':read('easy_all.jsonl'),'paddle':read('paddle_subset.jsonl'),'enhanced':read('easy_enhanced.jsonl'),'paddle_enhanced':read('paddle_enhanced.jsonl')}
refs=json.loads((E/'ocr_reference.json').read_text(encoding='utf-8'))
metrics={};details=[]
for name,data in models.items():
    if not data:continue
    total=0;hits=0;by=collections.defaultdict(lambda:[0,0])
    for item in refs['items']:
        if item['status']!='scorable':continue
        row=data.get(item['file'],{});text=' '.join(x['text'] for x in row.get('lines',[]));s=norm(text)
        for phrase in item['reference_strings']:
            found=norm(phrase) in s;total+=1;hits+=int(found);by[item['stratum']][0]+=int(found);by[item['stratum']][1]+=1
            details.append({'model':name,'file':item['file'],'reference':phrase,'found':found})
    metrics[name]={'hits':hits,'total':total,'recall':hits/total,'by_stratum':dict(by)}
union={};total=0
for item in refs['items']:
    if item['status']!='scorable':continue
    for phrase in item['reference_strings']:
        total+=1
        for group,names in [('native_union',['easy','paddle']),('enhanced_union',['enhanced','paddle_enhanced'])]:
            hit=any(norm(phrase) in norm(' '.join(x['text'] for x in models[n].get(item['file'],{}).get('lines',[]))) for n in names)
            union[group]=union.get(group,0)+int(hit)
for name,hits in union.items():metrics[name]={'hits':hits,'total':total,'recall':hits/total,'meaning':'any engine contains phrase; evidence availability, not adjudicated correctness'}
stats={}
for name,file,timing in [('patch','patch_all.jsonl','inference_seconds'),('patch_regions','patch_regions.jsonl','inference_seconds'),('easy','easy_all.jsonl','seconds'),('paddle_subset','paddle_subset.jsonl','seconds'),('paddle_all','paddle_all.jsonl','seconds'),('florence','florence_subset.jsonl','seconds'),('enhanced','easy_enhanced.jsonl','seconds'),('paddle_enhanced','paddle_enhanced.jsonl','seconds')]:
    data=read(file)
    if (E/'svg_repair.json').exists() and name in ['patch','easy','enhanced']:
        repair=json.loads((E/'svg_repair.json').read_text(encoding='utf-8'))[{'patch':'patch','easy':'easy','enhanced':'easy_enhanced'}[name]]
        data[repair['file']]=repair
    rows=list(data.values());valid=[r for r in rows if 'error' not in r];times=[r[timing] for r in valid if timing in r]
    stats[name]={'records':len(rows),'successful':len(valid),'errors':[r for r in rows if 'error' in r],'median_seconds':statistics.median(times) if times else None,'mean_seconds':statistics.mean(times) if times else None,'sum_seconds':sum(times),'p95_seconds':sorted(times)[min(len(times)-1,int(.95*len(times)))] if times else None,'peak_gpu_allocated_mb':max((r.get('peak_gpu_allocated_mb',0) for r in valid),default=0),'ocr_nonempty':sum(any(str(x.get('text','')).strip() for x in r.get('lines',[])) for r in valid)}
result={'keyphrase_method':'NFC + Unicode alphanumeric only + casefold; exact substring within concatenated engine reading-order strings; assistant transcribed selected phrases; not full CER or human expert accuracy','metrics':metrics,'statistics':stats,'details':details}
expected=json.loads((E/'analysis.json').read_text(encoding='utf-8'))
assert metrics == expected['metrics'], 'Saved metrics do not match recalculation'
print(json.dumps({'metrics':metrics,'statistics':stats},ensure_ascii=False,indent=2))
