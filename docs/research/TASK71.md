# TASK71 — 해석적 모형 v0 정식화와 기존 데이터 대조 계획 선등록

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 01 작업 B–D를 집행한다. Stage 3([TASK70](TASK70.md))의 첫 단계로, 관측 규칙(FIFO·시퀀스 단위 slot의 생존 절벽, 격자 정렬, prefill 배타 실행)을 `SubstrateDescriptor` 파라미터만으로 계산되는 **해석적 모형 v0**로 정식화하고, **기존 데이터와 대조하기 전에** 대조 방법·판정 기준·사전 예측을 선등록하며, 대조에 필요한 raw 데이터의 존재를 확인한다.

**측정 0, device 접근 0, compile 0, 대조 계산 0.** 시뮬레이터 동작 변경 0.

## 배경

관련 TASK:

- [TASK14](TASK14.md), [TASK15](TASK15.md) — 순차 생존 문턱(배경 7개에서 소멸), FIFO·할당 순서 축출, 할당 후 조회
- [TASK16](TASK16.md) — `SubstrateDescriptor`와 `survives_gap()`(이번에 일반화한 법칙 후보)
- [TASK20](TASK20.md), [TASK22](TASK22.md) — 동시 부하 sweep, prefill 배타 실행과 stall 항
- [TASK24](TASK24.md), [TASK25](TASK25.md) — 시뮬레이터와 예측력. 완료 block의 evictable 전환 지연
- [TASK29](TASK29.md) — `GranularPool` 절제 문턱 61/31/16, GPU 측 source 인용, chunked prefill 절제
- [TASK58](TASK58.md), [TASK63](TASK63.md), [TASK64](TASK64.md) — 회수 산술 `max(0, ALLOC + 1 − 8)`, dummy block 경로, admission 경로 회수
- [TASK61](TASK61.md) — config_search 재실행, 후보 정의와 `--max-buckets` 한 칸 어긋남
- [TASK68](TASK68.md), [TASK69](TASK69.md) — 재도착 되먹임 스위치, dummy block 시뮬레이터 스위치

## 시작 상태

- branch `main`, HEAD `362dd2f`([TASK70](TASK70.md)), `git status --short`: `?? .idea/`만
- `vllm 0.22.0+cpu`(source-read만), Python 3.10.12, device 미사용

## 수행 내용

1. **B1–B4를 새 패키지 `src/continuum/model/`로 구현**했다(accelerator-neutral, RBLN 상수 없음). 명세는 [MODEL_V0.md](MODEL_V0.md) — 구성요소마다 (i) 수식 (ii) 가정 (iii) 입력 파라미터와 값의 출처 층 (iv) 예측하지 않는 것.
2. **vLLM의 조회·할당 순서를 source-read로 확인**했다: `vllm/v1/core/sched/scheduler.py:594`(`get_computed_blocks`)가 `:721`(`allocate_slots`)보다 먼저다 — 측정 기판(할당 후 조회)과 반대. 모형 파라미터 `resume_allocates_first`로 반영했다.
3. **합성 입력만으로 정확성 self-check**를 만들고 통과시켰다(아래 결과).
4. **작업 D**: R1–R5에 필요한 raw 데이터를 read-only로 확인했다(subagent 1개가 조사, 핵심 수치 5개를 직접 재확인). 인벤토리는 선등록 문서 §6.
5. **선등록** [MODEL_V0_RETRO_PREREG.md](MODEL_V0_RETRO_PREREG.md)를 모형 코드와 **같은 commit `8c107a01d09fd6327cd7457e5e7d64ad2abf0b80`**(2026-09-29 16:02:52 +0900)으로 commit했다. 대조 계산은 지시문 02에서 수행한다.

## 변경된 파일

선등록 commit `8c107a0`:

- `src/continuum/model/{__init__,survival,occupancy,grid,interference}.py` (신규)
- `experiments/npu/analysis/model_v0_selfcheck.py` (신규)
- `docs/research/MODEL_V0.md` (신규)
- `docs/research/MODEL_V0_RETRO_PREREG.md` (신규)

기록 commit:

