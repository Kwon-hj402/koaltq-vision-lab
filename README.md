# KoAltQ Vision Lab

**[보고서와 전체 실험 결과 열기](https://kwon-hj402.github.io/koaltq-vision-lab/)**

한국어 웹 이미지에서 그림 설명과 글자를 어떻게 추출할지 조사하고, 대회 샘플에 실제 모델을 적용한 기록입니다. 팀원이 조사 이유 → 코드 구성 → 실행 결과 → 실패 사례를 따라갈 수 있도록 정리했습니다.

## 먼저 볼 자료

- [진행 설명](https://kwon-hj402.github.io/koaltq-vision-lab/report.html): 무엇을 조사했고, 어떻게 연결하고 돌렸는가.
- [43개 예시](https://kwon-hj402.github.io/koaltq-vision-lab/gallery.html): 이미지·모델 원문·OCR·오류 메모 비교.
- [299개 결과 검색](https://kwon-hj402.github.io/koaltq-vision-lab/results.html): 개별 이미지, OCR 좌표, 설명, 메타데이터.
- [코드 설명](https://kwon-hj402.github.io/koaltq-vision-lab/code.html) / [실행 가이드](docs/RUNNING.md) / [데이터 안내](https://kwon-hj402.github.io/koaltq-vision-lab/data-guide.html).
- [논문 조사](https://kwon-hj402.github.io/koaltq-vision-lab/literature.html): 후보별 논문·공식 코드·적합성·공개 상태.

## 이번에 실행한 범위

| 실험 | 이미지 수 | 목적 |
|---|---:|---|
| Patch-ioner / EasyOCR / PP-OCRv5 한국어 | 각 299 | 전역 설명과 OCR 비교 |
| Florence-2 / 패치 영역 설명 | 각 42 | 상세 설명과 영역별 설명 진단 |
| EasyOCR / PP-OCRv5 조건부 전처리 | 85 / 42 | 확대·투명 배경·타일링 비교 |

- 29개 이미지의 선택 문구 72개 중 기본 EasyOCR 46개, 기본 PP-OCRv5 57개를 회수했습니다.
- 이 수치는 assistant가 선정·전사한 문구의 소규모 진단입니다. 전체 OCR 정확도나 최종 대회 F1이 아닙니다.
- Florence 설명과 한국어 OCR를 별도 근거로 추출하는 단일 이미지 CLI를 제공합니다. 추가 학습은 없습니다.
- Gemma의 최종 alt 판정·생성, 웹 검증 에이전트, 최종 대회 성능은 아직 구현·평가하지 않았습니다.

## 모델 없이 결과부터 확인하기

Python 3에서 저장소 루트 기준으로 실행합니다. 아래 명령에는 외부 패키지가 필요하지 않습니다.

```sh
python scripts/score_saved.py
python scripts/validate_site.py
python -m http.server 8000
```

브라우저에서 `http://127.0.0.1:8000/`을 엽니다. `score_saved.py`는 원시 OCR 결과로 핵심문구 지표를 다시 계산하고 저장된 지표와 일치하는지 확인합니다. 원본 결과를 덮어쓰지 않습니다.

모델을 실제 실행하려면 [환경 설치 및 한 장 실행 가이드](docs/RUNNING.md)를 따릅니다. GitHub Pages는 저장된 결과를 보여주는 정적 사이트이며 서버에서 모델을 실행하지 않습니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `src/` | Florence·Paddle 별도 Python 환경을 호출하는 현재 CLI |
| `requirements/` | 모델별 의존성 목록 |
| `scripts/` | 저장 결과 재집계·HTML 데이터 갱신·내부 링크 검사 |
| `dataset/` | 제공받은 원본 299개 이미지, 레코드, 출처 매핑 |
| `assets/` | 보고서에서 보기 위한 정규화 PNG와 SVG 배경 비교 |
| `data/` | 모델 원시 출력, 통합 결과, 평가 근거, 실행 메타데이터 |
| `experiments/` | 당시 실험 및 보고서 제작 코드의 보존 스냅샷 |
| `retest_20260926_205941/` | 기존 4모델 한 장 재실행 결과 |
| `docs/` | 실행·보고서 수정 안내 |

스냅샷에는 당시 폴더 구조 의존성이 있습니다. 팀원 PC에서 실행할 진입점은 `src/describe_image.py`입니다. 공개본에서는 개인 PC 경로를 치환했고, 모델 출력과 수치는 유지했습니다. 모델 가중치·가상환경은 포함하지 않았습니다.

보고서 수정은 [REPORT_EDITING.md](docs/REPORT_EDITING.md)를 참고하세요. 출처와 이미지·제3자 모델의 권리 범위는 [NOTICE.md](NOTICE.md)에 구분했습니다.
