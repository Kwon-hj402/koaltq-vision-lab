# 단일 이미지 실행 안내

`src/describe_image.py`는 이미지 한 장을 받아 **Florence-2-base의 전체 상세 설명**과 **PP-OCRv5 한국어 OCR 근거**를 별도로 추출한다. 모델의 추가 학습은 없다. 기존 alt, 정답 라벨, 페이지 메타데이터는 읽지 않는다. **최종 LLM 판정·대체텍스트 생성·웹 검색 에이전트는 구현하지 않았다.**

이 CLI는 재현 범위를 작게 유지한 전체 이미지 baseline이다. 보고서의 확대·대비 배경·타일 OCR 실험을 재현하는 실행기는 아니다. `<MORE_DETAILED_CAPTION>`만 실행하며 dense region caption은 실행하지 않는다.

## 환경 두 개를 따로 지정한다

실행 조정기는 Python 표준 라이브러리만 사용한다. Paddle 작업을 마치고 별도 프로세스에서 Florence 작업을 실행하므로 두 프레임워크를 한 환경에 섞지 않아도 된다.

| 구성 | 로컬에서 확인한 환경 | CLI 기본값 |
|---|---|---|
| Python | Windows, Python 3.11.9 | 실행한 Python |
| Florence | PyTorch 2.4.1+cu121, transformers 4.46.3, CUDA float16 | CPU float32 |
| OCR | paddlepaddle 3.2.2, paddleocr 3.3.2, CPU 4 threads | CPU 4 threads |
| 비전 모델 | `microsoft/Florence-2-base`, 0.23B pretrained | 동일한 공개 모델 ID |
| OCR 검출 | `PP-OCRv5_mobile_det` | 명시적으로 고정 |
| OCR 인식 | `korean_PP-OCRv5_mobile_rec` | 명시적으로 고정 |

`requirements/observed-versions.json`과 두 requirements 파일은 기존 실행 환경에서 확인한 버전을 기록한다. **빈 환경에서 설치·의존성 해석을 검증한 lockfile은 아니다.** CPU용 Florence와 GPU용 Paddle 경로도 CLI에서 선택할 수 있지만 이번 휴대형 CLI 검증은 **Florence CUDA + Paddle CPU** 구성이다.

새 환경을 만들 때의 출발점은 다음과 같다. 프로젝트 루트에서 실행한다. 기존 연구 환경에 바로 설치하지 말고 별도 환경을 사용한다.

```powershell
py -3.11 -m venv .venv-florence
py -3.11 -m venv .venv-paddle

# NVIDIA CUDA 12.1용으로 로컬에서 사용한 PyTorch 빌드를 먼저 선택하는 예
.\.venv-florence\Scripts\python.exe -m pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121
.\.venv-florence\Scripts\python.exe -m pip install -r requirements/florence.txt
.\.venv-paddle\Scripts\python.exe -m pip install -r requirements/paddle-cpu.txt
```

CUDA wheel과 드라이버는 실행 PC에 맞춰야 한다. CPU 전용 Florence 환경이라면 PyTorch의 CPU wheel을 선택하고 `--caption-device cpu`를 사용한다. `--ocr-device gpu:0`은 별도의 GPU Paddle 환경이 필요하며, 제공한 `paddle-cpu.txt`는 GPU 환경 설치 안내가 아니다. 본 저장소는 GPU Paddle 설치를 검증하지 않았다.

## 첫 실행: 공식 모델 내려받기 허용

다음 예시의 입력 파일과 Python 경로를 자신의 PC에 맞게 바꾼다. 모델 가중치는 저장소에 포함하지 않는다.

```powershell
python src/describe_image.py "sample.png" `
  --output "runs/sample" `
  --florence-python ".venv-florence/Scripts/python.exe" `
  --paddle-python ".venv-paddle/Scripts/python.exe" `
  --florence-model "microsoft/Florence-2-base" `
  --hf-cache "models/huggingface" `
  --paddle-cache "models/paddlex" `
  --caption-device cuda `
  --ocr-device cpu
```

