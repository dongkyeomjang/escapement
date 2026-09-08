# TASK57 — 세션 실행 의미론의 코드 수준 확인

## 상태

DONE

## 판정

read-only 조사다. **새 측정 0, 새 serving 0, device 접근 0.** 코드 5개 질문에 대한
답과 저장 자료로 검증 가능한 것/불가능한 것을 갈랐다. 기존 판정과 수치는 그대로다.

**가장 중요한 두 가지.**

1. **재도착 prompt는 계획된 합성 token이 아니라 직전 응답의 *실제 생성 text*를
   이어붙인다**(`session_runner.py:340`). 따라서 두 조건의 생성 내용이 byte 수준에서
   같은지가 짝 비교의 전제인데, **JSONL이 생성 text를 저장하지 않아 저장 자료만으로는
   검증할 수 없다.** 필요조건 4종은 전부 만족한다(아래 §3).
2. **`plan_summary`는 `text_seed`와 `session_id`를 담지 않는다**(`agentic.py:234-245`).
   [TASK54](TASK54.md)의 G1 게이트가 대조한 plan SHA256은 **길이와 gap의 동일성**을
   증명하며, prompt 본문의 동일성은 `(base_seed, block_id)` 고정에서 **구성상** 따라올
   뿐 해시가 직접 담고 있지 않다.

## 날짜

2026-09-08

## 목적

[TASK54](TASK54.md)·[TASK56](TASK56.md)의 "동일 trace" 주장이 정확히 무엇을 고정하고
무엇을 시스템 결과로 남기는지, 실행 코드에서 확인한다.

## 배경

관련 TASK:

- [TASK54](TASK54.md) — "동일 trace" 짝 비교. G1 plan 해시 게이트
- [TASK56](TASK56.md) — CONVENTIONAL step 열 불변성에 기댄 분해
- [TASK24](TASK24.md) — 층 2 hit 규칙(관측 2)과 outer block 사건 순서(관측 3)
- [TASK11](TASK11.md) — inner block 128 token
- [TASK18](TASK18.md) — per-request 귀속 게이트

## 시작 상태

- Git commit: `5ff9d46`, `git status --short`: `?? .idea/`만
- 조사 대상: `experiments/npu/stage2/session_runner.py`,
  `src/continuum/workload/agentic.py`, `src/continuum/workload/paired.py`
- 대조 자료: [TASK54](TASK54.md) run의 `probe/requests.*.jsonl` 24개 (336 요청)

## 수행 내용

코드를 읽고, 저장 JSONL로 확인 가능한 필요조건을 계산으로 검사했다. 측정하지 않았다.

## 변경된 파일

- `docs/research/TASK57.md` (신규), `docs/research/INDEX.md` (갱신)

코드는 **한 줄도 고치지 않았다.**

## 결과

### 1. 세션 시작 시각 — 계획은 동시, 관측은 12–24 ms 뒤 2–12 ms 퍼짐

기준 시각은 pool 시작 **전에** 한 번 잡는다.

```python
282:    origin = time.perf_counter()
...
345:    with ThreadPoolExecutor(max_workers=len(sessions)) as pool:
346:        list(pool.map(run_session, list(enumerate(sessions))))
```

**시차·지터를 넣는 코드는 없다.** barrier도 없다. `pool.map`은 N개 작업을 한꺼번에
제출하고 `max_workers=len(sessions)`라 모든 세션이 동시에 출발하도록 되어 있다.

그러나 **전송 시각은 tokenizer 작업 뒤에 찍힌다.**

```python
302:            segment = build_exact(tok, turn.new_segment_tokens, turn.text_seed)
303:            prompt = (context + " " + segment).strip() if context else segment
...
307:            sent = time.perf_counter() - origin
```

`build_exact`(`:125-146`)는 목표 token 수에 수렴할 때까지 tokenizer를 반복 호출하는
루프이고, turn 0의 목표는 800–1600 token이다. 그 비용이 `origin`과 `sent` 사이에 들어간다.

**저장 자료 관측** ([TASK54](TASK54.md) 24칸, turn 0):

| 항목 | 값 |
|---|---|
| 첫 전송 `sent_s` | **0.0120 – 0.0139 s** |
| 칸 안 세션 간 퍼짐 (`max − min`) | 최소 **0.0019 s**, 중앙 **0.0052 s**, 최대 **0.0117 s** |

**계획된 시차는 0이고, 관측된 2–12 ms 퍼짐은 thread 생성과 GIL 아래 tokenizer 작업의
직렬화가 만든 시스템 결과다** (원인 귀속은 해석이며 profiling으로 확인하지 않았다).

