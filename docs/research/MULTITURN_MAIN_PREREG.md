# multi-turn steady-state 본 실험 — blind 예측과 판정 기준 선등록

작성: 2026-09-29, Advisor 지시문 04 작업 D. **본 측정은 하지 않았다.** 이 문서는 Advisor 검토 후 지시문 05에서 측정할 실험의 plan·예측·판정 기준을 측정 전에 고정한다. 기준은 **제안**이며, Advisor가 바꾸면 측정 전에 개정 commit한다.

## 1. plan (고정)

- N ∈ {6, 8, 10, 12}, replicate r = 0..4, **seed `20261400 + 10N + r`**, plan_id `main-n{N}-r{r}`. 생성 규칙은 `make_plan.py`(K = 8, 첫 prompt U(800,1600), 이후 segment 8, 생성 U(32,256), gap `toolmix` 상한 60 s, slot당 세션 16개)와 [TASK77](TASK77.md)의 `generate_plan`. `cycle_s`(엇갈림·구간 규칙)는 해석 모형의 TUNED 예측값.
- 파일: `experiments/npu/stage3/plans/main/main-n{N}-r{r}.json` 20개, 목록 `INDEX.json`(SHA256 `f542e971…d471dcadd`). 각 파일의 내용·파일 SHA256과 최대 context(3,022–3,309 token)는 `INDEX.json`에 있다.
- **seed 겹침**: 격자 선정(`20261200 + 10N + r`, N=10이면 `20261300–02`)과 파일럿(`20261300–02`)의 **base seed 숫자가 겹친다.** 세션 seed는 `derive_block_seed(base_seed, "<plan_id>/slot…/g…")`로 plan_id를 포함해 파생되므로 같은 세션이 생기지는 않는다. 본 실험 seed(`20261460–20261524`)는 둘과 겹치지 않는다.
- 같은 (N, r)의 plan을 모든 구성이 쓴다(짝 설계).

## 2. 구성

| 구성 | 격자 | `batch_size` | artifact |
|---|---|---|---|
| BASE | (1,2,4,8) | 8 | `Qwen3-4B-rbln-b8-s8192-d4-mb` (기존) |
| BATCHONLY | (1,2,4,8,16) | 16 | `…-b16-s8192-d4-batchonly` (기존) |
| TUNED | (1,4,6,8,10,16) | 16 | `…-b16-s8192-d4-mb16` (기존) |
| DP(N) | N=6 (1,2,3,4,5,16), N=8 (1,2,3,4,6,16), N=10 (1,3,4,5,7,16), N=12 (1,4,5,6,8,16) | 16 | **미compile**([TASK78](TASK78.md), Advisor 결정 대기). compile되는 N에서만 측정 |

lifecycle: 4 N × 3 구성 × 5 = **60** (+ DP 격자 compile 수 × 5). 순서는 replicate 블록 안에서 구성 순서를 무작위(seed `20261410`)로 정해 측정 지시문에서 고정한다.

## 3. 측정 정의

`experiments/npu/stage3/mt_measure.py`(파일럿과 같은 정의). cell (N, 구성, r)마다 평가 구간(`WindowRule`)의:

- **재사용률** = turn ≥ 1 요청 중 `cached > 0` 비율. `cached`는 client `cached_tokens`, `null`이면 server 조회 줄(파일럿에서 vLLM이 캐시 0일 때 field를 생략함을 source로 확인 — [TASK79](TASK79.md)).
- **h(n)** = server 창의 `[BUCKET]` step 가중 분포, **padding 비** = Σ(b−n)/Σb.
- **turn당 decode·prefill·전체 device time** = 채널 A′ / 평가 구간 요청 수.
- **BASE 대비 비** = 같은 (N, r)의 turn당 A′ 비. replicate 5개의 **중앙값**과 **95 % percentile bootstrap CI**(replicate 복원 추출 10,000회, seed `20261420`).
- **streaming**: 파일럿 판정 `EQUIVALENT`([TASK79](TASK79.md))에 따라 **본 실험은 streaming**(`run_multiturn.sh … stream`).
- **W per turn (측정, 탐색 정의)**: 평가 구간 요청마다 streaming chunk 도착 간격 중 그 요청의 간격 중앙값의 3배를 넘는 간격을 "정지"로 보고, (간격 − 중앙값)을 합한다. 평가 구간 요청 전체의 합 / 평가 구간 요청 수. 다른 세션의 prefill이 decode를 멈춘 시간(원고 식 (6)의 ∫K dt)을 희생자 쪽에서 센 값이다. 정의가 새로우므로 탐색이다.
- **turn ≥ 1 TTFT**: 평가 구간 turn ≥ 1 요청의 `first_token_s − sent_s` 중앙값(보고만).

