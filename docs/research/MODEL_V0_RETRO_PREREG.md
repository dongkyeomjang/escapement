# 해석적 모형 v0 — 기존 데이터 대조 계획 선등록 (R1–R5)

작성: 2026-09-29, [TASK71](TASK71.md) (Advisor 지시문 01 작업 C). 모형 명세: [MODEL_V0.md](MODEL_V0.md).

**이 문서는 대조 계산 전에 commit한다.** 모형 코드(`src/continuum/model/`)와 같은 commit이다. **이 commit 시점까지 R1–R5의 대조 계산은 한 건도 수행하지 않았다.** 대조 계산은 Advisor가 이 문서를 검토한 뒤 발행하는 지시문 02에서 수행하며, 그때 이 문서의 기준을 완화하지 않는다. 기준 수정이 필요하면 **계산 전에** 새 commit으로 개정하고 개정 이력을 이 문서 끝에 남긴다.

## 0. 공통 규칙

1. **blind가 아닌 것을 명시한다.** B1의 결정론적 핵심과 block 단위 인스턴스는 [TASK14](TASK14.md)·[TASK15](TASK15.md)·[TASK29](TASK29.md)·[TASK58](TASK58.md)·[TASK63](TASK63.md)·[TASK64](TASK64.md)의 **요약 결과를 알고** 세웠다. 따라서 R1·R2의 통과는 "식이 모든 raw run을 빠짐없이 덮는다"는 증거이지 blind 예측 성공의 증거가 아니다. 논문에서도 그렇게 적는다. **raw 사건 단위(개별 축출의 대상 ID·시점)는 이번 정식화에서 읽지 않았다** — R1의 사건 단위 항목은 그 의미에서만 새 검사다.
2. 모형 코드는 commit된 상태로만 쓴다. 대조 스크립트는 `src/continuum/model/`을 import만 하고 수정하지 않는다. 모형 수정이 필요하면 대조를 멈추고 보고한다.
3. 시뮬레이터(`src/continuum/sim/`)의 기본 동작을 바꾸지 않는다.
4. 관측 불가 field는 0으로 채우지 않고 `UNKNOWN`으로 둔다. 데이터 경로·field 존재는 §6 인벤토리가 기준이다.
5. 원고 표 번호(Table I, III, VI, XI, XIII)와 저장소 산출물의 대응은 **원고가 저장소 밖**이라 확인할 수 없다. 아래 대응은 내용 기준 추정이며, 지시문 02 전에 Advisor 확인을 요청한다(§7 결정 D1).

---

## R1 — B1 결정론적 핵심 vs 순차 실험 전 run (확증)

### 데이터 (§6 인벤토리 R1)

| run | TASK | trial | 성격 |
|---|---|---|---|
| `results/npu/stage2/20260819-200800-gap-turnover` | [TASK14](TASK14.md) | 9 (B0,3,6,7,8,9,16,33,49) | 순차 |
| `results/npu/stage2/20260819-204900-cliff-repro` | [TASK15](TASK15.md) | 12 (B5–B8 × r0–r2) | 순차 |
| `results/npu/stage2/20260912-134732-dummy-lifecycle` | [TASK63](TASK63.md) | A 8 (B5–B8 × r0,r1) 순차 + B 2 (8 세션 동시 시작) | `[OBS]` 경로 라벨 있음 |
| `results/npu/stage2/20260912-144017-admission-eviction` | [TASK64](TASK64.md) | 5 (배경 8 + 간격 없는 X·Y) | `[OBS]` 있음, 재사용 lookup 없음 |

합 36 trial. ([TASK58](TASK58.md)의 21 trial = TASK14 9 + TASK15 12. 지시문의 "S3의 21 run"이 이 21건인지, S3 표(TASK63)를 가리키는지는 §7 D1에서 확인한다 — 어느 쪽이든 위 36 trial이 둘을 모두 포함한다.)

### 계산 방법

