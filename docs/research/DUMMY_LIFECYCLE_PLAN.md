# 계산 전 정의 — dummy block의 생애 주기 관측 (탐색 실험)

## 문서 성격

**탐색적 관측 실험**이다. 결과는 TASK 기록과 리뷰 대응 자료로만 쓰고 **논문 판정에 사용하지 않는다.** 방향 예측은 등록하지 않는다. 대신 [CLAUDE.md](../../CLAUDE.md) 실행 원칙 16에 따라 **Q1–Q5 각각에 대해 "어떤 로그 패턴이 어떤 답을 뜻하는가"의 해석 규칙**을 측정 전에 commit한다. 측정 후 규칙을 바꾸지 않는다.

## 승인 범위 (Advisor 지시문, 사용자 전달, 2026-09-11)

- 승인: 관측 전용 patch 추가(추가만, 수정·삭제 없음, 제어 흐름 불관여, 적용 후 SHA256 기록), 순차·저동시성(N ≤ 8) 측정, 서버 재기동, 분석 script, TASK 문서
- 금지: compile, descriptor·시뮬레이터 변경, 기존 TASK 문서 수정, 제어 흐름에 관여하는 코드 변경. **이 patch를 적용한 상태로 논문용 측정을 재실행하지 않는다**(환경 분리)
- patch 적용·복구는 root 권한이 필요하고 이 host의 sudo는 비밀번호를 요구하므로 **사용자가 별도 터미널에서 실행한다**

## 배경과 참조 정정

지시문의 "TASK37 계열이 확인한 dummy block의 효과(pool 순 소비 1칸, 회수 건수 `max(0, m−5)`, 재할당 없는 회수 1건/실행)"는 이 저장소에서 **[TASK58](TASK58.md)** 쟁점 2(과 그 원자료인 [TASK14](TASK14.md)·[TASK15](TASK15.md))에 해당한다. [TASK37](TASK37.md)에는 dummy에 관한 서술이 없다(`grep -i dummy` 0건). 이 문서와 TASK는 [TASK58](TASK58.md)의 소스 대조를 출발점으로 한다.

[TASK58](TASK58.md)의 한계: `[PFX] [EVICTION]` 줄에 호출자 표시가 없어 dummy 경로의 회수는 **소거법**으로만 귀속됐다.

## 작업 1 — 소스 확인 (측정 전, 설치 소스 읽기 전용)

| 역할 | 위치 (`vllm_rbln 0.11.1`) | 내용 |
|---|---|---|
| **요청 조건** | `v1/core/optimum_scheduler.py:594-597` | `enable_prefix_caching`이면 `num_decode_reqs = len(scheduled_running_reqs)`, **`0 < num_decode_reqs < max_num_running_reqs`일 때** `kv_cache_manager.get_dummy_block()` |
| encoder-decoder 분기 | `optimum_scheduler.py:587-593`, `optimum_block_pool.py:88-95` | Whisper 전용 고정 dummy. 이 모델(decoder-only)에서는 `block_pool.dummy_block is None` |
| 위임 | `v1/core/optimum_kv_cache_manager.py:347-356` | block pool dummy가 없으면 `prefix_cache_manager.get_dummy_block()` |
| **확보** | `v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py:508-528` | full-block 구성이면 `can_allocate(1, 0)` → `_check_free_blocks(1)` → **`peek_dummy_block()`** |
| 회수 | 같은 파일 `:460-484` `can_allocate` | free가 부족하면 FIFO로 inactive block을 골라 `_evict_block` — **검사 함수의 부작용으로 회수** |
| **"확보"의 실체** | 같은 파일 `:108-112` `peek_dummy_block` | `self._free_blocks[0].block_id`를 **돌려줄 뿐 할당하지 않는다** — free list에서 빼지 않는다 |
| 사용 | `model_executor/models/optimum/model_base.py:312-354`, `decoder_only.py:50-56` | decode padding 행의 block table을 `dummy_block`으로 채운다 |
| **반납** | — | `dummy_block`을 되돌리는 함수는 **소스 어디에도 없다**(`grep -rn dummy_block` 전수: 위 위치들과 whisper 경로뿐) |
| `can_allocate` 호출자 | `optimum_prefix_cache_manager.py:520`, `optimum_kv_cache_manager.py:285` | **둘뿐** — dummy 경로와 요청 admission |
| free list 순서 | 같은 파일 `:78-94` | `allocate`는 `popleft`(머리), `deallocate`(회수)는 `append`(꼬리). **dummy가 peek하는 머리 = 다음 요청 할당이 가져갈 블록** |
| prefill 배타 | `optimum_scheduler.py:335-337`, `:465` | 한 schedule 호출은 prefill 1건만 받고, `req_index == 0`(prefill 없음)일 때만 running 요청을 decode로 싣는다 → dummy 요청은 decode step에서만 가능 |

