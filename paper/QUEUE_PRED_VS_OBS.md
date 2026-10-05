# 예측 대기열 대 관측 대기열 (지시문 15 작업 E)

생성: `experiments/npu/analysis/queue_pred_vs_obs.py` → `results/npu/stage3/queue_obs/queue_pred_vs_obs.json`(비추적). 관측: `results/npu/stage3/queue_obs/queue_obs.json`(TASK96·105). GPU: `docs/research/gpu/GTASK14.md` 「대기열과 시간」 표.

## 1. 정의

| 양 | 정의 | 가중 | 출처 |
|---|---|---|---|
| 관측 Q (NPU) | 평가 구간 decode step마다 client in-flight − `[BUCKET] request_nums` | decode step | `experiments/npu/analysis/queue_depth_obs.py` |
| 예측 Q (시뮬레이터) | 평가 구간 decode step마다 #{arrival ≤ t} − #{admit ≤ t} | decode step | `queue_pred_vs_obs.py:run` |
| 예측 Q (해석 모형) | Σ_n π(n)·max(0, n − M), 고정점 마지막 반복의 점유 분포 | 시간 | `queue_pred_vs_obs.py:analytic_queue` → `mt_predict.analytic` |
| 관측·예측 Q (GPU) | 창 안 step마다 송신했으나 아직 조회되지 않은 요청 수 | step | GTASK14 수행 내용 1·2 |

예측 파일(측정 전 commit)에는 대기열 길이가 없다. 같은 plan·descriptor·비용 파일·코드로 다시 계산했고, **33 cell 전부에서 재계산 재사용률이 선등록 예측 파일 값과 정확히 같다**(입력·코드 동일 확인). 해석 모형 값은 TASK86이 측정 전에 기록한 B2 대기 값과 같다(N14 0.496 ≈ 0.50, N16 1.243 ≈ 1.24).

관측 Q에는 전송·응답 종료 시간의 바닥값(구조적 대기 0 cell 0.013–0.040)이 있고 시뮬레이터에는 없다.

## 2. cell별 (NPU)

| 묶음 (선등록 commit) | N | 구성 | 관측 Q | 주 sim 예측 | 원래 비용 sim 예측 | 해석 모형 예측 | 해석 P(대기 > 0) |
|---|---|---|---|---|---|---|---|
| TASK82 (eedf5ed / 5f62fb4) | 6 | BASE | 0.013 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 6 | BATCHONLY | 0.013 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 6 | TUNED | 0.014 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 8 | BASE | 0.018 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 8 | BATCHONLY | 0.018 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 8 | TUNED | 0.018 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 10 | BASE | 0.044 | 0.020 (`sim_observed`) | 0.020 | 0.002 | 0.002 |
| TASK82 (eedf5ed / 5f62fb4) | 10 | BATCHONLY | 0.022 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 10 | TUNED | 0.022 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 12 | BASE | 0.280 | 0.204 (`sim_observed`) | 0.204 | 0.079 | 0.058 |
| TASK82 (eedf5ed / 5f62fb4) | 12 | BATCHONLY | 0.029 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK82 (eedf5ed / 5f62fb4) | 12 | TUNED | 0.031 | 0.000 (`sim_observed`) | 0.000 | 0.000 | 0.000 |
| TASK87 (f75c8e7) | 14 | BASE | 0.761 | 0.628 (`sim`) | 0.628 | 0.496 | 0.270 |
| TASK87 (f75c8e7) | 14 | BATCHONLY | 0.035 | 0.000 (`sim`) | 0.000 | 0.000 | 0.000 |
| TASK87 (f75c8e7) | 14 | TUNED | 0.034 | 0.000 (`sim`) | 0.000 | 0.000 | 0.000 |
| TASK87 (f75c8e7) | 16 | BASE | 1.802 | 1.505 (`sim`) | 1.505 | 1.243 | 0.507 |
| TASK87 (f75c8e7) | 16 | BATCHONLY | 0.040 | 0.000 (`sim`) | 0.000 | 0.000 | 0.000 |
| TASK87 (f75c8e7) | 16 | TUNED | 0.038 | 0.000 (`sim`) | 0.000 | 0.000 | 0.000 |
| TASK95 (cc29e76) | 13 | BASE | 0.420 | 0.319 (`sim_op`) | 0.278 | 0.158 | 0.104 |
| TASK95 (cc29e76) | 13 | BATCHONLY | 0.031 | 0.000 (`sim_op`) | 0.000 | 0.000 | 0.000 |
| TASK95 (cc29e76) | 13 | TUNED | 0.032 | 0.000 (`sim_op`) | 0.000 | 0.000 | 0.000 |
| TASK95 (cc29e76) | 17 | BASE | 3.528 | 3.235 (`sim_op`) | 3.137 | 2.326 | 0.733 |
| TASK95 (cc29e76) | 17 | BATCHONLY | 0.045 | 0.000 (`sim_op`) | 0.000 | 0.000 | 0.000 |
| TASK95 (cc29e76) | 17 | TUNED | 0.045 | 0.000 (`sim_op`) | 0.000 | 0.000 | 0.000 |
| TASK95 (cc29e76) | 20 | BASE | 6.820 | 6.678 (`sim_op`) | 6.558 | 4.771 | 0.936 |
| TASK95 (cc29e76) | 20 | BATCHONLY | 0.099 | 0.030 (`sim_op`) | 0.032 | 0.018 | 0.014 |
| TASK95 (cc29e76) | 20 | TUNED | 0.096 | 0.038 (`sim_op`) | 0.037 | 0.020 | 0.016 |
| TASK102 (cb1eec4) | 15 | BASE | 1.612 | 1.650 (`sim_ctx_op`) | 1.305 | 0.915 | 0.421 |
| TASK102 (cb1eec4) | 15 | BATCHONLY | 0.040 | 0.000 (`sim_ctx_op`) | 0.000 | 0.000 | 0.000 |
| TASK102 (cb1eec4) | 15 | TUNED | 0.037 | 0.000 (`sim_ctx_op`) | 0.000 | 0.000 | 0.000 |
| TASK102 (cb1eec4) | 18 | BASE | 3.852 | 3.850 (`sim_ctx_op`) | 3.634 | 2.703 | 0.773 |
| TASK102 (cb1eec4) | 18 | BATCHONLY | 0.048 | 0.000 (`sim_ctx_op`) | 0.000 | 0.000 | 0.000 |
| TASK102 (cb1eec4) | 18 | TUNED | 0.046 | 0.000 (`sim_ctx_op`) | 0.000 | 0.000 | 0.000 |

