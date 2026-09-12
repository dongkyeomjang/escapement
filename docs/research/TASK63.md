# TASK63 — dummy block 생애 주기의 직접 관측 (탐색)

## 상태

DONE

## 판정

**탐색 실험이며 논문 판정에 사용하지 않는다.** 방향 예측은 등록하지 않았고, Q1–Q5 각각의 "로그 패턴 → 답" 해석 규칙을 측정 전에 commit했다.

선등록 문서: [DUMMY_LIFECYCLE_PLAN.md](DUMMY_LIFECYCLE_PLAN.md) (commit `13a1fe9`, 2026-09-12T12:41:03+09:00). **patch 적용 13:47:10(대상 파일 mtime), 파일럿 시작 13:48:11(선등록 1시간 7분 8초 뒤), 본 측정 시작 13:50:23.** 해석 규칙·분석 script·실행 script·patch 파일을 측정 후에 바꾸지 않았다(`git diff 13a1fe9` 비어 있음, 파일 SHA256은 재현 정보).

선등록 규칙이 가리키는 답 (10 trial = 실험 A 8 + 실험 B 2):

| 질문 | 관측 패턴 | 규칙이 정하는 답 |
|---|---|---|
| **Q1** 언제 처음 확보되는가 | **10/10**: 첫 `DUMMY-BEGIN`이 첫 `ALLOC` 1개 뒤·첫 `[BUCKET]` 앞이고, 그 구간의 다음 `[BUCKET]`이 `n = 1` | **첫 decode step을 준비하는 schedule 호출에서 처음 요청·확보된다** |
| **Q2** 유지인가 매 step 재확보인가 | `0 < n < 8`인 decode step **1,084개 전부**에서 그 schedule 구간의 `DUMMY-BEGIN`이 정확히 1개(예외 0) | **step마다 새로 요청된다** |
| **Q2** "반납" | 회수 없는 dummy 괄호 **1,070개 전부** `FREE_AFTER = FREE_BEFORE`, 반환 OB = `HEAD` 1,070/1,070, dummy 괄호 안 `ALLOC` 0, free 수 장부 **10,112 전이 끊김 0** | **확보는 free 수를 줄이지 않는다 — 할당되지 않으므로 반납 사건도 없다** |
| **Q3** 요청이 slot을 요구할 때 dummy가 가리키던 slot은 회수 대상인가 | 첫 요청 뒤의 `ALLOC` **74/74**가 대기 중 dummy OB를 가져갔고, 대기 중 그 OB의 `EVICT` 0, 대기 중 다른 OB를 받은 `ALLOC` 0 | **회수 없이 요청에 할당된다 — 회수 대상이 아니라 free slot으로 쓰인다** |
| **Q4** 그 뒤 재확보와 회수 유발 | 74 사례 중 `FREE_BEFORE ≥ 1`·괄호 안 회수 없음 **60**, `FREE_BEFORE = 0`·괄호 안 `dummy` 회수 **14**, 재확보 없음 0. 규칙 밖 사례 0 | 사례별로 두 답이 섞인다 — **free가 남아 있으면 회수 없이 재확보(60), free가 0이면 재확보가 다른 slot의 회수를 유발(14)**. trial별 수는 관측 4 |
| **Q5** n = 8에서 반납되는가 | 실험 B **2/2**: `n = 8` decode step 231개(회차당)의 schedule 구간에 `DUMMY-BEGIN` **0개** | **n = 8에서는 dummy가 요청되지 않는다.** Q2 반납 판정이 "반납 사건 없음"이므로 규칙대로 **"요청이 멈춘다 — 되돌리는 사건은 없다"**. 8 → 7로 내려온 첫 구간: `DUMMY-BEGIN FREE_BEFORE=0`, 괄호 안 회수 `OB0#1`(2/2) |

정합 확인 (선등록 C1–C4, 불일치 시 사실만 보고):

| # | 대조 | 결과 |
|---|---|---|
| C1 | trial별 `[OBS] [EVICT]` 수 = `[PFX] [EVICTION]` 수 | **10/10 일치** |
| C2 | 실험 A 회수 수 = `max(0, m − 5)` | **8/8 일치** (0, 0, 1, 1, 2, 2, 3, 3) |
| C3 | 실험 A 회수 수 = 같은 key의 [TASK15](TASK15.md) 원로그 `[PFX] [EVICTION]` 수 | **8/8 일치** |
| C4 | [TASK58](TASK58.md) "회수 있는 trial마다 끝내 재할당되지 않는 회수 정확히 1건" 대 이번 호출 경로별 수 | **일치** — 회수 있는 8 trial 전부 재할당 없는 회수 1건이고 그 호출 경로는 전부 `dummy`(`request_alloc` 0). 회수 없는 2 trial은 0건 |

## 날짜

