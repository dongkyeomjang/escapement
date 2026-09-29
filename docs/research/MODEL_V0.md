# 해석적 모형 v0 명세

작성: 2026-09-29, [TASK71](TASK71.md) (Advisor 지시문 01 작업 B). 코드: [`src/continuum/model/`](../../src/continuum/model/). 정확성 self-check: [`experiments/npu/analysis/model_v0_selfcheck.py`](../../experiments/npu/analysis/model_v0_selfcheck.py).

**이 문서는 정식화다. 기존 측정 데이터와의 대조는 하지 않았다.** 대조 방법·판정 기준·사전 예측은 [MODEL_V0_RETRO_PREREG.md](MODEL_V0_RETRO_PREREG.md)에 계산 전에 등록한다.

**accelerator-neutral 원칙**: 모든 상수는 `SubstrateDescriptor` field 또는 workload 파라미터로 들어온다. 코드에 RBLN 고유 값이 없다. 아래 "출처 층"은 그 파라미터 값이 어느 층에 속하는지(`TASK_GUIDE.md`의 층 태그)를 뜻한다 — **식의 형태**가 아니라 **값**의 층이다.

**정직성 주의**: 이 모형의 결정론적 핵심(B1)과 block 단위 인스턴스는 [TASK14](TASK14.md)·[TASK15](TASK15.md)·[TASK29](TASK29.md)·[TASK58](TASK58.md)·[TASK63](TASK63.md)·[TASK64](TASK64.md)의 결과를 **알고 있는 상태에서** 세웠다. 따라서 그 데이터와의 일치는 blind 예측의 증거가 아니라 **식이 모든 raw run을 빠짐없이 덮는가**의 검사다. blind 예측은 새 workload(steady-state multi-turn)와 두 번째 기판에서만 가능하다.

---

## B1. 생존 모형 — `survival.py`

### (i) 수식

**결정론적 핵심.** 용량 `C`(단위 수)인 pool에서, 대상 요청 T가 캐시한 prefix가 재도착 요청 R의 lookup 시점에 남아 있을 조건:

```
u_T + Σ_{a ∈ A} u_a + K_pin + D  ≤  C                         (B1-1)
```

- `u(·)`: 요청 하나가 소비하는 단위 수(아래 "소비 함수")
- `A`: **창(window)** 안에서 일어난 할당들의 집합. R이 lookup 전에 자기 slot을 먼저 확보하는 기판에서는 **R 자신의 할당을 포함**한다
- `K_pin`: T보다 **먼저** 할당됐고, T를 축출할지 결정되는 순간 아직 running 요청이 붙들고 있어 축출 불가능한 단위 수
- `D`: lookup 순간 요청이 아닌 소비자(padding용 dummy)가 붙든 단위 수

block 단위 pool(tail-first 부분 손실)에서는 남는 단위와 재사용 token이:

```
s_T  = max(0, u_T − max(0, u_T + Σ u_a + K_pin + D − C))          (B1-2)
hit  = HitFormula(shared = min(prefix, s_T × unit_tokens), query)
```

**창의 정의 — eviction 순서가 정한다.**

| eviction 순서 | 창 시작 | 창 끝 | 근거 |
|---|---|---|---|
| **FIFO-by-allocation** (측정 기판) | **T의 slot 할당 시점** — tool gap 시작이 아니다. T 자신의 prefill·decode가 창 안에 있다 | R의 lookup. R이 먼저 할당하면 그 할당도 창 안 | 대기열 위치가 할당 때 고정된다([TASK14](TASK14.md) 발견 5). 할당 후 조회([TASK15](TASK15.md), [TASK24](TASK24.md)) |
| **LRU over free queue** (vLLM block pool) | **T의 release(요청 종료) 시점** — running 요청의 block은 queue 밖에 있다 | R의 lookup. vLLM은 **lookup이 할당보다 먼저**다(`vllm/v1/core/sched/scheduler.py:594` `get_computed_blocks` → `:721` `allocate_slots`, 설치 `vllm 0.22.0+cpu` source-read) | [TASK29](TASK29.md) 인용 ①, 이번 source-read |

