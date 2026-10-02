# GTASK01 — A6000 기판 착수: 환경 inventory, vLLM 0.22.0 설치, source 감사

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-01(Advisor, 2026-09-29) 작업 A·B·C를 집행한다. A6000 서버를 두 번째 기판으로 쓰기 위해 (A) 환경을 read-only로 inventory하고, (B) 격리 가상환경에 NPU 스택의 upstream 기준과 같은 `vllm 0.22.0` CUDA 빌드와 같은 revision의 `Qwen/Qwen3-4B`를 설치하며, (C) 설치된 vLLM source에서 조회·할당 순서, block 회수, hit 공식, KV 용량 고정, preemption, decode 격자, chunked prefill, 요청이 아닌 KV 소비자, 관측 수단을 감사한다.

**측정 0, server 기동 0, 판정 0.** site-packages 수정·patch 적용 0. `src/continuum/`·`docs/research/INDEX.md`·기존 `TASK*.md` 변경 0.

## 배경

관련 TASK (NPU namespace, 읽기만 함):

- [TASK29](../TASK29.md) — GPU 측 예측(격자 `[1,2,4,8,16]`, LRU·block 단위 회수, chunked prefill)을 `vllm 0.22.0+cpu` source로 인용. 측정 전 commit `d67b19d`
- [TASK70](../TASK70.md) — Stage 3 개시, 결정 4 2차 개정(A6000을 두 번째 기판으로 격상)
- [TASK71](../TASK71.md) — 모형 v0, `resume_allocates_first`(vLLM은 조회 후 할당, NPU 서버 source-read)
- [TASK72](../TASK72.md) — 사건 재생, 완료 항목의 즉시 evictable 전환, dummy `PRE_EVICT`, `details.get("cached_tokens", 0)` 함정
- [TASK06](../TASK06.md) — NPU Stage 0, model revision `1cfa9a72…`, 13 파일 8,060,926,626 B
- [TASK09](../TASK09.md) — frontend `num_gpu_blocks` 2배 누적(`core_client.py:712`)
- [TASK11](../TASK11.md), [TASK24](../TASK24.md) — NPU hit 공식(128 token, prefill token만 캐시)
- [TASK63](../TASK63.md) — NPU dummy block
- [MODEL_V0.md](../MODEL_V0.md) — B1 창 정의, `K_pin`, `D`

## 시작 상태

- 작업 규약: 지시문 G-01 §0에 따라 `origin/main` 최신 `e1f791eff6e4b65093248343a8246e9a8bbbfc2b`(TASK72)에서 branch `gpu-a6000`을 만들었다. clone 직후 자동 설정된 upstream(`origin/main`)은 실수 push를 막기 위해 `git branch --unset-upstream`으로 해제했다.
- 작업 디렉터리 `/home/csdc/kyeom/Project/escapement`는 비어 있었고 git 저장소가 아니었다 → 이 위치에 clone했다.
- 시스템 Python 3.10.12(`vllm`·`torch` 없음, `pip3` 없음), `uv 0.11.23`, uv 관리 CPython 3.12.13.

## 수행 내용

1. **작업 A — inventory** (read-only). 수집 script [`experiments/gpu/env/collect_inventory.sh`](../../../experiments/gpu/env/collect_inventory.sh)를 만들어 `results/gpu/env/inventory-20260929T084320Z/`에 남겼다.
2. **작업 B — 설치**. 저장소 밖 `/home/csdc/kyeom/envs/vllm-0.22.0`에 uv venv(CPython 3.12.13)를 만들고 `uv pip install vllm==0.22.0`(PyPI x86_64 wheel). 시스템 Python·driver·CUDA는 건드리지 않았다. model은 NPU TASK06 revision을 **지정해** `snapshot_download`로 받았다.
3. **작업 C — source 감사**. 설치본 `.../site-packages/vllm/`를 읽었다. 아래 표의 모든 줄 번호는 이 설치본 기준이다.

## 변경된 파일

- `docs/research/gpu/GTASK01.md` (신규)
- `docs/research/gpu/GPU_INDEX.md` (신규)
- `experiments/gpu/env/collect_inventory.sh` (신규)
- (같은 commit) `docs/research/gpu/GPU_STAGE0_PREREG.md`, `experiments/gpu/stage0/{run_stage0.sh,probe.py}` — Stage 0 선등록. 판정은 [GTASK02](GTASK02.md)

## 실험 또는 검증 방법

```bash
experiments/gpu/env/collect_inventory.sh /home/csdc/kyeom/Project/escapement/results/gpu/env/inventory-<UTC>
# 설치
uv venv --python ~/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12 /home/csdc/kyeom/envs/vllm-0.22.0
uv pip install --python /home/csdc/kyeom/envs/vllm-0.22.0/bin/python 'vllm==0.22.0'
# model (HF_HOME=/mnt/nvme/hf, ~/.bashrc)
HF_HUB_ENABLE_HF_TRANSFER=0 python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-4B', revision='1cfa9a7208912126459214e8b04321603b3df60c')"
```

## 결과

### 작업 A — 환경 inventory

