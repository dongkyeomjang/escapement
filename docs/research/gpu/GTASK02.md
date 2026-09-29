# GTASK02 — GPU Stage 0 기능 확인과 A6000 descriptor 초안

## 상태

DONE

## 날짜

2026-09-29

## 판정

**Stage 0 `PASS`** — 선등록 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md)의 C0–C5를 L2에서 전부 충족했다.

| 조건 | 판정 | 근거 (L2) |
|---|---|---|
| C0 provenance | 충족 | 로그 `Initializing a V1 LLM engine (v0.22.0)`, `revision=1cfa9a72…`. ready 시점 compute process는 GPU 0(`GPU-00596b63…`, serial `1320523024057`)의 `VLLM::EngineCore` pid 18063 하나, 기동 전 0개 |
| C1 단일 생성 | 충족 | `text_r1` HTTP 200, `completion_tokens` 64, `finish_reason length`, text `" A neural processing unit (NPU) is a specialized piece of ha…"` |
| C2 결정성 | 충족 | `text_r1`·`text_r2` 생성 token id 64개 전체 일치(r3도 일치). prompt 12 token(< 16)이라 hit 0 경로 |
| C3 KV 용량 고정 | 충족 | `Overriding num_gpu_blocks=16034 with num_gpu_blocks_override=2048`, `GPU KV cache size: 32,768 tokens` |
| C4 hit 공식 | 충족 **5/5** | H1 992, H2 1,008, H3 496, H4a 0, H4b 16 — 응답 `cached_tokens`와 `prompt_tokens_cached_total` 증분이 사례마다 예측과 같다 |
| C5 격자 반영 | 충족 | resolved `cudagraph_capture_sizes: [1, 2, 4, 6, 8]`, `max_cudagraph_capture_size: 8` |

**측정 성격**: 기능 확인. 기동 시간·요청 시간은 기록만 했고 판정에 쓰지 않았다.

## 목적

GPU 지시문 G-01 작업 D·E. (D) 설치가 동작하는지 선등록 조건으로 확인하고 서버 명령·resolved config를 남긴다. (E) source-read와 Stage 0로 확정된 필드만으로 A6000 descriptor 초안을 만들고, 현재 `SubstrateDescriptor`가 GPU 기판을 표현하지 못하는 부분을 목록으로 보고한다.

## 배경

관련 TASK:

- [GTASK01](GTASK01.md) — inventory·설치·source 감사. 이 TASK의 예측 E1–E12의 근거
- [STAGE0_PREREG.md](../STAGE0_PREREG.md), [TASK06](../TASK06.md) — NPU Stage 0 형식과 같은 prompt
- [TASK09](../TASK09.md) — NPU의 frontend `num_gpu_blocks` 2배 누적
- [TASK11](../TASK11.md), [TASK24](../TASK24.md) — NPU hit 공식(128 token, prefill token만 캐시)
- [TASK16](../TASK16.md) — `SubstrateDescriptor`와 층 태깅
- [TASK71](../TASK71.md), [TASK72](../TASK72.md) — 모형 v0·v1 권고(`resume_allocates_first`, `release_rule`, `dummy_mode`)

## 시작 상태

- branch `gpu-a6000`, HEAD `7bb07f5845a80a0077fa9fae81694e8f4d2acf5f`(선등록), working tree clean
- venv `/home/csdc/kyeom/envs/vllm-0.22.0`(`vllm 0.22.0`, `torch 2.11.0+cu130`), driver 580.178.04
- model `Qwen/Qwen3-4B@1cfa9a72…`(`/mnt/nvme/hf`), 추가 download 없음(`HF_HUB_OFFLINE=1`)
- GPU 3장 모두 1 MiB·compute process 없음

## 수행 내용

