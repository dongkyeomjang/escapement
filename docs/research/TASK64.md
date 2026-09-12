# TASK64 — admission 경로 회수의 존재 조건 관측 (탐색)

## 상태

DONE

## 판정

**탐색 실험이며 논문 판정에 사용하지 않는다.** 방향 예측은 등록하지 않았고, 처치 성립 판정 규칙·반복·전환 규칙·Q1–Q3의 "로그 패턴 → 답" 해석 규칙을 측정 전에 commit했다.

선등록 문서: [ADMISSION_EVICTION_PLAN.md](ADMISSION_EVICTION_PLAN.md) (commit `cb17211`, 2026-09-12T14:37:51+09:00). **patch 재적용 14:39:53(대상 파일 mtime, 선등록 2분 2초 뒤), 측정 시작 14:40:53(선등록 3분 2초 뒤).** 규칙과 script를 측정 후에 바꾸지 않았다(`git diff cb17211` 비어 있음).

처치 성립 (반복 규칙: 1–5회 `consecutive`, 성립 ≤ 2면 `simultaneous` 전환, 현재 모드 성립 5회 또는 20회에서 종료):

| 모드 | 반복 | `ESTABLISHED` | `NOT_ESTABLISHED` | `SATURATION_FAIL` | `UNCLASSIFIABLE` | `INVALID` |
|---|---|---|---|---|---|---|
| `consecutive` | 5 (R01–R05) | **5** | 0 | 0 | 0 | 0 |
| `simultaneous` | 0 (전환 조건 미충족) | — | — | — | — | — |

현재 모드의 성립이 5회에 도달해 R05에서 멈췄다. 재실행 0.

선등록 규칙이 가리키는 답 (성립 반복 5회):

| 질문 | 관측 패턴 | 규칙이 정하는 답 |
|---|---|---|
| **Q1** 연속 admission에서 admission 경로 회수가 발생하는가 | **5/5 `P1`**: 두 번째 admission 진입 `E2`가 `FREE=0 REQUIRED_OB=1`이고, `E2` 구간에 `request_alloc` 회수 1건(`OB1#1`)이 있으며 구간이 두 번째 요청의 `ALLOC`(`OB1#2`)으로 끝난다 | **admission 경로 회수가 발생한다** |
| **Q2** 회수 대상이 dummy 경로와 같은 규칙인가 | 성립 반복의 `request_alloc` 회수 **5/5**가 할당 순서상 가장 이른 inactive block이고, 같은 반복의 `dummy` 회수도 **10/10** 그렇다 | **같은 규칙이다 — 두 경로 모두 할당 순서상 가장 이른 inactive block을 회수한다** |
| **Q3** 회수하지 않았다면 두 번째 요청은 어떻게 되는가 | 5/5 `NOT_APPLICABLE`(전부 `P1`) | **적용 불가** — 회수하지 않는 경우가 관측되지 않았다 |

정합 확인 (불일치 시 사실만 보고):

| # | 대조 | 결과 |
|---|---|---|
| C1 | `[OBS] [EVICT]` 수 = `[PFX] [EVICTION]` 수 | **5/5 일치** (3 = 3) |
| C2 | 회수 수 = `max(0, ALLOC + 1 − 8)` ([TASK58](TASK58.md)·[TASK63](TASK63.md) 산술) | **5/5 일치** (`ALLOC` 10 → 3) |
| C3 | `FREE`의 `PREEMPTION=True` | 0 (5/5) |
| C4 | free 수 장부 끊김 | **0** (반복당 291 전이) |
| C5 | HTTP status / 처치 요청 `prompt_tokens` / `completion_tokens` | 10건 전부 200 (5/5) / X·Y 2,000·2,000 / 8·8 |
| C6 | 끝내 재할당되지 않는 회수의 호출 경로 | 반복마다 1건, 전부 `dummy`(`OB2#1`). `request_alloc` 0 |

## 날짜

2026-09-12

## 목적

