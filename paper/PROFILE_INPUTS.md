# 기판 profile 입력표 — 시뮬레이터와 해석 모형이 읽는 입력

작성: 2026-10-05, Advisor 지시문 15 작업 F. **측정 0, 예측 0.** 코드와 기존 기록에서 옮긴 값만 적는다.

## 0. 범위와 표기

입력을 읽는 코드:

| 코드 | 기판 | 읽는 방식 |
|---|---|---|
| `src/continuum/sim/engine.py` (`exclusive` 엔진) | NPU | `SubstrateDescriptorV2` + `SimConfig`. `semantics="descriptor"`면 규칙 field를 descriptor에서 읽고, 구현하지 않은 규칙은 거부한다. `semantics="legacy"`(기본)면 `SimConfig.release_rule`·`dummy_mode`·`eviction_policy` 스위치를 쓴다 |
| `src/continuum/sim/paged.py` (`mixed` 엔진) | GPU | `SubstrateDescriptorV2` + `SimConfig`. `prefill.execution`으로 dispatch |
| `experiments/npu/stage3/mt_predict.py::analytic` (v1) | NPU | v1 view(`RBLN_CA25_VLLM_RBLN_0111`)를 `config_search.descriptor_for(D, grid, batch)`로 구성별로 바꿔 읽는다. 규칙은 함수 선택으로 고정(allocation FIFO 생존식 `survival_v1.steady_state_survival`) |
| `experiments/npu/stage3/mt_predict_v11.py` (v1.1) | NPU | `RBLN_CA25_V2.with_config(grid, max_running, reuse_capacity)` |
| `experiments/gpu/multiturn/gpu_mt_model.py::analytic` (v1 GPU) | GPU | `gpu_cost.py` 상수 + `GpuConfig`(`num_gpu_blocks`, `max_num_seqs`, `capture_sizes`, `budget`) + `BLOCK = 16`. 규칙은 함수 선택으로 고정(release LRU 생존식 `lru_block_survival`) |
| `experiments/gpu/multiturn/gpu_mt_sim.py` (GPU wrapper sim) | GPU | GTASK09·11·20 예측을 낸 시뮬레이터. 통합 엔진(`paged.py`)과 GTASK09 44 cell 정확 일치(TASK89), GTASK20 주 예측기 12 cell 정확 일치(TASK103) |

값의 출처:

- NPU: `experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py::RBLN_CA25_V2`(provenance dict의 TASK 번호), `experiments/npu/stage3/plans/main/{OPCOST_SIM.json, CTXCOST_BLIND.json}`, `mt_predict.CONFIGS`.
- GPU: GPU 파일 영역에는 descriptor 인스턴스가 없다(`experiments/gpu/substrate/a6000_vllm_0220_draft.py`는 초안). 규칙·구성 값은 `tests/test_descriptor_v2.py::gpu_test_descriptor`(테스트 전용, provenance는 GTASK01–04), 비용은 `experiments/gpu/multiturn/gpu_cost.py`(GTASK05)와 `tests/gpu_sim_parity.py::descriptor`(이 둘을 묶는 함수), 구성은 `experiments/gpu/multiturn/selection/{selection.json, blind_grids.json}`.
- **†** = 구성 의존(격자·batch·pool 크기에 따라 값이 바뀜). 구성별 값은 §4.

## 1. KV 관리 규칙 (원고의 일곱 항목 = P09 규칙 field 7개)