**pool 상태와 무관한 이유.** 단위 1개씩인 경우로 적는다. T 할당 직후 빈 slot이 `f`개이면 pool에는 T를 포함해 `C − f`개가 있고 T보다 오래된 항목은 `C − f − 1`개다. 창 안의 할당 `A`개 중 앞의 `f`개는 빈 slot을 쓰고 나머지 `A − f`개가 축출을 부른다. FIFO는 T보다 오래된 inactive 항목을 먼저 축출하므로 T가 축출될 조건은 `A − f > (C − f − 1) − K_pin`, 즉 `1 + A + K_pin > C`다 — `f`가 소거된다. 측정 문턱이 **개수**이고 배경 크기 500–4,000 token에서 같은 값(7)이었던 것이 이 성질이다([TASK29](TASK29.md)).

**소비 함수 — 두 인스턴스가 같은 식이다.**

| 인스턴스 | `u(tokens)` | descriptor field |
|---|---|---|
| 시퀀스 단위 slot | `ceil(ceil(tokens / inner_block_tokens) / block_ratio)` (8,192 token 이하면 1) | `outer_slots_for`, `outer_slot_count` = C |
| block 단위 pool | `ceil(tokens / inner_block_tokens)` | `inner_block_tokens`, `inner_block_count` = C |

시퀀스 단위에서 (B1-1)은 **요청 개수** 문턱이 되고, block 단위에서는 **token 총량** 문턱이 된다.

**순차 프로토콜([TASK14](TASK14.md)·[TASK15](TASK15.md)) 인스턴스.** target → 배경 m개(각 u_bg) → resume. 동시 실행이 없으므로 `K_pin = 0`:

```
생존  ⇔  u_T + m·u_bg + u_R ≤ C       (resume 선할당)
m*   =  floor((C − u_T − u_R) / u_bg)
```

block 단위(tail-first)에서 손실 시작 B와 전손 B:

```
B_first = floor((C − u_T − u_R + (u_T − u_hit)) / u_bg) + 1,   u_hit = hit 가능한 선두 단위 수
B_total = ceil((C − u_R) / u_bg)
```

**dummy block — 두 가지 읽기.** [TASK63](TASK63.md)은 `0 < n < 상한`인 decode step마다 padding 요청이 free list 머리를 가리키고, free가 0이면 가장 이른 inactive 항목을 회수하며, **다음 admission이 그 slot을 회수 없이 가져가는 것**(74/74)을 관측했다.

| 모드 | lookup 시 `D` | 효과 |
|---|---|---|
| `PRE_EVICT` (관측 기반 읽기) | **0** | admission이 필요로 하는 축출이 **한 decode step 앞당겨질** 뿐이다. 추가 축출은 run 끝(마지막 admission 뒤)에 1건 — [TASK58](TASK58.md)의 `max(0, ALLOC + 1 − C)`. 생존 문턱은 바뀌지 않고, 축출 시점이 바뀌어 `K_pin`의 평가 시점만 달라진다 |
| `RESERVED` (시뮬레이터 [TASK69](TASK69.md) 스위치) | `1{0 < running_at_admission < 상한}` | admission 시점에 한 slot을 예약한 것으로 계산한다. 다른 요청이 decode 중일 때의 lookup에서 유효 용량이 C−1이 된다 |

**확률적 확장.** steady-state multi-turn 부하에서 창 안의 할당 수 `A`는 확률변수다:

```
P(생존) = E_W[ P( u_T + A_other·u_o + u_R + K_pin + D ≤ C | W ) ]        (B1-3)
W_FIFO = (T의 할당 후 체류: prefill + decode) + tool gap + 재입장 대기
W_LRU  = tool gap + 재입장 대기
```

다른 세션 `N−1`개는 각각 평균 주기 `c = Z + R`(think + 응답)의 정상 renewal 과정이다. 주기 분포와 무관하게 창 길이 w 동안의 **평균** 할당 수는 `(N−1)·w/c`이고, 분산만 분포에 따라 다르다. 두 계수 법칙을 둔다:

| 법칙 | 식 | 근거 |
|---|---|---|
| `binomial` (유한 모집단) | 세션마다 `floor(w/c) + Bernoulli(frac(w/c))`, 합은 `(N−1)·floor(w/c) + Bin(N−1, frac(w/c))` | 주기가 규칙적이면 한 세션은 한 주기 안에 두 번 할당될 수 없다. N이 작고(이 연구는 N ≤ 16) 창이 주기보다 짧은 영역에 맞다. **분산 최소** |
| `poisson` | `Poisson((N−1)·w/c)` | 같은 총률의 N→∞ 극한. 주기가 지수분포일 때 정확 |

실측 tool gap은 heavy-tailed([TASK31](TASK31.md), `toolmix`)이라 주기 CV가 1을 넘을 수 있고, 그 경우 실제 분산은 Poisson보다도 크다 — 두 법칙은 **CV ≤ 1 구간만** 괄호로 묶는다.

**평균장(characteristic time) 형태.**

- **FIFO-by-allocation, 모든 admission이 할당(hit이어도 새 slot)**: 항목은 뒤에 `C − K̄_pin` 단위가 삽입될 때까지 산다. `T_F = (C − K̄_pin) / (삽입률 × ū)`. 고전 FIFO(miss 시에만 삽입, Martina·Garetto·Leonardi INFOCOM 2014)와 달리 삽입률이 hit 확률에 의존하지 않아 **고정점이 필요 없다.** `P(생존) ≈ P(W_FIFO < T_F)`
- **LRU(free queue), Che 근사**(Che·Tung·Wang IEEE JSAC 2002): `N · u_rel · E[min(G, T_C)] / c = C − Ū_active`를 `T_C`에 대해 푼다. `P(생존) ≈ P(W_LRU < T_C)`

**KV cache가 고전 캐시와 다른 점과 반영 여부.**

| 차이 | 반영 |
|---|---|
| 활성 요청이 쥔 block은 축출 불가 | **반영.** FIFO: `K_pin`. LRU: queue 용량을 `C − Ū_active`로 줄임(running 요청 block은 queue 밖) |
| 항목 크기가 가변 | **부분 반영.** 결정론적 핵심은 요청별 `u_a` 합이라 정확. 확률적 확장은 다른 세션 단위를 평균 `u_o` 하나로 둔다 |
| 요청이 아닌 소비자(dummy) | **반영.** `D`와 두 모드. 단 `PRE_EVICT`에서 축출 시점 이동이 `K_pin`에 미치는 효과는 식이 아니라 사건 순서로만 정해진다 |
| hit이어도 새 slot을 할당(측정 기판) | **반영.** FIFO 삽입률이 hit과 무관 → `T_F` 닫힌 식 |
| release되는 것은 prefix가 아니라 전체 문맥(생성 token 포함) | **반영(LRU).** `u_rel`을 전체 문맥 단위로 받는다. 측정 기판의 층 2는 prefill token만 캐시한다([TASK24](TASK24.md)) |
| 한 요청의 block이 꼬리부터 회수됨 | **반영.** (B1-2) tail-first. 평균장 LRU는 all-or-nothing으로 근사 |
| 완료 요청 block이 evictable로 바뀌는 시점 | **미반영(파라미터로 둠).** 아래 (iv) |

### (ii) 가정

1. FIFO 기판에서 축출 대상은 "할당 순서상 가장 이른 **inactive** 항목"이다([TASK14](TASK14.md), [TASK63](TASK63.md) 15/15·[TASK64](TASK64.md) 5/5 관측과 source-read).
2. 모든 admission은 할당한다(hit이어도). 할당 후 조회 여부는 파라미터 `resume_allocates_first`다(측정 기판 `True`, vLLM `False`).
3. 확률적 확장: 다른 세션은 서로 독립인 정상 renewal 과정, 창 길이 W와 A_other는 W를 통해서만 연결된다(T 자신의 체류 시간과 다른 세션의 도착의 상관을 무시).
4. `K_pin`은 확률적 확장에서 입력(기본 0)이다. 분포를 유도하지 않았다.

### (iii) 입력 파라미터와 출처 층

