# TASK72 — 모형 v0 선등록 개정과 기존 데이터 대조(R1–R5′)

## 상태

DONE

## 날짜

2026-09-29

## 판정

| 항목 | 성격 | 판정 | 사전 예측 대비 | 핵심 수치 |
|---|---|---|---|---|
| **R1** | 확증 | **`PASS`** | 적중 (전건 일치 예측) | P1 29/29, P2 36/36, P3 140/140, P4 140/140 (admission 경로 예측 5건 = TASK64 5건) |
| **R2** | 모형–시뮬레이터 일관성(측정 아님) | **`CONSISTENT`** | 적중 | 4 배경 크기 × B 0..130 = 524칸 불일치 0. 문턱 121/124, 61/62, 31/31, 16/16 |
| **R3** | 확증(고정점 필요조건) | **`PASS (EXACT)`** | 적중 (R3a EXACT 예측, R3b PASS 예측보다 강함) | DP 격자 = G\* (R3a·R3b 모두). regret 0, E(h) 0.0285 / 0.0298. 원 기준도 PASS. R3c 시작점이 고정점 |
| R4 | 탐색 | 판정 없음 | **빗나감** ("대부분 TVD>0.3", "평균 과소" 예측) | 17 cell, TVD 중앙값 0.248, >0.3은 5개. 평균 running 과소 8, 과대 9 |
| R5 | 탐색 | 판정 없음 | 부분 적중 | 126 cell, 평균 절대오차 binomial 1.08 / poisson 1.12 요청/cell. TASK50 N=6에서 관측 60 대 예측 36 |
| **R5′** | 확증 | **`PASS`** | 적중 (≥ 0.97 예측) | 1,298/1,298 일치(7 run 모두 1.000). UNDECIDABLE·UNKNOWN 0. 불일치 0 → 범주 (i)(ii)(iii) 모두 0. RESERVED 0.847 |

**선후 관계**: 선등록 초판 `8c107a0`(16:02:52) → 개정 1 `1728f0d`(**2026-09-29 16:25:38 +0900**) → 대조 계산 첫 실행 **16:29:09 +0900**. 개정 1 이전에는 데이터 형식·provenance 확인만 했다(§시작 상태). 기준은 계산 후 바꾸지 않았다.

**측정 0, device 접근 0, compile 0.** 모형 코드(`src/continuum/model/`)·시뮬레이터·`session_runner.py` 변경 0.

## 목적

Advisor 지시문 02를 집행한다. D1–D3 결정과 기준 강화를 **계산 전에** 선등록에 반영하고, [TASK71](TASK71.md)이 등록한 대조 R1–R5와 확증 대안 R5′를 계산한다.

## 배경

관련 TASK:

- [TASK71](TASK71.md) — 모형 v0와 선등록 초판 [MODEL_V0_RETRO_PREREG.md](MODEL_V0_RETRO_PREREG.md)
- [TASK14](TASK14.md), [TASK15](TASK15.md), [TASK58](TASK58.md), [TASK63](TASK63.md), [TASK64](TASK64.md) — R1 데이터
- [TASK29](TASK29.md) — R2 비교 대상(시뮬레이터 절제)
- [TASK34](TASK34.md), [TASK35](TASK35.md), [TASK36](TASK36.md), [TASK61](TASK61.md) — R3 선정 격자·TUNED arm·ledger
- [TASK19](TASK19.md), [TASK20](TASK20.md), [TASK23](TASK23.md), [TASK25](TASK25.md), [TASK52](TASK52.md), [TASK53](TASK53.md) — R4(원고 Table I) 데이터
- [TASK40](TASK40.md), [TASK50](TASK50.md), [TASK54](TASK54.md) — R5·R5′ 데이터
- [TASK24](TASK24.md) — 완료 block의 evictable 전환 지연(이번에 판별)
- [TASK69](TASK69.md) — dummy block 시뮬레이터 스위치(`RESERVED` 읽기)

## 시작 상태

