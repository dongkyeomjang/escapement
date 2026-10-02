# GTASK08 — GPU multi-turn 구성과 pool 크기의 blind 선정

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-03 작업 B.
- NPU의 BASE·BATCHONLY·TUNED에 대응하는 GPU 구성을 **측정 없이 모형으로** 정한다.
- 재사용률이 확증 N에서 0.4–0.85에 오도록 KV pool 크기와 N을 고른다.
- 모든 구성이 preemption 불가 조건을 만족하게 한다.
- 선정은 파일럿·측정보다 먼저 commit한다.

## 배경

- [GTASK07](GTASK07.md): 예측기 코드
- [GTASK05](GTASK05.md): step 비용
- [TASK78](../TASK78.md): NPU blind 격자 선정
- [TASK80](../TASK80.md) 발견 1: BASE 재사용이 0.74–0.83으로 높아 구성 차가 작았다.

## 시작 상태

branch `gpu-a6000`, HEAD `9af6af9`(GTASK07). 멀티턴 측정값은 없다.

## 수행 내용

1. 선정 규칙을 `select_configs.py` docstring에 먼저 적고 실행했다. 규칙 요지는 다음과 같다.
   1. 모든 구성은 `max_num_seqs` 8이다.
   2. preemption 불가 조건은 workload **최악** 요청(3,712 token = 232 block)으로 계산한다: `pool ≥ 1 + 8·232 = 1,857`.
   3. BASE는 pool 1,900, 격자는 기본값 (1,2,4,8,16)이다.
   4. 후보 N은 16–32(짝수)이고 N마다 선정 plan 3개를 쓴다(seed `20262100 + i`). BASE 재사용 예측(시뮬레이터 LRU와 해석, 각 두 bound)이 모두 [0.40, 0.85] 안이고 plan 간 spread ≤ 0.25인 N 중에서, 가장 작은 연속 세 N을 고른다.
   5. POOL은 가운데 N에서 재사용 ≤ 0.85인 가장 큰 pool이다.
   6. POOL+GRID는 POOL pool에 N별 B3 DP 격자(4 폭 ≤ 8, + 16)를 쓴다.
2. **첫 실행에서 규칙 5가 해 없음으로 멈췄다.**
   - BASE가 가운데 N(22)에서 이미 0.848이라, 더 큰 pool은 모두 0.85를 넘는다.
   - **개정 1**(측정 전, 측정값 없음)은 규칙 5의 상한만 0.90으로 완화한 규칙 5′다. 나머지 규칙은 그대로 두었다.
   - 개정 규칙을 정하기 전에 POOL 후보(2,200–3,600)를 시뮬레이터로 훑어본 사실도 기록한다.
   - 규칙 1–4와 6은 두 실행에서 같은 표를 냈다(결정적 계산).
3. 선정 plan 27개는 seed로 재생성할 수 있어 git에 넣지 않았다(`results/gpu/multiturn/selection_plans/`, 내용 SHA256은 `selection.json`에 있다).

## 변경된 파일

- `experiments/gpu/multiturn/select_configs.py`, `experiments/gpu/multiturn/configs.py`, `experiments/gpu/multiturn/selection/selection.json` (신규)
- `docs/research/gpu/GTASK08.md` (신규), `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/select_configs.py \
  --out-dir <abs>/experiments/gpu/multiturn/selection --plans-dir <abs>/results/gpu/multiturn/selection_plans
```

Population: 선정 plan 27개(N 9개 × 3). 평가 구간 요청은 시뮬레이터가 정한다.
Source: 예측기(측정 아님).
단위: 재사용은 turn ≥ 1 요청 비율, 비용은 ms/turn(A′-GPU 정의).

## 결과

### BASE (pool 1,900) 예측 — N별

| N | sim LRU 재사용 lo / hi | plan 간 spread | 해석 재사용 | sim FIFO 재사용 | sim ms/turn | 해석 평균 running | 판정 |
|---|---|---|---|---|---|---|---|
| 16 | 0.908 / 0.913 | 0.03 | 0.887 | 0.855 | 375 | 5.23 | 범위 밖 |
| 18 | 0.881 / 0.878 | 0.01 | 0.859 | 0.779 | 315 | 6.40 | 범위 밖 |
| **20** | 0.845 / 0.827 | 0.09 | 0.849 | 0.715 | 303 | 7.12 | **가능** |
| **22** | 0.848 / 0.848 | 0.08 | 0.830 | 0.714 | 286 | 7.45 | **가능** |
| **24** | 0.779 / 0.766 | 0.07 | 0.804 | 0.608 | 282 | 7.73 | **가능** |
| 26 | **0.366** / 0.355 | **0.31** | 0.779 | 0.436 | 332 | 7.90 | 붕괴 |
| 28 | 0.197 / 0.183 | 0.35 | 0.746 | 0.296 | 353 | 7.97 | 붕괴 |
| 30 | 0.273 / 0.297 | 0.24 | 0.000 | 0.364 | 333 | 8.00 | 붕괴 |
| 32 | 0.061 / 0.038 | 0.18 | 0.000 | 0.204 | 365 | 8.00 | 붕괴 |

### 선정

| 구성 | `--num-gpu-blocks-override` | `--max-num-seqs` | capture 격자 | 가운데 N(22) 예측 재사용 (sim lo / 해석) |
|---|---|---|---|---|
| BASE | 1,900 | 8 | (1,2,4,8,16) | 0.848 / 0.830 |
| POOL | 2,300 | 8 | (1,2,4,8,16) | 0.887 / 0.866 |
| POOL+GRID | 2,300 | 8 | **(1,5,7,8,16)** (N=20·22·24 모두) | — |