| # | 규칙 (descriptor field) | NPU 값 | GPU 값 | 읽는 곳 | NPU 출처 | GPU 출처 |
|---|---|---|---|---|---|---|
| 1 | 축출 순서 (재사용 층 `layers[reuse].eviction_order`) | `allocation_fifo` (outer slot) | `release_lru` (block pool) | exclusive 엔진: `allocation_fifo`만 허용; paged 엔진: `release_lru`·`allocation_fifo`; 해석: 함수 선택 | `RBLN_CA25_V2` provenance `layers[1].eviction_order` — TASK14 source-read, TASK63 15/15·TASK64 5/5 | `gpu_test_descriptor` `layers[0].eviction_order` — GTASK01 source-read; GTASK11 `LRU_SUPPORTED` |
| 2 | 초기 free 순서 (`semantics.initial_free_order`) | `not_applicable` | `never_used_first` | paged 엔진(`never_used_first`만) | provenance — MODEL_V0 derived | GTASK04 measured |
| 3 | 요청 내부 손실 (`semantics.intra_request_loss`) | `all_or_nothing` | `tail_first` | exclusive: `all_or_nothing`만; paged: `tail_first`만 | TASK15 measured (절벽 1,920 → 0, 12/12) | GTASK01 source-read (`reversed(req_blocks)`) |
| 4 | 조회·할당 순서 (`semantics.resume_allocates_first`) | `True` (할당 후 조회) | `False` (조회 후 할당) | exclusive: `True`만; paged: `False`만; GTASK04 순차 예측 인자 | TASK15 measured; TASK72 R1 36/36 | GTASK01 source-read (`scheduler.py:594→721`) |
| 5 | hit 보호 (`semantics.hit_protection`) | `not_applicable` | `touch_before_alloc` | paged 엔진(`touch_before_alloc`만) | TASK15 derived | GTASK01 source-read (`kv_cache_manager.py:397→404`) |
| 6 | 보유 KV token (`semantics.kv_tokens_held`) | `computed` | `computed` (prompt + output − 1) | paged 엔진(`computed`만); 해석 GPU: `(P+g−1)/16` block | TASK08 derived | GTASK02 measured (H5) |
| 7 | 캐시 대상 (`semantics.cacheable_tokens`) | `prefill_only` | `computed` | exclusive: `prefill_only`만; paged: 둘 다 | TASK24 measured (271/271) | GTASK04 measured (resume hit 2,016 > 2,000) |

출처 표: `results/tables/P09.md`(TASK84, GTASK04), `docs/research/DESCRIPTOR_V2.md` §3·§7, `docs/research/gpu/DESCRIPTOR_REQUIREMENTS.md` §1 B–D.

## 2. 구성·실행 규칙

