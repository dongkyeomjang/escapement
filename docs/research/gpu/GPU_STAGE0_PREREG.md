# GPU Stage 0 선등록 — A6000 · vLLM 0.22.0 · Qwen3-4B 기능 확인

## 문서 성격

GPU 지시문 G-01 작업 D의 **선등록**이다. 이 문서와 실행 script([`run_stage0.sh`](../../../experiments/gpu/stage0/run_stage0.sh), [`probe.py`](../../../experiments/gpu/stage0/probe.py))를 담은 commit이 만들어진 뒤에 server를 기동한다. 형식은 NPU [STAGE0_PREREG.md](../STAGE0_PREREG.md)를 따른다. 결과와 판정은 [GTASK02](GTASK02.md)에 쓴다. 측정 후 기준을 완화하지 않으며, 완화가 불가피하면 원 기준의 실패를 함께 보고한다.

**이 Stage 0는 설치가 동작하는지만 본다. latency·throughput 등 성능 수치는 기록만 하고 판정에 쓰지 않는다.**

## 승인 범위

지시문 G-01 §4·§6: 격리 venv(`/home/csdc/kyeom/envs/vllm-0.22.0`)의 `vllm 0.22.0`, `Qwen/Qwen3-4B@1cfa9a72…`(이미 download, [GTASK01](GTASK01.md)), 단일 GPU serving 기동과 짧은 요청. site-packages 수정, patch, 성능 실험은 범위 밖이다.

## 예산

| 항목 | 상한 | 초과 시 |
|---|---|---|
| serving lifecycle | 3회(L1·L2·L3) + 기동 실패 시 원인 확인 재시도 lifecycle당 1회 | 중단, `BLOCKED` 기록 |
| lifecycle당 기동 대기 | 900 s | script가 exit 5, 로그 보존 |
| 추가 download | 0 (`HF_HUB_OFFLINE=1`) | — |

## 실험 격자

| 요소 | 고정값 |
|---|---|
| GPU | `CUDA_VISIBLE_DEVICES=0` (A6000 1장, serial `1320523024057` 예상 — `nvidia-smi` 기록으로 확인) |
| 공통 server 인자 | `vllm serve Qwen/Qwen3-4B --revision 1cfa9a7208912126459214e8b04321603b3df60c --dtype bfloat16 --max-model-len 8192 --max-num-seqs 8 --seed 20260929 --host 127.0.0.1 --port 8100 --generation-config vllm --enable-prompt-tokens-details` |
| **L1** (기본값 해석) | 공통 인자만. `block_size`·KV 용량·capture 목록·chunked prefill·runner를 기본값으로 둔다 |
| **L2** (판정) | 공통 + `--block-size 16 --num-gpu-blocks-override 2048 --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 6, 8]}' --cudagraph-metrics` |
| **L3** (탐색, 판정 없음) | L2 + 환경변수 `VLLM_USE_V2_MODEL_RUNNER=0` (v1 runner) |
| 실행 순서 | L1 → L2 → L3, 한 번에 하나(같은 GPU·port) |
| 요청 (모든 lifecycle) | `/v1/completions`, `temperature 0.0`, `top_p 1.0`, `seed 20260929`, `return_token_ids true`, **순차** |
| 텍스트 요청 | NPU Stage 0와 같은 prompt `Explain in two sentences what a neural processing unit is.`, `max_tokens 64`, 3회(r1·r2·r3) |
| hit 사례 | token-id prompt(사례마다 다른 seed로 `[1000, 150000)` 균등 난수). 각 사례는 seed 요청(`max_tokens 1`) 뒤 probe 요청(`max_tokens 1`) |
| H5 | seed 1,000 token, `max_tokens 40`, `ignore_eos true` → probe = seed + 생성 token id + 새 5 token |
| 동시 묶음 (L2·L3) | 텍스트 prompt 변형 3개·5개를 동시에(`max_tokens 64`, `ignore_eos`), 이후 15 s 대기(통계 로그 주기) |