2026-09-12

## 목적

[TASK58](TASK58.md)은 회수 건수의 `+1`을 padding용 dummy block으로 귀속했으나, `[PFX] [EVICTION]` 줄에 호출자 표시가 없어 **소거법**으로만 닫았다. 관측 전용 patch로 dummy 경로를 괄호로 감싸고 `can_allocate` 진입을 표시해 **회수 하나하나에 호출 경로를 직접 붙이고**, dummy block이 언제 확보되고(Q1) 유지되는지·반납되는지(Q2), 요청이 slot을 요구할 때 어떻게 되는지(Q3·Q4), 동시성 상한에서 어떻게 되는지(Q5)를 로그 사건 순서로 본다(Advisor 지시, 탐색 실험, 사용자 전달 2026-09-11).

## 배경

관련 TASK:

- [TASK58](TASK58.md) — 쟁점 2: 회수 = `max(0, ALLOC + 1 − 8)`(21/21), `+1` = dummy block(소스), 재할당 없는 회수 1건/실행. 한계로 "직접 라벨은 observation-only patch와 재측정이 필요"를 남겼다. 지시문의 "TASK37 계열"은 이 저장소에서 [TASK58](TASK58.md)이다([TASK37](TASK37.md)에는 dummy 서술이 없다)
- [TASK14](TASK14.md) / [TASK15](TASK15.md) — 층 2(outer block 8개, FIFO) 생존 절벽과 그 원로그. 실험 A는 [TASK15](TASK15.md) r0·r1과 **같은 prompt**를 쓴다
- [TASK12](TASK12.md) — `[BUCKET]` 관측 patch. decode step 경계와 `n`을 준다
- [TASK62](TASK62.md) — 파일럿 `C_model`·ITL을 나란히 적는 비교 대상(판정 아님)
- [TASK24](TASK24.md) — 즉시 복귀 세션의 자기 보호(CLAIMS 1.13)의 출처

## 시작 상태

- 선등록 commit `13a1fe94f275b8a024014c864d9fa0c02070715f` (2026-09-12T12:41:03+09:00), `git status --short`: `?? .idea/`만
- Package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`, `rebel-compiler 0.11.1.post1`, `torch 2.11.0+cpu` (run의 `provenance.txt`)
- Host `atom-max8`, KMD 3.2.2, 측정 전 32 device 전부 `0.0B`
- Artifact `models/Qwen3-4B-rbln-b8-s8192-d4-mb`, manifest `b4f5cbf1…651f5f` — 파일럿·본 측정 전 모두 일치
- Substrate: [TASK12](TASK12.md) patch `patched`(`model_base.py` `70942d16…`), **이번 patch `patched`(`optimum_prefix_cache_manager.py` `a51f93ab…`)** — 두 patch 모두 파일럿·본 측정 전후 `patched`
- **작업 연속성**: 선등록과 측정 개시는 이전 Claude 세션이 했다. 사용자가 patch를 적용한 뒤(13:47:10) 그 세션이 run을 만들고(13:47:32) 파일럿(13:48:11)과 본 측정(13:50:23)을 시작했다. 그 세션은 연결이 끊겼지만 실행 shell(`run_dummy_lifecycle.sh … main`)은 계속 돌았고, 이 세션은 측정 중 run 디렉터리를 **읽기만** 한 뒤 종료(14:02:08) 후 분석과 기록을 이어받았다. patch 적용 명령의 출력은 run에 보존되지 않았고 `status`만 남아 있다

## 수행 내용

1. (이전 세션) 소스를 대조해 해석 규칙·관측 patch·실행 script·분석 script를 선등록했다(`13a1fe9`).
2. (사용자, sudo) 관측 patch를 적용했다.
3. 파일럿 1 lifecycle으로 로그 폭주를 확인했다: decode step당 `[OBS]` **4.006줄 ≤ 10** → 선등록대로 patch를 그대로 썼다(상태 전이 기록형으로 바꾸지 않았다).
4. 본 측정: 실험 A 8 trial(`B{5,6,7,8}r{0,1}`), 실험 B 2 trial(`b0`, `b1`). trial마다 fresh server. **10/10 첫 시도에 끝났다**(재실행 0, 무효 0).
5. 선등록 분석 script로 `dummy_lifecycle.json`을 만들었다. 실험 A 원로그의 사건 순서를 [TASK15](TASK15.md) r0·r1 원로그와 나란히 대조했다(선등록 문서가 같은 prompt를 쓰는 목적으로 적은 대조).
6. (사용자, sudo) patch를 revert했다 — 재현 정보 「환경 분리」에 기록.

## 변경된 파일

- `docs/research/TASK63.md` (신규), `docs/research/INDEX.md` (갱신)
- 선등록 파일 7개(`DUMMY_LIFECYCLE_PLAN.md`, `dummy_lifecycle.py`, `run_dummy_lifecycle.sh`, `dummy_lifecycle_b_probe.py`, `DUMMY_LIFECYCLE.md`, `apply_dummy_lifecycle.sh`, `dummy_lifecycle_observe.patch`)는 `13a1fe9` 이후 바뀌지 않았다

기존 TASK 문서, 논문 원고, descriptor, 시뮬레이터는 수정하지 않았다. compile 0회.

## 실험 또는 검증 방법

```bash
RUN=results/npu/stage2/20260912-134732-dummy-lifecycle
bash experiments/npu/stage2/run_dummy_lifecycle.sh "$RUN" pilot
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py pilot --run "$RUN"
bash experiments/npu/stage2/run_dummy_lifecycle.sh "$RUN" main
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py analyze \
    --run "$RUN" --output "$RUN/dummy_lifecycle.json"