- `docs/research/TASK71.md` (신규), `docs/research/INDEX.md` (갱신)

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py   # seed 20260929
```

self-check는 측정 histogram·run·descriptor 상수를 하나도 읽지 않는다(합성 입력은 seed로 생성). 보간 규칙 동일성 검사만 `config_search.descriptor_for`를 **합성 descriptor**에 대해 호출한다.

모형 인스턴스 값(선등록 사전 예측에 쓴 것)은 RBLN descriptor를 모형에 넣어 계산했다 — 이것은 모형의 예측값 산출이지 데이터와의 대조가 아니다.

## 결과

### B3 DP self-check (합성 입력만)

| 항목 | 결과 |
|---|---|
| 합성 입력 수 | 1,200 (top ∈ {4,8,10,12,16} × k ∈ {2,…,6} × h 모양 6종 × 비용 곡선 4종 × 2) |
| 전수 열거와의 일치 | **1,200/1,200** — 최적 비용 동일(상대 1e-9), DP 격자가 동률 최적 집합 안. 유일 최적 1,144건, 동률 56건 |
| 계산 시간 | DP 합 0.043 s, 전수 열거 합 0.417 s (단일 thread) |
| 보간 규칙 | 합성 descriptor 200개에서 `config_search.descriptor_for`와 **bit 동일**(최대 차 0.0) |
| `count_grids(16, 6)` | 1,471 = [TASK61](TASK61.md) batch 16 후보 수 |

### B2·B1 self-check

- B2: 상수 step 비용·prefill 0에서 closed-form 이항 분포와 최대 차 1.7e-16(12 경우). prefill 고정점 잔차 5.5e-13, 수렴.
- B1: 퇴화 창(결정론적)에서 확률식 = 결정론적 부등식 60/60. 두 계수 법칙의 평균 = `(N−1)·w/c`(최대 차 4.5e-14). 합성 pool 순차 문턱 `m ≤ C − 2` 전건 일치.

### 모형 인스턴스 값 (사전 예측의 근거)

- 순차 생존 문턱(C=8, u=1, 선할당): `m* = 6`
- block 단위(C=512, block 128, target 2,000·resume 2,008): 선할당 — 500: 121/124, 1,000: 61/62, 2,000: 31/31, 4,000: 16/16 (첫 손실/전손 B). 조회 후 할당(vLLM) — 125/128, 63/64, 32/32, 16/16
- 순차 축출 수(PRE_EVICT): `max(0, ALLOC + 1 − 8)` — ALLOC 9 → 2, 10 → 3, 35 → 28, 51 → 44

### 데이터 인벤토리 요약 (상세는 선등록 §6)

R1 36 trial 전부 로그 존재(`[OBS]`는 TASK63·64만), R2 산출물 없음(코드로 재계산), R3 ledger 2,077행·gap 파일 SHA 일치·TUNED `[BUCKET]` 12 파일(폭 16 관측 0회), R4 `padding_ratio.json` 17 cell(pooled 행은 합산 필요), R5 6개 run 전부 요청 단위 field 존재(동일 plan 10회는 TASK50만). `UNKNOWN`: 원고 표 ↔ run 대응, `at_utc` 의미, TASK50 파일 수 차이(110 → 149).

- `requested_condition`: 측정 없음
- `observed_condition`: 해당 없음
- `condition_reached`: 해당 없음

## 핵심 발견

1. **`universal`** — **FIFO-by-allocation에서 생존 조건은 `u_T + Σ_창 u_a + K_pin + D ≤ C`이고, T 할당 시점의 빈 slot 수와 T보다 오래된 항목 수가 소거된다.** FIFO 대기열의 산술이므로 기판과 무관하다. 측정 문턱이 배경 크기에 무관하게 개수였던 이유가 이 소거다.
2. **`class`** — **창의 시작은 eviction 순서가 정한다: FIFO-by-allocation은 대상의 할당 시점(자기 prefill·decode 포함), free-queue LRU는 release 시점.** 근거: 대기열 위치가 언제 고정되는가는 설계 범주(할당 순서 대 사용 순서)에서 나오며 특정 상수에 의존하지 않는다. 같은 gap이라도 FIFO 기판은 대상 자신의 체류 시간만큼 창이 길다.
3. **`stack`** — **조회·할당 순서가 두 기판에서 반대다**: 측정 기판은 할당 후 조회([TASK15](TASK15.md)), `vllm 0.22.0` scheduler는 조회(`:594`) 후 할당(`:721`)(source-read). block 단위 문턱이 한 요청분 달라진다(2,000 token 배경 전손 31 대 32). [TASK29](TASK29.md)의 GPU 측 절제 계산은 할당 후 조회를 썼다 — 원문은 고치지 않고 GPU 선등록 때 명시한다.
4. **`stack`** — **관측된 dummy 동작(다음 admission이 dummy slot을 그대로 가져감, [TASK63](TASK63.md) 74/74)을 식으로 옮기면 lookup 시점의 추가 소비는 0이고, 효과는 축출을 한 decode step 앞당기는 것과 run 끝의 trailing 축출 1건이다.** 그 읽기에서는 순차 생존 문턱이 바뀌지 않고 회수 산술 `max(0, ALLOC + 1 − 8)`이 나온다. 반면 [TASK69](TASK69.md)의 시뮬레이터 스위치는 admission 시점 예약이라 동시 부하 lookup에서 유효 용량을 한 칸 줄인다. **두 읽기가 다르다는 것은 식에서 나온 가설이며 데이터 대조는 하지 않았다**(선등록 R5′·D3).
5. **`universal`** — **step 가중 h(n)과 시간 가중 분포는 다르다**(`step_share ∝ time_share / t_step`). `[BUCKET]` 로그와 격자 비용은 step 가중이다. 방법론 사실이다.
6. **`universal`** — **격자 DP는 h에 대한 최선 응답일 뿐 격자–h 고정점이 아니다.** 되먹임이 있는 계에서 선정 격자를 판정하려면 자기 h에 대한 최선 응답인지(필요조건)를 묻는 것이 맞다 — R3의 설계 근거.

## 해석

- 확률적 확장의 두 계수 법칙(binomial, Poisson)은 주기 CV ≤ 1 구간을 괄호로 묶는다. 실측 tool gap은 heavy-tailed([TASK31](TASK31.md))라 그 괄호 밖일 수 있다 — steady-state 실험에서 주기 분산을 재야 하는 이유다(hypothesis).
- B2의 φ 고정점은 배타 prefill이 체류를 늘려 평균 batch 폭을 키우는 효과를 담는다. [TASK29](TASK29.md)의 chunked 전환 device time 증가의 **부호**는 담고 크기는 과소 추정할 것으로 본다(hypothesis, 미검증).

## 확인되지 않은 사항

- 원고 식 (6)·(9), Table I·III·VI·XI·XIII, "S3의 21 run"과 저장소 산출물의 대응(선등록 §7 D1)
- 완료 block의 evictable 전환 시점 규칙([TASK24](TASK24.md) 대 [TASK63](TASK63.md) B.b0)
- vLLM에서 조회로 찾은 block이 같은 admission의 할당 축출로부터 보호되는지(source-read는 순서까지만 확인)
- `at_utc` field의 의미, TASK50 run 파일 수 차이의 원인

## 실패 / 무효 시도

없음. self-check 첫 실행에서 통과했다.

## 연구 원칙에 미치는 영향

- 원칙 16(선등록)의 적용 — 모형이 기존 결과를 알고 세워졌다는 점을 선등록 §0에 명시했다. retro 대조의 통과를 blind 예측 성공으로 보고하지 않는다.
- 원칙 4의 역방향 — 조회·할당 순서처럼 RBLN 의미론이 GPU 예측에 새어 들어가는 지점을 모형 파라미터로 분리했다.

## 다음 작업

- Advisor의 선등록 검토와 D1–D3 결정 → 지시문 02(R1–R5 대조 계산). **사용자·Advisor 지시 없이 착수하지 않는다.**

## 재현 정보

- self-check: `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py --seed 20260929` (0.5 s, exit 0, `SELF-CHECK PASS`)
- 모형 인스턴스 값: `PYTHONPATH=src:experiments/npu/substrate python3 -c "from continuum.model import survival as S; ..."` — `sequential_threshold`, `block_pool_thresholds`, `sequential_eviction_count`에 RBLN descriptor 값을 넣음
- vLLM source-read: `/usr/local/lib/python3.10/dist-packages/vllm/v1/core/sched/scheduler.py:594, :721`
- **선등록 commit: `8c107a01d09fd6327cd7457e5e7d64ad2abf0b80` (2026-09-29 16:02:52 +0900). 대조 계산은 아직 시작하지 않았다** — 측정·대조 시작 시각은 지시문 02 TASK에 기록한다.
