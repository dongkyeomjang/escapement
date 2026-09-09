# TASK58 — 3.2 근거 마감 감사: 계층 표기·회수 사건·용량 개입

## 상태

DONE

## 판정

감사 계획: [LAYER_AUDIT_PLAN.md](LAYER_AUDIT_PLAN.md) (commit `a1826b7`, 계산 전).
기준 commit `a4e6433`. **신규 측정 0, compile 0, serving lifecycle 0.**

| 쟁점 | 결과 |
|---|---|
| **1. 계층 표기** | [TASK57](TASK57.md) §4는 **표기 오류 3곳**이며 **내용 오류는 없다.** 계층 번호를 바로잡으면 수식·수치·결론이 그대로 성립한다. 저장소의 나머지 문서는 전부 canonical과 일치한다 |
| **2. 회수 한 건 차이** | **닫혔다.** 회수 건수 = `max(0, ALLOC + 1 − 8)`이 **21/21 trial에서 정확히 일치**한다. `+1`은 **decode batch가 덜 찼을 때 요청되는 dummy block**이며, 그 경로는 회수만 하고 **할당하지 않는다**(소스 확인). 로그에서도 evicting trial마다 **회수된 블록이 끝내 재할당되지 않는 회수가 정확히 1건**이다 |
| **3. 용량 개입** | 합산 **9/24 → 24/24** 대조 완료. **추가 bucket 16의 사용은 0 step**이고, **공통 bucket 분포는 동일하지 않다**(b1 891→936, b2 136→121; b4·b8은 동일). 입력 계획은 3반복 전부 plan SHA256·`total_gap_s`·요청 길이 열이 동일하다 |

**과거 판정과 수치는 하나도 바꾸지 않았다.** [TASK14](TASK14.md)의 문턱 7,
[TASK15](TASK15.md)의 12/12, [TASK35](TASK35.md)의 9→24/24는 그대로다. 어긋난
서술은 아래 정정표에만 적었다.

## 날짜

2026-09-09

## 목적

논문 3.2절의 근거를 마감한다. 계층 표기 충돌, 회수 건수의 한 건 차이,
용량 개입 표 — 세 항목을 기존 기록·설치 소스·원로그만으로 닫는다.

## 배경

관련 TASK: [TASK08](TASK08.md)(`kvcache_num_blocks = batch_size`),
[TASK11](TASK11.md)(inner block 128), [TASK14](TASK14.md)·[TASK15](TASK15.md)(생존
문턱과 재현), [TASK18](TASK18.md)(요청별 귀속), [TASK21](TASK21.md)(도착 순서),
[TASK24](TASK24.md)(hit 규칙·사건 순서), [TASK35](TASK35.md)(용량 개입),
[TASK40](TASK40.md)(포화 곡선), [TASK50](TASK50.md)(무처치 반복),
[TASK57](TASK57.md)(표기 충돌의 출처).

## 시작 상태

- 기준 commit `a4e643320bf5645f8e6e6c17730edbaf16fbbf4f` (Advisor가 읽은 public main과 동일)
- 감사 계획 commit `a1826b7` — **모든 재집계보다 앞선다**
- `git status --short`: `?? .idea/`만
- 설치 package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`(patched), `optimum-rbln 0.11.1`

## 수행 내용

1. [AGENTS.md](../../AGENTS.md), [INDEX.md](INDEX.md), [TASK_GUIDE.md](TASK_GUIDE.md),
   [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md)를 읽었다.
2. 감사 질문과 재집계 정의를 **계산 전에** commit했다(`a1826b7`).
3. 설치 소스에서 두 계층의 정의·정책·회수 경로를 읽었다.
4. `[PFX]` 원로그 21개를 **파일 등장 순서 그대로** 재생하는 script를 쓰고, outer block
   ID에 **할당 세대**를 붙였다.
5. [TASK35](TASK35.md) 원자료에서 용량 개입 표를 재집계했다.
6. 두 artifact의 `rbln_config.json`을 읽어 병기했다.

## 변경된 파일

- `docs/research/LAYER_AUDIT_PLAN.md` (계산 전 commit `a1826b7`)
- `experiments/npu/analysis/layer_audit.py` (신규)
- `docs/research/TASK58.md`, `docs/research/PAPER_3_2.md`,
  `docs/research/PROVENANCE_3_2.md` (신규)
- `docs/research/INDEX.md` (갱신)

**기존 TASK 문서를 수정하지 않았다.**

## 실험 또는 검증 방법

측정 없음. 검증은 소스 대조와 원로그 재생이다.

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py \
    --output results/npu/stage2/layer_audit.json
```

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| 신규 측정 | 0 | 0 | `YES` |
| 회수 감사 대상 | m=6·7 최소 | **21 trial 전수**(파일럿 9 + 재현 12) | `YES` |
| 용량 개입 범위 | N=8, BASE→BATCHONLY | 동일 | `YES` |
| 원자료 덮어쓰기 | 금지 | 0건(읽기 전용) | `YES` |

