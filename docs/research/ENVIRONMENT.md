# 실측 환경 명세

**성격**: 이 문서의 모든 값은 **2026-08-28에 이 서버에서 명령으로 재확인**한 것이다. 과거 TASK 문서의 기록을 전사하지 않았다. 기록과 현물이 어긋난 항목은 §F에 따로 모았다.

**형식**: 명세표만 둔다. 논문 문장은 사용자가 쓴다.

**조사 성격**: read-only. 측정·compile·serving 기동 없음 — 버전 조회, 파일 읽기, 장치 상태 조회 명령만 실행했다.

---

## A. 하드웨어

| 항목 | 값 | 확인 명령 |
|---|---|---|
| 서버 제품명 | **Supermicro AS -4125GS-TNRT2** | `cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name` |
| 호스트명 | **`atom-max8`** | `hostname` |
| NPU 제품명 | **RBLN-CA25** | `rbln-smi` |
| NPU 세대 | **`UNKNOWN`** — 도구가 제품명만 출력하고 세대·아키텍처 문자열을 내지 않는다 | — |
| visible device 수 | **32** (`rbln0`–`rbln31`) | `rbln-smi \| grep -cE "^\| [0-9]+ +\|"` → `32` |
| 카드(그룹) 수 | **8** — 제품명이 4 device마다 한 번씩 출력되고 NPU 번호 0·4·8·12·16·20·24·28에 붙는다 | `rbln-smi \| grep -E "^\| [0-9]+ +\| RBLN"` → 8행 |
| device당 메모리 | **15.7 GiB** (32/32 device 전부 동일) | `rbln-smi \| grep -oE "/ *[0-9.]+GiB"` → `15.7GiB` × 32 |
| PCI BUS 배치 | 4 device씩 연속 (예: `0000:05:00.0`–`0000:08:00.0`) | `rbln-smi` 원문 |
| KMD(커널 드라이버) 버전 | **3.2.2** | `rbln-smi` 헤더 `Device Information KMD ver: 3.2.2` |
| 커널 모듈 상세 | **`UNKNOWN`** — `modinfo rbln`·`lsmod \| grep rbln`이 아무것도 반환하지 않는다(모듈명 미상) | `modinfo rbln`, `lsmod` |
| host CPU | **AMD EPYC 9254 24-Core Processor × 2 socket** | `lscpu` |
| host 코어/스레드 | **48 physical core / 96 logical** (24 core/socket × 2 socket, 2 thread/core) | `lscpu` |
| host RAM | **1,511 GiB total** (조회 시 available 1,490 GiB) | `free -g` |
| 스토리지 | LVM 논리 볼륨 `/dev/mapper/ubuntu--vg-lv--0`, **876 GB**, 조회 시 사용 138 GB (17 %) | `df -h /` |
| 스토리지 매체 종류 | **`UNKNOWN`** — `lsblk`가 loop 장치만 먼저 보고하고 물리 매체의 회전 여부·모델을 확인하지 못했다 | `lsblk -d -o NAME,SIZE,ROTA,MODEL` |

**`rbln-stat`과 `rbln-smi`는 같은 출력을 낸다** (둘 다 `/usr/bin`에 존재, 동일 표 형식).

### 명령 출력 원문 (발췌)

```
$ rbln-smi
Fri Aug 28 18:46:50 2026
+-------------------------------------------------------------------------------------------------+
|                                Device Information KMD ver: 3.2.2                                |
+-----+-----------+---------+---------------+------+---------+------+---------------------+-------+
| NPU |    Name   |  Device |   PCI BUS ID  | Temp |  Power  | Perf |  Memory(used/total) |  Util |
+=====+===========+=========+===============+======+=========+======+=====================+=======+
| 0   | RBLN-CA25 | rbln0   |  0000:05:00.0 |  39C |  45.2W  |  P14 |    0.0B / 15.7GiB   |   0.0 |
| 1   |           | rbln1   |  0000:06:00.0 |  42C |         |  P14 |    0.0B / 15.7GiB   |   0.0 |
| 2   |           | rbln2   |  0000:07:00.0 |  37C |         |  P14 |    0.0B / 15.7GiB   |   0.0 |
| 3   |           | rbln3   |  0000:08:00.0 |  32C |         |  P14 |    0.0B / 15.7GiB   |   0.0 |
+-----+-----------+---------+---------------+------+---------+------+---------------------+-------+
| 4   | RBLN-CA25 | rbln4   |  0000:0c:00.0 |  42C |  45.6W  |  P14 |    0.0B / 15.7GiB   |   0.0 |
...
```