trial마다 server 로그를 파일 순서대로 재생해 `[PFX] [ALLOC]`(할당 순서, OB), `[PFX] [EVICTION]`(대상 OB), `[CACHE-HIT]`/`[CACHE-PARTIAL]`(resume 조회 결과)를 뽑는다. 모형 입력은 로그의 **할당 수열**과 prompt token 수(probe)뿐이다 — 결과 field(HIT/PARTIAL, EVICTION)는 입력에 쓰지 않는다.

모형 예측(C = `outer_slot_count` = 8, u = 1, `resume_allocates_first=True`, `DummyMode.PRE_EVICT`):

- **P1 생존**: resume 조회가 있는 순차 trial에서 `생존 ⇔ 1 + m + 1 ≤ 8 ⇔ m ≤ 6`
- **P2 축출 수**: `max(0, ALLOC + 1 − 8)` (PRE_EVICT의 trailing 축출 1건). 순차가 아닌 TASK63 B·TASK64에도 적용
- **P3 축출 대상**: 매 축출의 대상은 그 시점 할당 순서상 가장 이른 inactive OB (순차 trial에서는 곧 할당 순서 첫째 남은 OB)
- **P4 축출 시점(PRE_EVICT)**: `[OBS]`가 있는 trial(TASK63 A)에서 k번째 축출은 (8+k−1)번째 할당 뒤 첫 decode step의 dummy 괄호 안에서 일어난다. `[OBS]`가 없는 trial(TASK14/15)에서는 "축출 직후 사건이 `[BUCKET]`"인지로 대신한다

### 사전 예측

- P1: 순차 trial 29건(TASK14 9 + TASK15 12 + TASK63 A 8) 전부 일치. m ≤ 6 생존(B0,3,5,6 계열), m ≥ 7 소멸.
- P2: 36 trial 전부 일치 (예: ALLOC 9 → 2, 10 → 3, 35 → 28, 51 → 44, TASK63 B ALLOC 8 → 1, TASK64 ALLOC 10 → 3).
- P3: 전 축출 일치.
- P4: TASK63 A 전 축출 일치. **TASK64의 admission 경로 축출(5건)은 P4의 예외로 예측한다** — 두 admission 사이에 decode step이 없으면 pre-evict 기회가 없어 admission이 스스로 축출한다. 이 경우 모형 예측은 "축출 시점 = 두 번째 admission"이다.
- TASK14 B33·B49: layer 2 조회 로그가 없다. P1은 "resume ALLOC 전에 target OB가 축출됨"으로 판정한다(예측: 소멸).

### 판정 기준

**R1 `PASS` ⇔ P1 29/29, P2 36/36, P3 전 축출, P4 해당 전 축출이 모두 일치.** 한 건이라도 어긋나면 `FAIL`이다(부분 통과 없음). 판정 불가 trial(로그 결손)은 `UNKNOWN`으로 따로 세고, UNKNOWN이 1건이라도 있으면 판정은 `PASS (UNKNOWN k건 제외)`로 표기한다.

### 실패 시 결론

- P1 불일치: (B1-1)이 이 기판의 순차 생존 조건이 아니다. 불일치 trial의 사건 순서를 보고하고 모형의 창 정의(할당 시점 시작, 선할당)를 재검토한다. **이 경우 B1 기반 GPU 사전 예측은 하지 않는다.**
- P2만 불일치: 생존 식은 유지하되 dummy 모드(`PRE_EVICT`) 읽기가 틀렸다. [TASK58](TASK58.md)·[TASK63](TASK63.md) 산술과의 모순으로 보고한다.
- P3·P4만 불일치: FIFO 대상 규칙 또는 축출 시점 읽기가 틀렸다. 생존 판정은 개수 산술로 유지되나 동시 부하 확장(`K_pin`)의 근거가 약해진다.

---

## R2 — B1 block 단위 인스턴스 vs TASK29 `GranularPool` 절제 (모형–시뮬레이터 일관성, **측정 아님**)

