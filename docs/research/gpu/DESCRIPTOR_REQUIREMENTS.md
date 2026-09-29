# `SubstrateDescriptor` 구조 요구사항 — 두 기판(RBLN CA25 NPU, A6000 GPU)을 함께 표현하기 위해

작성: 2026-09-29, GPU 지시문 G-02 작업 E ([GTASK06](GTASK06.md)). **코드는 쓰지 않는다.** descriptor 개편은 NPU 쪽이 `src/continuum/`에서 하며, 이 문서는 그 입력이다.

근거: GPU 쪽은 [GTASK01](GTASK01.md)(source-read), [GTASK02](GTASK02.md)(Stage 0, FIT_GAPS 11건), [GTASK03](GTASK03.md)(관측), [GTASK04](GTASK04.md)(순차 생존), [GTASK05](GTASK05.md)(step 비용). NPU 쪽은 [INDEX](../INDEX.md)와 인용 TASK. 현재 descriptor(`src/continuum/substrate/descriptor.py`, [TASK73](../TASK73.md) 반영: `release_rule`·`dummy_mode`·`resume_allocates_first` 추가)를 기준으로 쓴다.

## 0. 설계 원칙 (제안)

1. **pool을 층의 목록으로 둔다.** 현재의 `outer_*`/`inner_*` 고정 2층은 NPU 구조를 그대로 옮긴 것이다. GPU는 1층이다. 각 층이 같은 field 묶음을 갖고, **어느 층이 실제 재사용을 정하는지**(`reuse_layer`)를 따로 적는다(NPU는 층 2, 층 1은 metric만 보고한다 — [TASK14](../TASK14.md)·[TASK15](../TASK15.md)).
2. **의미론 field는 값이 아니라 규칙을 담는다.** "lru"라는 문자열 하나로는 순서의 기준(할당 대 release)·tie-break·초기 순서를 담을 수 없다(GTASK02 FIT_GAPS 3).
3. **runtime flag로 정해지는 값과 compile로 정해지는 값을 구분한다**(`value_source`). GPU의 pool 크기·격자는 server 인자, NPU는 compile artifact다. 모형이 "재고 예측"할 때 무엇을 다시 재야 하는지가 여기서 갈린다.
4. 모든 field는 기존처럼 `Provenance`(층 태그·출처·측정 방식)를 요구하고, `None` = "측정·확정되지 않음"(0이나 기본값이 아님)을 유지한다.

## 1. field 목록 — NPU 값과 GPU 값

### A. KV pool 층 (층마다 반복)

| field (제안) | 의미 | NPU (RBLN CA25 / vllm-rbln 0.11.1) | GPU (A6000 / vllm 0.22.0) | 현재 descriptor |
|---|---|---|---|---|
| `layers[].name` | 층 이름 | 층 1 inner block, 층 2 outer slot | 단일 block pool | 없음(`inner_*`/`outer_*` 고정) |
| `layers[].unit_tokens` | 할당 단위의 token 수 | 층 1 128, 층 2 8,192 ([TASK08](../TASK08.md)) | **16** (GTASK02) | `inner_block_tokens`, `outer_slot_tokens` |
| `layers[].capacity_units` | 요청이 쓸 수 있는 단위 수(물리 − 예약) | 층 1 512(= 513 − null), 층 2 8 (`batch_size`) | **`num_gpu_blocks − 1`**(null block 제외; GTASK04 800) | `inner_block_count`, `outer_slot_count` |
| `layers[].reserved_units` | 요청이 아닌 **상수** 점유 | 층 1 null 1 | **null block 1**(`block_pool.py:176`) | 없음(notes에만) |
| `layers[].value_source` | 용량이 정해지는 곳 | compile `batch_size` | server 인자 `--num-gpu-blocks-override` | 없음 |
| `layers[].consumption` | 요청 하나가 차지하는 단위 수 | 층 2: `ceil(ceil(t/128)/64)`(≤ 8,192 token이면 1, 요청 **개수** 문턱) | `ceil(t/16)`, `t` = 그 시점까지 KV가 계산된 token(**생성 포함**) — token **총량** 문턱 | `outer_slots_for`(층 2 전용) |
| `reuse_layer` | 실제 재사용(재계산 회피)을 정하는 층 | 층 2 | 단일 층 | 없음 |
| `physical_tokens` / `usable_tokens` | pool 크기의 두 정의 | 8 × 8,192 / 같음 | `N × 16` / `(N − 1) × 16` | `kv_pool_tokens`(구분 없음, FIT_GAPS 11) |

### B. 축출 순서와 생존 창

