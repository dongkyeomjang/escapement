# GPU multi-turn steady-state 본 실험 — blind 예측과 판정 기준 선등록

작성: 2026-09-29, GPU 지시문 G-03 작업 C ([GTASK09](GTASK09.md)).

**이 문서의 성격**
- **본 측정은 하지 않았다.** 이 문서는 Advisor 검토 뒤 G-04에서 측정할 실험의 plan·예측·판정 기준을 측정 전에 고정한다.
- 기준은 **제안**이다. Advisor가 바꾸면 측정 전에 개정 commit한다.
- 예측은 파일럿([GPU_MT_PILOT_PREREG.md](GPU_MT_PILOT_PREREG.md)) 전에 계산했고, 파일럿 산출을 읽지 않는다.

**NPU 지시문 05 개정 2 원문 부재**
- G-03 §5.4가 인용하는 "NPU 지시문 05의 개정 2"(영 예측기 대비 skill 조건) 원문은 이 저장소에 없다.
- 이 문서는 G-03 본문의 설명을 따른다. 기존 기준에 **영 예측기 대비 skill 조건을 AND로** 붙이고, 영 예측기는 측정 전에 정해지는 값으로만 둔다.

## 1. plan (고정)

- **확증 N = 20, 22, 24**(GTASK08). **탐색 N = 26**: 붕괴 경계 cell이며, Advisor가 추가를 결정할 때만 측정한다.
- replicate r = 0..4, seed `20262300 + i`(i = 순번), plan_id `gmain-n{N}-r{r}`.
- 생성 규칙은 NPU와 같다(`make_plan.build`, K = 8, 첫 prompt U(800,1600), segment 8, 생성 U(32,256), gap `toolmix` 상한 60 s, slot당 세션 16). `cycle_s`는 해석 모형의 POOL 예측이다.
- 파일: `experiments/gpu/multiturn/plans/main/gmain-n{N}-r{r}.json` 20개와 `INDEX.json`(내용·파일 SHA256, 최대 context 3,064–3,274 token, preemption 불가에 필요한 block 1,537–1,641 ≤ 1,900).
- 같은 (N, r)의 plan을 모든 구성이 쓴다(짝 설계).
- seed 범위는 NPU(`20261200–20261524`), GPU 선정(`20262100–26`), 파일럿(`20262500–02`)과 겹치지 않는다.

## 2. 구성 (GTASK08)

| 구성 | `--num-gpu-blocks-override` | `--max-num-seqs` | `cudagraph_capture_sizes` | budget |
|---|---|---|---|---|
| BASE | 1,900 | 8 | (1,2,4,8,16) | 2,048 |
| POOL | 2,300 | 8 | (1,2,4,8,16) | 2,048 |
| POOL+GRID | 2,300 | 8 | (1,5,7,8,16) (N = 20·22·24) | 2,048 |

- lifecycle은 3 N × 3 구성 × 5 = **45개**다(N=26 추가 시 BASE·POOL × 5 = +10).
- 순서 제안은 `plans/main/SCHEDULE_PROPOSED.json`이다. replicate 블록 안에서 9 cell의 순서를 seed `20262410`으로 섞었다. streaming 여부는 파일럿 판정으로 정한다. 최종 순서는 G-04에서 고정한다.
- 공통 조건
  - server 인자는 `launch.lifecycle.base_args`를 쓴다(revision `1cfa9a72…`, bf16, `--max-model-len 8192`, `--seed 20260929`, `--enable-prompt-tokens-details`, block 16).
  - 관측 patch와 KV events는 켠다.
  - 카드는 uuid `GPU-4485e769…` 하나만 쓴다.

## 3. 측정 정의

[GPU_MULTITURN_DESIGN.md](GPU_MULTITURN_DESIGN.md) §5와 `experiments/gpu/multiturn/gpu_mt_measure.py`를 따른다. 파일럿에서 동작을 확인한 정의다.

