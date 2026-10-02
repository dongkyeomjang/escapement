# 해석적 모형 v1.1 명세 — B1 생존의 대기열·부하 결합

작성: 2026-10-01, [TASK85](TASK85.md) (Advisor 지시문 06 작업 C). 이전 명세: [MODEL_V0.md](MODEL_V0.md), [MODEL_V1.md](MODEL_V1.md). 코드: [`src/continuum/model/survival_v11.py`](../../src/continuum/model/survival_v11.py), 분석 경로 [`experiments/npu/stage3/mt_predict_v11.py`](../../experiments/npu/stage3/mt_predict_v11.py).

**v1.1은 [TASK82](TASK82.md) N = 12 데이터(개발 집합으로 선언)를 본 뒤 만든 모형이다.** 그 데이터에서의 성적은 개발 집합 성적이지 검증이 아니다. N = 6·8·10 관측은 개발에 쓰지 않았다. blind 검증은 새 N = 14·16 cell에서 한다([TASK86](TASK86.md)).

---

## 0. B2는 바꾸지 않는다

지시문 06 §5.1이 권고한 출발점 — 서비스율 `μ(min(n, M))`인 부하 의존 station, 초과분 FCFS 대기 — 은 **v0부터 B2가 이미 쓰던 형태**다(`occupancy._distribution`, [MODEL_V0.md](MODEL_V0.md) B2 (i) `r(n) = min(n, M)`). N > M에서 무감응성이 깨지는 근사라는 점도 v0 명세에 적혀 있다. v1.1은 B2를 그대로 두고, **B2가 가진 대기열 상태를 B1 생존에 전달**하는 부분을 바꾼다. B2의 한계(아래 §5)는 v1.1 범위 밖으로 남긴다.

## 1. v1이 대기열에서 틀린 곳 (개발 집합 진단)

N = 12 BASE(M = 8), 재도착 918건, 정확 추적기 918/918 일치. v1 예측 0.404 대 관측 0.484.

| T 할당 시 older active `a0` | n | 관측 생존 | v1 (기록 상태) | 창 안 할당(관측 / λ 기대) |
|---|---|---|---|---|
| 2 | 69 | 0.78 | 0.52 | 7.2 / 9.3 |
| 4 | 120 | 0.72 | 0.46 | 8.8 / 9.3 |
| 6 | 133 | 0.48 | 0.39 | 11.7 / 11.3 |
| 7 (다른 slot 전부 running) | 314 | **0.18** | **0.44** | 13.1 / 11.7 |

v1의 오차는 **두 방향으로 상쇄**하고 있었다. 부하가 낮을 때 할당은 λ보다 적고(생존 과소 예측), 가득 찼을 때는 많고 대기가 길다(과대 예측). 원인은 셋이다.

1. **부하 지속성 — gap 모양.** plan의 gap은 중앙 0.12–0.18 s, 평균 3.3–4.4 s, CV ≈ 2.7, 12.8 %가 정확히 0(세션 갱신)이다. 막 끝난 세션은 새 gap을 뽑아 대개 1 s 안에 돌아오고, 이미 밖에 있는 세션은 길이 편향으로 긴 gap 안에 있다. 그래서 **지금 엔진 안에 있는 세션이 이후 할당의 대부분을 낸다**. 지수 gap은 이 방향을 거꾸로 만든다(한가한 순간 = 곧 돌아올 세션이 많음).
2. **결합(coupling).** 대기열이 있으면 할당은 running 요청이 끝나는 순간에 일어난다. 끝난 요청이 T보다 오래됐으면 그 항목이 가장 오래된 inactive라 할당이 곧바로 가져가므로 T에게 여유를 주지 않는다. v1은 release와 할당을 독립 사건으로 두어 여유를 계산한다.
3. **대기.** T와 재도착 R이 자리를 기다리고, R 앞의 대기 할당은 R의 lookup 전에 모두 T에 청구된다.