### 2. CONVENTIONAL의 "즉시 재도착" — `sleep(0)`이 아니라 sleep 호출 자체가 없다

`zero_gaps`는 gap만 0으로 바꾼 같은 plan을 만든다.

```python
171: def zero_gaps(sessions: list[Session]) -> list[Session]:
...
188:                    gap_after_s=0.0,
189:                    text_seed=t.text_seed,
```

전송 루프의 마지막 두 줄이 답이다.

```python
340:            context = prompt + text
341:            held_s = 0.0
342:            if turn.gap_after_s > 0:
343:                time.sleep(turn.gap_after_s)
```

`gap_after_s == 0`이면 **`time.sleep`이 호출되지 않는다.** `sleep(0)`도 아니다.
루프가 곧바로 다음 turn으로 돌아가 `build_exact`(`:302`) → `sent`(`:307`)로 간다.

"완료"의 정의는 **client 측 동기 반환**이다 — `completion()`은 blocking이다.

```python
158:        with urllib.request.urlopen(req, timeout=3600) as resp:
159:            return {"status": resp.status, "body": json.loads(resp.read().decode())}
```

콜백도 event loop도 없다. `done`(`:312`)은 응답 본문을 다 읽은 시각이고, 그 뒤에
`emit`(`:321-339`, `_write_lock` 아래 파일 append)과 `build_exact`가 끼어든다.

**저장 자료 관측** (`turn0.done_s` → `turn1.sent_s`, 84건):

| 격자·N | 최소 | 중앙 | 최대 |
|---|---|---|---|
| 전체 | 0.0005 s | **0.0006 s** | 0.0012 s |

계획 gap 0에 대한 실제 재도착 지연은 **0.5–1.2 ms**다. AGENTIC에서 같은 양(실측 간격
− 계획 gap)은 중앙 3.9 ms, 최대 6.1 ms다.

### 3. 재도착 prompt — 실제 생성 token을 이어붙인다

```python
318:            text = ""
319:            if isinstance(body, dict):
320:                text = body.get("choices", [{}])[0].get("text", "")
...
340:            context = prompt + text
303:            prompt = (context + " " + segment).strip() if context else segment
```

**전자다.** `context_tokens_before()`(`agentic.py:102-114`)는 `plan_summary` 회계용
보조 함수일 뿐 prompt 구성에 쓰이지 않는다. 계획이 정하는 것은 `max_tokens`뿐이다.

```python
310:            r = completion(base, model_id, prompt, turn.generation_tokens,
311:                           args.sampling_seed)
```

sampling은 greedy·고정 seed다.

```python
150:        "model": model, "prompt": prompt, "max_tokens": max_tokens,
151:        "temperature": 0.0, "top_p": 1.0, "seed": seed, "stream": False,
```

`run_sweep.sh`가 `--sampling-seed 20260819`로 고정한다.

#### byte-identity는 저장 자료로 검증할 수 없다

`emit`이 쓰는 field에 **생성 text가 없다**(`:321-339`):

`arm, block_id, session, session_index, turn, request_id, status, sent_s, done_s,
requested_generation_tokens, requested_segment_tokens, gap_after_s, held_s,
prompt_tokens, completion_tokens, cached_tokens, at_utc`

#### 저장 자료로 확인한 필요조건 4종 ([TASK54](TASK54.md) 336 요청)

| # | 조건 | 결과 |
|---|---|---|
| a | `completion_tokens == requested_generation_tokens` | **336/336** — 생성 길이가 계획대로 나왔다(EOS 조기 종료 0) |
| b | 격자 간 `prompt_tokens` 동일 (같은 N·rep·arm·session·turn) | **turn 0 84/84, turn 1 84/84** |
| c | arm 간 `prompt_tokens` 동일 (같은 격자·N·rep) | **turn 0 84/84, turn 1 84/84** |
| d | `p₁ == p₀ + g₀ + seg₁` (계획 회계) | **328/336.** 어긋난 8건은 **전부 정확히 −1** |

**(d)의 8건이 가장 강한 증거다.** 어긋남은 `mb/mb6 × AGENTIC/CONVENTIONAL` 네 조건
전부에서 **같은 두 세션**(N=6 rep1 session 3, N=8 rep1 session 4)에만 나타나며 값도
같은 −1이다. 이 −1은 `prompt + text + " " + segment` 이어붙이기에서 생긴 **token
경계 병합**이고, 병합 여부는 생성 text의 **마지막 문자에 의존**한다. 네 조건에서
같은 자리에 같은 병합이 재현됐다는 것은 그 세션의 생성 text가 적어도 그 경계에서
같았다는 뜻이다.