Florence 구현은 공식 모델의 `trust_remote_code=True` 경로를 사용한다. 첫 다운로드 시 해당 모델 저장소의 Python 코드를 불러와 실행한다. 기존 코드와 가중치를 보유한 경우 아래 오프라인 경로를 쓸 수 있다. 공개 모델 ID의 최신 파일이 향후 바뀔 수 있으므로 엄밀한 재현에서는 다운로드한 파일과 버전을 별도로 보존한다.

## 기존 캐시·로컬 모델로 오프라인 실행

```powershell
python src/describe_image.py "sample.png" `
  --output "runs/sample-offline" `
  --florence-python "C:/path/to/florence-env/Scripts/python.exe" `
  --paddle-python "C:/path/to/paddle-env/Scripts/python.exe" `
  --florence-model "C:/path/to/models/florence2" `
  --hf-cache "C:/path/to/models/huggingface" `
  --paddle-cache "C:/path/to/models/paddlex" `
  --caption-device cuda `
  --ocr-device cpu `
  --offline
```

Florence 로컬 폴더에는 가중치뿐 아니라 config, processor, tokenizer와 모델 Python 구현 파일도 필요하다. Hugging Face 캐시가 이미 채워져 있다면 공개 모델 ID를 그대로 사용하면서 `--offline`을 지정할 수도 있다.

Paddle 캐시의 형태는 다음과 같다.

```text
models/paddlex/
└── official_models/
    ├── PP-OCRv5_mobile_det/
    │   └── inference.yml, inference.json, inference.pdiparams, ...
    └── korean_PP-OCRv5_mobile_rec/
        └── inference.yml, inference.json, inference.pdiparams, ...
```

캐시 구조와 다른 곳에 모델을 보관했다면 `--paddle-det-model-dir`와 `--paddle-rec-model-dir`로 각 export 폴더를 직접 지정한다. `--offline`에서는 두 폴더를 확인한 뒤 명시적인 local model directory로 넘기며, 없으면 오류를 기록한다. OCR 버전의 기본 언어 모델로 조용히 대체하지 않는다.

`einops`처럼 별도 모듈 디렉터리를 기존 환경과 함께 사용하는 경우 `--extra-module-path "C:/path/to/extra-modules"`를 추가한다. 이 옵션은 Florence worker에만 적용되며 여러 번 지정할 수 있다. Paddle 쪽에 별도 경로가 필요하면 `--paddle-extra-module-path`를 사용한다. 정상 설치한 새 환경에는 필요하지 않다.

macOS/Linux에서는 Python 실행 파일을 각 가상환경의 `bin/python` 경로로 바꾸고 셸에 맞게 줄바꿈한다. 해당 OS의 새 설치나 실행은 이번 검증 범위에 포함하지 않는다.

## 출력 확인

| 파일 | 내용 |
|---|---|
| `result.html` | 흰 배경의 정적 결과 페이지. 이미지, 설명, OCR 원문·점수·좌표를 나란히 검토 |
| `evidence.json` | 두 모델의 별도 결과, 입력 파일 SHA-256, 설정, 버전, 시간, 구현 범위 |
| `caption.json` | 설명 원시 토큰 문자열, 파싱 결과, 최종 원출력 설명 |
| `ocr.json` | OCR 원문, 폴리곤 `[x,y]`, 인식 점수, 전체 Paddle 원출력 |
| `input.png` | 첫 프레임·EXIF 보정·흰 배경 합성한 검토용 이미지 |
| `caption.log`, `ocr.log` | 모델별 로그. 실패도 그대로 보존 |

각 OCR 폴리곤은 **EXIF 보정 후 원본 크기 이미지의 좌표**다. OCR 자체의 내부 리사이즈는 사용할 수 있지만 외부 확대·타일 처리는 하지 않는다. OCR 반환 순서를 보존하며 문서 읽기 순서를 재구성했다고 보장하지 않는다. 모델 점수는 정답 확률로 해석하면 안 된다.

두 모델이 모두 성공하면 exit code는 `0`, 하나라도 실패하면 `1`이다. 한쪽이 실패해도 다른 작업을 시도하고 `evidence.json`과 `result.html`에 성공·실패를 구분해 저장한다. 출력 폴더가 이미 차 있으면 실행을 중단한다. 덮어쓸 때만 `--overwrite`를 사용하며, 이 경우 이 실행기가 만드는 이름의 파일들만 교체한다.

## 실제 실행 확인: 2026-09-26

기존 Windows Python 3.11.9 환경 두 개에서 로컬 Florence 가중치와 Paddle export 폴더를 명시해 `--offline`으로 한 장을 실행했다. 입력은 `3fd77908165a4ba9.jpg`, 임산부·영유아 비대면 건강 교실 안내 이미지다. 추가 설치나 새 학습 없이 두 worker가 성공했고, 출력 JSON·HTML·PNG·로그를 확인했다.

| 측정 항목 | 이번 한 장의 결과 |
|---|---:|
| Paddle 모델 로딩 | 1.86초 |
| Paddle 추론 | 9.54초 |
| OCR 인식 라인 | 25개 |
| Florence 모델 로딩 | 1.40초 |
| Florence 상세 설명 생성 | 4.44초 |
| Florence 최대 GPU tensor allocation | 618.1 MiB |

OCR 첫 줄은 `2026년 3분기 임산부·영유아 비대면 건강 교실 운영`으로 추출됐다. 그러나 Florence는 실제 포스터를 웹페이지로 해석하고, 선택 메뉴 세 개나 하단 링크가 있다는 설명을 생성했다. 이미지에서 그 기능을 확인할 수 없으므로 **설명 생성 성공이 사실 정확성을 보장하지 않는다.** 이 CLI는 해당 설명을 교정하거나 OCR과 결합해 최종 정답으로 판정하지 않는다.

이 수치는 한 PC의 단일 실행 관찰값이며 독립 성능 벤치마크가 아니다. JSON 구조, OCR ID 연속성, 출력 파일 간 링크 존재는 확인했다. `file://` 브라우저 열기는 보안 정책으로 차단되어 로컬 브라우저 시각 검증은 하지 않았다. 새 환경의 clean install, 다른 OS, 다른 GPU 구성은 검증하지 않았다.

