# GPU 사건 재생 검사 — 선등록 (GPU 지시문 G-05 작업 A)

작성: 2026-10-01. [GTASK12](GTASK12.md).

**이 문서의 성격**
- NPU [TASK72](../TASK72.md) R5′의 GPU판이다. **이 문서를 commit하기 전까지 사건 재생 계산(hit 예측과 관측 대조)은 한 건도 하지 않았다.** 재생 script도 이 commit 뒤에 작성한다.
- commit 전에 본 것은 다음뿐이다.
  - [GTASK11](GTASK11.md) 결과 문서 전체
  - 55 lifecycle의 구조 개수: `[GPFX] LOOKUP` 수 = client 행 수(55/55), `ALLOC_FAIL` 0, 같은 요청의 LOOKUP 중복 0, prompt > 2,048 token 5,417건(chunked prefill 발생), 전체 행 27,652
  - KV events 한 파일의 field 이름(`BlockStored`에 `block_hashes`·`parent_block_hash`·`token_ids`, `BlockRemoved`에 `block_hashes`)
  - 설치된 vLLM 0.22.0 source(아래 §2의 근거 줄)
- 기준은 계산 뒤 완화하지 않는다.

## 1. 대상과 모집단

- run `results/gpu/multiturn/main/20260930T1411Z/`([GTASK11](GTASK11.md))의 **55 lifecycle 전부**(확증 N 20·22·24 × BASE·POOL·POOL+GRID × r0–r4 = 45, 탐색 N 26 × BASE·POOL × r0–r4 = 10).
- **판정 모집단**: lifecycle마다 평가 구간에 보낸(`w0 ≤ sent_s < w1`) turn ≥ 1 요청. GTASK11 §5.1과 같은 집합이다(55 lifecycle 합 약 13,600건).
- 보고 모집단(판정 밖): lifecycle 전체의 turn ≥ 1 요청.
- 관측값: client `cached_tokens`(GTASK11과 같은 규칙: `null`이고 server log에 `enable_prompt_tokens_details`가 켜져 있으면 0). GTASK11에서 server `LOOKUP hit=`와의 불일치는 0이었다.

## 2. 재생 입력과 정렬

**입력으로 쓰는 것**
- server log의 `[GPFX] LOOKUP`·`[GPFX] ALLOC`·`[GSTEP]` 줄의 **log 순서**. 단일 EngineCore process의 실행 순서다. 시각(`t`, `wall`)은 정렬에 쓰지 않는다. client와 server 사이 시계 정렬도 하지 않는다.
- client 행: request id(server id의 접두사로 join, GTASK11과 같은 규칙), session, turn, `prompt_tokens`, `requested_generation_tokens`(= 생성 길이, `ignore_eos`).
- pool 크기: `provenance.json`의 `num_gpu_blocks`(사용 가능 = 그 값 − 1), `max_num_batched_tokens` 2,048, `block_size` 16.

**입력으로 쓰지 않는 것(검증에만 쓴다)**
- `LOOKUP`·`ALLOC` 줄의 `free=`, `hit=`, `scheduled=`, `computed=`, `[GSTEP]`의 `reqs`·`toks`
- KV events(`BlockStored`·`BlockRemoved`)
- client `done_s`·streaming token 시각

**schedule 묶음**: 직전 `[GSTEP]` 뒤부터 다음 `[GSTEP]`까지의 `LOOKUP`/`ALLOC` 줄은 그 다음 `[GSTEP]`을 만든 schedule 호출의 admission이다(GTASK03 사상 375/375, GTASK11 가격 채널과 같은 규칙).

## 3. 재생 의미론 (GPU 정확 의미론, 판정 대상)

근거는 설치된 `vllm 0.22.0` source다(경로는 `site-packages/vllm/v1/`).

1. **pool**: block 1 … N−1을 id 순서로 free queue에 둔다. block 0은 null block이며 쓰지 않는다.
2. **한 schedule 호출**(`core/sched/scheduler.py:366` 이후):
   1. 해제 시점이 된 요청을 먼저 반납한다(규칙 5).
   2. running 요청을 admission 순서로 돈다. budget이 0이면 멈춘다.
      - 마지막 생성 token이 이미 schedule되고 그 출력이 아직 처리되지 않은 요청은 건너뛴다(`:372–383`, async 건너뛰기).
      - prefill 중이면 `min(남은 prompt, budget)`, decode 중이면 1 token.
      - 필요한 block을 할당한다: `ceil(computed 후 token 수 / 16)`개가 될 때까지 free queue 머리에서 꺼낸다.
   3. 이 묶음의 admission(관측 `LOOKUP` 순서): **조회** — 같은 세션의 block key `(session, j)`가 j = 0부터 연속으로 캐시에 있는 만큼, 최대 `floor((prompt − 1)/16)`개. hit block을 **touch**(ref 증가, free queue에서 제거)한 **뒤** 새 block을 할당한다(조회 후 할당, hit 선보호; `:594 → :721`). 예측 hit token = hit block 수 × 16. 이번 schedule에 `min(prompt − hit, budget 남은 양)` token.
   4. 할당할 때 꺼낸 block에 캐시 key가 있으면 그 key를 캐시에서 지운다(축출).
