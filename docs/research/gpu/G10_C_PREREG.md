# G-10 작업 C — 긴 도구 출력에서 재사용량·비용 예측 선등록

작성: 2026-10-08. GPU 지시문 G-10 §5. 기록 TASK는 [GTASK25](GTASK25.md)다. **이 문서, 용량 계산, 후보 N 전체 예측과 선택, plan, 순서표, driver, 판정 script를 측정 전에 commit한다.** 측정은 작업 B 측정 뒤에 시작한다.

**지위**: 새 문맥 증가 조건의 선등록 검증이다. timing 입력은 이 조건을 위해 새로 잰 긴 문맥 계수(`c_long`, [G10_CTX_LONG_PREREG.md](G10_CTX_LONG_PREREG.md))를 쓰므로 **기존 모형 그대로의 외삽 검증이 아니다**(함수 형태는 그대로, 계수만 갱신). N·용량은 측정 전에 시뮬레이터 예측만으로 정했다.

## 1. 워크로드

| 조건 | 이전 생성 결과 | 호출 사이 추가 도구 결과 | tool-wait 상한 |
|---|---|---:|---:|
| SHORT_TOOL | 다음 prompt에 정확히 이어 붙임(token id) | 8 token | 60 s |
| LONG_TOOL | 같음 | **512 token** | 60 s |

- 8 turn, 첫 prompt U(800, 1600), 생성 U(32, 256), toolmix gap(상한 60 s) — GTASK09/20 법칙. 두 조건의 plan은 같은 `plan_id`·seed로 만들어 세션별 첫 prompt·생성 길이·tool wait·text seed가 **모두 같고 이후 segment 길이만 다르다**(`Distribution("fixed").draw`는 난수를 쓰지 않는다; `predict_c.py`가 세션·turn 단위로 assert). 새 도구 token은 `Random(text_seed)`의 [1000, 150000) id로 세션·turn마다 고유하다(다른 세션과 우연한 prefix 공유 없음). LONG의 처음 8 token은 SHORT의 8 token과 같다.
- 길이 한도: workload 법칙의 최대 prompt + 생성 = 1,600 + 7 × 512 + 8 × 256 = **7,232 ≤ 8,192**(`max_model_len`) → 목표 512를 그대로 쓴다(256 대체 불필요, 입력 길이만으로 결정). plan별 최대: SHORT 3,048–3,212, LONG 6,576–6,740(N = 24). runner는 `prompt_tokens`와 보낸 길이를 기록하므로 truncation을 검사한다.
- `cycle_s`(stagger·창 규칙)는 (N, r)마다 LONG plan의 해석 예측(GPU_LONG_KV, lo)으로 한 번 정하고 두 조건에 같이 쓴다.

## 2. 용량 (두 워크로드 공통)

- 규칙(GTASK08과 같음): `GPU_LONG_BASE = 1 + max_num_seqs · ⌈W/16⌉`, W = 법칙 최대 7,232 token.
  - null block 1개(`block_pool.py:176`, GTASK01), 16-token block 정렬.
  - 요청 하나가 잡는 block은 최대 ⌈(prompt + 생성 − 1)/16⌉ ≤ ⌈W/16⌉ = 452: 마지막 sampled token의 KV는 계산되지 않고(GTASK02 H5), async scheduling은 `max_tokens`에 도달한 요청에 추가 step을 잡지 않으며(`scheduler.py:370–383`), 추측 token이 없어 lookahead = 0(`scheduler.py:215`). hit block은 같은 요청의 block 목록에 들어가며 세션 간 공유가 없다.
  - 따라서 동시 실행 8개가 모두 최대 길이여도 1 + 8 × 452 = **3,617 block**이면 active 요청 preemption이 구조적으로 불가능하다(free queue의 cached block은 언제든 회수 가능).
- `GPU_LONG_KV = ⌈3,617 × 2,300 / 1,900⌉ = 4,379 block`.
- block당 KV 2.25 MiB(Qwen3-4B: 36 layer × 8 KV head × 128 × K/V × bf16 × 16 token) → 3,617 block 7.95 GiB, 4,379 block 9.62 GiB. 48 GiB 카드 안이다.
- 동시 실행 상한 8, 격자 (1,2,4,8,16), budget 2,048은 두 구성이 같다. 파일 `experiments/gpu/g10/plans_c/CONFIGS.json`(SHA256 `558a2a1277e52ed0…`), runner 이름 `GPU_LONG_BASE`·`GPU_LONG_KV`. 원고의 GPU_BASE/GPU_KV와 이름·용량·결과를 분리한다.