Population: host 1대. Source: `nvidia-smi`, `lscpu`, `df`, `ps`, `/etc/os-release`. 시각 2026-09-29 08:33–08:43 UTC.

| 항목 | 값 |
|---|---|
| host | hostname `csdc`, Ubuntu 22.04.5 LTS, kernel 5.15.0-191-generic, uptime 5일 21시간(마지막 boot 2026-09-23 11:03 UTC) |
| CPU / RAM | Intel Xeon Gold 6226R 1 socket 32 thread, NUMA 1개 / 125 GiB (여유 121 GiB), swap 7 GiB |
| GPU | **NVIDIA RTX A6000 × 3** (compute capability 8.6), 각 49,140 MiB(`torch` 기준 50,897,289,216 B). serial `1320523024057`, `1324321024960`, `1324321025786` |
| topology | GPU0–GPU1 `PHB`, GPU0/1–GPU2 `NODE`, NVLink 없음, 전부 NUMA 0 |
| driver / CUDA | driver **580.178.04**, driver 지원 CUDA 13.0. 시스템 CUDA toolkit 없음(`nvcc` 없음, `/usr/local/cuda*` 없음) — venv의 `nvidia-*` wheel이 CUDA 13.0 runtime을 제공 |
| GPU 설정 | persistence mode **Disabled**, compute mode **Default**(비배타) — 세 장 모두 |
| 점유 (조사 시점) | 세 GPU 모두 1 MiB, utilization 0 %, compute process 없음 |
| disk | `/`·`/home` 1.8 TiB 중 39 GiB 사용(1.7 TiB 여유). `/mnt/nvme` 1.8 TiB 중 54 GiB 사용(1.7 TiB 여유) — `HF_HOME=/mnt/nvme/hf` |
| 사용자 | 로그인 계정 `csdc` 하나(process 소유 사용자: `csdc`·root·system 계정만). `docker` 없음, `csdc` crontab 없음 |
| 기존 Python/vLLM | 시스템 Python에 vLLM 없음. **과거 CUDA 연구 fork** `/home/csdc/kyeom/Project/vllm-continuum`(origin `dongkyeomjang/vllm-continuum`, upstream `Hanchenli/vllm-continuum`, HEAD `19dbe06` [TASK31], 9.8 GiB, 자체 `.venv` Python 3.12.13에 fork editable 설치 `vllm 0.1.dev9+g316a58794`)와 `/home/csdc/kyeom/Project/vllm-continuum-glaucus`(HEAD `316a587`)가 있다. **둘 다 읽기만 했고 쓰지 않았다** |
| 과거 GPU 사용 흔적 | `~/vllm-*.log`(2026-06-22, fork로 Qwen2.5-7B·Llama 서빙), `~/.cache/vllm/torch_compile_cache` 최신 mtime 2026-07-17, `/mnt/nvme/{kvbench,lmcache_*}` 최신 mtime **2026-08-24**. HF cache에 `Qwen2.5-7B-Instruct`, `Llama-3.1-8B-Instruct`(각 15 GiB)가 이미 있었다 |
| shell 환경 | `~/.bashrc`: `HF_HOME=/mnt/nvme/hf`, `HF_HUB_ENABLE_HF_TRANSFER=1`(아래 실패 시도 참조) |

**측정 간섭 위험 판단** (파생 해석): 조사 시점 세 GPU는 완전히 비어 있고, 계정은 하나뿐이며, 마지막 GPU 작업 흔적은 5주 전(2026-08-24)이다. 따라서 **현재 간섭 위험은 낮다.** 다만 (1) compute mode가 `Default`라 같은 계정의 다른 session(다른 agent, 사용자 수동 작업)이 같은 GPU에 올라올 수 있고, (2) GPU 사용 이력을 남기는 장치(accounting, DCGM)가 없어 **측정 구간 밖의 과거 사용은 검증할 수 없으며(`UNKNOWN`)**, (3) persistence mode가 꺼져 있어 첫 CUDA context 생성 시 driver 초기화 지연이 있다. 측정 TASK에서는 GPU를 `CUDA_VISIBLE_DEVICES=0` 한 장으로 고정하고 run 전·ready 시점·후의 `nvidia-smi --query-compute-apps`로 **자기 PID 외 process 부재**를 run마다 기록할 것을 권고한다. `EXCLUSIVE_PROCESS` 모드와 persistence mode는 root 권한이 필요해 이 작업 범위 밖이다(Advisor 결정 사항).

### 작업 B — 설치

