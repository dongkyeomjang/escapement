# DEFINITIONS — 재사용률·비용 채널·예측 대 관측 입력·"최대 33 %" 출처

Advisor 지시문 15 작업 B. 표·식·수치·출처만 적는다. 새 측정·새 예측 없음.

- 작성 기준: HEAD `63b4bcc`(2026-10-05), branch `main`
- 표기: "코드" = `파일:함수`, "문서" = TASK/GTASK 문서의 절
- **[사후]** 표시는 이 문서 작성 중 기존 raw/verdict를 읽어 새로 계산한 값이다. 선등록·판정과 무관한 기술 통계 값이다. 계산은 단일 process 읽기 전용(`env -u PYTHONPATH python3`)으로 했다.

## 0. 대상 실험과 자료 위치

| 기판 | 실험 | 확증 cell | 탐색 cell | replicate | 판정 자료 (경로, 상태) |
|---|---|---|---|---|---|
| NPU | TASK82 (본 측정) | N ∈ {6, 8, 10} × {BASE, BATCHONLY, TUNED} + DP N8 | N12 × 3 구성 | r0–r4 (DP·TUNED N8은 §5.4에 r5–r9 추가) | `results/npu/stage3/20260930-main/main_verdict.json` (비추적, SHA256 `a91bf2fdd54dd232…`) |
| NPU | TASK87 (고부하 blind) | N ∈ {14, 16} × 3 구성 | — | r0–r4 | `results/npu/stage3/20261001-hiload/hiload_verdict.json` (비추적, `7370c378253931d0…`) |
| NPU | TASK95 (통합 sim blind) | N ∈ {13, 17, 20} × 3 구성 (N20 BASE는 §5.1 제외, 비의 분모로는 사용) | — | r0–r4 | `results/npu/stage3/20261002-simblind/simblind_verdict.json` (비추적, `e118828666d3d78a…`) |
| NPU | TASK102 (context 비용 sim blind) | N ∈ {15, 18} × 3 구성 | — | r0–r4 | `results/npu/stage3/20261002-ctxblind/ctxblind_verdict.json` (비추적, `e6f7b4a098a69762…`) |
| GPU | GTASK11 (본 측정) | N ∈ {20, 22, 24} × {BASE, POOL, POOL+GRID} | N26 × {BASE, POOL} | r0–r4 | raw·`verdict.json`은 이 host에 없음(`results/gpu/multiturn/main/20260930T1411Z/`, GPU host 비추적). 수치는 `docs/research/gpu/GTASK11.md` |
| GPU | GTASK20 (붕괴 영역 blind) | N ∈ {25, 28} × 3 구성 | — | r0–r4 | `experiments/gpu/multiturn/blind_result/verdict.json` @ `bac3e63` (SHA256 `a6609d1eae06d43f…`) |

## 1. 재사용률

### 1.1 정의 (정상 상태 실험)

| 항목 | NPU (TASK82·87·95·102) | GPU (GTASK11·20) |
|---|---|---|
| 단위 | **요청 단위 성공 비율**(token 비율 아님) | **요청 단위 성공 비율**(판정용). token 비율은 별도 보고 지표 |
| 모집단 | 평가 구간 `[w0, w0 + 120 s)`에 **발행(`sent_s`)된** 요청 중 `turn ≥ 1` | 같음(`w0 = warmup_end_s`, `w1 = eval_end_s`) |
| 분자 | `cached > 0`인 `turn ≥ 1` 요청 수 | `cached > 0`인 `turn ≥ 1` 요청 수 |
| 분모 | `turn ≥ 1` 요청 수 | `turn ≥ 1` 요청 수 |
| `cached` 출처 | client 행 `cached_tokens`(runner가 기록). 값이 `null`이면 server 조회 줄: `[PFX] [CACHE-HIT]` → `IB_COUNT × inner_block_tokens`, `[PFX] [CACHE-PARTIAL]` → `REUSED`, 조회 줄 없음 → 0 | client `cached_tokens`. 부재면 server log에 `enable_prompt_tokens_details=True`가 있을 때만 0, 아니면 그 요청 `INVALID`. server `[GPFX] LOOKUP hit=`는 교차 확인용 |
| client–server 불일치 | 4 실험 전 lifecycle 0건(verdict `cached_source.client_server_disagree`) **[사후 집계]** | GTASK11 0건(GTASK11 §관측 조건), GTASK10 0건 |
| 부분 재사용(0 < cached < 재사용 가능량) | 분자에 **hit로 셈**(`cached > 0`). 관측: 평가 구간 `turn ≥ 1` 요청의 `[CACHE-PARTIAL]` 줄은 4 실험 server log 전체에서 모두 `REUSED=0/…`(부분 hit 0건; 줄 수 main 2,096, hiload 3,039, simblind 5,696, ctxblind 3,446) **[사후]**. 즉 관측된 hit는 전부 `[CACHE-HIT]` | 분자에 **hit로 셈**(`cached > 0`). 별도로 `hit_shape` = zero / partial(`0 < cached < 재사용 가능`) / full(`cached ≥ 재사용 가능`)로 분류해 보고. GTASK11 관측 부분 hit 비율 0.9–7.4 %(cell별, `turn ≥ 1` 대비) |
| 재사용 가능 token(GPU만) | — | `min(⌊(이전 prompt + 이전 요청 생성 수 − 1)/16⌋, ⌊(prompt − 1)/16⌋) × 16`, 같은 session의 직전 turn 행에서 계산(block 16) |
| token 비율 | 정의·보고 없음 | `token_reuse_ratio = Σ cached / Σ 재사용 가능`(`turn ≥ 1`). §5.5 보고 항목, 판정 아님 |
| cell 값 | replicate r0–r4의 **분자 합 / 분모 합**(pooled; replicate 비율의 평균 아님) | 같음 |
| 코드 | `experiments/npu/stage3/mt_measure.py:lifecycle_metrics`(`reuse = [hits, n]`), cell 합산 `main_analyze.py:main`(·`hiload_/simblind_/ctxblind_analyze.py:main`, 같은 식) | `experiments/gpu/multiturn/gpu_mt_measure.py:lifecycle_metrics`, cell 합산 `main_judge.py:main`·`blind_judge.py:main` |
| 영 예측기 | 0.67635 = 675/998(TASK73 A4 개발 집합 합산 생존율). `MULTITURN_MAIN_PREREG.md` §7.2 | 0.84718 = 5,771/6,812(TASK82 확증 10 cell 합산). `GPU_MULTITURN_PREREG.md` 개정 1 §7, `main_judge.py:NPU_NULL_REUSE` |
| 선등록 | `MULTITURN_MAIN_PREREG.md` §3 | `GPU_MULTITURN_DESIGN.md` §5, `GPU_MULTITURN_PREREG.md` §5.1 |