| field (제안) | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `eviction_order` | 축출 순서의 기준 | **`allocation_fifo`** — 할당 순서상 가장 이른 inactive 항목([TASK14](../TASK14.md), [TASK72](../TASK72.md)) | **`release_lru`** — free queue에 반납된 순서, 머리부터(`block_pool.py:347,431`) | `outer_eviction_policy`/`inner_eviction_policy` 문자열 |
| `evictable_when` | 끝난 요청의 항목이 축출 후보가 되는 시점 | `immediate`([TASK72](../TASK72.md) 1.000 대 지연 0.934) | `immediate`(요청 종료 처리 안에서 반납, `scheduler.py:1480→1862`). async scheduling으로 한 step 늦을 수 있음(`UNKNOWN`) | **`release_rule`** (있음) |
| `window_start` | 생존 창이 시작되는 사건 | 대상의 **할당** | 대상의 **release** | 없음(모형 명세에만) |
| `intra_request_loss` | 한 요청 안에서 잃는 순서 | `all_or_nothing`(slot 1개) | **`tail_first`**(`reversed(req_blocks)`, `single_type_kv_cache_manager.py:350`) → 부분 손실, 16 token 계단 | 없음 |
| `initial_free_order` | 한 번도 안 쓴 단위의 소비 순서 | 해당 없음(slot 수 = 동시성, 기록 없음) | **`never_used_first`**(block ID 순 초기화) — 새 server의 순차 프로토콜에서 release LRU를 할당 FIFO와 같은 순서로 만든다(GTASK04) | 없음 |
| `active_pinned` | running 요청의 단위가 축출 불가인가 | 예(`K_pin`) | 예(ref_cnt > 0이면 queue 밖) | 없음(모형 입력) |

### C. 조회와 할당

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `resume_allocates_first` | 재도착 요청이 조회 전에 자기 단위를 잡는가 | `True`([TASK15](../TASK15.md)) | **`False`**(`scheduler.py:594 → 721`) | **있음** |
| `hit_protection` | 조회로 찾은 단위가 같은 admission의 새 할당에서 보호되는가 | 해당 없음(할당이 먼저) | **`touch_before_alloc`**(`kv_cache_manager.py:397 → 404`) | 없음 |
| `failed_admission_evicts` | 할당 실패가 축출을 남기는가 | `UNKNOWN` | **아니오**(검사 후 `None`, `kv_cache_manager.py:387`) | 없음 |
| `cache_registration` | 계산 중인 block이 캐시에 등록되는 시점 | `UNKNOWN` | **할당 시점**(같은 step의 뒤 요청이 hit 가능, `kv_cache_manager.py:421–425`) | 없음 |

### D. 무엇이 캐시되는가와 hit 식

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `hit_formula.block_tokens` | hit 단위 | 128 | 16 | `HitFormula` (있음) |
| `hit_formula.reserve_last_query_token` | 마지막 query token 재계산 | 예 | 예(`max_cache_hit_length = num_tokens − 1`) | 있음 |
| `cacheable_tokens` | 끝난 요청이 남기는 캐시 가능 prefix | **`prefill_only`**([TASK24](../TASK24.md) 271/271) | **`computed`** = prompt + output − 1(GTASK02 H5 1,024; GTASK04 (ii)) | 없음(FIT_GAPS 6) |

### E. 요청이 아닌 소비자

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `dummy_mode` | 시변 padding 소비자 | `pre_evict`([TASK63](../TASK63.md), [TASK72](../TASK72.md)) | `none`(padding은 `PAD_SLOT_ID=-1`, block 없음) | **있음** |
| `dummy_trigger` | 발동 조건 | `0 < n < 상한`인 decode step. 상한이 `batch_size`인지 최상위 bucket인지 `UNKNOWN`([TASK69](../TASK69.md)) | 해당 없음 | 없음 |
| `reserved_units` | 상수 소비자 | (A의 층 1 null) | null block 1 | A로 이동 |

### F. preemption

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `preemption` | running 요청을 내보내는 경로 | `none`(지시문 전제, NPU 기록 기준) | **`recompute`**(block 전부 반납, `num_computed_tokens = 0`, swap 없음) | 없음 |
| `preemption_trigger` | 발동 조건 | — | running 요청의 새 block 수요 > free(= 미사용 + inactive 캐시 전부) | 없음 |
| `preemption_victim` | 대상 | — | `fcfs`: running 목록 마지막(가장 최근 admission), `priority`: `max(priority, arrival)` | 없음 |
| `preemption_disableable` | 끌 수 있는가 | — | **아니오**. 구조적 회피 조건 `usable ≥ max_num_seqs × ceil(max_len/16)` | 없음 |
| `preempted_keeps_cache` | 반납된 block이 hit 가능하게 남는가 | — | 예(hash 유지, 재입장 시 자기 prefix hit 가능) | 없음 |

### G. admission 제약

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `max_running` | 동시 running 상한 | compile `batch_size` | `--max-num-seqs` | 없음(시뮬레이터 `SimConfig`) |
| `step_token_budget` | step당 token 상한 | `UNKNOWN`(prefill은 요청 단위 배타, 128 chunk) | `--max-num-batched-tokens`(A6000 OpenAI server 기본 2048, **로그에 안 남으므로 명시 필수** — GTASK02 발견 6) | 없음 |
| `admission_requires_full_prompt` | prompt 전체 block이 free에 들어가야 admission | `UNKNOWN` | 예(`scheduler_reserve_full_isl=True`) | 없음 |