- **재사용률**: 평가 구간 turn ≥ 1 요청 중 `cached > 0`인 비율. cell (N, 구성)마다 replicate 5개를 합산한다.
- **재사용 token 비율**, **hit 분포**(0 / 부분 / 전체)도 같은 방식으로 합산한다.
- **turn당 A′-GPU**: server 창 `[GSTEP]` × GTASK05 비용 모형. 하한 `lo`와 상한 `hi`를 모두 계산한다.
- **BASE 대비 비**: 같은 (N, r)의 turn당 A′-GPU 비. replicate 5개의 **중앙값** m과 **95 % percentile bootstrap CI** [l, u]를 구한다(replicate 복원 추출 10,000회, seed `20262420`). bound마다 따로 계산한다.
- **h(n)**: 평가 server 창의 `[GSTEP]` step 가중 `reqs` 분포. **padding** = Σ(padded − toks)/Σ padded.
- **혼합 step 간섭**: Σ(혼합 step 가격 − 같은 decode 수의 decode 기준선) × decode 수 / 평가 구간 요청 수. 하한·상한을 모두 계산한다.

## 4. 예측 (세 예측기, 측정 전 고정)

**예측 산출물**
- 전체 수치: `experiments/gpu/multiturn/plans/PREDICTIONS.json`(이 commit, SHA256 `1be9a991…3e7c71a45f`)
- 산출 script: `predict_mt.py`. 요약은 `summarize_predictions.py`로 뽑는다.
- 입력은 GTASK01–05의 상수, `selection.json`, §1 plan뿐이다.

**예측기**
1. **해석**: v1 GPU 인스턴스. B2 + B1 LRU(`lru_block_survival`, log 공간 wrapper) + B3 + B4.
2. **sim LRU**: GPU 의미론 시뮬레이터.
3. **sim FIFO**: 2와 같은 코드이며, 축출 순서만 할당 순서 FIFO로 바꿨다(반사실).

모든 예측은 비용 bound `lo`/`hi` 두 값으로 계산했다.

### 4.1 재사용률 (turn ≥ 1), lo / hi

| N | 구성 | 해석 | sim LRU | sim FIFO | LRU − FIFO |
|---|---|---|---|---|---|
| 20 | BASE | 0.844 / 0.844 | 0.857 / 0.857 | 0.761 / 0.747 | 0.096 / 0.109 |
| 20 | POOL | 0.877 / 0.878 | 0.904 / 0.905 | 0.819 / 0.826 | 0.085 / 0.079 |
| 20 | POOL+GRID | 0.877 / 0.877 | 0.900 / 0.903 | 0.821 / 0.818 | 0.079 / 0.085 |
| 22 | BASE | 0.828 / 0.828 | 0.849 / 0.848 | 0.735 / 0.724 | 0.115 / 0.124 |
| 22 | POOL | 0.862 / 0.863 | 0.895 / 0.899 | 0.787 / 0.790 | 0.107 / 0.109 |
| 22 | POOL+GRID | 0.862 / 0.862 | 0.892 / 0.897 | 0.788 / 0.793 | 0.104 / 0.104 |
| 24 | BASE | 0.807 / 0.807 | 0.753 / 0.751 | 0.611 / 0.608 | 0.142 / 0.143 |
| 24 | POOL | 0.850 / 0.850 | 0.861 / 0.863 | 0.717 / 0.706 | 0.144 / 0.157 |
| 24 | POOL+GRID | 0.850 / 0.850 | 0.862 / 0.862 | 0.702 / 0.693 | 0.160 / 0.170 |
| 26 (탐색) | BASE | 0.786 / 0.785 | 0.657 / 0.637 | 0.552 / 0.550 | 0.106 / 0.087 |
| 26 (탐색) | POOL | 0.831 / 0.831 | 0.833 / 0.835 | 0.674 / 0.659 | 0.160 / 0.176 |

- **재사용 token 비율**(lo)은 해석 0.80–0.87, sim LRU 0.73–0.90, sim FIFO 0.54–0.77이다.
- **hit 분포**(sim lo, 확증 cell)
  - LRU는 부분 hit가 0.4–5.6 %로 드물고 대부분 0 아니면 전체다.
  - FIFO는 부분 hit가 9.8–13.9 %다. 할당 순서 축출은 사슬의 중간을 끊는다.

### 4.2 turn당 A′-GPU (ms, lo / hi)와 BASE 대비 비

