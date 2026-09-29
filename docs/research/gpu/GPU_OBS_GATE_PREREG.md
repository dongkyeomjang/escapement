# GPU 관측 patch 검증 관문 선등록 (G1–G3)

## 문서 성격

GPU 지시문 G-02 작업 B의 **선등록**이다. 이 문서, patch 파일, 적용 script, collector, 실행·판정 script를 담은 commit이 만들어진 **뒤에** patch를 처음 적용한다. 판정 결과는 [GTASK03](GTASK03.md)에 쓴다. 형식은 NPU [TASK12](../TASK12.md)(결정 3 집행)의 관문 3개를 따른다. 측정 후 기준을 완화하지 않는다.

## 승인 범위 (지시문 G-02 §2.1–2.2)

- 대상: venv `/home/csdc/kyeom/envs/vllm-0.22.0`의 `vllm 0.22.0` 설치본(저장소 밖, 이 서버 전용). v2 model runner 고정.
- 관측 지점 두 곳: (1) v2 runner step dispatch, (2) scheduler admission(WAITING 요청의 조회·할당).
- 축출 귀속은 patch 없이 `--kv-events-config`(zmq) + collector로.

## patch 내용

파일 [`experiments/gpu/patches/vllm-0.22.0/escapement_obs.patch`](../../../experiments/gpu/patches/vllm-0.22.0/escapement_obs.patch), 적용·복구 [`apply.sh`](../../../experiments/gpu/patches/vllm-0.22.0/apply.sh)(`status|apply|revert`, 두 파일 SHA256 guard, version guard, 적용 후 AST 검사).

| 대상 | 원본 SHA256 | patch 후 SHA256 | 추가 |
|---|---|---|---|
| `vllm/v1/core/sched/scheduler.py` | `41ff2e52…bb5983` | `6054015f…23a1` | module 상수 1줄 + `LOOKUP` 로그(`get_computed_blocks` 직후) + `ALLOC`/`ALLOC_FAIL` 로그(`allocate_slots` 직후) |
| `vllm/v1/worker/gpu/model_runner.py` | `c5332aad…8a16` | `dc6221e9…cf83` | module 상수 1줄 + `GSTEP` 로그(`dispatch_cg_and_sync_dp` 뒤, 빈 step return 뒤, `not dummy_run`일 때만) |

- 추가 32줄, **삭제·수정 0줄**. 모든 추가 코드는 `if _ESC_OBS:` 안의 `logger.info` 호출이고, `_ESC_OBS`는 import 시 `ESCAPEMENT_OBS == "1"`로 한 번 정해진다. 환경변수가 없으면 patch된 코드도 아무것도 출력하지 않는다.
- 로그가 읽는 값: `request_id`, `request.num_tokens`, `num_new_local_computed_tokens`, `new_blocks.blocks` 길이, `num_new_tokens`, `num_computed_tokens`, `block_pool.get_num_free_blocks()`(읽기 전용 속성), step의 `num_reqs`, `num_toks`, `max_query_len`, `uniform_tok_count`, `batch_desc.num_tokens`, `batch_desc.cg_mode`, `time.perf_counter()`, `time.time()`. **어떤 상태도 쓰지 않으며** scheduling·KV 할당·sampling·dispatch 결정에 들어가는 값을 바꾸지 않는다.

로그 형식:

```
[GSTEP] t=<perf_counter> wall=<epoch> reqs=<n> toks=<scheduled tokens> maxq=<max query len> uniform=<int|None> padded=<graph tokens> mode=<FULL|PIECEWISE|NONE>
[GPFX] LOOKUP req=<id> t=… wall=… num_tokens=<prompt+output tokens> hit=<local hit tokens> free=<free blocks>
[GPFX] ALLOC|ALLOC_FAIL req=<id> t=… wall=… new_blocks=<n|-1> scheduled=<tokens> computed=<hit tokens> free=<free blocks after>
```

KV events collector [`kv_events_collector.py`](../../../experiments/gpu/obs/kv_events_collector.py): zmq SUB, vLLM import 없이 msgpack generic decode, engine step batch마다 JSON 1줄(`seq`, `ts`, `recv_wall`, `BlockStored{block_hashes, token_ids, …}`, `BlockRemoved{block_hashes}`).

## 실행 설계

[`run_gates.sh`](../../../experiments/gpu/obs/run_gates.sh) 한 번 실행: arm A(원본) → `apply` → arm B(patch) → `revert` → 판정([`gate_judge.py`](../../../experiments/gpu/obs/gate_judge.py)).