```

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| 파일럿 | 요청 1개, `max_tokens=512` → decode 511 step, 폭주 판정 | 511 step, `[OBS]` 2,047줄(4.006줄/step), `flood=false` | `YES` |
| 실험 A | m ∈ {5,6,7,8} × r ∈ {0,1}, 동시성 1, [TASK15](TASK15.md)와 같은 prompt | 8/8 완료, `ALLOC` = m + 2 (7/8/9/10), decode step 49/56/63/70, 전 step `n = 1` | `YES` |
| 실험 B | `n = 8` 구간이 있고 그 앞뒤에 `0 < n < 8` 구간 | 2/2: `n = 8` 231 step, 상한 진입 1회, 8 → 7 이탈 1회. 요청 8건 전부 200·384 token, 도착 간격 0.300–0.301 s | `YES` |
| patch 상태 | 두 patch 모두 `patched`, 측정 전후 동일 | 파일럿·본 측정 전후 4회 모두 `patched`, SHA256 동일 | `YES` |
| artifact | manifest 일치 | 파일럿·본 측정 전 모두 일치 | `YES` |
| 환경 분리 | 측정 후 revert, `pristine`(`81850a8b…`), [TASK12](TASK12.md) patch는 `patched` 유지 | 14:14:06 `pristine` `81850a8b…` / `patched` `70942d16…` | `YES` |

## 결과

Population: trial 1개 = fresh server 1개의 EngineCore 로그 전체. Source: 서버 로그의 `[OBS]`(이번 patch), `[PFX]`(기존 DEBUG), `[BUCKET]`([TASK12](TASK12.md) patch). 순서 = 파일 순서(한 EngineCore process, `async_scheduling=False`). Device scope: `rbln0`–`rbln3`.

### 관측 1 — 파일럿: 로그 폭주 확인과 보고용 비교 (판정 아님)

| 항목 | 값 |
|---|---|
| decode step (`[BUCKET]`) | 511 |
| `[OBS]` 줄 (종류별) | `CAN-ALLOCATE` 1,023, `DUMMY-BEGIN` 511, `DUMMY-END` 511, `ALLOC` 1, `FREE` 1 → 2,047 |
| decode step당 `[OBS]` | **4.006** (문턱 10) |
| 서버 로그 | 601,132 B, 3,258줄 |

step당 `CAN-ALLOCATE`가 2개인 것은 원로그에서 확인된다 — running 요청의 slot 검사(`NUM_NEW=0 … REQUIRED_OB=0`)와 dummy 괄호 안의 검사(`NUM_NEW=1 COMPUTED=0 REQUIRED_OB=1`)다.

선등록대로 [TASK62](TASK62.md) A1 bucket 1과 나란히 적는다(판정 아님, 조건이 다르다 — 이 파일럿은 `[OBS]` DEBUG 줄이 step당 4개 더 나오고 `--enable-prefix-caching`을 명시했으며 다른 날이다):

| 항목 | 이번 파일럿 | [TASK62](TASK62.md) A1 b1 (5회차) |
|---|---|---|
| `C_model` p50 (ms) | 9.79 | 중앙값 9.51 (범위 9.49–9.60) |
| `C_sampler` p50 (ms) | 0.59 | 0.36 (관측 6) |
| probe `client_median_itl_ms` / `server_mean_itl_ms` | 12.175 / 11.832 | 관측 6 채널 C 10.356 / 채널 D 10.358 |

### 관측 2 — trial별 요약

| trial | decode step | `n` 분포 | `ALLOC` (`OBS`/`PFX`) | 회수 (`OBS`/`PFX`) | 호출 경로 | 재할당 없는 회수 | 회수된 `OB#세대` |
|---|---|---|---|---|---|---|---|
| A.B5r0 / r1 | 49 / 49 | 전부 1 | 7/7 | 0/0 | — | 0 | — |
| A.B6r0 / r1 | 56 / 56 | 전부 1 | 8/8 | 1/1 | `dummy` 1 | 1 (`dummy`) | `OB0#1` |
| A.B7r0 / r1 | 63 / 63 | 전부 1 | 9/9 | 2/2 | `dummy` 2 | 1 (`dummy`) | `OB0#1`, `OB1#1` |
| A.B8r0 / r1 | 70 / 70 | 전부 1 | 10/10 | 3/3 | `dummy` 3 | 1 (`dummy`) | `OB0#1`, `OB1#1`, `OB2#1` |
| B.b0 | 535 | 1:43, 2:43, 3:43, 4:46, 5:43, 6:43, 7:43, **8:231** | 8/8 | 1/1 | `dummy` 1 | 1 (`dummy`) | `OB0#1` |
| B.b1 | 535 | 1:43, 2:43, 3:44, 4:44, 5:44, 6:43, 7:43, **8:231** | 8/8 | 1/1 | `dummy` 1 | 1 (`dummy`) | `OB0#1` |