소스 수준에서 "확보"는 할당이 아니라 **free list 머리의 조회**다. 관측은 이 읽기가 실행에서 어떻게 나타나는지를 본다. **소스 읽기는 관측 결과가 아니며, 아래 해석 규칙은 로그 패턴만으로 답을 정한다.**

## 작업 2 — 관측 patch

[patches/vllm_rbln-0.11.1/DUMMY_LIFECYCLE.md](../../patches/vllm_rbln-0.11.1/DUMMY_LIFECYCLE.md)가 7개 정책 항목을 채운다. 요약:

- 대상: `optimum_prefix_cache_manager.py` 한 파일. **추가 42줄, 수정·삭제 0**, 7 hunk. SHA256 `81850a8b…d296b` → `a51f93ab…60856`. 사본에서 apply → revert 왕복 검증
- 새 줄: `[OBS] [ALLOC]`·`[EVICT]`·`[FREE]`·`[CAN-ALLOCATE]`·`[DUMMY-BEGIN]`·`[DUMMY-END]`·`[DUMMY-FIXED]`, 각각 `t=`(wall time, 초, 소수 6자리)와 OB·free 수
- **할당 세대**는 분석이 OB별 `[OBS] [ALLOC]` 순서로 붙인다. **호출 경로**는 dummy 괄호와 `CAN-ALLOCATE` 표지로 붙인다
- [TASK12](TASK12.md)의 `[BUCKET]` patch(`model_base.py`)는 적용 상태 그대로 둔다 — decode step마다 `request_nums`를 준다

### 로그 폭주 확인 (파일럿, 측정 전 고정)

`run_dummy_lifecycle.sh <RUN> pilot`: 요청 1개, `max_tokens=512`(decode 511 step)를 fresh server로 1회. `dummy_lifecycle.py pilot`이 **decode step당 `[OBS]` 줄 수**를 센다.

- **decode step당 10줄 이하면 patch를 그대로 쓴다**
- 10줄을 넘으면 **상태 전이 기록형**으로 바꾼다: 직전 dummy 호출과 `(FREE_BEFORE, HEAD, 반환 OB)`가 같고 회수가 없으면 줄을 남기지 않고, 다음 전이 줄에 `REPEAT=<생략 횟수>`를 싣는다. 이 경우 patch를 새로 만들어 SHA256을 다시 기록하고 조정 내용을 TASK에 적는다. 아래 규칙은 `REPEAT`를 호출 횟수에 더해 똑같이 적용한다
- 파일럿의 `C_model`·ITL은 [TASK62](TASK62.md) A1 bucket 1과 나란히 **보고만** 한다(판정 아님)

## 실험 설계

공통: artifact `models/Qwen3-4B-rbln-b8-s8192-d4-mb`(manifest `b4f5cbf1…651f5f`, 측정 전 대조), trial마다 fresh server, `vllm serve <artifact> --host 127.0.0.1 --port 8000 --enable-prefix-caching`, `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1`. 두 patch가 모두 `patched`가 아니면 시작하지 않는다. 실패한 trial은 즉시 1회 재실행한다(첫 시도는 `failed/`에 보존).

