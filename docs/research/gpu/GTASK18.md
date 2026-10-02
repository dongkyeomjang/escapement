# GTASK18 — context 길이 step 비용 측정

## 상태

IN_PROGRESS

## 날짜

2026-10-02

## 목적

GPU 지시문 G-07 작업 B. FULL decode step 비용을 decode 폭 n × 요청당 context 길이 L에서 재서, GTASK15 운영 초과가 context 길이에서 오는지 본다. **파라미터 측정, 판정 없음.**

## 수행 내용

1. G-07 작업 A: `git merge origin/main` → merge commit `5f69657`(충돌 없음, TASK88–96 반영). TASK91·92·95를 읽었다.
2. 통제 부하의 context 길이를 기록에서 확인하고, 설계 [GPU_STEPCOST_CTX_PREREG.md](GPU_STEPCOST_CTX_PREREG.md)와 측정·분석 코드를 측정 전에 commit했다.
3. (진행 중) `run_stepcost_ctx.sh`를 세션과 분리해 실행한다. driver가 요약 두 파일을 자동 local commit한다.

## 재개 방법

- run dir: `results/gpu/stepcost_ctx/<시작 UTC>/`, 진행은 `sequence.log`, commit 결과는 `commit.log`
- 자동 commit 대상: `experiments/gpu/stepcost/ctx_result/`
- 결과 해석과 이 문서 완성 뒤 작업 C(붕괴 영역 blind 선등록)