| 항목 | 값 |
|---|---|
| venv | `/home/csdc/kyeom/envs/vllm-0.22.0` (저장소 밖), CPython 3.12.13 |
| **vLLM** | **`0.22.0`** (PyPI `vllm-0.22.0-cp38-abi3-manylinux_2_28_x86_64.whl`) — NPU 스택 upstream 기준과 **같은 버전** |
| torch | `2.11.0+cu130`(CUDA 13.0, cuDNN 91900), triton 3.6.0, flashinfer 0.6.11.post2, transformers 4.57.6 |
| CUDA 동작 확인 | `torch.cuda.is_available()` True, device 3, `ones(4)*2` 합 8.0 |
| 설치 시간 | 2026-09-29 08:34:5x → 08:36:03 UTC, `EXIT=0` |
| package 목록 | `results/gpu/env/inventory-20260929T084320Z/pip-freeze.txt` (194 package), 설치 로그 `results/gpu/env/install-vllm-0.22.0.log` |
| **model** | `Qwen/Qwen3-4B` revision **`1cfa9a7208912126459214e8b04321603b3df60c`** = [TASK06](../TASK06.md) 기록과 **일치**. download 시점 HF `main`도 같은 hash였다 |
| model 파일 | 13 파일, **8,060,926,626 B** — TASK06 실측(8,060,926,626 B, 13 파일)과 **byte 단위 일치**. download 66.5 s(08:37:56–08:39:03 UTC) |
| model SHA256 | `results/gpu/env/inventory-20260929T084320Z/model-sha256.txt`. LFS 4개는 SHA256이 blob 이름과 일치: shard 1 `328a91d3…`, shard 2 `6cd087b3…`, shard 3 `e4bf4369…`, `tokenizer.json` `aeb13307…`. NPU 쪽 기록에는 파일별 SHA256이 없어 **파일 단위 대조는 불가**(revision·크기·파일 수로만 일치 확인) |

`dtype bfloat16`은 Stage 0 실행 시 지정한다([GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md)).

### 작업 C — vLLM 0.22.0 source 감사

경로 접두 `V = /home/csdc/kyeom/envs/vllm-0.22.0/lib/python3.12/site-packages/vllm/`. **표의 모든 내용은 source-read이며 runtime 확인이 필요한 항목은 `runtime 확인`으로 표시했다.** NPU 측 서술은 이 저장소의 기존 TASK 기록이며, 이 서버에서 재확인할 수 없다.

TASK29·TASK71이 인용한 줄(`scheduler.py:594`·`:721`, `compilation.py:676–690`의 기본 목록 docstring, `kv_cache_utils.py:164–181`의 `FreeKVCacheBlockQueue` docstring)은 **이 CUDA 빌드에서도 같은 줄에 있다** — 두 기판의 scheduler·KV 관리 코드가 같은 upstream임을 뒷받침한다(`vllm 0.22.0+cpu`와의 파일 단위 diff는 NPU 서버 접근이 없어 하지 않았다, `UNKNOWN`).

