from pathlib import Path
import json, re, html, shutil, collections
from urllib.parse import quote

R=Path(__file__).resolve().parents[1]; O=R/'outputs'; W=R/'work'
for name in ['report.html','reproducibility.html','results.html','report.css']:
    backup=W/('before_team_'+name)
    if not backup.exists(): shutil.copy2(O/name,backup)
rows=json.loads((O/'data/sample_results.json').read_text(encoding='utf-8'))
byfile={r['file']:r for r in rows}
analysis=json.loads((O/'data/analysis.json').read_text(encoding='utf-8'))
old=(W/'before_team_report.html').read_text(encoding='utf-8')
oldtables=re.findall(r'<div class="table-wrap">.*?</div>',old,re.S)
esc=lambda x:html.escape(str(x))
def ul(items): return '<ul class="facts">'+''.join('<li>'+s+'</li>' for s in items)+'</ul>'
def link(url,label): return f'<a href="{esc(url)}">{esc(label)}</a>'
def table(headers,items,cls=''):
    return f'<div class="table-wrap {cls}"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in items)+'</tbody></table></div>'
nav='<nav aria-label="자료 이동"><a href="report.html">조사·실험 진행 정리</a><a href="literature.html">논문 조사 노트</a><a href="gallery.html">43개 예시 모아보기</a><a href="results.html">299개 원문·좌표 확인</a><a href="reproducibility.html">재실행·기록</a></nav>'
def page(title,body,subtitle='2026.09.26 실험 기록 · 결과를 다시 실행하지 않고 공유 형식을 개편함'):
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><link rel="stylesheet" href="team-notes.css?v=3"></head><body><main><header><div class="eyebrow">0923 PROJECT / TEAM NOTES</div><h1>'+title+'</h1><p class="meta">'+subtitle+'</p>'+nav+'</header>'+body+'<footer>2026.09.26의 조사·실측 기록이다. 모델 원문과 확인 메모를 분리하였다. 문헌 확인, 실제 실행, 후속 제안을 구분해 표시하였다.</footer></main></body></html>'
groups={'photo':'사진','icon':'아이콘','logo':'로고','text_banner':'텍스트 배너','mixed':'사진·그림 + 글자','layout':'지도·표·흐름도','challenge':'작거나 큰 입력'}
titles={
'039c94d89a6db2c3':'마이크를 들고 말하는 인물','18e9f9bdfa0ef112.png':'얼굴 중심의 인물 사진','21f0660741e35439.jpg':'화재 흔적과 잔해','2704361fd844b918.jpg':'전시장의 로봇','7eb29474dd9cd8e3.jpg':'도로 공사 현장','9c17cdeeba6b0782.jpg':'현수막 앞 단체사진',
'1138e6cad536ac89.png':'노란 해 아이콘','14e1ab1c400daf72.png':'모니터와 선그래프','28310e5cc65c488e.gif':'오른쪽 이동 화살표','3b117c7e08f4d107.png':'주황색 태양 아이콘','428f1b4c5969909c.png':'악수 아이콘','c0394af33514ebb1.png':'자동차와 전기 플러그',
'026769b1356f3283.png':'문화체육관광부·국립중앙도서관','075ba88c36bea11a.do':'보건복지부 로고','0e1b6909831958ac.png':'NVIDIA 로고','1e071b0427c69490.png':'MIRIAN 로고','423177cbdda8d724.gif':'국립암센터 로고','d5aeb9aec8a6aac3.png':'DONG-GU 로고',
'1b7d42dd2f95b6e1.jpg':'레드플래그 안내와 긴급전화','1d3b9f31517547fe.jpg':'정책브리핑 뉴스스탠드 배너','38f9fbfe72f770f3.jpg':'공공재정 부정청구 신고 안내','4741d9518dea78ff.jpg':'배고픔과 증명서에 관한 문구','569b18fe5cf1b3f9.jpg':'대구 도시디자인 공모전','ad9f57c142a01c88.jpg':'대구광역시 사회조사 안내',
'046bf6ae3c5e646b.es':'아동권리 사연 공모전','2426950fc41b9a93.png':'초등방학 틈새돌봄 안내','3fd77908165a4ba9.jpg':'임산부·영유아 건강 교실','425f8567e6c2156b.jpg':'국민의 멜로디 징글 공모전','7a9e3ca7407f9a30.jpg':'가족 사진과 국민연금 문구','b182f126d1b1dbba.jpg':'트로피와 박물관 성과 안내',
'01fee160037c164e.do':'APEC 웹 화면의 3분할 배치','0be9f0f533833af2.jpg':'안전점검 안내 인포그래픽','0c65e63384de3f64.png':'기관 주변 지도','25198da01a56c796.png':'민원 창구 배치도','28b16068d4379176.png':'농업인 교육 일정표','658a87ad149352ab.jpg':'신고 처리 절차도',
'11cc05715bac383f.png':'16×16 숫자 3','1515dfefb89fa6d5.gif':'22×6 NEW 표시','58a031d1909dc03e.do':'치매안심 재산관리 포스터','6f96819d13a5746b.do':'고해상도 빙상장 썸네일','c218978fb8f2c443.gif':'문자를 확정하기 어려운 10×10 아이콘','f87a726b3de847c3.do':'HPV 예방접종 안내',
'f59e7f64d7640153.svg':'밝은 전경의 투명 SVG'}
def ocr_text(r,key):
    return ' | '.join(x['text'] for x in (r['models'].get(key) or {}).get('lines',[]) if x['text'].strip()) or '(반환된 문자열 없음)'
