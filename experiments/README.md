# 당시 실험 코드의 기록

`snapshots/`는 2026-09-26 로컬에서 사용한 실험 코드, `report_builders/`는 HTML/JSON 생성과 후속 설명 개편 코드이다.

원래 작업공간의 `work/` 구조, 별도 가상환경, 캐시와 Patch-ioner 어댑터에 의존한다. 개인 경로는 `${ORIGINAL_WORKSPACE}`, `${PATCHIONER_SOURCE}`, `${PATCHIONER_RUNTIME}` 등으로 치환하였다. 이 폴더를 그대로 실행하는 완전한 재현 패키지가 아니다.

현재 Florence + PP-OCRv5 단일 이미지 실행은 `src/`, 설치·실행 설명은 `docs/RUNNING.md`를 사용한다. 이미 저장된 결과의 수치 확인은 `scripts/score_saved.py`로 모델 없이 가능하다.
