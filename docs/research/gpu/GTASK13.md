# GTASK13 — 시간 척도 가설: step 비용을 dispatch 채널로 바꾼 sim LRU (개발 집합)

## 상태

DONE

## 날짜

2026-10-01

## 목적

GPU 지시문 G-05 작업 B. **개발 집합 분석이며 판정하지 않는다.**
- 관측(GTASK11)을 본 뒤 그 관측에서 얻은 비율로 시뮬레이터를 고친 결과다.
- 이 변형의 blind 검증은 v1.1과 함께 새 붕괴 영역 cell에서 한다(G-04 §6).
- 질문: sim LRU가 실제보다 빠른 step 비용으로 시간을 진행해서 붕괴를 과소 예측했는가(GTASK11 발견 4)?

## 배경

- [GTASK11](GTASK11.md): direct/price lifecycle 중앙 1.131. sim LRU N24 BASE +0.084, N26 BASE +0.207 과대
- [GTASK12](GTASK12.md): 의미론은 맞다(사건 재생 16,794/16,794). 오차는 동역학에 있다.
- [GTASK15](GTASK15.md): lag 1 귀속에서 창 wall/price = 1.210, idle 조각 0

## 시작 상태

- HEAD `3ddbba8`(GTASK12). 정상성 방법 commit `f61b4fd`는 sim 실행 중에 들어갔다(이 작업과 무관)

## 수행 내용

1. **시뮬레이터의 시간 진행 비용을 코드로 확인했다.**
   - `gpu_mt_sim.simulate`는 step마다 `dur = gpu_cost.step_ms(decodes, prefill_tokens, grid, bound) / 1e3`만큼 시간을 진행한다(`gpu_mt_sim.py`의 step 끝 `now += dur`).
   - `gpu_cost.step_ms`는 GTASK05의 A′-GPU **가격 채널**이다: FULL `F[b] + g·n`(13.2–13.7 ms), mixed는 PIECEWISE 증분 [0, 1.5] ms 또는 eager 증분 표.
   - client 지연은 0이다. 다음 turn은 `완료 + gap_after_s`에 도착한다.
2. 변형 script `sim_timescale.py`를 만들었다.
   - `gpu_mt_sim.py`는 고치지 않았다. 호출 중에만 그 안의 `C`(cost module) 참조를 wrapper로 바꾼다.
   - 비용 지표는 언제나 원래 `gpu_cost`로 창 step을 다시 가격 매긴다. 관측 비용 비와 같은 가격 채널을 유지하기 위해서다.
   - GTASK09 plan(`gmain-n{N}-r{r}`) 그대로, `lo` bound, LRU
3. 변형 4종 × 11 cell × replicate 5 = 220 run을 세션과 분리해 실행했다(07:15–07:18 UTC).
   - `orig`: 가격 채널. **회귀: PREDICTIONS.json sim_lru/lo와 재사용·비용 비 차 0**(최대 2e−16)
   - `x1.131`: 모든 step × 1.131(지시문 방법 1, GTASK11 lifecycle 중앙)
   - `x1.210`: 모든 step × 1.210(보조; lag 1 귀속 창 wall/price, GTASK15)
   - `mode_dist`: step 계급별 관측 lag 1 dispatch/가격 비 분포에서 step마다 추출(지시문 방법 2; seed는 (N, 구성, r)로 고정)
   - step 계급은 `step_classes.py`에 있다. FULL decode, PIECEWISE 혼합, eager 혼합(p ≤ 128, ≤ 256, ≤ 512, ≤ 1024, > 1024)이다. 55 lifecycle 합산 분포이고 계급 중앙은 다음과 같다: FULL 1.217, PIECEWISE 1.506, eager p ≤ 128 1.328, p ≤ 256 1.563, p ≤ 512 1.441, p ≤ 1024 1.012, p > 1024 1.079.
4. `timescale_report.py`로 GTASK11 관측(`verdict.json`)과 대조했다.

