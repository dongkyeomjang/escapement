# 계산 전 정의 — admission 경로 회수의 존재 조건 관측 (탐색 실험)

## 문서 성격

**탐색적 관측 실험**이며 [TASK63](TASK63.md)의 후속이다. 결과는 TASK 기록과 리뷰 대응 자료로만 쓰고 **논문 판정에 사용하지 않는다.** 방향 예측은 등록하지 않는다. [CLAUDE.md](../../CLAUDE.md) 실행 원칙 16에 따라 **처치 성립 판정 규칙, 반복·전환 규칙, Q1–Q3의 "로그 패턴 → 답" 해석 규칙**을 측정 전에 commit하고, 측정 후 바꾸지 않는다.

## 승인 범위 (Advisor 지시문, 사용자 전달, 2026-09-12)

- 승인: [TASK63](TASK63.md)의 관측 patch 재적용(같은 파일, SHA256 대조), 순차·저동시성 측정, 서버 재기동, 분석 script, TASK 문서
- 금지: compile, descriptor·시뮬레이터 변경, 기존 TASK 문서 수정, patch의 기능 변경. **이번 설계는 로그 지점을 추가하지 않는다** — [TASK63](TASK63.md) patch(`dummy_lifecycle_observe.patch`, SHA256 `645dc1a8…`)를 그대로 쓴다
- 측정 종료 후 patch revert와 pristine SHA256 확인을 TASK에 기록한다. 적용·복구는 root 권한이 필요하고 이 host의 sudo는 비밀번호를 요구하므로 **사용자가 별도 터미널에서 실행한다**

## 질문

[TASK63](TASK63.md)은 순차 부하(동시성 1)에서 회수 14건 전부가 dummy 경로임을 확인했고, admission 경로의 회수가 0건이라 그 경로가 어떤 조건에서 나타나는지를 `UNKNOWN`으로 남겼다.

- **Q1.** 연속 admission 조건(첫 요청의 admission과 두 번째 요청의 admission 사이에 decode step이 끼지 않음)에서 admission 경로의 회수가 실제로 발생하는가
- **Q2.** 발생한다면 회수 대상이 dummy 경로와 같은 규칙(할당 순서상 가장 이른 inactive block)으로 정해지는가
- **Q3.** 발생하지 않는다면 두 번째 요청은 어떻게 처리되는가(대기, 오류, 기타)

### 참고 가설 (판정에 사용하지 않음)

[TASK63](TASK63.md) 해석 절의 파생 관측 — "dummy 경로가 `0 < n < 8`인 동안 free를 1 이상으로 되돌려 두므로 순차 부하의 admission은 회수할 기회가 없다" — 이 맞다면, **처치가 성립한 반복에서 두 번째 admission은 `FREE=0`을 만나 스스로 회수해야 한다.** 기록만 하며 아래 해석 규칙은 이 가설을 참조하지 않는다.

## 소스 확인 (측정 전, 설치 소스 읽기 전용, pristine 줄 번호)

| 역할 | 위치 (`vllm_rbln 0.11.1`) | 내용 |
|---|---|---|
| waiting 우선 | `v1/core/optimum_scheduler.py:324-329` | WAITING을 먼저 스케줄한다. `len(self.running) == max_num_running_reqs`이면 즉시 `break` |
| prefill 1건 제한 | 같은 파일 `:336-337` | `req_index > 0`이면 `break` — 한 schedule 호출은 새 요청을 1건만 admission한다 |
| admission 할당 | 같은 파일 `:378-385` | `allocate_slots`가 `None`이면 `break` — 그 요청은 waiting에 남는다(`pop`은 `:425`에서 성공 시에만) |
| decode 조건 | 같은 파일 `if req_index == 0:` | admission이 있었던 호출에서는 running 요청을 decode로 싣지 않는다 → **그 호출에는 decode step도 dummy 요청도 없다** |
| admission의 slot 검사 | `v1/core/optimum_kv_cache_manager.py:281-290` | inner block pool 검사 뒤 `prefix_cache_manager.can_allocate(num_blocks, num_computed_tokens)` |
| 회수 | `v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py` `can_allocate` | free가 부족하면 `select_blocks_for_eviction`으로 고른 block을 `_evict_block` |
| 대상 선정 | `v1/core/prefix_cache_manager/optimum_eviction_policy.py:48-82` `FIFOEvictionPolicy` | 할당 시 `register_block`한 순서(`_allocation_order`)에서 **inactive mapping인 block을 앞에서부터** `count`개 |
| inactive 전이 | `optimum_prefix_cache_manager.py` `free_request` | `PREEMPTION=False`이면 mapping을 남기고 `is_active = False` — free list로 돌아가지 않는다 |

