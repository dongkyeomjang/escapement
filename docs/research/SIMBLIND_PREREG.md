# 통합 시뮬레이터 blind cell N = 13·17·20 — 선등록

작성: 2026-10-02, [TASK93](TASK93.md) (Advisor 지시문 08 작업 C). **측정 전.** 이 문서와 plan·예측·영 예측기·순서·판정 스크립트를 한 commit으로 고정한 뒤 측정한다. 기준의 원천: [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) §5와 §7(개정 2), 적용 방식은 [HILOAD_PREREG.md](HILOAD_PREREG.md)와 같다.

## 1. 목적

[결정 10](INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정)에서 해석 모형(v1)의 적용 범위를 "동시 실행 상한 아래"로 정하고 대기열·포화 영역은 **통합 시뮬레이터**를 권장 도구로 두었다. 그 권장 도구를 개발 집합(N ≤ 16)과 겹치지 않는 새 seed·새 N에서 blind로 검증한다. 주 예측기는 [TASK92](TASK92.md)의 운영 조건 step 비용으로 시간을 진행하는 시뮬레이터다.

## 2. plan과 구성

- N ∈ {13, 17, 20}, replicate r = 0..4, plan_id `main-n{N}-r{r}`, 생성 규칙은 본 실험과 같다(`make_simblind_plans.py` = `make_main_plans.py` 규칙, `cycle_s`는 v1 해석 TUNED 예측). 목록 `INDEX_SIM.json`.
  - seed: N = 13 `20261400 + 10N + r` = 20261530–34, N = 20 = 20261600–04. **N = 17은 규칙값 20261570–74의 첫 값이 `ORDER_HI` 순서 seed와 같아 다음 빈 구간 20261575–79**를 쓴다. 기존 plan·격자 선정·파일럿·순서 seed와 겹치지 않는다.
  - context 상한: plan별 최대 context N = 13 3,089–3,249, N = 17 3,008–3,309, N = 20 3,041–3,224 token ≤ `max_seq_len` 8,192.
- 구성: BASE `(1,2,4,8)` b8, BATCHONLY `(1,2,4,8,16)` b16, TUNED `(1,4,6,8,10,16)` b16 — 기존 artifact, **새 compile 없음**. streaming.
- 대기열(주 예측기의 시뮬레이터, 요청당 평균 대기 s): BASE N = 13 0.25, N = 17 1.82, N = 20 3.72. batch 16 구성 N = 13 0.02, N = 17 0.04, N = 20 0.06–0.07. **N = 17·20은 batch 16 구성도 N > 동시 실행 상한**이다.
- lifecycle: 3 N × 3 구성 × 5 = **45**, 약 2.5 h.

**N 선택의 기록.** 원래 지시문의 N = 13·20 중 N = 20 BASE는 시뮬레이터 예측 재사용률이 0.001이라 재사용 판정에 정보가 없다. 사용자 결정(2026-10-02): N = 13·17·20을 측정하고, **N = 20 BASE는 §5.1(기본 기준과 skill 계산)에서 제외하고 "정보 없음"으로 보고하며, 비용 비의 분모로는 그대로 쓴다.** 세 N 모두 측정 전에 예측을 commit한다.

## 3. 예측기와 예측 (측정 전 고정)

`PREDICTIONS_SIM.json`(`predict_simblind.py`, 이 commit에 포함, = `results/npu/stage3/predict/simblind_predictions.json` byte 동일). 입력은 descriptor 상수, `OPCOST_SIM.json`, plan뿐이다. **[TASK91](TASK91.md)의 관측 step 비율과 TASK82·87에서 얻은 어떤 배율도 입력이 아니다.**

- **(1) `sim_op` (주 예측기)** — 시뮬레이터(descriptor v2 관측 의미론, `SimConfig(semantics="descriptor")`)의 **시간 진행**을 [TASK92](TASK92.md) 운영 비용(`OPCOST_SIM.json` = artifact별 decode `F[b] + β·n`, 배타 prefill `ceil(c/128)·(a + d·c)`)으로 한다. turn당 A′의 **가격**은 관측 채널 A′와 같이 원래 비용 모형(TASK13 decode, TASK22 prefill)으로 매긴다 — 시뮬레이션된 decode step마다 `step_time_s(running)`, prefill마다 `prefill_s(computed)`.
- **(2) `sim`** — 같은 시뮬레이터, 시간·가격 모두 원래 비용(= [TASK86](TASK86.md)의 sim 경로; N = 13 plan 하나에서 `predict_v11.sim_plan`과 값이 같음을 확인).
- **(3) `v1` (참고)** — `mt_predict.analytic`, cell의 plan 합산(TASK80 절차). **N > 동시 실행 상한인 cell은 "범위 밖"**([결정 10](INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정)-1) — N = 13 BASE, N = 17·20 전 구성. v1에는 판정을 붙이지 않는다.