| N | 구성 | 해석 ms | 해석 비 | sim LRU ms | sim LRU 비 | sim FIFO 비 |
|---|---|---|---|---|---|---|
| 20 | BASE | 305.9 / 307.0 | 1 | 305.5 / 304.9 | 1 | 1 |
| 20 | POOL | 303.7 / 304.7 | 0.9928 / 0.9924 | 302.0 / 302.6 | 0.9886 / 0.9924 | 0.9938 / 0.9788 |
| 20 | POOL+GRID | 303.4 / 304.4 | 0.9919 / 0.9915 | 300.5 / 302.6 | 0.9836 / 0.9925 | 0.9922 / 0.9823 |
| 22 | BASE | 292.9 / 294.3 | 1 | 295.8 / 297.3 | 1 | 1 |
| 22 | POOL | 290.3 / 291.4 | 0.9909 / 0.9903 | 291.0 / 292.4 | 0.9839 / 0.9834 | 0.9890 / 0.9777 |
| 22 | POOL+GRID | 290.1 / 291.2 | 0.9903 / 0.9897 | 290.9 / 291.6 | 0.9835 / 0.9807 | 0.9833 / 0.9777 |
| 24 | BASE | 284.1 / 285.8 | 1 | 289.9 / 292.3 | 1 | 1 |
| 24 | POOL | 280.1 / 281.5 | 0.9858 / 0.9850 | 277.8 / 279.2 | 0.9583 / 0.9552 | 0.9664 / 0.9713 |
| 24 | POOL+GRID | 280.0 / 281.4 | 0.9855 / 0.9847 | 277.4 / 279.7 | 0.9568 / 0.9570 | 0.9741 / 0.9707 |
| 26 (탐색) | POOL | 277.1 / 278.7 | 0.9838 / 0.9829 | 284.5 / 286.1 | 0.9393 / 0.9364 | 0.9643 / 0.9697 |

- sim LRU의 replicate별 POOL/BASE 비(lo)는 다음과 같다. 효과(1–4 %)가 replicate 간 산포와 같은 자릿수다.
  - N=20: 0.978–1.002
  - N=22: 0.965–0.995
  - N=24: 0.893–1.005
- **구성 순위(해석, 두 bound 같음)**: 모든 N에서 POOL+GRID < POOL < BASE다. POOL+GRID/POOL 비는 해석 0.9991–0.9997, sim LRU 0.9950–1.0018이다.

### 4.3 §2.1 구간(PIECEWISE 증분 [0, 1.5] ms)의 최대 영향 (G-03 §2.1 보고)

- 확증 cell에서 PIECEWISE 혼합 step은 turn당 **0.04–0.09개**뿐이다(sim LRU lo).
- 재도착 요청의 계산량(9–24 token)에 running 약 7을 더하면 16 token을 넘어, 대부분의 혼합 step은 PIECEWISE가 아니라 **eager**로 실행된다.
- 따라서 구간의 최대 영향은 **turn당 0.05–0.13 ms**, 즉 turn당 비용의 **0.02–0.04 %**다. 이 구간 폭이 결론을 바꿀 cell은 없을 것으로 예측한다.
- eager 혼합 증분 구간(lag-1 대 3-step 창)까지 합친 lo–hi 차는 turn당 −0.6 ~ +2.7 ms(≤ 1 %)다. 음수는 bound에 따라 시뮬레이터 궤적이 달라진 탓이다.

### 4.4 h(n)·padding·간섭

- **padding(lo)**
  - BASE: 해석 0.026–0.091, sim LRU 0.005–0.026
  - POOL+GRID: 해석 0.008–0.034, sim LRU 0.002–0.010
- 해석 B2의 h는 n = 8에 59–85 %가 몰린다(GTASK08).
- **혼합 step 간섭(lo, ms/turn)**: 해석 165–248, sim LRU 136–272, sim FIFO 240–414. N과 BASE에서 크다(miss prefill이 decode를 늦춘다).
- 전체 수치는 JSON에 있다.

## 5. 판정 기준 (제안)

**공통 규칙**
- 확증 cell = N ∈ {20, 22, 24}. **N = 26은 모든 항목에서 탐색**이다.
- **bound 규칙**
  - 비용이 들어가는 판정은 `lo` 예측 대 `lo` 관측, `hi` 예측 대 `hi` 관측으로 각각 한다.
  - **PASS는 두 bound 모두에서 성립해야 한다.**
  - 두 bound의 판정이 다른 cell은 "구간 민감"으로 따로 표기한다(G-03 §2.1).
- **영 예측기**(측정 전에 정해지는 값만)
  - 재사용률: **같은 예측기의 같은 N BASE 예측값을 모든 구성에 쓴다**(구성 무관 상수).
  - 비용 비: **1.0**
  - h(n): **{1..8} 균등 분포**(부하 정보 없는 사전분포)