| # | 항목 | 파일:줄 | 핵심 코드 요약 | 층 | NPU 기판과의 차이 |
|---|---|---|---|---|---|
| 1 | **조회와 할당의 순서** | `v1/core/sched/scheduler.py:594` → `:721`; `v1/core/kv_cache_manager.py:219,228,397,404`; `v1/core/single_type_kv_cache_manager.py:165,219`; `v1/core/block_pool.py:347,414` | WAITING 요청마다 `get_computed_blocks`(조회, `max_cache_hit_length = num_tokens − 1`) → `allocate_slots`. `allocate_slots` 안에서 **hit block을 먼저 `touch`**(ref_cnt+1, free queue에서 제거, `:397`→`single_type:219`→`block_pool:414`)한 뒤 새 block을 `popleft_n`으로 가져온다(`:404`→`block_pool:347`). 용량 검사는 hit block 중 free queue에 있는 것(ref_cnt 0)까지 필요량에 넣는다(`single_type:165`). 검사 실패 시 `None`을 반환하고 **아무 block도 축출하지 않는다**(`kv_cache_manager.py:387`), scheduler는 `break`(`scheduler.py:733`) | `stack` | NPU(RBLN)는 **할당 후 조회** — resume 요청이 자기 slot을 먼저 잡으며 대상 prefix를 축출할 수 있다([TASK15](../TASK15.md), [TASK24](../TASK24.md)). GPU는 **조회 후 할당 + hit block 선보호**라 **같은 admission 안에서 hit block이 축출되는 경로가 없다**(source 범위). 창의 끝은 R의 lookup이고, 같은 step에서 **RUNNING 요청의 block 증가(`scheduler.py:444`)와 앞선 WAITING 요청의 할당은 R의 lookup보다 먼저** 일어나 창 안에 들어간다. 할당 실패로 대기한 요청은 다음 step에 조회를 다시 한다(값이 갱신됨) |
| 2 | **block 회수 의미론** | `scheduler.py:1480` → `:1842–1862`; `single_type_kv_cache_manager.py:338–354`(`:350`); `block_pool.py:176,347,365–400,419–433`; `kv_cache_utils.py:164–181` | 요청 종료 처리(`update_from_output`)에서 `_free_request` → `_free_blocks` → `kv_cache_manager.free`로 **즉시** 반납(KV connector가 없을 때; `delay_free_blocks`는 connector 전용). 반납 순서는 `reversed(req_blocks)`(`:350`)이고 `append_n`으로 **free queue 꼬리**에 붙는다(`block_pool:431`) → 한 요청 안에서는 **꼬리 block이 먼저** 축출된다. 할당은 queue **머리**에서 `popleft_n`하고 그때 hash를 지운다(`_maybe_evict_cached_block`, `:365`) → **release 시점 LRU**. 초기 queue는 block ID 순이라 **한 번도 안 쓴 block이 먼저** 소비된다. hit된 block은 `touch`로 queue에서 빠지고(ref_cnt>0 동안 queue 밖), ref_cnt가 0이 되면 다시 꼬리로 간다(공유 prefix는 마지막 사용자 반납 시점 기준) | 형태 `class`, 세부 `stack` | NPU 층 2는 **할당 순서 FIFO**의 시퀀스 단위 outer slot 8개, 완료 즉시 evictable([TASK72](../TASK72.md))이다. GPU는 **release 순서 LRU**의 16-token block 단위 pool. 창 시작이 T의 할당이 아니라 **T의 release**다([MODEL_V0.md](../MODEL_V0.md) B1 표). 부분 손실(tail-first)이 생긴다. **`class` 근거**: "반납된 block이 재할당 전까지 hit 가능한 evictable 상태로 남고 사용 순서로 축출된다"는 것은 paged prefix cache 설계 범주의 성질이고 특정 상수에 의존하지 않는다. tail-first·미사용 block 우선은 이 구현의 선택이라 `stack`. async scheduling(기본 on, 아래 7)에서 종료 처리가 한 step 늦게 반영될 수 있으나 **순서 규칙은 같다**(시점 지연 크기는 `UNKNOWN`) |
| 3 | **hit 공식** | `kv_cache_manager.py:219`; `single_type_kv_cache_manager.py:483–529`(`:507`); `config/cache.py:45,93`; `v1/request.py:216–232`; `kv_cache_manager.py:421–425` | hash는 `block_size` token 단위 연쇄 hash(`prefix_caching_hash_algo="sha256"`, 부모 hash 포함). 조회는 앞에서부터 연속 hit block만 센다(`max_num_blocks = max_length // block_size`). `max_length = num_tokens − 1`(마지막 query token 재계산). **decode 중 생성 token도 hash가 추가되고**(`append_output_token_ids`→`update_block_hashes`), KV가 계산된 full block은 `allocate_slots`마다 `cache_blocks`로 캐시된다 | 형태 `class`, 값 `stack` | **형태는 NPU `HitFormula`와 같다**: `floor(min(shared, query − 1)/B)·B`. 차이 둘: (a) `B` = **16**(`DEFAULT_BLOCK_SIZE`, backend가 바꿀 수 있어 `runtime 확인`) 대 NPU 128. (b) **`shared`에 생성 token이 들어간다** — 캐시 가능한 길이는 이전 요청의 `prompt + output − 1`(마지막 sampled token은 KV가 계산되지 않음)이다. NPU 층 2는 prefill token만 캐시한다([TASK24](../TASK24.md) 271/271). 따라서 GPU에서는 재도착 prompt가 이전 생성문을 token 단위로 그대로 담으면 그만큼 더 hit한다(chat template의 재토큰화·Qwen3 `<think>` 처리에 따라 달라짐, `UNKNOWN`). Stage 0 예측 H5가 (b)를 판별한다 |
| 4 | **KV 용량 고정** | `config/cache.py:85`; `engine/arg_utils.py:1126`; `v1/core/kv_cache_utils.py:898–905,2007–2026,1715–1739,877–895`; `v1/engine/core.py:276`; `v1/engine/core_client.py:712–714`; `block_pool.py:176,505`; `v1/metrics/loggers.py:1040` | `--num-gpu-blocks-override N`이 profiling 결과를 덮어쓴다(`may_override_num_blocks`). 적용 시 INFO 로그 `Overriding num_gpu_blocks=%d with num_gpu_blocks_override=%d`(`:2022`). EngineCore INFO 로그 `GPU KV cache size: %s tokens`(= `max_concurrency × max_model_len`, `max_concurrency = num_blocks / ceil(max_model_len/B)`)와 `Maximum concurrency for … : %.2fx`. Prometheus `vllm:cache_config_info`(label `num_gpu_blocks`). pool N개 중 **block 0은 null block으로 영구 점유**(`block_pool:176`) → 사용 가능 N−1, `kv_cache_usage_perc` 분모도 N−1(`:505`) | `stack` | NPU는 pool 크기를 **compile `batch_size`가 정하고**([TASK08](../TASK08.md)) runtime에서 못 바꾼다. GPU는 **server 인자 하나로** 바뀐다(재compile 없음). `GPU KV cache size` 로그가 물리 pool이 아니라 `max_concurrency × max_model_len`인 점은 NPU와 같은 코드다(INDEX 관측). frontend가 `num_gpu_blocks`를 누적하는 줄(`core_client.py:712–714`)이 그대로 있어 [TASK09](../TASK09.md)의 2배 현상이 GPU에서도 나는지는 `runtime 확인`(Stage 0 예측) |
| 5 | **preemption** | `scheduler.py:442–490`(`:457`,`:481`), `:929–950`(`:938,941,949`), `:545`, `:733`; `config/scheduler.py:109` | **RUNNING 요청**(decode의 block 경계 통과, chunk 이어받기)이 `allocate_slots`에서 `None`을 받으면 루프를 돌며 preempt한다. 대상: `fcfs`(기본) → `self.running.pop()` = **running 목록의 마지막(가장 최근 admission)**, 그것이 자기 자신이면 자기를 preempt하고 중단. `priority` → `max(priority, arrival_time)`. preempt된 요청은 **block 전부 반납**(`:938`, 캐시 내용은 hash가 남아 hit 가능), `num_computed_tokens = 0`(**recompute**, `:941`), waiting 머리에 재삽입(`:949`). **swap 경로 없음.** WAITING 요청은 할당 실패 시 preempt하지 않고 `break`(`:733`). preemption이 난 step에는 새 admission이 없다(`:545`). **끄는 설정은 없다**(flag 부재) | `stack` | **NPU에는 없는 경로**(지시문 전제; NPU는 admission 시 시퀀스 slot을 잡는다). 모형 v1의 "active 항목은 축출 불가" 가정은 **축출(eviction)에 대해서는 GPU에서도 성립**한다 — free queue에는 ref_cnt 0 block만 있다. 대신 **active 요청 전체가 release되는 별도 사건**이 생긴다: 조건은 `Σ(running 요청의 필요 block) > N − 1`, 즉 inactive 캐시가 전부 축출된 뒤에도 모자랄 때다. 회피 조건(충분조건): `N − 1 ≥ max_num_seqs × ceil(max_model_len / B)`(예: 8 × 512 = 4,096 → N ≥ 4,097) 또는 workload의 길이 상한. 관측은 `vllm:num_preemptions`(counter)와 요청별 `num_preemptions`(응답에는 없음) |
| 6 | **decode 격자** | `config/vllm.py:1597–1768`(`:1647–1661`, `:1669–1680`, `:1682–1686`, `:1688–1708`); `config/compilation.py:675–690`; `config/vllm.py:69,244,493–532`; `v1/worker/gpu/cudagraph_utils.py:119–182,256–269`; `v1/cudagraph_dispatcher.py:76–95,136–160,239–328`; `v1/worker/gpu/block_table.py:174–178` | 기본 목록: `max = min(max_num_seqs × 2, 512)`를 `max_num_batched_tokens`로 자르고 `[1,2,4] + range(8, min(max+1,256), 8) + …`, `max_num_batched_tokens ≤ max`이면 그것도 추가. **`max_num_seqs=8` → `[1,2,4,8,16]`**. 사용자 목록(`compilation_config.cudagraph_capture_sizes`)이 있으면 그것을 쓰고(`max_num_batched_tokens` 초과분 제거) max를 목록 최댓값으로 둔다. `performance_mode=interactivity`면 **`1..min(max,32)` 연속 목록**. 기본 `cudagraph_mode = FULL_AND_PIECEWISE`. runtime 사상: **token 수 n → n 이상인 가장 작은 capture size**(v2 `_candidates`, v1 `_bs_to_padded_graph_size` 동일 규칙), n > max이면 graph 없이 eager(`NONE`). **uniform decode**(모든 요청 query 1)는 FULL graph(요청 수 = token 수로 padding), **혼합 batch(prefill chunk + decode)는 PIECEWISE graph를 token 수로 padding**, token 수가 max를 넘으면 eager. padding token은 `PAD_SLOT_ID=-1`로 KV를 쓰지 않는다. **`Qwen3ForCausalLM`은 0.22.0에서 model runner v2의 유일한 기본 architecture**(`config/vllm.py:69`) | 형태 `class`, 목록 `stack` | NPU 격자는 compile `decoder_batch_sizes`이고 **요청 수**로 bucket을 고른다. GPU는 **token 수**로 고르며, decode-only step에서는 둘이 같아 TASK29의 "유효 구간 `{1,2,4,8}`이 같다"가 성립한다(`max_num_seqs=8`). **다른 점**: (a) 격자가 재compile 없이 server 인자로 바뀐다, (b) **prefill이 섞인 step은 token 수가 max(16)를 넘으면 cudagraph 없이 실행**되어 padding이 없다, (c) `interactivity` 모드는 [TASK29](../TASK29.md) 절제의 **연속 격자를 실제 기판 설정으로** 제공한다(시간 비용은 다를 수 있음, `UNKNOWN`). v2 runner 사용 여부는 `runtime 확인` |
| 7 | **chunked prefill** | `config/scheduler.py:42,49,70,80,84,140`; `engine/arg_utils.py:2311–2330,2366–2395,2475–2520`; `scheduler.py:329–339,366–491,544–` (`:662`); `config/vllm.py:935–980` | 기본 **on**. token budget `max_num_batched_tokens`: OpenAI server + device memory < 70 GiB(A6000 48 GiB) → **2048**. 매 step **RUNNING 먼저**(decode는 1 token, 진행 중 chunk는 남은 prompt) 그다음 **WAITING을 남은 budget으로** 채운다 → prefill과 decode가 **한 forward에 섞인다**. `long_prefill_token_threshold=0`, `max_num_partial_prefills=1`. 끄기: `--no-enable-chunked-prefill` → prompt를 나누지 않고, 남은 budget보다 긴 prompt가 오면 그 step의 admission을 멈춘다(`:662`). 끄면 `max_num_batched_tokens = max(max_model_len, 2048)`, "does not officially support disabling chunked prefill" 경고. `scheduler_reserve_full_isl=True`: admission 때 prompt 전체 block이 free(캐시된 evictable 포함)에 들어가야 한다(`:730`). async scheduling 기본 on | `stack` | NPU(RBLN)는 prefill을 **배타 실행**한다([TASK22](../TASK22.md), [TASK29](../TASK29.md) 인용 ④). **GPU는 chunked prefill을 꺼도 배타 실행이 되지 않는다** — scheduler에 phase 구분이 없고(`:330–339` 주석), 끄는 것은 prompt 분할만 막을 뿐 decode와 같은 step에 섞는 것은 그대로다. 따라서 **NPU의 배타 prefill 의미론은 이 기판에서 설정으로 재현할 수 없다**(source 범위). B4의 stall 항 `P·K`는 GPU에서 "정지"가 아니라 "혼합 step의 step 시간 증가"로 바뀐다(`UNKNOWN`, 측정 대상) |
| 8 | **요청이 아닌 KV 소비자** | `block_pool.py:176`; `v1/attention/backends/utils.py:44`; `v1/worker/gpu/block_table.py:140–178` | **null block 1개**(block 0)가 pool 생성 시 영구 제외된다. cudagraph padding 요청·token은 block을 받지 않고 slot `PAD_SLOT_ID=-1`로 쓴다. step마다 block을 요청하는 dummy 경로는 **없다**(source 범위, v2 runner) | `stack` | NPU는 `0 < n < 8`인 decode step마다 padding용 **dummy block이 free list 머리를 가리키고** free가 0이면 회수한다([TASK63](../TASK63.md), `PRE_EVICT`). GPU에는 그런 시변 소비자가 없고 **상수 1 block**(null)만 있다 → B1의 `D`는 0, 용량 C = N − 1 |
| 9 | **관측 수단 (patch 없이)** | 아래 목록 | 아래 목록 | `stack` | 아래 목록 |