### 1.2 예측 쪽 재사용률

| 예측기 계열 | 정의 |
|---|---|
| NPU·GPU 시뮬레이터(sim_default·sim_observed·sim·sim_op·sim_ctx_op / sim LRU·FIFO·ctx 등) | 관측과 같은 식: 시뮬레이터 자신의 완료에 `WindowRule`을 적용해 얻은 창 안 **도착 시각** 기준 `turn ≥ 1` 요청 중 `cached_tokens > 0`(GPU는 `hit > 0`) 비율. plan 5개 합산 hit/분모. 코드 `mt_predict.py:simulate_plan`, `predict_main.py:main`, `gpu_mt_sim.py:window_metrics`, `predict_mt.py`, `predict_blind.py` |
| NPU 해석 v1·v1.1, GPU 해석 | 창 없음. 정상 상태 생존 확률 `p_s`(`mt_predict.py:analytic`의 고정점, `survival_v1.steady_state_survival`). 요청 수를 세지 않는다 |

## 2. 비용(device time) 채널 A′

### 2.1 식

**NPU 채널 A′** (`mt_measure.py:lifecycle_metrics`, 정의 출처 TASK35 §수행 내용 1, `experiments/npu/analysis/config_device.py` docstring)

```
A′_turn = ( Σ_{k ∈ S} [ F(b_k) + c0 + g · n_k ]  +  Σ_{q ∈ Q} P( max(prompt_q − cached_q, 0) ) ) / |Q|

P(x) = ⌈x / 128⌉ · (0.021206 s + 6.399e-7 s · x)          (TASK22, x = 0이면 0)
c0 = 0.501 ms,  g = 0.0413 ms/요청                        (TASK13)
```

| 기호 | 정의 |
|---|---|
| `Q` | 평가 구간 `[w0, w0 + 120 s)`에 발행된 요청 전부(**turn 0 포함**) |
| `S` | server log에서 `Q`의 `[PFX] [ALLOC]` 줄 중 **첫 줄 위치부터 마지막 줄 위치까지**의 `[BUCKET] request_nums=n padded_batch_size=b` 줄 전부. `Q` 밖 요청의 decode도 포함. client–server 시계 정렬 없음 |
| `F(b)` | bucket별 고정 비용(TASK13 model p50 + sampler p50): b1 9.87, b2 10.42, b4 10.825, b8 12.97 ms(측정). 미측정 bucket은 `config_search.py:descriptor_for`가 선형 보간·외삽: b3 10.6225, b6 11.8975, b10 14.0425, **b16 17.26**(b4–b8 외삽) ms |
| `prompt_q` | client `prompt_tokens`. 없으면 cell `INVALID` |

**GPU 채널 A′-GPU(가격 채널)** (`gpu_mt_measure.py:lifecycle_metrics`, 비용 `gpu_cost.py:step_ms`, GTASK05 값)