hit 사례 (`B = 16`):

| 사례 | seed 길이 | probe 길이 (query) | 공유 prefix | 예측 `cached_tokens` = `floor(min(shared, query−1)/16)·16` |
|---|---|---|---|---|
| H1 | 1,000 | 1,000 (동일) | 1,000 | **992** |
| H2 | 1,024 | 1,024 (동일) | 1,024 | **1,008** (마지막 block 재계산) |
| H3 | 800 | 800 | 500 | **496** |
| H4a | 16 | 16 (동일) | 16 | **0** |
| H4b | 17 | 17 (동일) | 17 | **16** |

## PASS 조건 (L2에서 판정)

아래 C0–C5를 **전부** 충족하면 Stage 0 `PASS`.

- **C0 (provenance, 유효성)** — server 로그의 resolved config에 `vllm 0.22.0`과 revision `1cfa9a72…`가 있고, ready 시점 `nvidia-smi --query-compute-apps`에 GPU 0 uuid의 process만 있으며 다른 GPU에는 이 run의 process가 없다. 실패 시 이 lifecycle은 `INVALID`.
- **C1 (단일 생성)** — `text_r1`이 HTTP 200, `completion_tokens ≥ 1`, text가 공백만이 아니고 `[A-Za-z]`를 1자 이상 포함한다(NPU Stage 0 조건 4와 같은 조작적 정의).
- **C2 (결정성)** — `text_r1`과 `text_r2`의 생성 `token_ids`가 전체 일치한다. (이 prompt는 16 token 미만일 것으로 예측되어 hit이 구조적으로 0이므로 두 요청의 계산 경로가 같다. prompt가 17 token 이상이면 r2·r3로 판정하고 그 사실을 기록한다.)
- **C3 (KV 용량 고정)** — server 로그에 `Overriding num_gpu_blocks=<X> with num_gpu_blocks_override=2048`이 있고, **그리고** `GPU KV cache size: 32,768 tokens`가 있다(`= 2048 / ceil(8192/16) × 8192`, EngineCore 값).
- **C4 (hit 공식)** — H1·H2·H3·H4a·H4b **5/5**에서 probe의 관측 `cached_tokens`가 예측과 같다. 관측값은 응답 `usage.prompt_tokens_details.cached_tokens`이며, **필드가 없으면 0으로 읽는다 — 단 L2 server 로그에서 `enable_prompt_tokens_details`가 True일 때만**(source: 값이 0이면 필드를 생략, `completion/serving.py:586`). 동시에 같은 요청의 `vllm:prompt_tokens_cached_total` 증분(순차 요청이므로 귀속 가능)이 같은 값이어야 한다. 두 채널이 다르면 그 사례는 불일치로 센다.
- **C5 (격자 반영)** — server 로그의 resolved `compilation_config`에서 `cudagraph_capture_sizes`가 `[1, 2, 4, 6, 8]`이고 `max_cudagraph_capture_size`가 8이다.

판정 규칙: C0 실패 → `INVALID`. C1 실패 → `FAILED`. C1·C2 충족, C3–C5 중 일부 실패 → `PARTIAL`(실패 항목 명시). 전부 충족 → `PASS`.

## 사전 예측 (판정 기준 아님, 빗나가도 기준을 바꾸지 않는다)

source-read([GTASK01](GTASK01.md))에서 나온 예측이다.

