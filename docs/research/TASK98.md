# TASK98 — [사후 분석] context 길이 비용으로 TASK87·95 cell 재예측 (post_hoc)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 10 작업 B. **사후 분석이다 — 관측을 이미 본 cell이므로 판정하지 않고 결과 색인에 `post_hoc`으로 넣는다.** [TASK97](TASK97.md)의 context 길이 decode 비용으로 통합 시뮬레이터의 시간을 진행해 TASK87(N = 14·16)·TASK95(N = 13·17·20) cell과 TASK90 발견 4의 N = 12(TASK82) cell을 다시 예측하고, 기존 예측(원래 비용, 운영 비용)과 오차를 비교한다.

**측정 0.**

## 배경

- [TASK97](TASK97.md) — F1 `t = f(b) + βn + c·ΣL`
- [TASK90](TASK90.md) 발견 4 — sim 비 편향(batch 16, N = 12·14·16, 6 cell Σ 0.262), [TASK91](TASK91.md) 시간 척도로 48.5 % 설명(개발 집합 비율 사용)
- [TASK95](TASK95.md) — blind 판정(이 TASK는 판정을 바꾸지 않는다)

## 시작 상태

- HEAD `dfd908d`(TASK97 설계), TASK97 측정 종료 후

## 수행 내용

1. **시뮬레이터에 선택 hook 추가**(`SimConfig.decode_cost_fn`, 기본 `None` = 기존 동작): `(bucket, running, ΣL) → s`. ΣL = running 요청마다 prompt + 생성된 token. **회귀: TASK93 `PREDICTIONS_SIM.json`을 다시 계산해 byte 동일**(`cmp` 일치). paged 엔진(GPU)은 읽지 않는다.
2. `make_ctxcost_sim.py` → `CTXCOST_SIM.json`(재예측 실행 전 동결): BASE·TUNED는 자기 F1. **BATCHONLY는 측정하지 않아 규칙으로 정함**: f(b)는 b ∈ {1, 4, 8, 16} TUNED, b = 2 BASE, β·c는 두 적합의 평균.
3. `posthoc_ctx_predict.py`: 변형 4개 × N ∈ {12, 13, 14, 16, 17, 20} × 3 구성 × 5 plan. 시간 진행만 바꾸고 turn당 A′ 가격은 원래 비용(관측 A′와 같은 정의).
   - `sim` 원래 비용, `sim_op` TASK92 운영 비용, **`sim_ctx`** decode = context 비용 + prefill 원래, **`sim_ctx_op`** decode = context 비용 + prefill TASK92 운영.
4. 검증: `sim`의 발견 4 Σ 0.2620이 TASK90·91의 0.262를 재현, TASK95 cell의 `sim`·`sim_op`가 TASK93 예측과 같은 값(Σ 0.1017·0.1086, 재사용 MAE 0.0132·0.0161).

## 변경된 파일

- `src/continuum/sim/engine.py`(`decode_cost_fn` hook, 기본 동작 불변)
- `experiments/npu/stage3/{make_ctxcost_sim.py, posthoc_ctx_predict.py}`(신규), `plans/main/CTXCOST_SIM.json`
- `docs/research/TASK98.md`(신규), `docs/research/INDEX.md`, `paper/RESULTS_INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/make_ctxcost_sim.py --source results/npu/stage3/ctxcost/ctxcost.json
cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 posthoc_ctx_predict.py \
    --output /home/rebel/continuum-npu/results/npu/stage3/posthoc_ctx/posthoc_ctx.json
```

Population: 18 cell × 5 plan, 시뮬레이션 평가 구간 120 s. 관측은 TASK82 `main_verdict.json`, TASK87 `hiload_verdict.json`, TASK95 `simblind_verdict.json`(오차 계산에만).

## 결과 (전부 post_hoc)

### 요약 (비 = batch 16 구성의 BASE 대비 비)

| 집합 | 지표 | sim | sim_op | **sim_ctx** | **sim_ctx_op** |
|---|---|---|---|---|---|
| 발견 4 (N12·14·16, 6 cell) | 비 Σ\|오차\| | 0.262 | 0.185 | **0.174** | **0.111** |
| | 비 평균 부호 오차 | +0.044 | +0.031 | +0.029 | +0.018 |
| | 재사용 MAE (9 cell) | 0.0124 | 0.0046 | 0.0064 | 0.0064 |
| TASK87 (N14·16, 4 cell) | 비 Σ\|오차\| | 0.189 | 0.132 | 0.109 | 0.081 |
| | 재사용 MAE (6 cell) | 0.0128 | 0.0041 | 0.0068 | 0.0062 |
| TASK95 (N13·17·20, 6 cell) | 비 Σ\|오차\| | 0.102 | 0.109 | **0.041** | 0.060 |
| | 비 평균 부호 오차 | +0.010 | +0.005 | −0.004 | −0.010 |
| | 재사용 MAE (8 cell, BASE N20 제외) | 0.0132 | 0.0161 | **0.0066** | 0.0112 |