def excerpt(text,n=270): return esc(text[:n])+('…' if len(text)>n else '')
def florence(r): return (r['models'].get('florence') or {}).get('tasks',{}).get('<MORE_DETAILED_CAPTION>',{}).get('parsed',{}).get('<MORE_DETAILED_CAPTION>','이 샘플에서는 실행하지 않았다.')
def check_table(r):
    ref=r.get('reference')
    if not ref or not ref.get('reference_strings'): return ''
    checks={(x['model'],x['reference']):x['found'] for x in r.get('keyphrase_checks',[])}
    out=[]
    for text in ref['reference_strings']:
        out.append([esc(text)]+[('포함' if checks[(key,text)] else '미포함') if (key,text) in checks else '—' for key in ['easy','paddle','enhanced','paddle_enhanced']])
    return '<h4>선정한 문구가 출력에 남았는가</h4>'+table(['이미지에서 선정한 문구','Easy 기본','PP 기본','Easy 보완','PP 보완'],out,'phrase-table')
def case(r,index,full=False):
    f=r['file']; a=r['audit']; out='<article class="sample-case" id="case-'+Path(f).stem+'"><div class="case-heading"><span>'+str(index).zfill(2)+'</span><h3>'+esc(titles.get(f,f))+'</h3></div>'
    out+='<div class="case-body"><figure><a href="'+r['asset']+'" target="_blank"><img src="'+r['asset']+'" loading="lazy" alt="'+esc(titles.get(f,f))+'"'+(' class="tiny"' if max(r['size'])<70 else '')+'></a><figcaption>'+esc(r['record_id'])+' · '+str(r['size'][0])+'×'+str(r['size'][1])+' px<br>클릭하면 큰 이미지로 확인할 수 있다.</figcaption></figure><div>'
    out+=ul(['<b>Patch 확인:</b> '+esc((a.get('patch') or {}).get('note','추가 시각 점검 없음.')),'<b>Florence 확인:</b> '+esc((a.get('florence') or {}).get('note','추가 시각 점검 없음.'))])
    if r.get('reference') and r['reference'].get('status')=='scorable':
        checks=r['keyphrase_checks']; summary=[]
        for key,label in [('easy','Easy 기본'),('paddle','PP 기본'),('enhanced','Easy 보완'),('paddle_enhanced','PP 보완')]:
            subset=[c for c in checks if c['model']==key]
            if subset:summary.append(label+' '+str(sum(x['found'] for x in subset))+'/'+str(len(subset)))
        out+='<p class="case-metric">선정 문구 포함: '+ ' · '.join(summary)+'</p>'
    out+='<div class="raw-output"><b>Patch 원문</b><blockquote>'+esc(r['models']['patch']['whole_image'])+'</blockquote><b>PP-OCRv5 원문'+(' 발췌' if len(ocr_text(r,'paddle'))>320 else '')+'</b><blockquote>'+excerpt(ocr_text(r,'paddle'),320)+'</blockquote><b>Florence 원문 발췌</b><blockquote>'+excerpt(florence(r))+'</blockquote></div>'
    if full:
        out+=check_table(r)
        out+='<details><summary>모델별 OCR·상세 설명 전문 펼치기</summary>'
        for key,label in [('paddle','PP-OCRv5 기본'),('easy','EasyOCR 기본'),('paddle_enhanced','PP-OCRv5 보완'),('enhanced','EasyOCR 보완')]:
            out+='<h4>'+label+'</h4><pre>'+esc(ocr_text(r,key))+'</pre>'
        out+='<h4>Florence 상세 설명 전문</h4><pre>'+esc(florence(r))+'</pre></details>'
        regions=(r['models'].get('patch_regions') or {}).get('regions',[])
        if regions:
            out+='<details><summary>실제 패치 집계·영역별 출력 펼치기</summary>'+ul(['전체 프레임 Gaussian 집계와 Florence가 예측한 영역을 사용하였다. 정답 box는 사용하지 않았다.'])
            for j,region in enumerate(regions):
                out+='<h4>'+('전체 프레임 Gaussian 집계' if j==0 else f'자동 영역 {j}')+'</h4><p class="meta">원본 좌표 '+esc([round(v,1) for v in region['box_xyxy']])+'</p><pre>'+esc(region['caption'])+'</pre>'
            out+='</details>'
        extra=(a.get('florence') or {}).get('factual_errors',[])+(a.get('florence') or {}).get('uncertain_inferences',[])
        if extra: out+='<details><summary>세부 오류·추정 메모</summary>'+ul([esc(x) for x in extra])+'</details>'
    out+='<a class="text-link" href="results.html#'+quote(f)+'">전체 출력·좌표·영역 설명 확인 →</a></div></div></article>'
    return out