### 데이터

측정 데이터가 아니다. [TASK29](TASK29.md) 축 ①의 시뮬레이터 계산이며, 산출물이 저장돼 있지 않아(§6) `experiments/npu/analysis/ablation.py`와 `GranularPool`로 **재계산**한다. 입력: C = `inner_block_count` 512, block 128 token, target 2,000·resume 2,008 token, 배경 {500, 1,000, 2,000, 4,000} token, B = 0..130.

### 계산 방법

(a) 모형: `survival.block_pool_thresholds(resume_allocates_first=True)`. (b) 시뮬레이터: `GranularPool(policy="lru")`에 같은 순차 프로토콜을 넣고 B마다 resume의 hit token을 계산. (c) B마다 hit token 값 자체도 모형의 (B1-2)와 대조한다.

### 사전 예측 (모형 값, 계산 완료 — 대조는 미수행)

| 배경 | u_bg | 첫 손실 B | 전손 B |
|---|---|---|---|
| 500 | 4 | 121 | 124 |
| 1,000 | 8 | 61 | 62 |
| 2,000 | 16 | 31 | 31 |
| 4,000 | 32 | 16 | 16 |

[TASK29](TASK29.md) 기록(500: B=70까지 손실 없음, 1,000: 61/62, 2,000: 31/31, 4,000: 16/16)과 문턱이 같을 것으로 예측한다. 이 기록을 알고 있었음을 밝힌다. 500 token의 121/124는 TASK29가 재지 않은 범위라 새 값이다.

### 판정 기준

**R2 `CONSISTENT` ⇔ 4개 배경 크기 × B = 0..130 전 칸에서 모형 hit token = 시뮬레이터 hit token.** 한 칸이라도 다르면 `INCONSISTENT`.

### 실패 시 결론

모형과 시뮬레이터 중 하나가 자기 명세와 다르다. 어느 쪽인지 사건 단위로 가른다. **이 항목은 어느 결과든 기판에 대한 사실을 말하지 않는다.** GPU 예측에 쓸 때는 vLLM의 조회 후 할당(`resume_allocates_first=False`)으로 바꾸며 그때 값은 1,000: 63/64, 2,000: 32/32, 4,000: 16/16이다 — 이것은 GPU 측 선등록에서 다시 등록한다.

---

## R3 — B3 DP 최적 격자 vs `config_search` 선정 (되먹임 반영 판정)

### 설계 원칙

h(n)은 격자에 따라 바뀐다(원고 III-D, [TASK68](TASK68.md)). 따라서 **다른 격자에서 얻은 h로 G\*를 평가하지 않는다.** 판정은 G\* = `(1,4,6,8,10,16)`·`batch_size` 16([TASK61](TASK61.md))이 **자기 자신이 만든 h에 대한 최선 응답인가**(고정점 조건)로 한다. 이것은 G\*가 되먹임 계에서 최적이기 위한 필요조건이며, 충분조건은 아니다.

### 데이터

- **R3a (config_search와 동일 입력)**: config_search 탐색 입력(탐색 seed 20260910·20260921·20260932 × block 0,1,2 × N 6,8,10, gap `toolmix` summary.json SHA256 `25bb1b0f…`)을 G\*·batch 16으로 시뮬레이션한 decode step 히스토그램 `h_sim(n)`(`SimResult.pair_histogram`). 시뮬레이터 기본 설정(dummy off, fixed_arrivals off).
- **R3b (관측)**: [TASK35](TASK35.md) TUNED arm 9 파일(N 6·8·10 × 3블록)과 [TASK36](TASK36.md) TUNED 3 파일의 `[BUCKET] request_nums` 히스토그램 `h_obs(n)`. N별·전체 합산 둘 다.

### 계산 방법

`fixed`: RBLN descriptor의 측정 폭 {1,2,4,8}에 `interpolated_fixed_costs`(= `config_search.descriptor_for` 규칙). DP: `optimal_grid(h, top=16, max_buckets=6)`. 비교 지표:

```
regret_rel(h) = [cost(G*; h) − cost(G_DP; h)] / cost(G*; h)
cost = Σ h(n)·t_step(b(n), n)   (intercept·marginal 포함, 즉 decode device time)
```

### 사전 예측

- R3a: `G_DP = G*`(확신 중간). 다르더라도 `regret_rel ≤ 0.5 %`.
- R3b(전체 합산): `regret_rel ≤ 1 %`. 격자 일치는 예측하지 않는다(h_obs에서 n=2,3,5,7 비중에 따라 2 또는 3·5·7 폭이 들어올 수 있다).
- 두 경우 모두 폭 16에는 가중치가 없다(n ≤ 10, 인벤토리: 관측 padded 16 없음).

### 판정 기준

**R3 `PASS` ⇔ R3a와 R3b(전체 합산) 모두 `regret_rel ≤ 1.0 %`.** 격자가 같으면 `PASS (EXACT)`로 표기한다. N별 regret은 보고만 한다. 한쪽이라도 1.0 %를 넘으면 `FAIL`.

탐색(판정 없음) R3c: `G_DP ≠ G*`이면 G_DP로 다시 시뮬레이션해 h를 얻고 DP를 반복한다(최대 5회). 고정점 수렴·순환 여부와 각 격자의 config_search 탐색 ratio(재계산)를 보고한다.

### 실패 시 결론

G\*가 자기 h에 대해 decode padding 항만으로는 최선 응답이 아니다. 즉 config_search의 선정은 padding 항이 아니라 **되먹임 또는 prefill·재도착 시각 경로**에서 이득을 얻었다는 뜻이며, **격자 선택에 DP(해석 모형)만으로는 부족하고 시뮬레이터가 필요하다**고 결론 낸다. 이는 Stage 3의 "시뮬레이터 = 근사가 깨지는 영역을 보여주는 중간 단계" 위치 설정의 구체적 사례로 기록한다.

---

## R4 — B2 예측 h(n) vs 원고 Table I 조건의 관측 h(n) (**탐색적, 판정 없음**)

### 사전 선언

원고 workload는 세션당 2요청·동시 시작으로 **steady state가 아니다.** B2는 steady state만 다루므로 **불일치가 예상된다.** 이 항목은 판정하지 않고 거리만 보고한다. 결과가 좋든 나쁘든 B2의 검증으로 쓰지 않는다.

### 데이터

`results/npu/stage2/padding_ratio.json`의 `cells`(17개, `hist_agentic`/`hist_conventional`, "actual->bucket": step 수)와 그 입력 run 5개(§6 R4). Table I(T01)의 pooled 행은 cell을 합산해 만든다.

### 계산 방법

cell마다 B2 입력: N, M = 8(해당 artifact의 `batch_size`), G = plan의 평균 생성 길이 − 1, Z = plan의 평균 gap(AGENTIC), E[P] = plan 평균 prompt의 `prefill_s`(재사용 무시). **CONVENTIONAL(gap 0)은 Z → 0 극한에서 B2가 정의되지 않으므로 계산하지 않는다**(보고: `NOT_APPLICABLE`). 비교 대상: `step_share`.

지표: total variation distance `TVD = ½ Σ |h_pred(n) − h_obs(n)|`, step 가중 평균 running 수의 차, `padding` 비(Σ(b−n)/Σb)의 예측 대 관측.

### 사전 예측 (판정 아님)

- TVD는 대부분의 AGENTIC cell에서 0.3을 넘을 것이다. 관측 h는 n=N 근처(시작 폭주)와 n=1..3(drain)에 질량이 몰린 두 봉우리이고, B2는 한 봉우리다.
- 평균 running 수는 B2가 **과소** 예측할 것이다(시작 동기화가 steady state보다 겹침을 늘린다).

### 결과 해석 규칙