### 5.1 재사용률 — 확증 (예측기별: 해석이 주, sim LRU 병기)

- cell 9개(3 N × 3 구성)이고, 관측 = replicate 5개 합산 비율이다.
- **PASS ⇔ (a) ∧ (b) ∧ (c)**
  - (a) 9/9 cell에서 |예측 − 관측| ≤ 0.10
  - (b) |mean(예측 − 관측)| ≤ 0.05
  - (c) **skill**: Σ|예측 − 관측| < Σ|영 − 관측|
  - 각 bound에서 판정한다(예측이 bound에 거의 무관하므로 사실상 같다).
- **근거**
  - 0.10은 cell당 turn ≥ 1 요청 수(replicate 5개 합 약 1,500–2,000)의 표본 오차(±0.02; 예측상 cell당 약 1,700–1,800)보다 크다. NPU 기준(지시문 04)을 계승한 값이다.
  - 확증 cell이 포화 근처(B2 가정 경계)라는 점은 기준을 바꾸지 않고 해석에서 다룬다.
- **보고**: 재사용 token 비율과 hit 분포의 예측 대 관측, sim FIFO의 같은 지표
- **실패 시**
  - 해석이 실패하고 sim LRU가 통과하면, v1 평균장 근사(할당률 Poisson, 앞선 touch의 residual 근사, B2 FCFS 근사)가 포화 근처에서 부족한 것이다. 되먹임을 넣은 모형이 필요하다.
  - 둘 다 실패하면 공통 입력(step 비용, gap 법칙, scheduler 의미론 재진술)을 의심한다.
  - (c)만 실패하면, 예측이 구성 간 차이를 영 예측기보다 잘 가르지 못한다는 뜻이다.

### 5.2 BASE 대비 비용 비 — 확증 (예측기별: 해석이 주, sim LRU 병기)

- cell 6개(3 N × POOL·POOL+GRID)다.
- **기본 기준**: |예측 − m| ≤ 0.03이고 방향이 일치한다(sign(1 − 예측) = sign(1 − m)). 단 CI가 1을 포함하면 방향 대신 |예측 − 1| ≤ 0.03을 본다.
- **강화 기준**: 예측 ∈ [l − 0.01, u + 0.01]
- **skill**: Σ|예측 − m| < Σ|1 − m|
- **PASS ⇔ 6/6 기본 ∧ 강화 5/6 이상 ∧ skill**(두 bound 모두)
- **`NOT_INFORMATIVE` ⇔ 6개 cell의 CI가 모두 1을 포함**(구성 효과가 해상도 아래)
  - 이 경우 PASS/FAIL 대신 이 판정을 쓰고, 기본·강화 결과는 보고만 한다.
  - **사전 예측: N = 20·22는 CI가 1을 포함할 가능성이 크다.** 예측 효과는 1 %이고 sim replicate 산포는 0.97–1.00이다.
- **실패 시**
  - 해석만 실패하면, 이 부하에서 근사가 깨지는 영역이 있다는 뜻이다.
  - 둘 다 실패하면 GTASK05 비용 모형(특히 eager 혼합 증분)의 전이 가능성을 의심한다.

### 5.3 구성 순위 — 확증 (해석)

- N마다 쌍 (BASE, POOL), (BASE, POOL+GRID), (POOL, POOL+GRID)의 짝 비 중앙값과 bootstrap CI를 구한다.
- **CI가 1을 포함하지 않는 쌍만 '해소된 쌍'**이다.
- **PASS ⇔ 해소된 모든 쌍에서 해석 예측 순서 = 관측 순서**이고, 해소된 쌍이 N마다 0이면 그 N은 `UNRESOLVED`다.
- skill 조건은 적용하지 않는다(순위의 영 예측기 "모두 같음"은 해소된 쌍에서 정의상 틀린다).
- **사전 예측**: N=24의 BASE 포함 쌍만 해소되고, POOL 대 POOL+GRID는 모든 N에서 미해소일 것이다.
- **실패 시**: 모형이 구성 선택을 잘못 안내한다.

### 5.4 POOL+GRID 대 POOL — 확증