**그래도 byte-identity의 증명은 아니다.** 위 4종은 전부 필요조건이고, 같은 token 수·
같은 경계를 가지면서 내용이 다른 text가 원리적으로 가능하다.

#### 제안하는 검증 방법 (미실행 — script 변경과 재측정이 필요하다)

1. `emit`의 dict(`:321-339`)에 **`"text_sha256": hashlib.sha256(text.encode()).hexdigest()`**
   한 줄을 추가한다. client 측 관측 전용이며 server·patch·요청 payload를 건드리지
   않는다. 런타임 비용은 무시할 수준이다.
2. 같은 선등록 칸을 같은 `base_seed`·`block_id`·`sampling_seed`로 재실행하고,
   `(session_index, turn)`별 해시를 **격자 간·arm 간**으로 대조한다.
3. 판정: turn 0의 해시가 전건 일치해야 하고(입력이 같으므로), turn 1은 turn 0이
   일치한 세션에 한해 대조한다.
4. 해시가 어긋나면 그것 자체가 결과다 — **batch 구성이 logits에 영향을 주는지**를
   묻는 실험으로 이어진다. 이 저장소에 그 판정 기록은 아직 없다.

이 변경은 script 수정이므로 **선등록과 사용자 승인 뒤에** 한다.

### 4. 첫 요청 완료 시 서버 KV 상태

#### 층 2 (inner block, 128 token — [TASK11](TASK11.md))

[TASK24](TASK24.md) 관측 2가 확정한 규칙은 **prefill이 계산한 prompt token만 캐시되고
decode가 써 넣은 생성 token은 캐시되지 않는다**이다.

```
hits = floor(min(p₀, p₁ − 1) / 128) × 128        (TASK24: 271/271)
```

구현은 `HitFormula.hit_tokens`(`src/continuum/substrate/descriptor.py:156-161`)다.

**[TASK54](TASK54.md) 배치에서 재확인했다** (이번 조사의 유일한 신규 대조):

| 후보 | 적중 |
|---|---|
| **`floor(min(p₀, p₁−1)/128)×128` (prefill 계산분만)** | **95/95** |
| `floor(min(p₀+g₀, p₁−1)/128)×128` (생성분 포함) | 24/95 |

`cached_tokens > 0`인 turn-1 요청 95건 기준이며, 두 후보가 **갈리는 건이 71/95**다.
구체 예 (`mb`/CONVENTIONAL/n6/rep0, session 3): `p₀=1252, g₀=230, p₁=1490`,
관측 `cached_tokens = 1152 = floor(1252/128)×128`. 생성분 포함 후보는 1408을 예측한다.

**따라서 첫 요청이 끝난 시점에 층 2에 남아 재사용 가능한 범위는 그 요청의 prompt
prefix를 128의 배수로 내림한 부분이고, 생성분은 포함되지 않는다.**

turn-1 요청 168건 중 **73건은 `cached_tokens = 0`** 이다 — 규칙이 틀린 게 아니라
층 1에서 축출됐다는 뜻이다.

#### 층 1 (outer slot, [TASK14](TASK14.md)·[TASK24](TASK24.md) 관측 3)

- admission마다 새 outer block을 **하나 할당**한다. cache hit이 나도 마찬가지다
- free block이 없으면 먼저 축출하고, victim은 할당 순서(FIFO) 최고참 **inactive** block이다
- **완료 요청의 block이 evictable로 바뀌는 시점은 다음 admission이 victim을 고른 *뒤*다**
  (`EVICTION` → `FREE-REQUEST` → `ALLOC` 순)

세 번째가 §2의 "즉시 재도착"과 직접 맞물린다 — **gap 없이 돌아오는 세션은 자기
entry를 자기가 축출하지 않는다**([TASK24](TASK24.md) 발견 2).

### 5. "동일 trace"가 고정하는 것의 전수 목록

#### (A) `(base_seed, block_id)`가 결정하는 것 — `generate_sessions`(`agentic.py:116-168`)

세션별 난수원은 `rng = random.Random(derive_block_seed(base_seed, sid))`(`:147`),
`sid = f"{block_id}/s{s}"`(`:146`)이고 `derive_block_seed`는 SHA256이다
(`paired.py:15-18`).