## 3. timing 입력과 N 선택

- LONG 문맥(최대 7,232)은 GTASK18 측정 범위(L ≤ 3,064)를 벗어나므로 독립 microbenchmark로 L ≤ 7,000을 쟀다(`ctx_long_result/summary.json`, commit `228ce77`, calibration seed 20264800대). F1 `c_long = 2.108 × 10⁻⁴ ms/token`(GTASK18 2.120 × 10⁻⁴), 잔차 ≤ 0.10 ms. 예측기: `gpu_mt_sim` LRU + `price + c_long·(Σ decode context − decodes·128)`(decode가 있는 step). 혼합 step·prefill의 문맥 의존은 모형에 없다.
- 후보 N ∈ {24, 28, 32, 36}, 각 5 plan(seed `20264200 + 10·idx(N) + r`). 선택 규칙: LONG_TOOL·GPU_LONG_BASE의 lo/hi 재사용률이 모두 [0.2, 0.8]이고, 두 설정 모두 GPU_LONG_KV가 0.05 이상 높은 후보 중 가장 작은 N.

| N | LONG·BASE 재사용 lo / hi | LONG·KV lo / hi | KV − BASE lo / hi | 적격 |
|---|---|---|---|---|
| **24** | 0.474 / 0.476 | 0.780 / 0.776 | 0.306 / 0.300 | **예 → 선택** |
| 28 | 0.047 / 0.035 | 0.322 / 0.298 | 0.274 / 0.264 | 아니오 |
| 32 | 0.012 / 0.012 | 0.156 / 0.147 | 0.144 / 0.135 | 아니오 |
| 36 | 0.000 / 0.000 | 0.001 / 0.000 | 0.001 / 0.000 | 아니오 |

- lo/hi를 재사용률의 상하한이라고 가정하지 않는다. 전체 예측: `plans_c/PREDICTIONS_C.json`(SHA256 `be0536f7f83537de…`), plan 색인 `plans_c/INDEX.json`(`4d207714de3d1898…`).

## 4. 동결 예측 (N = 24)

| 조건 | 구성 | bound | 요청 재사용 | token 재사용 | partial 비율 | 재조회 prefill 계산 token | 호출당 가격 (s) | 대기 평균 (s) |
|---|---|---|---|---|---|---|---|---|
| SHORT | BASE | lo / hi | 0.955 / 0.953 | 0.954 / 0.951 | 0.004 / 0.006 | 164,689 / 170,262 | 0.2670 / 0.2680 | 1.63 / 1.65 |
| SHORT | KV | lo / hi | 0.975 / 0.972 | 0.974 / 0.972 | 0.003 / 0.001 | 104,618 / 109,010 | 0.2648 / 0.2669 | 1.60 / 1.62 |
| LONG | BASE | lo / hi | 0.474 / 0.476 | 0.444 / 0.429 | 0.052 / 0.091 | 2,483,961 / 2,499,270 | 0.3898 / 0.3985 | 4.33 / 4.54 |
| LONG | KV | lo / hi | 0.780 / 0.776 | 0.758 / 0.741 | 0.049 / 0.056 | 1,584,131 / 1,611,785 | 0.3320 / 0.3424 | 3.41 / 3.57 |

| 조건 | R_PRED lo (replicate별) | R_PRED hi |
|---|---|---|
| SHORT_TOOL | **0.9935** (1.001, 0.993, 0.986, 0.996, 0.981) | **0.9990** |
| LONG_TOOL | **0.8657** (0.858, 0.870, 0.925, 0.745, 0.866) | **0.8623** |

- 재사용 pooled 비율은 시뮬레이터 자체의 분자·분모 합(5 plan)이다.

## 5. 측정

- 행렬: N = 24 × {SHORT_TOOL, LONG_TOOL} × {GPU_LONG_BASE, GPU_LONG_KV} × 5 paired replicate = **20 lifecycle**. 네 cell은 같은 세션별 계획을 쓴다.
- 순서 `plans_c/ORDER_C.json`(seed 20264260): replicate 순서를 섞고 replicate 안 4 cell은 서로 다른 순열 5개.
- runner·창·서버 재기동·관측은 작업 B와 같다(`--stream --exec-timing`). driver `run_c.sh`: 측정 → 재실행 → `judge_c.py` 1회 → `c_result/verdict.json`만 local commit.
- INVALID·재실행·preemption 처리: [G10_B_PREREG.md](G10_B_PREREG.md) §3과 같다. preemption이 관측되면 설계 오류로 C 확증을 중단하고 원인을 보고하며, 변경 설계는 새 버전·새 seed로 따로 선등록한다(원 실패를 지우지 않는다).

