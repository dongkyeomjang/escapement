# 해석적 모형 v1 명세 — B1 생존의 기준 의미론과 상태 변수 근사

작성: 2026-09-29, [TASK73](TASK73.md) (Advisor 지시문 03 작업 A). v0 명세: [MODEL_V0.md](MODEL_V0.md). v1은 **B1만** 바꾼다. B2(점유)·B3(격자)·B4(간섭)는 v0 그대로다.

코드: [`src/continuum/model/reference.py`](../../src/continuum/model/reference.py) (기준 의미론), [`src/continuum/model/survival_v1.py`](../../src/continuum/model/survival_v1.py) (상태 변수와 근사), descriptor 필드 `release_rule`·`dummy_mode`·`resume_allocates_first`.

**v1은 [TASK72](TASK72.md)의 데이터(R5′ 1,298 재도착)를 본 뒤 만든 모형이다.** 그 데이터에서의 성적(아래 A4)은 개발 집합 성적이지 검증이 아니다. blind 검증은 multi-turn steady-state 실험에서 한다.

---

## 1. 기준 의미론 (reference semantics)

**규칙.** 축출은 그 순간 pool에서 **가장 오래된 inactive 항목**을 제거한다. 따라서 대상 T는 창 안의 어떤 축출 순간에 **T가 inactive이고, T보다 오래된 현존 항목이 모두 active일 때, 그리고 그때만** 축출된다.

`FifoReplay`는 세 사건만 순서대로 재생한다.

| 사건 | 동작 |
|---|---|
| `alloc(key, session)` | 빈 slot이 없으면 먼저 축출(admission 경로). 자기 slot을 잡은 **뒤** 세션의 이전 항목을 조회(`allocate_before_lookup`) |
| `free(key)` | `release="immediate"`면 즉시 inactive. `deferred`면 다음 admission의 victim 선택 뒤 |
| `decode(n)` | `dummy="pre_evict"`이고 `0 < n < ceiling`이면 padding 요청. 빈 slot이 없으면 가장 오래된 inactive 1개 축출. 그 slot은 다음 admission이 축출 없이 가져간다 |

**이 기판의 값**(descriptor, provenance 포함): `release_rule="immediate"`([TASK72](TASK72.md), 즉시 1.000 대 지연 0.934), `dummy_mode="pre_evict"`([TASK63](TASK63.md) 74/74, TASK72 `pre_evict` 1.000 대 `reserved` 0.847), `resume_allocates_first=True`([TASK15](TASK15.md), TASK72 R1 36/36). 세 필드는 `None` = 측정되지 않음이며, 값이 있으면 provenance가 필수다. **시뮬레이터는 이 필드를 읽지 않는다** — 읽는 것은 지시문 03 작업 B의 시뮬레이터 스위치뿐이다.

**회귀 검사**: 대조 스크립트의 재생 구현을 제거하고 `FifoReplay`를 import하게 바꾼 뒤 R1·R5′를 다시 돌렸다. 산출 JSON이 계산 시각 외에 **완전히 같다**(R1 36/36·140/140, R5′ 1,298/1,298).

## 2. 상태 변수 d와 정확한 추적기

T의 창에서 필요한 상태는 셋이다.

- `f` = 빈 slot 수, `a` = T보다 오래된 **active** 항목 수, `d` = T보다 오래된, pool에 있는 **inactive** 항목 수.

T가 놓인 직후(빈 slot `f₀`, T 외 running `k`개 — 모두 T보다 오래됐다):

```
a₀ = k,    d₀ = (C − f₀ − 1) − k          full pool (f₀ = 0):  d₀ = C − 1 − k
```

전이(기준 의미론의 직접 귀결):

| 사건 | 전이 |
|---|---|
| 다른 요청의 할당, `f > 0` | `f → f − 1` (축출 없음) |
| 축출(할당·padding 경로), `d > 0` | `d → d − 1`, T 무사 |
| 축출, `d = 0`, T active | 더 새 inactive 항목이 나간다. T 무사(**보호 효과**) |
| 축출, `d = 0`, T inactive | **T 축출(흡수)** |
| 오래된 active 항목의 release | `a → a − 1`, `d → d + 1` |
| T의 release | T inactive |
| 재도착 R의 자기 할당(조회 전) | 할당 1회 — 위 규칙 적용 |