r0과 r1은 표의 모든 칸이 같다. **회수 14건의 호출 경로는 전부 `dummy`이고 `request_alloc`·`preemption`·`unlabeled`는 0이다.** `FREE`의 `PREEMPTION=True`는 0건이다.

### 관측 3 — Q2: dummy 괄호 집계

| trial (r0, r1 같음) | `0<n<8` step | step당 `DUMMY-BEGIN` | 회수 없는 괄호 (free 불변 / 반환 OB = `HEAD`) | 회수 있는 괄호 (`FREE_BEFORE=0` → `FREE_AFTER=1`) | 장부 전이 / 끊김 | 연속 `DUMMY-END` OB 같음 |
|---|---|---|---|---|---|---|
| A.B5 | 49 | 1 × 49 | 49 (49/49) | 0 | 216 / 0 | 42/48 |
| A.B6 | 56 | 1 × 56 | 55 (55/55) | 1 (1/1) | 248 / 0 | 48/55 |
| A.B7 | 63 | 1 × 63 | 61 (61/61) | 2 (2/2) | 280 / 0 | 54/62 |
| A.B8 | 70 | 1 × 70 | 67 (67/67) | 3 (3/3) | 312 / 0 | 60/69 |
| B.b0, B.b1 | 304 | 1 × 304 | 303 (303/303) | 1 (1/1) | 4,000 / 0 | 296/303 |
| **합 (10 trial)** | **1,084** | **예외 0** | **1,070 (1,070/1,070)** | **14 (14/14)** | **10,112 / 0** | — |

decode step 밖(마지막 `[BUCKET]` 뒤)의 `DUMMY-BEGIN`은 0이다. 연속 `DUMMY-END`의 OB가 바뀐 횟수(A.B5 6, A.B6 7, A.B7 8, A.B8 9, B 7)는 관측 4의 "dummy OB를 요청이 가져간" 횟수와 같다. 파일럿(분석 대상 밖)도 `DUMMY-BEGIN` 511 = decode step 511이다.

### 관측 4 — Q3·Q4: dummy가 가리키던 slot과 그 뒤

| trial (r0, r1 같음) | 요청 `ALLOC`이 대기 중 dummy OB를 가져감 | 대기 중 그 OB 회수 | 다음 `DUMMY-BEGIN`: `FREE_BEFORE ≥ 1`·회수 없음 | 다음 `DUMMY-BEGIN`: `FREE_BEFORE = 0`·괄호 안 회수 |
|---|---|---|---|---|
| A.B5 | 6/6 | 0 | 6 | 0 |
| A.B6 | 7/7 | 0 | 6 | 1 (`OB0#1`) |
| A.B7 | 8/8 | 0 | 6 | 2 (`OB0#1`, `OB1#1`) |
| A.B8 | 9/9 | 0 | 6 | 3 (`OB0#1`, `OB1#1`, `OB2#1`) |
| B.b0, B.b1 | 7/7 | 0 | 6 (`FREE_BEFORE` 6, 5, 4, 3, 2, 1) | 1 (`OB0#1`, 8 → 7 이탈 구간) |

첫 요청의 `ALLOC`은 dummy 요청보다 먼저라 대기 중 dummy OB가 없다. 그 뒤의 `ALLOC`은 74/74가 직전 `DUMMY-END`의 OB를 받았다.

### 관측 5 — 원로그 발췌

**A.B7r0 (m = 7)**, `server-A.B7r0.log` L884–L947, 줄머리(시각·파일) 생략:

```
[OBS] [CAN-ALLOCATE] NUM_NEW=16 COMPUTED=0 REQUIRED_OB=1 FREE=1
[PFX] [ALLOC] REQUEST=cmpl-bda09ba3… | OB_COUNT=1 OB=[7]            ← 7번째 배경 요청
[OBS] [ALLOC] … OB=[7] FREE_AFTER=0
[OBS] [CAN-ALLOCATE] NUM_NEW=0 COMPUTED=2000 REQUIRED_OB=0 FREE=0
[OBS] [DUMMY-BEGIN] FREE_BEFORE=0 HEAD=-1
[OBS] [CAN-ALLOCATE] NUM_NEW=1 COMPUTED=0 REQUIRED_OB=1 FREE=0
[PFX] [MAPPING-REMOVE] OB=0 …
[PFX] [EVICTION] OB=0 | IB_COUNT=16 | FREE_BLOCKS_AFTER=1 | INACTIVE_MAPPINGS_AFTER=[1, 2, 3, 4, 5, 6]
[OBS] [EVICT] OB=0 FREE_AFTER=1                                       ← 대상 KV OB0#1, dummy 괄호 안
[OBS] [DUMMY-END] OB=0 FREE_AFTER=1
[BUCKET] request_nums=1 padded_batch_size=1                           ← 7번째 배경 요청의 첫 decode step
…
[OBS] [FREE] REQUEST=cmpl-bda09ba3… PREEMPTION=False OB=[7] FREE=1
[OBS] [CAN-ALLOCATE] NUM_NEW=16 COMPUTED=0 REQUIRED_OB=1 FREE=1
[PFX] [ALLOC] REQUEST=cmpl-9caf5eea… | OB_COUNT=1 OB=[0]              ← 재개 요청, OB0#2
[OBS] [ALLOC] … OB=[0] FREE_AFTER=0
[PFX] [MAPPING-SEARCH] … | MATCHED_OB=None
[PFX] [CACHE-PARTIAL] … REUSED=0/1920 tokens (0.0%)
[OBS] [CAN-ALLOCATE] NUM_NEW=0 COMPUTED=2008 REQUIRED_OB=0 FREE=0
[OBS] [DUMMY-BEGIN] FREE_BEFORE=0 HEAD=-1
[OBS] [CAN-ALLOCATE] NUM_NEW=1 COMPUTED=0 REQUIRED_OB=1 FREE=0
[PFX] [EVICTION] OB=1 | … | FREE_BLOCKS_AFTER=1
[OBS] [EVICT] OB=1 FREE_AFTER=1                                       ← OB1#1, 이후 재할당 없음
[OBS] [DUMMY-END] OB=1 FREE_AFTER=1
```

**B.b0 상한 진입** (L1859–L1884): `DUMMY-END OB=7 FREE_AFTER=1` → `[BUCKET] request_nums=7` → `DUMMY-BEGIN FREE_BEFORE=1` → `DUMMY-END OB=7` → `[BUCKET] request_nums=7` → 8번째 요청 `[PFX] [ALLOC] … OB=[7]` → `[BUCKET] request_nums=8`. 이후 `n = 8`인 231 step 동안 `DUMMY-BEGIN`이 없다.

**B.b0 상한 이탈** (L3954–L3972): `[BUCKET] request_nums=8` → 첫 요청 완료 `[OBS] [FREE] … PREEMPTION=False` → `DUMMY-BEGIN FREE_BEFORE=0` → `[PFX] [EVICTION] OB=0 | IB_COUNT=4 | FREE_BLOCKS_AFTER=1` → `[OBS] [EVICT] OB=0 FREE_AFTER=1` → `DUMMY-END OB=0 FREE_AFTER=1` → `[BUCKET] request_nums=7`.

### 관측 6 — 회수의 위치와 [TASK15](TASK15.md) 원로그 대조

각 회수에 대해 (직전까지의 `[PFX] [ALLOC]` 수, 회수 직후에 오는 `[BUCKET]`/`[PFX] [ALLOC]`, 재개 요청의 조회와의 선후, 이후 재할당 여부)를 적었다. 재개 요청은 m + 2번째 `ALLOC`이다.

| key | 이번 run | [TASK15](TASK15.md) 같은 key (r0·r1) |
|---|---|---|
| B5 | 회수 없음 | 회수 없음 |
| B6 | `OB0`: `ALLOC` 8개 뒤(재개), 직후 `[BUCKET]`, 재개 `CACHE-HIT` 뒤, 재할당 없음 | 같음 |
| B7 | `OB0`: `ALLOC` 8개 뒤(7번째 배경), 직후 `[BUCKET]`, 재개 조회 전, **재할당됨**(재개 요청) / `OB1`: `ALLOC` 9개 뒤(재개), 직후 `[BUCKET]`, 재개 `CACHE-PARTIAL` 뒤, 재할당 없음 | 같음 |
| B8 | `OB0`: 8개 뒤, 직후 `[BUCKET]`, 조회 전, 재할당됨 / `OB1`: 9개 뒤, 직후 `[BUCKET]`, 조회 전, 재할당됨 / `OB2`: 10개 뒤(재개), 직후 `[BUCKET]`, `CACHE-PARTIAL` 뒤, 재할당 없음 | 같음 |