- 짝 비 POOL+GRID/POOL의 중앙값과 CI를 구한다.
- **PASS ⇔ u < 1**, **FAIL ⇔ l > 1**, 그 밖은 `INCONCLUSIVE`다.
- **사전 예측: `INCONCLUSIVE`**. 해석 예측 이득은 0.03–0.09 %다. GTASK05의 `F[b]`가 2 ≤ b ≤ 8에서 13.17–13.29 ms로 평탄하기 때문이다.
- 실패 시(`FAIL`): 격자 선택이 비용을 늘린다. PIECEWISE·eager 경계 이동(5·7 capture가 혼합 step mode를 바꿈)의 영향을 의심한다.

### 5.5 LRU 대 FIFO 판별 — 확증 (G-03 §5.3)

- **판별 가능성(측정 전 계산)**
  - sim LRU와 sim FIFO의 재사용 예측이 확증 9 cell **모두**에서 0.079–0.170 갈린다(두 bound).
  - 따라서 `NOT_TESTABLE`이 아니다.
- **분리 cell**: |sim LRU − sim FIFO| ≥ 0.07(두 bound 모두)인 확증 cell. 현재 9개다.
- 관측 재사용률(cell 합산)에 대해 다음을 구한다. 예측은 두 bound의 평균이다.
  - d_L = |관측 − sim LRU|
  - d_F = |관측 − sim FIFO|
- **`LRU_SUPPORTED` ⇔ 분리 cell의 7/9 이상에서 d_L < d_F ∧ Σd_L < Σd_F**
- `FIFO_SUPPORTED`는 대칭이고, 그 밖은 `INCONCLUSIVE`다.
- **사전 예측: `LRU_SUPPORTED`**. source(`block_pool.py:347,431`)와 GTASK04가 LRU 해제 순서를 말한다.
- **보고**
  - 재사용 token 비율, 부분 hit 비율로 같은 비교를 한다. FIFO는 부분 hit를 10–14 % 예측하고 LRU는 1–6 %를 예측한다. 이것이 두 번째 판별 신호다.
  - **탐색**: KV events `BlockRemoved` 순서를 요청 해제 순서·할당 순서와 대조한다. 대조 정의는 G-04 전에 분석 코드와 함께 고정한다.
- **해석 제한**: 이 비교는 "어느 시뮬레이터 변형이 더 맞는가"다. sim LRU가 다른 이유로 치우치면(예: N=24 BASE 해석 0.807 대 sim LRU 0.753) 판정이 흔들릴 수 있으므로, 결론은 해석 v1과 함께 읽는다.
- **실패 시**
  - `FIFO_SUPPORTED`면 source 감사(GTASK01) 또는 시뮬레이터의 LRU 재진술이 틀렸다.
  - `INCONCLUSIVE`면 다른 오차가 축출 순서 효과를 가린다.

### 5.6 h(n)·padding — 확증 (해석 B2)

- **PASS ⇔ 확증 9 cell에서 예측 h와 관측 h의 TVD 중앙값 ≤ 0.10 ∧ 최댓값 ≤ 0.20 ∧ skill**
  - skill: TVD 중앙값 < 균등 분포 h의 TVD 중앙값
- 관측 h는 `[GSTEP]` `reqs`이며 혼합 step의 prefill 요청을 포함한다. B2 h는 running decode 수다. 이 정의 차이는 판정 전에 알려진 편향으로 적어 둔다.
- 보고: padding의 |예측 − 관측|, sim LRU의 TVD
- 실패 시: B2 곱 형태가 포화 근처(n ≈ M, FCFS 대기)에서 부족하다.

### 5.7 혼합 step 간섭 — 탐색

- 예측 대 관측 비와 cell 간 순위 상관을 보고한다(두 bound). 판정하지 않는다.

### 5.8 무효 조건

- lifecycle은 다음 중 하나라도 어긋나면 `INVALID`다.
  - runner 유효(`windows.json` `valid`): `stopped_by = window`, 고갈 slot 0, 카드 uuid, preemption 증분 0, GPU 외부 process
  - 구간 온라인 = 재계산, 평가 끝 이후 발행 0, HTTP 오류 0, 생성 id 수 일치
  - client–server join 누락 0, plan SHA 일치
- 재실행 규칙은 G-04에서 정한다.
- 정상성(평가 구간 전·후반 h TVD, 재사용률 차)은 보고만 한다.

## 6. 예산

- lifecycle당 약 4.5–5분을 예상한다: server 기동·capture 약 60–70 s + warm-up 약 50–70 s + 평가 120 s + drain.
- 45 lifecycle ≈ **3.5–4 h**이고, N = 26 추가 시 +10 ≈ +0.8 h다.
- 파일럿이 실측 lifecycle 시간을 준다.