추가로 plan 간 이질성이 크다(BASE 관측 r0 0.708 대 r1 0.286, plan 평균 gap 4.6 대 2.1 s) — pooled 통계 하나로는 이 비선형을 평균낼 수 없다.

## 2. 수식 — 부하와 결합된 흡수 연쇄

**상태**: 다른 세션 중 엔진 안(running 또는 대기) `m`, gap 위상 `k`에 있는 수 `n_k`(합 `N − 1 − m`), pool의 `(a, d)`(v1과 같다: T보다 오래된 active·inactive 항목 수, pool은 가득). T가 running이면 다른 세션에게 남은 자리 `M_T = M − 1`, 아니면 `M`. running `R = min(m, M_T)`, 나머지는 FCFS 대기.

**gap 법칙**: 확률 `z`로 0(즉시 복귀), 아니면 확률 `p_k`로 평균 `θ_k`인 지수 위상(hyperexponential). plan의 gap에 zero atom 수 세기 + 지수 혼합 EM(분위 시작, 결정론적)으로 맞춘다. EM은 표본 평균을 보존하므로 `Z = (1 − z) Σ p_k θ_k`는 B2의 `think_mean_s`와 같다.

**전이** (균일화로 적분):

| 사건 | 율 | 효과 |
|---|---|---|
| gap 위상 k에서 복귀 | `n_k / θ_k` | `m + 1`. 빈 자리가 있으면 admission → 할당(d-rule), 없으면 대기 |
| running 다른 요청 완료 | `R · c(r)`, `c(r) = φ / (G · t_step(r))`(B2의 PS 율, `r` = 전체 running) | older(확률 `p_old`)면 `(a, d) → (a − 1, d + 1)`. 대기 머리가 있으면 곧바로 할당(d-rule). 완료한 세션은 확률 `z`로 즉시 복귀(자리 있으면 할당, 없으면 대기), 아니면 위상 k로 |
| 할당(d-rule) | — | `d > 0` → `d − 1`; `d = 0`이고 T active → 더 새 inactive가 나감; `d = 0`이고 T inactive → **T 축출(흡수)** |

**완료 순서** `p_old`: `random`(지수 서비스: `a / R`) 또는 **`admission`**(서비스 길이가 비슷한 PS에서 먼저 들어온 요청이 먼저 끝남: `1{a > 0}`). 생성 길이가 U(32, 256)(CV ≈ 0.45)인 이 부하에서 `admission`이 물리적으로 가깝고, 개발 집합에서도 그쪽이 맞았다(§4).

**T의 역사**:

1. T 도착: 다른 세션의 상태는 arrival theorem — `m ~ π_{N−1}`(B2, `occupancy.others_in_engine_at_arrival`), gap 위상은 시간 몫 `p_k θ_k / Σ p_j θ_j`의 다항분포(지연 station의 곱 형태는 gap 법칙에 무감응).
2. `m < M`이면 즉시 할당: `a0 = m`, `d0 = C − 1 − m`. 아니면 대기(뒤에 오는 복귀는 T 뒤에 선다, 매입 연쇄로 admission 시점의 `(m, n)` 분포를 구함) 후 할당: `a0 = M − 1`, `d0 = C − M`.
3. running `s_active` 동안(결정론적, v1과 같은 `E[P] + (G − 1)·t_step(n̄)/φ`): T 보호.
4. T 완료: 대기가 있으면 대기 머리가 곧바로 할당(T inactive).
5. idle(T의 gap, 표본별 결정론적): T 취약.
6. R 복귀: 자리가 있으면 즉시, 없으면 대기 `m − M`명 뒤. 앞선 대기 할당마다 d-rule, 기판이 할당 후 조회(`resume_allocates_first`)면 R의 할당도 1회.

**분석 경로**: v1의 재사용–prefill 고정점(`mt_predict.analytic`)과 같다 — 생존만 위 연쇄로 바꾼다. **plan별로** 계산해 cell 값을 plan 평균으로 낸다(재사용률, turn당 device time, padding, h).

## 3. 입력과 출처 층