### H. step 격자

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `grid_sizes` | 격자 | compile `decoder_batch_sizes`(예 `(1,2,4,8)`) | `cudagraph_capture_sizes`(기본 `[1,2,4,8,16]` @ `max_num_seqs=8`) | `bucket_sizes` |
| `grid_unit` | 사상 단위 | **요청 수** | **스케줄 token 수**(decode-only에서는 요청 수와 같다) | 없음(`bucket_for`는 요청 수 가정) |
| `grid_value_source` | 격자가 정해지는 곳 | compile(재compile 필요) | server 인자 | 없음 |
| `above_top` | 최상위보다 큰 step | 발생 불가(running ≤ `batch_size`) | **eager**(padding 없음) | 없음(`bucket_for`가 예외) |
| `mixed_step_graph` | prefill이 섞인 step의 격자 | 해당 없음(배타) | `PIECEWISE`(token 수 ≤ 최상위), 넘으면 eager | 없음 |
| `graph_modes` | graph 종류 | 단일 compiled graph | `FULL`(uniform decode) / `PIECEWISE`(혼합) / `NONE` | 없음 |

### I. step 비용

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `step_cost.decode` | decode-only step | `f(bucket) + g·actual`([TASK13](../TASK13.md)) | FULL: `F[capture] + g·n`(GTASK05 측정) | `StepCostModel` 하나 |
| `step_cost.mixed` | 혼합 step(≤ 최상위) | 해당 없음 | PIECEWISE 증분 곡선(GTASK05) | 없음 |
| `step_cost.eager` | 격자 밖 step | 해당 없음 | eager: decode 폭 d + prefill p의 증분 곡선(GTASK05) | 없음 |
| `step_cost.measurement` | 비용을 어떤 채널로 쟀는가 | device model span + sampler p50 | dispatch 간격(async lag 규칙, GTASK05) | 없음 |

### J. prefill 실행 방식

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `prefill_execution` | prefill과 decode의 관계 | **`exclusive`** — 모든 decoder 정지([TASK22](../TASK22.md)) | **`mixed`** — chunked on/off 모두 같은 step에 혼합(GTASK01 항목 7) | 없음(`PrefillCostModel` 존재 = 배타로 해석, FIT_GAPS 9) |
| `prefill_cost` | prefill 비용 | `prefill_s(n) = ceil(n/128)·(a + b·n)`, 정지 비용 = × 동시 decoder | 혼합 step 증분 `h(d, p)`, 정지 항 없음 | `PrefillCostModel` |
| `prefill_chunking` | prompt 분할 | 128 token chunk, 요청 단위 배타 | budget 단위(기본 2048), 끄면 분할만 사라짐 | `PrefillCostModel.chunk_tokens` |

### K. 실행 pipeline (측정 해석용)

| field | 의미 | NPU | GPU | 현재 |
|---|---|---|---|---|
| `in_flight_batches` | 동시에 떠 있는 batch | `UNKNOWN`(기록 없음) | 2(async scheduling 기본 on, `core.py:469–533`) — 종료·반납 시점과 dispatch 간격 해석에 영향 | 없음 |
| `startup_nonrequest_steps` | 요청 없이 실행되는 step | `UNKNOWN` | warmup 2 step(8 요청 dummy, KV pool 미사용, GTASK03) | 없음 |

## 2. 모형 코드가 각 field를 어디에 쓰는가 (참고)

| 모형 부분 | 필요한 field |
|---|---|
| B1 결정론 핵심·v1 추적기 | A(층·용량·소비), B 전체, C(`resume_allocates_first`, `hit_protection`), D, E, F(preemption이 있는 영역) |
| B1 확률 확장 | 위 + G(`max_running`), I·J(체류 시간) |
| B2 점유 | G, H, I, J |
| B3 격자 DP | H(`grid_unit`, `above_top`, `mixed_step_graph`), I(mode별 곡선) |
| B4 간섭 | J(`prefill_execution`이 `exclusive`일 때만 stall 항), I(`mixed`이면 혼합 증분) |

GTASK04에서 GPU 순차 생존을 모형 코드로 예측할 때 wrapper가 대신 넣어야 했던 것은 A의 `consumption`(생성 포함), B의 `window_start`·`initial_free_order`·`intra_request_loss`, D의 `cacheable_tokens`였다. 이 field들이 descriptor에 들어가면 wrapper가 필요 없다.

## 3. 결정이 필요한 점 (NPU 쪽 개편 담당에게)

1. 층 목록 도입 시 기존 `outer_*`/`inner_*` 이름을 호환용으로 남길지(과거 TASK 재현 command가 RBLN 인스턴스를 import한다).
2. `step_cost`를 mode별 dict로 바꿀 때 `StepCostModel`을 그대로 `decode` 항목으로 쓸지.
3. `UNKNOWN`으로 남은 NPU 값(`failed_admission_evicts`, `cache_registration`, `step_token_budget`, `in_flight_batches`)을 `None`으로 둘지, 측정 TASK를 열지.