| # | 고정되는 것 | 코드 |
|---|---|---|
| 1 | `session_count` | 인자 |
| 2 | `turns_per_session` | 인자 |
| 3 | turn별 `new_segment_tokens` | `:150` |
| 4 | turn별 `generation_tokens` → 요청의 `max_tokens` | `:151` → `:310` |
| 5 | turn별 `gap_after_s` (마지막 turn은 0) | `:152-157` |
| 6 | turn별 `text_seed` → **prompt 본문 자체** | `:164` → `build_exact` `:125-146` |
| 7 | `session_id` | `:146`, `:167` |

#### (B) 다른 인자가 고정하는 것

| 고정되는 것 | 출처 |
|---|---|
| sampling seed, `temperature=0.0`, `top_p=1.0` | `session_runner.py:150-151` |
| CONVENTIONAL의 gap = 0 | `--zero-gaps` → `agentic.py:171-196` |
| model artifact와 `served_model_id` | `:277-278` |

#### (C) plan 해시가 **담지 않는** 것

```python
234: def plan_summary(sessions: list[Session]) -> dict:
236:     return {
237:         "session_count": len(sessions),
238:         "turns_per_session": [...],
239:         "generation_tokens": [...],
240:         "new_segment_tokens": [...],
241:         "gap_after_s": [...],
242:         "context_tokens_before_last": [...],
243:     }
```

**`text_seed`와 `session_id`가 빠져 있다.** [TASK54](TASK54.md) G1이 대조한 해시는
(A)의 1–5를 덮고 **6·7은 덮지 않는다.** 두 plan이 길이·gap만 같고 prompt 본문이 다르면
해시는 같다. [TASK54](TASK54.md)에서는 `base_seed`와 `block_id`를 같은 값으로 고정해
6·7이 **구성상** 같지만, 그것은 해시가 준 보증이 아니다. 독립 증거는 §3의 (b)(c)(d)다.

#### (D) 시스템 결과로 남는 것 — 고정되지 않는다

| # | 항목 | [TASK54](TASK54.md)에서 관측된 폭 |
|---|---|---|
| 1 | 실제 전송 시각 `sent_s` | 첫 전송 12–14 ms, 칸 안 퍼짐 2–12 ms |
| 2 | 실제 완료 시각 `done_s`, `wall_clock_s` | — |
| 3 | 재도착 지연 (계획 gap 위의 초과분) | CONVENTIONAL 0.5–1.2 ms, AGENTIC 0.8–6.1 ms |
| 4 | 매 순간의 동시 실행 세션 수 → **`[BUCKET]` step 열** | AGENTIC은 격자에 따라 다름(2,001 대 1,970), CONVENTIONAL은 이 배치에서 우연히 동일(1,288) |
| 5 | `cached_tokens` (축출 결과) | turn-1 168건 중 **73건이 0** |
| 6 | `prompt_tokens` (파생값) | 계획 회계와 328/336 일치, 8건 −1 |
| 7 | 생성 text의 내용 | **저장되지 않아 미검증** |
| 8 | `completion_tokens` | 336/336이 계획대로였으나 **보증이 아니라 관측 결과**다 (EOS가 짧게 끝낼 수 있다) |

**(D)4가 [TASK56](TASK56.md)의 전제와 직결된다.** CONVENTIONAL의 step 열 불변성은
설계가 보장하는 성질이 아니라 **그 배치에서 관측된 결과**다.

## 핵심 발견

1. **`universal` — plan 해시는 "같은 계획"의 일부만 담는다.** `plan_summary`가
   `text_seed`를 담지 않으므로, 해시 일치는 **길이·gap의 동일성**이지 **prompt 본문의
   동일성**이 아니다. [TASK54](TASK54.md) G1의 주장 범위를 이 선까지로 읽어야 한다.

2. **`universal` — 짝 비교의 "같은 trace"에는 검증되지 않은 고리가 하나 있다.**
   재도착 prompt가 **실제 생성 text**에 의존하는데(`:340`) 그 text가 저장되지 않는다.
   token 수준 필요조건 4종은 만족하지만 byte-identity는 미확인이다.

3. **`stack` — CONVENTIONAL의 "즉시"는 0.5–1.2 ms다.** `sleep`이 호출되지 않고 같은
   thread에서 동기적으로 이어지며, 그 사이에 있는 것은 `emit`의 파일 append와
   8 token짜리 `build_exact`뿐이다.

4. **`stack` — 세션은 동시에 출발하도록 설계됐고 실제로는 2–12 ms 퍼져 출발한다.**
   `sent`가 `build_exact` **뒤에** 찍히기 때문이며, turn 0의 세그먼트가 800–1600
   token이라 그 비용이 관측 출발 시각에 실린다.