| 입력 | NPU 값 | GPU 값 | 읽는 곳 | NPU 출처 | GPU 출처 |
|---|---|---|---|---|---|
| KV 용량 (재사용 층 `capacity_units`) † | outer slot 8 (b8 artifact) / 16 (b16 artifact) = compile `batch_size` | `num_gpu_blocks − 1`: 800 (GTASK04), 1,899 (BASE), 2,299 (POOL·POOL+GRID) | 두 엔진; 해석 NPU `capacity=batch`, 해석 GPU `cap = num_gpu_blocks − 1` | TASK14 source-read (`ceil(512/64) = batch_size`), TASK08 (`kvcache_num_blocks = batch_size`); `descriptor_for`·`with_config`가 batch로 바꿈 | GTASK02 measured (`--num-gpu-blocks-override` − null); `selection.json` `base_pool` 1,900, `pool_pool` 2,300; GTASK04 서버 인자 801 |
| 예약 단위 (`reserved_units`) | 0 (outer), 1 (inner null block) | 1 (null block) | paged 엔진(앞쪽 block id 예약) | TASK14 | GTASK01 source-read (`block_pool.py:176`) |
| 재사용 층 (`reuse_layer`) | 1 (outer slot) | 0 (단일 block pool) | 두 엔진 | TASK15 measured (절벽 12/12) | GTASK04 measured |
| 관리 단위 (`unit_tokens`) | outer 8,192 token/slot; inner 128 | 16 token/block | exclusive: slot 수 계산; paged: 조회·할당·등록 단위; 해석 GPU `BLOCK = 16` | TASK08 source-read | GTASK02 measured |
| 소비 (요청당 단위 수) | `ceil(t/8192)` slot (8,192 미만이면 1) | `ceil((P+g−1)/16)` block | 두 엔진(`units_for(held_tokens)`) | TASK08 derived | GTASK02 measured |
| 정렬 크기 (hit 단위, `hit_formula`) | 128 token, 마지막 query token 예약: `floor(min(shared, q−1)/128)·128` | 16 token, 같은 형태 | exclusive 엔진 `hit_formula.hit_tokens`; 해석 NPU `D.inner_block_tokens`; paged 엔진 `unit_tokens`로 `(prompt−1)//16`; 순차 모형 `protocol` | TASK11 measured (10/10) | GTASK02 measured |
| release 시점 (`semantics.evictable_when`) | `immediate` | `immediate` | exclusive: `immediate`/`deferred`; paged: `immediate`만. legacy 경로는 `SimConfig.release_rule`(기본 `deferred`) | TASK72 derived (재생 1.000 대 0.934) | GTASK01 source-read |
| 생존 창 시작 (`semantics.window_start`) | `allocation` | `release` | 모형 순차 경로(`protocol`) | TASK14 derived | GTASK01 source-read |
| 실행 중 보호 (`semantics.active_pinned`) | `True` | `True` | 모형·엔진 공통 전제 | TASK63 measured | GTASK01 source-read |
| dummy 소비 (`semantics.dummy_mode`) | `pre_evict` (decode step마다 `0 < n < 상한`이면 가장 오래된 비활성 slot 축출) | `none` | exclusive: `none`/`pre_evict`/`reserved`; paged: `none`만. legacy 경로는 `SimConfig.dummy_mode`(기본 `off`) | TASK63 measured (74/74), TASK72 재생 1.000 대 `reserved` 0.847 | GTASK01 source-read (`PAD_SLOT_ID`) |
| dummy 상한 (`semantics.dummy_ceiling`) | `None` (UNKNOWN; 최상위 격자 = `max_running`일 때만 엔진이 받음) | `not_applicable` | exclusive 엔진 검사 | TASK69 | GTASK01 source-read |
| preemption (`semantics.preemption`) | `none` | `recompute` (FCFS 마지막 running, 끌 수 없음, cache 유지) | exclusive: `none`만; paged: 필요해지면 `PreemptionNeeded`로 중단(시뮬레이션 안 함) | TASK08 derived | GTASK01 source-read; GTASK08 pool 하한 1,857 block으로 preemption 불가 구성 선정 |
| 동시 실행 상한 (`admission.max_running`) † | 8 (BASE) / 16 (BATCHONLY·TUNED·DP) — `compile` | `max_num_seqs` 1 (GTASK04) / 8 (multi-turn) — `server_arg` | 두 엔진(`SimConfig.max_running_requests`와 같아야 함); 해석 B2 `max_running` | TASK08 source-read | GTASK04, `selection.json` `max_num_seqs` 8 |
| step token 예산 (`admission.step_token_budget`) | `None` (UNKNOWN; exclusive 엔진은 읽지 않음) | 2,048 | paged 엔진(필수); 해석 GPU `_chunks_inc(budget=2048)` | DESCRIPTOR_V2 §3 | GTASK02 measured; `selection.json` `budget` |
| 격자 크기 (`grid.sizes`) † | BASE (1,2,4,8); BATCHONLY (1,2,4,8,16); TUNED (1,4,6,8,10,16); DP8 (1,2,3,4,6,16) | BASE·POOL (1,2,4,8,16); POOL+GRID (1,5,7,8,16) (N = 20·22·24·25·28) | 두 엔진; 해석 `bucket_for`·padding | TASK13 measured (b8 사상), `mt_predict.CONFIGS`, `DP_GRIDS.json`(TASK78·81) | GTASK02 measured; `selection.json` `base_grid`·`per_n_grid`, `blind_grids.json` |
| 격자 기준 단위 (`grid.unit`) | `requests` | `tokens` (decode + prefill token 합) | exclusive: 요청 수 사상; paged: `tokens` 필수 | TASK13 measured | GTASK01 source-read |
| 격자 위 초과 (`grid.above_top`) | `impossible` | `eager` | 두 엔진 | TASK08 derived | GTASK01 source-read |
| 혼합 step graph (`grid.mixed_step_graph`) | `not_applicable` | `piecewise` | paged 엔진(mode 결정) | TASK22 measured | GTASK01 source-read |
| 격자 값 출처 (`grid.value_source`) | `compile` | `server_arg` | 구성 변경 시 재측정 범위 판단(엔진은 읽지 않음) | TASK23 measured | GTASK02 measured |
| prefill 실행 방식 (`prefill.execution`) | `exclusive` (prefill이 step 독점, decoder 정지) | `mixed` (chunk가 decode step에 섞임) | `simulate()`의 엔진 dispatch; 해석 B4 | TASK22 measured | GTASK01 source-read |
| prefill chunk (`prefill.chunk_tokens`) | 128 | 2,048 (= budget) | exclusive: prefill 비용 `ceil(n/128)`; paged: chunk 분할 | TASK22 measured | GTASK02 measured |
| 미측정 격자 폭의 decode 고정 비용 † | 측정 폭(1,2,4,8) 사이 선형 보간, 밖은 양끝 두 점으로 외삽(`descriptor_for` = `with_config` = `grid.interpolated_fixed_costs`) | 해당 없음(1–16 전 폭 측정) | 원래 비용 경로의 해석·sim | `experiments/npu/analysis/config_search.py::descriptor_for` | `gpu_cost.F_MS` 1–16 |

