# context 비용 시뮬레이터 blind cell N = 15·18 — 선등록

작성: 2026-10-02, [TASK101](TASK101.md) (Advisor 지시문 11 작업 B). **측정 전.** 이 문서와 plan·예측·영 예측기·순서·판정 스크립트를 한 commit으로 고정한 뒤 측정한다. 기준의 원천: [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) §5와 §7(개정 2). 적용 방식은 [SIMBLIND_PREREG.md](SIMBLIND_PREREG.md)와 같다.

## 1. 목적

[결정 12](INDEX.md#결정-12--지시문-11-결정-context-비용-채택과-blind-검증)에서 context 길이 decode 비용 형태(`t = f(b) + βn + c·ΣL`, [TASK97](TASK97.md)·[TASK100](TASK100.md))를 채택했다. 지금까지의 시뮬레이터 개선([TASK98](TASK98.md))은 모두 사후 분석이므로, 이 비용을 쓰는 통합 시뮬레이터를 **처음 보는 N**에서 blind로 검증한다.

## 2. plan과 구성

- N ∈ {15, 18}, replicate r = 0..4, plan_id `main-n{N}-r{r}`, 생성 규칙은 본 실험과 같다(`make_ctxblind_plans.py` = `make_main_plans.py` 규칙, `cycle_s`는 v1 해석 TUNED 예측). seed `20261400 + 10N + r` = 20261550–54, 20261580–84 — 기존 plan·격자 선정·파일럿·순서 seed와 겹치지 않는다. 목록 `INDEX_CTX.json`. 두 N 모두 지금까지 측정하지 않은 값이며 BASE는 대기열 영역이다(N > 8).
- `cycle_s` N15 6.182–6.313, N18 7.238–7.313. 최대 context N15 3,085–3,236, N18 3,077–3,260 ≤ 8,192.
- 구성: BASE `(1,2,4,8)` b8, BATCHONLY `(1,2,4,8,16)` b16, TUNED `(1,4,6,8,10,16)` b16 — 기존 artifact, 새 compile 없음. streaming.
- 대기열(주 예측기 시뮬레이터, 요청당 평균 대기): BASE N15 1.03 s, N18 2.27 s; batch 16 구성 0.03 s. **N = 18은 batch 16 구성도 N > 동시 실행 상한**이다.
- lifecycle: 2 N × 3 구성 × 5 = **30**, 약 2–2.3 h.
- **N = 18 BASE 정보량 점검(지시문 11 §4.1)**: 주 예측기의 예측 재사용 **0.045**(≥ 0.03)이라 대안 N을 제안하지 않고 N = 18을 그대로 쓴다. 단 예측기 (2)는 0.026이다(< 0.03). §5.1에서 N = 18 BASE를 빼지 않는다(이전 N = 20 BASE의 "정보 없음" 처리는 예측 0.000–0.001일 때의 사용자 결정이었다).

## 3. 예측기와 예측 (측정 전 고정)

`PREDICTIONS_CTX.json`(`predict_ctxblind.py`, = `results/npu/stage3/predict/ctxblind_predictions.json` byte 동일). 입력은 descriptor 상수, `CTXCOST_BLIND.json`(context 비용, BASE·TUNED [TASK97](TASK97.md) F1, **BATCHONLY [TASK100](TASK100.md) 실측 F1** — 규칙 추정 없음), `OPCOST_SIM.json`([TASK92](TASK92.md) 운영 prefill), plan뿐이다. multi-turn run의 관측값은 읽지 않는다.

- **(1) 주 예측기 `sim_ctx_op`** — 통합 시뮬레이터(descriptor v2 관측 의미론)의 시간을 decode = context 비용, 배타 prefill = TASK92 운영 비용으로 진행한다. turn당 A′ 가격은 원래 비용 모형(관측 A′와 같은 정의).
- **(2) `sim`** — 원래 비용(= TASK93 예측기 (2)).
- **(3) `v1`** — 해석 v1 참고. N > 동시 실행 상한인 cell(BASE 두 N, N = 18 batch 16 구성)은 **범위 밖**. 판정 없음.
- 보고만: `sim_ctx`(context 비용 + 원래 prefill) — 주 예측기의 다른 후보, 판정 없음.

### 3.1 주 예측기 선택과 근거

**사전에 정한 조합 `sim_ctx_op`(context 비용 + 운영 prefill)을 주 예측기로 둔다** — TASK98에서 집합마다 오차가 가장 작았던 조합을 고르는 방식이 아니다. 근거:

1. 구성 요소가 모두 **결과와 독립된 통제 측정**에서 왔다. decode는 TASK97·100, prefill은 TASK92 `op-prefill-mt`. TASK92는 작은 cache-hit prefill의 운영 초과(통제 대비 1.23–1.48)가 같은 경로의 통제 부하에서도 재현됨을 보였다. 원래 prefill 비용을 쓰면 알려진 과소를 그대로 남긴다.
2. 지시문 11 §4.2가 (1)을 "context 비용 + 운영 prefill"로 제시했다.
3. **사후 결과에 기댄 부분(명시)**: [TASK98](TASK98.md)에서 이 조합은 발견 4 집합(N12·14·16)에서 비 Σ 0.111로 가장 작았다. 반면 TASK95 집합(N13·17·20)에서는 0.060으로 `sim_ctx`(0.041)보다 컸다. 두 집합 결과가 엇갈리므로 사후 결과는 선택을 정하지 못한다. 위 1·2를 근거로 정했고, 사후 결과는 두 조합 모두 원래 비용보다 낫다는 정도로만 참고했다.

### 3.2 예측

| N | 구성 | 재사용 (1) / (2) / (3) | 비 (1) / (2) / (3) | 순위 (1)(2)(3) |
|---|---|---|---|---|
| 15 | BASE | 0.110 / 0.156 / 0.313† | 1 | 3 3 3 |
| 15 | BATCHONLY | 0.786 / 0.797 / 0.783 | 0.7486 / 0.7774 / 0.8430 | 2 2 2 |
| 15 | TUNED | 0.787 / 0.792 / 0.774 | 0.7302 / 0.7576 / 0.8217 | 1 1 1 |
| 18 | BASE | 0.045 / 0.026 / 0.286† | 1 | 3 3 3 |
| 18 | BATCHONLY | 0.733 / 0.745 / 0.540† | 0.7011 / 0.7158 / 0.8791† | 2 2 2 |
| 18 | TUNED | 0.733 / 0.739 / 0.643† | 0.6797 / 0.6949 / 0.8140† | 1 1 1 |

† v1 범위 밖. `sim_ctx`: 재사용 0.137 / 0.790 / 0.793 / 0.043 / 0.730 / 0.742, 비 0.7561 / 0.7371 / 0.7054 / 0.6791. h(n)·대기·replicate별 값은 JSON.

## 4. 판정 기준 (개정 2 그대로, skill 0.5×)

주 예측기는 (1). (2)는 같은 계산으로 판정을 보고하고, (3)과 `sim_ctx`는 값만 보고한다. 확증 cell = N ∈ {15, 18} × {BASE, BATCHONLY, TUNED}(6), 비용 비 cell = BATCHONLY·TUNED(4).

- **§5.1 재사용**: PASS ⇔ ⌈0.9 × 6⌉ = **6/6** cell에서 |예측 − 관측| ≤ 0.10, 평균 부호 오차 절댓값 ≤ 0.05. skill: `MAE((1)) ≤ 0.5 × MAE(영)`(영 = 0.67635), 관측 범위 < 0.10이면 `NOT_INFORMATIVE`.
- **§5.2 비용 비**: cell 기본 기준(|예측 − m| ≤ 0.03, 방향 일치 또는 CI가 1 포함 시 |예측 − 1| ≤ 0.03) **4/4**, 강화 기준(예측 ∈ [l − 0.01, u + 0.01]) 83 % 이상 = **4/4**(3/4 = 0.75). skill: `Σ|예측 − m| ≤ 0.5 × Σ|1 − m|`, 평균 |1 − m| < 0.01이면 `NOT_INFORMATIVE`.
- **§5.3 순위**: N마다 3쌍의 짝 비 중앙값·CI. CI가 1을 포함하지 않는 쌍만 해소. PASS ⇔ 해소된 모든 쌍에서 (1)의 순서 = 관측 순서, 해소 쌍 0이면 `UNRESOLVED`.
- **§5.6 h(n)**: 6 cell. PASS ⇔ TVD 중앙값 ≤ 0.10, 최댓값 ≤ 0.20. skill: 중앙값 < 영 예측기 TVD 중앙값.
- **추가 확증 — (1) 대 (2)**: PASS ⇔ `MAE_재사용((1)) < MAE_재사용((2))`(6 cell) **그리고** `Σ|비 예측 − m|((1)) < Σ((2))`(4 cell). 하나라도 아니면 FAIL(각각 보고).
- 최종 표기와 skill 실패 시 결론은 개정 2 §7.3과 같다. 새 종류의 기준은 없다.

### 4.1 영 예측기

`NULL_PREDICTORS_CTX.json`(`null_predictors_ctx.py`): 재사용 0.67635, 비 1.0, h(n) = 원고 Table I 행. **운용 규칙(입력값 규칙)**: N = 15 = 인접 두 행 12·16 합산(5,682 step; N = 13·14와 같은 규칙), N = 18 = 가장 가까운 행 16(3,885 step; N = 17·20과 같은 규칙).

## 5. 측정 절차와 규칙 (지시문 05 §2.4와 같다)

- 순서 `ORDER_CTX.json`(`make_ctxblind_order.py`, seed 20261596 — 미사용): 5 round, round k에 블록 (15, k)·(18, k) 무작위 순서, 블록 안 구성 순열은 같은 N의 replicate끼리 서로 다름.
- 구동 `run_ctxblind.sh`(= `run_simblind.sh` 절차), lifecycle마다 `mt_check.py` 유효성만 본다(index에 `INDEX_CTX.json` 추가).
- `INVALID`는 같은 plan으로 1회만 재실행(`.retry1`), 두 번째도 `INVALID`면 남은 replicate로 판정하고 수를 표기.
- 판정은 모든 lifecycle 뒤 `ctxblind_analyze.py` 한 번. bootstrap(seed 20261420, 10,000)·lifecycle 선택·측정 정의는 `main_analyze`의 것.
- **측정 중 HEAD를 바꾸지 않고, 다른 작업(저장소 scan, export, 분석, 시뮬레이션)을 돌리지 않는다**(지시문 11 §4.4).

## 6. 사전 예측 (판정 결과에 대한; 기준 아님)

근거: [TASK95](TASK95.md) blind에서 원래 비용 sim이 §5.1·5.3·5.6을 통과하고 §5.2는 한 cell 차(0.0328)로 FAIL했다. **운영 비용 대 원래 비용의 추가 확증은 FAIL**이었다(두 지표 모두 원래 비용이 작음). [TASK98](TASK98.md)(사후)에서 `sim_ctx_op`는 두 집합 모두 원래 비용보다 비 Σ와 재사용 MAE가 작았다. 다만 재사용 MAE 차는 0.002–0.006으로 replicate 산포와 같은 자릿수다.

| 항목 | (1) sim_ctx_op (주) | (2) sim |
|---|---|---|
| §5.1 | PASS 쪽 — N15 BASE에서 두 예측기가 0.11 대 0.16으로 갈려 이 cell이 가른다 | PASS 쪽 |
| §5.2 | PASS 쪽(경계) — TASK98 사후 오차가 N14·16에서 0.01–0.03 | FAIL 쪽 — TASK98에서 원래 비용 비 오차가 N14·16에서 0.03–0.06 |
| §5.3 | PASS | PASS |
| §5.6 | PASS 쪽 | PASS 쪽 |
| (1) 대 (2) | 비 Σ는 (1)이 작을 것. 재사용 MAE는 불확실 → **전체 PASS 쪽, 확신 낮음** | — |

TASK95의 같은 형태 비교가 FAIL이었다는 이력 때문에 확신을 낮게 둔다. 차이를 만드는 것은 decode의 context 항이다. TASK95의 운영 비용은 decode에서 통제 비용과 거의 같았고, 이번 비용은 다르다.

## 7. 고정 파일 (SHA256 앞 16자리)

`INDEX_CTX.json` `02cd4fb133e379f8`, `PREDICTIONS_CTX.json` `06349354fa6d5f5c`, `NULL_PREDICTORS_CTX.json` `6c5b96768716e2e8`, `ORDER_CTX.json` `18b0e2eb0fd931cf`, `CTXCOST_BLIND.json` `a6a3a614ecc6dd66`, `OPCOST_SIM.json` `29b96b8a14850f6c`, `predict_ctxblind.py` `b1d1817a28c35f8f`, `ctxblind_analyze.py` `87b8b10a5b9656aa`, `run_ctxblind.sh` `a6efaf538fc931fe`. 판정 스크립트는 가짜 run(TASK87 N14·16 산출을 N15·18 tag에 symlink)으로 코드 경로만 시험했다(값 무의미).

## 개정 이력

- 2026-10-02 초판(측정 전).