1. 선등록 문서와 실행 script를 commit(`7bb07f5`, 08:52:13 UTC)한 뒤 [`run_stage0.sh`](../../../experiments/gpu/stage0/run_stage0.sh)로 L1 → L2 → L3를 차례로 실행했다(한 번에 한 server, GPU 0, port 8100).
2. 각 lifecycle에서 [`probe.py`](../../../experiments/gpu/stage0/probe.py)가 순차 요청(텍스트 3회, hit 사례 5쌍, H5 1쌍)과 L2·L3의 동시 묶음(3·5개)을 보냈다.
3. L3(v1 runner)는 기동 중 실패했다. 선등록대로 인자를 바꿔 재시도하지 않고 원인만 확인했다.
4. descriptor 초안 [`a6000_vllm_0220_draft.py`](../../../experiments/gpu/substrate/a6000_vllm_0220_draft.py)를 작성·실행했다.

## 변경된 파일

- `docs/research/gpu/GTASK02.md` (skeleton → 완성)
- `docs/research/gpu/GPU_INDEX.md` (GTASK02 행·현재 상태)
- `experiments/gpu/substrate/a6000_vllm_0220_draft.py` (신규)

## 실험 또는 검증 방법

```bash
RUN=/home/csdc/kyeom/Project/escapement/results/gpu/stage0/20260929T0853Z-qwen3-4b
experiments/gpu/stage0/run_stage0.sh "$RUN" L1   # 08:52:18–08:53:50 UTC
experiments/gpu/stage0/run_stage0.sh "$RUN" L2   # 08:54:36–08:56:10 UTC
experiments/gpu/stage0/run_stage0.sh "$RUN" L3   # 08:56:37–08:57:34 UTC, 기동 실패(exit 4)
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/substrate/a6000_vllm_0220_draft.py
```

L2 server 명령 전문(`provenance.txt`에서):

```
vllm serve Qwen/Qwen3-4B --revision 1cfa9a7208912126459214e8b04321603b3df60c --dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 8 --seed 20260929 --host 127.0.0.1 --port 8100 \
  --generation-config vllm --enable-prompt-tokens-details \
  --block-size 16 --num-gpu-blocks-override 2048 \
  --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 6, 8]}' --cudagraph-metrics
# env: CUDA_VISIBLE_DEVICES=0 HF_HOME=/mnt/nvme/hf HF_HUB_OFFLINE=1 HF_HUB_ENABLE_HF_TRANSFER=0
```

## 결과

Population: server lifecycle 3개(판정 L2), 요청 L1 15건·L2 23건(동시 8건 포함). Source: server 로그(resolved config 전체 포함), 응답 JSON, `/metrics` 전후 스냅샷, `nvidia-smi`. Device scope: GPU 0.

- `requested_condition`: L1 기본값, L2 block 16·pool 2,048 block·격자 `[1,2,4,6,8]`, L3 L2 + v1 runner
- `observed_condition`: L1·L2 요청대로 resolved(아래). L3 기동 실패
- `condition_reached`: L1 `YES`, L2 `YES`, L3 `NO`

### lifecycle 요약

| | L1 (기본값) | L2 (판정) | L3 (v1 runner, 탐색) |
|---|---|---|---|
| 기동 → ready | 87 s | 72 s | 실패(57 s 후 exit) |
| model runner | **V2** (`gpu_worker.py:289 Using V2 Model Runner`) | V2 | v1(`gpu_model_runner.py`) |
| attention backend | `FLASH_ATTN` | `FLASH_ATTN` | — |
| async scheduling | enabled | enabled | — |
| `cudagraph_mode` | `FULL_AND_PIECEWISE` | 같음 | — |
| capture 목록 | **`[1, 2, 4, 8, 16]`**, max 16 | **`[1, 2, 4, 6, 8]`**, max 8 | — |
| `num_gpu_blocks` | profiled **16,034**(가용 KV 35.23 GiB) | override **2,048** | — |
| `GPU KV cache size` / 최대 동시성 | 256,544 tokens / 31.32x | 32,768 tokens / 4.00x | — |
| `cache_config_info` | — | `block_size="16"`, `num_gpu_blocks="2048"`, `num_gpu_blocks_override="2048"` | — |
| ready 시 GPU 0 사용량 | 44,356 MiB | 12,826 MiB | — |
| preemption | 0 | 0 | — |

### 사전 예측 대조

