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

> **개정 1(§8.2)로 대체됨.** 아래 원 기준은 병기용으로만 계산한다.

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

> **개정 1(§8.3)로 확증 항목으로 채택되고 계산 방법·기준이 구체화됐다.** 아래는 초판 제안이다.

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

## 8. 개정 1 — Advisor 지시문 02 반영 (2026-09-29, 대조 계산 전)

이 절이 §1–§7과 충돌하면 이 절이 우선한다. **이 개정을 commit하기 전까지 R1–R5′의 대조 계산은 한 건도 수행하지 않았다.** 개정 전에 한 일은 데이터 형식·provenance 확인(아래 §8.3의 code-read와 server 인자 확인, TUNED artifact 확인)뿐이다.

### 8.1 D1 — 원고 번호와 저장소 산출물의 대응 (Advisor 확인)

| 원고 | 저장소 | 비고 |
|---|---|---|
| Table I (padding, decode device time, N=3..16) | `results/tables/T01`, `padding_ratio.json` | N=3·7은 두 측정 batch가 합산돼 있다 |
| Table II (bucket 6 개입) | T02, [TASK54](TASK54.md) | |
| Table III (8 vs 16 slot, 재사용 9/24 vs 24/24) | T03, [TASK35](TASK35.md) final-confirm N=8 | |
| Table VI (N=6, padding 0.232→0.167, 재사용 18/18→14/18) | [TASK54](TASK54.md) grid-paired의 기존 격자 arm | 같은 절 "N=8 기존 격자 11/24 vs 7/24"도 TASK54. "대기 시간 동일 vs 세션별 7/24 vs 11/24"는 [TASK21](TASK21.md) |
| Table IX / X / XII | T07 / T08 / T09 | |
| Table XI (fixed-arrival 비교) | [TASK68](TASK68.md) 산출물 | T 파일 없음 |
| Table XIII (slot 16·24·32 포화) | T10, [TASK40](TASK40.md) | |
| III-B-c "같은 N=8 plan 10회, 7회 6/8·3회 5/8" | [TASK50](TASK50.md) null-channel N=8 | |
| "S3의 21 run" | **[TASK58](TASK58.md)의 21 trial (TASK14 9 + TASK15 12)** | 원고 보충 S3의 `max(0, m−5)` 21/21. 같은 절 Table S4 10 run은 [TASK63](TASK63.md) |
| 보충 S1·S2·S4·S5·S6·S7·S8·S9 | T12·S02·T13·T14·S06a·S06b·B01·S08 | 원고 S 번호와 파일 번호가 다르다 |

원고의 식: (5) `T̂_prefill(q) = ceil(q/128)·(0.021206 + 6.399e-7·q)`, (6) `W_j = ∫ K_j(t) dt`, (9) `Ŵ = Σ_j T̂_prefill(q̂_j)·K̂_j`. B4 재구성은 (9)와 일치한다. **B4의 기대값 형태는 P와 K의 독립을 가정하며, 재사용 실패(긴 P)가 고부하(큰 K)에 몰려 공분산이 양일 가능성이 높다** — [MODEL_V0.md](MODEL_V0.md) B4 가정에 추가했다(식은 수정하지 않음).

R1 모집단은 바뀌지 않는다(36 trial이 21 trial과 S4 10 run을 모두 포함). §0-5의 확인 요청은 해소됐다.

### 8.2 R3 판정 기준 강화 (§R3 "판정 기준" 대체)

- regret은 **격자 의존 항만**으로 계산한다: `cost_grid(G; h) = Σ h(n)·fixed(b_G(n))`, `regret_rel(h) = [cost_grid(G*; h) − cost_grid(G_DP; h)] / cost_grid(G*; h)`.
- 효과 척도: `E(h) = [cost_grid(G_ref; h) − cost_grid(G*; h)] / cost_grid(G*; h)`, `G_ref = (1,2,4,8,16)`. `fixed`는 두 격자 모두 `interpolated_fixed_costs`(= `config_search.descriptor_for` 규칙)로 만든다.
- **R3 `PASS` ⇔ R3a와 R3b(전체 합산) 모두 `regret_rel ≤ 0.25·E(h)`.** 한 항목에서 `E(h) ≤ 0`이면 그 항목은 `NOT_INFORMATIVE`로 보고하고 판정에서 뺀다(둘 다 그러면 R3 전체 `NOT_INFORMATIVE`). 격자가 같으면(`regret_rel = 0`) `PASS (EXACT)`.
- **병기**: 원 기준(`regret_rel ≤ 1.0 %`, 분모에 intercept·marginal을 포함한 전체 decode 비용)의 결과. intercept·marginal은 RBLN descriptor 값.
- **R3b provenance 확인(계산 전 완료)**: [TASK35](TASK35.md)·[TASK36](TASK36.md) TUNED arm의 `served_model_id`는 `Qwen3-4B-rbln-b16-s8192-d4-mb16`(meta 9+3건 전부)이고, 그 artifact의 `rbln_config.json`은 `batch_size 16`, `kvcache_num_blocks 16`, `decoder_batch_sizes [16, 10, 8, 6, 4, 1]`이다. 파일 mtime 2026-08-23 17:09:59로 두 run(08-23 18:35, 08-24)보다 앞선다. **확인됨 → R3b 계산 가능.**
- 사전 예측(개정): R3a `PASS (EXACT)` 또는 PASS, R3b PASS. E(h)는 R3a·R3b 모두 양수(2–6 % 범위)로 예측한다. 확신 중간.
- 실패 시 결론은 §R3과 같다.