```
$ lscpu | grep -E "^Model name|^CPU\(s\)|^Thread|^Core|^Socket|^Architecture"
Architecture:                         x86_64
CPU(s):                               96
Model name:                           AMD EPYC 9254 24-Core Processor
Thread(s) per core:                   2
Core(s) per socket:                   24
Socket(s):                            2

$ free -g | head -2
               total        used        free      shared  buff/cache   available
Mem:            1511          12        1372           0         125        1490

$ df -h / | tail -1
/dev/mapper/ubuntu--vg-lv--0  876G  138G  694G  17% /
```

---

## B. 소프트웨어 스택

| 항목 | 값 | 확인 명령 |
|---|---|---|
| OS | **Ubuntu 22.04.5 LTS** | `cat /etc/os-release` |
| 커널 | **6.8.0-40-generic** | `uname -r` |
| Python | **3.10.12** | `python3 --version` |

### 패키지 버전

발췌 기준: **실험 실행 경로가 import하거나 artifact를 만드는 데 쓰인 패키지**. `importlib.metadata.version()`으로 조회했다 — `pip list`의 표시명(`vllm_rbln`)과 배포명(`vllm-rbln`)이 달라 배포명 기준으로 재확인했다.

| 패키지 | 버전 |
|---|---|
| `vllm` | **0.22.0+cpu** |
| `vllm-rbln` | **0.11.1** |
| `optimum-rbln` | **0.11.1** |
| `rebel-compiler` | **0.11.1.post1** |
| `torch` | **2.11.0+cpu** |
| `transformers` | **5.8.1** |
| `tokenizers` | 0.22.1 |
| `safetensors` | 0.8.0 |
| `huggingface-hub` | 1.27.0 |
| `numpy` | 2.2.6 |

`pip list`에는 `torch-rbln 0.3.0`도 있으나 실험 경로가 import하지 않는다.

```
$ python3 -c "import importlib.metadata as m; print(m.version('vllm-rbln'))"
0.11.1
$ python3 -m pip list | grep -iE "rbln|vllm"
optimum-rbln     0.11.1
torch-rbln       0.3.0
vllm             0.22.0+cpu
vllm_rbln        0.11.1
```

### 실험에서 상수로 걸린 환경 변수

출처: [`experiments/npu/stage2/run_sweep.sh`](../../experiments/npu/stage2/run_sweep.sh) — **모든 stage 2 측정이 이 script를 거친다.**

| 변수 | 값 | 위치 | 목적 |
|---|---|---|---|
| `PYTHONPATH` | **제거**(`env -u PYTHONPATH`) | `run_sweep.sh:44`, `:60` | host의 다른 PYTHONPATH가 import 경로에 섞이지 않게 |
| `VLLM_LOGGING_LEVEL` | `DEBUG` | `run_sweep.sh:44` | `[BUCKET]`·`[PFX]` 로그를 켜기 위해 |
| `VLLM_RBLN_METRICS` | `1` | `run_sweep.sh:44` | 벤더 metric 절 출력 |

**attention 모드를 강제하는 플래그는 쓰지 않았다.** `attn_impl`은 환경 변수가 아니라 **compile 시점 artifact 설정**이며 값은 `eager`다(§C).

serving 인자(`run_sweep.sh:45–47`): `vllm serve <ARTIFACT> --host 127.0.0.1 --port 8000 --enable-prefix-caching --enable-prompt-tokens-details`.

---

## C. 모델과 컴파일 구성