## 알고 있는 한계

- Florence 설명에는 누락·환각이 있을 수 있다. 한국어 문자 인식은 별도 OCR 근거로 제공하며, Florence 설명이 OCR과 일치하는지 자동 검증하지 않는다.
- 투명 배경은 흰색으로 합성한다. 흰색 글자 로고, 극소 문자, 긴 포스터는 baseline에서 실패할 수 있다. 보고서의 별도 전처리 실험과 혼동하지 않는다.
- GIF 등 다중 프레임은 첫 프레임만 쓴다. 입력은 Pillow가 읽을 수 있는 로컬 raster 이미지이며 SVG·PDF·웹 페이지 자동 렌더링은 제공하지 않는다.
- 언어 번역, 사용자에게 필요한 정보 선정, 링크·버튼 기능 판단, 최종 alt 작성은 구현하지 않았다. `final_alt`는 `null`, `final_llm_judgement_implemented`는 `false`다.
- 실행 시간에는 모델 로딩과 프로세스 실행 시간을 구분해 기록하지만, 일반적인 성능 보증이나 고정 벤치마크 수치로 해석하지 않는다.

## 모델·코드 출처

- [Florence-2-base 공식 모델](https://huggingface.co/microsoft/Florence-2-base) — MIT, CVPR 2024 계열. 2026 엄격 선별 후보가 아니라 실용 비교 구성이다.
- [PaddleOCR 공식 코드](https://github.com/PaddlePaddle/PaddleOCR) — Apache-2.0.
- [한국어 PP-OCRv5 mobile 인식 모델](https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec) — Apache-2.0.

프로젝트 코드의 라이선스와 각 모델의 라이선스는 별도로 확인한다. 이 CLI가 타사 모델의 권리나 라이선스를 변경하지 않는다.