### 8.3 R5′ — 확증 항목으로 채택, 전제·방법·기준

**전제 확인 (code-read·server 인자, 계산 전 완료).**

1. `at_utc`: `experiments/npu/stage2/session_runner.py`의 모든 이력 버전(`37604b5`, `838a42d`, `f9cc106`, `980f0c7`, `f61bafe`)에서 `at_utc`는 **응답 수신(`done`) 직후, `emit` 직전**에 찍힌다 — 완료 시각에 가깝다. run별 runner 버전은 run 시작 시각 직전의 runner commit으로 정하며(run 디렉터리에 runner commit이 없는 run이 있다) 의미는 모든 버전에서 같다. run별 표는 TASK에 기록한다. **R5′는 `at_utc`를 쓰지 않는다**(아래 방법 참조).
2. `--enable-prompt-tokens-details`: R5·R5′ 대상 7개 run 디렉터리의 server 로그 **160/160**에서 `enable_prompt_tokens_details: True`가 확인된다(nslots-sweep 44, null-channel 20, final-confirm 27, n6-reconfirm 9, batch-saturation 36, grid-paired mb 12·mb6 12). 따라서 이 run들의 `cached_tokens = 0`은 관측으로 취급한다. 단 runner의 `details.get("cached_tokens", 0)` 0 채움은 원칙 14와 충돌하는 잠재 결함이며 KNOWN_PITFALLS 추가 후보로 보고만 한다(runner 수정 없음). 응답에 `prompt_tokens_details`가 실제로 없었던 행은 jsonl에서 구별할 수 없으므로, 각 행의 server 로그 조회 결과(`[CACHE-HIT]`/`[CACHE-PARTIAL]`)와 교차 확인하고, 둘이 어긋나는 행은 `UNKNOWN`으로 둔다.

**시각 정렬 — 쓰지 않는다.** R5′의 모든 판정은 **server EngineCore 로그의 파일 순서**만으로 한다. EngineCore는 단일 process이고 `[PFX]`·`[BUCKET]` 줄은 사건 순서대로 기록된다. client 시각(`sent_s`, `done_s`, `at_utc`)은 판정에 쓰지 않는다. client 행과 server 요청의 join은 `request_id`가 server `REQUEST=` 값의 strict prefix라는 성질([TASK18](TASK18.md))로 한다. 따라서 초 단위 시각 경계 문제는 구조적으로 생기지 않는다.

**계산 방법 — (B1-1)의 사건 재생.** 입력은 server 로그의 `[PFX] [ALLOC] REQUEST=…`, `[PFX] [FREE-REQUEST] REQUEST=…`, `[BUCKET] request_nums=n` 세 종류뿐이다. **결과 줄(`[EVICTION]`, `[MAPPING-*]`, `[CACHE-*]`)은 입력에 쓰지 않는다.** C = artifact `batch_size`(= `kvcache_num_blocks`, 모델 이름의 `b8`/`b16`/…), 상한 = 같은 값.