3. **캐시 등록**: 계산된 token으로 가득 찬 block은 key `(session, block index)`로 등록한다. 생성 token도 포함하고, 마지막 sampled token은 계산되지 않는다(요청이 계산하는 token 수 = prompt + 생성 − 1; GTASK02 H5, GTASK04). 같은 key가 이미 캐시에 있으면 두 block을 함께 둔다(조회는 먼저 등록된 쪽).
4. **진행**: prefill이 끝나는 step에서 첫 token을 sampling하고, 그 뒤 step마다 1 token. 마지막(G번째) token을 sampling하는 step을 그 요청의 **종료 step** e로 둔다.
5. **해제 시점(lag 1)**: batch queue 크기 2의 async engine loop(`engine/core.py:469–`)에서 step e의 출력 처리(`update_from_output` → `_free_request`)는 step e+1의 schedule 뒤, e+2의 schedule 전이다. 그래서 종료 step이 e인 요청은 **`[GSTEP]` e+2를 만드는 schedule 호출의 시작에서** 반납한다.
   - 예외(빈 schedule): e+1의 schedule 시점에 running 요청이 모두 async 건너뛰기 대상이면, 그 호출은 아무것도 schedule하지 못한 빈 호출일 수 있고 그 경우 출력 처리가 바로 따른다. 이때 재생은 반납을 `[GSTEP]` e+1의 schedule 시작에 둔다(주 규칙). 이 경우를 **모호 해제**로 표시한다(§4).
6. **반납 순서**: 같은 출력 처리에서 끝난 요청들은 schedule 순서(running 순서)대로, 요청 안에서는 **tail block 먼저**(`single_type_kv_cache_manager.py:350`) free queue 꼬리에 붙인다. ref가 0이 된 block만 붙는다.
7. **축출 순서**: free queue 머리부터(해제 순서 LRU). hit block의 touch는 그 block을 queue에서 빼므로, 나중에 반납될 때 꼬리로 간다.

## 4. `UNDECIDABLE`과 `UNKNOWN`

- **`UNKNOWN`**: (a) 관측 `cached_tokens`를 정할 수 없는 요청(`null`이고 flag 없음), (b) server id join 실패, (c) 같은 세션 이전 turn이 log에 없는 요청, (d) 재생이 구조적으로 진행할 수 없게 된 lifecycle(예: 할당할 free block이 없음 — 관측에서는 preemption 0이었으므로 생기면 재생 오류다)에서 그 시점 이후의 요청.
- **`UNDECIDABLE`**: 모호 해제(§3 규칙 5 예외)가 그 요청의 `LOOKUP`보다 앞서 하나라도 있었고, 그 모호 해제들을 모두 "한 schedule 늦게"(e+2) 둔 대안 재생에서 그 요청의 예측 hit가 주 재생과 달라지는 요청.
- 판정 계산에서 `UNDECIDABLE`·`UNKNOWN`은 일치율의 분모에서 뺀다. 둘의 합은 별도 상한을 둔다(§5).

## 5. 판정 기준

- lifecycle ℓ의 **정확 일치율** `a_ℓ` = (예측 hit token = 관측 `cached_tokens`인 요청 수) / (판정 모집단 − `UNDECIDABLE` − `UNKNOWN`).
- lifecycle ℓ의 **결정 불가 비율** `u_ℓ` = (`UNDECIDABLE` + `UNKNOWN`) / 판정 모집단.
- **`PASS`** ⇔ 55 lifecycle 모두 `a_ℓ ≥ 0.95` **그리고** 모두 `u_ℓ ≤ 0.05`.
- **`FAIL`** ⇔ 그 밖. 원 기준의 실패는 lifecycle별 수치와 함께 보고한다.
- 함께 보고(판정 밖): 이진 일치(`hit > 0` 여부) 비율, 55 lifecycle 합산 일치율, cell별 합산, **N24 BASE·N26 BASE를 따로**, 보고 모집단(lifecycle 전체)의 일치율.