## 4. 예측 (세 예측기, 측정 전 고정)

전체 수치는 `experiments/npu/stage3/plans/main/PREDICTIONS.json`(이 commit에 포함, `predict_main.py` 산출, SHA256 `0c32701c…6da3fea`, DP 격자 입력 `DP_GRIDS.json`). 입력은 TASK72까지의 descriptor 상수와 §1 plan뿐이며 **파일럿 측정값은 쓰지 않았다.** 예측기: (1) **해석** — v1 생존 + B2 + B3 + B4, (2) **sim 기본**, (3) **sim 관측 의미론**(`immediate` + `pre_evict`).

BASE 대비 비(turn당 A′):

| N | BATCHONLY 해석 / sim기본 / sim관측 | TUNED | DP(N) |
|---|---|---|---|
| 6 | 0.9834 / 0.9941 / 0.9941 | 0.9876 / 0.9898 / 0.9898 | 0.9795 / 0.9917 / 0.9917 |
| 8 | 0.9716 / 0.9825 / 0.9825 | 0.9687 / 0.9839 / 0.9839 | 0.9649 / 0.9713 / 0.9713 |
| 10 | 0.9534 / 0.9689 / 0.9649 | 0.9451 / 0.9593 / 0.9553 | 0.9422 / 0.9585 / 0.9545 |
| 12 | 0.8905 / 0.8755 / 0.8828 | 0.8751 / 0.8565 / 0.8637 | 0.8738 / 0.8669 / 0.8741 |

재사용률(turn ≥ 1):

| N | BASE 해석 / sim기본 / sim관측 | BATCHONLY | TUNED | DP |
|---|---|---|---|---|
| 6 | 0.825 / 0.827 / 0.827 | 0.915 / 0.916 / 0.916 | 0.915 / 0.918 / 0.918 | 0.915 / 0.917 / 0.917 |
| 8 | 0.736 / 0.780 / 0.779 | 0.882 / 0.879 / 0.879 | 0.882 / 0.880 / 0.880 | 0.882 / 0.875 / 0.875 |
| 10 | 0.634 / 0.697 / 0.697 | 0.858 / 0.856 / 0.856 | 0.857 / 0.861 / 0.861 | 0.857 / 0.860 / 0.860 |
| 12 | 0.404 / 0.485 / 0.507 | 0.834 / 0.861 / 0.861 | 0.837 / 0.864 / 0.864 | 0.839 / 0.860 / 0.860 |

turn당 A′ (ms, 해석 / sim기본): N=6 BASE 820 / 826, TUNED 810 / 818; N=8 BASE 697 / 714, TUNED 676 / 702; N=10 BASE 611 / 632, TUNED 578 / 606; N=12 BASE 563 / 547, TUNED 493 / 468. padding 비·h(n)·W는 JSON.

구성 순위(turn당 A′, 1 = 가장 싸다):

| N | 해석 | sim 기본 | sim 관측 |
|---|---|---|---|
| 6 | DP < BATCHONLY < TUNED < BASE | TUNED < DP < BATCHONLY < BASE | 같음(sim 기본) |
| 8 | DP < TUNED < BATCHONLY < BASE | DP < BATCHONLY < TUNED < BASE | 같음 |
| 10 | DP < TUNED < BATCHONLY < BASE | DP < TUNED < BATCHONLY < BASE | 같음 |
| 12 | DP < TUNED < BATCHONLY < BASE | TUNED < DP < BATCHONLY < BASE | 같음 |

**세 예측기가 크게 갈리는 cell**: (a) N=12 BASE 재사용(0.404 / 0.485 / 0.507)과 그에 따른 N=12 비의 방향(해석은 BASE 비용을 더 낮게, 시뮬레이터는 더 높게 본다 — turn당 A′ 563 대 547 ms), (b) N=6 BATCHONLY 비(해석 0.9834 대 시뮬 0.9941), (c) N=6·12 순위의 1위(해석 DP, 시뮬 TUNED). sim 기본과 sim 관측은 N ≤ 8에서 같고 N ≥ 10에서 0.004–0.008 갈린다.