`a`는 줄어들기만 한다(T 뒤에 생긴 항목은 T보다 오래될 수 없다).

`track_target`은 이 전이를 관측 사건열에 적용한다. **정확하다**: 무작위 일정 400개(용량 2–8, 두 dummy 모드)의 target 5,133개에서 참조 재생과 5,133/5,133 일치했고, R5′ 실제 로그의 1,298 재도착에서도 1,298/1,298 일치했다(self-check·A4).

**v0 닫힌 형태가 틀린 두 방향이 이 표에서 바로 보인다**: T가 active인 동안의 축출은 `d = 0`이어도 T를 비켜 간다(v0가 생존을 소멸로 예측한 130건), 오래된 항목의 active 여부는 축출 순간의 `a`·`d`로 들어간다(v0가 lookup 시점 `K_pin`을 써서 소멸을 생존으로 예측한 87건).

## 3. 근사 — 흡수 상태가 있는 유한 birth–death 연쇄

### 수식

상태 `(f, a, d)`와 흡수 상태 DEAD. 두 구간을 차례로 적분한다.

- 구간 1 (길이 `s_active`, T active): 다른 세션의 할당이 Poisson(`λ`)으로 온다. `f>0`이면 `f−1`, 아니면 `d>0`이면 `d−1`, 아니면 변화 없음(보호). 오래된 active 항목은 각각 율 `μ`로 끝난다: `(a, d) → (a−1, d+1)`, 전체 율 `a·μ`.
- 구간 2 (길이 `s_idle`, T inactive): 같은 전이, 단 `f = d = 0`에서의 할당은 DEAD로.
- 끝: 재도착의 자기 할당(조회 전)이 1회 더 — `f = d = 0`이면 DEAD.

```
P_v1(생존) = 1 − P(DEAD)   (균일화 급수로 계산, 상태 수 ≤ (f₀+1)(a₀+1)(C+1))
```

steady state 형태(가득 찬 pool): `f₀ = 0`, `k ~ P_arr`(B2의 arrival theorem), `d₀ = C − 1 − k`, 휴지 시간 분포로 평균한다(`steady_state_survival`).

### 입력 파라미터와 출처 층

| 파라미터 | 식 | 출처 | 층 (값) |
|---|---|---|---|
| `C` | `outer_slot_count` = `batch_size` | descriptor | `stack` |
| 의미론 3종 | `release_rule`, `dummy_mode`, `resume_allocates_first` | descriptor | `stack` |
| `λ` | `X·(N−1)/N` (B2 처리율) | B2 + workload | `silicon`(step·prefill 시간) × workload |
| `μ` | `1 / (E[P] + (G−1)·t_step(n̄)/φ)` | B2 | `silicon` × workload |
| `P_arr(k)` | arrival theorem | B2 | 같음 |
| `s_active` | T의 `P(q) + (g_T−1)·t_step(n̄)/φ` | descriptor + T의 길이 | `silicon` × workload |
| `s_idle` | T의 tool gap + 재입장 대기 | workload | — |
| 전이 규칙 자체 | 가장 오래된 inactive 축출 | — | `universal`(FIFO 대기열 산술) |

### 가정

1. 다른 세션의 할당은 **Poisson**이다(유한 모집단·renewal 구조 무시). 세션 수가 작고 주기가 규칙적이면 분산을 과대평가한다.
2. 오래된 active 항목의 잔여 체류는 **지수분포**(율 `μ`)다.
3. padding 경로 축출은 별도 사건으로 두지 않는다. 가득 찬 pool에서 pre-evict는 다음 할당의 축출을 한 step 앞당길 뿐 수를 바꾸지 않는다(v0 §B1). 앞당겨진 시점 차이는 무시한다.
4. `λ`는 창 동안 일정하다(동시 시작 workload의 비정상성 무시).

### 퇴화 경우 self-check