| 파라미터 | descriptor/workload | 층 (현 인스턴스 값의 층) |
|---|---|---|
| `C` (slot 수 / block 수) | `outer_slot_count` / `inner_block_count` | `stack` (compile `batch_size`가 정함, [TASK08](TASK08.md)) |
| 소비 함수 단위 | `outer_slot_tokens`, `inner_block_tokens` | `stack` |
| eviction 순서 → 창 정의 | `outer_eviction_policy`, `inner_eviction_policy` | `stack`(FIFO 하드코딩) / `class`(vLLM LRU) |
| 할당·조회 순서 | 신규 파라미터 `resume_allocates_first` (descriptor에 아직 없음) | `stack` |
| dummy 모드와 상한 | 신규 파라미터 (descriptor에 아직 없음) | `stack` |
| hit 식 | `hit_formula` | 형태 `class`, block 크기 `stack` |
| N, 주기 c, gap 분포, 생성 길이 | workload | 해당 없음(workload) |
| 체류 시간(W_FIFO의 첫 항) | B2 출력 또는 descriptor 비용 모형 | `silicon` |
| 식 (B1-1)의 형태 | — | `universal`(FIFO 대기열의 산술) |

### (iv) 예측하지 않는 것

- **완료된 요청의 항목이 언제 evictable이 되는가.** [TASK24](TASK24.md)는 "다음 admission의 victim 선택 뒤"라고 했고 시뮬레이터가 그렇게 구현했으나, [TASK63](TASK63.md) B.b0 상한 이탈 로그에서는 방금 끝난 요청의 OB0이 바로 다음 dummy 괄호에서 회수됐다. 모형은 이 시점을 `K_pin` 입력으로 밀어낼 뿐 정하지 않는다
- **layer 1(inner block LRU)과 layer 2의 상호작용.** 측정 기판은 두 층이고 metric이 층 1을 보고한다([TASK14](TASK14.md)). 모형은 한 pool씩 다룬다
- 동시 도착의 admission 순서(OS thread 순서, [TASK24](TASK24.md))
- `K_pin`의 분포, heavy-tailed 주기(CV > 1)에서의 A 분산
- 재도착 prompt의 byte-identity 등 hit 식 밖의 조회 실패([TASK57](TASK57.md))

---

## B2. 활성 요청 수 분포 — `occupancy.py`

### 한계 (먼저 적는다)

**arXiv 원고의 workload(세션당 2요청, 동시 시작)는 steady state가 아니다.** 모든 세션이 t=0에 turn 0을 보내므로 running 수는 N에서 시작해 gap으로 흩어졌다가 turn 1과 drain으로 끝난다. 관측 h(n)은 이 ramp·drain이 지배한다. **이 모형의 본 검증 대상은 이후 steady-state multi-turn 실험이다.** 원고 조건과의 비교(R4)는 탐색이며 불일치가 예상된다.

### (i) 수식

N개 세션이 "엔진 안(대기 또는 running)"과 "tool gap(평균 Z)"을 번갈아 하는 **유한 모집단 closed 2-station 망**. 엔진 안 수가 n일 때 running `r(n) = min(n, M)` (`M` = `max_num_seqs`).

```
μ(n)     = φ · r(n) / (G · t_step(r(n)))                 요청 완료율
π(n+1)/π(n) = ((N − n)/Z) / μ(n+1)                        birth-death 곱 형태
X        = Σ_n π(n)·(N − n)/Z                             처리율
φ        = 1 − X · E[P]                                   배타 prefill이 남긴 decode 시간 몫
```

`φ`와 `π`는 서로에 의존하므로 감쇠 고정점 반복으로 푼다(self-check에서 잔차 5.5e-13).

**두 분포를 구분한다.**

```
time_share(r) = Σ_{n: min(n,M)=r} π(n)                   시간 가중
step_share(r) ∝ time_share(r) · φ / t_step(r),  r ≥ 1     step 가중 = [BUCKET] 로그가 세는 것
```

B3의 격자 비용은 step 가중 h를 쓴다(Σ h(n)·t_step = decode device time).

**arrival theorem.** 곱 형태 closed 망에서 도착 요청이 보는 분포는 자신을 뺀 N−1 모집단의 시간 정상 분포다. B4의 `K_j` 분포로 쓴다(φ는 N 모집단 해를 쓴다).

### (ii) 가정과 근거