progress=[
['01','문제와 기준을 정리하였다.','한국어 글자, 사진·아이콘, 혼합 이미지의 설명 문제를 나누었다.','<a href="#problem">목표와 조사 기준</a>'],
['02','2026 후보 20개를 비교하였다.','논문·공식 코드·가중치·학습 조건·한국어 근거를 확인하였다.','<a href="#research">조사한 방법과 선택</a>'],
['03','로컬 샘플 299개를 정리하였다.','포맷·크기·투명도·중복을 확인하고 모델 입력을 준비하였다.','<a href="#data">샘플 처리 과정</a>'],
['04','기본 3개 구성요소를 299개에 실행하였다.','Patch-ioner, EasyOCR, PP-OCRv5의 결과를 저장하였다.','<a href="#runs">실행 범위와 조건</a>'],
['05','42개를 추가 비교하였다.','Florence, 실제 패치 집계, 확대·대비·타일 처리를 확인하였다.','<a href="#findings">수치와 확인 결과</a>'],
['06','출력과 이미지를 대조하였다.','대표 사례 12개와 유형별 진단 42개를 정리하였다.','<a href="#examples">실제 예시</a>'],
['07','LLM에 전달할 형태를 정리하였다.','299개 근거 묶음을 만들고, 다음 실험을 제안하였다.','<a href="#next">결합안과 남은 작업</a>']]
body='<section id="contents"><h2>먼저, 어떤 순서로 진행하였는가</h2>'+table(['순서','진행한 작업','확인한 내용','목차'],progress,'progress-table')
body+='<div class="brief">'+ul(['<b>실행 완료:</b> 비전·OCR 추출, 보완 전처리, 출력 비교, 299개 근거 묶음 저장.','<b>아직 미실행:</b> Gemma 최종 판정, 웹 검증 agent, 대회 F1 측정.','<b>먼저 확인한 결론:</b> 한국어 글자는 OCR로, 장면·도형은 caption으로 나누어 추출할 필요가 있었다.'])+'</div></section>'
body+='<section id="problem"><h2>1. 해결할 문제를 이렇게 나누었다</h2>'+ul(['<b>목표:</b> 단일 이미지에서 빠진 정보와 지어낸 정보를 줄여 description의 재료를 추출하고자 하였다.','<b>대회와 연결:</b> 최종 과제는 주어진 alt의 품질을 7범주로 판정하는 것이므로, 이미지 설명은 판정에 쓰일 증거로 다루었다. '+link('https://aida.kisti.re.kr/competition/main/problem/PROB_000000000004610/detail.do','공식 문제'),'한글이 포함된 포스터와 사진·아이콘을 같은 captioner 하나로 처리할 수 있는지 확인하였다.'])
body+=table(['이미지에서 필요한 정보','확인한 처리','주의할 부분'],[['기관명·날짜·전화번호','Text detection → recognition(OCR)','위치 탐지만으로 글자가 읽히지는 않는다.'],['사람·사물·행동·장면','전체 및 영역 caption','유창한 설명에도 없는 물체·행동이 포함될 수 있다.'],['표·지도·화살표의 관계','좌표와 구조 분석','OCR 문자열만 나열해도 행·열·연결 관계는 빠질 수 있다.'],['아이콘의 기능·장식성','이미지 + 링크·주변 문맥','외형만 보고 링크 목적과 장식 여부를 확정하기 어렵다.']])+'</section>'
body+='<section id="research"><h2>2. 논문은 무엇을 찾고, 어떻게 걸렀는가</h2>'+ul(['<b>2026 후보 20개</b>를 중복 없이 비교하였다. 2024/25 방법은 보완 후보로 따로 다루었다.','공식 논문에서 입출력·구조·학습 조건을 확인하였다. GitHub에서는 저장소 존재와 실제 실행 코드 공개를 구분하였다.','한국어 출력 가능 여부와 한국어 글자 인식 근거를 구분하였다. 우리 샘플에서 동작한다는 뜻으로 확대하지 않았다.','<b>training (x)</b>는 공개 가중치를 사용하고 우리 데이터로 추가 학습하지 않는 조건으로 적용하였다.','지정 BK21 표는 CVPR oral=4, spotlight=2, poster=공란이었다. 학회 이름만으로 IF≥4 충족 처리하지 않았다. '+link('https://gist.github.com/Pusnow/6eb933355b5cb8d31ef1abcb3c3e1206','지정 기준표'),'모든 조건을 동시에 확인한 완성형 방법은 이번 조사 후보군에서 찾지 못하였다.'])
body+=oldtables[1]+'<p class="jump">'+link('literature.html','20개 후보별 구조·코드 공개·한국어 근거·판단 보기 →')+'</p>'+ul(['<b>직접 실행 대상으로 선택:</b> Patch-ioner + PP-OCRv5 + EasyOCR + Florence-2.','<b>선택 이유:</b> 공개 가중치와 실행 경로가 있고, 한국어 OCR와 시각 설명의 역할을 분리 비교할 수 있었다.','<b>문헌 검토에만 포함:</b> PaddleOCR-VL, DnR, Cap-Workflow 등. 이들을 이번 샘플에서 실행한 것으로 표시하지 않았다.'])+'</section>'
body+='<section id="data"><h2>3. 샘플 데이터는 어떻게 처리하였는가</h2><h3>3-1. 압축 파일에서 실제 이미지와 메타데이터를 확인하였다</h3>'+ul(['입력은 로컬 <code>koaltq_sample_299.zip</code>이었다. 299개 레코드와 299개 이미지 파일의 대응을 확인하였다.','파일 내용의 고유 SHA-256은 289개였다. 동일한 파일 내용이 중복되어 있었다.','JPEG 157개, PNG 135개, GIF 6개, SVG 1개로 확인하였다. GIF 6개는 모두 한 프레임이었다.','긴 변이 64픽셀 이하인 이미지가 38개였다. 큰 예로 4,961×7,016 포스터와 7,257×4,082 썸네일이 있었다.','확장자가 .do·.es이거나 없어도 이미지 헤더로 포맷을 확인하였다.','<b>비전 모델에는 픽셀만 넣었다.</b> 기존 alt, 페이지 문맥, 정답 label은 입력하지 않았다.'])
body+='<h3>3-2. 원본을 보존하고, 입력 표현을 정리하였다</h3>'+table(['단계','실제로 한 처리','남긴 기록'],[['파일 확인','이미지 크기·포맷·프레임·hash를 확인하였다.','파일별 목록을 저장하였다.'],['방향·투명도','EXIF 방향을 적용하고, 기본 입력은 흰 배경에 합성하였다.','원본과 입력 정책을 구분하였다.'],['SVG 처리','직접 열기 실패 후 resvg로 변환하고 재실행하였다.','초기 실패와 보완 결과를 함께 남겼다.'],['모델 실행','각 모델의 자체 resize와 설정으로 추론하였다.','문장·OCR 원문·좌표·score·시간을 저장하였다.'],['추가 관찰','작은 입력은 확대하고, 밝은 투명 전경은 대비 배경을 사용하였다. 큰 입력은 타일을 추가하였다.','원본 좌표로 복원하고 처리 출처를 남겼다.'],['비교','기본 출력과 보완 출력을 대조하였다.','기본 결과를 보완 결과로 덮어쓰지 않았다.']])
body+='<h3>3-3. 전처리는 이런 차이를 만들었다</h3><div class="processing-example"><h4>예시 A. 16×16 숫자는 확대 후 읽혔다</h4><div class="before-after"><figure><div class="size-demo"><img src="assets/11cc05715bac383f.png" width="16" height="16" alt="원래 16×16 숫자"></div><figcaption>원래 크기: 16×16<br>기본 PP 출력: <code>·</code></figcaption></figure><figure><div class="size-demo"><img src="assets/11cc05715bac383f.png" width="128" height="128" alt="같은 숫자를 8배 크기로 표시한 예시"></div><figcaption>적용 배율: 8배 → 128×128<br>보완 PP 출력: <code>3</code></figcaption></figure></div>'+ul(['긴 변 512를 목표로 하되 최대 8배까지만 확대하였다. 따라서 이 입력은 512가 아니라 128픽셀이 되었다.','오른쪽 이미지는 확대 크기 설명을 위한 브라우저 표시이다. 실제 추론 입력 확대에는 Lanczos를 사용하였다.','작은 이미지를 확대해도 원본에 없는 글자 정보가 새로 생기지는 않는다.'])+'</div>'
body+='<div class="processing-example"><h4>예시 B. 흰 SVG는 배경을 바꾸어 다시 확인하였다</h4><div class="before-after"><figure><div class="svg-demo"><img src="assets/f59e7f64d7640153.png" alt="흰 배경에 합성해 전경이 보이지 않는 SVG"></div><figcaption>흰 배경 + 고유 크기 129×29</figcaption></figure><figure><div class="svg-demo"><img src="assets/f59e7f64d7640153_enhanced.png" alt="어두운 배경과 확대로 글자가 보이는 같은 SVG"></div><figcaption>어두운 배경 + 확대 입력</figcaption></figure></div>'+ul(['투명도와 전경 밝기로 배경 전환 여부를 결정하였다.','밝은 투명 전경은 흰 배경에서 사라질 수 있음을 확인하였다.','어두운 배경은 OCR용 보완 조건이다. 실제 웹사이트 배경색을 확인한 것은 아니다.'])+'</div>'
body+='<div class="processing-example"><h4>예시 C. 큰 포스터는 전체 이미지와 타일을 함께 처리하였다</h4>'+ul(['긴 변이 1,800픽셀을 넘으면 1,600픽셀 타일을 추가하였다. 타일 간 160픽셀을 겹쳤다.','타일 OCR 좌표를 원본 위치로 되돌린 뒤, 겹치는 문자열을 병합하였다.','Paddle 보완 42개에서는 총 85개 뷰를 처리하였다. 원시 999줄이 병합 후 877줄이 되었다.','<b>확인한 문제:</b> 줄 수는 늘어도 부분 문자열·중복·읽기 순서 때문에 제목과 날짜가 끊어질 수 있었다.','<b>수정 방향:</b> 전체뷰 결과를 유지하고 타일 결과는 별도 관찰로 전달해야 한다.'])+'</div>'
body+='<h3>3-4. 전체 299개와 자세히 볼 42개를 나누었다</h3>'+table(['비교 묶음','구성','용도'],[['전체 실행','299개','출력 생성·오류·시간·OCR 문자열을 확인하였다.'],['핵심 유형','사진·아이콘·로고·텍스트 배너·혼합·레이아웃 각각 6개 = 36개','caption 내용과 이미지가 맞는지 대조하였다.'],['난례','초소형·고해상도 6개','입력 크기와 전처리 문제를 추가 확인하였다.'],['OCR 문구 점검','문자 평가 대상 30개 중 판독 불가 1개 제외 → 29개 / 72문구','기관명·주제·날짜·전화번호가 출력에 남았는지 확인하였다.']])+ul(['42개는 유형과 난례를 보기 위한 목적 표집이었다. 전체 데이터의 무작위 대표 표본은 아니다.','72개 문구는 OCR 출력·alt·label을 보지 않은 다른 assistant가 이미지에서 선정하였다. 전문가가 전체 문서를 전사한 정답은 아니다.'])+'</section>'
body+='<section id="runs"><h2>4. 무엇을 몇 개에 실행하였는가</h2>'+table(['실행 항목','이미지 수','이 실험에서 확인할 것'],[['Patch-ioner 전역 CLS','299개','기존 단일 caption으로 한국어 웹 이미지를 설명할 수 있는가'],['EasyOCR + PP-OCRv5 한국어','각 299개','이미지 안의 실제 글자를 어느 정도 남기는가'],['Florence-2 상세 + dense 영역','42개','사진·도형·배치 설명이 더 구체적으로 나오는가'],['Patch Gaussian 집계 + 자동 영역','42개','패치를 모으는 범위를 바꾸면 설명이 달라지는가'],['EasyOCR 전처리 보완','85개','공통 42개 + 투명/SVG 진단 43개'],['PP-OCRv5 전처리 보완','42개','같은 진단 표본에서 확대·배경·타일이 도움 되는가']])
body+=ul(['추가 학습은 하지 않았다. 공개 가중치로 추론하였다.','Patch 영역은 Florence가 예측한 첫 3개 유효 box와 전체 프레임을 사용하였다. 논문의 정답 box 실험을 그대로 재현한 것은 아니다.','Paddle 전체 결과 299개 중 42개는 먼저 실행한 진단 표본 결과를 재사용하였다. 새 추론은 나머지 257개였다.','장비는 GTX 1660 6GB, Ryzen 7 3700X, RAM 약 32GiB였다. Paddle는 CPU, 나머지 모델은 GPU로 실행하였다.'])
body+='<details><summary>모델 설정과 시간·메모리 표 펼치기</summary>'+oldtables[3]+ul(['시간은 모델 로드를 제외한 한 번의 관측값이다. 일부 작업을 병행하여 통제된 속도 비교가 아니다.','GPU 수치는 PyTorch 최대 할당 텐서 메모리이다. PC 전체 VRAM 사용량이 아니다.','Florence 시간은 상세 설명과 dense 영역 두 작업의 합계이다.','<a href="reproducibility.html">정확한 버전·설정·재실행 방법</a>을 별도 기록하였다.'])+'</details></section>'
body+='<section id="findings"><h2>5. 확인해 보니 이렇게 나왔다</h2><h3>5-1. 한국어 문구는 OCR에서 더 직접적으로 확보되었다</h3>'+oldtables[4]+ul(['기본 PP-OCRv5는 선택한 72문구 중 57개, EasyOCR는 46개를 출력에 남겼다.','전처리 후 EasyOCR는 48개로 늘었지만 PP-OCRv5는 56개로 줄었다.','<b>따라서 확대·분할을 항상 켜는 것이 개선은 아니었다.</b> 입력 조건별 결과와 병합 실패를 확인해야 한다.','합집합 수치는 어느 한 엔진에 해당 문구가 있었는지를 뜻한다. 시스템이 정답을 자동 선택했다는 의미는 아니다.','<b>채점 방식:</b> 공백·문장부호를 제외하고 정규화한 문구가 출력 안에 연속해서 포함되는지 검사하였다.','이 수치는 선택 문구 포함 여부이다. OCR 전체 정확도, CER, 최종 대회 F1로 해석하지 않았다.'])
body+='<h3>5-2. 상세한 caption에도 지어낸 정보가 있었다</h3>'+oldtables[5]+ul(['사진·아이콘·로고 등 핵심 36개를 assistant가 직접 대조하였다.','Patch CLS는 표지판·버스·사람 등 익숙한 장면으로 잘못 설명하는 경우가 많았다.','Florence는 중심 대상을 더 자주 포착하였다. 그러나 보이지 않는 행동·목적과 잘못된 한글을 추가하였다.','Florence 상세 설명은 이 36개 중 19개에서 이미지와 다른 문자·문구를 생성한 것으로 점검하였다.','표의 ‘근거 없는 주장 포함’은 오류가 하나라도 있는 이미지 수이다. 문장별 hallucination 비율은 아니다.','중심 대상이 맞아도 세부 정보까지 모두 맞는 것은 아니다. 이 점검은 전문가 검증이 아니다.'])
body+='<h3>5-3. 패치 집계 범위를 바꾸어도 오류가 남았다</h3>'
region_rows=[]
for f,title in [('039c94d89a6db2c3','마이크를 든 인물'),('026769b1356f3283.png','국립중앙도서관 로고')]:
    r=byfile[f];reg=r['models']['patch_regions']['regions']
    region_rows.append([title,esc(r['models']['patch']['whole_image']),esc(reg[0]['caption']),esc(reg[-1]['caption'])])
