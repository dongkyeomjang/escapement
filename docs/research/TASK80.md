# TASK80 — multi-turn 본 실험 plan·blind 예측·판정 기준 선등록

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 04 작업 D. 본 실험의 전체 plan을 고정하고, 세 예측기(해석 v1, 시뮬레이터 기본, 시뮬레이터 관측 의미론)의 blind 예측과 판정 기준(제안)을 **본 측정 전에** commit한다. 본 측정은 지시문 05에서 한다.

**본 측정 0.**

## 배경

관련 TASK:

- [TASK77](TASK77.md) — runner·plan 생성·시뮬레이터 갱신 옵션
- [TASK78](TASK78.md) — DP 격자 선정(compile 보류)
- [TASK79](TASK79.md) — streaming 파일럿 `EQUIVALENT`
- [TASK73](TASK73.md)·[TASK74](TASK74.md) — 모형 v1, 시뮬레이터 의미론 스위치와 가설 H-sim의 출처

## 시작 상태

- plan·예측 계산: HEAD `c714b03`에서 파일럿 측정 중 수행(18:3x–18:5x). 예측 입력은 descriptor 상수와 plan뿐이며 파일럿 산출을 읽지 않았다.
- 선등록 commit 시점 HEAD `adad645`([TASK79](TASK79.md)).

## 수행 내용

1. `make_main_plans.py`로 plan 20개(N ∈ {6,8,10,12} × r 0–4, seed `20261400 + 10N + r`)를 생성하고 `INDEX.json`에 SHA256과 최대 context를 기록했다.
2. `predict_main.py`로 (N, 구성) × 세 예측기의 재사용률, h(n)·padding, turn당 decode·prefill·전체 A′, BASE 대비 비, 순위, W를 계산해 `PREDICTIONS.json`으로 고정했다. DP 격자는 compile 여부와 무관하게 네 N 모두 조건부로 등록했다.
3. [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md)에 측정 정의, 예측 요약, 판정 기준 제안(§5.1–5.8), 예산을 적어 commit했다.

## 변경된 파일

선등록 commit `eedf5ed`: `docs/research/MULTITURN_MAIN_PREREG.md`, `experiments/npu/stage3/plans/main/{main-n*-r*.json ×20, INDEX.json, PREDICTIONS.json, DP_GRIDS.json}`

기록 commit: `docs/research/TASK80.md`, `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/make_main_plans.py
env -u PYTHONPATH python3 experiments/npu/stage3/predict_main.py \
  --dp-grids experiments/npu/stage3/plans/main/DP_GRIDS.json \
  --output results/npu/stage3/predict/main_predictions.json
```

## 결과

- plan 20개: `cycle_s` 4.955–6.560 s, 최대 context 3,022–3,309 token(상한 8,192 안). `INDEX.json` SHA256 `f542e971…d471dcadd`, `PREDICTIONS.json` SHA256 `0c32701c…6da3fea`.
- **예측 요약**(BASE 대비 비, 해석 / sim 기본): N=6 BATCHONLY 0.983 / 0.994, TUNED 0.988 / 0.990; N=8 0.972 / 0.983, 0.969 / 0.984; N=10 0.953 / 0.969, 0.945 / 0.959; N=12 0.891 / 0.876, 0.875 / 0.857. DP/TUNED(해석) 0.992–0.998.
- **세 예측기가 크게 갈리는 cell**: N=12 BASE 재사용(0.404 / 0.485 / 0.507), N=6 BATCHONLY 비(0.983 대 0.994), N=6·12의 1위 구성(해석 DP, 시뮬 TUNED). sim 기본과 sim 관측은 N ≤ 8에서 같다.
- 판정 기준 제안 전문은 [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) §5.

- `requested_condition` 등: 해당 없음(측정 없음)

## 핵심 발견

1. **`stack`** — **steady-state multi-turn에서 모형이 예측하는 구성 간 차이는 원고 조건보다 작다**(N=6·8에서 BASE 대비 1–3 %, 원고 N=8 X ≈ +10 %). tool gap이 길어 동시 running이 낮고, `batch_size` 16이 살리는 캐시 손실(BASE 재사용 0.74–0.83)이 원고(9/24)보다 작기 때문이다. N이 커질수록(N=12 BASE 재사용 0.40–0.51) 차이가 커진다.

## 해석

- 구성 간 차이가 파일럿의 run 간 산포(짝 ratio 0.998–1.023)와 같은 자릿수라, §5.3 순위는 BASE를 포함한 쌍만 해소될 것으로 본다. 이것이 판정 기준을 "해소된 쌍만" 세도록 설계한 이유다.

## 확인되지 않은 사항

- DP 격자 compile 여부(Advisor 결정 대기, [TASK78](TASK78.md))
- 판정 기준(제안)의 채택 여부

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- base seed 숫자가 격자 선정(N=10)과 파일럿 사이에서 겹쳤다(세션 seed는 plan_id로 갈려 같은 세션은 없음). 앞으로 seed 범위를 N에 곱하지 않는 방식으로 잡을 것을 권고한다.

## 다음 작업

- Advisor 검토: 판정 기준 채택, DP compile 선택지, 측정 순서 → 지시문 05에서 본 측정.

## 재현 정보

- 위 명령. 산출 `results/npu/stage3/predict/main_predictions.json`(비추적)과 추적 사본 `plans/main/PREDICTIONS.json`이 byte 동일.
- **선등록 commit: `eedf5edb28b7caa98c5dfed7fc0c25530fb11a37` (2026-09-29 19:13:53 +0900). 본 측정은 아직 시작하지 않았다.**