[TASK63](TASK63.md)은 순차 부하에서 회수 14건 전부가 dummy 경로임을 확인했고, admission 경로의 회수가 0건이라 **그 경로가 어떤 조건에서 나타나는지를 `UNKNOWN`으로 남겼다.** [TASK63](TASK63.md)의 파생 해석("dummy가 매 decode step마다 free를 1 이상으로 되돌려 두기 때문")이 맞다면 **연속된 admission 사이에 decode step이 끼지 못하는 조건**에서는 두 번째 admission이 free 0을 만나 스스로 회수해야 한다. 그 조건을 만들어 Q1–Q3을 로그 사건 순서로 본다(Advisor 지시, 탐색 실험, 사용자 전달 2026-09-12).

## 배경

관련 TASK:

- [TASK63](TASK63.md) — 직전 TASK. 관측 patch, 사건 정의, 회수 호출 경로 라벨, free 수 장부를 그대로 쓴다. 해석 절의 파생 관측이 이번 참고 가설이다
- [TASK58](TASK58.md) — 회수 건수 산술 `max(0, ALLOC + 1 − 8)`
- [TASK15](TASK15.md) — 이번 prompt의 출처(`cliff_prompts.json`)
- [TASK60](TASK60.md) — scheduler의 "배타"(prefill 1건 제한, `req_index == 0`일 때만 decode)와 "우선순위"(running에 자리가 있을 때 waiting 먼저)의 코드 위치
- [TASK18](TASK18.md) — 응답 `id`가 서버 요청 id의 strict prefix라는 귀속 채널

## 시작 상태

- 시작 commit `dce0f31`(TASK63), 선등록 commit `cb172116852e2e48323d033392ee42690ef87721` (2026-09-12T14:37:51+09:00), `git status --short`: `?? .idea/`만
- Package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`, `rebel-compiler 0.11.1.post1`, `torch 2.11.0+cpu` (run의 `provenance.txt`)
- Host `atom-max8`, 측정 전 32 device 전부 `0.0B`, 서버 없음, port 8000 비어 있음
- Artifact `models/Qwen3-4B-rbln-b8-s8192-d4-mb`, manifest `b4f5cbf1…651f5f` 일치
- Substrate: 측정 전 [TASK63](TASK63.md) patch는 `pristine`(`81850a8b…`)이었고, 사용자가 선등록 뒤 재적용했다 → `patched` `a51f93ab…`([TASK63](TASK63.md) 기록과 같음). [TASK12](TASK12.md) patch `patched` `70942d16…`. 두 patch 모두 측정 전후 `patched`

## 수행 내용

1. 설치 소스(읽기 전용)에서 admission 경로(waiting 우선, prefill 1건 제한, `allocate_slots` 실패 시 `break`)와 FIFO 대상 선정(`_allocation_order` 중 inactive를 앞에서부터)을 확인하고 계획서에 줄 번호를 적었다.
2. 지시문의 "m ≥ 2부터 free 1칸"을 [TASK63](TASK63.md) 기록과 대조해 **할당 7건 이후**로 정정하고(측정 전 기록), 포화를 배경 8건으로 정했다.
3. probe·구동·분석 script와 선등록 문서를 작성했다. **측정 전 계기 점검**: 로컬 모의 HTTP 서버로 두 전송 모드(연속 전송 송신 간격 0.08 ms), 합성 로그 3종(성립+`P1`, 불성립+`P2`, 성립+`P3`→대기 후 할당)과 [TASK63](TASK63.md) 실로그 1개로 분석 경로를 확인했다. 그 과정에서 fixture의 자리표시자 결함(분석 script와 무관)과 `P1` 반복의 Q3 표시(`OTHER` → `NOT_APPLICABLE`)를 고친 뒤 commit했다. fixture·모의 서버 출력은 commit하지 않았다.
4. (사용자, sudo) patch 재적용 → SHA256 대조.
5. 측정: `consecutive` 5회, 5/5 성립으로 종료.
6. 선등록 분석으로 `admission_eviction.json`을 만들었다.
7. (사용자, sudo) patch revert — 재현 정보 「환경 분리」에 기록.

## 변경된 파일

- `docs/research/ADMISSION_EVICTION_PLAN.md`, `experiments/npu/stage2/admission_eviction_probe.py`, `experiments/npu/stage2/run_admission_eviction.sh`, `experiments/npu/analysis/admission_eviction.py` (선등록, 측정 전 commit `cb17211`)
- `docs/research/TASK64.md` (신규), `docs/research/INDEX.md` (갱신)

기존 TASK 문서, 논문 원고, descriptor, 시뮬레이터, patch 파일은 수정하지 않았다. 분석 script는 [TASK63](TASK63.md)의 `dummy_lifecycle.py`를 import만 한다(수정 없음). compile 0회.

## 실험 또는 검증 방법

```bash
RUN=results/npu/stage2/20260912-144017-admission-eviction
bash experiments/npu/stage2/run_admission_eviction.sh "$RUN"
env -u PYTHONPATH python3 experiments/npu/analysis/admission_eviction.py analyze \
    --run "$RUN" --output "$RUN/admission_eviction.json"
