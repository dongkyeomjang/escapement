# 고부하 blind cell N = 14·16 — 모형 v1.1 검증 선등록

작성: 2026-10-01, [TASK86](TASK86.md) (Advisor 지시문 06 작업 D). **측정 전.** 이 문서와 v1.1 코드·예측·판정 스크립트를 한 commit으로 고정한 뒤 측정한다. v1.1 명세: [MODEL_V1_1.md](MODEL_V1_1.md)([TASK85](TASK85.md)). 기준의 원천: [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) §5와 §7(개정 2).

## 1. 목적

v1.1(대기열·부하 결합 생존)을 개발 집합(N = 12) 밖의 **더 높은 부하**에서 blind로 검증한다. N = 14·16에서 BASE(`M` = 8)는 대기열이 상시적이고, batch 16 구성은 아직 대기열이 없다.

## 2. plan과 구성

- N ∈ {14, 16}, replicate r = 0..4, seed `20261400 + 10N + r` = 20261540–44, 20261560–64(기존 plan·격자 선정·파일럿 seed와 겹치지 않음), plan_id `main-n{N}-r{r}`. 생성 규칙은 본 실험과 같다(`make_hiload_plans.py` = `make_main_plans.py` 규칙, `cycle_s`는 v1 해석 TUNED 예측). 목록 `INDEX_HI.json`.
- **context 상한**: plan별 최대 context 3,016–3,189 token(N=14 최대 3,131, N=16 최대 3,189) ≤ `max_seq_len` 8,192.
- 구성: BASE `(1,2,4,8)` b8, BATCHONLY `(1,2,4,8,16)` b16, TUNED `(1,4,6,8,10,16)` b16 — 기존 artifact, **새 compile 없음**. streaming.
- **BASE 대기열 깊이(B2, v1 고정점, 측정 전 계산)**: N = 12 P(대기 > 0) 0.058·E[대기] 0.08, **N = 14 0.27·0.50, N = 16 0.51·1.24**. batch 16 구성은 N ≤ 16에서 대기 0(N ≤ M).
- lifecycle: 2 N × 3 구성 × 5 = **30**, 약 2–2.5 h.

## 3. 예측기와 예측 (측정 전 고정)

`PREDICTIONS_HI.json`(`predict_v11.py`, 이 commit에 포함). 입력은 descriptor 상수와 plan뿐이다.

- **v1.1 (주 예측기)** — [TASK85](TASK85.md)에서 동결: plan별로 gap 법칙(zero atom + 지수 3위상, EM) 적합, 완료 순서 `admission`, 대기열·부하 결합 연쇄 생존을 v1 해석 경로의 재사용–prefill 고정점에 넣음, cell 값 = plan 평균.
- **v1** — `mt_predict.analytic`, cell의 plan 합산 통계(TASK80 절차 그대로).
- **sim** — 시뮬레이터, descriptor v2의 관측 의미론(`SimConfig(semantics="descriptor")`), plan 합산.

| N | 구성 | 재사용 v1.1 / v1 / sim | BASE 대비 비 v1.1 / v1 / sim | turn당 A′ ms v1.1 / v1 / sim | 순위(1 = 싸다) |
|---|---|---|---|---|---|
| 14 | BASE | **0.173** / 0.329 / 0.330 | 1 | 553 / 522 / 544 | 3 (셋 모두) |
| 14 | BATCHONLY | 0.816 / 0.800 / 0.805 | **0.8057** / 0.8569 / 0.8321 | 445 / 448 / 453 | 2 |
| 14 | TUNED | 0.817 / 0.804 / 0.807 | **0.7861** / 0.8350 / 0.8108 | 434 / 436 / 441 | 1 |
| 16 | BASE | **0.068** / 0.305 / 0.191 | 1 | 555 / 504 / 547 | 3 |
| 16 | BATCHONLY | 0.803 / 0.770 / 0.778 | **0.7525** / 0.8383 / 0.7804 | 418 / 423 / 427 | 2 |
| 16 | TUNED | 0.799 / 0.759 / 0.792 | **0.7316** / 0.8167 / 0.7544 | 406 / 412 / 413 | 1 |