| # | 예측 | 근거 |
|---|---|---|
| E1 | L1의 resolved `block_size` = 16 | `config/cache.py:45`, FLASH_ATTN이 16 지원 |
| E2 | L1의 `cudagraph_capture_sizes` = `[1, 2, 4, 8, 16]`, max 16 | `config/vllm.py:1647–1708` |
| E3 | L1 로그 `Chunked prefill is enabled with max_num_batched_tokens=2048` | `arg_utils.py:2311–2325` |
| E4 | L1·L2 로그 `Asynchronous scheduling is enabled` | `config/vllm.py:975` |
| E5 | L1·L2에서 model runner **v2** 사용(로그 source 위치가 `v1/worker/gpu/model_runner.py`), L3에서 v1(`gpu_model_runner.py`) | `config/vllm.py:69,493–532` |
| E6 | L1 profiled `num_gpu_blocks`는 1만 단위(대략 1.2만–1.8만). 값 자체는 `UNKNOWN`, 기록만 | 48 GiB × 0.92 − weight 7.5 GiB − 활성화·graph, block당 2.25 MiB(`36×8×128×2×2×16` B) |
| E7 | L2 `vllm:cache_config_info`의 `num_gpu_blocks` label = `2048`(TASK09의 2배 누적은 **나지 않을** 것) | frontend config의 초기값이 None이면 `core_client.py:712`는 0 + 2048. 단 NPU에서 났던 현상이라 확신 낮음 |
| E8 | 텍스트 prompt의 `prompt_tokens` < 16 → r1–r3 모두 `cached_tokens` 필드 부재, `prompt_tokens_cached` 증분 0 | hit에 full block 16 token이 필요 |
| E9 | **H5**: probe `cached_tokens` = **1,024** (`floor(min(1000+40−1, 1045−1)/16)·16`, 생성 token이 캐시됨). 대안(NPU처럼 prompt만 캐시) = 992 | `v1/request.py:232`, `kv_cache_manager.py:421–425` |
| E10 | 전 lifecycle에서 `vllm:num_preemptions_total` = 0 | 사용 block ≪ pool |
| E11 | **L2(v2 runner)의 `--cudagraph-metrics` 표는 비어 있거나 출력되지 않는다**; **L3(v1 runner)에서는 표가 나오고**, 동시 3·5 묶음의 decode step이 `Unpadded 3 → Padded 4`, `5 → 6` (`FULL`)로, prefill이 섞여 8 token을 넘는 step은 `NONE`(padding 없음)으로 기록된다 | `gpu_model_runner.py:3818–3832`, v2에 생산자 없음; 사상 규칙 GTASK01 항목 6 |
| E12 | L2 로그 `Maximum concurrency for 8,192 tokens per request: 4.00x` | `kv_cache_utils.py:877–895` |

## FAIL / PARTIAL / 기타 처리

| 상황 | 처리 |
|---|---|
| L1 기동 실패 | L1은 판정 대상이 아니다. 로그를 보존하고 원인을 기록한 뒤 L2로 진행한다(원인이 L2에도 해당하면 중단) |
| L2 기동 실패 | 원인 확인 재시도 1회. 인자를 바꿔야 하면 **중단하고 보고**(선등록 인자 변경 금지) |
| L3 기동 실패 | 탐색이므로 기록만 한다 |
| 다른 process가 GPU 0에 나타남 | 해당 lifecycle `INVALID`, 원인 기록 |

## 실행 절차

```bash
RUN=/home/csdc/kyeom/Project/escapement/results/gpu/stage0/<UTC>-qwen3-4b
experiments/gpu/stage0/run_stage0.sh "$RUN" L1
experiments/gpu/stage0/run_stage0.sh "$RUN" L2
experiments/gpu/stage0/run_stage0.sh "$RUN" L3
```

- script는 절대 경로만 받고, 기동한 server를 **받은 PID로만** 종료하며(KNOWN_PITFALLS 1·2), 실행 중에는 script를 편집하지 않는다(KNOWN_PITFALLS 5).
- lifecycle마다 `provenance.txt`(repo HEAD·명령 전문·시각·PID), `env.txt`, `server.log`(resolved config 전체), `nvidia-smi-{pre,ready,post}.csv`, `gpu-apps-{pre,ready}.csv`, `probe/{requests.jsonl,summary.json,metrics_pre.txt,metrics_post.txt,models.json}`을 남긴다(`results/gpu/`, git 비추적).
- 판정은 raw 산출물에서 [GTASK02](GTASK02.md)에 기록한다.
