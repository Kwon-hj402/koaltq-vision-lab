# 출처와 권리 안내

## 샘플 데이터
KoAltQ 대회 제공 샘플 299쌍을 이용하였다. 공식 문제: https://aida.kisti.re.kr/competition/main/problem/PROB_000000000004610/detail.do

원본 제공 설명은 `dataset/README.source.md`에 보존하였다. 이 설명에 따르면 라벨·메타데이터는 CC BY이며, 이미지는 공공누리 표시 페이지를 우선 수집하고 `kogl_marker`로 구분하였다. 버전 번호가 없는 CC BY 설명을 이 저장소가 임의로 특정 버전으로 바꾸지는 않았다.

이미지의 권리는 원 출처에 있다. 모든 이미지를 동일한 자유 이용 라이선스로 재허가하지 않는다. 파일별 출처는 `dataset/image_sources.json`의 원문 이미지·페이지 URL을 확인한다. 보고서의 `assets/`는 원본을 표시용으로 변환한 이미지이다.

## 모델과 라이브러리
모델 가중치를 포함하지 않는다. Patch-ioner, Microsoft Florence-2, PaddleOCR, EasyOCR는 각각 공식 저장소·모델 배포 페이지의 이용 조건을 따른다. 논문과 공식 링크는 `literature.html`에 수록하였다.

## 이 저장소의 실험·설명
모델이 생성한 설명과 OCR에는 오류가 있다. assistant가 작성한 시각 점검은 전문가 정답 데이터가 아니다. 저장소 전체에 하나의 라이선스를 적용해 원본 이미지·외부 모델·실험 결과의 권리를 혼동하지 않도록 하였다.