| # | 예측 | 관측 | 결과 |
|---|---|---|---|
| E1 | L1 `block_size` 16 | config dump에 `block_size`가 출력되지 않음. hit 값(496 = `floor(500/16)·16` 등)과 L2 `cache_config_info block_size="16"`(명시 인자)로 16과 정합 | 적중(행동 기반) |
| E2 | L1 capture `[1,2,4,8,16]` | `[1, 2, 4, 8, 16]`, max 16 | 적중 |
| E3 | L1 로그 `Chunked prefill is enabled with max_num_batched_tokens=2048` | **해당 줄이 로그에 없다.** config dump에는 `enable_chunked_prefill=True`만 있고 `max_num_batched_tokens`는 출력되지 않는다 | **확인 불가** — budget 값 `UNKNOWN`(source 예측 2048 유지) |
| E4 | async scheduling enabled | L1·L2 enabled | 적중 |
| E5 | L1·L2 v2, L3 v1 | L1·L2 `Using V2 Model Runner`, L3는 `gpu_model_runner.py`(v1) | 적중 |
| E6 | profiled 약 1.2만–1.8만 block | 16,034 | 적중 |
| E7 | `num_gpu_blocks` label 2,048(2배 누적 없음) | `num_gpu_blocks="2048"` | 적중 — [TASK09](../TASK09.md)의 2배 현상은 이 GPU 구성에서 **재현되지 않았다** |
| E8 | 텍스트 prompt < 16 token, `cached_tokens` 부재, 증분 0 | 12 token, 부재, 0 (L1·L2 모두 r1–r3) | 적중 |
| E9 | **H5 = 1,024**(생성 token 캐시), 대안 992 | **L1 1,024, L2 1,024**(응답·counter 모두) | 적중 — **생성 token이 캐시된다** |
| E10 | preemption 0 | 전 lifecycle 0 | 적중 |
| E11 | L2(v2)에서 cudagraph 표 없음, L3(v1)에서 표 | L2 로그에 `CUDAGraph` 표 **0줄**. L3는 기동 실패로 확인 못 함 | 절반 적중, 절반 `UNKNOWN` |
| E12 | 최대 동시성 4.00x | 4.00x | 적중 |

L1에서도 hit 사례 5/5와 H5가 L2와 같은 값이었다(L1은 판정 대상이 아니다).

### L3 실패 원인

v1 runner의 `profile_run` → `_dummy_sampler_run` → FlashInfer `top_k_top_p_sampling_from_logits`가 sampling kernel을 **JIT build**하려다 `RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist`로 멈췄다. 이 서버에는 시스템 CUDA toolkit이 없다([GTASK01](GTASK01.md)). venv 안에는 pip wheel의 `nvcc`(`site-packages/nvidia/cu13/bin/nvcc`)가 있지만 FlashInfer는 PATH와 `/usr/local/cuda`만 찾는다. v2 runner는 이 sampler 경로를 쓰지 않아 L1·L2에 영향이 없었다. patch 없는 우회는 두 가지로 보인다(적용하지 않음, source-read): `VLLM_USE_FLASHINFER_SAMPLER=0`(`vllm/envs.py:818`, PyTorch 구현 sampler로 전환) 또는 `CUDA_HOME`을 venv의 `nvidia/cu13`로 지정. 전자는 sampler 구현을 바꾸고 후자는 JIT build를 허용한다 — 어느 쪽이든 선등록 밖이라 Advisor 결정 사항이다.

### descriptor 초안 (작업 E)

[`experiments/gpu/substrate/a6000_vllm_0220_draft.py`](../../../experiments/gpu/substrate/a6000_vllm_0220_draft.py). **`SubstrateDescriptor` 인스턴스가 아니다** — 생성자는 측정값 `step_cost_model`과 2층 pool의 outer field를 요구하므로, 값을 지어내지 않으면 생성이 거부된다(실행 시 `TypeError`로 거부를 확인). 채운 field(모두 provenance 동반):