### 실험 A — 순차 (Q1·Q2·Q3·Q4)

[TASK15](TASK15.md)와 같은 구조: 대상 1 + 배경 m + 재개 1, 동시성 1. `gap_turnover_probe.py`(수정 없음), `--prompts-file experiments/npu/stage2/cliff_prompts.json --max-tokens 8 --seed 20260819`. **trial key `B{5,6,7,8}r{0,1}`** — [TASK15](TASK15.md)의 r0·r1과 **같은 prompt**를 써서 그 원로그와 사건 순서를 나란히 볼 수 있게 한다. 순서: `B5r0 B5r1 B6r0 B6r1 B7r0 B7r1 B8r0 B8r1`.

### 실험 B — 상한 도달 (Q5, 보조로 Q3·Q4)

[`dummy_lifecycle_b_probe.py`](../../experiments/npu/stage2/dummy_lifecycle_b_probe.py): 요청 8개를 **0.3 s 간격으로 하나씩** 보내고 모두 `max_tokens=384`, `ignore_eos=true`, prompt `"[i] " + experiments/npu/stage1/prompt.txt`(129 token 미만, 서로 다름). 도착이 decode 수를 1 → 8로 올리고 완료가 8 → 1로 내린다. **2회**(`b0`, `b1`).

- `requested_condition`: decode step 중 `request_nums = 8`인 구간이 있고, 그 앞뒤에 `0 < n < 8` 구간이 있다
- 도달하지 못한 run은 Q5를 `UNKNOWN`으로 보고한다(추가 run 없음)
- **지시문과의 차이(측정 전 기록)**: 지시문은 "N=8 동시 전송, 짧은 생성"이다. 동시 전송에 같은 생성 길이를 쓰면 (i) prefill이 배타·1건씩이라 decode가 시작되기 전에 8건이 모두 들어올 수 있어 **`n < 8`에서 dummy를 쥔 상태로 상한에 진입하는 전이**가 없을 수 있고, (ii) 8건이 같은 step에 끝나 **8 → 0**으로 떨어져 8 → 7 전이가 없다. Q5("상한에 도달하면 반납되는가")는 도달 **전후**의 비교이므로 도착을 0.3 s 간격으로 벌렸다. 활성 동시성 상한 8은 지시문과 같고 N ≤ 8 승인 범위 안이다. 생성 384 token은 첫 요청이 8번째 도착(2.1 s)까지 살아 있게 하는 최소 여유(decode ≈ 11 ms/step × 384 ≈ 4.2 s)로 잡았다

## 사건 정의 (분석 규칙)

- **순서**: 서버 로그의 파일 순서 = 실행 순서로 본다. `[PFX]`·`[BUCKET]`·`[OBS]`가 모두 한 EngineCore process에서 나오고 `async_scheduling=False`다([TASK15](TASK15.md) 로그에서 확인)
- **decode step** = `[BUCKET]` 줄 하나. 그 `request_nums`가 그 step의 `n`이다
- **schedule 구간 k** = (k−1)번째와 k번째 `[BUCKET]` 사이의 사건 — k번째 decode step을 준비한 schedule 호출이다
- **dummy 요청** = `DUMMY-BEGIN` 한 줄. **dummy 확보** = `DUMMY-END`(반환 OB)
- **할당 세대** `OB<id>#<g>` = 그 OB가 `[OBS] [ALLOC]`에 g번째로 등장한 뒤의 상태
- **회수 호출 경로**: `DUMMY-BEGIN`–`DUMMY-END` 괄호 안의 `EVICT` = `dummy`, 괄호 밖이고 직전 표지가 `CAN-ALLOCATE` = `request_alloc`, 직전 표지가 `PREEMPTION=True` `FREE` = `preemption`, 그 외 `unlabeled`

## 해석 규칙 (측정 전 고정)

각 질문에 대해 **trial별로 패턴을 세고**, 모든 trial에서 같은 패턴이면 그 답을, trial마다 다르면 **trial별 답을 그대로** 보고한다.