body+=table(['같은 이미지','전역 CLS 출력','전체 프레임 패치 집계','자동 영역 출력 예시'],region_rows)+ul(['인물 사진은 와인잔에서 전화기로 설명이 바뀌었지만 마이크를 정확히 설명하지 못하였다.','로고에서는 따옴표가 반복되었고, 기관명을 읽지 못하였다.','집계 범위가 달라지면 출력은 달라졌다. 그러나 영역 집계가 한국어 OCR를 대신하지는 못하였다.','42개 영역 출력 전문은 <a href="gallery.html">예시 모아보기</a>에서 펼쳐 볼 수 있다.'])
body+='<h3>5-4. 데이터가 잘 처리되었다는 것과 설명이 맞다는 것은 달랐다</h3>'+ul(['최종 통합 결과에서는 기본 3개 구성요소가 각각 299개를 처리하였다. 빈 문자열 반환도 기술적 성공에 포함하였다.','실행이 끝났다는 이유로 한국어·숫자·객체 설명을 정답 처리하지 않았다.','원문과 오류를 그대로 남겨 다음 단계에서 다시 확인할 수 있게 하였다.'])+'</section>'
mainfiles=['039c94d89a6db2c3','7eb29474dd9cd8e3.jpg','1138e6cad536ac89.png','428f1b4c5969909c.png','026769b1356f3283.png','1b7d42dd2f95b6e1.jpg','7a9e3ca7407f9a30.jpg','046bf6ae3c5e646b.es','25198da01a56c796.png','658a87ad149352ab.jpg','11cc05715bac383f.png','58a031d1909dc03e.do']
body+='<section id="examples"><h2>6. 실제 이미지를 놓고 비교한 대표 사례 12개</h2>'+ul(['왼쪽에서 이미지를 보고, 오른쪽에서 확인 메모와 모델 원문을 함께 읽도록 구성하였다.','영어 원문은 모델 출력이다. 오류를 자연스러운 문장으로 고쳐 쓰지 않았다.','<a href="gallery.html"><b>유형별 진단 42개 + 투명 SVG 1개를 한 번에 보기 →</b></a>'])
body+=''.join(case(byfile[f],i) for i,f in enumerate(mainfiles,1))+'</section>'
body+='<section id="next"><h2>7. 지금 결과를 바탕으로 다음 구성을 제안하였다</h2><ol class="pipeline"><li><b>이미지 입력을 정리한다.</b><span>방향·투명도·SVG·크기를 확인하고 원본을 보존한다.</span></li><li><b>한국어 글자와 장면을 각각 추출한다.</b><span>PP-OCRv5 원문·좌표와 Florence 시각 설명 후보를 분리한다.</span></li><li><b>필요한 입력만 다시 관찰한다.</b><span>작은 글자·낮은 대비·긴 포스터에 확대·대비·타일을 비교한다.</span></li><li><b>출처와 충돌을 남긴다.</b><span>전체뷰와 보완뷰를 함께 저장하고, 어느 결과에서 나온 주장인지 표시한다.</span></li><li><b>메타데이터를 붙여 LLM으로 전달한다.</b><span>기존 alt·링크·주변 문맥을 추가하고 최종 품질 판정에 사용한다.</span></li></ol>'
body+=table(['이번에 만든 것','다음에 구현·검증할 것'],[['299개 이미지의 OCR·caption 후보와 문맥을 분리한 JSON','Gemma 12B-QAT의 최종 7범주 판정'],['정답 label·참조 문구·시각 점검 판정을 제외한 LLM 입력 묶음','OCR만 / caption만 / 둘 다 넣는 비교 실험'],['기본 결과·보완 결과·오류 기록','필요한 사례만 재관찰하는 자동 분기'],['실행 환경과 단일 이미지 재실행 진입점','문서 구조 모델·사실 확인 모듈 추가 비교']])
body+=ul(['<b>고유명사·날짜·숫자:</b> caption에서 추정하지 않고 OCR 원문과 box를 우선 증거로 사용한다.','<b>국적·신분·행사 목적:</b> caption이 말하더라도 픽셀 근거가 부족하면 미확인으로 남긴다.','<b>메타데이터:</b> 최종 판정에서 기존 alt·문맥은 사용할 수 있다. 정답 label과 라벨러 설명은 제외한다.','<b>Gemma:</b> 이 PC에서는 비전 결과 저장 → 비전 모델 해제 → LLM 순차 실행을 우선 검토한다. 아직 속도와 분류 성능을 측정하지 않았다.','<b>웹 확인:</b> 링크 목적·주변 설명처럼 부족한 문맥을 선택적으로 보완하는 용도로 제안한다. 대회에서 참가 시스템의 외부 인터넷 이용이 허용되는지는 별도 확인이 필요하다.'])+'</section>'
body+='<section id="files"><h2>8. 팀에서 바로 열어볼 자료</h2>'+table(['자료','무엇을 볼 수 있는가'],[[link('literature.html','논문 조사 노트'),'2026 후보 20개, 논문·GitHub·공개 상태·도입 판단'],[link('gallery.html','43개 예시 모아보기'),'진단 42개 + 투명 SVG, 유형별 이미지·출력·확인 메모'],[link('results.html','299개 원문·좌표 확인'),'검색, 모델별 OCR 원문, 좌표, 상세 설명, JSON'],[link('reproducibility.html','재실행·기록'),'모델 설정, 로그, 원시 파일, 한 장 다시 실행'],[link('data/evidence_packets.jsonl','299개 LLM 입력용 근거 묶음'),'시각 관찰·OCR·문맥·불확실성을 분리한 입력 후보']])+ul(['이번 수정은 공유 형식과 예시 구성을 바꾸었다. 기존 모델 출력·집계 수치는 변경하지 않았다.','최종 description의 정확도와 대회 점수는 아직 검증하지 않았다. 다음 단계에서는 동일 분할에서 구성요소별 효과를 비교해야 한다.'])+'</section>'
main=page('한국어 웹 이미지, 무엇을 조사하고 확인하였는가',body,'조사 → 샘플 정리 → 모델 실행 → 출력 대조 → 다음 구성 제안 · 2026.09.26')
(O/'report.html').write_text(main,encoding='utf-8')
(W/'report_template.html').write_text(main,encoding='utf-8')