## 결과

### 쟁점 1 — canonical 계층·지표 대응표

설치 소스 기준이다. `BlockConfiguration`
(`vllm_rbln/v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py:32-45`)이
두 크기를 함께 들고 있고 `block_ratio = ob_size // ib_size`다.

| 항목 | **층 1** | **층 2** |
|---|---|---|
| 이름 | vLLM **inner block** | RBLN **outer block** |
| 소스 field | `ib_size` | `ob_size` |
| 크기 | **128 token** | **8,192 token** (`kvcache_block_size` = `max_seq_len`) |
| 개수 (b8 기준) | 512 | **8** (`kvcache_num_blocks` = `batch_size`, [TASK08](TASK08.md)) |
| 회수 정책 | LRU (vLLM free queue) | **FIFO** (`FIFOEvictionPolicy()` 하드코딩, `:258`) |
| 할당 단위 | prefix 관리 단위 | **요청 1건 = outer block 1개** ([TASK14](TASK14.md) `ALLOC` 149/149 `OB_COUNT=1`) |
| 논문의 명칭 | **128-token prefix 관리 단위** | **8,192-token KV slot** |
| `block_ratio` | — | `8192 // 128` = **64** |

**신호 대응표.** 요청별 값은 아래 두 줄에서만 가져온다 —
[TASK18](TASK18.md)이 확정한 귀속이고 [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 항목 3이
금지하는 것이 누적 counter 차분이다.

| 신호 | 계층 | 단위 | 요청별 | 주의 |
|---|---|---|---|---|
| `vllm:prefix_cache_hits_total` | **층 1** | token, 누적 | **✗** | 층 2가 회수된 뒤에도 hit을 보고한다 — 7 ≤ m ≤ 16에서 **100 % 과대**([TASK14](TASK14.md)·[TASK15](TASK15.md) 12/12) |
| `vllm:prompt_tokens_cached_total` | **층 2** | token, 누적 | **✗** | `[PFX]`와 일치([TASK15](TASK15.md) 관측). 집계 지표로만 쓴다 |
| 응답 `usage.prompt_tokens_details.cached_tokens` | **층 2** | token, **요청별** | **✓** | [TASK18](TASK18.md) 게이트 통과. **128의 배수로 양자화**된다 |
| `[PFX] [CACHE-HIT]` / `[CACHE-PARTIAL]` | **층 2** | 사건 + token, **요청 id 포함** | **✓** | 실제 재사용의 1차 신호 |
| `[PFX] [ALLOC]` / `[FREE-REQUEST]` | **층 2** | 사건, 요청 id 포함 | **✓** | `OB_COUNT`·`OB` 목록 |
| `[PFX] [EVICTION]` / `[MAPPING-REMOVE]` | **층 2** | 사건, **요청 id 없음** | **✗** | 회수는 요청에 귀속되지 않는다 |

**두 계층이 한 값에 겹치는 지점을 분명히 해 둔다.** 재사용의 **성립 여부**는 층 2가
all-or-nothing으로 정하고([TASK14](TASK14.md) 발견 6), 성립했을 때 **보고되는 양**은
층 1의 block 크기 128로 내림된다. 그래서 `cached_tokens`의 값이 128의 배수인 것은
층 1의 성질이고, 그 값이 0이 되는 것은 층 2의 성질이다.

#### [TASK57](TASK57.md) 정정표

**과거 문서를 덮어쓰지 않는다.** 아래는 정정 기록이며 [TASK57](TASK57.md) 원문은
그대로 둔다.

| 위치 | 원문 | canonical | 판정 |
|---|---|---|---|
| §4 소제목 (L210) | `층 2 (inner block, 128 token)` | 이 절이 다루는 hit 규칙의 **양**은 층 2가 보고하고, **128은 층 1의 block 크기**다. 층 번호는 맞고 괄호가 두 계층을 뒤섞었다 | **표기 오류** |
| L236 | "…규칙이 틀린 게 아니라 **층 1**에서 축출됐다는 뜻이다" | 축출은 **층 2**(outer, FIFO) | **표기 역전** |
| §4 소제목 (L238) | `층 1 (outer slot)` | outer slot은 **층 2** | **표기 역전** |
| L232 / L38 / L327 / L329 / L351 | "층 2에 남아 재사용 가능한 범위" 등 | canonical과 일치 | **정확** |
| L238 이하 4개 항목 | admission 할당 / FIFO inactive victim / evictable 전환 지연 / 자기 축출 안 함 | 전부 층 2의 사실 | **내용 정확** |

**결론: 표기 오류 3곳, 내용 오류 0건.** 계층 번호를 바로잡으면
[TASK57](TASK57.md) §4의 수식·수치·결론이 그대로 성립한다. 저장소의 다른 문서
([TASK14](TASK14.md), [TASK15](TASK15.md), [CLIFF_REPRO_PREREG.md](CLIFF_REPRO_PREREG.md),
[TASK42](TASK42.md), [INDEX.md](INDEX.md))는 전부 canonical과 일치한다 —
**[TASK57](TASK57.md)이 유일한 이탈이다.**

### 쟁점 2 — 회수 건수의 한 건 차이

#### 관측 1 — 두 산술식의 적합 (21 trial 전수)

| 산술식 | 일치 |
|---|---|
| `max(0, ALLOC − 8)` (요청 할당만 셈) | **5/21** (회수가 0인 trial만) |
| **`max(0, ALLOC + 1 − 8)`** | **21/21** |

`ALLOC`은 그 trial 로그의 `[PFX] [ALLOC]` 줄 수이고 요청 수(`m + 2`)와 같다.
회수 건수는 `[PFX] [EVICTION]` 줄 수다.

| m | trial | ALLOC | EVICT | `ALLOC−8` | `ALLOC+1−8` |
|---|---|---|---|---|---|
| 0 | 파일럿 | 2 | 0 | 0 | 0 |
| 3 | 파일럿 | 5 | 0 | 0 | 0 |
| 5 | 재현 ×3 | 7 | 0 | 0 | 0 |
| 6 | 파일럿 + 재현 ×3 | 8 | **1** | 0 | **1** |
| 7 | 파일럿 + 재현 ×3 | 9 | **2** | 1 | **2** |
| 8 | 파일럿 + 재현 ×3 | 10 | **3** | 2 | **3** |
| 9 | 파일럿 | 11 | 4 | 3 | 4 |
| 16 | 파일럿 | 18 | 11 | 10 | 11 |
| 33 | 파일럿 | 35 | 28 | 27 | 28 |
| 49 | 파일럿 | 51 | 44 | 43 | 44 |

#### 관측 2 — `+1`의 정체는 dummy block이다 (소스)

```python
# optimum_scheduler.py:594-597
elif self.cache_config.enable_prefix_caching:
    num_decode_reqs = len(scheduled_running_reqs)
    if num_decode_reqs > 0 and num_decode_reqs < self.max_num_running_reqs:
        dummy_block = self.kv_cache_manager.get_dummy_block()
```

```python
# optimum_prefix_cache_manager.py:508-529
def get_dummy_block(self) -> int:
    if not self.is_full_block_available():
        return self._config.num_ob
    else:
        num_blocks_to_allocate = 1
        can_allocate = self.can_allocate(num_blocks_to_allocate, 0)   # ← 여기서 회수한다
        ...
        dummy_block = self._allocator.peek_dummy_block()              # ← peek: 할당하지 않는다
        return dummy_block
```

세 가지가 맞물린다.

1. **이 구성은 `is_full_block_available()`이 참이다.**
   `blocks_per_seq = ceil(8192/8192) = 1`, `ideal_total = max_num_seqs × 1 = 8`,
   `num_ob = 8` → `8 >= 8`. 따라서 회수하는 else 분기를 탄다 (`:260-263`).
2. **`can_allocate`는 검사 함수인데 부작용으로 회수한다.**
   `evict_count = required_num_ob − free_count`만큼 `_evict_block`을 부른다 (`:469-484`).
3. **`peek_dummy_block`은 `self._free_blocks[0].block_id`를 돌려줄 뿐 할당하지 않는다**
   (`:108-112`). 그래서 **`[ALLOC]` 줄이 남지 않는다.**

**dummy block이 요청되는 조건이 `0 < num_decode_reqs < max_num_running_reqs`, 곧
decode batch가 덜 찬 상태 — padding이 일어나는 바로 그 조건**이다.

#### 관측 3 — 로그가 소스와 맞는가

| 검사 | 결과 |
|---|---|
| `FREE-REQUEST`의 `PREEMPTION=True` | **0/21** → `free_request`의 회수 분기(`:416`)는 한 번도 타지 않았다. **모든 회수는 `can_allocate`에서 나왔다** |
| 회수된 블록이 **끝내 재할당되지 않는** 회수 건수 | 회수가 있는 **16 trial 전부에서 정확히 1건** (회수 0인 5 trial은 0건) |
| 그 1건의 `FREE_BLOCKS_AFTER` | 전부 **1** — 한 칸을 비우고 멈춘다. 이후 dummy 요청은 `free_count ≥ 1`이라 더 회수하지 않는다 |

**요청 할당을 위한 회수는 회수된 블록이 곧바로 재할당되고, dummy를 위한 회수는
재할당되지 않는다.** 후자가 trial마다 정확히 1건이다.

#### 관측 4 — 대상 KV의 사건 순서 (할당 세대 표기)

대상 KV = 첫 `[ALLOC]`이 잡은 outer block, **그 세대**. `OB<id>#<세대>`.

**m = 6** (파일럿, `OB0#1`)

| # | 사건 | 비고 |
|---|---|---|
| 0 | `ALLOC` | target이 `OB0#1`을 잡는다 |
| 1 | `FREE-REQUEST` | target 완료. `PREEMPTION=False`이므로 mapping은 남고 `is_active=False`가 된다 |
| … | 배경 6건의 `ALLOC`/`FREE-REQUEST` | `OB1`–`OB6` |
| 15 | `ALLOC` (재개 요청) | **`OB7`** — pool 8칸이 정확히 찬다 |
| — | `MAPPING-SEARCH` | `MATCHED_OB=0` |
| 16 | **`CACHE-HIT` `OB=[0]`** | **재사용 성립** |
| 17 | `MAPPING-REMOVE OB=0` | |
| 18 | **`EVICTION OB=0`** `FREE_BLOCKS_AFTER=1` | 재사용 **뒤**의 회수. 이후 `ALLOC` 없음 |

→ **Q2-3 답: 예. m=6의 회수는 재사용 뒤에 일어났다.**

**m = 7** (파일럿, `OB0#1`)

| # | 사건 | 비고 |
|---|---|---|
| 0 | `ALLOC` | target이 `OB0#1` |
| 1 | `FREE-REQUEST` | target 완료 |
| … | 배경 7건 | `OB1`–`OB7` |
| 15 | `MAPPING-REMOVE OB=0` | |
| 16 | **`EVICTION OB=0`** `FREE_BLOCKS_AFTER=1` | **재개 요청의 `ALLOC`보다 앞** |
| — | `ALLOC` (재개 요청) `OB=[0]` | **같은 ID의 새 세대 `OB0#2`** |
| — | `MAPPING-SEARCH` | **`MATCHED_OB=None`** |
| — | `CACHE-PARTIAL REUSED=0/1920` | **재사용 실패** |
| — | `MAPPING-REMOVE OB=1` → `EVICTION OB=1` | dummy용 회수. 이후 `ALLOC` 없음 |

→ **Q2-4 답: 예. m=7에서 대상 KV는 조회 전에 이미 회수됐다.**

**세대 구분이 실제로 필요했다.** m=7에서 재개 요청은 방금 비워진 **같은 ID `OB0`**을
받는다. ID만 보면 대상 KV가 살아 있는 것처럼 보이지만 **`OB0#1`은 회수됐고 `OB0#2`는
다른 KV**다.

#### 판정

| 질문 | 답 |
|---|---|
| Q2-1. `m − 5`는 실행 전체의 회수 건수인가 | **예.** trial 로그 전체의 `[EVICTION]` 줄 수다 |
| Q2-2. `m − 6`이 같은 구간·같은 이벤트를 세는가 | **아니다.** `m − 6`은 **요청 할당만**을 세고 dummy block의 수요를 세지 않는다. 두 식은 같은 구간을 보지만 **수요의 population이 다르다** |
| Q2-3. m=6의 회수는 재사용 뒤인가 | **예** |
| Q2-4. m=7은 조회 전에 없어졌는가 | **예** |
| Q2-5. dummy block·종료 처리·재개 할당의 기존 증거 | **dummy block: 소스에 경로가 있고 조건이 특정된다.** 종료 처리: `PREEMPTION=False`라 회수하지 않는다(0/21). 재개 요청의 할당: m ≥ 7에서 회수를 유발한다(m=7 사건 순서) |

**[TASK14](TASK14.md)·[TASK15](TASK15.md)가 `UNKNOWN`으로 남긴 한 건의 차이는
닫혔다.** 다만 **[TASK14](TASK14.md)가 적었던 hypothesis("resume 요청의 decode가
outer block을 하나 더 요구한 것으로 보이나")는 확인 사실이 아니다** — 실제 경로는
decode의 KV 할당이 아니라 **scheduler가 padding용으로 집는 dummy block**이다.

**남는 한계**: `[PFX] [EVICTION]` 줄에는 **어느 호출자가 회수를 유발했는지 표시가
없다.** 위 귀속은 (i) 선점 경로 배제(0/21), (ii) 회수 블록의 재할당 여부, (iii) 21/21
산술 일치, (iv) 소스의 유일한 무할당 회수 경로 — 네 가지의 **소거법**이다.
직접 라벨을 남기려면 dummy 경로에 로그 한 줄을 넣는 observation-only patch와
재측정이 필요하며 **이번 범위 밖이다**.

### 쟁점 3 — 용량 개입 (N=8, `BASE` → `BATCHONLY`)

#### artifact config

| 항목 | `BASE` | `BATCHONLY` |
|---|---|---|
| `batch_size` | **8** | **16** |
| `kvcache_num_blocks` | **8** | **16** |
| `decoder_batch_sizes` | `[8, 4, 2, 1]` | `[16, 8, 4, 2, 1]` |
| `max_seq_len` | 8,192 | 8,192 |
| `kvcache_block_size` | 8,192 | 8,192 |
| `attn_impl` | `eager` | `eager` |

`kvcache_num_blocks = batch_size`가 두 config 모두에서 확인된다([TASK08](TASK08.md)).

#### 반복별 결과

| 구성 | 반복 | 재도착 요청 | 재사용 성공 | cached token 합 | prefill 계산 token 합 (전체) | (재도착분) | 최대 actual batch | decode step |
|---|---|---|---|---|---|---|---|---|
| `BASE` | b0 | 8 | **3** | 3,840 | 18,193 | 7,816 | 8 | 891 |
| `BASE` | b1 | 8 | **3** | 3,200 | 16,180 | 7,025 | 8 | 682 |
| `BASE` | b2 | 8 | **3** | 2,816 | 16,363 | 7,262 | 8 | 391 |
| `BATCHONLY` | b0 | 8 | **8** | 9,856 | 12,177 | 1,800 | 8 | 921 |
| `BATCHONLY` | b1 | 8 | **8** | 8,448 | 10,932 | 1,777 | 8 | 682 |
| `BATCHONLY` | b2 | 8 | **8** | 8,576 | 10,603 | 1,502 | 8 | 391 |

#### 합산

| 구성 | 재사용 | cached token | prefill 계산 token (전체) | (재도착분) | decode step | 최대 actual batch |
|---|---|---|---|---|---|---|
| `BASE` | **9 / 24** | 9,856 | 50,736 | 22,103 | 1,964 | 8 |
| `BATCHONLY` | **24 / 24** | 26,880 | 33,712 | 5,079 | 1,994 | 8 |

**[TASK35](TASK35.md)의 `9 → 24/24`와 일치한다.** prefill 계산 token은
**50,736 → 33,712 (−33.6 %)**, 재도착분만 보면 **22,103 → 5,079 (−77.0 %)**다.

#### 선택 bucket별 step 수 — 두 사실을 **별개로** 보고한다

| 구성 | b1 | b2 | b4 | b8 | **b16** | 합 |
|---|---|---|---|---|---|---|
| `BASE` | 891 | 136 | 283 | 654 | — | 1,964 |
| `BATCHONLY` | 936 | 121 | 283 | 654 | **0** | 1,994 |

1. **추가 bucket 16의 실제 사용은 0 step이다.** `pair_histogram`에 bucket 16이
   등장하지 않는다. 최대 actual batch가 두 구성 모두 8이므로 9 이상이 될 일이 없었다
   ([TASK35](TASK35.md)이 "`BATCHONLY`는 동시성 9 이상에서만 bucket 16을 쓴다"고
   적은 것과 일관).
2. **그러나 공통 bucket의 사용 분포는 동일하지 않다.** b4(283)·b8(654)은 정확히 같지만
   **b1이 891 → 936, b2가 136 → 121**로 움직였고 총 step도 1,964 → 1,994다.
   **"추가 bucket을 안 썼다"가 "실행 batch 분포가 같다"를 뜻하지 않는다.**

#### 입력 계획 동일성의 근거

| 반복 | plan SHA256 (`BASE` / `BATCHONLY`) | `total_gap_s` | 요청 세그먼트 열 | 생성 길이 열 |
|---|---|---|---|---|
| b0 | `04ad040b40fbe2ef…` / **동일** | 37.012 / 37.012 | **동일** | **동일** |
| b1 | `565f601ae711186a…` / **동일** | 41.947 / 41.947 | **동일** | **동일** |
| b2 | `767564fee3066e83…` / **동일** | 13.358 / 13.358 | **동일** | **동일** |

**[TASK57](TASK57.md) 발견 1의 한계가 여기에도 적용된다** — `plan_summary`는
`text_seed`를 담지 않으므로 이 해시는 **길이·gap의 동일성**을 증명한다.

#### [TASK40](TASK40.md)과 섞지 않는다

[TASK40](TASK40.md)의 N=8 `10/24`는 격자 `(1,4,6,8,10,B)`의 **다른 실험**이고,
그 TASK가 B8→B16을 **"통제되지 않은 인접쌍"** 으로 분류했다. 위 표에 넣지 않았고
"slot만 바꾼 통제 실험"으로 재해석하지 않는다.

## 핵심 발견

1. **`stack` — 회수 건수의 한 건 차이는 padding용 dummy block이다.**
   회수 = `max(0, ALLOC + 1 − 8)`이 21/21로 맞고, `+1`의 수요자는
   `0 < num_decode_reqs < max_num_running_reqs`일 때 scheduler가 집는 dummy block이다.
   그 경로는 `can_allocate`로 회수하고 `peek_dummy_block`으로 **할당 없이** 가져간다.

2. **`class`(형태) + `stack`(값) — padding이 KV slot을 한 칸 먹는다.** decode batch가
   compiled 폭을 채우지 못하면 그 padding을 위한 scratch block이 필요하고, pool이
   꽉 차 있으면 **살아 있던 prefix 하나가 그 대가로 회수된다.** 이 저장소가 따로
   다뤄 온 두 기전(격자 padding, KV 생존)이 **같은 자원에서 만난다.**
   형태를 `class`로 보는 근거: "고정 폭 batch를 padding하려면 scratch가 필요하고
   그 scratch를 같은 pool에서 꺼낸다"는 구조는 특정 상수에 의존하지 않는다.
   값(8칸, `+1`)은 `stack`이다.

3. **`universal` — 계층 이름은 값의 성질을 나눠 갖는다.** 재사용의 **성립**은 층 2가
   all-or-nothing으로 정하고 **보고되는 양**은 층 1의 128로 양자화된다. 한 계층
   이름만으로 `cached_tokens`를 설명할 수 없다.

4. **`universal` — 같은 자원 ID의 재등장을 생존으로 읽으면 안 된다.** m=7에서 재개
   요청이 방금 비워진 `OB0`을 그대로 받는다. 세대 표기가 없으면 "대상 KV가 살아
   있었다"는 정반대 판독이 가능하다.

5. **`stack` — 용량 개입에서 "추가 bucket 미사용"과 "실행 분포 동일"은 다른 주장이다.**
   bucket 16은 0 step인데 b1·b2 분포는 움직였다. 전자만 확인하고 후자를 주장하면
   근거를 넘어선다.

## 해석

- **(해석)** 발견 1·2를 합치면 [TASK14](TASK14.md)의 문턱 7에 대한 서술이 더
  정확해진다. pool 8칸 중 **1칸은 padding scratch의 몫으로 잠재적으로 예약**돼 있으므로,
  실효 용량은 8이 아니라 **"8 − (padding이 일어나는 동안 1)"** 이다. 문턱의 위치를
  예측하는 산술식으로 `max(0, ALLOC + 1 − 8)`이 21/21로 맞지만, **이것은 회수 건수의
  식이지 문턱의 식이 아니다** — 문턱은 "대상 KV의 회수가 조회보다 앞서는가"라는
  순서 문제이고, 그 순서는 [TASK24](TASK24.md) 관측 3의 지연 규칙이 정한다.
- **(해석)** 발견 2가 맞다면 padding이 큰 워크로드는 KV 생존에서도 손해를 본다.
  **이 방향은 이 감사가 계산한 것이 아니라 소스에서 읽은 구조의 함의**이며,
  확인하려면 padding 정도를 바꿔 가며 생존을 재는 새 측정이 필요하다.
- **(해석)** 쟁점 3에서 prefill 계산량이 재도착분 기준 77 % 줄어든 것은 용량 개입의
  이득을 **작업량 단위**로 보여준다. [TASK35](TASK35.md)가 device time으로 보고한
  이득(+8.25 %)과 자릿수가 다른 이유는 prefill이 전체 device time의 일부이기 때문이며,
  두 값은 서로 다른 분모를 갖는다.

## 확인되지 않은 사항

- **회수의 직접 라벨이 로그에 없다** (`UNKNOWN`의 잔여). 위 귀속은 소거법이며,
  `get_dummy_block` 경로에 로그 한 줄을 넣는 observation-only patch와 재측정으로만
  직접 확인된다. **이번 범위 밖이다.**
- **padding 정도와 KV 생존의 정량 관계** (`UNKNOWN`). 발견 2는 구조의 함의이고
  측정이 아니다. dummy block이 실제로 몇 번, 어떤 조건에서 회수를 유발하는지는
  동시성 > 1 조건에서 재야 한다.
- **`m − 5` 식의 적용 범위** — 21 trial 전부 **동시성 1**의 순차 실행이다. 동시
  실행에서는 `num_decode_reqs`가 달라져 dummy 요청 조건이 바뀐다 (`UNKNOWN`).
- **쟁점 3의 b1·b2 분포 이동의 원인** (`UNKNOWN`). 총 step이 30 늘었고 b1이 45 늘고
  b2가 15 줄었다. 재사용 성공이 늘어 prefill이 짧아진 결과로 보이나 **분해하지 않았다.**
- [TASK57](TASK57.md) 발견 1의 한계(plan 해시가 `text_seed`를 담지 않음)가 쟁점 3의
  입력 동일성 근거에도 그대로 적용된다.

## 실패 / 무효 시도

- 첫 판 script의 `MATCHED_OB` 정규식이 숫자만 받아 `MATCHED_OB=None`을 놓쳤다.
  로그 원문을 확인하고 `(\S+)`로 고친 뒤 재실행했다. **정의를 바꾼 것이 아니라
  계기의 결함을 고친 것**이며 [LAYER_AUDIT_PLAN.md](LAYER_AUDIT_PLAN.md)의 정의는
  그대로다.
- 회수 판별을 처음에 "이후 `ALLOC`이 하나라도 있는가"로 두었는데, 그것은 마지막
  회수만 걸러내는 약한 검사였다. **"회수된 그 블록이 이후 재할당되는가"** 를 추가해
  날카롭게 했다. 두 지표를 **둘 다** 보고한다.

## 연구 원칙에 미치는 영향

1. **자원 ID에는 세대를 붙여 읽는다.** 같은 ID의 재등장을 연속 생존으로 읽으면
   정반대 결론이 나온다(발견 4).
2. **"검사"라는 이름의 함수가 상태를 바꿀 수 있다.** `can_allocate`는 이름이 술어인데
   회수를 수행한다. 회계가 안 맞을 때 **부작용이 있는 검사 함수**를 먼저 의심한다.
3. **소거법으로 얻은 귀속은 그렇다고 적는다.** 직접 라벨이 없으면 무엇을 배제해
   무엇이 남았는지 나열하고, 직접 확인에 필요한 것을 함께 적는다.
4. **한 지표에 두 계층이 겹칠 수 있다.** 값의 **성립**과 **크기**가 다른 계층에서
   올 수 있으므로 계층 이름을 값에 통째로 붙이지 않는다(발견 3).

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **dummy block 회수의 직접 라벨** — `get_dummy_block`의 `can_allocate` 호출 앞뒤에
   DEBUG 한 줄을 넣는 observation-only patch. **patch 승인과 선등록, 재측정이 필요**하며
   그래야 소거법이 직접 증거로 바뀐다.
2. **padding × 생존의 정량 측정** — 동시성 > 1에서 decode batch 충전율을 바꿔 가며
   dummy 유발 회수를 센다. 발견 2의 함의를 재는 유일한 길이다.
3. **[TASK57](TASK57.md) 표기 각주** — 원문을 고치지 않고 이 정정표를 가리키는 한 줄을
   그 TASK의 `확인되지 않은 사항`에 추가할지 결정한다. **사용자 판단 사항.**
4. **쟁점 3의 b1·b2 이동 분해** — [TASK56](TASK56.md)의 `h(n)`별 분해를 이 짝에 적용한다.
   새 측정 불필요.

## 재현 정보

- 선등록 commit: **해당 없음** — 신규 측정이 없는 감사다. 대신
  **감사 계획 commit `a1826b7`이 모든 재집계보다 앞선다**
- 기준 commit: `a4e643320bf5645f8e6e6c17730edbaf16fbbf4f`
- 재집계: `env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py --output results/npu/stage2/layer_audit.json`
- 입력 (읽기 전용, 덮어쓰지 않음)
  - `results/npu/stage2/20260819-200800-gap-turnover/server-B{0,3,6,7,8,9,16,33,49}.log`
  - `results/npu/stage2/20260819-204900-cliff-repro/server-B{5,6,7,8}r{0,1,2}.log`
  - `results/npu/stage2/20260823-183505-final-confirm/{util,probe/requests,probe/meta}.{BASE,BATCHONLY}.n8.b{0,1,2}.*`
  - `models/Qwen3-4B-rbln-b8-s8192-d4-mb/rbln_config.json`,
    `models/Qwen3-4B-rbln-b16-s8192-d4-batchonly/rbln_config.json`
- 설치 소스 (읽기 전용)
  - `vllm_rbln/v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py`
    (`:32-45` 계층 크기, `:108-112` `peek_dummy_block`, `:258` FIFO, `:260-263`
    `is_full_block_available`, `:317-339` 블록 수 계산, `:351-378` `_evict_block`,
    `:400-419` `free_request`, `:462-484` `can_allocate`, `:508-529` `get_dummy_block`)
  - `vllm_rbln/v1/core/optimum_scheduler.py:586-597` (dummy block 요청 조건)
  - `vllm_rbln/v1/core/optimum_kv_cache_manager.py:285-321` (admission 경로)
- 산출: `results/npu/stage2/layer_audit.json` (`results/`는 `.gitignore` 대상)
- 예산: **compile 0, serving lifecycle 0, 신규 측정 0, device 접근 0**