| 항목 | 값 | 확인 |
|---|---|---|
| 모델 | **`Qwen/Qwen3-4B`** | HF 캐시 `models--Qwen--Qwen3-4B` |
| revision | **`1cfa9a7208912126459214e8b04321603b3df60c`** | `~/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/` |
| dtype | **bfloat16** | artifact `config.json` `dtype` |
| 아키텍처 | `Qwen3ForCausalLM`, `model_type=qwen3` | 동 |
| layer 수 | **36** (전부 full attention) | `num_hidden_layers=36` |
| attention head | 32 | `num_attention_heads` |
| KV head | **8** | `num_key_value_heads` |
| head_dim | **128** | `head_dim` |
| hidden_size | 2560 | 동 |
| `max_position_embeddings` | 40,960 | 동 |
| vocab | 151,936 | 동 |
| **compile `max_seq_len`** | **8,192** | `rbln_config.json` |
| **`num_devices`** | **4** | `rbln_config.json` (키 이름이 `num_devices`이며 `tensor_parallel_size`가 아니다) |
| `attn_impl` | **`eager`** | `rbln_config.json` |
| `quantization` | `{}` (없음) | 동 |
| 파라미터 수 | **4.02 B** — 공식 명세 인용. **이 서버에서 재계산하지 않았다** | — |
| KV bytes/token (파생) | `36 × 8 × 128 × 2 × 2` = **147,456 B = 144.0 KiB** | 위 값들에서 계산 |

### Compile artifact 전수

디렉터리 실측 크기(`os.walk` 바이트 합 ÷ 2³⁰)와 각 `rbln_config.json`에서 재확인했다. **compile 소요 시간은 이 서버에서 재확인할 수 없어 생성 TASK의 기록을 인용한다**(그 사실을 열에 표기).

| artifact | `batch_size` | `decoder_batch_sizes` | `kvcache_num_blocks` | `kvcache_block_size` | 크기(실측) | compile 시간(기록) | 생성 / 사용 |
|---|---|---|---|---|---|---|---|
| `Qwen3-4B-rbln-b1-s8192-d4` | 1 | `[1]` | 1 | 8,192 | **9.083 GiB** | 165.0 s ([TASK06](TASK06.md)) | 생성 [TASK06](TASK06.md), 사용 [TASK09](TASK09.md) |
| `Qwen3-4B-rbln-b8-s8192-d4-mb` | 8 | `[8,4,2,1]` | 8 | 8,192 | **11.501 GiB** | 349.0 s ([TASK10](TASK10.md)) | 생성 [TASK10](TASK10.md), 기준 arm으로 [TASK13](TASK13.md)–[TASK40](TASK40.md) 전반 |
| `Qwen3-4B-rbln-b8-s8192-d4-mb6` | 8 | `[8,6,4,2,1]` | 8 | 8,192 | **12.306 GiB** | 416.0 s ([TASK23](TASK23.md)) | 생성·사용 [TASK23](TASK23.md) 격자 개입 |
| `Qwen3-4B-rbln-b16-s8192-d4-batchonly` | 16 | `[16,8,4,2,1]` | 16 | 8,192 | **12.378 GiB** | 407.0 s ([TASK35](TASK35.md)) | 생성·사용 [TASK35](TASK35.md) 절제 arm ② |
| `Qwen3-4B-rbln-b16-s8192-d4-mb16` | 16 | `[16,10,8,6,4,1]` | 16 | 8,192 | **13.202 GiB** | 480.0 s ([TASK34](TASK34.md)) | 생성 [TASK34](TASK34.md), 사용 [TASK35](TASK35.md)·[TASK36](TASK36.md)·[TASK40](TASK40.md) |
| `Qwen3-4B-rbln-b24-s8192-d4-mb24` | 24 | `[24,10,8,6,4,1]` | 24 | 8,192 | **13.259 GiB** | 486.0 s ([TASK40](TASK40.md)) | 생성·사용 [TASK40](TASK40.md) |
| `Qwen3-4B-rbln-b32-s8192-d4-mb32` | 32 | `[32,10,8,6,4,1]` | 32 | 8,192 | **13.320 GiB** | 474.0 s ([TASK40](TASK40.md)) | 생성·사용 [TASK40](TASK40.md) |

`models/` 합계 **85.0 GiB**.

