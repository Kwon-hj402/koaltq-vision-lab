from pathlib import Path
import json,html,shutil,hashlib,collections,statistics,datetime,platform,subprocess
from urllib.parse import quote
from PIL import Image
R=Path(__file__).resolve().parents[1];W=R/'work';O=R/'outputs';D=O/'data';D.mkdir(exist_ok=True)
def j(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').split('\n') if x.strip()]
def esc(s):return html.escape(str(s))
def table(headers,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+str(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def link(url,label):return f'<a href="{html.escape(url,quote=True)}">{esc(label)}</a>'
inventory=j(W/'image_inventory.json');subset={x['file']:x for x in j(W/'subset.json')};records={r['image_file']:r for r in jl(W/'data/koaltq_sample/records.jsonl')};refs={r['file']:r for r in j(W/'ocr_reference.json')['items']}
model_paths={'patch':'patch_all.jsonl','patch_regions':'patch_regions.jsonl','easy':'easy_all.jsonl','paddle':'paddle_all.jsonl','florence':'florence_subset.jsonl','enhanced':'easy_enhanced.jsonl','paddle_enhanced':'paddle_enhanced.jsonl'}
models={k:{r['file']:r for r in jl(W/'experiments'/v)} for k,v in model_paths.items()}
repair=j(W/'experiments/svg_repair.json')
for k,rk in [('patch','patch'),('easy','easy'),('enhanced','easy_enhanced')]:models[k][repair[rk]['file']]=repair[rk]
audits={k:{r['file']:r for r in j(W/f'{k}_visual_audit.json')['records']} for k in ['patch','florence']}
analysis=j(W/'experiments/analysis.json');rows=[];packets=[]
for r in inventory:
    file=r['file'];m=records[file];s=subset.get(file,{});row={'file':file,'record_id':m['record_id'],'sha256':r['sha256'],'size':r['size'],'format':r['format'],'asset':'assets/'+Path(file).stem+'.png','stratum':s.get('stratum','unselected'),'models':{key:values.get(file) for key,values in models.items()},'reference':refs.get(file),'audit':{key:a.get(file) for key,a in audits.items()},'metadata':{key:m[key] for key in ['alt_text','page_title','context_text','in_link','link_dest','heading_path','page_url']}}
    if file.endswith('.svg'):row['alternate_asset']='assets/'+Path(file).stem+'_enhanced.png'
    row['keyphrase_checks']=[x for x in analysis['details'] if x['file']==file]
    rows.append(row)
    observations=[]
    for key in ['paddle','easy','paddle_enhanced','enhanced']:
        pred=row['models'].get(key)
        if pred:
            observations.append({'source':key,'preprocessing':pred.get('policy') or ('native white composite' if key in ['paddle','easy'] else 'conditional alpha/upscale/tiles'),'status':'raw_unverified_ocr','lines':pred.get('lines',[]),'view_results':pred.get('view_results'),'notes':'score is not calibrated probability; keep primary and alternate observations separate'})
    visual=[]
    p=row['models']['patch']
    if p and 'whole_image' in p:visual.append({'source':'patchioner_capdec_cls','text':p['whole_image'],'status':'unverified'})
    p=row['models']['florence']
    if p and p.get('tasks'):
        visual.append({'source':'florence2_base_detailed','text':p['tasks']['<MORE_DETAILED_CAPTION>']['parsed']['<MORE_DETAILED_CAPTION>'],'status':'unverified'})
        visual.append({'source':'florence2_base_dense','regions':p['tasks']['<DENSE_REGION_CAPTION>']['parsed']['<DENSE_REGION_CAPTION>'],'status':'unverified'})
    packets.append({'schema_version':'pre_llm_evidence_v1','record_id':m['record_id'],'image':{'file':file,'sha256':r['sha256'],'width':r['size'][0],'height':r['size'][1]},'ocr_observations':observations,'visual_candidates':visual,'uncertainty':['OCR and model-generated descriptions are unverified; preserve conflicting alternatives','Caption demographic, identity, count, purpose and event claims must not be assumed true','No final description synthesis or classification has been run'],'context_metadata':row['metadata'],'provenance':{'vision_used_metadata':False,'vision_used_label':False,'florence_and_enhanced_scope':'purposeful diagnostic subset, not an automatic production router'}})
(D/'sample_results.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
(D/'evidence_packets.jsonl').write_text('\n'.join(json.dumps(p,ensure_ascii=False) for p in packets)+'\n',encoding='utf-8')
for p in (W/'experiments').glob('*.json*'):shutil.copy2(p,D/p.name)
for name in ['patch_visual_audit.json','florence_visual_audit.json','patch_region_notes.json','ocr_reference.json','subset.json','caption_candidates.json','ocr_candidates.json']:shutil.copy2(W/name,D/name)
shutil.copy2(W/'evaluation_sources/evaluation_candidates.json',D/'evaluation_candidates.json')
shutil.copy2(W/'evaluation_sources/aida_overview_2026-09-26.json',D/'aida_overview_2026-09-26.json')
(D/'image_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
manifest={'created_at':datetime.datetime.now().astimezone().isoformat(),'date':'2026-09-26','source_archive_name':'koaltq_sample_299.zip','source_archive_sha256':hashlib.sha256(Path(r'${DATASET_ARCHIVE}').read_bytes()).hexdigest(),'record_count':len(records),'unique_image_files':len(inventory),'unique_file_content_sha256':len({r['sha256'] for r in inventory}),'hardware':{'gpu':'NVIDIA GeForce GTX 1660','vram_mib':6144,'cpu':'AMD Ryzen 7 3700X, 8C/16T','ram_bytes':34277883904,'os':'Windows'},'label_counts':dict(collections.Counter(r['label'] for r in records.values())),'scope':'Description/OCR component diagnostics, not a Gemma or final 7-class evaluation','global_image_policy':'EXIF transpose; alpha over white; first frame; all GIFs single-frame; SVG separately rasterized with resvg-py0.5.0','inference_inputs':'image pixels only, without alt/context/labels','references':'assistant-authored visual diagnoses; not independently human validated','metadata':{p.stem:j(p) for p in (W/'experiments').glob('*meta.json')}}
for root in [W/'models/florence2',W/'models/easyocr']:
    manifest.setdefault('weights',[]).extend({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.glob('*') if p.suffix in ['.safetensors','.pth'])
(D/'experiment_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
payload=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
(O/'results.html').write_text((W/'results_template.html').read_text(encoding='utf-8').replace('@@DATA@@',payload),encoding='utf-8')
priorities=[
['Patch-ioner','CVPR 2026 poster; IF4 확인 안 됨','코드·CapDec 가중치 공개 / 사용자 학습 없음','한국어 OCR 아님. 정답 box를 쓰는 논문 실험과 자동 검출을 구분.','299개 전역 +42개 영역 실행',link('https://github.com/Ruggero1912/Patch-ioner','코드')+' · '+link('https://arxiv.org/html/2510.02898v2','논문')],
['PP-OCRv5 한국어','CVPR 2026 poster; IF4 확인 안 됨','탐지·인식 코드와 한국어 배포 가중치 공개','OCR 구성요소. 사진·아이콘 의미를 단독 설명하지 않음.','299개 기본 +42개 보완 실행',link('https://github.com/PaddlePaddle/PaddleOCR','코드')+' · '+link('https://openaccess.thecvf.com/content/CVPR2026/html/Cui_PP-OCRv5_A_Specialized_5M-Parameter_Model_Rivaling_Billion-Parameter_Vision-Language_Models_on_CVPR_2026_paper.html','논문')],
['PaddleOCR-VL','CVPR 2026 highlight poster','0.9B·코드 공개; 영역·관계 탐지 후 세부 인식','한국어 문서형 후보. 전체 파서와 recognition-only 예제를 구분.','문헌 검증, 로컬 미실행',link('https://github.com/PaddlePaddle/PaddleOCR','코드')+' · '+link('https://openaccess.thecvf.com/content/CVPR2026/html/Cui_Boosting_Document_Parsing_Efficiency_and_Performance_with_Coarse-to-Fine_Visual_Processing_CVPR_2026_paper.html','논문')],
['Cap-Workflow','CVPR 2026 poster','저장소는 README·그림; 실행 코드 없음','설계 적합하지만 공개 구현 조건 불충족. 보충자료에 일부 외부 API 사용.','설계 참고',link('https://github.com/syp2ysy/Cap-Workflow','저장소')+' · '+link('https://openaccess.thecvf.com/content/CVPR2026/html/Sun_Enhancing_Descriptive_Captions_with_Visual_Attributes_for_Multimodal_Perception_CVPR_2026_paper.html','논문')],
['Draft and Refine (DnR)','CVPR 2026 highlight poster','초안 → visual expert → 수정. 기본 전수 비교 경로는 추가학습 없음','학습된 selector 확장은 별개. 한국어 성능 미확인.','후속 오류 억제 후보',link('https://github.com/EavnJeong/Draft-and-Refine-with-Visual-Experts','코드')+' · '+link('https://arxiv.org/abs/2511.11005','논문')],
['GroundingAgent / CEBC','AAAI 2026 / ACL 2026 본회의','GroundingAgent 코드 공개. CEBC 공식 코드 미확인','전자는 query→box, 후자는 detector 기반 생성 보정. 포괄 설명 완성품과 다름.','구성요소·평가 참고',link('https://github.com/loiqy/GroundingAgent','GroundingAgent')+' · '+link('https://aclanthology.org/2026.acl-long.2142/','CEBC')],
['Florence-2 / EasyOCR','CVPR 2024 / CRAFT CVPR 2019 계열','코드·가중치 존재; 2026 엄격 후보 밖','이미지/영역 설명과 한국어 OCR를 분리 비교하기 위한 실용 기준선.','42개/299개 실제 실행',link('https://huggingface.co/microsoft/Florence-2-base','Florence 구현')+' · '+link('https://github.com/JaidedAI/EasyOCR','EasyOCR 코드')]]
stats=analysis['statistics']; runtime_rows=[]
for key,name,device,note in [('patch','Patch-ioner CapDec CLS','GPU','SVG 보완 포함'),('patch_regions','Patch Gaussian 집계 + 자동 영역','GPU','전체 프레임 + 최대3개 후보 영역'),('easy','EasyOCR 기본','GPU','SVG 보완 포함'),('paddle_all','PP-OCRv5 한국어 기본','CPU','42개 결과 재사용 + 나머지257개'),('florence','Florence-2-base','GPU','상세 설명 + dense region 두 작업 합계'),('enhanced','EasyOCR 보완','GPU','공통42개 + alpha/SVG 진단43개'),('paddle_enhanced','PP-OCRv5 보완','CPU','공통42개')]:
    v=stats[key];runtime_rows.append([name,f"{v['successful']}/{v['records']}",device,f"{v['median_seconds']:.3f}",f"{v['p95_seconds']:.3f}",f"{v['peak_gpu_allocated_mb']:.1f}" if device=='GPU' else '해당 없음',note])
metrics=analysis['metrics'];recall_rows=[]
names={'easy':'EasyOCR 기본','enhanced':'EasyOCR + 조건부 전처리','paddle':'PP-OCRv5 한국어 기본','paddle_enhanced':'PP-OCRv5 + 조건부 전처리','native_union':'두 기본 OCR의 출력 합집합','enhanced_union':'두 보완 OCR의 출력 합집합'}
for key in ['easy','enhanced','paddle','paddle_enhanced','native_union','enhanced_union']:
    v=metrics[key];by=v.get('by_stratum',{});recall_rows.append([names[key],f"<strong>{v['hits']}/72 ({100*v['recall']:.1f}%)</strong>"]+[f'{by[g][0]}/{by[g][1]}' if g in by else '—' for g in ['logo','text_banner','mixed','layout','challenge']])
audit_rows=[]
for key,name in [('patch','Patch CapDec CLS'),('florence','Florence 상세')]:
    a=[v for v in audits[key].values() if v['stratum']!='challenge'];counts=collections.Counter(v['alignment'] for v in a)
    audit_rows.append([name,len(a),counts['핵심대상 맞음'],counts['부분적'],counts['불일치'],sum(bool(v['unsupported']) for v in a)])
ocr_interpretation='<p>이 표본에서는 기본 PP-OCRv5가 57/72로 기본 EasyOCR의 46/72보다 선택 문구를 더 많이 남겼다. 하지만 한국어 OCR 전체의 우열이나 대회 성능을 확정할 수는 없다. 확대·분할 후 EasyOCR는 48/72로 늘었으나 PP-OCRv5는 56/72로 줄었다. <strong>전처리를 늘리는 것 자체가 개선을 보장하지 않았다.</strong></p><p>16×16 숫자 ‘3’은 확대 후 두 OCR에서 회복됐다. 반면 긴 포스터에서는 타일 경계의 부분 문자열과 중복 병합이 ‘치매안심 재산관리 서비스’, 생년월일 범위를 끊거나 반복해 핵심문구의 연속성을 잃었다. 이 감소에는 인식 오류뿐 아니라 병합·읽기 순서 오류도 포함된다. 따라서 기본 전체뷰 결과를 보존하고 타일 결과는 출처가 다른 대안으로 전달해야 한다. 합집합의 작은 증가는 정답을 자동 선택한 개선치로 사용할 수 없다.</p>'
cases=[
('039c94d89a6db2c3','사진: 마이크를 와인잔으로 바꾸는 오류','Patch는 인물이라는 큰 범주는 잡았지만 손에 든 마이크를 와인잔으로 기술했다. Florence는 마이크를 회복했으나 보이지 않는 손짓과 연령·배경 추정을 추가했다. 실제 없는 글자를 OCR가 반환할 수도 있으므로 사진의 잡음을 텍스트로 확정하지 않는다.'),
('026769b1356f3283.png','로고: 기관명은 OCR에서 회복','두 OCR는 문화체육관광부·국립중앙도서관 문구를 읽었다. Patch의 표지판·인물 설명으로는 기관을 식별할 수 없다. 기관명을 LLM이 caption에서 추론하게 할 필요가 없다.'),
('1b7d42dd2f95b6e1.jpg','텍스트 배너: 핵심 문구와 숫자의 보존','사진 캡션은 이 안내물을 소화전으로 묘사했다. OCR는 상담 1366과 신고 112를 남겼지만, 장식적인 제목 글꼴과 기관명의 오독이 남아 있다. 숫자 일부가 맞았다고 전체 문구가 정확한 것은 아니다.'),
('7a9e3ca7407f9a30.jpg','혼합 이미지: 사진의 장면과 홍보 주제를 분리','OCR는 ‘평생소득 / 안전망, / 국민연금’을 읽었다. Florence는 드라마 홍보물이라고 추정했다. 가족 사진처럼 보이는 요소가 있더라도 홍보의 주제는 글자 증거에서 확인해야 한다.'),
('25198da01a56c796.png','배치도: OCR 이후에도 공간 구조는 남는 문제','Patch는 배치도를 버스로 잘못 설명했다. OCR의 많은 줄은 방·창구·연락처 정보를 일부 남기지만 위치와 기능의 대응까지 검증되지는 않았다. 구조화 parser가 필요한 이유다.'),
('11cc05715bac383f.png','16×16 숫자: 확대가 실제 도움이 된 사례','기본 EasyOCR는 문자를 반환하지 않았고 PP-OCRv5는 점을 반환했다. 고정 확대 규칙 이후 숫자 3이 회복됐다. 모든 작은 이미지에서 동일한 복원 효과를 보장하지는 않는다.'),
('58a031d1909dc03e.do','고해상도 포스터: 타일을 늘려도 병합이 실패할 수 있음','전체뷰 PP-OCRv5에는 ‘치매안심재산관리서비스란?’이 남았지만 보완 병합에서는 제목이 부분 문자열로 나뉘었다. 더 많은 검출 줄이 더 좋은 최종 description을 뜻하지 않는다. 원래 전체뷰와 타일별 결과를 따로 보존해야 한다.')]
byfile={r['file']:r for r in rows};case_html=[]
for i,(file,title,note) in enumerate(cases,1):
    r=byfile[file];p=r['models'];f=p.get('florence');caption=f['tasks']['<MORE_DETAILED_CAPTION>']['parsed']['<MORE_DETAILED_CAPTION>'] if f else '미실행'
    ocr=' | '.join(x['text'] for x in p['paddle'].get('lines',[]) if x['text'].strip())
    extras=''
    if file=='11cc05715bac383f.png':extras='<p class="label">확대 후 PP-OCRv5</p><p class="output">'+esc(' | '.join(x['text'] for x in p['paddle_enhanced'].get('lines',[])))+'</p>'
    case_html.append(f'<article class="case"><h3>5.{i} {esc(title)}</h3><div class="case-grid"><figure><img src="{r["asset"]}" alt="{esc(title)}" loading="lazy" style="'+('width:160px;image-rendering:pixelated' if max(r['size'])<64 else '')+f'"><figcaption>{esc(r["record_id"])} · {r["size"][0]}×{r["size"][1]}</figcaption></figure><div><p class="label">Patch 전역 원문</p><p class="output">{esc(p["patch"]["whole_image"])}</p><p class="label">PP-OCRv5 원문 발췌</p><p class="output">{esc(ocr[:310])}{"…" if len(ocr)>310 else ""}</p><p class="label">Florence 상세 원문 발췌</p><p class="output">{esc(caption[:290])}{"…" if len(caption)>290 else ""}</p>{extras}<p>{esc(note)}</p><p class="small"><a href="results.html#{quote(file)}">이 샘플의 전체 출력·좌표 열기</a></p></div></div></article>')
replace={'@@ABSTRACT_RECALL@@':'EasyOCR 기본 46/72, PP-OCRv5 기본 57/72, 보완 후 각각 48/72와 56/72','@@PRIORITY_TABLE@@':table(['후보','학회·엄격 기준','공개·학습 조건','이 문제와의 관계','이번 확인','직접 링크'],priorities),'@@RUNTIME_TABLE@@':table(['실험','성공/대상','장치','중앙값(초)','P95(초)','GPU 최대(MiB)','범위'],runtime_rows),'@@RECALL_TABLE@@':table(['조건','전체 핵심문구','로고','텍스트','혼합','레이아웃','난례'],recall_rows),'@@AUDIT_TABLE@@':table(['상세 설명 조건','n','핵심대상 맞음','부분적','불일치','근거 없는 주장 포함'],audit_rows),'@@OCR_INTERPRETATION@@':ocr_interpretation,'@@CASE_STUDIES@@':'\n'.join(case_html)}
report=(W/'report_template.html').read_text(encoding='utf-8')
for a,b in replace.items():report=report.replace(a,b)
assert '@@' not in report
(O/'report.html').write_text(report,encoding='utf-8')
print(json.dumps({'reports':'created','samples':len(rows),'packets':len(packets),'runtime_counts':{k:v['successful'] for k,v in stats.items()},'audit':audit_rows,'recall':{k:v['hits'] for k,v in metrics.items()}},ensure_ascii=False,indent=2))