**항목 9 상세 — 설치 그대로 얻을 수 있는 것**

| 수단 | 켜는 법 | 무엇을 보나 | 주의 (source) |
|---|---|---|---|
| 요청별 `cached_tokens` | `--enable-prompt-tokens-details` | 응답 `usage.prompt_tokens_details.cached_tokens` = 첫 schedule 시점 조회 결과(local + external, `v1/metrics/stats.py:266`, `scheduler.py:627–632`) | **값이 0이면 필드 자체가 빠진다**(`completion/serving.py:446,586`, `chat_completion/serving.py:952`). flag 누락과 구별되지 않으므로 server 로그의 `enable_prompt_tokens_details`로 flag를 확인한 run에서만 "부재 = 0"으로 읽는다([TASK72](../TASK72.md) 함정과 같은 구조). preempt 후 재계산은 반영되지 않는다(첫 schedule 값) |
| prefix cache counter | 기본 | `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits`(token 단위) | **조회할 때마다** 기록된다(`kv_cache_manager.py:228`, `get_computed_blocks` 안) → 할당 실패로 대기하며 여러 번 조회한 요청은 **중복 계상**된다. 단일 층이라 NPU의 층 1/층 2 괴리는 없다 |
| prefill 출처 counter | 기본 | `vllm:prompt_tokens_cached`, `vllm:prompt_tokens_by_source{source=local_compute/local_cache_hit/…}`, `vllm:request_prefill_kv_computed_tokens` | `prefill_stats` 기반(응답 `cached_tokens`와 같은 출처, 전달 경로만 다름) |
| preemption | 기본 | `vllm:num_preemptions`(counter), 주기 로그 `Preemptions:` | 요청 단위 귀속 없음 |
| 부하 gauge | 기본 | `vllm:num_requests_running/waiting`, `vllm:kv_cache_usage_perc`(분모 N−1) | in-flight 표집 필요(INDEX 관측) |
| step token 수 | 기본 | `vllm:iteration_tokens_total` histogram | bucket 경계 `1,8,16,32,…` → **batch 2–7을 구별하지 못한다** |
| KV 거주 시간 | `--kv-cache-metrics` | `vllm:kv_block_lifetime_seconds`, `…idle_before_evict_seconds`, `…reuse_gap_seconds` | 기본 1 % block 표본 |
| **block 단위 저장·축출 사건** | `--kv-events-config '{"enable_kv_cache_events": true, "publisher": "zmq", …}'` | `BlockStored`(hash, **token_ids**, block_size)와 `BlockRemoved`(hash)가 **축출 순간마다** 발행된다(`block_pool.py:316,385–392`) | 요청 id가 없다 — 귀속은 token 내용으로 해야 한다. zmq 수신기가 필요(local tcp) |
| **cudagraph padding 표** | `--cudagraph-metrics` | 로그 주기마다 `(Unpadded Tokens, Padded Tokens, Num Paddings, Runtime Mode, Count)` 표 | **v1 runner만 `cudagraph_stats`를 채운다**(`gpu_model_runner.py:3818–3832`). v2 runner(`v1/worker/gpu/`)에는 생산자가 없다 → Qwen3 기본(v2)에서는 **빈 표로 예상**(Stage 0 L2·L3에서 확인). step 시각 없이 주기 집계뿐 |
| resolved config | 기본 | EngineCore 기동 로그 `Initializing a V1 LLM engine (v0.22.0) with config: …`, `Chunked prefill is enabled with max_num_batched_tokens=…`, `Asynchronous scheduling is …` | — |