읽지 않는 descriptor field(참고): `semantics.failed_admission_evicts`(NPU `None`, GPU `False`), `semantics.cache_registration`(NPU `None`, GPU `at_allocation`), `admission.admission_requires_full_prompt`(NPU `None`, GPU `True`), `pipeline.*`(NPU `None`, GPU 2·2). 두 엔진 모두 이 field를 분기에 쓰지 않는다.

## 3. 성능 입력

### 3.1 decode step 비용

| 입력 | NPU 값 | GPU 값 | 쓰는 예측기 | NPU 출처 | GPU 출처 |
|---|---|---|---|---|---|
| 원래 decode 비용 (형태) | `step = fixed[bucket] + intercept + marginal · n` (초) | FULL: `F[b] + g · n` (ms); 격자 밖: eager 표 | NPU: v1, v1.1, sim legacy, sim descriptor, 3·4의 가격; GPU: 해석 v1, sim LRU/FIFO, GTASK20 (3)·(1) 기반 | `rbln_ca25_vllm_rbln_0111.py::STEP_COST` | `gpu_cost.py::decode_ms` |
| 원래 decode 고정 비용 † | fixed (ms): b1 9.870, b2 10.420, b4 10.825, b8 12.970 (측정); 보간·외삽: b3 10.6225, b6 11.8975, b10 14.0425, b16 17.260 | `F_MS` (ms) b1 13.367 … b8 13.295 … b16 13.717 (1–16 전부, 13.17–13.72) | 위와 같음 | TASK13 (model + sampler p50 per bucket) | GTASK05 FULL fit (G1+G3, 최대 잔차 0.035 ms) |
| 원래 decode 요청당 기울기 | marginal 0.0413 ms/요청, intercept 0.501 ms | `G_MS` 0.04061 ms/요청 | 위와 같음 | TASK13 잔차 회귀 | GTASK05 |
| eager decode (격자 밖) | 해당 없음(`impossible`) | n = 9–16: 19.3385, 19.311, 19.483, 19.5295, 19.448, 19.4765, 19.508, 19.5405 ms | GPU 전 예측기 | — | GTASK05 G2 중앙값 |
| 운영 decode 비용 † (`F[b] + β·n`, 초) | BASE F (ms) 10.362/10.878/11.436/12.920, β 0.1398 ms; BATCHONLY 10.277/11.031/11.135/13.268/16.426, β 0.1312 ms; TUNED (1,4,6,8,10,16) 10.231/11.188/12.032/12.741/13.793/16.381, β 0.1376 ms; DP (1,2,3,4,6,16) 10.351/11.143/11.176/11.539/12.532/17.824, β 0.0135 ms | 해당 없음(GPU에 같은 예측기 없음) | NPU 3의 `sim_op`(시간 진행만) | `OPCOST_SIM.json` ← TASK92 `stepcost_op.json` (SHA256 `4ca494a7…`) | — |
| context 비용 기본 decode (F1 `f(b) + β·n`, 초) † | BASE f (ms) 10.451/11.029/11.566/13.463, β −0.00491 ms; BATCHONLY 10.423/11.273/11.666/14.075/18.299, β −0.06944 ms; TUNED 10.398/11.446/12.573/13.463/14.729/17.455, β −0.01732 ms | 기본 decode는 GTASK05 가격 그대로 | NPU 4의 `sim_ctx_op`·`sim_ctx`; GPU 7의 (1) | `CTXCOST_BLIND.json` ← TASK97 (BASE·TUNED), TASK100 (BATCHONLY), `ctxcost_v2.json` (SHA256 `ad74845c…`) | `predict_blind.py` (가격 = `gpu_cost.step_ms`) |
| GPU 시간 척도 보정 | 해당 없음 | (2) 가격 × 1.210; (2′) GTASK11 관측 mode별 비 분포 | GPU 7의 (2)·(2′) (보고) | — | GTASK13 (`predict_blind.X_CAL`), GTASK13 `obs.json` |