**12/12 회수에서 위치·직후 사건·조회와의 선후·재할당 여부가 [TASK15](TASK15.md) 원로그와 같다.** `ALLOC`·`[BUCKET]` 총수도 8쌍 모두 같다. [TASK15](TASK15.md) 로그에는 `[OBS]` 줄이 없으므로 호출 경로 라벨은 없다.

## 핵심 발견

1. **`stack`** — **dummy block은 `0 < n < 8`인 decode step마다 매번 새로 요청되고(1,084/1,084), `n = 8`에서는 요청되지 않는다(462 step에서 0).** 처음 요청되는 곳은 첫 decode step을 준비하는 schedule 호출이다(10/10). 요청 조건과 상한 8은 이 구성(`batch_size` 8, full-block)의 것이다.
2. **`stack`** — **"확보"는 실행에서 free list 머리의 조회로 나타나고 할당도 반납도 없다.** 회수 없는 괄호 1,070개 전부 free 수가 변하지 않고 반환 OB가 `HEAD`와 같으며, free 수 장부가 10,112 전이에서 끊기지 않는다. 상한 도달 시에는 요청이 멈출 뿐 되돌리는 사건이 없다.
3. **`stack`** — **dummy가 가리키던 slot은 다음 요청의 할당이 회수 없이 그대로 가져간다(74/74).** 그 뒤 첫 dummy 요청은 free가 남아 있으면 회수 없이 머리를 가리키고(60), **free가 0이면 inactive block 하나를 회수해 free를 1로 만든다(14/14, 전부 `FREE_AFTER=1`)**. 회수된 block은 할당 순서상 가장 이른 inactive block이었다(`OB0#1` → `OB1#1` → `OB2#1`).
4. **`stack`** — **이번 10 trial의 회수 14건은 전부 dummy 경로이고, 요청 admission 경로와 선점 경로의 회수는 0건이다.** 끝내 재할당되는 회수(A.B7·A.B8의 6건)도 dummy 경로다 — 그 slot이 `DUMMY-END`의 OB로 반환된 뒤 다음 요청 `ALLOC`이 그것을 가져갔다(관측 4·5). **[TASK58](TASK58.md)의 회수 건수 산술(C2)과 "재할당 없는 회수 1건 = dummy"(C4)는 직접 라벨과 맞는다. 그러나 [TASK58](TASK58.md) 관측 3의 "요청 할당을 위한 회수는 회수된 블록이 곧바로 재할당되고"와 판정 Q2-5의 "재개 요청의 할당: m ≥ 7에서 회수를 유발한다"는 이번 라벨과 맞지 않는다** — 재할당되는 회수도 요청 할당 경로가 아니라 dummy 경로에서 일어났다. [TASK58](TASK58.md) 원문은 수정하지 않는다.
5. **`stack`** — **m ≥ 7에서 대상 KV(`OB0#1`)는 재개 요청이 조회하기 전, 마지막 배경 요청의 첫 decode step을 준비하는 dummy 괄호 안에서 회수됐다.** 재개 요청은 같은 ID의 새 세대(`OB0#2`)를 받아 `MATCHED_OB=None`이 된다. m = 6에서는 재개 요청의 조회·재사용(`CACHE-HIT`) 뒤, 재개 요청의 첫 decode step dummy 괄호에서 회수됐다. 문턱 m과 slot 수 8은 이 인스턴스의 값이다.
6. **`universal`** — **개수 산술과 소거법은 개수를 맞혀도 호출 경로 귀속을 보증하지 않는다.** [TASK58](TASK58.md)의 21/21 산술 일치와 "재할당 없는 회수 1건" 서명은 직접 라벨과 전부 맞았지만, 나머지 회수를 요청 할당 경로로 본 귀속은 맞지 않았다. 호출 경로를 묻는 질문에는 호출 경로 표지가 필요하다. 방법론의 문제이므로 substrate와 무관하다.

## 해석

지시에 따라 스택 설계의 좋고 나쁨은 평가하지 않는다. 아래는 관찰에서 파생한 해석이며 hypothesis를 포함한다.