| field | 값 (L2 구성) | 층 / 종류 / 출처 |
|---|---|---|
| `bucket_sizes` | 기본 `(1,2,4,8,16)`; server 인자로 바뀜(L2 `(1,2,4,6,8)`) | `stack` / source-read / GTASK01, runtime 확인 GTASK02 |
| `inner_block_tokens` | 16 | `stack` / measured / GTASK02 |
| `inner_block_count` | `num_gpu_blocks − 1` = 2,047 (null block 제외) | `stack` / measured / GTASK02 |
| `inner_eviction_policy` | `lru-by-release/tail-first` | 형태 `class` / source-read / GTASK01 |
| `hit_formula` | `HitFormula(16, reserve_last_query_token=True)` | 형태 `class` / measured / GTASK02 |
| `kv_pool_tokens` | 2,047 × 16 = 32,752 | `stack` / derived / GTASK02 |

채우지 않은 것(측정 TASK 필요): `step_cost_model`, `prefill_cost_model`.

## 핵심 발견

1. **`stack`** — **A6000 + `vllm 0.22.0` + Qwen3-4B bf16 serving이 선등록 조건 C0–C5를 충족한다(Stage 0 `PASS`).** KV pool 크기(`--num-gpu-blocks-override`)와 decode 격자(`cudagraph_capture_sizes`)가 **재compile 없이 server 인자로 고정되고 로그·metric으로 확인된다.**
2. **`class`(형태) / `stack`(값)** — **hit 공식 `floor(min(shared, query−1)/16)·16`이 5/5 사례에서 두 lifecycle 모두 정확히 맞았다.** 형태는 NPU `HitFormula`와 같고([TASK11](../TASK11.md)), block 크기만 16이다. 형태를 `class`로 보는 근거: 마지막 query token 재계산과 full block 단위 hash는 vLLM 계열 prefix cache의 설계에서 나오며 NPU·GPU 두 기판에서 같은 형태로 관측됐다.
3. **`stack`** — **이 기판은 decode가 생성한 token도 캐시한다.** H5에서 1,000 token prompt + 40 token 생성 뒤 그 생성문을 그대로 이어 붙인 요청이 **1,024** token hit했다(= `floor(1,039/16)·16`, 마지막 sampled token은 KV가 없어 제외). prompt만 캐시하는 읽기(NPU 층 2, [TASK24](../TASK24.md))라면 992다. **재사용의 상한이 생성 길이에 따라 NPU와 반대 방향으로 움직일 수 있다.**
4. **`stack`** — **Qwen3-4B는 기본으로 model runner v2에서 돌고, v2에서는 `--cudagraph-metrics`가 아무것도 출력하지 않는다.** patch 없는 step padding 관측을 v1 runner로 얻으려던 경로는 이 서버에서 **FlashInfer sampler의 JIT build(`nvcc` 필요)** 때문에 기동조차 되지 않았다.
5. **`stack`** — **이 GPU 구성에서 frontend `num_gpu_blocks`의 2배 누적([TASK09](../TASK09.md))은 나타나지 않았다**(`cache_config_info num_gpu_blocks="2048"`). 같은 누적 코드(`core_client.py:712`)가 있으므로 NPU에서의 2배는 frontend 초기값이 채워져 있던 plugin 경로의 결과로 보인다(가설, 미확인).
6. **`stack`** — **resolved config dump만으로는 `block_size`와 `max_num_batched_tokens`를 확인할 수 없다**(dump에 없음, `Chunked prefill is enabled…` 줄도 출력되지 않음). `block_size`는 `cache_config_info` metric으로 확인되지만 token budget은 로그·metric 어디에도 없다 → 측정 run에서는 `--max-num-batched-tokens`를 **명시**해야 provenance가 선다.
7. **`stack`** — **`--num-gpu-blocks-override`는 KV 할당 자체를 줄인다**(ready 시 GPU 0 사용량 44,356 → 12,826 MiB). 남는 메모리는 비어 있으므로, 같은 GPU를 쓰는 다른 process가 있으면 그 메모리를 쓸 수 있다 — 간섭 통제는 compute process 목록으로 해야 한다.

## 해석