```

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| 포화 | 배경 8건 순차 뒤 첫 처치 admission 진입 `E1`의 `FREE = 1` | 5/5 `E1 FREE=1 REQUIRED_OB=1`. 포화 단계 회수는 반복마다 dummy `OB0#1` 1건 | `YES` |
| 처치 | 두 admission 사이에 decode step·dummy 요청 없음 | 5/5 `A1`–`E2` 사이 `[BUCKET]` 0, `DUMMY-BEGIN` 0 | `YES` |
| 연속 전송 | X를 socket에 쓴 직후 Y | 송신 간격 0.089–0.198 ms. X·Y 모두 서버의 X 할당(`A1`)보다 9.0–17.1 ms 앞서 송신 | `YES` |
| 처치 요청 | 각 2,000 token, 생성 상한 8, 서로·배경과 prefix 비공유 | `prompt_tokens` 2,000·2,000, `completion_tokens` 8·8, 10개 prompt의 쌍별 공통 접두부 최대 2글자, `CACHE-HIT`·`CACHE-PARTIAL` 0줄 | `YES` |
| 반복 | 성립 5회 또는 20회 | 5회에서 성립 5 | `YES` |
| patch 상태 | 두 patch `patched`, 측정 전후 동일 | 전후 모두 `patched`, SHA256 동일 | `YES` |
| 환경 분리 | 측정 후 revert, `pristine`(`81850a8b…`), [TASK12](TASK12.md) patch는 `patched` 유지 | 14:54:36 `pristine` `81850a8b…` / `patched` `70942d16…` | `YES` |

## 결과

Population: 반복 1개 = fresh server 1개의 EngineCore 로그 전체와 그 반복의 probe 기록. Source: 서버 로그의 `[OBS]`·`[PFX]`·`[BUCKET]`, probe JSON(송신·응답 시각은 `time.time()`, 서버 `[OBS] t=`와 같은 벽시계). Device scope: `rbln0`–`rbln3`.

### 관측 1 — 반복별 요약

| 반복 | 송신 간격 (ms) | X·Y 송신 − `A1` (ms) | `A1` (X) | `E1 FREE` | `E2` − `A1` (ms) | `E2 FREE` | `E2` 구간 회수 | `A2` (Y) | 회수 전체 (경로) |
|---|---|---|---|---|---|---|---|---|---|
| R01 | 0.092 | −9.1 / −9.0 | `OB0#2` | 1 | 359.8 | 0 | `OB1#1:request_alloc` | `OB1#2` | `OB0#1:dummy`, `OB1#1:request_alloc`, `OB2#1:dummy` |
| R02 | 0.132 | −11.3 / −11.2 | `OB0#2` | 1 | 359.7 | 0 | `OB1#1:request_alloc` | `OB1#2` | 같음 |
| R03 | 0.089 | −17.1 / −17.1 | `OB0#2` | 1 | 361.6 | 0 | `OB1#1:request_alloc` | `OB1#2` | 같음 |
| R04 | 0.198 | −15.5 / −15.3 | `OB0#2` | 1 | 367.0 | 0 | `OB1#1:request_alloc` | `OB1#2` | 같음 |
| R05 | 0.126 | −14.5 / −14.3 | `OB0#2` | 1 | 360.9 | 0 | `OB1#1:request_alloc` | `OB1#2` | 같음 |

5회 모두 로그에서 X가 먼저 admission됐다(`A1` = X). `E2` − `A1`(359.7–367.0 ms)은 X의 prefill 시간이며 Y는 그 전에 보내졌다. X와 Y의 응답은 `A1` 뒤 812.6–837.3 ms에 서로 0.4 ms 안에서 도착했다.