5. **`stack` — [TASK24](TASK24.md) 관측 2의 층 2 hit 규칙이 새 배치에서 재확인됐다.**
   실제 hit 95건 전부가 prefill 계산분만 세는 규칙과 맞고, 판별력 있는 71건에서
   생성분 포함 후보가 기각된다. **첫 요청 완료 시 층 2에 남는 범위에 생성분은 없다.**

## 해석

- **(해석)** 발견 1·2를 합치면 [TASK54](TASK54.md)의 G1은 **필요조건 게이트**로 읽는
  것이 정확하다. 격자가 trace 생성 경로에 들어가지 않는다는 코드 사실(`generate_sessions`
  의 인자에 격자가 없고 `--buckets`는 `immediate` 정책에서 읽히지 않는다)이 본체이고,
  해시 대조는 그 사실을 실행 산출물에서 확인한 것이다. **결론은 바뀌지 않지만 주장의
  근거가 하나가 아니라 둘이라는 점이 정확한 서술이다.**
- **(해석)** 발견 3·4는 `Δp`·device time에 실릴 여지가 거의 없다. 재도착 지연
  0.5–1.2 ms는 decode step 하나(9.5–12.9 ms)보다 작고, 출발 퍼짐 2–12 ms는 step 한둘
  수준이다. 다만 **CONVENTIONAL의 "완전 동기 도착"은 이 크기만큼 이상화**다.
- **(hypothesis)** (d)의 −1 경계 병합이 네 조건에서 같은 자리에 재현된 것은 생성
  text가 같았다는 정황이다. 확증하려면 §3의 해시 field가 필요하다.

## 확인되지 않은 사항

- **두 조건의 생성 text가 byte-identical한지 `UNKNOWN`.** 저장 자료로는 검증 불가.
- **batch 구성(padding 폭)이 logits에 영향을 주는지 `UNKNOWN`.** 이 저장소에 판정
  기록이 없다. 위 해시 field가 그 질문의 첫 관문이다.
- **출발 퍼짐 2–12 ms의 귀속 `UNKNOWN`.** thread 생성·GIL·tokenizer 중 무엇이
  지배적인지 profiling하지 않았다.
- **turn ≥ 3에서 층 2 mapping이 어떻게 연장되는지** — [TASK24](TASK24.md)가 남긴
  `UNKNOWN`이 그대로다. 실측이 전부 2 turn이다.
- **`completion_tokens < requested`가 나는 조건 `UNKNOWN`.** 336/336이 계획대로였을
  뿐 EOS가 언제 걸리는지 재지 않았다.

## 실패 / 무효 시도

없다. 코드 인용과 저장 자료 대조뿐이다.

## 연구 원칙에 미치는 영향

1. **"동일 trace"를 주장할 때 무엇이 해시에 담기고 무엇이 구성상 따라오는지 나눠
   적는다.** 해시가 담지 않는 항목은 별도 근거를 댄다(발견 1).
2. **처치 사이에서 보존된다고 가정하는 양이 실행 산출물에 저장되지 않으면, 저장하도록
   먼저 고친다.** 생성 text가 그 경우다(발견 2).
3. **"즉시"·"동시"처럼 이상화된 말은 관측된 크기와 함께 적는다**(발견 3·4).

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **`text_sha256` field 추가와 재측정** — §3의 검증 방법. script 변경이므로 선등록과
   승인이 필요하다. lifecycle은 최소 8회(1 반복 × 8 구성)면 된다.
2. **[TASK54](TASK54.md) G1 서술의 각주** — 해시가 `text_seed`를 담지 않는다는 사실을
   그 TASK의 `확인되지 않은 사항`에 추가할지 결정한다. **원 판정은 건드리지 않는다.**
3. **논문 서술 점검** — "same trace"를 무엇으로 정의해 쓸지 §5의 (A)–(D) 구분에 맞춘다.

## 재현 정보

- 선등록 commit: **해당 없음** — 새 측정이 없는 read-only 조사다
- 시작 commit: `5ff9d46`
- 인용 파일: `experiments/npu/stage2/session_runner.py`,
  `src/continuum/workload/agentic.py`, `src/continuum/workload/paired.py`,
  `src/continuum/substrate/descriptor.py` (줄 번호는 이 commit 기준)
- 대조 자료: `results/npu/stage2/20260908-133635-grid-paired/{mb,mb6}/probe/requests.*.jsonl`
  (24개 파일, 336 요청)
- 예산: 측정 0, serving lifecycle 0, 재compile 0, device 접근 0