```
A′GPU_turn(β) = Σ_{k ∈ S} step_ms(d_k, p_k, grid, β) / |Q|,   β ∈ {lo, hi}

step_ms(d, p) = decode_ms(d)                                  (p = 0)
              = decode_ms(max(d, 1)) + inc(p, d + p, β)       (p > 0)
decode_ms(n)  = F_GPU[b(n)] + 0.0406 ms · n   (FULL: n ≤ 최대 capture size, b(n) = 격자에서 n 이상인 최소 크기)
              = G2 eager 중앙값 19.31–19.54 ms (n = 9..16, 격자 초과)
inc           = [0, 1.5] ms (PIECEWISE: d + p ≤ 최대 capture size)
              = eager 표 (p = 32…2048, lo = lag-1 증분 0 하한, hi = 3-step 창 증분; 구간 선형 보간)
```

| 기호 | 정의 |
|---|---|
| `Q` | 평가 구간에 발행된 요청 전부(turn 0 포함) |
| `S` | `Q`의 `[GPFX] ALLOC` 첫 줄 ~ 마지막 줄 사이 `[GSTEP]` 전부 |
| `d_k`(decoder 수) | `maxq == 1`이면 `reqs`. 아니면 `reqs − max(1, k_alloc)`, `k_alloc` = 직전 `[GSTEP]` 이후 `[GPFX] ALLOC` 줄 수(긴 prompt의 이어지는 chunk는 ALLOC이 없어 최소 1) |
| `p_k`(prefill token 수) | `toks − d_k` |

### 2.2 prefill·decode가 섞인 step의 중복 없는 집계

| 항목 | NPU | GPU |
|---|---|---|
| 기판 사실 | prefill 배타 실행: prefill 동안 다른 session decode가 정지(TASK22). `[BUCKET]`은 decode step 줄 | chunked prefill: 한 `[GSTEP]`에 decode token과 prefill token이 함께 실린다 |
| 집계 | decode = `[BUCKET]` step 가격 합, prefill = 요청별 `P(계산 token)` 합. 두 항은 서로 다른 시간 구간을 가리키므로 더한다 | **step 1개 = 가격 1번.** 섞인 step은 `decode_ms(max(d,1)) + inc(p)` 하나로 매긴다. 요청별 prefill 가격 항이 따로 없으므로 같은 시간을 두 번 세지 않는다. decoder 0인 prefill-only step은 폭 1 baseline + 증분(GTASK05: 단독 비용 측정 불가) |
| 보조 분해(판정 아님) | `decode_per_turn_s`, `prefill_per_turn_s` | `interference_per_turn_s = Σ_{p>0} (step_ms − decode_ms(max(d,1))) · d / |Q|`(§5.7 탐색) |
| mode 검증 | — | 비용 모형의 예상 mode(`gpu_cost.py:mode`)와 `[GSTEP]` mode 불일치 step 수 `mode_mismatch_steps`: GTASK10·GTASK11 전 lifecycle 0 |

### 2.3 정규화 분모와 비

| 항목 | NPU | GPU |
|---|---|---|
| "turn당"(호출 1회당) 분모 | `|Q|` = 평가 구간 발행 요청 수(turn 0 포함, 완료 여부 무관). 코드 `eval_requests` | 같음(`n = len(ev_rows)`) |
| BASE 대비 비 | replicate r마다 `A′(구성, N, r) / A′(BASE, N, r)`(같은 plan 파일), 5개의 **중앙값** m | 같음, bound(lo/hi)별 |
| 출처 | `MULTITURN_MAIN_PREREG.md` §3, `main_analyze.py:main`(`paired`) | `GPU_MULTITURN_PREREG.md` §5(45행), `main_judge.py:main`(`paired`) |

### 2.4 GPU 직접 dispatch 채널 (탐색, 판정 아님)

| 항목 | 내용 |
|---|---|
| 식 | `direct_turn = Σ_{k ∈ S, k+1 존재} min(t_{k+1} − t_k, 2 · step_ms_hi(k) + 5 ms) / |Q|`, `t` = `[GSTEP]` dispatch 시각(lag 0 + cap) |
| 코드 | `gpu_mt_measure.py:lifecycle_metrics`(`direct_per_turn_s`) |
| 한계 | GTASK15 발견 3·4: async dispatch에서 lag 0 귀속은 큰 eager prefill(p > 1024)의 시간을 다음 간격으로 넘기고 cap이 잘라낸다(그 계급 lag 0 cap/가격 0.181). lag 1 귀속 총합/가격 = 1.210(창의 실제 wall/가격). GTASK15 연구 원칙: "직접 채널(lag 0 + cap)은 시간 척도로 쓰면 안 된다" |

## 3. 채널 B

### 3.1 정의와 측정 범위