소스상 연속 admission은 "첫 요청의 prefill이 진행되는 동안 두 번째 요청이 도착해 waiting에 있으면, 다음 schedule 호출이 decode 없이 두 번째 요청을 admission한다"는 경로로 만들어질 수 있다. **소스 읽기는 관측 결과가 아니며, 아래 규칙은 로그 패턴만으로 답을 정한다.**

## 참조 정정 (측정 전 기록)

지시문은 "TASK63 관측상 m ≥ 2부터 free가 dummy 유지분 1칸만 남는 상태"라고 적었다. [TASK63](TASK63.md) 기록은 이와 다르다 — 실험 B에서 요청 할당 뒤 `DUMMY-BEGIN FREE_BEFORE`가 6, 5, 4, 3, 2, 1로 줄었고(관측 4), 실험 A의 회수는 m = 6(할당 8건째)에서 시작했다(C2). **free가 1이 되는 것은 할당 7건 이후**이며, 8건째 할당이 free를 0으로 만들면 그 요청의 첫 decode step에서 dummy가 1칸을 회수해 free가 1로 돌아간다. 따라서 포화 단계는 **배경 8건**으로 하고, 정확한 상태는 아래 포화 성립 조건으로 로그에서 확인한다.

## 실험 설계

공통: artifact `models/Qwen3-4B-rbln-b8-s8192-d4-mb`(manifest `b4f5cbf1…651f5f`, 측정 전 대조), **반복마다 fresh server**, `vllm serve <artifact> --host 127.0.0.1 --port 8000 --enable-prefix-caching`, `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1`. [TASK12](TASK12.md) patch와 [TASK63](TASK63.md) patch가 모두 `patched`가 아니면 시작하지 않는다. 모든 요청은 `max_tokens=8`, `temperature=0`, `seed=20260819`.

prompt는 [TASK15](TASK15.md)의 `experiments/npu/stage2/cliff_prompts.json`에서 가져온다(생성기 규격 2,000 token, 서로 다른 seed). 반복마다 같은 10개를 쓴다(fresh server라 반복 간 캐시가 이어지지 않는다).

| 역할 | prompt | 비고 |
|---|---|---|
| 배경 `bg0`–`bg7` | `trials.B8r0.background[0..7]` | 포화 단계 |
| 처치 `X` | `trials.B8r0.target` | 먼저 보내는 요청 |
| 처치 `Y` | `trials.B8r1.target` | 나중에(또는 동시에) 보내는 요청 |

10개의 쌍별 공통 접두부는 최대 **2글자**다(측정 전 확인, prefix hit 단위 128 token ≈ 수백 글자에 한참 못 미친다). probe가 시작할 때 다시 검사해 64글자 이상이면 중단한다.

### 한 반복의 절차 ([`admission_eviction_probe.py`](../../experiments/npu/stage2/admission_eviction_probe.py))