### Q1 — dummy는 언제 처음 확보되는가

| 패턴 | 답 |
|---|---|
| 첫 `DUMMY-BEGIN`이 첫 `[BUCKET]`보다 앞, 첫 `ALLOC`보다 뒤이고, 그 구간의 다음 `[BUCKET]`이 `n ≥ 1` | **첫 decode step을 준비하는 schedule 호출에서 처음 요청·확보된다** |
| 첫 `DUMMY-BEGIN`이 첫 `ALLOC`보다 앞 | **요청 할당 전에 요청된다** |
| 첫 `DUMMY-BEGIN` 앞에 `[BUCKET]`이 1개 이상 | **decode가 시작된 뒤 k step째에 처음 요청된다**(k 보고) |
| `DUMMY-BEGIN` 없음 | **요청되지 않았다** |

### Q2 — 확보 후 유지되는가, step마다 반납·재확보를 반복하는가

| 패턴 | 답 |
|---|---|
| `0 < n < 8`인 decode step마다 그 schedule 구간의 `DUMMY-BEGIN`이 **정확히 1개**(예외 0) | **step마다 새로 요청된다** |
| `DUMMY-BEGIN`이 `0 < n < 8` step 수의 절반 미만 | **한 번 확보한 뒤 여러 step 유지된다** |
| 그 사이 | **혼재** — 분포를 보고한다 |

"반납"은 따로 판정한다:

| 패턴 | 답 |
|---|---|
| 회수가 없는 dummy 괄호에서 `DUMMY-END FREE_AFTER` = `DUMMY-BEGIN FREE_BEFORE`이고, dummy OB가 `[OBS] [ALLOC]`에 dummy 명의로 나타나지 않으며, dummy OB를 되돌리는 줄이 없다 | **확보는 free 수를 줄이지 않는다 — 할당되지 않으므로 반납 사건도 없다** |
| 회수가 없는데 `FREE_AFTER < FREE_BEFORE` | **확보가 free slot을 소비한다(할당)** — 반납 여부는 이후 `FREE_BEFORE` 회복으로 본다 |

"dummy OB를 되돌리는 줄이 없다"의 조작적 정의: **free 수 장부**가 끊기지 않는다 — free 수를 싣는 `[OBS]` 줄을 순서대로 읽을 때 `ALLOC`은 `|OB|`만큼 줄이고 `EVICT`는 1 늘리며 **그 밖의 줄에서는 변하지 않는다.** dummy 확보가 할당이거나 반납이 따로 있다면 `ALLOC`·`EVICT`가 아닌 곳에서 free 수가 움직여 장부가 끊긴다. 끊김 0이면 첫 행, 1 이상이면 끊긴 위치를 보고한다.

연속한 두 `DUMMY-END`의 OB가 같은 비율은 보조로 보고한다.

### Q3 — 요청이 slot을 요구할 때 dummy가 가리키던 slot은 회수 대상인가

| 패턴 | 답 |
|---|---|
| 직전 `DUMMY-END`의 OB가 이후 요청의 `ALLOC` OB 목록에 들어가고, 그 사이 그 OB의 `EVICT`가 없다 | **회수 없이 요청에 할당된다 — 회수 대상이 아니라 free slot으로 쓰인다** |
| 직전 `DUMMY-END`의 OB에 대한 `EVICT`가 있다 | **회수 대상이 된다** |
| 둘 다 없음 | **관측 기회 없음** |

"그 사이"의 조작적 정의: dummy OB는 그 `DUMMY-END`부터 **(a) 요청 `ALLOC`이 그 OB를 가져가거나 (b) 그 OB가 `EVICT`되거나 (c) 새 `DUMMY-END`가 나올 때까지** "대기 중"이다. 대기 중에 다른 OB를 받은 `ALLOC`은 따로 센다.

### Q4 — 그 뒤 재확보가 일어나는가, 그때 다른 slot의 회수를 유발하는가