어떤 값이 나와도 B2를 수정하지 않는다. steady-state multi-turn 실험 설계의 입력(ramp·drain을 버릴 구간 길이)으로만 쓴다.

---

## R5 — B1 확률적 확장 vs 동시 실행 재사용률 (**탐색적으로 둔다** + 확증 대안 R5′ 제안)

### 탐색으로 두는 근거

1. 원고의 동시 실행 run은 모두 세션당 2요청·동시 시작이다. 창 안의 할당 수 A는 renewal 과정이 아니라 plan과 도착 순서로 거의 결정된다 — (B1-3)의 가정 3(정상 renewal)이 성립하지 않는다. 불일치가 나와도 **모형 오류와 체제 불일치를 가를 수 없다.**
2. 확률적 확장의 입력(주기 c, 체류 시간)을 이 run들에서 추정하면 같은 데이터로 맞추고 평가하는 순환이 된다.

### R5 (탐색, 판정 없음)

- 데이터(§6 R5): [TASK50](TASK50.md) null-channel(b8, N 6·8, **같은 plan 10회**, 280 요청), [TASK35](TASK35.md) final-confirm(432), [TASK36](TASK36.md)(108), [TASK40](TASK40.md)(576), [TASK54](TASK54.md)(mb·mb6 각 168), [TASK20](TASK20.md)(864). 재사용 = `usage.prompt_tokens_details.cached_tokens > 0`(turn 1 요청).
- 계산: run의 plan에서 c = 평균 gap + 평균 응답 시간(모형 B2 값, 측정값 아님), W_FIFO = 모형 체류 + plan gap, law ∈ {binomial, poisson}. 세션 단위 예측 생존 확률의 합 = 예측 재사용 수.
- 보고: cell(run × N × arm)별 예측 대 관측 재사용률, 두 법칙의 차, TASK50 10회 반복의 관측 분산(같은 plan에서 재사용 수가 회차마다 얼마나 흔들리는가).
- 사전 예측: 두 법칙 모두 N=6에서 관측보다 **낮게**(동시 시작 뒤 흩어진 도착이 renewal보다 겹침이 적다), N ≥ 10에서는 관측과 비슷하거나 높게 예측할 것이다. 확신 낮음.

### R5′ (확증 대안, 제안 — §7 결정 D2)

확률 법칙 대신 **결정론적 핵심을 요청 단위로** 적용한다. 각 turn-1 요청 R에 대해 server 로그의 `[PFX] [ALLOC]` 순서에서 T(같은 세션 turn 0)의 할당부터 R의 할당까지의 할당 수 A를 세고, T보다 먼저 할당된 항목 중 T 축출 시점에 running이던 수 `K_pin`을 요청 완료 시각(probe `done_s`, `request_id` join)으로 정한다. 예측 = (B1-1), 관측 = `cached_tokens > 0`.

- 사전 예측: 전체 일치율 ≥ 0.97. 불일치는 (i) 즉시 복귀(gap ≈ 0) 요청의 release 시점 문제, (ii) `K_pin` 시점 판정이 초 단위 로그 시각에 걸리는 경우에 몰릴 것이다.
- 제안 기준: **R5′ `PASS` ⇔ run별 일치율이 모두 ≥ 0.95.** 불일치 요청은 전부 사건 순서와 함께 보고한다. dummy 모드는 `PRE_EVICT`와 `RESERVED` 둘 다 계산해 **어느 읽기가 더 많이 맞는지**를 함께 보고한다(판정은 `PRE_EVICT` 기준 — 관측 근거가 있는 읽기이므로 사전에 고정).
- 실패 시 결론: 동시 부하에서 (B1-1)의 창·`K_pin` 정의가 부족하다. release 시점 규칙(MODEL_V0 (iv) 1번)을 별도 관측 과제로 연다. B1 기반 steady-state 예측의 선등록은 그 해소 뒤로 미룬다.

---

