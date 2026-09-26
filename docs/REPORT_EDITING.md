# 보고서 수정 방법

- 현재 HTML이 배포 기준본이다. `report.html`은 진행 설명, `gallery.html`은 43개 예시, `literature.html`은 논문 조사이다.
- `team-notes.css`는 설명 문서, `report.css`는 결과 탐색 화면의 스타일이다.
- `data/sample_results.json`을 변경했다면 `python scripts/build_results.py`로 `results.html` 안의 데이터를 갱신한다. 이 명령은 모델을 실행하지 않는다.
- 보고서의 수치·정성 해석과 gallery의 고정 예시는 자동 변경되지 않는다. 실험 결과를 바꾸면 관련 본문도 확인하여 수정한다.
- `python scripts/validate_site.py`로 내부 링크와 샘플 수를 확인한다.
- 로컬 열람: 저장소 루트에서 `python -m http.server 8000` 실행 후 `http://127.0.0.1:8000/`을 연다.
- Pages는 `main` 브랜치 루트에서 배포한다. 정적 파일이므로 Python 모델 추론을 웹 서버에서 실행하지 않는다.