### 관측 2 — 원로그 발췌 (R01, `server-R01.log` 파일 920–939행 = 분석 JSON의 `line` 1020–1039, `[OBS]`·`[PFX]`·`[BUCKET]` 줄만, 줄머리 생략)

```
[OBS] [CAN-ALLOCATE] NUM_NEW=16 COMPUTED=0 REQUIRED_OB=1 FREE=1        ← E1 (X의 admission)
[PFX] [ALLOC] REQUEST=cmpl-9d3393a4b7d0d088-0-93e59639 | OB_COUNT=1 OB=[0]
[OBS] [ALLOC] … OB=[0] FREE_AFTER=0                                     ← A1 = X, OB0#2 (t=…722.524498)
[OBS] [CAN-ALLOCATE] NUM_NEW=16 COMPUTED=0 REQUIRED_OB=1 FREE=0        ← E2 (Y의 admission, t=…722.884301)
[PFX] [MAPPING-REMOVE] OB=1 …
[PFX] [EVICTION] OB=1 | IB_COUNT=16 | FREE_BLOCKS_AFTER=1 | …
[OBS] [EVICT] OB=1 FREE_AFTER=1                                         ← request_alloc 회수, OB1#1
[PFX] [ALLOC] REQUEST=cmpl-88c1ecd33d7205c8-0-915be546 | OB_COUNT=1 OB=[1]
[OBS] [ALLOC] … OB=[1] FREE_AFTER=0                                     ← A2 = Y, OB1#2
[OBS] [CAN-ALLOCATE] NUM_NEW=0 COMPUTED=2000 REQUIRED_OB=0 FREE=0      ← X의 decode 검사
[OBS] [CAN-ALLOCATE] NUM_NEW=0 COMPUTED=2000 REQUIRED_OB=0 FREE=0      ← Y의 decode 검사
[OBS] [DUMMY-BEGIN] FREE_BEFORE=0 HEAD=-1
[OBS] [CAN-ALLOCATE] NUM_NEW=1 COMPUTED=0 REQUIRED_OB=1 FREE=0
[PFX] [EVICTION] OB=2 | IB_COUNT=16 | FREE_BLOCKS_AFTER=1 | …
[OBS] [EVICT] OB=2 FREE_AFTER=1                                         ← dummy 회수, OB2#1 (이후 재할당 없음)
[OBS] [DUMMY-END] OB=2 FREE_AFTER=1
[BUCKET] request_nums=2 padded_batch_size=2                             ← 처치 뒤 첫 decode step
```

**admission 경로 회수의 로그 모양**(이번에 처음 관측): 새 요청의 `CAN-ALLOCATE`(`COMPUTED=0`, `FREE=0`) → `[PFX] [MAPPING-REMOVE]` → `[PFX] [EVICTION]` → `[OBS] [EVICT]` → **곧바로 같은 OB의 `[PFX] [ALLOC]`**. dummy 괄호와 `[BUCKET]`이 끼지 않는다.

### 관측 3 — 회수 대상 대조 (Q2)

각 회수 직전의 inactive 집합(할당 순서)과 회수 OB. 5회 모두 같다.

| 회수 | 호출 경로 | 직전 inactive 집합 (할당 순서) | 가장 이른 inactive | 일치 |
|---|---|---|---|---|
| `OB0#1` (포화 단계, 8번째 배경의 첫 decode step) | `dummy` | 0, 1, 2, 3, 4, 5, 6 | 0 | 예 |
| `OB1#1` (Y의 admission) | `request_alloc` | 1, 2, 3, 4, 5, 6, 7 | 1 | 예 |
| `OB2#1` (처치 뒤 첫 decode step) | `dummy` | 2, 3, 4, 5, 6, 7 | 2 | 예 |

Y의 admission 시점에 `OB0`은 X가 새 세대(`OB0#2`)로 쥐고 있어 active이므로 inactive 집합에 없다. 합계: `request_alloc` 5/5, `dummy` 10/10이 가장 이른 inactive다.

### 관측 4 — 로그 줄 번호의 두 체계와 [TASK63](TASK63.md) 정정