- **순차 부하에서 admission이 회수를 하지 않은 이유(파생)**: dummy 경로가 `0 < n < 8`인 동안 free를 1 이상으로 되돌려 두므로, 다음 요청이 도착해 `can_allocate`를 부를 때 free가 이미 요구량(`REQUIRED_OB=1`) 이상이었다(관측 5의 두 `ALLOC` 직전 `FREE=1`). 이번 격자에서는 admission이 회수할 기회가 생기지 않았다. admission 경로의 회수가 어떤 조건에서 나타나는지는 관측하지 못했다(`UNKNOWN`).
- **[TASK15](TASK15.md) 회수의 경로(hypothesis)**: [TASK15](TASK15.md) r0·r1 원로그의 회수 12건은 이번 run과 위치·직후 사건이 전부 같다(관측 6). 소스상 admission 경로의 회수라면 `can_allocate` 뒤 곧바로 그 요청의 `[PFX] [ALLOC]`이 와야 하는데, 12건 모두 직후가 `[BUCKET]`이다. 따라서 [TASK15](TASK15.md) r0·r1의 회수도 dummy 경로였을 것으로 본다. 라벨 없는 로그에 대한 추론이다.
- **논문 서술과의 관계(보고만, 수정 없음)**:
  - [PAPER_3_2.md](PAPER_3_2.md) 표 3.2-B 주석의 "+1은 padding scratch" 귀속은 직접 라벨과 맞는다. "요청 할당만 센 예측" 열은 수요의 **개수**이지 경로가 아니므로 이번 관측과 충돌하지 않는다. [PROVENANCE_3_2.md](PROVENANCE_3_2.md) 73행의 "직접 라벨 필요"는 이번 TASK가 채울 수 있는 항목이다.
  - [paper/CLAIMS.md](../../paper/CLAIMS.md) 1.13과 원고 §3(`paper/draft/03_mechanisms.md` 17행)은 즉시 복귀 세션의 자기 보호 기전을 "a completed block becomes evictable only after **the next admission has already chosen its victim**"으로 적는다. 이번 10 trial에서 victim 선택(회수)은 14/14 dummy 경로에서 일어났고 admission 경로에서는 0건이었다. **이번 격자에는 즉시 복귀 조건이 없으므로 1.13의 결론("즉시 돌아오는 세션은 자기 캐시를 자기가 축출하지 않는다")은 판정하지 않는다.** 기전 문장의 "admission" 표현을 재검토할지는 사용자 판단이다.

## 확인되지 않은 사항

- **관측 patch의 시간 관찰자 효과** (`UNKNOWN`). 파일럿 `C_model` 9.79 ms가 [TASK62](TASK62.md) A1 b1 범위(9.49–9.60) 밖이고 ITL도 1.5–1.8 ms 높다. 조건이 여럿 다르고(`[OBS]` 줄, `--enable-prefix-caching` 명시, 날짜) 관찰자 효과 시험을 등록하지 않았으므로 원인을 가르지 않는다. 이번 해석 규칙은 사건 **순서**만 쓴다.
- **admission 경로 회수의 발생 조건과 로그 모양** (`UNKNOWN`). 10 trial에서 0건이었다.
- **즉시 복귀 조건에서 victim 선택이 어느 경로에서 일어나는가** (`UNKNOWN`). CLAIMS 1.13 관련. 실험 A는 재개 전에 배경 요청 m개가 끼고, 실험 B는 prefix 재사용이 없다.
- **동시성과 prefix 재사용이 함께 있는 부하(agentic, gap)에서 dummy 회수가 대상 KV를 고르는 빈도** (`UNKNOWN`).
- **[TASK15](TASK15.md) r2와 [TASK14](TASK14.md) 파일럿 로그 9개의 회수 위치** — 이번에 대조하지 않았다([TASK58](TASK58.md) 21 trial 중 12개만 대조).
- **다른 구성(`batch_size` 16, 비-full-block)** — `DUMMY-FIXED` 분기는 이번 구성에서 한 번도 타지 않았다(0줄).
- **patch 적용 명령의 출력** — run에 보존되지 않았다. 적용 사실은 `status` 기록 4회(`patched`, `a51f93ab…`)와 대상 파일 mtime(13:47:10, root 소유)으로만 남는다.

## 실패 / 무효 시도

- 무효·재실행 trial은 없다(10/10 첫 시도).
- **측정 후 점검 1건에서 process 검사가 자기 명령과 일치했다.** `ps … | grep -E '[v]llm serve' || echo "no vllm server"`에서 fallback 문구의 `vllm server`가 패턴 `vllm serve`와 일치해 점검 shell 자신이 두 줄 잡혔다. port 8000 비어 있음과 device 32/32 `0.0B`로 서버가 없음을 따로 확인했다. 측정에는 영향이 없다([TASK62](TASK62.md) 원칙 3과 같은 계열).

## 연구 원칙에 미치는 영향