| 입력 | 출처 | 층(값) |
|---|---|---|
| `C` | descriptor v2 `reuse_pool.capacity_units` | `stack` |
| `M` | descriptor v2 `admission.max_running` | `stack` |
| 할당·조회 순서 | `semantics.resume_allocates_first` | `stack` |
| 축출 규칙(d-rule) | `layers[reuse].eviction_order = allocation_fifo`, `evictable_when = immediate`, `intra_request_loss = all_or_nothing` — 아니면 **거부** | 규칙 형태 `universal`(FIFO 대기열 산술) |
| `t_step(r)`, `E[P]` | descriptor 비용 모형 | `silicon` |
| `φ`, `π_{N−1}` | B2 | `silicon` × workload |
| gap 법칙(z, p, θ), G | plan(workload) | — |
| 완료 순서 | 모형 선택(`admission`) | 가정 |

코드에 가속기 이름이나 기판 상수가 없다(기판 중립). **범위**: allocation-FIFO pool만. release-ordered LRU block pool(GPU)은 decode 중 block 소비·hit touch가 있어 별도 형태가 필요하며, `check_substrate`가 거부한다(결정 요청).

## 4. 개발 집합 (N = 12) — 판정 없음

변형 선택 규칙(개발 전에 정한 것이 아니라 개발 과정의 규칙): **재사용 MAE 최소**(v1.1이 바꾸는 것은 생존이므로). 모든 변형과 v1:

| 변형 | BASE 재사용 (관측 0.484) | BATCHONLY / TUNED 재사용 (0.855 / 0.859) | 비 BATCHONLY / TUNED (0.844 / 0.830) | 재사용 MAE | 비 오차 합 |
|---|---|---|---|---|---|
| v1 | 0.404 | 0.834 / 0.837 | 0.891 / 0.875 | 0.041 | 0.092 |
| random, 지수(K=1, zero atom) pooled / per-plan | 0.261 / 0.262 | 0.838–0.840 | 0.854 / 0.840, 0.852 / 0.838 | 0.086 / 0.085 | 0.020 / 0.016 |
| random, K=2 pooled / per-plan | 0.284 / 0.282 | 0.837–0.839 | 0.860 / 0.845, 0.857 / 0.843 | 0.080 / 0.080 | 0.031 / 0.026 |
| random, K=3 pooled / per-plan | 0.290 / 0.288 | 0.837–0.839 | 0.861 / 0.847, 0.858 / 0.844 | 0.077 / 0.078 | 0.034 / 0.029 |
| admission, K=2 pooled / per-plan | 0.427 / 0.430 | 0.840–0.842 | 0.895 / 0.880, 0.893 / 0.878 | 0.030 / 0.029 | 0.101 / 0.097 |
| **admission, K=3 per-plan (동결)** | **0.436** | 0.841 / 0.842 | 0.894 / 0.879 | **0.026** | 0.100 |
| admission, K=3 pooled | 0.433 | 0.840 / 0.842 | 0.896 / 0.881 | 0.028 | 0.104 |

h TVD(BASE / BATCHONLY / TUNED): v1 0.142 / 0.101 / 0.103, 동결 v1.1 0.114 / 0.091 / 0.096(plan 평균 효과, B2 자체는 같다).

**관찰**: 재사용을 맞히는 변형(admission)은 비용 비를 v1보다 약간 나쁘게 맞히고, 비용 비를 맞히는 변형(random)은 BASE 재사용을 크게 과소 예측한다. random의 비용 비 "개선"은 BASE 재사용을 너무 낮게 봐서 BASE를 비싸게 예측한 결과라 옳은 이유가 아니다. 비용 비의 남은 오차는 B2 쪽이다 — batch 16 구성에서 평균 running을 과소(해석 4.6–4.7 대 관측 5.0–5.2)해 TUNED·BATCHONLY 비용을 BASE보다 더 크게 과대(7 % 대 5 %) 예측한다. 대기열이 없는 구성의 문제이므로 v1.1의 대기열 항이 고칠 수 없다.