## 5. 판정 기준 (제안)

확증 cell = N ∈ {6, 8, 10}. **N = 12는 모든 항목에서 탐색**(모형 적용 범위 경계, B2 가정 n ≤ M이 BASE에서 깨짐).

### 5.1 재사용률 — 확증(해석 v1)

- cell (N, 구성)의 관측 = replicate 5개 합산 비율. 확증 cell 9개(3 N × BASE·BATCHONLY·TUNED) + DP cell(compile된 경우).
- **PASS ⇔ 확증 cell의 90 % 이상(9개면 9/9, 12개면 11/12)에서 |예측 − 관측| ≤ 0.10, 그리고 평균 부호 오차 |mean(예측 − 관측)| ≤ 0.05(보정: 계통 편향 없음).**
- 근거: 0.10은 cell당 요청 수(≈ 500–800)에서 표본 오차(±0.03)보다 크고, 개발 집합에서 v1의 전체 예측 합이 관측과 2 % 차였던 것([TASK73](TASK73.md))을 감안한 cell 단위 허용. 0.05 편향 한계는 계통적 과대·과소를 따로 잡는다.
- 보고: sim 두 예측기의 같은 지표, 요청 단위 보정(v1 기록 상태 입력, [TASK73](TASK73.md) A4 방식).
- 실패 시: v1의 steady-state 근사(Poisson 할당, 지수 잔여 체류, λ 일정)가 steady-state 부하에서도 부족하다. 정확 추적기(`track_target`)가 로그에서 맞는지 먼저 보고(맞으면 전이 규칙이 아니라 할당 과정 근사의 문제), λ·μ 가정 중 어느 쪽인지 가른다.

### 5.2 BASE 대비 비용 비 — 확증(예측기별)

- 확증 cell 6개(3 N × BATCHONLY·TUNED) + DP cell. 관측 = 중앙 ratio m, 95 % CI [l, u].
- **cell 기본 기준(원고 확증 기준 계승)**: |예측 − m| ≤ 0.03, 그리고 방향 일치(sign(1 − 예측) = sign(1 − m)) — 단 CI가 1을 포함하면 방향 대신 |예측 − 1| ≤ 0.03.
- **강화 기준(replicate 5회 활용)**: 예측이 [l − 0.01, u + 0.01] 안.
- **예측기별 PASS ⇔ 모든 확증 cell이 기본 기준을 통과하고, 강화 기준을 5/6(DP 포함 시 그에 비례, 83 % 이상) 통과.** 해석·sim 기본·sim 관측 각각 판정한다. **주 예측기는 해석**(논문의 "모형 기반" 주장), sim 기본은 원고 검증 계승.
- 실패 시: 해석이 실패하고 시뮬레이터가 통과하면 "근사가 깨지는 영역"이 이 부하에 있다는 뜻이고, 둘 다 실패하면 공통 입력(step·prefill 비용 모형, 미측정 폭 보간)을 의심한다.

### 5.3 구성 순위 — 확증(해석)

- N ∈ {6, 8, 10}마다 구성 쌍 (A, B)의 짝 비 A/B(replicate별)의 중앙값과 bootstrap CI. **CI가 1을 포함하지 않는 쌍만 '해소된 쌍'**으로 센다.
- **PASS ⇔ 해소된 모든 쌍에서 해석 예측 순서가 관측 순서와 같다.** 해소된 쌍이 N마다 0이면 그 N은 `UNRESOLVED`.
- 예측(참고): 해석 기준 BASE는 모든 N에서 가장 비싸다 — BASE를 포함한 쌍은 해소될 것으로, BATCHONLY·TUNED·DP 사이 쌍(예측 차 0.3–1 %)은 대부분 미해소로 본다.
- 실패 시: 모형이 구성 선택을 잘못 안내한다 — 논문의 모형 기반 설정 선택 주장이 이 부하에서 성립하지 않는다.

### 5.4 DP 격자 대 TUNED — 확증(compile된 N)