v1.1 plan별 BASE 재사용: N = 14 0.218 / 0.139 / 0.195 / 0.161 / 0.155, N = 16 0.053 / 0.088 / 0.055 / 0.097 / 0.049. padding·h(n)·W·plan별 gap 법칙은 JSON. **세 예측기가 크게 갈리는 곳**: BASE 재사용(v1.1이 가장 낮다), 그리고 그 결과인 비용 비(v1.1 0.73–0.81, v1 0.82–0.86, sim 0.75–0.83).

v1.1 예측은 TASK85 동결 commit `ffd716f`의 코드(`survival_v11.py`, `mt_predict_v11.py`, `predict_v11.py`)로 계산했다 — 계산 시작 뒤 이 파일들은 바뀌지 않았다. v1은 `mt_predict.py`(TASK80 이후 무변경), sim은 TASK84 descriptor 경로.

## 4. 판정 기준 (MULTITURN_MAIN_PREREG.md 개정 2를 그대로)

확증 cell = N ∈ {14, 16} × {BASE, BATCHONLY, TUNED}(6개), 비용 비 cell은 BATCHONLY·TUNED(4개). 문턱·skill 조건·최종 표기는 개정 2와 같다. **주 예측기는 v1.1**(§5.1–5.3·5.6의 "해석" 자리), v1·sim은 같은 계산으로 보고한다.

- **§5.1 재사용**: PASS ⇔ 6 cell 중 ⌈0.9 × 6⌉ = **6**에서 |예측 − 관측| ≤ 0.10, 평균 부호 오차 절댓값 ≤ 0.05. skill: `MAE(v1.1) ≤ 0.5 × MAE(영)`(영 = 0.67635), 관측 범위 < 0.10이면 `NOT_INFORMATIVE`.
- **§5.2 비용 비**: cell 기본 기준(|예측 − m| ≤ 0.03, 방향 일치 또는 CI가 1 포함 시 |예측 − 1| ≤ 0.03) **4/4**, 강화 기준(예측 ∈ [l − 0.01, u + 0.01])은 83 % 이상 = **4/4**(3/4 = 0.75). skill: `Σ|예측 − m| ≤ 0.5 × Σ|1 − m|`, 평균 |1 − m| < 0.01이면 `NOT_INFORMATIVE`. 예측기별.
- **§5.3 순위**: N마다 3쌍의 짝 비 중앙값·CI. CI가 1을 포함하지 않는 쌍만 해소. PASS ⇔ 해소된 모든 쌍에서 v1.1 순서 = 관측 순서, 해소 쌍 0이면 `UNRESOLVED`.
- **§5.6 h(n)**: PASS ⇔ 6 cell TVD 중앙값 ≤ 0.10, 최댓값 ≤ 0.20. skill: 중앙값 < 영 예측기 TVD 중앙값.
- **추가 확증 — v1.1 대 v1**: PASS ⇔ 확증 cell에서 `MAE_재사용(v1.1) < MAE_재사용(v1)` **그리고** `Σ|비 예측 − m|(v1.1) < Σ(v1)`. 둘 중 하나라도 아니면 FAIL(각각 보고).
- 최종 표기(`PASS`, `PASS (skill NOT_INFORMATIVE)`, `NOT_CONFIRMED (base PASS, skill FAIL)`, `FAIL`)와 skill 실패 시 결론은 개정 2 §7.3과 같다.

### 4.1 영 예측기 — 정의 그대로, 하나의 운용 규칙

`NULL_PREDICTORS_HI.json`(`null_predictors_hi.py`, 이 commit): 재사용 0.67635(개정 2와 같음), 비 1.0, h(n) = **원고 Table I(T01) 행의 관측 h**를 Table I 행 정의(`padding_ratio.TASK26_CELLS`)에서 직접 만든다 — N = 16 = TASK20 n16 5블록(3,885 step, padding 0.039 = T01).

**운용 규칙(새 종류의 기준이 아니라 입력값 규칙)**: Table I에는 **N = 14 행이 없다**. N = 14의 영 예측기는 **인접 두 행 N = 12와 N = 16의 step 수 합산**(5,682 step)으로 정한다. 기준의 종류(TVD 중앙값 비교)는 바꾸지 않는다.