| N | 구성 | 재사용 (1) / (2) / (3) | BASE 대비 비 (1) / (2) / (3) | turn당 A′ ms (1) / (2) / (3) | 순위 (1)(2)(3) |
|---|---|---|---|---|---|
| 13 | BASE | 0.427 / 0.461 / 0.369† | 1 | 539 / 540 / 549 | 3 3 3 |
| 13 | BATCHONLY | 0.828 / 0.828 / 0.811 | 0.8901 / 0.9029 / 0.8834 | 480 / 488 / 485 | 2 2 2 |
| 13 | TUNED | 0.826 / 0.826 / 0.814 | 0.8825 / 0.8942 / 0.8669 | 476 / 483 / 476 | 1 1 1 |
| 17 | BASE | 0.068 / 0.053 / 0.293† | 1 | 544 / 549 / 496 | 3 3 3 |
| 17 | BATCHONLY | 0.739 / 0.751 / 0.573† | 0.7451 / 0.7376 / 0.8766† | 405 / 405 / 435 | 2 2 2 |
| 17 | TUNED | 0.748 / 0.757 / 0.708† | 0.7175 / 0.7121 / 0.7984† | 390 / 391 / 396 | 1 1 1 |
| 20 | BASE | 0.000 / 0.001 / 0.283† (§5.1 정보 없음) | 1 | 564 / 562 / 493 | 3 3 3 |
| 20 | BATCHONLY | 0.624 / 0.613 / 0.411† | 0.6865 / 0.6945 / 0.8783† | 387 / 390 / 433 | 2 2 2 |
| 20 | TUNED | 0.632 / 0.619 / 0.388† | 0.6691 / 0.6796 / 0.8742† | 377 / 382 / 431 | 1 1 1 |

† v1 범위 밖. padding·h(n)·대기·replicate별 값은 JSON. 운영 비용은 통제 비용과 decode에서 거의 같고(TASK92: 중앙 0.99–1.01) prefill chunk 비용이 약 7–10 % 크므로 **(1)과 (2)의 차이는 작다**(재사용 ≤ 0.034, 비 ≤ 0.013).

## 4. 판정 기준 (개정 2 그대로, skill 0.5×)

주 예측기는 (1). (2)는 같은 계산으로 판정을 함께 보고하고, (3)은 값만 보고한다.

- **§5.1 재사용**: 확증 cell = 9 cell 중 **N = 20 BASE를 뺀 8 cell**. PASS ⇔ ⌈0.9 × 8⌉ = **8** cell에서 |예측 − 관측| ≤ 0.10, 평균 부호 오차 절댓값 ≤ 0.05. skill: `MAE((1)) ≤ 0.5 × MAE(영)`(영 = 0.67635, 같은 8 cell), 관측 범위 < 0.10이면 `NOT_INFORMATIVE`. N = 20 BASE는 예측·관측 값만 "정보 없음"으로 보고한다.
- **§5.2 비용 비**: cell = BATCHONLY·TUNED × 3 N = 6(분모 BASE는 N = 20 포함 그대로). cell 기본 기준(|예측 − m| ≤ 0.03, 방향 일치 또는 CI가 1 포함 시 |예측 − 1| ≤ 0.03) **6/6**, 강화 기준(예측 ∈ [l − 0.01, u + 0.01]) 83 % 이상 = **5/6**. skill: `Σ|예측 − m| ≤ 0.5 × Σ|1 − m|`, 평균 |1 − m| < 0.01이면 `NOT_INFORMATIVE`.
- **§5.3 순위**: N마다 3쌍의 짝 비 중앙값·CI(N = 20 BASE 포함). CI가 1을 포함하지 않는 쌍만 해소. PASS ⇔ 해소된 모든 쌍에서 (1)의 순서 = 관측 순서, 해소 쌍 0이면 `UNRESOLVED`.
- **§5.6 h(n)**: 9 cell. PASS ⇔ TVD 중앙값 ≤ 0.10, 최댓값 ≤ 0.20. skill: 중앙값 < 영 예측기 TVD 중앙값. (사용자 결정의 "skill 계산 제외"는 재사용 skill에 적용한 것으로 해석한다 — N = 20 BASE의 h는 관측·예측 모두 정의되고 정보가 있다. 이 해석은 Advisor 확인 사항으로 보고한다.)
- **추가 확증 — (1) 대 (2)**: PASS ⇔ `MAE_재사용((1)) < MAE_재사용((2))`(§5.1의 8 cell) **그리고** `Σ|비 예측 − m|((1)) < Σ((2))`(6 cell). 하나라도 아니면 FAIL(각각 보고).
- 최종 표기(`PASS`, `PASS (skill NOT_INFORMATIVE)`, `NOT_CONFIRMED (base PASS, skill FAIL)`, `FAIL`)와 skill 실패 시 결론은 개정 2 §7.3과 같다.
- 판정에 새 종류의 기준은 없다. 비용 비 cell 수 6에서의 83 %는 개정 2의 비율 그대로 ⌈0.83 × 6⌉ = 5다.