1. **포화 단계**: `bg0`–`bg7`을 **순차로** 보낸다(각 요청은 응답을 받은 뒤 다음을 보낸다)
2. 마지막 배경 응답 뒤 **1.0 s** 쉰다(진행 중인 decode가 없게 한다)
3. **처치 단계**: `X`와 `Y`를 보낸다. 두 connection은 미리 연다
   - **`consecutive`(연속 전송, 기본)**: `X` 요청을 socket에 다 쓴 직후, 쉬지 않고 `Y` 요청을 쓴다. 응답은 그 뒤에 두 thread가 읽는다
   - **`simultaneous`(동시 전송, 예비안)**: thread 2개가 barrier에서 동시에 풀려 각자 요청을 쓰고 응답을 읽는다
4. 송신 시작·끝, 응답 수신 시각(`time.time()`, 서버 `[OBS] t=`와 같은 벽시계), HTTP status, 응답 `id`, `usage`를 기록한다. 응답 `id`는 서버 로그 요청 id의 strict prefix다([TASK18](TASK18.md))

probe 종료 코드: 포화 단계에서 200이 아닌 응답이나 연결 오류가 있으면 2(→ 그 반복을 실패로 보고 1회 재실행, 첫 시도는 `failed/`에 보존), prompt 검사 실패 3. **처치 단계의 오류 응답은 Q3의 자료이므로 실패로 치지 않는다**(종료 코드 0).

### 반복·전환 규칙 ([`run_admission_eviction.sh`](../../experiments/npu/stage2/run_admission_eviction.sh))

매 반복 직후 분석 script의 `classify`가 그 반복을 아래 네 부류 중 하나로 정하고, 구동 script가 그 결과로 다음을 정한다.

1. 반복 1–5는 `consecutive`
2. **전환**: 반복 5가 끝났을 때 `consecutive`의 `ESTABLISHED`가 **2회 이하**(불성립이 과반 = "지배적")이면 반복 6부터 `simultaneous`로 바꾼다. 3회 이상이면 `consecutive`를 유지한다
3. **종료**: **현재 모드의** `ESTABLISHED`가 5회에 도달하면 멈춘다. 전환된 경우 `consecutive`의 성립 반복은 따로 보고하고 `simultaneous`의 5회에 합산하지 않는다
4. **상한**: 반복은 총 20회(재실행은 따로 세지 않는다). 상한에 닿으면 성립 5회 미만이어도 멈추고 그대로 보고한다
5. 재실행 후에도 실패한 반복은 `INVALID`로 기록하고 반복 수에 넣는다(성립에는 넣지 않는다)

## 사건 정의

- **순서**: 서버 로그의 파일 순서 = 실행 순서([TASK63](TASK63.md)과 같다). decode step = `[BUCKET]` 줄 하나
- **dummy 괄호**: `DUMMY-BEGIN`–`DUMMY-END` 사이
- **admission 진입** = dummy 괄호 **밖**의 `[OBS] [CAN-ALLOCATE]`이면서 `COMPUTED=0`, `NUM_NEW > 0`인 줄 — 새 요청의 slot 검사다. running 요청의 decode 검사는 `COMPUTED > 0`이고 dummy의 검사는 괄호 안이라 섞이지 않는다([TASK63](TASK63.md) 관측 1·5)
- **처치 `ALLOC`**: 응답 `id`로 `X`·`Y`의 `[OBS] [ALLOC]`을 찾는다(`REQUEST`가 `id`와 같거나 `id-`로 시작). 응답 `id`가 하나라도 없으면 **순서 대체**: 배경 수(8)만큼의 `ALLOC` 뒤에 오는 `ALLOC`들을 처치로 본다. 어느 방법을 썼는지 기록한다
- **`A1` / `A2`** = 처치 `ALLOC` 중 로그에서 먼저 / 나중에 나오는 것(보낸 순서와 다를 수 있다 — 둘 다 기록)
- **`E1`** = `A1` 직전의 admission 진입(첫 처치 요청의 slot 검사). **`E2`** = `A1` 뒤 첫 admission 진입(두 번째 처치 요청의 slot 검사)
- **회수 호출 경로**: [TASK63](TASK63.md)의 `annotate`를 그대로 쓴다 — dummy 괄호 안 = `dummy`, 괄호 밖이고 직전 표지가 `CAN-ALLOCATE` = `request_alloc`, 직전 표지가 `PREEMPTION=True` `FREE` = `preemption`, 그 외 `unlabeled`