### 3.2 context 비용 c

| 입력 | NPU 값 | GPU 값 | 쓰는 예측기 | NPU 출처 | GPU 출처 |
|---|---|---|---|---|---|
| c (context token당 decode step 증가) † | BASE 1.4535e-7 s/token (0.145 µs); BATCHONLY 1.4596e-7 (0.146 µs); TUNED 1.4900e-7 (0.149 µs) | 2.120e-4 ms/token (0.212 µs) | NPU 4 (1); GPU 7 (1) | `CTXCOST_BLIND.json` `c_s_per_token` ← TASK97·TASK100 F1 | `predict_blind.C_CTX` ← GTASK18 F1 (`ctx_result/summary.json`) |
| 기준 context (`reference_tokens_per_decode`) | 0 (context 항과 함께 적합) | 128 token/decode (GTASK05 가격 부하: prompt 64 + 평균 생성 위치 64) | 위와 같음 | DESCRIPTOR_V2 §8 | `predict_blind.L_PRICE`, DESCRIPTOR_V2 §8 |
| 적용 step | decode 요청이 있는 step: `+ c · Σ_ctx` | decode가 있는 모든 mode(FULL·혼합·eager): `+ c · (Σ_ctx − decodes · 128)` | — | DESCRIPTOR_V2 §8 | GPU_BLIND_COLLAPSE_PREREG §3 |
| 단위 | `s` (exclusive 엔진) | `ms` (paged 엔진) | 엔진이 단위 불일치를 거부 | DESCRIPTOR_V2 §8 | DESCRIPTOR_V2 §8 |
| 원래·운영 비용 예측기 | context 항 없음 (`context_cost = None`) | 없음 (`price`) | NPU 1–3 전부, 4의 (2); GPU 5·6, 7의 (3) | — | — |

### 3.3 prefill 비용

| 입력 | NPU 값 | GPU 값 | 쓰는 예측기 | NPU 출처 | GPU 출처 |
|---|---|---|---|---|---|
| 원래 prefill 비용 | 배타: `ceil(n/128) · (0.021206 s + 6.399e-7 s · n)` (n = 계산 token) | 혼합 증분: PIECEWISE (총 token ≤ 격자 최상위) [0, 1.5] ms (`lo` 0, `hi` 1.5); eager (총 token > 최상위) p 의존 표 | NPU: v1, v1.1, sim legacy, sim descriptor, 3·4의 가격; GPU: 전 예측기 | `PREFILL_COST` ← TASK22 (4점 적합, 최대 잔차 2.4 ms) | `gpu_cost.PIECEWISE_INC_MS`, `_EAGER_*` ← GTASK05 |
| GPU eager 혼합 증분 표 (d = 4) | 해당 없음 | p = 32/64/128/256/512/1024/2048 token: `lo` 0.0/0.0/1.973/12.734/31.784/75.750/139.024 ms, `hi` 0.821/1.728/5.647/16.726/35.561/79.168/145.642 ms; 사이는 선형, p < 32는 (0,0)까지 선형, p > 2048은 비례 | GPU 전 예측기 (bound별) | — | GTASK05 (lo = lag-1 clamp, hi = 3-step window) |
| decoder 없는 prefill step | 해당 없음 | 폭 1 decode 기준선 + 증분 | GPU 전 예측기 | — | `gpu_cost.step_ms` docstring |
| 운영 prefill 비용 † (배타, `ceil(n/128) · (a + d·n)`) | BASE a 22.701 ms, d 2.2255e-7 s/token; BATCHONLY 23.393 ms, 5.385e-8; TUNED 22.930 ms, 1.8287e-7; DP 23.061 ms, 1.3575e-7 | 해당 없음 | NPU 3 `sim_op`, 4 `sim_ctx_op` (시간 진행만) | `OPCOST_SIM.json` ← TASK92 `op-prefill-mt` | — |