| 항목 | 내용 |
|---|---|
| 식 | `B = | ∪_q [sent_q, done_q] |` — client 송신·완료 시각으로 만든 in-flight 구간의 합집합 길이(tool gap 제외). 비용 모형 무의존 |
| 코드 | `experiments/npu/analysis/config_device.py:channel_b`(`policy_device.py:channel_b` 같은 식) |
| 잔차 | `r = B − A′` = queueing·HTTP·scheduler 오버헤드(TASK35 관측 4) |
| 허용차 | TASK35 선등록: `|A′비 − B비| ≤ 0.02`. TASK36부터: `τ(N) = max(0.02, r_BASE / B_BASE)`(유도: `config_device.py` docstring, TASK36 §1) |
| Stage 2 비 집계 | 블록(반복) 합산 비 `Σ_b A′_arm / Σ_b A′_BASE`, `Σ_b B_arm / Σ_b B_BASE`(`config_device.py:aggregate`) |
| 쓰인 범위 | Stage 2 비정상(동시 시작) 조건: TASK28, TASK34, TASK35, TASK36, TASK40, TASK49(사후 민감도), TASK50(무처치 null), TASK55 |
| 정상 상태 실험 | **TASK82·87·95·102와 GTASK11·20에서 정의·계산·판정 모두 없음**(`MULTITURN_MAIN_PREREG.md` §3 지표 목록에 없음, TASK82–102 문서에 "채널 B" 0회) |

### 3.2 Stage 2에서 채널 A′와의 일치 (기존 기록)

| 출처 | N | arm | A′비 | B비 | 채널 차 | 허용차 | 판정 |
|---|---|---|---|---|---|---|---|
| TASK35 (seed 20261000) | 6 | BATCHONLY | 0.9793 | 0.9588 | 0.0205 | 0.02 (사후 τ 0.0607) | 보류 |
| TASK35 | 6 | TUNED | 0.9660 | 0.9424 | 0.0236 | 0.02 (사후 τ 0.0607) | 보류 |
| TASK35 | 8 | BATCHONLY | 0.9175 | 0.9183 | 0.0008 | 0.02 | 확증 PASS |
| TASK35 | 8 | TUNED | 0.9028 | 0.8993 | 0.0035 | 0.02 | 확증 PASS |
| TASK35 | 10 | BATCHONLY | 0.9552 | 0.9551 | 0.0000 | (탐색) | — |
| TASK35 | 10 | TUNED | 0.9264 | 0.9287 | 0.0023 | (탐색) | — |
| TASK36 (seed 20261100) | 6 | BATCHONLY | 0.9941 | 0.9940 | 0.0001 | τ(6) = 0.0377 | 확증 PASS |
| TASK36 | 6 | TUNED | 0.9789 | 0.9726 | 0.0063 | τ(6) = 0.0377 | 확증 PASS |

출처: `results/tables/T08.csv`(TASK35·36), `T05.csv`, `T09.csv`. 잔차 r_BASE: N6 1.485 s(B의 6.1 %), N8 1.244 s(3.7 %), N10 1.688 s(4.0 %)(TASK35 관측 4), TASK36 N6 1.022 s(3.8 %).

| 출처 | 내용 |
|---|---|
| TASK50 (무처치 null, b8 같은 trace 10회) | 1-run 짝 45쌍 채널 차: N6 중앙 0.0184 / q95 0.0604 / 최대 0.0656, N8 중앙 0.0062 / q95 0.0320 / 최대 0.0343(`T12.csv`). 3-run 집계 단위(2,100쌍) q95 0.0326 / 0.0167 |
| TASK55 | 8개 짝 전부 `|A′비 − B비| ≤ τ(N)`(8/8), 고정 0.02로는 6/8 |
| TASK49 | 게이트 적용 20칸 재계산. A비·B비 40개 기록과 소수 넷째 자리 일치. τ 형태에서 기본값 0.005–0.05 전 범위 뒤집힘 0칸 |

### 3.3 정상 상태에서 채널 B를 쓰지 않은 이유

| 근거 | 내용 |
|---|---|
| TASK75 핵심 발견 3 (`universal`) | "steady state에서는 채널 B(in-flight 합집합)가 wall time에 수렴해 구성 간 변별력을 잃는다. 정의에서 나오는 성질" |
| `MULTITURN_DESIGN_DRAFT.md` §5 지표 표 | 같은 주의, "turn당 B" 병기 제안 |
| `MULTITURN_MAIN_PREREG.md` §3 | 측정 지표는 채널 A′만(turn당 decode·prefill·전체) |
| [사후] 평가 구간 점유율 = `|∪ [max(sent, w0), min(done, w1)]| / 120 s` | TASK82 lifecycle 75개 최소 0.800 / 중앙 0.974 / 최대 0.9998, TASK87 0.989 / 0.999 / 1.000, TASK95 0.974 / 0.999 / 1.000, TASK102 0.988 / 1.000 / 1.000. 즉 B ≈ 120 s이고, `B / |Q|`는 사실상 처리량의 역수다 |

### 3.4 정상 상태의 대체 확인 (기존 기록)

