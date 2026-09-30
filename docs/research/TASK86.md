# TASK86 — 고부하 blind cell N = 14·16 선등록 (v1.1 검증)

## 상태

DONE

## 날짜

2026-10-01

## 목적

Advisor 지시문 06 작업 D의 선등록. 동결된 v1.1([TASK85](TASK85.md))을 개발 집합 밖의 새 N = 14·16 cell에서 blind로 검증하기 위해 plan·예측(v1.1, v1, sim)·판정 기준·순서·판정 스크립트를 측정 전에 commit한다. 기준은 [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) 개정 2의 §5.1·5.2·5.3·5.6을 **그대로** 쓰고, "v1.1이 v1보다 재사용 MAE와 비 오차 합이 모두 작다"를 확증 항목으로 추가한다. 측정·판정은 [TASK87](TASK87.md)(예정).

**측정 0.**

## 배경

관련 TASK:

- [TASK85](TASK85.md) — v1.1 동결(`ffd716f`)
- [TASK82](TASK82.md)·[TASK81](TASK81.md) — 본 측정 절차와 개정 2 기준
- [TASK84](TASK84.md) — descriptor v2, 시뮬레이터 `semantics="descriptor"`

## 시작 상태

- HEAD `ffd716f`([TASK85](TASK85.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. plan 10개(`make_hiload_plans.py`, 본 실험 생성 규칙, seed 20261540–44·20261560–64, `INDEX_HI.json`). 최대 context 3,016–3,189 token.
2. BASE 대기열 깊이(B2): N = 14 P(대기 > 0) 0.27·E[대기] 0.50, N = 16 0.51·1.24(N = 12 0.06·0.08).
3. 예측(`predict_v11.py` → `PREDICTIONS_HI.json`): v1.1(동결), v1(TASK80 절차), sim(descriptor 관측 의미론).
4. 영 예측기(`null_predictors_hi.py`): 재사용 0.67635, 비 1.0, h(n)은 **Table I 행 정의**(`padding_ratio.TASK26_CELLS`)에서 직접. N = 16 = TASK20 n16. **N = 14 행이 Table I에 없어** N = 12·16 행의 step 합산(운용 규칙, 선등록 §4.1).
5. 순서 `ORDER_HI.json`(seed 20261570, 30 lifecycle), 구동 `run_hiload.sh`, `mt_check.py` index에 `INDEX_HI.json` 추가, 판정 `hiload_analyze.py`(가짜 run으로 코드 경로만 시험).
6. [HILOAD_PREREG.md](HILOAD_PREREG.md)에 목적·plan·대기열 깊이·예측·기준·운용 규칙·정정 기록·사전 예측을 쓰고 위 전부와 commit(`f75c8e7`, 01:49:49).

## 변경된 파일

- 선등록 `f75c8e7`: `docs/research/HILOAD_PREREG.md`, `experiments/npu/stage3/{hiload_analyze.py, make_hiload_order.py, make_hiload_plans.py, null_predictors_hi.py, run_hiload.sh}`(신규), `experiments/npu/stage3/mt_check.py`(index), `experiments/npu/stage3/plans/main/{INDEX_HI, NULL_PREDICTORS_HI, ORDER_HI, PREDICTIONS_HI}.json`, `main-n14-r*.json`·`main-n16-r*.json`
- 이 commit: `docs/research/TASK86.md`, `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/make_hiload_plans.py
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX_HI.json --ns 14,16 \
  --workers 30 --output results/npu/stage3/predict/hiload_predictions.json
env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors_hi.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS_HI.json
env -u PYTHONPATH python3 experiments/npu/stage3/make_hiload_order.py
```

## 결과

예측(재사용 v1.1 / v1 / sim, BASE 대비 비 v1.1 / v1 / sim):

| N | BASE 재사용 | BATCHONLY 비 | TUNED 비 |
|---|---|---|---|
| 14 | 0.173 / 0.329 / 0.330 | 0.806 / 0.857 / 0.832 | 0.786 / 0.835 / 0.811 |
| 16 | 0.068 / 0.305 / 0.191 | 0.753 / 0.838 / 0.780 | 0.732 / 0.817 / 0.754 |

batch 16 구성 재사용은 셋 모두 0.76–0.82. 순위는 셋 모두 TUNED < BATCHONLY < BASE.

**정정(기록)**: 개정 2의 N = 8 h 영 예측기는 TASK19·TASK20·TASK23-2a를 합산했으나 Table I N = 8 행은 TASK20 + TASK23-2a다. 두 분포의 TVD 0.026, TASK82 §5.6 영 예측기 TVD 중앙값은 정정 전후 모두 0.2956(판정 불변). T01 padding 대조 허용 오차(0.0005) 안이라 개정 2의 assert가 통과시켰다.

사전 예측([HILOAD_PREREG.md](HILOAD_PREREG.md) §6): 관측이 sim 근처라면 v1.1 §5.1 **FAIL**(BASE 과대 축출), §5.2 경계, §5.3 PASS, v1.1 대 v1 **FAIL**(비는 v1.1, 재사용은 v1이 나음).

- `requested_condition` 등: 해당 없음(선등록)

## 핵심 발견

1. **`stack`** — **대기열이 상시적인 영역(N = 14·16 BASE)에서 세 예측기의 생존 예측이 크게 갈린다**(v1.1 0.07–0.17, sim 0.19–0.33, v1 0.31–0.33). 이 cell들은 결합·대기 항의 가치를 가르는 판별력 있는 blind 검증이다.

## 해석

- 사전 예측이 v1.1에 불리하다는 것을 알고도 기준을 바꾸지 않는다. 개발 집합(N = 12)에서 v1.1이 BASE를 이미 0.048 과소 예측했고, 대기열이 길어질수록 그 근사가 벌을 키울 수 있다.

## 확인되지 않은 사항

- 측정 결과([TASK87](TASK87.md) 예정).

## 실패 / 무효 시도

- 없음(예측 계산의 thread 과다·병렬 실행 실수는 [TASK85](TASK85.md)에 기록).

## 연구 원칙에 미치는 영향

- 영 예측기의 입력은 "같은 이름의 표"가 아니라 그 표의 **행 정의 코드**에서 만든다(개정 2 N = 8 정정의 교훈).

## 다음 작업

- 측정 30 lifecycle과 판정([TASK87](TASK87.md)).

## 재현 정보

- 위 명령. 고정 파일 SHA256은 [HILOAD_PREREG.md](HILOAD_PREREG.md) §7.
- **선등록 commit `f75c8e7546e88f7a829b943902f597a9d04d9779` (2026-10-01 01:49:49 +0900). 측정은 이 TASK 기록 commit 뒤에 시작한다.**