## 6. 판정 기준

- 재사용률 = 창 요청 중 turn ≥ 1이고 `cached_tokens > 0`인 비율(cell pooled).
- token 재사용률 = Σ cached / Σ reusable. reusable = 같은 세션 이전 요청의 `min(⌊(prompt + 생성 − 1)/16⌋, ⌊(prompt − 1)/16⌋)·16`(이전 prompt + 실제 고정 길이 생성, 공통 prefix, block 정렬, 마지막 token 미계산; `gpu_mt_measure`와 시뮬레이터가 같은 식). 총 prompt token을 분모로 쓰지 않는다. partial 비율과 실제 prefill 계산 token(Σ(prompt − cached), turn ≥ 1)도 보고한다.

| 항목 | 기준 |
|---|---|
| C1 요청 재사용 | 4 cell 모두, lo·hi 각각 \|예측 − 관측\| ≤ 0.05. cell별 오차, MAE, 최대 오차 보고 |
| C2 token 재사용 | 같음(≤ 0.05). **G-10에서 추가한 기준이며 과거 gate가 아니다** |
| C3 재사용 skill | lo·hi 각각 Σ\|오차\| ≤ 0.5 × Σ\|0.84718 − 관측\|(GTASK11/20 §5.1의 사전 기준선 = NPU 상수 예측 0.84718을 그대로 고정). token 지표 skill은 사전 기준선이 없어 `NA` |
| C4 비용 비 | 도구 조건마다 `R = median_i(GPU_LONG_KV / GPU_LONG_BASE 호출당 비용)`. lo·hi 각각 \|R_PRED − R_ref\| ≤ 0.03. 두 설정을 평균내지 않는다 |
| C5 비용 skill | lo·hi 각각 Σ_조건 \|R_PRED − R_ref\| ≤ 0.5 × Σ\|1 − R_ref\|. 기준선 합 ≤ 1e-12이면 `NA` |

- **참조 채널 R_ref (결과 전 고정 규칙)**: 작업 A 점검(`exec_check_result/summary.json`)의 `overall`이 `OK`이면 **DIRECT_EXEC**, 아니면 RECON_b(공통 비용 함수 아래 검증임을 명시). 작업 A는 C 측정 전에 끝나므로 C 데이터는 이 선택에 들어가지 않는다. 다른 채널은 보고한다.
- DIRECT 참조일 때 판정 replicate = 두 구성 모두 유효·preemption 0·DIRECT 완전. 계산 불가 지표는 `NA`로 두고 다른 유효 결과는 보존한다.
- 보고(판정 없음): 문맥 길이 분포(turn ≥ 1 prompt 5/50/95 %, 최대), truncation 수, preemption 수, 대기(관측 proxy 대 예측), 절대 호출당 시간(RECON lo/hi, DIRECT), step 종류별 DIRECT, R_DIRECT의 bootstrap 구간(seed 20264250)과 sign test.
- LONG_TOOL에서 모형이 실패하면 그 실패가 결과다. 관측 사건 재현으로 규칙을 확인하고, 문맥·prefill·대기열·partial reuse별로 오차를 **사후 진단**한다. 새 함수 형태나 preemption 확장을 만들어 같은 데이터로 재검증하지 않는다.

## 7. 사전 예측 (기록용, 판정 아님)

- C1: SHORT cell은 통과 쪽(재사용 0.95 이상, 포화 아님). LONG·BASE는 붕괴 근처(0.47)라 replicate 산포가 크고(예측 replicate별 범위가 넓다) GTASK20처럼 시뮬레이터가 조금 높게 예측할 가능성 → |오차| 0.03–0.08, **C1 FAIL 쪽**.
- C2: C1과 같은 방향, 문턱 근처.
- C3: PASS(기준선 0.847은 LONG cell에서 크게 틀린다).
- C4: LONG_TOOL은 DIRECT 비가 가격 비보다 1에 가깝게 나올 것이다(긴 문맥 decode 비용이 두 구성에 공통으로 더해짐) → |차| 0.03 근처, **FAIL 쪽**. SHORT_TOOL은 비가 1 근처라 통과 쪽.
- C5: SHORT 기준선 오차가 작아 skill은 LONG 오차에 좌우된다. 불확실.