gallery='<section><h2>예시를 보는 순서</h2>'+ul(['사진·아이콘·로고·텍스트 배너·혼합·레이아웃·난례 각 6개, 총 42개를 묶었다.','투명 SVG 입력 문제 1개를 마지막에 추가하였다. SVG는 42개 시각 점검 점수에 포함하지 않았다.','확인 메모는 기존 assistant 시각 점검을 옮겼다. 모델 원문, 오류, 미실행 범위를 그대로 남겼다.','이미지는 클릭해서 크게 볼 수 있다. OCR 전문과 문구별 포함 여부도 사례마다 확인할 수 있다.'])+'<nav class="group-nav">'+''.join(link('#group-'+g,n+' 6개') for g,n in groups.items())+link('#svg-extra','투명 SVG 1개')+'</nav></section>'
idx=0
for g,n in groups.items():
    gallery+='<section id="group-'+g+'"><h2>'+n+' · 6개</h2>'
    for r in rows:
        if r['stratum']!=g:continue
        idx+=1;gallery+=case(r,idx,True)
    gallery+='</section>'
svg=next(r for r in rows if r['file'].lower().endswith('.svg'))
gallery+='<section id="svg-extra"><h2>추가 1개. 투명 SVG를 어떻게 처리하였는가</h2><div class="before-after"><figure><div class="svg-demo"><img src="'+svg['asset']+'" alt="흰 배경 SVG 입력"></div><figcaption>기본 흰 배경 입력</figcaption></figure><figure><div class="svg-demo"><img src="'+svg['alternate_asset']+'" alt="어두운 배경으로 보완한 SVG 입력"></div><figcaption>어두운 배경·확대 입력</figcaption></figure></div>'+ul(['초기 직접 로딩 오류 후 SVG를 렌더링하고 다시 실행하였다.','밝은 전경이 흰 배경에 묻히는 현상을 별도 확인하였다.','아래는 실제 EasyOCR 결과이다. 이 사례에 PP-OCRv5 보완과 Florence는 실행하지 않았다.'])
gallery+=table(['조건','실제 반환 문자열'],[['EasyOCR 기본',esc(ocr_text(svg,'easy'))],['EasyOCR 보완',esc(ocr_text(svg,'enhanced'))],['PP-OCRv5 기본',esc(ocr_text(svg,'paddle'))]])+link('results.html#'+quote(svg['file']),'이 SVG의 전체 결과·좌표 보기 →')+'</section>'
(O/'gallery.html').write_text(page('샘플 43개로 확인한 실제 출력',gallery,'진단 표본 42개 + 투명 SVG 추가 1개 · 원문·이미지·확인 메모를 함께 표시함'),encoding='utf-8')