1. **n ≤ M에서 엔진은 processor sharing**이다 — 모든 running 요청이 한 step에 한 token씩 같이 진행한다. gap station은 delay station이다. 따라서 BCMP 무감응성에 의해 **π는 gap 분포의 평균 Z에만 의존**하고 분포 형태에 무관하다. N > M이면 대기 요청이 FCFS라 무감응성이 깨지고 근사가 된다(코드가 `notes`에 기록).
2. **prefill은 시간 전체에 균일하게 퍼진 감속(φ)으로 근사**한다. 실제로는 모든 decoder를 동시에 멈췄다 동시에 재개시킨다.
3. 요청당 decode step 수 G는 평균 하나로 둔다(PS에서 π는 요구량 분포에 무감응이므로 n ≤ M에서는 정확).
4. E[P]는 입력이다. 재사용에 의존하므로 B1의 생존 확률로 갱신할 수 있다(`interference.expected_prefill_s`). v0는 결합 고정점을 자동으로 돌리지 않는다.

### (iii) 입력 파라미터와 출처 층

| 파라미터 | 출처 | 층 |
|---|---|---|
| `t_step(r)` | `descriptor.step_time_s` (`StepCostModel` + `bucket_sizes`) | `silicon`(절대 시간) × `stack`(격자) |
| E[P] | `PrefillCostModel` × 계산 token 분포 | `silicon` |
| M | `SimConfig.max_running_requests` = compile `batch_size` | `stack` |
| N, G, Z | workload | — |

### (iv) 예측하지 않는 것

- 과도 상태(동시 시작, drain). 원고 workload 전체
- 배타 prefill의 **동기화 효과**(재개 직후 넓은 batch) — 평균 감속 이상의 상관 구조
- 격자에 따른 h의 되먹임을 제외한 나머지 시간 상관([TASK68](TASK68.md)의 재도착 되먹임은 평균 수준에서만 들어간다)
- 캐시 생존과 E[P]의 결합(v0에서는 외부 입력)

---

## B3. 격자 최적화 — `grid.py`

### (i) 수식

h(n) (step 가중)과 `t_step(b, n) = fixed(b) + intercept + marginal·n`에서, `1`과 `top`(= `batch_size`)을 포함하고 크기 ≤ k인 격자 G 중

```
cost(G) = Σ_n h(n) · t_step(b_G(n), n),     b_G(n) = min{b ∈ G : b ≥ n}
```

를 최소화한다. `intercept + marginal·n` 항은 격자와 무관하므로 최적화는 `fixed(b)`만 본다. 동적계획법:

```
F[1][1] = h(1)·fixed(1)
F[j][b] = min_{b' < b} F[j−1][b'] + fixed(b) · H(b', b],   H(a,b] = Σ_{a<n≤b} h(n)
최적     = min_{j ≤ k} F[j][top]                            O(k·top²)
```

동률은 사전식으로 가장 작은 격자로 깬다(전수 열거와 비교 가능하게).

**미측정 버킷 비용**: `config_search.descriptor_for`의 규칙을 그대로 쓴다 — 측정 폭은 그대로, 범위 안의 미측정 폭은 양옆 측정 폭 사이 선형 보간, 범위 밖은 가장 바깥 측정 쌍으로 선형 외삽. `grid.interpolated_fixed_costs`는 이 규칙의 재진술이며, self-check에서 합성 descriptor 200개에 대해 `config_search.descriptor_for`와 **bit 단위 동일**함을 확인했다.

**k의 정의**: 여기서 k는 **격자 전체 크기**(1과 top 포함)다. [TASK61](TASK61.md)이 기록한 대로 `config_search.py --max-buckets m`은 전체 크기 ≤ m+1을 연다. 선등록 정의(전체 ≤ 6, 후보 2,077개)는 `--max-buckets 5`이고 이 모형의 `k = 6`에 대응한다. `count_grids(16, 6) = 1,471`은 [TASK61](TASK61.md)의 batch 16 후보 수와 같다.

### (ii) 가정

