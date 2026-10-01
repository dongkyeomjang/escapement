# SubstrateDescriptor v2 — 구조, 사용법, 요구사항 대응표

작성: 2026-09-30, [TASK84](TASK84.md) (Advisor 지시문 06 작업 B). 입력: GPU branch `docs/research/gpu/DESCRIPTOR_REQUIREMENTS.md`(GTASK06, `origin/gpu-a6000`에서 읽기만 함). 코드: [`src/continuum/substrate/v2.py`](../../src/continuum/substrate/v2.py).

## 1. 원칙

요구사항 문서 §0을 따른다.

1. **pool은 층의 목록**(`layers`)이고, 재사용을 정하는 층은 `reuse_layer`가 가리킨다.
2. **의미론 field는 값이 아니라 규칙**이다(`Semantics`, `PoolLayer.eviction_order`).
3. **값의 출처**(`value_source`: `compile` | `server_arg` | `fixed`)를 pool 층·격자·`max_running`에 적는다. 구성을 바꿀 때 무엇을 다시 재거나 compile해야 하는지가 여기서 갈린다.
4. 값이 있는 모든 leaf는 점 경로(`"layers[1].capacity_units"`, `"semantics.cacheable_tokens"`)로 **`Provenance`가 필수**다. 없으면 생성이 실패한다. provenance가 값 없는 field를 가리켜도 실패한다.
5. **`None` = 확정되지 않음**. 0이나 기본값이 아니다. 기판에서 생기지 않는 규칙은 `"not_applicable"`(`NA`) **값**이고 provenance가 필요하다. `unknown_paths()`가 `None` leaf 목록을 준다(preemption이 `none`이면 그 하위 field는 제외).

## 2. 구조

```
SubstrateDescriptorV2
├─ name
├─ layers: tuple[PoolLayer]      name, unit_tokens, capacity_units, reserved_units,
│                                value_source, eviction_order
├─ reuse_layer: int
├─ semantics: Semantics          evictable_when, window_start, intra_request_loss,
│                                initial_free_order, active_pinned, resume_allocates_first,
│                                hit_protection, failed_admission_evicts, cache_registration,
│                                kv_tokens_held, cacheable_tokens, dummy_mode, dummy_ceiling,
│                                preemption(+ trigger, victim, disableable, keeps_cache)
├─ admission: Admission          max_running, max_running_source, step_token_budget,
│                                admission_requires_full_prompt
├─ grid: Grid                    sizes, unit, value_source, above_top, mixed_step_graph
├─ hit_formula: HitFormula
├─ step_cost: {"decode"|"mixed"|"eager": StepCostModel | None}
├─ step_cost_measurement: str
├─ prefill: PrefillSpec          execution, cost(PrefillCostModel, exclusive only), chunk_tokens
├─ pipeline: Pipeline            in_flight_batches, startup_nonrequest_steps
├─ provenance: {path: Provenance}
└─ notes
```

파생: `reuse_pool`, `eviction_order`(재사용 층의 것), `max_running`, `step_time_s(n)`(uniform decode, 격자 위), `grid.width_for(n)`(최상위 초과는 `eager`면 `None`, `impossible`이면 오류), `PoolLayer.units_for(tokens)`, `Semantics.held_tokens(P, g)`·`cacheable_prefix(P, g)`.

구성 변형: `with_config(grid=, max_running=, reuse_capacity=)` — 미측정 격자 폭의 decode 고정 비용은 `config_search.descriptor_for`와 **bit 동일**한 보간 규칙으로 채우고 provenance note에 표시한다.

v1 view: `legacy_view()`는 이전 모든 script가 읽던 v1 `SubstrateDescriptor`를 돌려준다(2층·재사용 층 1·allocation FIFO·요청 수 격자일 때만). RBLN 인스턴스의 v1 객체 `RBLN_CA25_VLLM_RBLN_0111`은 이제 `RBLN_CA25_V2.legacy_view()`이며, provenance 문구를 제외한 모든 field가 이전과 같다([TASK84](TASK84.md) 회귀).

## 3. 요구사항 대응표

`DESCRIPTOR_REQUIREMENTS.md` §1의 항목 → v2 field. RBLN 값은 [`rbln_ca25_vllm_rbln_0111.py`](../../experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py)의 `RBLN_CA25_V2`, GPU 값은 **테스트 전용** descriptor(`tests/test_descriptor_v2.py::gpu_test_descriptor`, GPU 인스턴스가 아님).