## 6. 재생 무결성 지표 (보고, 판정 밖)

재생 상태가 관측과 같은 궤적에 있는지 보여준다. 입력으로 쓰지 않은 관측과 비교한다.
- `[GSTEP]`마다 (재생 schedule 요청 수, 재생 token 수) = (관측 `reqs`, `toks`)인 비율
- `LOOKUP`마다 재생 free block 수 = 관측 `free=`, `ALLOC`마다 같은 비교(`scheduled=`, `computed=` 포함)
- KV events: `BlockStored` chain(`parent_block_hash`)으로 hash를 `(session, block index)`로 사상한 뒤, 관측 `BlockRemoved`(캐시에 있던 것만)의 순서열과 재생 축출 순서열의 일치(전체 개수, 같은 위치 일치 비율)
- 이 지표가 1이 아니어도 판정 기준은 바뀌지 않는다. 대신 불일치 범주 (v)의 근거로 쓴다.

## 7. 불일치 범주 (사전 고정)

판정 모집단의 불일치 요청마다 아래 대안 재생을 **한 규칙씩만** 바꿔 돌리고, 관측 값을 재현하는 첫 범주를 이 순서로 붙인다.

| 순서 | 범주 | 대안 재생(나머지 규칙은 §3 그대로) |
|---|---|---|
| (i) | 해제 시점 | 모든 반납을 lag 0(`[GSTEP]` e+1의 schedule 시작) 또는 lag 2(e+3). 둘 중 하나라도 재현하면 이 범주 |
| (ii) | 조회·할당 순서 | 새 block을 먼저 할당한 뒤 조회(NPU 순서, hit 선보호 없음) |
| (iii) | 축출 순서 | 할당 순서 FIFO(첫 할당 admission 순, 요청 안 tail 먼저; GTASK09 sim FIFO와 같은 key) |
| (iv) | 요청 안 반납 순서 | head block 먼저 반납 |
| (v) | 생성 token 캐시 | prompt token으로 가득 찬 block만 등록 |
| (vi) | 상태 이탈 | 위 대안 어느 것도 재현하지 못하고, 그 요청의 `LOOKUP`에서 재생 free 수 ≠ 관측 `free=` |
| (vii) | 기타 | 그 밖 |

- 범주 (i)–(v)는 **어떤 의미론 규칙이 틀렸는가**의 후보이고, (vi)은 재생 궤적이 관측에서 벗어난 경우(입력 해석 또는 구현 문제)다.
- 모든 불일치 요청을 범주와 함께 저장한다.

## 8. 결론 규칙 (사전 고정)

- **`PASS`**: GPU 정확 의미론(§3)이 관측 사건 순서 위에서 요청 단위 hit를 재현한다. 그러면 **sim LRU의 붕괴 과소 예측(GTASK11 발견 4)은 의미론 오류가 아니라 동역학 오류**(시뮬레이터 안의 시간 진행·대기열·admission 순서)로 결론짓는다.
- **`FAIL`**: 불일치를 §7 범주로 나눠, 가장 많은 의미론 범주를 "틀린 규칙 후보"로 보고한다. (vi)이 지배적이면 의미론이 아니라 재생 입력·구현의 문제로 보고하고 결론을 `INCONCLUSIVE`로 둔다(의미론 대 동역학을 가르지 못함).

## 9. 예측

- `PASS`. 55 lifecycle 모두 `a_ℓ ≥ 0.98`, 합산 ≥ 0.99를 예상한다. 근거: GTASK11의 부분 hit 비율(0.9–7.4 %)과 고아 축출 0이 §3 규칙의 서명과 맞았다.
- 불일치가 있다면 (i) 해제 시점과 (vi) 상태 이탈에 몰릴 것이다(모호 해제, chunked prefill 경계).
- `UNDECIDABLE`은 lifecycle당 1 % 미만, `UNKNOWN`은 0을 예상한다.

## 10. 구현 오류 처리

- 재생 script는 이 commit 뒤에 쓴다. 첫 실행 결과를 전부 보존한다.
- **§6 무결성 지표가 §2·§3의 명세와 script가 다르다는 것을 보여주면**(명세 위반 구현 오류) 고칠 수 있다. 그때는 고친 내용, 고치기 전·후 판정 수치를 모두 보고한다. **명세(§3) 자체는 바꾸지 않는다.** 명세를 바꾸는 재생은 판정 밖 탐색으로만 보고한다.