## 개정 이력

- 2026-09-29 초판 (측정 전, 파일럿 전)

## 7. 개정 1 (2026-09-30, GPU 지시문 G-04, 본 측정 전)

**우선순위**: 이 절은 §5의 해당 부분보다 우선한다. **예측값은 바꾸지 않는다**(`PREDICTIONS.json`, `2bef619`, SHA256 `1be9a991…`).

### 7.1 이유

- GTASK09는 NPU 지시문 05 개정 2의 원문을 찾지 못했다. 원문은 `main` `5f62fb4`(`MULTITURN_MAIN_PREREG.md` §7)에 있었고, 그 전의 merge(`fe8a4df`)에서 보이지 않았다.
- 그래서 GPU의 skill 조건이 NPU보다 약하게 쓰였다(`<`, 영 예측기와 비슷하기만 하면 통과).
- merge `eb6343c`로 원문을 반영하고, 두 기판이 같은 강도의 기준을 쓰도록 고친다.

### 7.2 §5.1 재사용률 skill

- **영 예측기**: **NPU 본 실험([TASK82](../TASK82.md)) 확증 cell의 turn ≥ 1 합산 재사용률**을 모든 GPU cell에 같은 상수로 쓴다. 의미는 "GPU도 NPU처럼 재사용한다"는 기판 무관 예측이다.
  - 계산: TASK82 결과표의 확증 10 cell(N = 6·8·10 × BASE·BATCHONLY·TUNED + DP N8)의 r0–r4 합산 hit / turn ≥ 1 = (437 + 500 + 500 + 541 + 620 + 620 + 619 + 545 + 691 + 698) / (533 + 542 + 543 + 695 + 704 + 702 + 704 + 780 + 800 + 809) = **5,771 / 6,812 = 0.84718**
  - 이 값은 GPU 측정 전에 정해져 있다.
- **skill**: `MAE(예측기) ≤ 0.5 × MAE(영)`, 확증 9 cell, bound마다 판정한다.
  - **`MAE(영) < 0.05`이면 skill은 `NOT_INFORMATIVE`**다. 이때는 (a)(b)로만 판정한다.
  - 측정 전 참고: 확증 cell 예측 재사용이 0.75–0.90이므로 이 규칙이 적용될 가능성이 크다.
- **기존 영 예측기**(같은 예측기의 같은 N BASE 값)는 판정에서 빼고 **구성 차이 설명력** 보고로 남긴다. N별로 예측 (POOL − BASE) 재사용 차와 관측 차를 비교하고, 기존 합 비교(Σ|예측 − 관측| 대 Σ|BASE 예측 − 관측|)도 병기한다.
- **최종 표기(NPU §7.3과 같음)**

| 기존 기준 | skill | 최종 표기 |
|---|---|---|
| FAIL | — | `FAIL` |
| PASS | PASS | `PASS` |
| PASS | `NOT_INFORMATIVE` | `PASS (skill NOT_INFORMATIVE)` |
| PASS | FAIL | `NOT_CONFIRMED (base PASS, skill FAIL)` |

  이 표기는 §5.2·§5.6에도 같이 쓴다.

### 7.3 §5.2 비용 비 skill

- **skill**: `Σ|예측 − m| ≤ 0.5 × Σ|1 − m|`(확증 6 cell, 예측기별, bound별)
- **`NOT_INFORMATIVE` ⇔ Σ|1 − m| / 6 < 0.01**(NPU와 같은 규칙)
- 기존 규칙(6 cell CI가 모두 1을 포함하면 `NOT_INFORMATIVE`)의 결과도 병기한다.

### 7.4 §5.6 h(n)

- **skill**: `TVD 중앙값(해석) ≤ 0.5 × TVD 중앙값(균등 {1..8})`
- **관측 h 정의(판정용)**: **step별 decode 요청 수**의 step 가중 분포이며, decode가 없는 step은 뺀다.
  - decode 수 = `maxq == 1`이면 `reqs`, 아니면 `reqs − k`다.
  - k = 직전 `[GSTEP]` 이후의 `[GPFX] ALLOC` 줄 수(이 step에 admission된 요청)이고, 최소 1이다.
  - 가격 채널(`gpu_mt_measure`)의 decode 수 규칙과 같다.
  - **알려진 한계**: 긴 prompt의 두 번째 chunk는 ALLOC 줄이 없다. 같은 step에 새 admission과 이어지는 chunk가 함께 있으면 decode 수를 1 크게 센다. 계기 점검·파일럿에서 step mode 예측 불일치가 0이었으므로 드물다고 본다.