서버 로그에는 기동 중 progress bar가 남긴 `\r`이 105개 있고(단독 `\r` 100개), 분석 파서(`dummy_lifecycle.parse`, Python `str.splitlines()`)는 단독 `\r`도 줄 경계로 센다. 그래서 **분석 산출물 JSON의 `line` 값(`excerpt_*`의 `L…` 포함)은 `grep -n`·편집기의 파일 줄 번호보다 기동 구간 이후 100 크다**(R01: 파서 1122줄 대 `\n` 1022줄). 사건 순서와 개수는 두 체계에서 같으므로 판정·집계에는 영향이 없다. 확인한 대응:

| 로그 | 파서 번호 | 파일 번호 | 줄 |
|---|---|---|---|
| 이번 `server-R01.log` | 1020 / 1024 / 1027 / 1029 / 1039 | 920 / 924 / 927 / 929 / 939 | `E1` / `E2` / `EVICT OB=1` / `A2` / 처치 뒤 첫 `[BUCKET]` |
| [TASK63](TASK63.md) `server-B.b0.log` | 1859 / 1884 | 1759 / 1784 | 상한 진입 발췌의 처음(`DUMMY-END OB=7`) / 끝(`[BUCKET] request_nums=8`) |
| [TASK63](TASK63.md) `server-B.b0.log` | 3954 / 3972 | 3854 / 3872 | 상한 이탈 발췌의 처음(`[BUCKET] request_nums=8`) / 끝(`request_nums=7`) |

**[TASK63](TASK63.md) 정정 (원문은 수정하지 않는다)**: 관측 5의 "B.b0 상한 진입 (L1859–L1884)"과 "B.b0 상한 이탈 (L3954–L3972)"은 **파서 번호**이며, 파일 줄 번호로는 **1759–1784행**과 **3854–3872행**이다. 같은 관측 5의 A.B7r0 발췌 "L884–L947"은 `grep -n`으로 뽑은 **파일 번호**라 맞다(파서 번호 888은 파일 788행의 HTTP 접근 로그 줄이다). 발췌 내용과 판정은 그대로다.

## 핵심 발견

1. **`stack`** — **두 admission 사이에 decode step이 끼지 않으면, 두 번째 admission이 `FREE=0`을 만나 admission 경로에서 스스로 회수한다(5/5).** 로그 모양은 `CAN-ALLOCATE(COMPUTED=0, FREE=0)` → `EVICTION` → 곧바로 같은 OB의 `ALLOC`이다. [TASK63](TASK63.md)이 `UNKNOWN`으로 남긴 "admission 경로 회수의 발생 조건과 로그 모양" 가운데 **하나의 충분 조건과 그 모양**이 관측됐다. 값(slot 8, prefill 약 360 ms)은 이 구성의 것이다.
2. **`stack`** — **회수 대상 규칙은 두 경로에서 같다 — 할당 순서상 가장 이른 inactive block이다**(`request_alloc` 5/5, `dummy` 10/10). 두 경로가 같은 `can_allocate`와 같은 FIFO 정책을 부른다는 소스 확인과 부합한다(소스 확인은 관측이 아니다).
3. **`stack`** — **간격 없는 연속 전송이 5/5 처치를 만들었다.** Y는 X의 prefill(359.7–367.0 ms) 동안 waiting에 있었고, 다음 schedule 호출이 decode를 싣지 않고 Y를 admission했다. 불성립은 0회였고 예비안(동시 전송)으로 전환하지 않았다.
4. **`stack`** — **회수 경로가 dummy에서 admission으로 옮겨가도 회수 총수는 `max(0, ALLOC + 1 − 8)`을 유지한다(5/5, 10 → 3).** 이번 3건 중 1건이 `request_alloc`, 2건이 `dummy`이고, 끝내 재할당되지 않는 회수 1건은 이번에도 dummy 경로다.
5. **`universal`** — **한 부하에서 어떤 경로의 사건이 0건이라는 것은 그 경로가 없다는 뜻이 아니라, 그 부하가 발생 조건을 만들지 않았다는 뜻일 수 있다.** [TASK63](TASK63.md)의 admission 경로 회수 0/14는 순차 부하가 연속 admission을 만들지 않았기 때문이었고, 조건을 만들자 5/5 나타났다. 부재 관측에는 조건 범위를 함께 적어야 한다. 방법론의 문제이므로 substrate와 무관하다.