## 4. 구성별 값 (†의 실제 값)

### 4.1 NPU (artifact = compile 구성)

| 구성 | 격자 | batch = `max_running` = outer slot | 원래 decode fixed (ms) | 쓰인 실험 |
|---|---|---|---|---|
| BASE | (1,2,4,8) | 8 | 9.870 / 10.420 / 10.825 / 12.970 (전부 측정) | 1a·1b·2·3·4 |
| BATCHONLY | (1,2,4,8,16) | 16 | 위 + b16 17.260 (외삽) | 1a·1b·2·3·4 |
| TUNED | (1,4,6,8,10,16) | 16 | b1 9.870, b4 10.825, b6 11.8975 (보간), b8 12.970, b10 14.0425 (외삽), b16 17.260 (외삽) | 1a·1b·2·3·4 |
| DP8 | (1,2,3,4,6,16) | 16 | b3 10.6225 (보간), b6 11.8975 (보간), b16 17.260 (외삽) | 1a (N = 8) |

- 원래 비용 step 시간 = fixed + 0.501 ms + 0.0413 ms · n (예: BASE n = 1 10.412 ms, n = 8 13.801 ms; batch 16 n = 16 18.422 ms). 값은 `descriptor_for(RBLN_CA25_VLLM_RBLN_0111, grid, batch)`로 계산.
- inner 층 용량은 구성 변형에서도 512로 남는다(`descriptor_for`·`with_config`가 바꾸지 않음). exclusive 엔진은 기본 `cache_granularity="outer"`에서 inner 용량을 읽지 않는다.
- 운영 비용·context 비용 값은 artifact별 측정값이며(§3), 보간하지 않았다.

### 4.2 GPU (server 인자 구성)

| 구성 | `num_gpu_blocks` (가용) | 격자 (`cudagraph_capture_sizes`) | `max_num_seqs` | budget | 쓰인 실험 |
|---|---|---|---|---|---|
| 순차 (GTASK04) | 801 (800) | (1,2,4,8,16) | 1 | 2,048 | 5 |
| BASE | 1,900 (1,899) | (1,2,4,8,16) | 8 | 2,048 | 6a·6b·7 |
| POOL | 2,300 (2,299) | (1,2,4,8,16) | 8 | 2,048 | 6a·6b·7 |
| POOL+GRID | 2,300 (2,299) | (1,5,7,8,16) (N = 20·22·24·25·28) | 8 | 2,048 | 6a·7 |

실험 번호는 [PREREG_TABLE.md](PREREG_TABLE.md) §1의 행 번호다.

## 5. 기판이 아닌 입력 (참고)

시뮬레이터 `SimConfig`와 해석 모형이 함께 읽는 workload·창 입력. 두 기판에서 같은 의미다.

| 입력 | 값 | 출처 |
|---|---|---|
| session·turn 구조, gap, 생성 길이, prompt segment | plan 파일(`experiments/npu/stage3/plans/main/main-n*-r*.json`, `experiments/gpu/multiturn/plans/{main,blind}/*.json`) | `continuum.workload.multiturn.MultiTurnPlan` |
| `session_start_s`, `successor`, `slot_of`, `n_slots` | plan에서 `to_sim_inputs`로 생성 | TASK77 |
| 평가 창 | `WindowRule(cycle_s = plan.spec["cycle_s"], eval_s = 120 s)`; NPU exclusive 엔진은 창을 사후 적용(`mt_predict.simulate_plan`), paged 엔진은 `SimConfig.window_rule`로 창 끝 뒤 새 요청을 내지 않음 | TASK77, DESCRIPTOR_V2 §7 |
| `client_overhead_s` | 0 (기본) | `SimConfig` |