**정정 기록**: 개정 2의 N = 8 영 예측기는 `padding_ratio.json`의 격자 (1,2,4,8) N = 8 cell 셋(TASK19·TASK20·TASK23-2a)을 합산했으나, Table I의 N = 8 행은 **TASK20 + TASK23-2a**(TASK19 제외)다. 두 분포의 TVD는 0.026이다. TASK82 §5.6 판정에 미치는 영향은 [TASK86](TASK86.md)에 계산해 둔다(판정은 바꾸지 않는다).

## 5. 측정 절차와 규칙 (지시문 05 §2.4와 같다)

- 순서 `ORDER_HI.json`(`make_hiload_order.py`, seed 20261570): 5 round, round k에 블록 (14, k)·(16, k) 무작위 순서, 블록 안 구성 순열은 같은 N의 replicate끼리 서로 다름.
- 구동 `run_hiload.sh`(= `run_main.sh` 절차, DP 없음), lifecycle마다 `mt_check.py` 유효성만 본다(index에 `INDEX_HI.json` 추가).
- `INVALID`는 같은 plan으로 1회만 재실행(`.retry1`), 두 번째도 `INVALID`면 남은 replicate로 판정하고 수를 표기.
- 판정 계산은 모든 lifecycle 뒤 `hiload_analyze.py` 한 번. bootstrap·lifecycle 선택·측정 정의는 `main_analyze`의 것.
- 측정 중 HEAD를 바꾸지 않는다.

## 6. 사전 예측 (판정 결과에 대한)

판정은 아래 기준대로 하며 이 사전 예측은 기준이 아니다. 근거: 개발 집합과 사후 대조에서 시뮬레이터가 BASE 재사용을 가장 잘 맞혔다(N = 12 0.485 대 관측 0.484). 관측이 sim 예측 근처라면:

| 항목 | v1.1 (주) | v1 | sim |
|---|---|---|---|
| §5.1 | **FAIL** — BASE 오차 N14 −0.16, N16 −0.12로 6/6 불성립 | FAIL(N16 BASE +0.11) | PASS |
| §5.2 | 기본 기준 경계(차 0.023–0.028), skill PASS | FAIL(N16 차 0.058–0.062) | PASS |
| §5.3 | PASS(세 예측기 순서 동일) | PASS | PASS |
| §5.6 | 경계 | 경계 | 경계 |
| v1.1 대 v1 | **FAIL** — 비는 v1.1이 낫고(Σ ≈ 0.10 대 0.17) 재사용은 v1이 낫다(MAE ≈ 0.055 대 0.027) | — | — |

즉 **v1.1이 고부하 BASE의 축출을 과대 예측할 것**으로 본다(개발 집합에서 이미 −0.048 과소였고, 대기열이 길어질수록 결합·대기 항의 근사가 벌을 키운다). 이 예측이 틀리면(관측 BASE 재사용이 v1.1 쪽이면) 시뮬레이터와 v1이 대기열 영역에서 축출을 과소 평가한다는 뜻이다.

## 7. 고정 파일 (SHA256)

- `INDEX_HI.json` `97f8a642978c4e91cd1ff20510b59bfa777f5eea0110038016d3529724a73ead`
- `PREDICTIONS_HI.json` `df9eefa54af602d1d782c4d291afa9bc1834e835186cab4231b6b9d6354f6133`(= `results/npu/stage3/predict/hiload_predictions.json` byte 동일)
- `NULL_PREDICTORS_HI.json` `6c14d9b1baea38ff24495b1083d52020c5c34eb3b5ab76a2e85fe699311822fb`
- `ORDER_HI.json` `60fd8e38eba9d06743f7c3261c81b5d7bcf38bdeb9ec2850496b46715d09a971`
- 판정 `hiload_analyze.py` — 가짜 run(N = 12 산출을 symlink로 N = 14·16 tag에 배치)으로 코드 경로만 시험했다(값 무의미).

## 개정 이력

- 2026-10-01 초판(측정 전).