**patch 없이 얻을 수 없는 것 → observation-only patch 후보 (제안만, 작성·적용하지 않음)**

| 관측 대상 | 왜 없나 | 후보 지점 (제안) |
|---|---|---|
| step별 (running 요청 수, 스케줄 token 수, prefill 포함 여부, 선택된 capture size, runtime mode) — 시각 포함 | v2 runner는 `CUDAGraphStat`을 만들지 않고, v1 runner도 주기 집계뿐 | (a) `v1/worker/gpu/model_runner.py`의 dispatch 직후 DEBUG 1줄(NPU [TASK12](../TASK12.md)의 `[BUCKET]`과 같은 형식), 또는 (b) `VLLM_USE_V2_MODEL_RUNNER=0`으로 v1 runner를 쓰고 `--cudagraph-metrics`를 쓰는 **patch 없는 대안**(substrate가 바뀌므로 Advisor 결정) |
| 축출된 block이 **어느 요청의 어느 할당**으로 축출됐는가 | `get_new_blocks`에 요청 id가 없다. KV events는 축출된 block의 hash만 준다 | `single_type_kv_cache_manager.allocate_new_blocks`에서 `request_id`와 축출 block id·hash를 DEBUG 로그 — NPU `[PFX]`의 GPU 대응. 또는 KV events + scheduler 사건 순서를 client 없이 재생하는 방식([TASK72](../TASK72.md) R5′)으로 대체 가능한지 먼저 검토 |
| step별 admission 순서(조회 시각·할당 시각) | 로그 없음 | `scheduler.py:594`·`:721` 주변 DEBUG |