| 확인 | 대상 | 결과 | 출처 |
|---|---|---|---|
| step 단위 가격 감사: client streaming chunk 간격(ITL)을 각 `[BUCKET]` step의 시간으로 귀속해 A′ 가격과 비교 | TASK82·87 lifecycle 105개, 평가 구간 요청 20,166 | decode 관측/가격(step 가중) BASE 1.084, BATCHONLY 1.076, TUNED 1.085, DP 1.069. 배타 prefill: 계산 token ≤ 128에서 1.32–1.35, 129–512 1.20–1.21, > 512 1.01–1.03 | TASK91 결과 표, `experiments/npu/stage3/step_audit.py` |
| 운영 조건 통제 재측정 | 같은 serving 경로 | 짧은 context decode 관측/통제 0.99–1.01, 긴 context 1.03–1.15, 작은 prefill 1.23–1.48 | TASK92 |
| context 길이 항 | decode 통제 부하 | `c ≈ 0.145–0.149 µs/token`, 운영 run 구조 적용 시 1.095·1.096(관측 1.084·1.085) | TASK97 |
| W(prefill 간섭) 직접 측정 | streaming chunk 정지 | §5.7 탐색, 판정 없음 | `MULTITURN_MAIN_PREREG.md` §3·§5.7 |

위 확인은 절대 가격 수준(A′가 운영 step 시간보다 약 7–9 % 낮다)을 다룬다. **구성 간 비(A′비)에 대한 두 번째 독립 채널 판정은 정상 상태 NPU 실험에 없다.**

### 3.5 [사후] 정상 상태 NPU의 turn당 채널 B 비 대 A′ 비 (판정 아님)

정의: lifecycle마다 `B = |∪_{q∈Q} [sent_q, done_q]|`(`config_device.py:channel_b`와 같은 합집합 식, 구간을 창으로 자르지 않음), `B_turn = B / |Q|`. 비 = replicate별 `B_turn(구성) / B_turn(BASE)`의 중앙값. CI = `main_analyze.py:boot_median_ci`와 같은 방식(10,000회, seed 20261420). 3.3에 따라 이 값은 주로 처리량 비를 반영한다.

| 실험 | cell | A′ m | B_turn m [95 % CI] | \|m_A′ − m_B\| | replicate별 \|A′비 − B비\| 중앙 / 최대 |
|---|---|---|---|---|---|
| TASK82 | BATCHONLY.n6 | 0.9904 | 1.0046 [0.9564, 1.0150] | 0.0142 | 0.0103 / 0.0426 |
| TASK82 | TUNED.n6 | 0.9826 | 0.9985 [0.9450, 1.0128] | 0.0159 | 0.0166 / 0.0370 |
| TASK82 | BATCHONLY.n8 | 0.9796 | 0.9824 [0.9728, 0.9887] | 0.0029 | 0.0082 / 0.0273 |
| TASK82 | TUNED.n8 | 0.9722 | 0.9929 [0.9772, 0.9978] | 0.0207 | 0.0051 / 0.0374 |
| TASK82 | DP.n8 | 0.9725 | 0.9873 [0.9718, 1.0126] | 0.0149 | 0.0231 / 0.0351 |
| TASK82 | BATCHONLY.n10 | 0.9634 | 0.9821 [0.9132, 0.9943] | 0.0187 | 0.0085 / 0.0300 |
| TASK82 | TUNED.n10 | 0.9523 | 0.9605 [0.9018, 0.9840] | 0.0082 | 0.0112 / 0.0365 |
| TASK82 (탐색) | BATCHONLY.n12 | 0.8441 | 0.8507 [0.8144, 0.9682] | 0.0066 | 0.0110 / 0.0239 |
| TASK82 (탐색) | TUNED.n12 | 0.8296 | 0.8330 [0.7919, 0.9553] | 0.0034 | 0.0134 / 0.0299 |
| TASK87 | BATCHONLY.n14 | 0.8000 | 0.8051 [0.7835, 0.9206] | 0.0051 | 0.0120 / 0.0309 |
| TASK87 | TUNED.n14 | 0.7593 | 0.7933 [0.7571, 0.9050] | 0.0340 | 0.0242 / 0.0340 |
| TASK87 | BATCHONLY.n16 | 0.7337 | 0.7266 [0.7226, 0.8535] | 0.0071 | 0.0088 / 0.0168 |
| TASK87 | TUNED.n16 | 0.6955 | 0.7351 [0.7092, 0.8579] | 0.0396 | 0.0177 / 0.0502 |
| TASK95 | BATCHONLY.n13 | 0.8746 | 0.8941 [0.8083, 0.9655] | 0.0195 | 0.0122 / 0.0261 |
| TASK95 | TUNED.n13 | 0.8614 | 0.8752 [0.7946, 0.9505] | 0.0137 | 0.0245 / 0.0284 |
| TASK95 | BATCHONLY.n17 | 0.7259 | 0.7344 [0.6966, 0.7561] | 0.0086 | 0.0022 / 0.0128 |
| TASK95 | TUNED.n17 | 0.7036 | 0.7233 [0.6702, 0.7316] | 0.0197 | 0.0099 / 0.0252 |
| TASK95 | BATCHONLY.n20 | 0.6996 | 0.7018 [0.6287, 0.7172] | 0.0022 | 0.0092 / 0.0152 |
| TASK95 | TUNED.n20 | 0.6949 | 0.6859 [0.6139, 0.7133] | 0.0090 | 0.0070 / 0.0098 |
| TASK102 | BATCHONLY.n15 | 0.7605 | 0.7617 [0.7269, 0.8000] | 0.0012 | 0.0097 / 0.0138 |
| TASK102 | TUNED.n15 | 0.7523 | 0.7517 [0.7107, 0.7731] | 0.0006 | 0.0104 / 0.0221 |
| TASK102 | BATCHONLY.n18 | 0.7075 | 0.7113 [0.6670, 0.7321] | 0.0038 | 0.0079 / 0.0159 |
| TASK102 | TUNED.n18 | 0.6710 | 0.7010 [0.6590, 0.7181] | 0.0300 | 0.0067 / 0.0300 |