**정확성 self-check**(`tests/test_survival_v11.py`): 같은 가정의 항목 단위 Monte Carlo와 8 경우 모두 |차| ≤ 0.012(허용 0.02), gap 법칙 적합의 평균 보존, LRU 거부.

## 5. v1.1이 예측하지 않는 것

- B2의 한계: N > M의 FCFS 비무감응, 배타 prefill 동기화, batch 16 구성의 평균 running 과소(개발 집합).
- 완료 순서의 중간 경우(서비스 CV가 0도 1도 아닌 경우의 정확한 확률).
- 다른 세션 gap의 turn 간 상관, plan 안의 비정상성(세션 구성 단위의 느린 요동, [TASK83](TASK83.md)).
- LRU block pool의 대기열 형태.
- pre-evict dummy의 시점 이동(v1 가정 3 그대로).

## 6. n ≤ M 영역에서 v1과의 차이

v1.1은 v1을 **바꾸는 확장**이다. 대기열이 없어도(N ≤ M) 할당 흐름이 부하 상태와 gap 위상에 의존하기 때문이다(v1은 상수 Poisson). 차이의 크기는 구성에 따라 갈린다([TASK85](TASK85.md), 예측만 비교):

| N | BASE(M = 8) 재사용 v1 → v1.1 | batch 16 구성 재사용 v1 → v1.1 | 비 BATCHONLY / TUNED v1 → v1.1 |
|---|---|---|---|
| 6 | 0.825 → 0.833 | 0.915 → 0.914 | 0.983 / 0.988 → 0.985 / 0.989 |
| 8 | 0.736 → 0.770 | 0.882 → 0.882 | 0.972 / 0.969 → 0.978 / 0.975 (DP 0.965 → 0.971) |
| 10 | 0.634 → 0.697 | 0.858 → 0.859 | 0.953 / 0.945 → 0.966 / 0.958 |

- **batch 16 구성(n ≤ M 항상)**: 재사용 차 ≤ 0.002 — 용량(16)이 동시 running보다 훨씬 커서 할당 흐름의 모양이 생존을 거의 바꾸지 않는다.
- **BASE**: N = 6에서도 대기가 드물게 생기고(M = 8, 동시 running 분포의 꼬리), 부하 지속성이 v1의 상쇄 오차를 푼다. 차이는 N과 함께 커진다(+0.008 → +0.034 → +0.063).
- 비의 차이는 BASE 재사용 예측이 올라가 BASE 비용이 내려간 결과다.

사후 대조(개발에 쓰지 않았으나 이미 관측된 N = 6·8·10 확증 cell, **blind 아님**): 재사용 MAE v1 0.0142 → v1.1 **0.0052**, 비용 비 Σ|예측 − m| v1 0.0483 → v1.1 **0.0254**.

## 7. v1.2 시도 — 동결하지 않음 ([TASK90](TASK90.md), 지시문 07)

- **B2 진단**: BASE 평균 running 과대의 주성분은 gap 분포 모양과 배타 prefill의 상호작용(N14·16 −0.40·−0.45, step 가중)이다. 지수 gap이면 B2 = 시뮬레이터.
- **B2 후보**(`occupancy_v12.py`, 배타 prefill을 명시한 엔진 Markov 연쇄)는 gap 모양에 무감응이라 개선 없음 — plan에서 정해지는 Markov 자유도로는 B2를 고칠 수 없었다.
- **완료 순서 중간 형태** `pairwise`(`ρ` = 0.74, plan의 decode 길이에서)는 BASE 재사용을 더 과소 예측(N14 −0.162).
- **동결 전 점검**: v1.2 후보 개발 집합 9 cell 중 8 cell이 허용치 절반 초과 → 동결 안 함, blind 미실행.
- v1.1 코드는 `pairwise` 옵션과 `_expm` 결정화가 추가됐고 기본 동작은 같다(`_expm`으로 마지막 자리가 실행마다 흔들리던 것만 고정).