| 요구 항목 | v2 field | RBLN (`RBLN_CA25_V2`) | GPU 테스트 descriptor |
|---|---|---|---|
| A `layers[].name` | `PoolLayer.name` | `inner_block`, `outer_slot` | `block_pool` |
| A `unit_tokens` | `PoolLayer.unit_tokens` | 128, 8,192 | 16 |
| A `capacity_units` | `PoolLayer.capacity_units` | 512, 8 | `num_gpu_blocks − 1` |
| A `reserved_units` | `PoolLayer.reserved_units` | 1, 0 | 1 |
| A `value_source` | `PoolLayer.value_source` | `compile` | `server_arg` |
| A `consumption` | `PoolLayer.units_for(Semantics.held_tokens(P, g))` = `ceil(held / unit)` | slot: `ceil(t/8192)` = `ceil(ceil(t/128)/64)` | `ceil((P+g−1)/16)` |
| A `reuse_layer` | `reuse_layer` | 1 | 0 |
| A `physical_tokens` / `usable_tokens` | 파생: `(capacity + reserved) × unit` / `capacity × unit` | — | — |
| B `eviction_order` | `PoolLayer.eviction_order`(층마다) | 층 0 `release_lru`, 층 1 `allocation_fifo` | `release_lru` |
| B `evictable_when` | `Semantics.evictable_when` | `immediate` | `immediate` |
| B `window_start` | `Semantics.window_start` | `allocation` | `release` |
| B `intra_request_loss` | `Semantics.intra_request_loss` | `all_or_nothing` | `tail_first` |
| B `initial_free_order` | `Semantics.initial_free_order` | `not_applicable` | `never_used_first` |
| B `active_pinned` | `Semantics.active_pinned` | `True` | `True` |
| C `resume_allocates_first` | `Semantics.resume_allocates_first` | `True` | `False` |
| C `hit_protection` | `Semantics.hit_protection` | `not_applicable` | `touch_before_alloc` |
| C `failed_admission_evicts` | `Semantics.failed_admission_evicts` | `None` (UNKNOWN) | `False` |
| C `cache_registration` | `Semantics.cache_registration` | `None` (UNKNOWN) | `at_allocation` |
| D `hit_formula.*` | `hit_formula` (v1 `HitFormula`) | 128, 마지막 token 예약 | 16, 같음 |
| D `cacheable_tokens` | `Semantics.cacheable_tokens` (+ `kv_tokens_held`) | `prefill_only` | `computed` |
| E `dummy_mode` | `Semantics.dummy_mode` | `pre_evict` | `none` |
| E `dummy_trigger` | `Semantics.dummy_ceiling`(`0 < n < 상한`의 상한) | `None` (UNKNOWN, TASK69) | `not_applicable` |
| E `reserved_units` | A로 이동(`PoolLayer.reserved_units`) | — | — |
| F `preemption` | `Semantics.preemption` | `none` | `recompute` |
| F `preemption_trigger` / `_victim` / `_disableable` / `preempted_keeps_cache` | `Semantics.preemption_*` | 해당 없음(preemption `none`) | 문구 / `fcfs` / `False` / `True` |
| G `max_running` | `Admission.max_running` (+ `max_running_source`) | 8 (`compile`) | `--max-num-seqs` (`server_arg`) |
| G `step_token_budget` | `Admission.step_token_budget` | `None` (UNKNOWN) | 2048 |
| G `admission_requires_full_prompt` | `Admission.admission_requires_full_prompt` | `None` (UNKNOWN) | `True` |
| H `grid_sizes` | `Grid.sizes` | (1,2,4,8) | (1,2,4,8,16) |
| H `grid_unit` | `Grid.unit` | `requests` | `tokens` |
| H `grid_value_source` | `Grid.value_source` | `compile` | `server_arg` |
| H `above_top` | `Grid.above_top` | `impossible` | `eager` |
| H `mixed_step_graph` | `Grid.mixed_step_graph` | `not_applicable` | `piecewise` |
| H `graph_modes` | `step_cost`의 key(`decode`/`mixed`/`eager`) | `decode`만 | 셋 |
| I `step_cost.decode` | `step_cost["decode"]` (v1 `StepCostModel` 그대로) | TASK13 곡선 | `None`(테스트 descriptor는 비용 미기재; GTASK05 값은 GPU 인스턴스 몫) |
| I `step_cost.mixed` / `.eager` | `step_cost["mixed"]` / `["eager"]` | key 없음(발생 불가) | `None` |
| I `step_cost.measurement` | `step_cost_measurement` | model span + sampler p50 | `None` |
| J `prefill_execution` | `PrefillSpec.execution` | `exclusive` | `mixed` |
| J `prefill_cost` | `PrefillSpec.cost` (배타 전용 `PrefillCostModel`; `mixed`에서 값을 넣으면 거부) | TASK22 | `None` |
| J `prefill_chunking` | `PrefillSpec.chunk_tokens` | 128 | 2048 |
| K `in_flight_batches` | `Pipeline.in_flight_batches` | `None` (UNKNOWN) | 2 |
| K `startup_nonrequest_steps` | `Pipeline.startup_nonrequest_steps` | `None` (UNKNOWN) | 2 |

요구사항 문서 §3의 결정 요청에 대한 처리:

1. **`outer_*`/`inner_*` 이름**: v2에는 없다. v1 객체를 `legacy_view()`로 계속 만들어 과거 재현 command가 그대로 돈다.
2. **`step_cost`**: mode별 dict이고 `StepCostModel`을 `"decode"` 항목으로 그대로 쓴다. 발생하지 않는 mode는 key를 두지 않고, 발생하지만 미측정인 mode는 `None`이다.
3. **NPU `UNKNOWN` 값 4개**(`failed_admission_evicts`, `cache_registration`, `step_token_budget`, `in_flight_batches`)와 `dummy_ceiling`·`admission_requires_full_prompt`·`startup_nonrequest_steps`: **`None`으로 둔다**. 측정 TASK는 열지 않았다(Advisor 결정 대상).

## 4. 코드가 v2를 읽는 곳

| 부분 | v2 사용 |
|---|---|
| 시뮬레이터 `simulate` | v1·v2 둘 다 받는다. `SimConfig.semantics="descriptor"`면 `evictable_when`·`dummy_mode`·재사용 층 `eviction_order`를 descriptor에서 읽고, 구현하지 않은 규칙(release LRU, tail-first, 조회 후 할당, 생성 token 캐시, preemption, 혼합 prefill)은 **오류**로 거부한다. 상한이 확정되지 않은 dummy는 최상위 격자 = `max_running`일 때만 받는다. **기본값은 `"legacy"`** — 원고 시점 동작(config 스위치 `release_rule`·`dummy_mode`·`dummy_block`·`eviction_policy`, 기본 지연 release·dummy 없음)을 bit 단위로 재현한다. **새 예측은 `semantics="descriptor"`를 쓴다**(결정 8-4) |
| 기준 재생 `FifoReplay.for_descriptor` | v1·v2 둘 다. v2는 재사용 층이 `allocation_fifo`여야 한다 |
| 모형 `continuum.model.protocol.sequential_protocol` | 순차 프로토콜의 생존·hit를 v2 규칙만으로 계산(층 용량·소비·보유 token·캐시 대상·축출 순서·창·요청 내부 손실·조회/할당 순서·hit 보호). GTASK04 wrapper가 넣던 것이 모두 descriptor에서 온다 |
| B2·v1.1 점유 | `max_running`을 `admission.max_running`에서 읽는다([TASK85](TASK85.md) 예정) |

## 5. GPU 에이전트를 위한 사용법

```python
from continuum.substrate import (NA, Admission, Grid, HitFormula, Pipeline, PoolLayer,
                                 PrefillSpec, Provenance, Semantics, SubstrateDescriptorV2)

d = SubstrateDescriptorV2(
    name="...", layers=(PoolLayer(name="block_pool", unit_tokens=16, capacity_units=N - 1,
                                  reserved_units=1, value_source="server_arg",
                                  eviction_order="release_lru"),),
    reuse_layer=0, semantics=Semantics(...), admission=Admission(...), grid=Grid(...),
    hit_formula=HitFormula(block_tokens=16), step_cost={"decode": StepCostModel(...), ...},
    step_cost_measurement="...", prefill=PrefillSpec(execution="mixed", cost=None, chunk_tokens=...),
    pipeline=Pipeline(...), provenance={"layers[0].unit_tokens": Provenance(...), ...})
d.unknown_paths()   # 아직 확정되지 않은 field
```

- 인스턴스는 **GPU 파일 영역**(`experiments/gpu/substrate/`)에 둔다(결정 7). `tests/test_descriptor_v2.py::gpu_test_descriptor`는 구조 확인용 테스트 값이며 GPU 인스턴스를 대신하지 않는다.
- provenance key는 `value_paths()`가 내는 점 경로다. 중첩 객체 전체에 하나를 붙이려면 부모 경로를 key로 쓴다(`"hit_formula"`, `"step_cost.decode"`).
- `server_arg` 값은 구성마다 바뀐다. 구성별 인스턴스는 `with_config`나 인스턴스 생성 함수(server 인자 → descriptor)로 만든다.
- 현재 시뮬레이터는 GPU 규칙을 구현하지 않는다(거부됨). 모형 코드의 순차 경로(`sequential_protocol`)와 v1 생존·B2 점유는 v2 field로 계산된다.

## 6. 회귀 ([TASK84](TASK84.md))

`descriptor_v2_regression.sh`(변경 전·후) + `descriptor_v2_compare.py`: 표 29개 + manifest, `PREDICTIONS.json`·`PREDICTIONS_EXT.json` 재계산, R1–R5′·R4·R5, A4, self-check, TASK74 sim 의미론 산출 — 72 파일 중 **63 byte 동일**(표 59·예측 2·A4·sim 의미론). 나머지 9개(R1–R5′ JSON 6, `run_meta`, self-check, 표 manifest)는 실행 시각·소요 시간·HEAD를 파일 안에 적는 파일이라 byte 동일이 원리상 불가능하고, 그 key를 뺀 내용은 **전부 같다**. `semantics="descriptor"` = 명시적 관측 의미론 스위치 75/75 run 동일. `tests/test_descriptor_v2.py` PASS(GTASK04 60/60 포함).
