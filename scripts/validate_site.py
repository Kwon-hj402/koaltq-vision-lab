from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from collections import Counter
import json, re


root = Path(__file__).resolve().parent.parent
class Page(HTMLParser):
    def __init__(self, file):
        super().__init__(); self.file=file; self.ids=[]; self.links=[]
        self.feed(file.read_text(encoding='utf-8'))
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        for k in ('href','src'):
            if a.get(k): self.links.append(a[k])

pages={p.resolve():Page(p) for p in root.rglob('*.html')}
samples=json.loads((root/'data/sample_results.json').read_text(encoding='utf-8'))
files={r['file'] for r in samples}
errors=[]; links=0
for p,doc in pages.items():
    duplicate=[k for k,v in Counter(doc.ids).items() if v>1]
    if duplicate: errors.append({'page':p.name,'duplicate_ids':duplicate})
    if re.search(r'@@[A-Z_]+@@',p.read_text(encoding='utf-8')): errors.append({'page':p.name,'unfilled_placeholder':True})
    for link in doc.links:
        u=urlsplit(link)
        if u.scheme or u.netloc: continue
        links+=1; target=(p.parent/unquote(u.path)).resolve() if u.path else p
        if not target.exists(): errors.append({'page':p.name,'missing':link}); continue
        if u.fragment and target in pages:
            frag=unquote(u.fragment)
            valid=frag in pages[target].ids or (target.name=='results.html' and frag in files)
            if not valid: errors.append({'page':p.name,'bad_anchor':link})
image_count=0
for p in (root/'assets').glob('*.png'):
    assert p.read_bytes().startswith(bytes.fromhex("89504e470d0a1a0a")), p.name
    image_count+=1
for row in samples:
    assert (root/row['asset']).is_file(),row['asset']
    for key in ('patch','easy','paddle'):
        assert row['models'].get(key) and not row['models'][key].get('error'),(row['file'],key)
packets=[json.loads(s) for s in (root/'data/evidence_packets.jsonl').read_text(encoding='utf-8').split('\n') if s.strip()]
def check_packet(obj,path=''):
    if isinstance(obj,dict):
        for k,v in obj.items():
            assert k not in ('label','reference','audit','keyphrase_checks'),(path,k)
            check_packet(v,path+'/'+k)
    elif isinstance(obj,list):
        for i,v in enumerate(obj): check_packet(v,path+'/'+str(i))
for row in packets: check_packet(row)
assert len(samples)==len(packets)==299
result={'checked_at':'2026-09-26','html_files':len(pages),'local_links_checked':links,'sample_rows':len(samples),'evidence_packets':len(packets),'png_signature_checks':image_count,'errors':errors,'packet_label_reference_audit_leakage':False}

print(json.dumps(result,ensure_ascii=False,indent=2))
assert not errors