요약 [사후]: 확증 비 cell 21개(TASK82 7, TASK87 4, TASK95 6, TASK102 4)에서 `|m_A′ − m_B|` 0.0006–0.0396, 중앙 0.0137. 0.02 이하 17/21. 0.02 초과: TASK82 TUNED.n8 0.0207, TASK87 TUNED.n14 0.0340·TUNED.n16 0.0396, TASK102 TUNED.n18 0.0300.

### 3.6 GPU의 두 번째 채널 (직접 dispatch, 채널 B 아님)

| 출처 | 대상 | 수치 |
|---|---|---|
| GTASK10 (파일럿) | 구성 비 | 두 채널의 짝 ratio 차 ≤ 0.005(발견 3). streaming 동치: 직접 1.0053 [0.9937, 1.0105] |
| GTASK11 | lifecycle 55개 직접/가격 비 | 중앙 1.131, 범위 0.973–1.156. 구성 비의 채널 간 비교는 문서에 없음(verdict 미보유) |
| GTASK15 | 같은 55개, 귀속 분해 | lag 0 cap 합/가격 1.116(중앙 1.131), **lag 1 1.210**(1.211). 초과분의 89.4 %가 FULL decode |
| GTASK20 | lifecycle 30개 직접/가격 비 | 중앙 1.049, 범위 0.930–1.144(`verdict.json` `direct_vs_price`) |
| GTASK20 [사후] | 직접 채널 구성 비(lo 가격 × 직접/가격, replicate 짝 중앙, seed 20262420) | N25 POOL 0.9684 [0.9504, 0.9835](가격 0.8966), N25 POOL+GRID 0.9651 [0.9490, 0.9804](0.8933), N28 POOL 0.9631 [0.9580, 0.9793](0.9040), N28 POOL+GRID 0.9665 [0.9575, 0.9845](0.9145). \|m_직접 − m_가격\| 0.052–0.072. 붕괴 영역 BASE의 lifecycle별 직접/가격 비(0.930–1.055)가 POOL 계열(1.004–1.144)보다 낮다. 2.4의 lag 0 + cap 한계가 해당하는지는 확인하지 않았다 |

## 4. 예측과 관측 재구성값의 입력

### 4.1 예측기 목록

| 실험 | 주 예측기 | 그 밖(판정 대상) | 보고만 |
|---|---|---|---|
| TASK82 | 해석 v1(`mt_predict.py:analytic`) | sim_default, sim_observed | — |
| TASK87 | 해석 v1.1(`mt_predict_v11.py`) | v1, sim | — |
| TASK95 | sim_op(`predict_simblind.py`) | sim | v1 |
| TASK102 | sim_ctx_op(`predict_ctxblind.py`) | sim | sim_ctx, v1 |
| GTASK11 | 해석(§5.3 순위), sim LRU | sim FIFO | — |
| GTASK20 | ctx(`predict_blind.py`) | ×1.210, mode_dist, 가격 | — |

### 4.2 NPU: 항목별 입력