- 발견 1·2로 **GPU 기판의 hit 식과 용량 파라미터는 "재고 예측"할 준비가 됐다** — 두 값이 server 인자로 정해지고 관측으로 확인된다. 남은 기판 파라미터는 step 비용(FULL·PIECEWISE·eager 세 곡선)과 혼합 step 비용이며, 이것이 다음 측정 TASK의 대상이다(권고).
- 발견 3은 모형 B1의 GPU 인스턴스에서 `u_rel`(release되는 단위)과 hit 가능한 `shared`를 **prompt + output − 1**로 둬야 한다는 뜻이다. 다만 OpenAI chat 경로에서 재도착 prompt가 이전 생성 token을 같은 id로 담는지는 chat template(특히 Qwen3의 `<think>` 처리)에 달려 있어 workload 설계 때 따로 확인해야 한다(`UNKNOWN`).
- 발견 4 때문에 **step 단위 격자 관측은 현재 patch 없이 불가능**하다. 대안은 (a) v1 runner + sampler 우회(env 한 줄), (b) v2 runner에 observation-only patch — 둘 다 Advisor 결정 사항이다.

## 확인되지 않은 사항

- 실제 token budget(`max_num_batched_tokens`) — 로그 미출력(E3). source 예측은 2048
- v1 runner의 cudagraph 표(E11 후반) — L3 기동 실패
- 동시 묶음(3·5개)에서 실제 decode batch 구성과 padding — v2 runner에서는 관측 수단 없음
- NPU에서 2배 누적이 난 정확한 경로(발견 5의 가설)
- chat 경로에서 생성 token의 재도착 hit 여부

## 실패 / 무효 시도

- **L3 기동 실패**(exit 4, 08:57:34 UTC): 위 "L3 실패 원인". 선등록 규칙("L3 실패는 기록만")대로 재시도하지 않았다. `INVALID`가 아니라 **탐색 lifecycle 미도달**이며 Stage 0 판정에 영향이 없다.
- 첫 산출물 확인 명령이 scratchpad 디렉터리 부재로 실패했다(분석 명령만, run에 영향 없음).

## 연구 원칙에 미치는 영향

- **관측 불가를 0으로 채우지 않는다**: probe는 `prompt_tokens_details` 부재를 `None`으로 기록했고, 판정에서 0으로 읽은 것은 선등록된 조건(flag가 로그에서 True, source상 0일 때 생략)과 counter 교차 일치가 둘 다 성립한 경우뿐이다.
- 측정 run의 provenance에는 **명시하지 않으면 로그에 남지 않는 인자**(token budget)가 있다 → 측정 TASK의 server 인자는 기본값에 기대지 말고 명시한다(발견 6).

## 다음 작업

제안만 하며 Advisor 지시 없이 착수하지 않는다.

1. GPU step 비용 측정 선등록 — FULL(decode-only, capture size별)·PIECEWISE(혼합 ≤ max)·eager(> max) 세 곡선. 관측 수단 결정(아래 Advisor 결정 1)이 선행 조건이다.
2. GPU 생존 곡선 사전 예측의 선등록 — 이번 TASK로 확정된 파라미터(block 16, pool N−1, release LRU·tail-first, 조회 후 할당, 생성 token 캐시)로 [TASK29](../TASK29.md) 축 ①을 새로 계산해 측정 전에 commit.

## 재현 정보

- 선등록 commit: **`7bb07f5845a80a0077fa9fae81694e8f4d2acf5f` (2026-09-29 08:52:13 UTC)** → 첫 측정(L1 server 기동) **08:52:18 UTC**, L2 08:54:36, L3 08:56:37. 선등록이 먼저다. 판정 기준은 실행 후 바꾸지 않았다.
- raw artifact: `results/gpu/stage0/20260929T0853Z-qwen3-4b/{L1,L2,L3}/` — `provenance.txt`(명령 전문·PID·시각), `env.txt`, `server.log`(resolved config 전체), `nvidia-smi-*.csv`, `gpu-apps-*.csv`, `probe/{requests.jsonl,summary.json,metrics_pre.txt,metrics_post.txt,models.json}` (git 비추적)
- 환경: [GTASK01](GTASK01.md) 재현 정보, inventory `results/gpu/env/inventory-20260929T084320Z/`
- descriptor 초안: `env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/substrate/a6000_vllm_0220_draft.py` (exit 0, 생성자 거부 확인 출력)