- `ALLOC(R)`: free가 0이면 할당 순서상 가장 이른 inactive 항목 1개 축출(admission 경로). 그 뒤 R의 새 항목을 active로 등록. **그 다음** R 세션의 이전 turn 항목이 아직 pool에 있으면 예측 = 재사용(할당 후 조회).
- `FREE-REQUEST(R)`: R의 항목을 **즉시 inactive**로 둔다(release 규칙 = 즉시. 근거 [TASK63](TASK63.md) B.b0 상한 이탈, 계산 전 고정).
- `[BUCKET] n`: `PRE_EVICT` 모드에서 `0 < n < 상한`이고 free가 0이며 inactive 항목이 있으면 가장 이른 inactive 1개 축출(dummy 경로).
- `RESERVED` 모드(병기): `[BUCKET]`에서 축출하지 않고, `ALLOC` 시 `0 < (그 시점 active 수) < 상한`이면 free 요구량을 1 늘린다.
- 이 재생은 각 축출 순간의 `K_pin`(T보다 오래된 active 항목)을 정확히 반영한 (B1-1)이다. 보조로 R의 lookup 시점 값 `A`(T의 ALLOC부터 R의 ALLOC까지 할당 수), 그 시점 `K_pin`으로 `survival.survives`를 호출한 닫힌 형태 예측도 계산해 재생 예측과의 일치율을 보고한다(판정 미사용).
- 관측 = client `cached_tokens > 0`. server `[CACHE-HIT]`와 교차 확인.
- 모집단 = 7개 run 디렉터리의 모든 turn ≥ 1 요청.
- `UNDECIDABLE`: T 또는 R의 `ALLOC`을 join하지 못함, `OB_COUNT ≠ 1`, 재생 중 축출 대상이 없어 규칙이 정의되지 않음(inactive 0개인데 free 0). `UNKNOWN`: client 관측과 server 조회 결과가 어긋나는 행.

**기준.** 모두 `PRE_EVICT` 재생 기준.

- **R5′ `PASS` ⇔ run 디렉터리별 일치율(분모에서 `UNDECIDABLE`·`UNKNOWN` 제외) ≥ 0.95가 7개 run 모두에서 성립.** grid-paired는 mb·mb6를 별도 run으로 센다.
- `UNDECIDABLE + UNKNOWN`이 전체 turn ≥ 1 요청의 5 %를 넘으면 `INCONCLUSIVE`.
- 모든 불일치를 사전 범주로 분류한다. **(i) 즉시 복귀 release 시점**: release 규칙을 "다음 ALLOC의 축출 선택 뒤에 inactive"로 바꾼 재생에서 그 요청의 예측이 관측과 일치하게 되는 불일치. **(ii) 시각 경계**: client–server join이 모호해 판정이 갈리는 불일치(server 순서만 쓰므로 0건으로 예측). **(iii) 기타**. (iii)이 1건이라도 있으면 PASS여도 `PASS (미설명 k건)`으로 표기하고 사건 순서를 전부 보고한다.
- `RESERVED` 재생의 일치율을 병기해 두 읽기의 적중을 비교한다(판정 미사용).
- 원고 III-B-a의 "재사용 실패 73건"이 이 모집단의 부분집합으로 특정되면(관측 실패 수가 73인 run 조합을 찾는다) 그 73건의 모형 측 원인(창 안 할당 수 초과 / `K_pin` / dummy pre-evict / 기타)을 건별로 분류한다. 특정되지 않으면 `UNKNOWN`으로 보고한다.
- 사전 예측: 전체 일치율 ≥ 0.97, run별 모두 ≥ 0.95. 범주 (ii) 0건. `PRE_EVICT` 일치율 > `RESERVED` 일치율.

### 8.4 GPU 관련 기록 정정 (문서만)

[TASK29](TASK29.md)의 GPU 측 block 문턱 계산은 할당 후 조회를 가정했으므로 GPU 기판의 사전 예측으로 **그대로 쓰지 않는다.** TASK29 원문은 수정하지 않는다. GPU 측 사전 예측은 **GPU 서버에 실제 설치될 vLLM 버전의 source-read로 순서를 다시 확인한 뒤 새로 선등록**한다. 현재 확인은 NPU 서버의 `vllm 0.22.0+cpu` 기준이다. INDEX 결정 4에 같은 내용을 추가했다.

### 8.5 산출물 위치

계산 산출물은 `results/npu/stage3/model_v0_retro/`(비추적). 판정 요약표는 `results/tables/M01`부터(추적). 대조 스크립트는 `experiments/npu/analysis/model_v0_retro.py`이며 `src/continuum/model/`을 import만 한다. **모형 수정이 필요해 보이면 그 항목 계산을 멈추고 보고한다.**

## 개정 이력

- 2026-09-29 초판 (대조 계산 전, commit `8c107a0`).
- 2026-09-29 개정 1 (지시문 02, 대조 계산 전): §8 추가 — D1 대응표, R3 기준 강화(격자 의존 regret ≤ 0.25·E(h)), R5′ 확증 채택과 사건 재생 방법·기준·범주, GPU 기록 정정. 초판의 R3 기준은 병기용으로 격하.
