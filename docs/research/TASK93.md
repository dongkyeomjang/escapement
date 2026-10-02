# TASK93 — 통합 시뮬레이터 blind cell N = 13·17·20 선등록

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 08 작업 C의 선등록. [결정 10](INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정)에서 대기열·포화 영역의 권장 도구로 둔 통합 시뮬레이터를 새 seed·새 N에서 blind로 검증하기 위해 plan·예측((1) 운영 비용 sim, (2) 원래 비용 sim, (3) v1 참고)·영 예측기·판정 기준·순서·판정 스크립트를 측정 전에 commit한다. 기준은 [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) 개정 2의 §5.1·5.2·5.3·5.6 그대로(skill 0.5×) + "(1)이 (2)보다 재사용 MAE와 비 오차 합이 모두 작다". 문서 [SIMBLIND_PREREG.md](SIMBLIND_PREREG.md). 측정·판정은 다음 TASK.

**측정 0.**

## 배경

- [TASK92](TASK92.md) — 운영 조건 step 비용(`OPCOST_SIM.json`)
- [TASK86](TASK86.md)·[TASK87](TASK87.md) — 고부하 blind cell 절차와 결과(sim §5.1 MAE 0.013)
- [TASK89](TASK89.md) — 통합 시뮬레이터(`simulate()` dispatch, descriptor 의미론)
- 사용자 결정(2026-10-02): N = 13·17·20 측정, N = 20 BASE는 §5.1과 skill 계산에서 제외("정보 없음"), 비용 비 분모로는 사용, 세 N 모두 측정 전 예측 commit

## 시작 상태

- HEAD `f812705`(TASK92 개정 2), 미commit: N = 13·20 plan과 `make_simblind_plans.py`(이 TASK 앞부분에서 생성), `paper/RESULTS_INDEX.md`(작업 D, 별도 commit 예정), `.idea/`

## 수행 내용

1. **N 선택**: 지시문의 N = 13·20 plan을 만들고 sim 예측을 보니 N = 20 BASE 재사용 0.001 — §5.1에 정보가 없다. 대안 N(17·18, scratch plan seed 20261900 + 10N + r, 미commit)의 sim 값만 보고 사용자에게 선택지를 물었다(관측은 보지 않음). 사용자 결정은 위.
2. N = 17 plan: 규칙 seed 20261570–74의 첫 값이 `ORDER_HI` 순서 seed(20261570)와 같아 **20261575–79**. `make_simblind_plans.py`가 기존 N = 13·20 파일을 다시 만들어 byte 대조(같음) 후 15 plan의 `INDEX_SIM.json`을 썼다(N = 13·20 항목은 이전 index와 동일).
3. 예측 `predict_simblind.py`: (1) 운영 비용으로 시간 진행 + 원래 비용으로 가격, (2) 원래 비용(= `predict_v11.sim_plan`; N = 13 plan 하나에서 BASE·TUNED device 시간·재사용 정확 일치 확인), (3) v1(`in_scope` = N ≤ 동시 실행 상한).
4. 영 예측기 `null_predictors_sim.py`: N = 13 = Table I 행 12·16 합산(TASK86 N = 14 규칙, 분포 동일 확인), N = 17·20 = 행 16(위 행 없음).
5. 순서 `make_simblind_order.py`(seed 20261595), 구동 `run_simblind.sh`(= `run_hiload.sh`, 순서 파일만 다름), `mt_check.py` index에 `INDEX_SIM.json` 추가.
6. 판정 `simblind_analyze.py`(= `hiload_analyze.py` 구조, 9 cell, §5.1 8 cell, §5.2 강화 5/6, (1) 대 (2), v1 범위 안 참고값). **가짜 run**(TASK87 run의 N = 14 → 13, 16 → 17·20 tag symlink)으로 코드 경로만 시험했다 — 값 무의미, 45 lifecycle·`no_information`·cell 수 확인.

## 변경된 파일