주 sim: TASK82는 해석 모형이 주 예측기였으므로 `sim_observed`, TASK87은 주 예측기 v1.1이 대기열을 내지 않아 `sim`(descriptor 의미론)을 적었다.

## 3. 상관과 오차 (NPU 33 cell)

| 예측 | Pearson | Spearman | MAE | 평균 부호 오차 (예측 − 관측) | BASE N ≥ 12 예측/관측 중앙 |
|---|---|---|---|---|---|
| 주 sim | 0.999 | 0.820 | 0.058 | -0.055 | 0.876 |
| 원래 비용 sim | 0.999 | 0.820 | 0.080 | -0.080 | 0.830 |
| 해석 모형 | 0.999 | 0.911 | 0.220 | -0.220 | 0.656 |

GPU(GTASK11 cell 8개, BASE·POOL N20–26; 관측 대 원래 sim LRU): Pearson 0.996, Spearman 1.000, MAE 1.69, 예측/관측 중앙 0.608 (GTASK14 표 값).

| GPU cell | 관측 Q | 원래 sim LRU Q |
|---|---|---|
| N20 BASE | 2.35 | 1.11 |
| N20 POOL | 2.18 | 1.00 |
| N22 BASE | 3.18 | 1.82 |
| N22 POOL | 2.93 | 1.60 |
| N24 BASE | 5.57 | 3.84 |
| N24 POOL | 5.01 | 3.41 |
| N26 BASE | 8.15 | 5.56 |
| N26 POOL | 7.00 | 4.50 |

GPU N = 25·28(GTASK20)은 대기열 관측이 없어 제외. GTASK14 표에 POOL+GRID는 "POOL과 ±0.06 안"으로만 기록돼 있어 넣지 않았다.

## 4. 문턱과 혼동표

- **문턱 Q = 0.1**: Advisor 지시문 14가 그림 F_d에 세로 점선으로 지정한 값. 관측 BASE N = 10(0.044)과 N = 12(0.280) 사이에 놓이며, **관측을 본 뒤 정했다 — 이 분류 대조는 사후(`post_hoc`)다.** 예측 자체는 측정 전에 commit됐다.
- 분류: Q ≥ 0.1 = 대기열 있음.

| 예측 | 관측 있음·예측 있음 | 관측 있음·예측 없음 | 관측 없음·예측 있음 | 관측 없음·예측 없음 | 반대쪽 cell |
|---|---|---|---|---|---|
| 주 sim | 8 | 0 | 0 | 25 | 없음 |
| 원래 비용 sim | 8 | 0 | 0 | 25 | 없음 |
| 해석 모형 | 7 | 1 | 0 | 25 | TASK82 N12 BASE (관측 0.28, 예측 0.079) |

- 문턱 근처 cell: TASK95 N = 20 BATCHONLY·TUNED 관측 0.099·0.096(문턱 바로 아래, 예측 0.030–0.038). 문턱을 0.09로 내리면 관측만 '있음'으로 바뀐다.
- GPU 8 cell은 관측·예측 모두 1 이상이라 같은 쪽(있음)이다.

## 5. 결과 색인 판정 종류

| 항목 | 판정 종류 |
|---|---|
| 예측 대기열 값(측정 전 commit된 예측의 재계산) 대 관측의 상관·오차 | blind_confirm 아님 — 대기열은 선등록 판정 항목이 아니었다: `exploratory` |
| 문턱 0.1 기준 혼동표 | `post_hoc` (문턱을 관측을 보고 정함) |