## 해석

지시에 따라 스택 설계의 좋고 나쁨은 평가하지 않는다.

- **참고 가설과의 관계(판정 미사용)**: 선등록에 적은 [TASK63](TASK63.md) 파생 관측의 함의 — "처치 성립 시 두 번째 admission에서 free 0 조우" — 와 관측(`E2 FREE=0` 5/5)이 부합한다. 그 파생 해석은 "순차 부하의 admission이 회수하지 않은 이유"로서 이번 조건에서 반박되지 않았다. 다만 이것은 한 조건의 부합이며, 다른 조건(동시 전송, 더 높은 동시성)에서의 경로 분포는 재지 않았다.
- **이번 조건에서 dummy 여유분의 소비(파생)**: 포화 뒤 idle 상태의 free 1칸(dummy가 되돌려 둔 칸)을 X의 admission이 가져가고, decode step이 없으니 dummy가 그 칸을 되돌릴 기회가 없어, Y의 admission이 직접 회수했다(관측 2의 사건 순서). 이 연쇄는 관측된 줄 순서를 이어 쓴 것이다.
- **CLAIMS 1.13과의 관계(보고만, 수정 없음)**: [TASK63](TASK63.md)이 올린 사용자 결정 — [paper/CLAIMS.md](../../paper/CLAIMS.md) 1.13·원고 §3의 "the next admission has already chosen its victim" 문장 재검토 — 에 대해, 이번 TASK는 **admission 경로가 victim을 고르는 경우가 실재함**을 보였다(연속 admission 조건). **즉시 복귀 조건 자체는 여전히 재지 않았으므로** 1.13의 결론은 이번에도 판정하지 않는다. 판단은 사용자다.

## 확인되지 않은 사항

- **Q3 — admission이 회수하지 못하는 경우의 처리** (`UNKNOWN`). 5/5가 `P1`이라 관측되지 않았다. 소스상 inactive block이 없으면(`select_blocks_for_eviction`가 빈 목록) `can_allocate`가 거짓을 돌려주고 요청은 waiting에 남지만(`optimum_scheduler.py:383-385`), 실행에서 확인하지 않았다.
- **동시 전송(`simultaneous`)에서의 처치 성립 비율과 경로** (`UNKNOWN`). 전환 조건을 충족하지 않아 돌리지 않았다.
- **즉시 복귀 조건에서 victim 선택이 어느 경로에서 일어나는가** (`UNKNOWN`, CLAIMS 1.13 관련).
- **실제 워크로드(agentic, 동시성 > 2)에서 연속 admission이 얼마나 자주 생기고 회수 경로가 어떻게 나뉘는가** (`UNKNOWN`).
- **관측 patch의 시간 관찰자 효과** (`UNKNOWN`, [TASK63](TASK63.md)과 같다). 해석 규칙은 사건 순서만 쓴다.

## 실패 / 무효 시도

- 측정 중 무효·재실행 반복은 없다(5/5 첫 시도).
- **측정 전 계기 점검에서 결함 2건을 잡아 commit 전에 고쳤다.** (i) 합성 로그 생성기가 시각 자리표시자 `T`를 문자열의 첫 `T`와 바꿔 `CAN-ALLOCATE`·`EVICT` 줄이 깨졌다(fixture 결함, 분석 script와 무관). (ii) `P1` 반복의 Q3 부류가 `OTHER`로 표시돼 요약에서 오독될 수 있었다 → `NOT_APPLICABLE`. 둘 다 측정 전이다.
- 측정 후 R01 원로그 발췌를 `sed -n '1010,1046p'`로 뽑다가 빈 출력이 났다. 원인은 필터가 아니라 **줄 번호 체계의 차이**였다 — 분석 JSON의 번호를 파일 줄 번호로 알고 썼는데 파일은 1,022줄뿐이었다(관측 4). 원로그와 판정에는 영향이 없고, 같은 원인의 [TASK63](TASK63.md) 기록 2곳을 관측 4에서 정정했다.

## 연구 원칙에 미치는 영향