## 변경된 파일

- `experiments/gpu/multiturn/{sim_timescale.py, step_classes.py, timescale_report.py, obs_dynamics.py}`(신규)
- `docs/research/gpu/GTASK13.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
D=<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics
PY="env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python"
$PY experiments/gpu/multiturn/obs_dynamics.py --run-dir $D/.. --out $D/obs.json
$PY experiments/gpu/multiturn/sim_timescale.py --obs $D/obs.json --out $D/sim.json
python3 experiments/gpu/multiturn/timescale_report.py --sim $D/sim.json --verdict $D/../verdict.json \
  --pred experiments/gpu/multiturn/plans/PREDICTIONS.json --out $D/timescale_report.json
```

- Population: 재사용은 cell별 turn ≥ 1 요청 r0–r4 합산(GTASK11 §5.1 정의). 비용 비는 pooled `ratio_to_base`(PREDICTIONS.json과 같은 정의).
- Source: sim 출력. 관측은 GTASK11 `verdict.json`.
- Unit: 비율.

## 결과 (개발 집합, 판정 없음)

### 붕괴 곡선 (BASE 재사용, N = 20–26)

| N | 관측 | orig | x1.131 | x1.210 | mode_dist |
|---|---|---|---|---|---|
| 20 | 0.856 | 0.857 | 0.862 | 0.860 | 0.850 |
| 22 | 0.817 | 0.849 | 0.843 | 0.825 | 0.834 |
| 24 | **0.669** | 0.753 | 0.724 | 0.683 | 0.695 |
| 26 | **0.450** | 0.657 | 0.521 | 0.459 | 0.483 |

POOL은 모든 변형에서 관측과 ±0.03 안이다(N26 POOL: 관측 0.804, orig 0.833, x1.131 0.812, x1.210 0.800, mode_dist 0.816).

### 요약 지표

| 변형 | N24 BASE 차 | N26 BASE 차 | 확증 9 cell MAE | 평균 부호 오차 | 비용 비 Σ\|오차\| (6 cell) | N24 POOL−BASE (관측 0.183) |
|---|---|---|---|---|---|---|
| orig | +0.084 | +0.207 | 0.0173 | +0.013 | 0.0745 | 0.108 |
| x1.131 | +0.055 | +0.071 | 0.0111 | +0.009 | **0.0127** | 0.130 |
| x1.210 | **+0.014** | **+0.009** | **0.0047** | +0.004 | 0.0741 | 0.174 |
| mode_dist | +0.026 | +0.033 | 0.0071 | +0.005 | 0.0561 | 0.165 |

- **비용 비 부호**: x1.131은 6 cell 모두 ±0.004 안이다. x1.210과 mode_dist는 효과를 과대 예측한다(N24 POOL m 0.918·0.919 대 관측 0.940).
- **N26 POOL/BASE 비**: 관측 0.899, orig 0.939, x1.131 0.900, x1.210 0.878, mode_dist 0.879

### 발견 4 차이의 설명 비율

(orig 오차 − 변형 오차) / orig 오차

| cell | orig 오차 | x1.131 | x1.210 | mode_dist |
|---|---|---|---|---|
| N22 BASE | +0.032 | 18 % | 76 % | 47 % |
| N24 BASE | +0.084 | 34 % | 83 % | 70 % |
| N26 BASE | +0.207 | 66 % | 96 % | 84 % |

## 핵심 발견