| 항목 | 예측에서 | 관측 재구성(A′)에서 | 공유 여부 |
|---|---|---|---|
| decode step **가격** | `descriptor_for(D, 격자, batch)`의 `StepCostModel`(TASK13 F(b) + c0 + g·n, 미측정 bucket 보간·외삽). sim 계열은 각 simulated decode step에 `step_time_s(running)`; 해석은 `Σ h(r)·step_time_s(r) × steps/s ÷ 처리량` | 같은 `StepCostModel`로 관측 `[BUCKET]`의 (b, n)에 `step_time_s(bucket=b, actual=n)` | **공유** |
| prefill **가격** | 같은 `PrefillCostModel`(TASK22). sim: prefill step마다 `prefill_s(computed_tokens)`; 해석: 평균 `E[P] = share_first·P_first + (1 − share_first)(p_s·P_hit + (1 − p_s)·P_miss)` | 요청마다 `prefill_s(prompt − cached)` | **공유**(모형), 입력 token 수는 다름 |
| 시간 진행 비용(사건 시각을 정하는 step 시간) | TASK82 sim: 가격과 같은 모형. TASK95 sim_op: TASK92 운영 비용(`OPCOST_SIM.json`)으로 진행, 가격은 원 모형. TASK102 sim_ctx_op: context 길이 decode 비용 `f(b) + βn + c·ΣL`(TASK97·100) + TASK92 prefill로 진행, 가격은 원 모형 | 실제 device 시간(관측 사건 순서에 내재) | **다름** |
| 사건 순서(도착·admission·완료·축출) | sim: plan + 시뮬레이터 의미론(TASK82 sim_observed·TASK95·102는 관측 의미론 `immediate` + `pre_evict` 또는 v2 descriptor). 해석: 순서 없음(정상 상태 닫힌 형태: B2 점유, v1 생존 birth–death) | server log 순서(`[PFX] [ALLOC]`, `[BUCKET]`) 그대로. 생존 모형 없음 | **다름** |
| 재사용량(cached token) | sim: 시뮬레이터 캐시의 `cached_tokens`; 해석: 생존 확률 `p_s` | client `cached_tokens`(없으면 server 조회 줄) | **다름** |
| 점유 h(n)·bucket | sim: simulated decode step의 running; 해석: B2 `step_share` | `[BUCKET] request_nums`, `padded_batch_size` | **다름** |
| prompt·생성 길이 | plan 파일(`main-n{N}-r{r}` 등) | client `prompt_tokens`(plan을 보낸 결과) | 같은 plan에서 파생 |
| 평가 창 | sim: `WindowRule`을 시뮬레이터 완료에 적용, 창 안 **시작 시각** decode·prefill step | `WindowRule` 온라인 기록, 창은 첫·마지막 평가 요청 ALLOC의 **log 위치** 사이 step | 규칙 공유, 경계 정의 다름 |
| 분모(요청 수) | 창 안 simulated 도착 요청 수 | 창 안 발행 요청 수 | 정의 공유, 값 다름 |
| substrate 상수(격자, `batch_size` = KV 용량, inner block 128) | descriptor | descriptor(가격용 bucket·격자) | **공유** |
| client 오버헤드·HTTP·queueing | 0(sim) / 없음(해석) | A′에 들어가지 않음(채널 B 잔차 r에 해당) | 둘 다 제외 |
| 비 집계 | plan 5개 **합산** `Σ device / Σ 요청`의 구성 간 비(`predict_main.py:main` `ratio_to_base`) | replicate별 짝 비의 **중앙값** | **다름** |
| 순위 | 예측 `device_per_turn_s`(합산) 오름차순 `rank` | §5.3 해소된 쌍의 관측 싼 쪽 | — |

### 4.3 GPU: 항목별 입력

| 항목 | 예측에서 | 관측 재구성(A′-GPU)에서 | 공유 여부 |
|---|---|---|---|
| step 가격 | `gpu_cost.step_ms(d, p, grid, β)`(GTASK05) | 같은 함수 | **공유** |
| 시간 진행 비용 | GTASK11 sim: 가격과 같음. GTASK20 ctx: `step_ms + 2.120e-4 ms · (decode_ctx − d · 128)`(GTASK18 F1), ×1.210: `step_ms × 1.210`, mode_dist: GTASK11 lag-1 비 분포 표본, 가격: `step_ms` | 실제 시간 | **다름** |
| step의 d·p | 시뮬레이터가 아는 정확한 값 | ALLOC 수로 추정한 `d = reqs − max(1, k_alloc)`, `p = toks − d` | **다름**(식별 규칙) |
| step mode | `gpu_cost.mode(d, p)` | `[GSTEP]` mode(불일치 0, GTASK10·11) | 규칙 공유 |
| 사건 순서·축출 | `gpu_mt_sim.py` 엔진(FCFS, chunked prefill, 해제 순서 LRU 또는 FIFO 반사실) | server log | **다름** |
| 재사용량 | sim 캐시 hit(block 16 단위) | client `cached_tokens` | **다름** |
| 비 집계 | plan 5개 합산 `Σ price / Σ 요청`의 비(`predict_mt.py`, `predict_blind.py`) | replicate별 짝 비 중앙값 | **다름** |

## 5. "최대 33 %"의 출처 후보

저장소 문서·표에 "33 %"라는 문자열로 된 비용 감소 주장은 없다(`grep`, `docs/research`, `paper/RESULTS_INDEX.md`, `paper/draft`). 아래는 정상 상태 확증 cell의 관측 비 중 1 − 비가 33 %에 가까운 값이다. **원고 문장이 어느 값을 가리키는지는 사용자가 확인해야 한다.**