- **확증 N = 20, 22, 24.**
- **preemption 불가 조건**: 요구 1,857 block ≤ BASE 1,900(여유 43 block)이다. 선정 plan의 실제 최대 요청은 3,287 token = 206 block이므로, 실제 요구는 1 + 8·206 = 1,649 block이다.
- **규칙 5**(상한 0.85)의 해는 없었다(`rule5_solutions: []`). 규칙 5′(상한 0.90)는 2,300을 골랐다.
- **POOL+GRID 격자의 근거**: 해석 B2가 예측한 step 가중 h(n)은 n = 8에 59 %(N=20)–85 %(N=24)가 몰려 있다. DP는 2·4를 버리고 5·7을 넣는다.

## 핵심 발견

1. **`class`** — **preemption을 구조적으로 막는 조건(pool ≥ `max_num_seqs` × 최대 요청)을 지키면, 재사용 압력은 engine이 running 상한에 가까울 때만 생긴다.**
   - 이 부하에서 BASE 재사용이 0.85 아래로 내려가는 N은 평균 running이 7.1–7.7(상한 8의 89–97 %)인 곳뿐이었다.
   - 기전: 세션 평균 context는 최대 요청의 약 2/3이다. 그래서 pool이 모든 running 요청의 최대 수요를 덮으면, 세션 수가 상한의 약 1.5배를 넘을 때까지 캐시가 거의 다 살아남는다. tool gap 중앙값(0.16 s)이 짧아 LRU 앞쪽에 머무는 시간도 짧다.
   - `class`로 보는 근거는 이 성질이 preemption 회피 조건과 block pool LRU의 형태에서 나오기 때문이다. 수치 1,857·N=20–24는 `stack`이다.
2. **`class`** — **포화를 넘으면 재사용이 급격히 붕괴한다**(시뮬레이터: N=24 0.78 → N=26 0.37, plan 간 spread 0.07 → 0.31).
   - 되먹임: miss → prefill 증가 → 대기 증가 → idle 시간 증가 → 추가 손실.
   - **해석 모형은 이 붕괴를 예측하지 못한다**(N=26에서 0.78). B2의 FCFS 대기 근사와 평균장 생존식에 이 되먹임이 없다.
   - N=26은 확증에서 빠졌지만, 두 예측기가 가장 크게 갈리는 cell이다.
3. **`stack`** — **축출 순서(해제 순서 LRU 대 할당 순서 FIFO)가 이 부하에서 재사용을 0.13–0.17 가른다**(BASE, N=20–24).
   - GTASK04의 순차 프로토콜과 달리, multi-turn에서는 LRU와 FIFO가 구별 가능한 예측을 낸다.

## 해석

- 확증 cell이 모두 포화 근처라 B2의 가정(n ≤ M)이 부분적으로 깨지는 구간이다. NPU에서는 N=12 한 곳만 그런 경계였다. GPU 확증 cell의 해석 예측은 이 제약 아래의 검증이 된다.
- POOL과 BASE의 예측 비용 차는 2–5 %다(POOL 후보 탐색, 시뮬레이터). NPU 파일럿의 run 간 산포(1–2 %)와 비슷한 크기라 구성 효과가 해상도 경계에 있다. 예측은 GTASK09에서 확정한다.
- POOL+GRID 격자의 비용 이득은 GTASK05의 평탄한 `F[b]`(13.17–13.37 ms, b ≤ 8) 때문에 매우 작을 것이다.

## 확인되지 않은 사항

- 선정은 모형 예측뿐이다. 실제 재사용률 범위는 측정 전 `UNKNOWN`이다.
- 해석 모형이 N ≥ 30에서 재사용 0.000을 낸다. B2 포화(running 8.00)에서 반복이 0으로 수렴한 것으로 보이며, 원인은 확인하지 않았다(확증 범위 밖).

## 실패 / 무효 시도

- **규칙 5 해 없음**(첫 실행). 원 규칙의 실패를 이 문서와 `selection.json`(`rule5_solutions`, `rule5_ceiling` 0.85, `rule5p_ceiling` 0.90)에 기록했다. 첫 실행 로그는 `results/gpu/multiturn/selection_run1/`에 있다.

## 연구 원칙에 미치는 영향

- 선정 규칙의 상한을 정할 때 BASE가 이미 상한 근처인지 먼저 확인해야 한다. 규칙 5는 BASE 예측을 보기 전에 정해 해가 없었다.

## 다음 작업

GTASK09(본 실험 plan·예측·판정 기준 선등록). Advisor 결정 후보는 다음과 같다.
- N=26 붕괴 cell을 탐색으로 추가할지(15 lifecycle)
- `max_num_seqs` 16 구성(NPU BATCHONLY 대응; pool ≥ 3,313 필요, 재사용 > 0.9 예측)을 넣을지

## 재현 정보

- 위 명령. 산출 `selection.json` SHA256 `11eecd58…c7065c`.
- 입력: GTASK05 `summary.json`(`709f5941…`)의 값(`gpu_cost.py`), TraceLab `summary.json` SHA256 `25bb1b0f…`
- 선등록: 해당 없음(측정 없음). 선정 commit이 파일럿·측정보다 먼저다.