- `experiments/npu/stage3/{make_simblind_plans.py, predict_simblind.py, null_predictors_sim.py, make_simblind_order.py, run_simblind.sh, simblind_analyze.py}`(신규), `mt_check.py`(index 1줄)
- `experiments/npu/stage3/plans/main/`: `main-n{13,17,20}-r{0..4}.json`, `INDEX_SIM.json`, `PREDICTIONS_SIM.json`, `NULL_PREDICTORS_SIM.json`, `ORDER_SIM.json`(`OPCOST_SIM.json`은 TASK92)
- `docs/research/SIMBLIND_PREREG.md`, `docs/research/TASK93.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/make_simblind_plans.py
cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 predict_simblind.py \
    --output /home/rebel/continuum-npu/results/npu/stage3/predict/simblind_predictions.json && cd -
cp results/npu/stage3/predict/simblind_predictions.json experiments/npu/stage3/plans/main/PREDICTIONS_SIM.json
env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors_sim.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS_SIM.json
env -u PYTHONPATH python3 experiments/npu/stage3/make_simblind_order.py
# 측정 (다음 TASK)
bash /home/rebel/continuum-npu/experiments/npu/stage3/run_simblind.sh /home/rebel/continuum-npu/results/npu/stage3/20261002-simblind
```

## 결과

예측 표는 [SIMBLIND_PREREG.md](SIMBLIND_PREREG.md) §3. 요약:

- BASE 재사용 (1)/(2): N = 13 0.427/0.461, N = 17 0.068/0.053, N = 20 0.000/0.001(정보 없음). batch 16 구성: N = 13 0.83, N = 17 0.74–0.76, N = 20 0.61–0.63.
- 비 (1): N = 13 0.890·0.883, N = 17 0.745·0.718, N = 20 0.687·0.669 (BATCHONLY·TUNED). (2)와의 차 ≤ 0.013.
- v1(참고)은 N ≥ 17에서 batch 16 재사용을 0.39–0.71로 낮게, 비를 0.80–0.88로 높게 예측해 sim과 크게 다르다 — 범위 밖 표시.
- 시뮬레이터 대기(요청당 평균): BASE 0.25 / 1.82 / 3.72 s, batch 16 0.02–0.07 s.

## 핵심 발견

1. (1)과 (2)의 예측 차이가 작다(재사용 ≤ 0.034, 비 ≤ 0.013) — [TASK92](TASK92.md)에서 운영 비용이 통제 비용과 거의 같았기 때문. 추가 확증 "(1) 대 (2)"는 두 예측기를 가르기 어려울 것으로 사전 예측했다.
2. N = 17·20은 batch 16 구성도 N > 동시 실행 상한인 첫 측정이다(이전 blind cell은 N ≤ 16).

## 해석

- 사전 예측(기준 아님): §5.1 PASS 쪽, §5.2 기본 기준 FAIL 쪽(구성 효과 과소 예측이 TASK87과 같이 남을 것), §5.3 PASS, §5.6 PASS 쪽, (1) 대 (2) FAIL 쪽.

## 확인되지 않은 사항

- §5.6의 N = 20 BASE 포함 여부 — 사용자 결정의 "skill 계산 제외"를 재사용 skill로 해석했다(Advisor 확인 사항).
- v1 "범위 밖" 규칙(N > 동시 실행 상한)은 batch 16 구성의 N = 17·20처럼 대기가 작은(0.04–0.07 s) cell도 범위 밖으로 둔다.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음(기존 절차 그대로).

## 다음 작업

- 측정(45 lifecycle)과 일괄 판정 — 다음 TASK.

## 재현 정보

- 선등록 commit: 이 TASK의 commit(측정 시작 전). 측정 시작 시각은 다음 TASK에 기록.
- 고정 파일 SHA256: `INDEX_SIM.json` `395d034ddf319128…`, `PREDICTIONS_SIM.json` `6867e9efe8fbdc4c…`(= `results/npu/stage3/predict/simblind_predictions.json` byte 동일), `NULL_PREDICTORS_SIM.json` `fee1a97cb5467f52…`, `ORDER_SIM.json` `0ad6a4a4d11cd461…`, `OPCOST_SIM.json` `29b96b8a14850f6c…`, `predict_simblind.py` `655f279a24723e32…`, `simblind_analyze.py` `c80e09a655f7fe04…`, `run_simblind.sh` `7fcaa1856477935f…`.
- package: vllm 0.22.0+cpu, vllm-rbln 0.11.1(patched), Qwen3-4B artifact 3종(새 compile 없음).