## 6. 데이터 인벤토리 (작업 D — 존재 확인만, 대조 계산 없음)

2026-09-29 read-only 확인. `results/`는 git 비추적이므로 경로만 적는다. 모든 경로의 머리는 `results/npu/stage2/`.

| 항목 | 경로 | 파일 수 | 필요한 field | 존재 | 비고 |
|---|---|---|---|---|---|
| R1 | `20260819-200800-gap-turnover` (TASK14) | 32: server 9, probe log 9, probe JSON 9 | `[PFX] ALLOC/EVICTION/CACHE-HIT/PARTIAL`, B, prompt token | **YES** | 예: `server-B7.log` ALLOC 9·EVICTION 2·PARTIAL 1, `server-B49.log` ALLOC 51·EVICTION 44. probe `usage.prompt_tokens_details`가 null — 요청별 cached는 Prometheus delta(순차라 대응 성립). `[OBS]` 없음, `[BUCKET]` 있음 |
| R1 | `20260819-204900-cliff-repro` (TASK15) | 41: server 12, probe log 12, probe JSON 12 | 같음 | **YES** | ALLOC/EVIC/HIT/PARTIAL: B5 7/0/1/0, B6 8/1/1/0, B7 9/2/0/1, B8 10/3/0/1, 3회 동일. `[OBS]` 없음 |
| R1 | `20260912-134732-dummy-lifecycle` (TASK63) | 113: server 11(A 8, B 2, pilot 1), probe JSON 11 | PFX, `[OBS]`(epoch `t=`), `[BUCKET]` | **YES** | 예: `server-A.B7r0.log` `[OBS]` 281, DUMMY-BEGIN 63, EVICT 2 |
| R1 | `20260912-144017-admission-eviction` (TASK64) | 67: server 5, probe 5, class 5 | PFX, OBS, BUCKET, `send_start_s`/`response_s` | **YES** | 각 ALLOC 10·EVIC 3·HIT/PARTIAL 0 |
| R1 | `layer_audit.json` (TASK58) | 1 | 21 trial 축출 timeline | **YES** | 보조 대조용 |
| R1 | provenance | — | git commit, patch 상태 | **PARTIAL** | TASK14·15 run에는 `patch-state.txt`만, commit은 TASK 문서에만. TASK63·64 run은 `provenance.txt` 있음 |
| R2 | `experiments/npu/analysis/ablation.py` | 1 (commit `d67b19d`) | script | **YES** | 코드만으로 재현 가능 |
| R2 | ablation 산출물 | 0 | 결과 JSON | **NO** | 저장된 산출물 없음 → 재계산 필요 |
| R3 | `20260911-153800-config-search-rerun/run-a/ledger.{json,csv}` | 26 (run-b 동일본) | 후보별 buckets·batch·explore_ratio | **YES** | 2,077행, SHA TASK61 기록 일치. G\* `explore_rank` 1 |
| R3 | `/home/rebel/vllm-continuum/results/tracelab/summary.json` | 1 | gap 법칙, SHA256 | **YES** | `25bb1b0f…` 일치 |
| R3 | `20260823-183505-final-confirm` (TASK35) | server 27 (TUNED 9) | TUNED `[BUCKET]` | **YES** | TUNED 줄 수 n6 529/429/566, n8 905/682/391, n10 704/845/846 |
| R3 | 같은 run | — | padded 16 관측 | **PARTIAL** | 관측 padded는 n≤10까지. 16은 0회 |
| R3 | `20260824-160028-n6-reconfirm` (TASK36) | server 9 (TUNED 3) | TUNED `[BUCKET]` | **YES** | 717/598/519줄 |
| R4 | `padding_ratio.json` | 1, cells 17 | cell별 h(n) | **YES** | `hist_agentic`/`hist_conventional` |
| R4 | 같은 파일 | — | T01 pooled 행 h(n) | **PARTIAL** | pooled 행은 histogram 없음 → cell 합산 필요 |
| R4 | 입력 run 5개 (`20260819-233800-paired-pilot-v2` 4, `20260820-165200-nslots-sweep` 44, `20260821-222000-grid-observe` 24, `20260821-231000-grid-intervene` 12, `20260822-160532-sim-oos` 18) | util·server 각 수만큼 | `pair_histogram`, raw `[BUCKET]`, plan | **YES** | 세션당 2요청·동시 시작 확인(turn0 `sent_s` ≈ 0.01 s) |
| R4 | Table I ↔ T01 대응 | — | — | **PARTIAL** | 내용 기준 추정(`table_3_1` = T01). 원고 확인 필요 |
| R5 | `20260901-020342-null-channel` (TASK50) | 149 (server/util/requests/meta 각 20) | session, turn, prompt_tokens, cached_tokens, sent_s/done_s, gap_after_s, request_id | **YES** | 같은 plan 10회 반복, 280행 |
| R5 | `20260823-183505-final-confirm` (TASK35) | 요청 27 | 같음 | **YES** | 432행, 블록마다 plan 다름 |
| R5 | `20260824-160028-n6-reconfirm` (TASK36) | 요청 9 | 같음 | **YES** | 108행 |
| R5 | `20260824-222453-batch-saturation` (TASK40) | 요청 36 | 같음 | **YES** | 576행 |
| R5 | `20260908-133635-grid-paired` (TASK54) | `mb/`·`mb6/` 각 12 | 같음 | **YES** | 각 168행, 하위 디렉터리 |
| R5 | `20260820-165200-nslots-sweep` (TASK20) | 요청 44 | 같음 | **YES** | 864행 |
| R5 | 서버 admission 순서 | 위 run들의 server log | `[PFX] [ALLOC]` + request_id join | **YES** | final-confirm 1건으로 join 확인. 로그 시각은 초 단위(`[OBS]` 없음) → R5′의 `K_pin` 시점 판정은 probe `done_s`로 해야 함 |
| R5 | 절대 시각 정렬 | — | `at_utc` 의미 | **UNKNOWN** | `at_utc`가 송신 시각인지 완료 시각인지 미확인 |
| R5 | Table III·VI·XIII ↔ run 대응 | — | — | **UNKNOWN** | 원고가 저장소 밖. "반복 10회"는 TASK50만 해당 |
| R5 | TASK50 파일 수 | — | — | **PARTIAL** | TASK50 문서 기록 110개, 현재 149개. 차이 원인 `UNKNOWN`(후속 분석 산출물 추가로 추정) |

