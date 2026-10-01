# GTASK17 — 운영 조건 step 비용 재측정 (요인 분해)

## 상태

IN_PROGRESS

## 날짜

2026-10-01

## 목적

GPU 지시문 G-06 작업 A. FULL decode step 비용을 streaming × KV events × admission log 2³ 조건에서 다시 재서, GTASK15의 운영 초과(약 22 %, 요청당 약 0.35 ms)의 출처와 관찰자 효과 여부를 가린다.

## 수행 내용

1. 설계 [GPU_STEPCOST_OP_PREREG.md](GPU_STEPCOST_OP_PREREG.md)와 측정·분석 코드를 측정 전에 commit했다.
2. (진행 중) `run_stepcost_op.sh`를 세션과 분리해 실행한다. 끝나면 driver가 기계 생성 요약만 자동으로 local commit한다.

## 재개 방법

- run dir: `results/gpu/stepcost_op/<시작 UTC>/`, 진행은 `sequence.log`
- 자동 commit 대상: `experiments/gpu/stepcost/op_result/`
- 해석과 이 문서 완성, 그리고 GTASK18(blind cell 예측 선등록)은 다음 세션에서 한다.