1. **소거법 귀속은 "개수 서명"과 "경로 귀속"을 분리해 적는다.** 개수가 맞아도 경로가 틀릴 수 있다(발견 6). 경로를 주장하려면 경로 표지가 필요하다.
2. **탐색용 관측 patch는 측정 직후 revert하고 `pristine`을 기록한다**(환경 분리). 논문용 측정 script는 이 patch의 상태를 검사하지 않기 때문이다.
3. **process 점검의 fallback 문구에 검사 패턴을 넣지 않는다.**

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **CLAIMS 1.13·원고 §3의 기전 문장 재검토 여부** — 사용자 결정. 재검토하려면 즉시 복귀 조건의 직접 라벨 관측(이 patch 재적용 + 탐색 1회)이 필요하다.
2. **[TASK58](TASK58.md) 귀속 정정의 반영 방식** — [PROVENANCE_3_2.md](PROVENANCE_3_2.md) 정정 이력에 행을 추가하고 73행을 해소할지. 이번 TASK는 기존 문서를 수정하지 않았다.
3. **[TASK15](TASK15.md) r2·[TASK14](TASK14.md) 파일럿 로그의 회수 위치 대조** — 측정 불필요.
4. **동시성·재사용이 함께 있는 부하에서의 dummy 회수 관측** — 새 측정, patch 재적용 필요.

## 재현 정보

- 선등록 commit: **`13a1fe9`**, 2026-09-12T12:41:03+09:00. **patch 적용 13:47:10(대상 파일 mtime), 파일럿 13:48:11–13:49:23(선등록 1시간 7분 8초 뒤), 본 측정 13:50:23–14:02:08.** 해석 규칙은 측정 후 바뀌지 않았다
- Raw artifact: `results/npu/stage2/20260912-134732-dummy-lifecycle/` (gitignored)
  - `provenance.txt`, `git-head.txt`, `manifest-{pilot,main}.txt`, `patch-{bucket,dummy}-{pilot,main}-{before,after}.txt`, `rbln-smi-{pilot,main}-{before,after}.txt`, `{pilot,main}-{start,end}.txt`
  - trial별 `server-<TAG>.log`(합계 4,208,668 B), `probe-<TAG>.log`, `<TAG>-launch.txt`·`-server-start.txt`·`-server-stop.txt`, `smi/<TAG>.txt`, `done.<TAG>`. `failed/` 비어 있음, `reruns.txt` 없음
  - `probe/decode_cost.level1.json`(파일럿), `probe/dummy_b.{b0,b1}.json`, 실험 A probe 출력
  - 산출: `pilot.json` (SHA256 `1efb08f351ede47068c006679f72714e6506fb4184fe0eade688c3f097dc98a7`), `dummy_lifecycle.json` (SHA256 `a938550648e876a19e0a66f7abbd96f042d74cbee0b8991c4d76a817f8156955`), `analyze.out`
- trial 기동 시각: pilot 13:48:11, A.B5r0 13:50:23, A.B5r1 13:51:31, A.B6r0 13:52:40, A.B6r1 13:53:49, A.B7r0 13:54:58, A.B7r1 13:56:08, A.B8r0 13:57:18, A.B8r1 13:58:28, B.b0 13:59:39, B.b1 14:00:54. serving lifecycle 11회(파일럿 1 + 본 측정 10)
- 대조 원로그: [TASK15](TASK15.md) `results/npu/stage2/20260819-204900-cliff-repro/server-B{5,6,7,8}r{0,1}.log`
- 파일 SHA256: `dummy_lifecycle_observe.patch` `645dc1a8067c2a20ad74e979be5bd44c7b43fc39f893c744df45e9831655b751`, `dummy_lifecycle.py` `eb6d541a56bf05204360ef8074b1de0eda2125e4496d2e574f9e00b0721c3e5b`, `run_dummy_lifecycle.sh` `bf51f65629f8c415619a4c838ab3bb98f3a5583373f87431d11f9ce6baa9e74a`, `dummy_lifecycle_b_probe.py` `79f2db8ea9bab771fa8b6322c729e102d65d8f7ca89b6a1884f62ee8f92c37c9`
- 대상 파일 SHA256: pristine `81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b`, patched `a51f93abab815107dd762da5f9d43cd3314eb12e163c95a0b32779c11ee60856`
- 측정 후 device 상태: 32 ID 전부 `0.0B / 15.7GiB`, port 8000 비어 있음, 서버 없음
- **환경 분리**: 사용자가 `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert`를 실행했다(출력 `reverted. sha256=81850a8b…`, 대상 파일 mtime 2026-09-12T14:13:53+09:00). 14:14:06의 `status`: `apply_dummy_lifecycle.sh` → **`pristine`** `81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b`, `apply.sh` → **`patched`** `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`([TASK12](TASK12.md) patch만 적용된 상태로 복귀). 출력은 run의 `patch-{dummy,bucket}-after-revert.txt`에 남겼다. 관측 patch가 적용돼 있던 구간은 13:47:10–14:13:53이며, 그 구간에 `results/` 아래에서 이 run 밖에 쓰인 파일은 0개다(`find -newermt`로 확인). 이 run 외의 측정 산출물은 없다