---

## 7. Advisor 결정 요청

- **D1 — 원고 표·절 번호와 저장소 산출물의 대응 확인.** 원고(Table I·III·VI·XI·XIII, III-B, III-D, V-A, S3, 식 (6)·(9))는 저장소에 없다. 위의 대응(Table I = T01, "S3의 21 run" = TASK58 21 trial 또는 TASK63, 재사용 표 = §6 R5 run들)을 확인해 달라. 대응이 다르면 **대조 계산 전에** 이 문서를 개정 commit한다.
- **D2 — R5의 성격.** 권고: 확률적 확장 R5는 탐색으로 두고, 결정론적 핵심을 동시 run에 요청 단위로 적용하는 **R5′를 확증으로 추가**한다. 대안: (a) R5만 탐색으로 두고 R5′ 없음 — 동시 부하 모형의 확증이 multi-turn 실험까지 미뤄진다. (b) R5를 확증으로 — 비정상 workload에서 renewal 가정을 판정하게 되어 결과 해석이 불가능하다(비권고).
- **D3 — dummy 모드.** 판정은 관측 근거가 있는 `PRE_EVICT`로 사전 고정하고 `RESERVED`는 병기만 한다(권고). [TASK69](TASK69.md) 스위치 정의를 바꾸는 일은 이 대조 뒤 별도 TASK로.

## 개정 이력

- 2026-09-29 초판 (대조 계산 전).