| 요소 | arm A | arm B |
|---|---|---|
| 설치본 | 원본(`status` = pristine 확인 후 시작) | patch(`status` = patched 확인 후 시작) |
| `ESCAPEMENT_OBS` | 없음 | `1` |
| KV events | 끔 | `--kv-events-config` zmq `tcp://127.0.0.1:5557` + collector |
| 공통 server 인자 | `--revision 1cfa9a72… --dtype bfloat16 --max-model-len 8192 --seed 20260929 --generation-config vllm --enable-prompt-tokens-details --block-size 16 --num-gpu-blocks-override 2048 --max-num-seqs 8 --max-num-batched-tokens 2048 --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 6, 8]}'`, `CUDA_VISIBLE_DEVICES=0`, async scheduling 기본(on) | 같음 |
| 요청 (같음) | 순차 15건: 텍스트 prompt 3회(`max_tokens 64`), H1·H2·H3·H4a·H4b seed/probe 10건(`max_tokens 1`, GTASK02와 같은 token-id prompt), H5 seed(1,000, `max_tokens 40`)/probe 2건. 이어서 동시 3건·5건(텍스트 변형, `max_tokens 64`). 모두 greedy, `ignore_eos`. 순차 요청은 전후 `/metrics` 스크랩 | 같음 |

preemption 구조적 불가 확인: 가용 2,047 block ≥ `max_num_seqs 8 × ceil(1,046/16) = 528`.

## 관문과 기준 (전부 사전 고정)

**G1 의미론** (arm B) — 아래 (a)–(f) 전부 성립:

- (a) `LOOKUP` 수 = `ALLOC` 수 = 요청 수(23) = `vllm:request_success_total` 증분, `ALLOC_FAIL` 0.
- (b) 요청마다(응답 id가 로그 `req`의 prefix인 것으로 join) `LOOKUP hit` = 응답 `cached_tokens`(부재는 서버 로그에 `enable_prompt_tokens_details: True`가 있을 때만 0으로 읽는다). 순차 요청은 추가로 `prompt_tokens_cached_total` 증분 = `prefix_cache_hits_total` 증분 = 같은 값. 23/23.
- (c) Σ `GSTEP.toks` = Σ_요청 (`prompt_tokens − cached + completion_tokens − 1`).
- (d) 첫 동시 요청의 `LOOKUP` 이전 `GSTEP` 수 = Σ_순차 (`ceil((prompt − cached)/2048) + completion − 1`).
- (e) 모든 `GSTEP`에서 (`padded`, `mode`) = 규칙값: `toks ≤ 8`이면 `padded` = `[1,2,4,6,8]` 중 `toks` 이상 최소값, `maxq = 1`이면 `FULL` 아니면 `PIECEWISE`; `toks > 8`이면 `padded = toks`, `NONE`(GTASK01 항목 6의 source-read 규칙).
- (f) KV events: `BlockRemoved` 0건(가용 block 안에서 미사용 block이 먼저 쓰이므로), H1–H4b seed prompt의 full block(`floor(L/16)`개씩) 전부가 `BlockStored.token_ids`에 같은 내용으로 존재.

**G2 관찰자 효과** — 순차 15건의 생성 token id가 arm A와 B에서 **15/15 동일**, 그리고 요청별 `elapsed(B)/elapsed(A)`의 **중앙값이 [0.90, 1.10]**. 동시 8건의 token 동일 여부, server process tree의 CPU 시간(workload 구간), collector CPU 시간은 **보고만** 한다(동시 batch는 batch 구성에 따라 bf16 수치가 달라질 수 있어 판정에서 뺀다).

**G3 복구** — `revert` 후 두 파일 SHA256이 위 원본 값과 같고 `apply.sh status`가 `pristine`.

**처리**: G1–G3 모두 충족 → patch를 이후 측정(GTASK04·05)에서 재적용해 쓴다(재적용 시 `apply.sh`가 hash를 다시 검증). 하나라도 실패 → 원인 기록, GTASK04·05의 **측정은 하지 않는다**(선등록·예측 commit은 가능, 지시문 §4). lifecycle 유효성(GPU 0 외 process 부재)이 깨지면 해당 arm `INVALID`, 관문 판정 불가.

## 사전 예측 (판정 아님)

- G2 elapsed 중앙값 비는 1.00–1.03(로그 1줄/step ≈ 수십 µs 대 step ≈ 10 ms). KV events publisher는 별도 thread라 server CPU 증가는 수 % 이내.
- 동시 요청의 prompt가 첫 16 token을 공유하면 같은 step에 admission된 뒤 요청이 앞 요청의 block에 hit할 수 있다(`allocate_slots`가 할당 시점에 full block을 캐시로 등록, `kv_cache_manager.py:421–425`). (b)는 로그·응답의 일치만 보므로 영향 없다.