- 기존 정의(`reqs`)의 TVD도 병기한다.
- 구현: `main_judge.py` `decode_h`

### 7.5 재실행 규칙

- `INVALID` lifecycle은 **같은 plan으로 1회만** 재실행한다(`<tag>.retry1`).
- 두 번째도 `INVALID`면 그 replicate는 빠지고, 그 cell·쌍은 남은 replicate로 판정하며 수를 표기한다.
- `INVALID`는 §5.8(runner 유효와 측정 모듈의 구간·join·발행·HTTP·생성 길이 검사)로 정한다.
- 첫 순서표를 다 돈 뒤 한 번에 재실행한다.

### 7.6 실행 순서

- `plans/main/ORDER.json`(`make_main_order.py`, seed 20262410, 55 lifecycle, SHA256 `95aac4b5…`)을 쓴다.
- 5 round로 나뉘고, round k에 블록 (N = 20·22·24·26, r = k)을 무작위 순서로 돈다.
- 블록 안 구성 순서는 N = 20·22·24에서 replicate마다 서로 다른 순열(3! = 6개 중 5개 비복원 추출)이고, N = 26은 BASE·POOL 교대다.
- 모든 lifecycle은 streaming이다(파일럿 `EQUIVALENT`).
- `SCHEDULE_PROPOSED.json`(GTASK09)은 이 순서표로 대체한다.

### 7.7 판정 시점

- 모든 lifecycle과 재실행이 끝난 뒤 `main_judge.py`로 한 번 계산한다.
- 측정 중에는 유효성 검사만 본다.
- 측정 중 HEAD를 바꾸지 않는다.
- 판정 전 script 버그로 수정이 필요하면 멈추고 고친 뒤 무엇을 고쳤는지 기록한다.
- bootstrap은 percentile, replicate 복원 추출 10,000회, cell·쌍마다 새 `random.Random(20262420)`이다.

### 7.8 추가 보고 (판정 없음)

- **H-sim 지표**: sim LRU의 비용 비 오차 `e = m − 예측`의 부호 수와 |e| 중앙값(확증 6 cell, 두 bound). NPU TASK82(음 6/7, 중앙 0.0055)와 나란히 보고한다.
- **N = 26 탐색**: 세 예측기 대 관측 재사용, POOL/BASE 비, N=24 → 26 BASE 재사용 하락폭
- **가격 채널 대 직접 dispatch 채널** 비(lifecycle별)
- **KV events 고아 축출 비율(탐색, §5.5 보고 항목)**
  - 정의: `BlockRemoved` 사건 중, 축출되는 순간 그 block의 자식 block(`BlockStored`의 `block_hashes` 사슬·`parent_block_hash`로 복원)이 아직 캐시에 있는 비율이다.
  - source 규칙에서 나오는 기대는 해제 순서 LRU ≈ 0(요청 반납은 tail 먼저), 할당 순서 FIFO는 높음(오래된 turn의 prefix block이 먼저 나감)이다.
  - 새 예측 계산은 하지 않는다.
- **사실 기록**: 판정 script는 파일럿 산출을 symlink로 엮은 가짜 run에서 코드 경로만 시험했다. 이 시험에서 파일럿의 고아 축출 비율(0.0)과 decode-only h의 TVD를 보게 됐다. 두 항목의 정의와 판정 기준은 이 지시문(G-04)과 §5.5 선등록(`2bef619`)이 정한 것이며, 그 값을 보고 바꾸지 않았다.

### 7.9 v1.1과 N = 26

- 이번 N = 26 탐색 결과는 NPU 쪽 v1.1(대기열 항) 개발에 쓰일 수 있다.
- 그래서 **v1.1 blind 검증에는 이 N = 26 plan(`gmain-n26-r*`)을 다시 쓰지 않는다**(GPU_INDEX에도 적는다).

### 개정 이력 추가

- 2026-09-30 개정 1 (본 측정 전, G-04): §7 — skill 조건을 NPU 개정 2와 정렬, NPU 영 재사용 0.84718, decode-only h, 재실행·순서·판정 시점, 추가 보고, 판정 script `main_judge.py`