| 순위 | 실험 | cell | 채널 | 집계 | 값 | 1 − 값 | 95 % CI | 출처 |
|---|---|---|---|---|---|---|---|---|
| 1 | TASK102 | TUNED / BASE, N = 18 | NPU A′(turn당) | replicate 짝 비 r0–r4의 **중앙값** | **0.6710** | **32.9 %** | [0.6506, 0.7248] | `ctxblind_verdict.json` `cells.TUNED.n18.ratio`, `results/tables/figures/F_b_reuse_ratio_vs_N.csv`, TASK102 결과 표 |
| 2 | TASK95 | TUNED / BASE, N = 20 | NPU A′ | 짝 비 중앙값 | 0.6949 | 30.5 % | [0.6185, 0.7044] | `simblind_verdict.json` |
| 3 | TASK87 | TUNED / BASE, N = 16 | NPU A′ | 짝 비 중앙값 | 0.6955 | 30.4 % | [0.6778, 0.8489] | `hiload_verdict.json` |
| 4 | TASK95 | BATCHONLY / BASE, N = 20 | NPU A′ | 짝 비 중앙값 | 0.6996 | 30.0 % | [0.6439, 0.7184] | `simblind_verdict.json` |
| 5 | TASK95 | TUNED / BASE, N = 17 | NPU A′ | 짝 비 중앙값 | 0.7036 | 29.6 % | [0.6603, 0.7145] | `simblind_verdict.json` |

같은 cell의 다른 집계 [사후]:

| cell | replicate 평균 A′의 비(구성 평균 / BASE 평균) | 1 − 값 | 가장 작은 replicate 짝 비 |
|---|---|---|---|
| TASK102 TUNED N18 | 378.5 / 554.7 ms = 0.6824 | 31.8 % | 0.6506 (r2) |
| TASK95 TUNED N20 | 378.8 / 557.5 ms = 0.6795 | 32.0 % | 0.6185 (r2) |
| TASK87 TUNED N16 | 401.8 / 547.8 ms = 0.7334 | 26.7 % | 0.6778 (r0) |

같은 cell의 예측(blind, 선등록): TASK102 TUNED N18 sim_ctx_op 0.6797(32.0 %), sim 0.6949; TASK95 TUNED N20 sim_op 0.6691(33.1 %), sim 0.6796.

GPU 확증 cell의 가장 작은 관측 비: GTASK20 N25 POOL+GRID/BASE 0.8933 [0.8535, 0.9428](lo, 10.7 %), 탐색 GTASK11 N26 POOL/BASE 0.899 [0.806, 0.907]. GPU에는 33 % 근처 값이 없다.

## 6. NPU와 GPU의 정의 차이 요약

| 항목 | NPU | GPU |
|---|---|---|
| 비용 채널 | decode step 가격 + 요청별 배타 prefill 가격 | step 1개 가격(섞인 step은 decode baseline + prefill 증분), `lo`/`hi` 두 bound |
| 창 안 prefill 범위 | 평가 요청 `Q`의 prefill만 | 창 안 모든 step(평가 밖 요청의 prefill chunk 포함) |
| decoder 수 | `[BUCKET] request_nums` 직접 | ALLOC 수로 추정 |
| 미측정 폭 | bucket 비용 보간·외삽(b3·b5·b6·b10·b16) | 측정 범위 밖이면 오류(`ValueError`) |
| `cached` 부재 처리 | server 조회 줄 | flag 확인 시 0, 아니면 INVALID |
| 부분 hit | 관측 0건 | 0.9–7.4 %(GTASK11), hit로 셈 |
| token 재사용 비율 | 없음 | 보고 |
| bootstrap seed | 20261420 | 20262420 |
| 두 번째 채널 | Stage 2 채널 B(in-flight 합집합), 정상 상태 없음 | 직접 dispatch(lag 0 + cap), 보고만 |
| 영 재사용 예측기 | 0.67635(개발 집합) | 0.84718(NPU TASK82 관측) |
| h(n) 정의 | `[BUCKET] request_nums` step 가중 | 판정: decode-only(`d ≥ 1`) step 가중(개정 1 §7.4), 병기: `reqs` |

## 7. 이 host에서 확인할 수 없는 것

| 항목 | 이유 |
|---|---|
| GTASK11 replicate별 재사용률·turn당 A′-GPU·직접 채널 값 | raw(`results/gpu/multiturn/main/20260930T1411Z/`)와 `verdict.json`이 GPU host에만 있다. 문서에는 cell 합산값과 m·CI만 있다 |
| GTASK11 구성 비의 직접 채널 대 가격 채널 비교 | 같음 |
| GPU hit_shape의 GTASK20 값 | `blind_judge.py`가 기록하지 않는다 |
| GPU 정상 상태의 채널 B | client 행이 이 host에 없다(GTASK20도 verdict만 있음) |