## 처치 성립 판정 (반복마다, 측정 전 고정)

| 부류 | 조건 |
|---|---|
| `SATURATION_FAIL` | `E1`의 `FREE`가 1이 아니다(포화 상태가 가정과 다르다) |
| **`ESTABLISHED`** | `E1 FREE = 1`이고, `A1`과 `E2` 사이에 `[BUCKET]`도 `DUMMY-BEGIN`도 **없다** |
| `NOT_ESTABLISHED` | `E1 FREE = 1`이고, `A1`과 `E2` 사이에 `[BUCKET]` 또는 `DUMMY-BEGIN`이 1개 이상 있다 |
| `UNCLASSIFIABLE` | 처치 `ALLOC`이 없거나 `E1`·`E2`를 찾을 수 없다 |

불성립·분류 불가 반복도 **폐기하지 않고 그대로 보고한다**(불성립 비율 자체가 scheduler 동작의 정보다). 부류별 건수를 모드별로 보고한다.

## 해석 규칙 (측정 전 고정)

각 질문은 **`ESTABLISHED` 반복**에서 패턴을 센다. 모든 성립 반복에서 같은 패턴이면 그 답을, 반복마다 다르면 반복별 답을 그대로 보고한다. 불성립 반복의 같은 수치는 참고로 따로 보고한다. 전환이 일어나면 모드별로 따로 답한다.

### Q1 — 연속 admission에서 admission 경로 회수가 발생하는가

`E2` 뒤부터 다음 `ALLOC`·`[BUCKET]`·`DUMMY-BEGIN`·admission 진입 중 먼저 오는 것까지를 **`E2` 구간**이라 한다.

| 패턴 | 이름 | 답 |
|---|---|---|
| `E2 FREE < REQUIRED_OB`, `E2` 구간에 `EVICT`(호출 경로 `request_alloc`) 1개 이상, 구간이 `A2`로 끝남 | `P1` | **admission 경로 회수가 발생한다**(회수된 `OB#세대` 보고) |
| `E2 FREE ≥ REQUIRED_OB`, 구간에 `EVICT` 없음, 구간이 `A2`로 끝남 | `P2` | **두 번째 admission이 free 부족을 만나지 않았다 — 회수 없이 할당된다**(Q1: 발생하지 않음) |
| `E2 FREE < REQUIRED_OB`, 구간에 `EVICT` 없음, 구간이 `A2`로 끝나지 않음 | `P3` | **free가 부족한데 admission이 회수하지 않았다** → Q3 |
| 그 밖 | `OTHER` | 사건 열을 그대로 보고 |

### Q2 — 회수 대상이 dummy 경로와 같은 규칙인가

각 `[OBS] [EVICT]`에 대해, 그 시점의 **inactive 집합**(마지막 사건이 `PREEMPTION=False` `FREE`인 OB)을 로그에서 재구성하고, 그 가운데 **가장 최근 `ALLOC` 줄이 가장 이른 OB**를 "할당 순서상 가장 이른 inactive"라 한다.

| 패턴 | 답 |
|---|---|
| 성립 반복의 `request_alloc` 회수 전부에서 회수 OB = 가장 이른 inactive이고, 같은 반복들의 `dummy` 회수도 전부 그렇다 | **같은 규칙이다 — 두 경로 모두 할당 순서상 가장 이른 inactive block을 회수한다** |
| `request_alloc` 회수 중 하나라도 가장 이른 inactive가 아니다 | **다른 대상을 고른 사례가 있다**(사례별로 회수 OB와 가장 이른 inactive를 보고) |
| `request_alloc` 회수가 `dummy`와 같은 규칙이나 `dummy` 회수 중 예외가 있다 | 두 경로의 일치·불일치 수를 그대로 보고 |
| `request_alloc` 회수 0 | **적용 불가**(Q1이 `P1`이 아님) |