## 핵심 발견

1. **`stack`** — **설치된 CUDA 빌드는 `vllm 0.22.0`이고 NPU 스택 upstream과 같은 버전이다.** TASK29·TASK71이 NPU 서버의 `+cpu` 빌드에서 인용한 줄(`scheduler.py:594`·`:721`, `kv_cache_utils.py:164–181`, `compilation.py:676–690`)이 이 빌드에서도 같은 줄에 있다. model도 같은 revision·같은 byte 수다.
2. **`stack`** — **조회 후 할당이며 hit block은 새 할당 전에 `touch`로 보호된다.** 같은 admission 안에서 hit block이 축출되는 경로는 source에 없다. 할당 실패는 축출 없이 대기로 끝난다. NPU(할당 후 조회)와 반대이고 [TASK71](../TASK71.md) 발견 3과 일치한다.
3. **`class`(형태) / `stack`(세부)** — **회수는 release 시점 LRU, 한 요청 안에서는 꼬리 먼저, 미사용 block 먼저.** 형태를 `class`로 보는 근거: 반납된 block이 hit 가능한 evictable 상태로 남고 사용 순서로 축출되는 것은 paged prefix cache 설계 범주의 성질이다. tail-first와 미사용 우선은 이 구현의 선택이다.
4. **`class`(형태) / `stack`(값)** — **hit 공식의 형태는 NPU와 같고(`floor(min(shared, query−1)/B)·B`), block 크기(16 대 128)와 `shared`의 정의가 다르다** — GPU는 KV가 계산된 생성 token까지 캐시하므로 `shared ≤ prompt + output − 1`, NPU 층 2는 prefill token만.
5. **`stack`** — **GPU에는 preemption(recompute) 경로가 있고 끌 수 없다.** 발동 조건은 running 요청의 block 수요가 N−1을 넘는 것이고, 대상은 FCFS에서 가장 최근 admission이다. **inactive 캐시는 항상 먼저 축출되므로 "active 항목은 축출 불가"는 축출에 대해 여전히 참이며**, preemption은 "active 요청 전체 release + 재계산"이라는 별도 사건으로 모형에 넣어야 한다.
6. **`stack`** — **chunked prefill을 꺼도 prefill은 decode와 같은 step에 섞인다.** NPU의 배타 prefill은 이 기판에서 설정으로 재현되지 않는다.
7. **`stack`** — **격자 사상은 요청 수가 아니라 token 수다.** decode-only step에서는 같지만, prefill이 섞인 step은 token 수가 최대 capture size를 넘으면 cudagraph 없이 실행되어 padding이 없다. 격자는 server 인자로 바뀌고 `performance_mode=interactivity`가 연속 격자를 준다.
8. **`stack`** — **0.22.0은 `Qwen3ForCausalLM`에 model runner v2를 기본으로 쓰며, v2는 `--cudagraph-metrics` 통계를 만들지 않는다.** patch 없는 padding 관측은 v1 runner에서만 가능하다(Stage 0에서 확인).
9. **`stack`** — **요청이 아닌 KV 소비자는 상수 null block 1개뿐이다**(NPU의 시변 dummy block 없음).