Q3 패턴이 나온 각 사례에서 **다음 `DUMMY-BEGIN`** 을 본다.

| 패턴 | 답 |
|---|---|
| `FREE_BEFORE = 0`이고 그 괄호 안에 `EVICT`(호출 경로 `dummy`) | **재확보가 다른 slot의 회수를 유발한다**(회수된 `OB#세대` 보고) |
| `FREE_BEFORE ≥ 1`이고 괄호 안 `EVICT` 없음 | **회수 없이 재확보된다** |
| 다음 `DUMMY-BEGIN`이 로그 끝까지 없음 | **관측 구간 안에서 재확보 없음** |

### Q5 — 활성 요청 수가 상한에 도달하면(n = 8) dummy는 반납되는가

| 패턴 | 답 |
|---|---|
| `n = 8`인 decode step의 schedule 구간에 `DUMMY-BEGIN`이 **0개** | **n = 8에서는 dummy가 요청되지 않는다** |
| 1개 이상 | **n = 8에서도 요청된다**(개수 보고) |
| `n = 8` step 없음 | `UNKNOWN`(조건 미도달) |

Q2의 "반납" 판정이 "반납 사건 없음"이면, Q5의 답은 **"요청이 멈춘다 — 되돌리는 사건은 없다"** 로 적는다. 8 → 7로 내려온 첫 구간의 `DUMMY-BEGIN FREE_BEFORE`와 괄호 안 `EVICT`를 함께 보고한다.

## 정합 확인 (작업 5)

| # | 대조 | 불일치 시 |
|---|---|---|
| C1 | trial별 `[OBS] [EVICT]` 수 = `[PFX] [EVICTION]` 수 | patch가 회수 경로를 빠뜨렸다는 뜻 — 사실만 보고 |
| C2 | 실험 A trial별 회수 수 = `max(0, m − 5)` | 사실만 보고 |
| C3 | 실험 A trial별 회수 수 = 같은 key의 [TASK15](TASK15.md) 원로그 `[PFX] [EVICTION]` 수 | 사실만 보고 |
| C4 | [TASK58](TASK58.md) "회수 있는 trial마다 끝내 재할당되지 않는 회수 정확히 1건" 대 이번 호출 경로별 재할당 없는 회수 수 | 사실만 보고 |

**불일치가 나와도 원인을 추정하지 않는다.**

분석 script는 측정 전에 **합성 로그**(위 소스 표의 기전을 그대로 흉내 낸 fixture, m ∈ {5, 6, 8}·상한 도달 1개·파일럿 1개)로 모든 경로가 도는지만 확인했다. **fixture의 출력은 예측이 아니며 등록하지 않는다** — script의 계기 결함을 잡기 위한 것이다. fixture는 commit하지 않는다(소스 해석을 로그 형태로 굳혀 두면 예측처럼 읽힌다).

## 환경 분리 (측정 후)

실험이 끝나면 사용자가 `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert`를 실행하고, `status`가 **`pristine`(`81850a8b…`)** 인 것과 `apply.sh status`가 여전히 `patched`(`70942d16…`)인 것을 TASK에 기록한다.

## 산출물

`<RUN>` = `results/npu/stage2/<timestamp>-dummy-lifecycle`

- trial별 `server-<TAG>.log`(`[OBS]`·`[PFX]`·`[BUCKET]` 전문), `probe/`, `<TAG>-launch.txt` 등, `smi/<TAG>.txt`
- `patch-{bucket,dummy}-<phase>-{before,after}.txt`, `manifest-<phase>.txt`, `rbln-smi-*`, `reruns.txt`, `failed/`
- `pilot.json`, `dummy_lifecycle.json`(Q1–Q5 패턴 수, 회수 라벨, 정합, 로그 발췌)

## 보고

TASK/commit hash, patch diff와 SHA256, Q1–Q5 각각의 답과 근거 로그 발췌, 회수 산술 정합, `UNKNOWN`. **"스택 설계가 좋다/나쁘다"류 평가를 하지 않는다.**