1. h(n)이 주어진 것으로 본다 — 격자를 바꾸면 h가 바뀌는 되먹임([TASK68](TASK68.md), 원고 III-D)은 **식 안에 없다.** DP 최적은 한 h에 대한 **최선 응답**이지 격자–h 고정점이 아니다.
2. 격자 선택이 캐시 생존에 영향을 주지 않는다(`top` 고정 = pool 크기 고정). `batch_size`를 바꾸는 선택은 B1의 C를 바꾸므로 이 DP의 범위 밖이다.
3. compile 예산은 k ≤ 6에서 걸리지 않는다(`42.3 + 61.33·(k+1) ≤ 1800 s` ⇔ k ≤ 27).

### (iii) 입력 파라미터와 출처 층

| 파라미터 | 출처 | 층 |
|---|---|---|
| `fixed(b)` 측정값 | `StepCostModel.fixed_s_by_bucket` | `silicon` |
| 보간·외삽 규칙 | `config_search.descriptor_for` | 규칙 자체는 모형 가정(`universal`한 방법 선택), 값은 `silicon` 두 번 모형 |
| `top`, k | compile 구성 | `stack` |
| h(n) | B2 출력 또는 관측 `[BUCKET]` | workload × 기판 |

### (iv) 예측하지 않는 것

- 되먹임으로 바뀐 h에서의 성능(최선 응답의 반복이 수렴하는지도 보장 없음)
- 캐시 생존 경로의 이득(`batch_size` 효과, [TASK35](TASK35.md) 지배 인자) — 이 DP는 decode padding 항만 본다
- 측정되지 않은 폭(6, 10, 16 등)의 실제 비용 — 보간 오차는 [TASK55](TASK55.md)에서 C(6) 2.00 %

### self-check 결과 (합성 입력만, 측정 데이터 미사용)

| 항목 | 결과 |
|---|---|
| DP vs 전수 열거 | **1,200/1,200 일치** (top ∈ {4,8,10,12,16} × k ∈ {2..6} × h 모양 6종 × 비용 곡선 4종 × 2회, seed 20260929). 최적 비용 동일(상대 1e-9)이고 DP 격자가 동률 최적 집합 안. 유일 최적 1,144건, 동률 56건 |
| 계산 시간 | DP 합 0.043 s, 전수 열거 합 0.417 s (1,200건, 96 core host 단일 thread) |
| 보간 규칙 | 합성 descriptor 200개에서 `config_search.descriptor_for`와 bit 동일(최대 차 0.0) |

---

## B4. prefill 간섭 — `interference.py`

**원고 식 (6)·(9)의 본문은 이 저장소에 없다**(개정 1에서 Advisor가 식을 제공했고 (9)와 일치함을 확인 — [선등록 §8.1](MODEL_V0_RETRO_PREREG.md))([TASK65](TASK65.md)에서 원고 제거). 아래는 [TASK22](TASK22.md)·[TASK66](TASK66.md)·[TASK67](TASK67.md) 기록에서 재구성한 형태이며, 원고 식과의 번호 대응은 Advisor 확인이 필요하다.

### (i) 수식 (정식화만, 검증 없음)

사건 단위:

```
stall_j = P(q_j) · K_j,      q_j = L_j − H_j                       (W의 항)
W       = Σ_j P(q_j) · K_j                                          세션 시간 손실
D_pf    = Σ_j P(q_j)                                                device 시간
```

기대값 형태(q_j와 K_j 독립 가정):

```
E[W] / 시간 = X · E[P(q)] · E[K]
E[K]        = Σ_k k · P_arr(k),   P_arr = arrival theorem 분포(B2)
E[P(q)]     = p_s · P(L − H) + (1 − p_s) · P(L),   p_s = B1의 생존 확률
재사용 실패 1건 = device (P(L) − P(L − H))  +  세션 (P(L) − P(L − H)) · K
```

재사용 실패 비용의 정의는 증분형(`P(L) − P(L−H)`)이다 — 시뮬레이터가 `q = L − H`를 넣어 사실상 이 정의를 쓴다([TASK67](TASK67.md)).