### Q3 — 회수하지 않았다면 두 번째 요청은 어떻게 되는가

`P2`·`P3`·`OTHER` 반복에서 두 번째 처치 요청(= `A2`의 요청, `A2`가 없으면 `A1`이 아닌 처치 요청)을 본다.

| 패턴 | 답 |
|---|---|
| `A2`가 `E2`보다 뒤에 `[BUCKET]` 1개 이상을 사이에 두고 나오고 HTTP 200 | **대기했다가 decode step 뒤에 할당된다**(끼인 decode step 수, 재시도 admission 진입 수, 그 사이 회수의 호출 경로 보고) |
| `A2`가 없거나 HTTP status가 200이 아니다 | **오류 또는 미처리**(status·오류 본문 보고) |
| `P2`로 곧바로 할당 | **free가 남아 있어 즉시 할당된다** |
| 그 밖 | **기타** — 사건 열을 그대로 보고 |

## 정합 확인

| # | 대조 | 불일치 시 |
|---|---|---|
| C1 | 반복별 `[OBS] [EVICT]` 수 = `[PFX] [EVICTION]` 수 | 사실만 보고 |
| C2 | 반복별 회수 수 = `max(0, ALLOC + 1 − 8)` ([TASK58](TASK58.md)·[TASK63](TASK63.md) 산술) | 사실만 보고 |
| C3 | `FREE`의 `PREEMPTION=True` 수 | 보고만 |
| C4 | free 수 장부([TASK63](TASK63.md) 정의: `ALLOC`은 −\|OB\|, `EVICT`는 +1, 그 밖에서는 불변) 끊김 수 | 사실만 보고 |
| C5 | 요청 10건의 HTTP status, 처치 요청의 `prompt_tokens`(2,000 기대)·`completion_tokens` | 보고만 |
| C6 | 끝내 재할당되지 않는 회수의 호출 경로별 수 | 보고만 |

**불일치가 나와도 원인을 추정하지 않는다.**

## 계기 점검 (측정 전)

- 분석 script는 **합성 로그**(성립·불성립·`P1`·`P3` 경로를 흉내 낸 fixture)와 [TASK63](TASK63.md) 실로그로 모든 경로가 도는지만 확인한다
- probe는 **로컬 모의 HTTP 서버**로 두 모드의 송신 순서·기록 field를 확인한다
- **fixture와 모의 서버의 출력은 예측이 아니며 commit하지 않는다**

## 환경 분리 (측정 후)

실험이 끝나면 사용자가 `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert`를 실행하고, `status`가 **`pristine`(`81850a8b…`)** 인 것과 `apply.sh status`가 여전히 `patched`(`70942d16…`)인 것을 TASK에 기록한다. **이 patch를 적용한 상태로 논문용 측정을 하지 않는다.**

## 산출물

`<RUN>` = `results/npu/stage2/<timestamp>-admission-eviction`

- 반복별 `server-<TAG>.log`, `probe/admission.<TAG>.json`, `probe-<TAG>.log`, `class/<TAG>.json`, `<TAG>-launch.txt` 등, `smi/<TAG>.txt`
- `order.txt`(반복·모드·부류·시각), `switch.txt`(전환 시), `provenance.txt`, `patch-{bucket,dummy}-{before,after}.txt`, `manifest.txt`, `rbln-smi-{before,after}.txt`, `reruns.txt`, `failed/`
- `admission_eviction.json`(부류, Q1–Q3 패턴 수, 회수 대상 대조, 정합, 로그 발췌)

## 보고

TASK/commit hash(선등록 선행 증빙), patch 적용·revert SHA256, 처치 성립/불성립 건수(모드별), Q1–Q3 답과 근거 로그 발췌, [TASK63](TASK63.md) 회수 산술과의 정합, `UNKNOWN`. **스택 설계 평가를 하지 않는다.**
