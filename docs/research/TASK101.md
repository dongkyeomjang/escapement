# TASK101 — context 비용 시뮬레이터 blind cell N = 15·18 선등록

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 11 작업 B의 선등록. context 비용(TASK97·100)과 운영 prefill(TASK92)로 시간을 진행하는 통합 시뮬레이터를 새 N = 15·18 cell에서 blind로 검증하기 위해 plan·예측·영 예측기·기준·순서·판정 스크립트를 측정 전에 commit한다. 문서 [CTXBLIND_PREREG.md](CTXBLIND_PREREG.md). 측정·판정은 다음 TASK.

**측정 0.**

## 배경

- [결정 12](INDEX.md#결정-12--지시문-11-결정-context-비용-채택과-blind-검증) — context 비용 형태 채택, blind 검증
- [TASK97](TASK97.md)·[TASK100](TASK100.md) — context 비용, [TASK92](TASK92.md) — 운영 prefill
- [TASK93](TASK93.md)·[TASK95](TASK95.md) — 같은 절차의 이전 blind cell, 운영 비용 대 원래 비용 FAIL
- [TASK98](TASK98.md) — 사후 재예측(주 예측기 선택에 일부 참고, 명시)

## 시작 상태

- HEAD `f91b8e2`, TASK100 측정 종료 후

## 수행 내용

1. `CTXCOST_BLIND.json`(`make_ctxcost_sim.py`, BATCHONLY는 TASK100 실측 F1 — 규칙 추정 없음).
2. plan N = 15·18(seed 20261550–54, 20261580–84, `INDEX_CTX.json`).
3. 예측 `predict_ctxblind.py`: (1) `sim_ctx_op`(주), (2) `sim`, (3) `v1`, 보고만 `sim_ctx`. **주 예측기는 사전에 정한 조합이며 근거는 선등록 §3.1**(사후 결과에 기댄 부분 명시).
4. **N = 18 BASE 점검**: 주 예측기 예측 재사용 0.045 ≥ 0.03 → 대안 N 제안 없이 진행. 예측기 (2)는 0.026임을 기록.
5. 영 예측기(N15 = Table I 12·16 합산, N18 = 16), 순서(seed 20261596), 구동 `run_ctxblind.sh`, `mt_check.py` index에 `INDEX_CTX.json`, 판정 `ctxblind_analyze.py`(가짜 run으로 코드 경로만 시험).

## 변경된 파일

- `experiments/npu/stage3/{make_ctxblind_plans.py, predict_ctxblind.py, null_predictors_ctx.py, make_ctxblind_order.py, run_ctxblind.sh, ctxblind_analyze.py}`(신규), `mt_check.py`
- `experiments/npu/stage3/plans/main/`: `main-n{15,18}-r{0..4}.json`, `INDEX_CTX.json`, `PREDICTIONS_CTX.json`, `NULL_PREDICTORS_CTX.json`, `ORDER_CTX.json`, `CTXCOST_BLIND.json`
- `docs/research/CTXBLIND_PREREG.md`, `docs/research/TASK101.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
S=experiments/npu/stage3
env -u PYTHONPATH python3 $S/make_ctxcost_sim.py --source results/npu/stage3/ctxcost/ctxcost_v2.json --output $S/plans/main/CTXCOST_BLIND.json
env -u PYTHONPATH python3 $S/make_ctxblind_plans.py
cd $S && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 predict_ctxblind.py --output /home/rebel/continuum-npu/results/npu/stage3/predict/ctxblind_predictions.json && cd -
cp results/npu/stage3/predict/ctxblind_predictions.json $S/plans/main/PREDICTIONS_CTX.json
env -u PYTHONPATH python3 $S/null_predictors_ctx.py --output $S/plans/main/NULL_PREDICTORS_CTX.json
env -u PYTHONPATH python3 $S/make_ctxblind_order.py
# 측정 (다음 TASK)
bash /home/rebel/continuum-npu/experiments/npu/stage3/run_ctxblind.sh /home/rebel/continuum-npu/results/npu/stage3/20261002-ctxblind
```

## 결과

예측 표는 [CTXBLIND_PREREG.md](CTXBLIND_PREREG.md) §3.2. 요약: BASE 재사용 (1)/(2) N15 0.110/0.156, N18 0.045/0.026; batch 16 재사용 0.73–0.80; 비 (1) N15 0.749·0.730, N18 0.701·0.680 ((2)보다 0.015–0.029 낮음).

## 핵심 발견

1. (1)과 (2)의 차이가 TASK95(운영 비용 대 원래 비용, 비 차 ≤ 0.013)보다 크다 — 비 차 0.015–0.029, N15 BASE 재사용 차 0.046. decode의 context 항 때문이다.

## 해석

- 사전 예측(기준 아님): §5.1 PASS 쪽, §5.2 (1) 경계 PASS 쪽 / (2) FAIL 쪽, §5.3 PASS, §5.6 PASS 쪽, (1) 대 (2) PASS 쪽이나 확신 낮음(TASK95 이력).

## 확인되지 않은 사항

- 없음(측정 전).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 측정(30 lifecycle, 측정 중 다른 작업 없음)과 일괄 판정 — 다음 TASK.

## 재현 정보

- 선등록 commit: 이 TASK의 commit(측정 시작 전). 측정 시작 시각은 다음 TASK에 기록.
- 고정 파일 SHA256은 [CTXBLIND_PREREG.md](CTXBLIND_PREREG.md) §7.