# Keep the complete interactive viewer, aligning only its navigation and introductory copy.
for p in [W/'results_template.html',O/'results.html']:
    s=p.read_text(encoding='utf-8')
    s=s.replace('종합·실측 보고서','조사·실험 진행 정리').replace('상세 문헌 조사','논문 조사 노트').replace('재현·실행 기록','재실행·기록')
    if 'href="gallery.html"' not in s:s=s.replace('<a href="reproducibility.html">','<a href="gallery.html">43개 예시 모아보기</a><a href="reproducibility.html">')
    s=s.replace('<div class="eyebrow">Experimental Evidence · 299 Samples</div>','<div class="eyebrow">0923 PROJECT / SAMPLE OUTPUTS</div>')
    p.write_text(s,encoding='utf-8')

# Reformat the reproducibility notes without modifying any paths, settings or logs.
s=(W/'before_team_reproducibility.html').read_text(encoding='utf-8')
s=s.replace('Methods Appendix · Reproducibility','0923 PROJECT / RUN NOTES').replace('실험 기록 및 재현 방법','같은 샘플을 다시 실행하는 방법').replace('종합·실측 보고서','조사·실험 진행 정리').replace('상세 문헌 조사','논문 조사 노트').replace('href="report.css?v=20260926b"','href="team-notes.css?v=3"')
def to_bullets(m):
    attrs,text=m.groups()
    if 'class="meta"' in attrs:return m.group(0)
    # Sentence boundaries exclude decimal numbers, URLs and dot-containing filenames.
    parts=re.split(r'(?<=[다요오])\.\s+(?=[가-힣A-Z0-9<])',text)
    if len(parts)<2:return '<ul class="facts"><li>'+text+'</li></ul>'
    return '<ul class="facts">'+''.join('<li>'+v.rstrip('.')+'.</li>' for v in parts)+'</ul>'
s=re.sub(r'<p([^>]*)>(.*?)</p>',to_bullets,s,flags=re.S)
(O/'reproducibility.html').write_text(s,encoding='utf-8')
print(json.dumps({'main_examples':len(mainfiles),'gallery_audited_examples':idx,'svg_extra':1,'unchanged_sample_rows':len(rows),'html_written':['report.html','gallery.html','reproducibility.html','results.html']},ensure_ascii=False))