| 경우 | 결과 |
|---|---|
| `s_active = 0`, `a₀ = 0`, `f₀ = 0`, `d₀ = C−1` → v0 Poisson 법칙 `P(N+1 ≤ C−1)` | C ∈ {4,8,16} × 3 조합, 최대 차 **2.2e-16** |
| 결정론적: T 창 내내 inactive, 할당 A개 → v0 (B1-1) `1 + A ≤ C` | C ∈ {3,5,8,16} × A ∈ 0..19 **전건 일치** |
| 정확 추적기 = 참조 재생 | 무작위 target 5,133/5,133 |

## 4. block 단위·LRU 기판에서의 형태

vLLM의 free-queue LRU에서는 구조가 두 곳에서 바뀐다.

1. **순서는 release 시점에 매겨진다.** running 요청의 block은 queue 밖에 있으므로 "T보다 오래된 active 항목"이 없다(`a ≡ 0`). T가 queue에 들어간 뒤의 release는 모두 T **뒤**에 선다 — `d`는 줄어들기만 하는 순수 사멸 과정이다. 보호 구간도 없다(T는 release 전에 queue에 없다). 창은 release에서 시작한다(v0 §B1).
2. **조회 후 할당**(`scheduler.py:594` → `:721`): 재도착의 자기 block은 T를 밀어내지 않는다.

단위가 block이고 한 요청의 block은 꼬리부터 회수되므로, 생존은 all-or-nothing이 아니라 **남는 선두 block 수의 분포**가 된다:

```
N_ev ~ Poisson(λ_blocks · s_idle),     잃은 block = min(u_T, max(0, N_ev − d₀_blocks))
```

`lru_block_survival`로 구현했다(분포 반환). **구현은 했으나 검증하지 않았다** — GPU 기판 데이터가 없다. 이 형태에 빠진 것: (a) hit로 조회된 block의 touch(재사용 block이 queue 뒤로 옮겨진다), (b) 여러 요청이 공유하는 prefix block, (c) `λ_blocks`의 유도(요청 크기 분포 × 할당률 − 빈 block). GPU 측 사전 예측은 GPU 서버의 vLLM 버전을 source-read한 뒤 새로 선등록한다([INDEX 결정 4](INDEX.md#결정-4--gpua6000-교차검증-착수-시점)).

## 5. 개발 집합 평가 (A4) — 판정 없음

**개발 집합**: [TASK72](TASK72.md) R5′의 7개 run, 재도착 1,298건. **이 성적은 검증이 아니다**(v1은 이 데이터를 보고 만들었다). 또한 이 run들은 세션당 2요청·동시 시작이라 v0·v1 모두의 renewal/Poisson 가정이 깨진다([TASK72](TASK72.md) R5).

평가 대상: gap이 있는 cell의 998건(gap 평균 0인 CONVENTIONAL cell 300건은 B2가 정의되지 않아 제외). 관측 재사용 675건.

| 모형 | Brier | 예측 합 | 비고 |
|---|---|---|---|
| 기후값(관측 비율 상수) | 0.2189 | — | 기준선 |
| **v1 (기록된 초기 상태)** | **0.1358** | 663.0 | `(f₀, a₀, d₀)`를 T 할당 시점 로그 상태에서 |
| **v1 (steady state)** | **0.1335** | 659.8 | arrival theorem 초기 상태 |
| v0 binomial | 0.1629 | 670.7 | |
| v0 poisson | 0.1433 | 681.5 | |
| 정확 추적기(사건열) | — | 1,298/1,298 | 예측이 아니라 규칙 확인 |

구간별 보정(예측 확률 구간 → 관측 생존 비율, n): `results/tables/M06.md`. v1은 0.3–0.9 구간이 단조에 가깝고(steady: 0.36, 0.58, 0.62, 0.75, 0.63, 0.80), 양 끝 구간(0–0.1: 0.21~0.22, 0.9–1: 0.94~0.95)에 표본이 몰린다. v0 binomial은 0.1–0.4 구간이 관측 0.52–0.67로 **역전**돼 있다 — 동시 시작에서 과소 예측이 몰린 결과다.

## 6. v1이 예측하지 않는 것

- 동시 시작·2 turn workload의 과도 상태(λ 일정 가정)
- 유한 모집단 효과(Poisson 할당)와 heavy-tailed 주기
- pre-evict 시점 이동의 효과, release 규칙이 다른 기판(deferred)의 보호 구간 연장
- layer 1(inner LRU)과 layer 2의 상호작용