- HEAD `64dc6e6`, `git status --short`: `?? .idea/`만
- 개정 1 작성 전에 한 확인(계산 아님):
  - `session_runner.py` 이력 5개 버전 전부 `at_utc`는 `done` 직후·`emit` 직전
  - 대상 server 로그 160/160에 `enable_prompt_tokens_details: True`
  - TUNED artifact `Qwen3-4B-rbln-b16-s8192-d4-mb16`의 `rbln_config.json`: `batch_size 16`, `kvcache_num_blocks 16`, `decoder_batch_sizes [16,10,8,6,4,1]`, mtime 08-23 17:09:59(두 run 이전)
  - server 로그에 `[PFX] [FREE-REQUEST]`가 사건 순서로 있어 client 시각 없이 판정 가능함을 확인
- Python 3.10.12, device 미사용

## 수행 내용

1. **선등록 개정 1**(`1728f0d`): D1 원고 대응표, R3 기준 강화(격자 의존 regret ≤ 0.25·E(h)), R5′ 확증 채택(server 사건 순서 재생, UNDECIDABLE/UNKNOWN 5 % 상한, 불일치 범주), B4 독립 가정의 방향 주석, INDEX 결정 4에 TASK29 GPU block 문턱 정정.
2. 대조 스크립트 [`model_v0_retro.py`](../../experiments/npu/analysis/model_v0_retro.py) 작성·실행. `continuum.model`은 import만.
3. 판정 요약표 M01–M05를 `make_tables.py`에 등록하고 전체 재생성(표 27개, 대조 220건, 불일치 0; 기존 22개 표 파일은 byte 불변).

## 변경된 파일

선등록 개정 commit `1728f0d`:

- `docs/research/MODEL_V0_RETRO_PREREG.md` (§8 개정 1), `docs/research/MODEL_V0.md` (B4 가정 주석), `docs/research/INDEX.md` (결정 4)

기록 commit:

- `experiments/npu/analysis/model_v0_retro.py` (신규)
- `experiments/npu/analysis/make_tables.py` (M01–M05 등록)
- `results/tables/M01–M05.{md,csv}` (신규), `results/tables/README.md`, `results/tables/manifest.json`
- `docs/research/TASK72.md` (신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_retro.py --items r1,r2,r3,r4,r5p,r5
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

**실행 경위**: 첫 실행(16:29:09)은 r1 단독. r2·r3 호출에서 r3가 ledger 키 이름(`rows`) 오류로 멈춰 고친 뒤 16:29:32 재실행했고, r4는 TASK19 pilot의 meta 파일명(block 접미사 없음) 때문에 빈 입력으로 멈춰 파일명 패턴을 고친 뒤 16:29:54 재실행했다. r5p·r5는 16:30:03에 한 번 돈 뒤, **선등록 §8.3에 등록돼 있었으나 첫 구현에서 빠진** 보조 닫힌 형태 계산과 실패 원인 분류를 추가해 16:31:04에 다시 돌렸다. **판정 기준·주 판정 입력은 어느 수정에서도 바뀌지 않았고**, 주 판정 수치(1,298/1,298)는 두 실행에서 같다.

## 결과

Population·unit·source: R1은 server EngineCore 로그(순차 29 + 동시 시작 2 + 연속 admission 5 trial, 축출 140건). R5′는 7개 run 디렉터리의 turn ≥ 1 요청 1,298건, 관측은 client `usage.prompt_tokens_details.cached_tokens`와 server `[CACHE-HIT]`/`REUSED>0` 교차. device scope `rbln0`–`rbln3`(원 측정의 것).

- `requested_condition`: 기존 artifact 재분석
- `observed_condition`: 등록된 모든 파일이 읽혔고 결손 0
- `condition_reached`: `YES`

### R1 — P1–P4

| 묶음 | trial | P1 | P2 (예측=관측) | P3 | P4 |
|---|---|---|---|---|---|
| [TASK14](TASK14.md) | 9 | 9/9 (m ≤ 6 생존, B7·8·9·16·33·49 소멸; B33·B49는 resume ALLOC 전 target OB 축출로 관측) | 9/9 (0,0,1,2,3,4,11,28,44) | 93/93 | 93/93 |
| [TASK15](TASK15.md) | 12 | 12/12 | 12/12 | 18/18 | 18/18 |
| [TASK63](TASK63.md) A | 8 | 8/8 | 8/8 | 12/12 | 12/12 (전부 DUMMY 괄호 안) |
| [TASK63](TASK63.md) B (동시 시작) | 2 | — | 2/2 (8 → 1) | 2/2 | 2/2 (n=8→7 이탈 첫 step) |
| [TASK64](TASK64.md) | 5 | — | 5/5 (10 → 3) | 15/15 | 15/15 — admission 경로 예측 5건이 전부 DUMMY 괄호 밖·직후 ALLOC, dummy 예측 10건은 괄호 안 |

불일치 0, UNKNOWN 0. 원고 S3의 `max(0, m−5)` 21/21과 같은 21 trial이 P2 21/21이다.

### R2

모형 hit token = `GranularPool` hit token, 524/524. 시뮬레이터 문턱이 [TASK29](TASK29.md) 기록(61/62, 31/31, 16/16)과 같고 500 token은 121/124(새 값, 모형 예측과 같음).

### R3

| h 출처 | DP 격자 | regret_rel | E(h) | 0.25·E | 판정 | 원 기준 |
|---|---|---|---|---|---|---|
| R3a 시뮬레이터(탐색 seed 27칸, config_search 입력 그대로) | (1,4,6,8,10,16) | 0 | 0.02851 | 0.00713 | PASS (EXACT) | PASS |
| R3b 실측 TUNED 12 파일 합 | (1,4,6,8,10,16) | 0 | 0.02978 | 0.00745 | PASS (EXACT) | PASS |
| R3b N=10 (보고만) | (1,3,5,8,10,16) | 0.00059 | 0.04946 | — | (PASS 상당) | |
| R3b N=6 (보고만) | (1,2,4,5,6,16) | 0.01399 | 0.02420 | — | (FAIL 상당) | |
| R3b N=8 (보고만) | (1,3,5,6,8,16) | 0.00743 | 0.01476 | — | (FAIL 상당) | |

R3c: DP 최적이 G\*와 같아 **시작점이 고정점**이다(반복 0회, 순환 없음). G\*의 ledger 탐색 순위 1.

### R4 (탐색)

cell별 TVD(AGENTIC): TASK19 N8 0.348, N16 0.308 / TASK20 N4 0.121, N6 0.186, N8 0.301, N10 0.248, N12 0.227, N16 0.290 / TASK23-2a N3 0.126, N5 0.211, N7 0.348, N8 0.296 / TASK23-2b N6 0.260, N8 0.313 / TASK25 N3 0.246, N4 0.242, N7 0.241. 평균 running 차(예측−관측)는 −0.36 ~ +1.63이고, N ≥ 12에서 +0.94 ~ +1.63으로 과대, N ≤ 5에서 대체로 과소다. 전체 표는 `results/tables/M04.md`. 모형 주기 c = 4.47–7.93 s.

### R5 (탐색)

run × N 합계(관측 대 binomial/poisson): TASK35 N6 51 대 46.9/46.4, N8 57 대 58.3/57.8, N10 63 대 69.8/68.9. TASK40 N6 69 대 63.6/63.9, N10 90 대 101.3/101.6. **TASK50 N6 60 대 36.3/37.0**(가장 큰 차). TASK20 N12 0 대 6.7/8.3, N16 0 대 3.8/6.4. 전체는 `M05.md`. **TASK50 10회 반복 재사용 수**: N=6은 10회 모두 6/6(분산 0), N=8은 `[6,5,6,6,6,6,5,6,6,5]` (평균 5.7, 분산 0.21) — 원고 III-B-c "7회 6/8·3회 5/8"과 같다.

### R5′

| run | 요청 | 일치 | 일치율 | RESERVED | 지연 release | 닫힌 형태 보조 |
|---|---|---|---|---|---|---|
| [TASK20](TASK20.md) nslots-sweep | 432 | 432 | 1.000 | 0.894 | 0.931 | 0.822 |
| [TASK50](TASK50.md) null-channel | 140 | 140 | 1.000 | 0.529 | 1.000 | 0.614 |
| [TASK35](TASK35.md) final-confirm | 216 | 216 | 1.000 | 0.931 | 0.963 | 0.931 |
| [TASK36](TASK36.md) n6-reconfirm | 54 | 54 | 1.000 | 0.870 | 1.000 | 0.926 |
| [TASK40](TASK40.md) batch-saturation | 288 | 288 | 1.000 | 0.951 | 0.969 | 0.931 |
| [TASK54](TASK54.md) mb | 84 | 84 | 1.000 | 0.667 | 0.738 | 0.690 |
| [TASK54](TASK54.md) mb6 | 84 | 84 | 1.000 | 0.738 | 0.798 | 0.750 |
| **합** | **1,298** | **1,298** | **1.000** | 0.847 | 0.934 | 0.833 |

관측 재사용 774, 실패 524(판정이 자명하지 않다). UNDECIDABLE 0, UNKNOWN 0(client `cached_tokens`와 server 조회 결과가 1,298건 전부 일치).

**원고 III-B-a의 재사용 실패 73건**: 단일 묶음(run, run×arm, run×arm×N)으로 73인 것은 없고, **run 쌍으로는 TASK54 mb + mb6(34 + 39 = 73)이 유일**하다. 원고 Table VI 절이 TASK54이므로 이 73건을 후보로 본다(Advisor 확인 필요). 그 73건의 모형 측 원인: 창 안 할당 수 초과(`1 + A > C`) 51건, dummy pre-evict로만 설명되는 것 22건(mb 12, mb6 10), `K_pin`·기타 0건. 축출 경로는 dummy 70건, admission 3건. 73건 전부 사건 재생이 실패를 예측했다.

전 모집단 실패 524건의 원인: 창 안 할당 수 초과 437, dummy pre-evict 61, 기타(닫힌 형태는 생존 예측, admission 경로 축출) 26(TASK20 19, TASK40 7). 모두 사건 재생은 맞혔다.

### `at_utc`·`--enable-prompt-tokens-details` run별 확인

| run | 시작 | 당시 runner commit | `at_utc` 의미 | prompt-tokens-details |
|---|---|---|---|---|
| nslots-sweep | 2026-08-20 16:52 | `f9cc106` | 응답 수신 직후 | 44/44 True |
| final-confirm | 2026-08-23 18:35 | `f61bafe` | 같음 | 27/27 True |
| n6-reconfirm | 2026-08-24 16:00 | `f61bafe` | 같음 | 9/9 True |
| batch-saturation | 2026-08-24 22:24 | `f61bafe` | 같음 | 36/36 True |
| null-channel | 2026-09-01 02:03 | `f61bafe` | 같음 | 20/20 True |
| grid-paired mb·mb6 | 2026-09-08 13:36 | `f61bafe` | 같음 | 24/24 True |

runner commit은 run 디렉터리에 기록이 없어 **시작 시각 직전의 runner commit으로 추정**했다(`PARTIAL`). 의미는 5개 이력 버전 모두 같으므로 추정 오차가 결론을 바꾸지 않는다. R5′는 `at_utc`를 쓰지 않았다.

## 핵심 발견

1. **`universal`** — **FIFO-by-allocation pool의 생존은 ALLOC·FREE·decode step 순서만으로 재생되는 (B1-1)로 7개 run의 1,298 재도착 전부와 순차 36 trial의 축출 140건 전부를 맞힌다.** 결과 줄을 입력에 쓰지 않은 재생이다. 재생 규칙(가장 이른 inactive 축출, 할당 후 조회)은 FIFO 대기열의 산술이라 기판 상수에 의존하지 않는다. 다만 결과를 알고 세운 모형이라 blind 예측이 아니다.
2. **`stack`** — **이 기판에서 완료된 요청의 항목은 FREE-REQUEST 즉시 evictable이 된다.** 즉시 전환 재생 1.000 대 "다음 admission의 victim 선택 뒤" 지연 재생 0.934(TASK54 mb 0.738). [TASK24](TASK24.md)가 세우고 시뮬레이터가 구현한 지연 규칙은 이 데이터와 맞지 않는다. [TASK63](TASK63.md) B.b0 관측과 일치한다.
3. **`stack`** — **dummy block은 lookup 시점에 slot을 쥐지 않는다(`PRE_EVICT`).** `PRE_EVICT` 1.000 대 `RESERVED`([TASK69](TASK69.md) 스위치 방식) 0.847. TASK69에서 스위치가 예측 오차를 키운 것과 방향이 같다.
4. **`universal`** — **(B1-1)의 lookup 시점 닫힌 형태는 동시 부하에서 부족하다(0.833).** 오답 217건이 양방향이다 — 생존인데 소멸 예측 130건(T 자신이 active인 동안 일어난 축출은 더 새 inactive 항목에 떨어져 T를 비켜 간다), 소멸인데 생존 예측 87건(`K_pin`은 lookup이 아니라 **축출 순간**에 세야 한다). 대기열 산술이므로 기판 무관하다. **모형 수정 필요 지점**이다(수정하지 않음).
5. **`stack`** — **G\* `(1,4,6,8,10,16)`은 자기 h(시뮬레이터·실측 모두)에 대한 decode padding 최선 응답이고, G_ref 대비 격자 의존 비용 이득 E(h)는 2.9–3.0 %다.** 다만 N별로 나눈 h에서는 N=6·8의 최적 격자가 다르다(regret 1.4 %·0.74 %) — G\*는 N을 합친 h의 최적이다. 격자 값은 이 인스턴스의 것이다.
6. **`class`** — **동시 시작 2-turn workload의 재사용은 steady-state renewal 계수 법칙으로 설명되지 않는 구간이 있다**(TASK50 N=6: 관측 60/60, 예측 36–37). 동시 시작이 도착을 정렬시켜 창 안 할당 수를 renewal보다 작게 만든다. 근거: 동시 시작이라는 workload 설계 범주의 성질이며 slot 수와 무관하다. 확률적 확장은 steady-state 실험에서만 검증할 수 있다.

## 해석

- R1·R5′의 완전 일치는 **사건 재생 = 모형 명세의 정확한 구현**이 이 기판의 FIFO pool을 기술한다는 뜻이다. SIGMETRICS 원고에서 "모형"으로 내세울 수 있는 것은 닫힌 형태가 아니라 이 재생 규칙이며, 닫힌 형태는 T가 창 내내 inactive인 순차 부하에서만 정확하다(R1 P1).
- R5′는 원고가 한계로 남긴 "재사용 실패 원인을 건별로 판정하지 않았다"를 해소한다 — 524건 전부 사건 재생으로 설명되며, 대부분(437)은 창 안 할당 수 초과, 61건은 dummy의 선축출 시점, 26건은 T 보호·`K_pin` 시점 효과다.
- 지연 release와 `RESERVED`가 틀렸다는 것은 **시뮬레이터 두 곳(`OuterBlockPool` 지연 release, TASK69 dummy 스위치)이 이 기판의 의미론과 다르다**는 뜻이다(hypothesis: 시뮬레이터의 계통적 양의 예측 오차([후속 연구](INDEX.md#후속-연구) 8번)와 관련될 수 있다 — 확인하지 않았다).
- R4의 사전 예측이 빗나간 것은 원고 workload의 관측 h가 예상보다 steady state에 가깝다는 뜻이다(TVD 중앙값 0.25). 그래도 N ≥ 12에서 B2가 평균 running을 과대 예측하는 계통 편향이 있다 — 대기열(n > M)의 FCFS가 곱 형태 가정 밖이라는 명세 (ii)1과 맞다.

## 확인되지 않은 사항

- 원고 III-B-a의 73건이 TASK54 mb+mb6인지(유일한 run 쌍이지만 원고 확인 필요)
- run별 runner commit(시작 시각 기준 추정, `PARTIAL`)
- 지연 release·RESERVED 교정이 시뮬레이터 예측 오차를 줄이는지(계산하지 않음)
- 응답에 `prompt_tokens_details`가 실제로 없던 행의 존재(jsonl에서 구별 불가. 이번에는 server 교차로 1,298건 일치)

## 실패 / 무효 시도

- 스크립트 첫 구현의 버그 2건(ledger 키, meta 파일명 패턴)은 판정 전에 멈춰 고쳤다. 등록된 보조 계산 2개(닫힌 형태, 실패 원인 분류)가 첫 구현에서 빠져 추가 후 재실행했다. 판정 기준·주 판정 입력은 바뀌지 않았다.

## 연구 원칙에 미치는 영향

- **KNOWN_PITFALLS 추가 후보(보고만)**: `session_runner.py`의 `details.get("cached_tokens", 0)`은 `prompt_tokens_details`가 없을 때 관측 불가 값을 0으로 채운다(원칙 14 충돌). 이번 run들은 server 인자와 로그 교차로 영향이 없음을 확인했으나, 새 runner나 플래그 누락 run에서는 조용히 "재사용 0"이 된다. runner는 이번 지시에 따라 고치지 않았다.
- 판정에 client 시각을 쓰지 않고 server 사건 순서만 쓰는 방식이 per-request 귀속의 새 채널로 쓸 만하다(원칙: 동시 workload에서 counter 증분 귀속 금지와 양립).

## 다음 작업

권고(사용자·Advisor 지시 없이 착수하지 않음):

1. **모형 수정 (v1)**: B1 결정론적 핵심을 사건 재생 규칙으로 정식화하고, 닫힌 형태는 "T가 창 내내 inactive"인 조건부 형태로 격하. `K_pin`을 축출 순간 정의로, T 자신의 active 구간 보호 항 추가. release 규칙 = 즉시(이 기판). descriptor에 `release_rule`, `dummy_mode`, `resume_allocates_first` 필드 추가.
2. **시뮬레이터 교정 검토**: `OuterBlockPool` 지연 release와 TASK69 `reserved` 방식을 관측 의미론(즉시 release, PRE_EVICT)으로 바꾸는 스위치를 두고 예측 오차 변화를 계산(선등록 대상).
3. **multi-turn steady-state 실험 설계**의 ramp·drain 제안: 모형 주기 c가 4.5–7.9 s였으므로 **처음 3c(약 15–25 s) 또는 모든 세션이 2 turn을 마칠 때까지 중 늦은 쪽**을 warm-up으로 버리고, **첫 세션이 마지막 turn을 보낸 시점 이후**를 drain으로 버린다. 세션당 turn 수는 평가 구간에 주기 ≥ 10개가 남도록 정한다.

## 재현 정보

- 대조: `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_retro.py --items r1,r2,r3,r4,r5p,r5` (산출 `results/npu/stage3/model_v0_retro/{r1,r2,r3,r4,r5,r5p,run_meta}.json`, 비추적)
- 표: `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` → `results/tables/M01–M05`
- gap 파일 SHA256 `25bb1b0f…`(R3a), ledger `20260911-153800-config-search-rerun/run-a/ledger.json`
- **선등록 commit: 초판 `8c107a01d09fd6327cd7457e5e7d64ad2abf0b80` (2026-09-29 16:02:52 +0900), 개정 1 `1728f0d7322ca62093371f2c79486d7e1eefed61` (2026-09-29 16:25:38 +0900). 대조 계산 시작 2026-09-29 16:29:09 +0900 — 두 선등록 commit 이후.**