### KV cache 구조

| 값 | 확인 |
|---|---|
| `kvcache_block_size` = **8,192** (= `max_seq_len`) | 7개 artifact 전부에서 동일하게 확인 |
| `kvcache_num_blocks` = **`batch_size`** | 7개 artifact 전부에서 `num_blocks == batch_size` 성립 (1·8·8·16·16·24·32) |
| 따라서 block 1개 = **sequence 1개분** | 위 두 값의 곱이 `batch_size × max_seq_len` |

---

## D. 관측 스택

### Patch

| 항목 | 값 |
|---|---|
| 대상 파일 | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/model_executor/models/optimum/model_base.py` |
| 대상 함수 | `RBLNOptimumDecoderMixin.preprocess_for_decoder` |
| 적용 전 SHA256 | `46ce1675a2b55e36d4d6dd0154edae793cd3874ed1fbe16e74a40ed7c809298e` |
| **현재 상태** | **`patched`**, SHA256 **`70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`** |
| patch 파일 SHA256 | `034b2492bb6623a5b63fad79f0c61c8dd690e946390feda4668e57db6fdd224d` |
| diff 규모 | 추가 9줄(코드 5 + 주석 4), 기존 줄 수정·삭제 0 |
| observation-only 근거 | [patches/README.md](../../patches/README.md) 7개 항목을 [patches/vllm_rbln-0.11.1/README.md](../../patches/vllm_rbln-0.11.1/README.md)가 채운다. 추가 코드는 `logger.debug` 호출 하나이며 제어 흐름·batch 선택·KV 할당을 건드리지 않는다 |

```
$ bash patches/vllm_rbln-0.11.1/apply.sh status
target:  /usr/local/lib/python3.10/dist-packages/vllm_rbln/model_executor/models/optimum/model_base.py
sha256:  70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01
state:   patched
```

**patch는 1건뿐이다.** `patches/` 아래에 다른 patch 디렉터리가 없다.

### 관측 신호

| 신호 | 층 | 성격 |
|---|---|---|
| `[BUCKET] request_nums=<n> padded_batch_size=<b>` (DEBUG 로그) | 실행 | patch가 노출. per-step `(실제 요청 수, 선택된 bucket)` |
| `[PFX] [CACHE-HIT]` (DEBUG 로그) | 층 2 | outer/inner block ID |
| `usage.prompt_tokens_details.cached_tokens` (응답 필드) | **층 2** | **동시 workload의 1차 per-request 채널** ([TASK18](TASK18.md) 게이트 통과) |
| `vllm:prompt_tokens_cached_total` | **층 2** | 재사용 token. **참 지표** |
| `vllm:request_prefill_kv_computed_tokens` | **층 2** | 실제 계산 token. **참 지표** |
| `vllm:prefix_cache_hits_total` | **층 1** | **거짓 양성** — 층 2가 evict된 뒤에도 hit을 보고해 실제 재사용을 최대 100 % 과대평가 ([TASK14](TASK14.md)·[TASK15](TASK15.md)) |
| `vllm:iteration_tokens_total` | — | **계산량 지표 아님** — 제출 prompt token을 센다 |
| `vllm:num_requests_running` / `_waiting` / `kv_cache_usage_perc` | scheduler | in-flight 표집 필요 |

### Device time 두 채널

구현: [`experiments/npu/analysis/config_device.py`](../../experiments/npu/analysis/config_device.py).

| 채널 | 정의 | 모형 의존 |
|---|---|---|
| **A′** | `[BUCKET]` step 열의 `(actual, bucket)`마다 [TASK13](TASK13.md) decode step 비용을 합산 + per-request `prompt_tokens − cached_tokens`에 [TASK22](TASK22.md) `PrefillCostModel` 적용 | 두 비용 모형에 의존 |
| **B** | client `sent_s`/`done_s`의 **in-flight 구간 합집합** | **무의존** |
| 허용차 | `τ(N) = max(0.02, r_BASE / B_BASE)`, `r_BASE = B_BASE − A′_BASE` | [TASK36](TASK36.md)에서 교정 |

---

## E. 워크로드

### Trace 원천

| 항목 | 값 | 확인 |
|---|---|---|
| 경로 | `/home/rebel/vllm-continuum/results/tracelab/summary.json` (legacy, **read-only**) | `ls -la` |
| **원 데이터셋** | **TraceLab** — `uw-syfi/TraceLab`, **arXiv:2606.30560**, Zhu·Jacob·Ma·Pan·Wang·Krishnamurthy·Kasikci (2026-06-29). **CC BY 4.0**(데이터) / Apache-2.0(코드) | legacy `tasks/TASK31.md` 판정 표, arXiv abs 재확인 (2026-08-28) |
| **사용 릴리스** | **v0.0.2** — `jsonl.gz` 96 MB + `duckdb` 152 MB. **665,453 스텝 / 743,819 도구호출 / 8,058 세션 / 52명**, Claude Code + Codex 실사용, 2025-09~2026-07 | legacy `tasks/TASK31.md` §1-1·§7 (SHA256 `11ce51ec…` 공표값 일치 확인 기록) |
| **arXiv 초록과 릴리스의 규모 차이** | 초록은 약 4,300 세션 / 35만 스텝 / 43만 도구호출로 적는다. **우리가 쓴 v0.0.2는 그보다 크다**(8,058 / 665,453 / 743,819). **버전을 명시해 인용해야 한다** | arXiv abs 대조 |
| **이 프로젝트가 읽은 것** | legacy가 원자료에서 재계산한 `summary.json`. **원 gz(`/mnt/ssd/tracelab/syfi_coding_trace.jsonl.gz`)는 현재 접근 불가** | [TASK31](TASK31.md), legacy `experiments/analyze_tracelab.py` |
| rows | **665,453** | `summary.json["rows"]` |
| tool calls | **743,819** | `summary.json["tools"]` |
| sessions | **8,058** | `summary.json["sessions"]` |
| latency 출처 분할 | wall **397,527** / internal **345,523** / none **769** (합 743,819) | `summary.json["lat_src"]` |
| latency 우선순위 | **internal이 있으면 internal, 없으면 wall.** 원 필드는 `tool_internal_latency_ms`(러너 보고)와 `tool_wall_latency_ms`(= `result_at − emitted_at`) | legacy `analyze_tracelab.py` 주석 ③ |
| front-end 구분 | `claude`, `codex` 두 계열의 `n`/`p50`/`p90`/`p99`/`sub1s_pct` | `summary.json["lat"]` 키 |
| **sampler가 쓰는 도구 종수** | **43** | `load_mix(..., cap_s=60).tools` 길이 재계산 |
| 제외 규칙 | `HUMAN_IN_THE_LOOP` = `AskUserQuestion`, `ExitPlanMode`, `request_user_input`, `TaskOutput` — **도구가 아니라 사람을 기다리는 것**이라 제외 | `tools.py` |
| cap | **60 s** | `load_mix(cap_s=60.0)` |

**분포 재구성 방식**: 도구를 호출 빈도로 뽑고, 그 도구의 **측정된 분위수를 지나는 곡선**에서 지연을 뽑는다. **적합(fit)이 없다** — 분위수는 정확히 맞추고, 가정된 형태는 중앙값 아래 구간(값이 작아 문제되지 않는 영역)뿐이다.

### Generator 파라미터

출처: [`run_sweep.sh`](../../experiments/npu/stage2/run_sweep.sh) `:60–68`이 `session_runner.py`에 넘기는 인자.

| 항목 | 값 |
|---|---|
| 세션 수 N | 측정마다 격자로 지정. stage 2 전반 `{3,4,5,6,7,8,10,12,16}`, 확증 구간 `{6,8}`, 탐색 `{10}` |
| 세션당 turn | **2** (`--turns 2`) |
| 첫 segment | `uniform:800:1600` token |
| 이후 segment | `fixed:8` token |
| 생성 길이 | `uniform:32:256` token |
| gap 법칙 | `toolmix:<summary.json>:60` (TASK31 이후). 그 이전 기본값은 `uniform:1:5` |
| sampling seed | **`20260819`** (전 측정 고정 — server측 sampling 통제값) |
| 반환 정책 기본 | `immediate` (정책 객체를 만들지 않아 client 경로가 byte-identical) |

### Seed 체계

`plan seed = (base_seed, block_id)` → `derive_block_seed()`가 `f"{base_seed}:{block_id}"`를 해시. **arm은 seed에 들어가지 않는다** — 그래서 같은 `(base_seed, block)`의 모든 arm이 **동일한 plan**을 받는다(불변식 P1).

| 용도 | seed |
|---|---|
| 구성 탐색 (explore) | `20260910`, `20260921`, `20260932` |
| 구성 평가 (eval) | `20260943`, `20260954`, `20260965` |
| [TASK34](TASK34.md) 측정 | `20260980` |
| [TASK35](TASK35.md) 최종 확증 | `20261000` |
| [TASK36](TASK36.md) N=6 재확증 | `20261100` |
| [TASK40](TASK40.md) 포화 곡선 | `20261200` |

선등록 문서별 `base_seed` 전수: `20260819`(decode cost), `20260821`, `20260822`, `20260823`, `20260830`, `20260831`, `20260840`, `20260841`·`20260842`, `20260850`, `20260860`, `20260910`, `20260980`, `20261000`, `20261100`, `20261200`.

**탐색/평가 분리 규칙**: 구성 선택은 explore seed에서만 점수화하고 eval seed에서 확인한다. **확증 측정은 그 어느 것도 아닌 새 seed**를 쓴다([TASK35](TASK35.md)·[TASK36](TASK36.md)·[TASK40](TASK40.md)이 각각 새 값).

### 블록 설계

| 항목 | 값 |
|---|---|
| 블록 수 | 확증 측정 **3**(b0·b1·b2). 일부 초기 측정은 5–6 |
| 짝 설계 (P1) | 같은 `(base_seed, block)`의 모든 arm이 동일 plan. 매 run 검증하며 위반 시 `INVALID` |
| P2 | 모든 arm의 decode 작업량 `Σ(completion_tokens − 1)` 동일 |
| arm 순서 | 블록마다 회전(예: [TASK40](TASK40.md) b0 `B8→B16→B24→B32`, b1 `B24→B32→B8→B16`, b2 `B32→B8→B16→B24`) |
| **fresh server** | **조합마다 server를 새로 띄우고 PID로 종료**한다. `SRV=$!` → `kill -TERM "$SRV"` → 유예 후 `kill -KILL`. pattern kill을 쓰지 않는다([KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 2번) |

---

## F. 정합 점검 — 기존 서술과의 불일치

**이 절은 보고만 한다. 어느 쪽이 맞는지는 Advisor·사용자 판정이며 수정하지 않았다.**

### F-1 (중대) — trace 출처 서술이 사실과 달랐다 — **[TASK48](TASK48.md)에서 정정됨**

| | |
|---|---|
| 위치 | [`paper/draft/02_background.md:29`](../../paper/draft/02_background.md) |
| 현재 서술 | "a trace of coding-agent sessions **collected by the authors from their own use** of two agent front-ends, **instrumented at the client**" |
| 재확인된 사실 | [TASK31](TASK31.md)과 `tools.py` docstring 모두 **"legacy 저장소가 공개(public) coding-agent trace에서 자체 재계산한 산출물"** 이라 기록한다. **원 gz는 접근 불가**이며 이 프로젝트는 재계산 산출물만 읽었다 |
| 파급 | 같은 문단의 **비공개 사유**("저자의 작업 세션 prompt·출력이라 제3자 자료 없이는 공개 불가")도 함께 성립하지 않는다. 실제 제약은 **원자료가 우리에게도 없다**는 것이다 |
| 판단 | **투고 전 반드시 정정해야 한다.** 자료 출처 진술이라 문체 문제가 아니다 |
| **정정** | **[TASK48](TASK48.md)에서 반영.** §II-D를 TraceLab v0.0.2 인용으로 다시 쓰고, "저자 수집"과 프라이버시 사유 문장을 삭제했으며, 실제 제약(**원 아카이브 접근 불가, 분위수만 사용**)을 §IX 한계로 옮겼다 |

### F-2 — trace 규모 표기가 rows와 tool calls를 혼동했다 — **[TASK48](TASK48.md)에서 정정됨**

| | |
|---|---|
| 현재 서술 | "**665,453 records** over 8,058 sessions" |
| 사실 | `rows` = 665,453, **`tools`(tool call 수) = 743,819**, `sessions` = 8,058. 세 수가 서로 다른 대상을 센다 |
| 판단 | "records"가 rows를 뜻한다면 맞지만, 뒤 문장이 도구 지연을 말하므로 **tool call 수(743,819)를 함께 적는 편이 정확**하다 |

### F-3 — vLLM 버전 표기가 절마다 달랐다 — **[TASK48](TASK48.md)에서 정정됨**

| 위치 | 표기 |
|---|---|
| `01_introduction.md:5` | `vllm 0.22.0` |
| `02_background.md:7` | `vllm 0.22.0+cpu` |
| 사실 | `importlib.metadata.version("vllm")` = **`0.22.0+cpu`** |

### F-4 — `num_devices`를 tensor parallel로 부르는 곳이 있었다 — **[TASK48](TASK48.md)에서 정정됨**

지시문과 일부 서술이 `num_devices`를 "tensor parallel 정도"로 부른다. **artifact의 키 이름은 `num_devices`이고 `tensor_parallel_size` 키는 존재하지 않는다.** 두 개념이 같은지는 이 조사로 확인하지 못했다(`UNKNOWN`).

### F-5 — "43 tools"가 전체가 아니라 sampler 채택분 — **[TASK48](TASK48.md)에서 조건화됨**

[`09_limitations.md:7`](../../paper/draft/09_limitations.md)이 "a single code-agent trace of 43 tools"라고 적는다. **43은 `load_mix`가 60 s cap과 human-in-the-loop 제외 후 채택한 도구 수**이며, trace 전체의 도구 종수는 이 조사로 확인하지 못했다(`summary.json`이 종수를 따로 내지 않는다, `UNKNOWN`).

### 일치 확인된 항목 (불일치 없음)

- artifact 크기 7종이 전부 생성 TASK 기록과 일치 (9.083 / 11.501 / 12.306 / 12.378 / 13.202 / 13.259 / 13.320 GiB)
- `kvcache_num_blocks == batch_size`가 7종 전부에서 성립 — [TASK08](TASK08.md)의 source 판정과 일치
- KV bytes/token 147,456 B가 현재 config(36·8·128)에서 재계산됨 — [TASK05](TASK05.md)와 일치
- device 32개 / 카드 8그룹 / 15.7 GiB — [TASK05](TASK05.md)의 재-inventory와 일치
- patch SHA256 `70942d16…`이 모든 측정 run의 provenance 기록과 일치
- compile 시간 486.0 s·474.0 s가 [TASK40](TASK40.md) 기록과 일치 → 논문 §VI-B의 "8.1분·7.9분"과 일치

---

## UNKNOWN 목록

| 항목 | 사유 |
|---|---|
| NPU 세대·아키텍처 명 | 도구가 제품명(`RBLN-CA25`)만 출력 |
| 커널 모듈 이름·버전 | `modinfo rbln`·`lsmod \| grep rbln` 무응답 |
| 스토리지 매체 종류(SSD/HDD) | `lsblk`에서 물리 매체를 특정하지 못함 |
| 모델 파라미터 수 | 공식 명세 인용(4.02 B). **이 서버에서 재계산하지 않았다** |
| `num_devices`와 tensor parallel의 동치 여부 | 확인 경로 없음 (F-4) |
| trace 전체의 도구 종수 | `summary.json`이 종수를 따로 내지 않고 원 아카이브에 접근할 수 없음 (F-5). 논문은 **"채택된 43종"** 으로 조건화해 표기한다 |
| host의 hostname 이력 | [NPU_ENVIRONMENT.md](../environment/NPU_ENVIRONMENT.md)의 `rebel-pcie-0123`과 현재 `atom-max8`이 같은 장비인지는 [TASK05](TASK05.md) 이래 `UNKNOWN` |