### cell별 비 (관측 m / sim / sim_op / sim_ctx / sim_ctx_op)

| cell | m | sim | sim_op | sim_ctx | sim_ctx_op |
|---|---|---|---|---|---|
| BATCHONLY N12 | 0.8441 | 0.8828 | 0.8716 | 0.8789 | 0.8612 |
| TUNED N12 | 0.8296 | 0.8637 | 0.8549 | 0.8595 | 0.8426 |
| BATCHONLY N14 | 0.8000 | 0.8321 | 0.8173 | 0.8212 | 0.8132 |
| TUNED N14 | 0.7593 | 0.8108 | 0.7982 | 0.7906 | 0.7851 |
| BATCHONLY N16 | 0.7337 | 0.7804 | 0.7644 | 0.7540 | 0.7485 |
| TUNED N16 | 0.6955 | 0.7544 | 0.7408 | 0.7321 | 0.7224 |
| BATCHONLY N13 | 0.8746 | 0.9029 | 0.8901 | 0.8783 | 0.8744 |
| TUNED N13 | 0.8614 | 0.8942 | 0.8825 | 0.8649 | 0.8587 |
| BATCHONLY N17 | 0.7259 | 0.7376 | 0.7451 | 0.7230 | 0.7265 |
| TUNED N17 | 0.7036 | 0.7121 | 0.7175 | 0.6988 | 0.6959 |
| BATCHONLY N20 | 0.6996 | 0.6945 | 0.6865 | 0.6929 | 0.6804 |
| TUNED N20 | 0.6949 | 0.6796 | 0.6691 | 0.6757 | 0.6650 |

BASE 재사용(관측 / sim / sim_ctx): N12 0.484 / 0.507 / 0.496, N13 0.419 / 0.461 / 0.411, N14 0.298 / 0.330 / 0.303, N16 0.165 / 0.191 / 0.174, N17 0.047 / 0.053 / 0.036, N20 0.000 / 0.001 / 0.000.

## 핵심 발견 (사후)

1. **TASK90 발견 4의 비 편향(Σ 0.262, 평균 +0.044)이 context 비용만으로 0.174(−34 %), context 비용 + 운영 prefill로 0.111(−58 %, 평균 +0.018)로 줄었다.** TASK91의 시간 척도(개발 집합 비율)로는 0.135(−48.5 %)였다 — 이번 비용은 TASK91 관측을 입력으로 쓰지 않은 독립 측정이다.
2. **TASK95 cell에서 context 비용 시뮬레이터가 비 Σ 0.102 → 0.041, 재사용 MAE 0.0132 → 0.0066으로 가장 좋다.** 사후이므로 TASK95의 판정((1) 대 (2) FAIL 포함)은 바뀌지 않는다.
3. 남은 편향은 양(+)이고 batch 16 구성의 구성 효과를 여전히 약간 과소 예측한다(발견 4 집합 평균 +0.018).

## 해석

- 관찰: decode 시간 척도에 context 항을 넣으면 고부하 cell의 비 편향이 줄고, prefill 운영 비용까지 넣으면 N ≤ 16에서 더 줄지만 N13·17·20에서는 오히려 약간 나빠진다(0.041 → 0.060). 파생 해석: 남은 편향의 일부는 prefill 비용(작은 cache-hit prefill의 context 의존, [TASK92](TASK92.md))에 있을 수 있다 — 형태 미확정.
- 이 결과는 사후이며 다음 blind 검증 없이는 확증이 아니다.

## 확인되지 않은 사항

- BATCHONLY의 context 비용(측정하지 않음, 규칙으로 정함).
- prefill의 context 의존 형태.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 시뮬레이터 시간 척도의 비용은 context 분포를 담아야 한다. 사후 개선은 blind 확증과 분리해 `post_hoc`으로만 보고한다.

## 다음 작업

- (Advisor) context 비용 시뮬레이터를 새 blind cell로 검증할지, GPU G-07과의 공통 형태 확인 후 결정.

## 재현 정보

- 위 명령. 산출(비추적) `posthoc_ctx/posthoc_ctx.json` SHA256 `c4d2ce780cf0c398…`, `CTXCOST_SIM.json` `d6d31b3ac303cc6d…`.
- 선등록 commit: 해당 없음(사후 분석, 판정 없음).