1. **부재 관측에는 그 부하가 발생 조건을 만들었는지를 함께 적는다**(발견 5). "0건"은 조건 범위와 함께만 일반화한다.
2. **탐색용 관측 patch는 측정 직후 revert하고 `pristine`을 기록한다**([TASK63](TASK63.md)과 같은 절차, 이번이 두 번째 적용·복구).
3. **로그 줄 번호를 인용할 때는 체계를 밝힌다.** 분석 JSON의 `line`(Python `splitlines()`)과 파일 줄 번호(`grep -n`)는 `\r`이 있는 로그에서 갈린다. TASK 본문에는 파일 줄 번호를 쓰고, JSON 번호를 옮길 때는 변환한다(관측 4).

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **CLAIMS 1.13·원고 §3 기전 문장의 재검토 여부**(사용자 결정, [TASK63](TASK63.md)에서 등록) — 이번 결과로 admission 경로 victim 선택의 실재가 확인됐다. 문장을 판단하려면 즉시 복귀 조건의 직접 관측이 필요하다.
2. **Q3 조건(inactive block이 없는 상태에서의 admission)** — 동시성 8로 pool을 전부 active로 채운 뒤 9번째 요청을 보내는 설계. 새 측정, patch 재적용 필요.
3. **동시 전송 모드와 더 높은 동시성에서의 경로 분포** — 새 측정.

## 재현 정보

- 선등록 commit: **`cb17211`**, 2026-09-12T14:37:51+09:00. **patch 재적용 14:39:53(2분 2초 뒤), 측정 시작 14:40:53(3분 2초 뒤), 종료 14:46:52.** 규칙은 측정 후 바뀌지 않았다
- Raw artifact: `results/npu/stage2/20260912-144017-admission-eviction/` (gitignored)
  - `provenance.txt`, `git-head.txt`(`cb17211`), `manifest.txt`, `patch-{bucket,dummy}-{before,after}.txt`, `rbln-smi-{before,after}.txt`, `start.txt`, `end.txt`, `driver.out`, `order.txt`. `switch.txt`·`reruns.txt` 없음, `failed/` 비어 있음
  - 반복별 `server-R0{1..5}.log`, `probe/admission.R0{1..5}.json`, `probe-R0{1..5}.log`, `class/R0{1..5}.json`, `R0{1..5}-launch.txt`·`-server-start.txt`·`-server-stop.txt`, `smi/`, `done.R0{1..5}`
  - 산출: `admission_eviction.json` (SHA256 `d161634afca20d13013827649eac56e6d208e9ded7aa98194545dad5ae932b11`), `analyze.out`
- 반복 기동 시각: R01 14:40:53, R02 14:42:04, R03 14:43:15, R04 14:44:28, R05 14:45:41. serving lifecycle 5회
- prompt: `experiments/npu/stage2/cliff_prompts.json` — 배경 `trials.B8r0.background[0..7]`, X `trials.B8r0.target`, Y `trials.B8r1.target`. `max_tokens=8`, `temperature=0`, `seed=20260819`, 포화 뒤 idle 1.0 s
- 대상 파일 SHA256: pristine `81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b`, patched `a51f93abab815107dd762da5f9d43cd3314eb12e163c95a0b32779c11ee60856`, patch 파일 `645dc1a8067c2a20ad74e979be5bd44c7b43fc39f893c744df45e9831655b751`
- 측정 후 device 상태: 32 ID 전부 `0.0B / 15.7GiB`, 서버 없음, port 8000 비어 있음
- **환경 분리**: 사용자가 `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert`를 실행했다(출력 `reverted. sha256=81850a8b…`, 대상 파일 mtime 2026-09-12T14:54:25+09:00). 14:54:36의 `status`: `apply_dummy_lifecycle.sh` → **`pristine`** `81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b`, `apply.sh` → **`patched`** `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`([TASK12](TASK12.md) patch만 적용된 상태로 복귀). 출력은 run의 `patch-{dummy,bucket}-after-revert.txt`에 남겼다. 관측 patch가 적용돼 있던 구간은 14:39:53–14:54:25이며, 그 구간에 `results/` 아래에서 이 run 밖에 쓰인 파일은 0개다(`find -newermt`로 확인)