### 4.1 영 예측기 — 정의 그대로, 운용 규칙

`NULL_PREDICTORS_SIM.json`(`null_predictors_sim.py`): 재사용 0.67635, 비 1.0, h(n) = 원고 Table I 행의 관측 h(Table I 행 정의 `padding_ratio.TASK26_CELLS`, TASK86과 같은 함수). **운용 규칙(입력값 규칙)**: Table I 행은 N = 6·8·10·12·16뿐이다. **N = 13 = 인접 두 행 12·16의 step 수 합산**(5,682 step; TASK86의 N = 14 규칙과 같음, 분포도 같음), **N = 17·20 = 가장 가까운 행 N = 16**(3,885 step; 16 위의 행이 없다).

## 5. 측정 절차와 규칙 (지시문 05 §2.4와 같다)

- 순서 `ORDER_SIM.json`(`make_simblind_order.py`, seed 20261595 — 미사용; 20261590–94는 N = 19 규칙값이라 피함): 5 round, round k에 블록 (13, k)·(17, k)·(20, k) 무작위 순서, 블록 안 구성 순열은 같은 N의 replicate끼리 서로 다름.
- 구동 `run_simblind.sh`(= `run_hiload.sh` 절차), lifecycle마다 `mt_check.py` 유효성만 본다(index에 `INDEX_SIM.json` 추가).
- `INVALID`는 같은 plan으로 1회만 재실행(`.retry1`), 두 번째도 `INVALID`면 남은 replicate로 판정하고 수를 표기.
- 판정 계산은 모든 lifecycle 뒤 `simblind_analyze.py` 한 번(일괄 판정). bootstrap(seed 20261420, 10,000)·lifecycle 선택·측정 정의는 `main_analyze`의 것.
- 측정 중 HEAD를 바꾸지 않는다.

## 6. 사전 예측 (판정 결과에 대한; 기준 아님)

근거: [TASK87](TASK87.md)에서 sim이 고부하 BASE 재사용을 가장 잘 맞혔고(MAE 0.013), 비용 비는 세 예측기 모두 구성 효과를 과소 예측했다(sim 비 예측이 관측 m보다 0.02–0.05 큼). [TASK92](TASK92.md)에서 운영 비용이 통제 비용과 거의 같았으므로 (1)이 그 편향을 줄이지 못할 것으로 본다.

| 항목 | (1) sim_op (주) | (2) sim |
|---|---|---|
| §5.1 | PASS 쪽 — 단 N = 17·20 batch 16 구성(N > 상한, 처음 관측하는 영역)이 위험 | 같음 |
| §5.2 | 기본 기준 **FAIL** 쪽(N = 13·17에서 차 > 0.03 예상), skill PASS → `FAIL` | 같음 |
| §5.3 | PASS(세 N 모두 TUNED < BATCHONLY < BASE) | PASS |
| §5.6 | PASS 쪽 | PASS 쪽 |
| (1) 대 (2) | **FAIL 쪽** — 두 예측기 차이가 replicate 산포보다 작아 두 조건이 함께 성립할 가능성이 낮다 | — |

## 7. 고정 파일 (SHA256)

commit 직전 값은 [TASK93](TASK93.md) 재현 정보에 적는다(이 문서 자신의 hash는 포함하지 않는다).

## 개정 이력

- 2026-10-02 초판(측정 전).