## 해석

- 발견 2·3·9를 합치면 GPU 기판의 B1 인스턴스는 `resume_allocates_first=False`, 창 = [T release, R lookup], `D = 0`, `C = N − 1`, 단위 16 token, tail-first 부분 손실이다. 모형 v0의 block 단위 식(B1-2)이 그대로 적용될 형태다(파생 해석, 미검증).
- 발견 4는 GPU에서 **생성이 길수록 재사용이 늘 수 있다**는 뜻이다(NPU와 반대 방향). 단 재도착 prompt가 생성 token을 같은 token id로 담을 때만이며, OpenAI chat 경로는 detokenize → template → 재토큰화를 거치므로 실제로 담기는지는 workload·template에 달렸다(`UNKNOWN`).
- 발견 5는 steady-state 실험 설계에서 **pool 크기 N과 `max_num_seqs × max_model_len`의 관계**를 통제 변수로 만든다. preemption이 없는 영역(`N − 1 ≥ 8 × 512`)에서 먼저 재고, preemption 영역은 모형 확장 뒤에 다루는 순서가 자연스럽다(권고).
- 발견 6·7로 [TASK29](../TASK29.md) 축 ③의 GPU 대응(chunked, 정지 0)은 source 수준에서 맞지만, 혼합 step이 eager로 돌아 **step 비용이 decode-only step과 다른 곡선**을 가진다. B2·B4의 GPU 인스턴스에는 혼합 step 비용 모형이 필요하다.

## 확인되지 않은 사항

- 실제 resolved `block_size`, 기본 capture 목록, model runner(v1/v2), attention backend, async scheduling 여부 — Stage 0 L1에서 확인([GTASK02](GTASK02.md))
- frontend `num_gpu_blocks` 2배 누적이 GPU에서도 나는지 — Stage 0 예측
- async scheduling에서 종료 요청의 block 반납이 다음 admission 대비 몇 step 늦는지(`UNKNOWN`)
- `vllm 0.22.0+cpu`(NPU)와 CUDA 빌드의 `v1/core/` 파일 단위 동일성(`UNKNOWN`, NPU 서버 접근 없음)
- chat 경로에서 재도착 prompt가 이전 생성 token을 같은 id로 담는지(`UNKNOWN`)
- GPU 사용 이력(측정 구간 밖) — 기록 장치 없음(`UNKNOWN`)

## 실패 / 무효 시도

- **model download 1차 실패**: `~/.bashrc`의 `HF_HUB_ENABLE_HF_TRANSFER=1` 때문에 `hf_transfer` package가 없다는 `ValueError`로 중단됐다(`results/gpu/env/model_download.attempt1_failed_hf_transfer.log`). package를 추가 설치하지 않고 해당 변수만 `0`으로 두고 재시도해 성공했다. 이후 run script도 `HF_HUB_ENABLE_HF_TRANSFER=0`, `HF_HUB_OFFLINE=1`을 명시한다.
- inventory script 첫 실행이 `ls`로 dotfile(`.gitattributes`)을 빠뜨려 12 파일로 셌다. `ls -A`로 고쳐 다시 수집했고 첫 산출물은 지웠다.

## 연구 원칙에 미치는 영향

- 원칙 4의 GPU 방향: RBLN 상수(128 token, outer slot 8, dummy, 배타 prefill)를 GPU 예측에 옮기지 않는다. 이 TASK의 표가 두 기판의 의미론 차이를 줄 단위로 고정한다.
- 관측 불가를 0으로 채우지 않는다: `cached_tokens` 필드가 **0일 때 빠지는** 구현이므로, 새 GPU runner는 flag 확인 전에는 부재를 `None`으로 기록해야 한다(Stage 0 probe가 그렇게 한다).

## 다음 작업

- [GTASK02](GTASK02.md) — Stage 0 기능 확인(선등록 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md))과 descriptor 초안.
- 그 뒤는 Advisor 지시 없이 착수하지 않는다.

## 재현 정보

- branch `gpu-a6000`, 시작 commit `e1f791eff6e4b65093248343a8246e9a8bbbfc2b`
- venv `/home/csdc/kyeom/envs/vllm-0.22.0`, `vllm 0.22.0`, `torch 2.11.0+cu130`, driver 580.178.04
- model `Qwen/Qwen3-4B@1cfa9a7208912126459214e8b04321603b3df60c`, `/mnt/nvme/hf/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a72…`
- inventory: `results/gpu/env/inventory-20260929T084320Z/` (git 비추적)
- source 감사 대상: `/home/csdc/kyeom/envs/vllm-0.22.0/lib/python3.12/site-packages/vllm/`
- 선등록 commit: 해당 없음(측정·판정 없음). Stage 0 선등록은 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md)