1. **`stack`** — **sim LRU는 가격 채널(GTASK05 FULL 13.2–13.7 ms)로 시간을 진행하고, 이 부하에서 실제 step은 그보다 약 21 % 길다**(창 wall/price 1.210, FULL decode 16.5 ms). step 비용만 관측 수준으로 바꾸면 붕괴 과소 예측의 대부분이 사라진다: N26 BASE +0.207 → +0.009(x1.210)·+0.033(mode_dist). **개발 집합 결과**이며 비율을 같은 관측에서 얻었다.
2. **`class`** — **포화 근처에서 재사용은 step 시간에 비선형으로 민감하다.** 같은 21 % 연장이 N20에서는 재사용을 거의 바꾸지 않고(0.857 → 0.860) N26에서는 0.198 내린다. `class`인 근거: 부하가 용량에 가까울수록 step 연장이 대기열 길이를 늘리고, 대기가 idle 구간을 늘려 축출을 늘리는 되먹임은 용량 제한 캐시 + 대기열 구조에서 나온다([GTASK14](GTASK14.md)).
3. **`stack`** — **재사용과 비용 비가 서로 다른 척도를 가리킨다.** 재사용은 x1.210이, 비용 비는 x1.131이 가장 잘 맞는다(Σ 0.0127 대 0.0741). 한 척도의 전역 배율로는 둘을 함께 맞출 수 없다. step 계급마다 비율이 다르고(FULL 1.22, 큰 eager prefill 1.08) 구성마다 step 구성이 다르기 때문으로 보인다(가설).
4. **`stack`** — **지시문의 1.131은 실제 시간 척도를 과소 추정한 값이다.** lag 0 귀속과 cap이 큰 prefill step의 밀린 시간을 잘라냈다([GTASK15](GTASK15.md)). 시간 척도로는 lag 1 귀속 값(1.21)을 쓰는 것이 맞다.

## 해석

- 발견 4의 차이(0.08–0.21) 중 x1.131은 34–66 %, mode_dist는 70–84 %, x1.210은 83–96 %를 설명한다(N24·N26 BASE).
- 남는 차이는 작다(N24 BASE +0.014–0.026). mode_dist가 x1.210보다 덜 설명하는 이유는 확인하지 않았다. 후보는 계급별 비율의 상관 구조(연속 step의 비율이 서로 독립이 아님)와 sim의 step 구성이 관측과 다른 것이다.
- 비용 비에는 시간 척도 효과와 가격 채널 정의가 섞여 있다. 비용 비 개선을 위해 시간 척도를 따로 조정하면 개발 집합 과적합이 된다.

## 확인되지 않은 사항

- FULL decode step이 GTASK05 측정보다 22 % 긴 원인([GTASK15](GTASK15.md) 가설)
- 같은 비율이 다른 N·plan에서도 성립하는지(blind 검증 필요)

## 실패 / 무효 시도

- 첫 비용 비 집계는 per-replicate 비의 중앙값으로 계산했다(orig Σ 0.0987). PREDICTIONS.json·GTASK11 판정의 정의(pooled `ratio_to_base`)와 달라서 같은 정의로 다시 계산했다(orig Σ 0.0745 = GTASK11 0.075). 표는 pooled 정의다.

## 연구 원칙에 미치는 영향

- 시뮬레이터의 시간 진행 비용은 결과를 크게 바꾸는 입력이다. 사전 예측에는 **가격 채널이 아니라 실제 운영 부하에서의 step 시간**이 필요하다. 그 값은 측정 프로토콜(관측 장치 포함)에 따라 다를 수 있다.

## 다음 작업

- (Advisor 결정) blind 검증: v1.1 + 시간 척도 변형(x1.210, mode_dist)을 새 붕괴 영역 cell(새 seed, N = 26·28 등)에서 측정 전에 예측한다. 시간 척도 값은 이번 관측에서 동결한다.

## 재현 정보

- 개발 집합(관측 후 분석), 선등록 없음
- sim run 07:15:32–07:18:18 UTC. `sim_timescale.py` SHA256 `556ed1b0…`(실행본 = commit본)
- 산출(비추적): `results/gpu/multiturn/main/20260930T1411Z/dynamics/{obs.json, sim.json, timescale_report.json}`
- 입력: GTASK09 plan(PREDICTIONS.json SHA256 `1be9a991…`, 변경 없음), GTASK11 `verdict.json`