**chunked prefill 기판.** `K_j → 0`으로 stall 항이 사라진다. prefill 일은 decode step 안으로 들어간다. [TASK29](TASK29.md) 절제는 이때 device time이 **3–10 % 늘어남**을 계산했다(배타 실행이 decoder를 붙잡아 재개 시 더 넓은 batch를 만들던 효과의 상실). B2에서 이 효과의 **평균 부분**은 φ로 들어간다 — 배타 prefill은 체류를 늘려 평균 running 수와 batch 폭을 올린다. 동기화(동시 재개) 부분은 곱 형태에 없다. 따라서 **모형은 chunked 전환의 부호는 맞히고 크기는 과소 추정할 것**으로 본다 — 가설이다.

### (ii) 가정

q_j와 K_j 독립, 동시 도착(동시 시작 workload의 t=0 폭주)은 arrival theorem 밖, P는 descriptor의 배타 prefill 모형.

**독립 가정의 방향 (개정 1, Advisor 지시문 02)**: 재사용 실패(긴 P)는 부하가 높을 때(큰 K) 몰리므로 P와 K의 공분산은 양일 가능성이 높다. 그렇다면 `X·E[P]·E[K]`는 `E[W]`를 **과소** 추정한다. 식은 수정하지 않는다. 원고 식 (9) `Ŵ = Σ_j T̂_prefill(q̂_j)·K̂_j`는 사건 단위 형태와 일치한다.

### (iii) 입력

`PrefillCostModel`(`silicon`), 배타 여부(`stack`: RBLN 배타, vLLM chunked 기본 — [TASK29](TASK29.md) 인용 ③·④), B1의 p_s, B2의 X·P_arr.

### (iv) 예측하지 않는 것

재개 동기화에 의한 batch 확대의 크기, chunked 기판에서 chunk가 decode step 비용을 얼마나 올리는지(descriptor에 chunk 혼합 step 비용이 없다), 동시 시작 폭주.

---

## 모형으로 표현하기 어려운 관측 사실 (정식화 중 발견)

1. **완료 block의 evictable 전환 시점** — [TASK24](TASK24.md)의 "다음 admission victim 선택 뒤"(시뮬레이터 구현)와 [TASK63](TASK63.md) B.b0 상한 이탈(방금 끝난 요청의 OB0이 다음 dummy 괄호에서 바로 회수)이 같은 규칙으로 읽히지 않는다. B1에서는 `K_pin` 입력으로만 남는다.
2. **dummy block의 모형화 방식 차이** — `PRE_EVICT` 읽기([TASK63](TASK63.md) 관측 4: 다음 admission이 dummy slot을 그대로 가져감 74/74)에서는 lookup 시 D = 0이고 생존 문턱이 바뀌지 않는다. [TASK69](TASK69.md)의 시뮬레이터 스위치(`reserved`)는 admission 시점에 한 slot을 예약해 **다른 요청이 decode 중인 lookup에서 유효 용량을 C−1로 만든다.** 두 읽기는 동시 부하에서 다른 예측을 낸다. [TASK69](TASK69.md)에서 스위치가 예측 오차를 키우고 sim 재사용을 실측보다 낮춘 것과 방향이 맞지만, **이것은 대조 계산 없이 식에서 나온 가설이다.**
3. **할당·조회 순서가 기판마다 반대다** — 측정 기판은 할당 후 조회, vLLM은 조회 후 할당(source-read). block 단위 문턱이 한 요청분 달라진다(예: C=512, u_T=u_R=u_bg=16에서 전손 B = 31 대 32). [TASK29](TASK29.md)의 GPU 측 절제 계산(`GranularPool`)은 할당 후 조회를 썼다. 이 차이는 [TASK29](TASK29.md) 원문을 고치지 않고 GPU 예측 선등록 때 명시해야 한다.
4. **동시 시작 workload의 비정상성** — B2는 steady state만 다룬다. 원고 조건의 h(n)은 ramp·drain이 지배한다.
5. **배타 prefill의 동기화 보조금** — 평균장(φ)으로는 부호만 담긴다.
6. **동시 도착의 admission 순서** — OS thread 순서라 재현 불가([TASK24](TASK24.md)). 결정론적 핵심은 관측된 순서를 받아야만 적용된다.
7. **layer 1/layer 2 이중 구조와 metric의 층 불일치** — 한 pool 모형 둘로 나눠야 한다.