- 예측(해석): DP/TUNED turn당 A′ 비 = N=6 0.9918, N=8 0.9960, N=10 0.9970, N=12 0.9984(0.2–0.8 % 이득). sim 기본(= sim 관측)은 N=6 1.0019(DP가 더 비쌈), N=8 0.9872, N=10 0.9991, N=12 1.0120.
- 관측: 짝 비 DP/TUNED 중앙값과 CI.
- **PASS ⇔ u < 1**(DP가 유의하게 싸다). **FAIL ⇔ l > 1**. 그 밖 `INCONCLUSIVE`(효과가 해상도 아래).
- **사전 예측: `INCONCLUSIVE`** — 예측 이득(≤ 0.8 %)이 replicate 5회의 CI 폭보다 작을 것이다(파일럿의 짝 ratio 산포 참조).
- 실패 시(`FAIL`): 모형 예측 h로 고른 격자가 기존 격자보다 나쁘다 — h 예측 또는 보간된 step 비용이 틀렸다.

### 5.5 가설 H-sim — 확증

TASK74에서 나온 가설: 원고의 계통적 양의 예측 오차(원고 8개 모두 `e > 0`, |e| 0.0058–0.0364, 중앙값 0.0130)가 동시 도착의 admission 순서·도착 시각 가정에서 왔다면, 동시 도착이 드문 steady state에서는 오차가 한쪽 부호로 몰리지 않고 작아야 한다.

- 대상: sim 기본의 `e = m − 예측`(BASE 대비 비, 확증 cell 6개 + DP cell).
- **(a) 부호**: 양수 수 k에 대한 양측 이항 검정(p = 0.5) p ≥ 0.05 — 6 cell이면 k ∈ {1, …, 5}.
- **(b) 크기**: |e|의 중앙값 < 0.0130(원고 8개의 중앙값).
- **SUPPORTED ⇔ (a) ∧ (b).** (b)만 성립하면 `PARTIAL`, 그 밖 `NOT_SUPPORTED`.
- 실패 시: 계통 오차의 원인은 동시 도착 가정이 아니다. 다음 후보 — [TASK74](TASK74.md) 목록의 (2) 미측정 bucket 비용 보간, (3) 채널 A′ 고정 오버헤드, (4) 재도착 되먹임.

### 5.6 h(n)·padding — 확증(해석 B2)

- **PASS ⇔ 확증 cell 9개(DP 포함 시 더)에서 예측 h와 관측 h의 TVD 중앙값 ≤ 0.10, 최댓값 ≤ 0.20.** 근거: 비정상 원고 조건에서 TVD 중앙값이 0.248이었다([TASK72](TASK72.md) R4); steady state에서 B2가 본래 가정 안에 있다면 절반 이하로 내려와야 한다.
- 보고: padding 비 |예측 − 관측|, sim 두 예측기의 TVD.
- 실패 시: B2의 곱 형태(PS 무감응성, prefill 균일 감속)가 steady state에서도 부족하다.

### 5.7 W (prefill 간섭) — 탐색

- 예측: 해석 B4 `E[P]·E[K_arr]`, 시뮬레이터 원고 식 (9) `Σ P̂·K̂ / 요청 수`(JSON의 `W_per_turn_s`). 예: N=8 TUNED 해석 239 ms / sim 217 ms, N=10 BASE 531 / 499 ms.
- 판정하지 않는다. 측정 정의(§3)가 처음 쓰이는 것이라, 예측 대 측정 비와 cell 간 순서 상관만 보고한다. B4의 독립 가정(P와 K) 편향 방향(양의 공분산이면 예측이 과소)도 함께 본다.

### 5.8 무효 조건

lifecycle 검사(파일럿과 같음: runner exit 0, `stopped_by = window`, 고갈 slot 0, 구간 온라인 = 재계산, 평가 끝 이후 발행 0, HTTP 오류 0, plan SHA 일치) 중 하나라도 어긋나면 그 lifecycle은 `INVALID`, 재실행 규칙은 측정 지시문에서 정한다. 정상성(평가 구간 전·후반 h TVD, 재사용률 차)은 보고만 한다.

## 6. 예산

60 lifecycle × 파일럿 실측 lifecycle 시간(3.5–4.2 분, [TASK79](TASK79.md)) ≈ **3.5–4.2 h** (DP 격자 N개당 +5 lifecycle ≈ +0.3 h; 권고안 (a) N=6·8 compile이면 70 lifecycle ≈ 4.1–4.9 h, compile 2회 ≈ 16 분 추가). 재시도 여유 ×1.5를 두어도 하루 안에 끝난다.

## 개정 이력

- 2026-09-29 초판 (측정 전, 파일럿 판정 [TASK79](TASK79.md) 후). 예측 계산은 파일럿 측정 중(18:45경) 파일럿 산출을 읽지 않고 수행했다.
