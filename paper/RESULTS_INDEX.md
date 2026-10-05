# RESULTS_INDEX

kind: blind_confirm · blind_fail · withheld (판정 전제 조건 불충족으로 판정하지 않음) · post_hoc · dev_set · exploratory · retro_check · code_check / layer: universal · class · stack · silicon · untagged (태그는 원 TASK/GTASK 문서의 태그만) / source: NPU `<path> @ <git log -1 commit>`, GPU `<path> @ <commit>` (gpu-a6000 merged into main in `af3dfe3`; GPU file commits are in main history) / data: `results/tables/` 표·그림 데이터 (`make_paper_tables.py`, `make_tables.py`)

## 1. arXiv 세 기전

### 1a. padding / 격자 정렬

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t13_h_same_bucket_equiv | 7/7 DIFFERENT | 동치 요구 쌍, 채널 C ITL bootstrap | docs/research/TASK13.md @ 7e7859b | blind_fail | untagged | T06 |
| t13_f_bucket_p50 | 9.51 / 10.05 / 10.355 / 12.4025 ms | model span, bucket 1 / 2 / 4 / 8 | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | T06 |
| t13_f_within_bucket_range | 0.01–0.03 ms | model span, 같은 bucket 안 범위 | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | T06 |
| t13_g_actual | 0.041 ms | 요청당 engine overhead | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | T06 |
| t13_boundary_effect_finding3 | +4.6 %~+17.8 %; 같은 bucket 안 최대 +1.2 % | ITL, 핵심 발견 3 | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | — |
| t13_boundary_effect_verdict | +5.7~17.8 %; 같은 bucket 내 최대 +1.2 % | ITL, 판정 절 | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | — |
| t13_transition_4to5 | +17.8 %; 2.06 ms | step 시간, 동시성 4 → 5 (bucket 4 → 8) | docs/research/TASK13.md @ 7e7859b | post_hoc | untagged | — |
| t20_prereg_pred_a_c | 사전 예측 (a)·(c) 빗나감 | 선등록 예측 | docs/research/TASK20.md @ a6861cf | blind_fail | untagged | — |
| t20_degradation_n10_12 | 저하 존재; pooled 0.9103 / 0.9192 | util(AGENTIC)/util(CONVENTIONAL), N = 10 / 12, 선등록 판정 규칙 (선등록 `f9cc106` 16:51:16 < 측정 시작 16:51:32, "저하 존재" 기준은 NSLOTS_SWEEP_PREREG.md에 고정) | docs/research/TASK20.md @ a6861cf | blind_confirm | stack | — |
| t20_sign_flip_n6 | pooled 1.1504 (INCONCLUSIVE) | util 비, N = 6 | docs/research/TASK20.md @ a6861cf | post_hoc | class | — |
| t20_v1_cost_transfer | 0.86 → 0.57; 최대 43 % 과소 | TASK13 비용 모형 예측/실측 비, N 증가 | docs/research/TASK20.md @ a6861cf | post_hoc | stack | — |
| t20_reuse_zero_n_ge12 | 0 | 층 2 재사용, N ≥ 12, 두 arm | docs/research/TASK20.md @ a6861cf | post_hoc | stack | — |
| t23_grid_intervention_n6 | 1.1504 → 0.9717; 역전 블록 3/3 → 0/3 | pooled util 비, N = 6, 격자 (1,2,4,8) → (1,2,4,6,8) | docs/research/TASK23.md @ 8254ceb | blind_confirm | class (형태) / stack (값) | — |
| t23_grid_intervention_n8 | 0.9253 → 0.9508 (3/3 저하) | pooled util 비, N = 8 | docs/research/TASK23.md @ 8254ceb | blind_confirm | stack | — |
| t23_conv_vs_agentic_gain | 1.241× / 1.048× | util 상승, CONVENTIONAL / AGENTIC, N = 6 | docs/research/TASK23.md @ 8254ceb | post_hoc | stack | — |
| t24_sim_reproduction | utilization 평균절대 0.0066; pooled ratio 방향 11/11, 최대 오차 0.0202 | 기존 실측 80조합, 보정 파라미터 없음 | docs/research/TASK24.md @ 0f6f302 | retro_check | universal | — |
| t25_sim_oos_gate | PASS 3/3; 최대 오차 0.0040 (허용 ±0.05) | 신규 seed pooled ratio, N = 3 / 4 / 7 | docs/research/TASK25.md @ 6361676 | blind_confirm | universal | — |

### 1b. prefill 직렬화

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t22_spike_existence | PARTIAL; 36/36 (대조 3 run에서도 문턱 초과) | 주입 9 run × bystander 4 | docs/research/TASK22.md @ d1968e3 | blind_fail | untagged | T04 |
| t22_spike_concurrency | 9/9 | run, K = 4 스파이크 공통 교집합 | docs/research/TASK22.md @ d1968e3 | blind_confirm | stack | T04 |
| t22_spike_proportionality | 1.140 / 1.036 / 1.012 | 스파이크/prefill 시간, 500 / 2000 / 6000 token | docs/research/TASK22.md @ d1968e3 | blind_confirm | stack | T04 |
| t22_prefill_fit | ceil(n/128) × (0.0212 + 6.4e-7 n); 최대 잔차 2.4 ms | 500–6000 token | docs/research/TASK22.md @ d1968e3 | post_hoc | stack | — |
| t22_v2_explains_t20_bias | 87–120 %; v1 0.565–0.855 → v2 0.973–1.039 | TASK20 cell 비용 비 | docs/research/TASK22.md @ d1968e3 | post_hoc | stack | — |
| t22_system_cost_example | 2,000 token × 4 decoder = 1.44 s | 시스템 정지 시간 | docs/research/TASK22.md @ d1968e3 | post_hoc | class | — |

### 1c. 재사용 절벽

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t14_layer2_threshold | B = 7 (B ≤ 6 100 %, B ≥ 7 0 %) | 배경 요청 수, 층 2 outer FIFO 8 | docs/research/TASK14.md @ 27ef708 | blind_confirm | untagged | P01, F_a |
| t14_prereg_predictions | 8개 중 7개 적중 | 선등록 예측 8개 | docs/research/TASK14.md @ 27ef708 | blind_confirm | untagged | — |
| t14_pred6_partial | 예측 6 부분 오답 (층 1 B16 1.0) | 선등록 예측 6 | docs/research/TASK14.md @ 27ef708 | blind_fail | untagged | — |
| t14_layer1_threshold | 16 < B ≤ 33 | 배경 요청 수, 층 1 inner LRU 512 | docs/research/TASK14.md @ 27ef708 | exploratory | untagged | — |
| t14_metric_overcount | 1,920 hit vs 0 % (100 % 과대) | `prefix_cache_hits_total`, 7 ≤ B ≤ 16 | docs/research/TASK14.md @ 27ef708 | post_hoc | untagged | — |
| t14_count_not_tokens | 149/149 | ≤ 8,192 token 요청당 outer block 1 | docs/research/TASK14.md @ 27ef708 | post_hoc | untagged | — |
| t14_resume_latency | 0.111 s → 0.444–0.448 s | resume latency, B ≤ 6 / B ≥ 7 | docs/research/TASK14.md @ 27ef708 | exploratory | untagged | — |
| t15_cliff_repro | 12/12 (B ∈ {5, 6}: 1,920; B ∈ {7, 8}: 0) | trial, 층 2 재사용 token | docs/research/TASK15.md @ 8e4c5db | blind_confirm | stack + class | P01, F_a |
| t15_metric_false_positive | 6/6 | B ∈ {7, 8} trial | docs/research/TASK15.md @ 8e4c5db | blind_confirm | stack | — |
| t15_recompute | prefill 시간 13.1배; `prefill_kv_computed` 88 → 2,008 | resume 요청 | docs/research/TASK15.md @ 8e4c5db | blind_confirm | stack | — |

### 1d. compile 구성 (용량·격자)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t34_channel_agreement | 0.0221 / 0.0908 / 0.0700 (요건 ≤ 0.02 초과, 판정 보류) | \|A−B\|, N = 6 / 8 / 10 | docs/research/TASK34.md @ e24cf76 | withheld | universal | — |
| t34_posthoc_channel | \|A′−B\| 0.0014–0.0045 | 측정 후 정의 채널, N = 6 / 8 / 10 | docs/research/TASK34.md @ e24cf76 | post_hoc | untagged | — |
| t34_X_observed | +7.38 % (N ∈ {6,8}); N10 +12.61 % | X, 채널 B, 판정 보류 | docs/research/TASK34.md @ e24cf76 | exploratory | stack | — |
| t34_sim_attribution | batch +7.21 %; bucket +0.71 % | sim 귀속 | docs/research/TASK34.md @ e24cf76 | exploratory | stack | — |
| t35_X_n8_tuned | +9.72 % / +10.07 % | X, N = 8 TUNED, 채널 A′ / B | docs/research/TASK35.md @ 3f8308e | blind_confirm | stack | T09 |
| t35_X_n8_batchonly | +8.25 % / +8.17 % | X, N = 8 BATCHONLY, 채널 A′ / B | docs/research/TASK35.md @ 3f8308e | blind_confirm | stack | T09 |
| t35_pred_error_n8 | +0.0074 / +0.0058 (≤ 0.03) | sim 예측 오차, N = 8 ② / ③ | docs/research/TASK35.md @ 3f8308e | blind_confirm | stack | T07 |
| t35_n6_held | PARTIAL (2 PASS / 2 보류); N = 6 오차 +0.0183 / +0.0194, 채널 0.0205 / 0.0236 > 0.02 | N = 6 ② / ③ | docs/research/TASK35.md @ 3f8308e | withheld | untagged | — |
| t35_ablation | ③−② +1.34 / +1.47 %p vs 예측 +1.45 / +1.30 %p; PASS 2/2 | N = 6 / 8 | docs/research/TASK35.md @ 3f8308e | blind_confirm | stack | — |
| t35_prefill_ratio_equal | 0.898/0.898, 0.678/0.678 | prefill비, ② / ③ | docs/research/TASK35.md @ 3f8308e | exploratory | stack | — |
| t36_n6_reconfirm | PASS 2/2; 오차 +0.0067 / +0.0076; 채널 0.0001 / 0.0063 | N = 6 신규 seed, ② / ③ | docs/research/TASK36.md @ 3f8308e | blind_confirm | stack | T05 |

## 2. 모형 v0 기존 데이터 대조 R1–R5′ (TASK72)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t72_R1 | P1 29/29, P2 36/36, P3 140/140, P4 140/140 | 순차·동시 시작·연속 admission 36 trial, 축출 140 | docs/research/TASK72.md @ e1f791e | retro_check | universal | M01, M02, P01, F_a |
| t72_R2 | 524칸 불일치 0 | 4 배경 크기 × B 0..130, 모형 vs 시뮬레이터 | docs/research/TASK72.md @ e1f791e | code_check | untagged | M01 |
| t72_R3 | regret 0; E(h) 0.0285 / 0.0298 | DP 격자 = G\*, R3a sim / R3b 실측 | docs/research/TASK72.md @ e1f791e | retro_check | stack | M03 |
| t72_R3_per_N_regret | N=6 0.01399; N=8 0.00743; N=10 0.00059 | R3b N별 regret (보고만) | docs/research/TASK72.md @ e1f791e | exploratory | stack | M03 |
| t72_R4 | TVD 중앙값 0.248; > 0.3 5/17 | 17 cell h(n) | docs/research/TASK72.md @ e1f791e | exploratory | untagged | M04 |
| t72_R5 | 평균 절대오차 1.08 / 1.12 | 126 cell, 요청/cell, binomial / poisson | docs/research/TASK72.md @ e1f791e | exploratory | untagged | M05 |
| t72_R5_t50_n6 | 관측 60 vs 예측 36–37 | TASK50 N = 6 재사용 | docs/research/TASK72.md @ e1f791e | exploratory | class | — |
| t72_R5prime | 1,298/1,298 (7 run 모두 1.000) | turn ≥ 1 재도착 | docs/research/TASK72.md @ e1f791e | retro_check | universal | M05, P06 |
| t72_R5prime_alt_rules | 즉시 1.000 vs 지연 0.934; PRE_EVICT 1.000 vs RESERVED 0.847 | 일치율, 1,298 요청 | docs/research/TASK72.md @ e1f791e | retro_check | stack | P06 |
| t72_closed_form_lookup | 0.833 (오답 217 = 130 + 87) | 일치율, 1,298 요청 | docs/research/TASK72.md @ e1f791e | retro_check | universal | P06 |
| t72_73_failures | 73건 전부 예측; 51 + 22 | TASK54 mb + mb6 재사용 실패 (34 + 39) | docs/research/TASK72.md @ e1f791e | retro_check | untagged | — |
| t72_all_failures_cause | 437 / 61 / 26 | 실패 524: 창 안 할당 수 초과 / dummy pre-evict / 기타 | docs/research/TASK72.md @ e1f791e | retro_check | untagged | — |

## 3. Descriptor v2 규칙 field와 두 기판 재현

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g04_sequential_survival | 60/60 | resume hit token, 60 trial, 측정 전 예측 | docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | universal | P01, F_a |
| g04_block_staircase | 손실 시작 674, 전손 800 | 누적 배경 block, 배경 크기 4종 | docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | class | P01, F_a |
| g04_generated_token_cached | 2,016 hit; T hash block 126 | 조건 (ii) | docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | stack | P01 |
| g04_four_channels | 60 trial 네 채널 일치 | 응답·admission 로그·counter·KV events | docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | universal | — |
| t84_rule_fields | 7 | descriptor 규칙 field | docs/research/TASK84.md @ c58daaf | code_check | class | P09 |
| t84_rbln_cliff | B = 7에서 1,920 → 0 (배경 500·1,000·2,000·4,000 token) | RBLN v2 descriptor + `sequential_protocol` | docs/research/TASK84.md @ c58daaf | code_check | class | P09, F_a |
| t84_gtask04_no_wrapper | 60/60 | GPU 테스트 descriptor + `sequential_protocol` | docs/research/TASK84.md @ c58daaf | code_check | class | P09 |
| t84_regression | 63/72 byte 동일 (9 시각 key) | 회귀 파일 | docs/research/TASK84.md @ c58daaf | code_check | universal | — |
| t84_descriptor_eq_switch | 75/75 | run, `descriptor` vs 관측 스위치 | docs/research/TASK84.md @ c58daaf | code_check | universal | — |
| t84_tests | 17항목 전부 ok | `tests/test_descriptor_v2.py` | docs/research/TASK84.md @ c58daaf | code_check | untagged | — |

## 4. NPU multi-turn 본 측정 (TASK82)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t82_validity | 75/75 유효, 재실행 0 | lifecycle | docs/research/TASK82.md @ 074aedc | blind_confirm | untagged | — |
| t82_s51_reuse | PASS; 10/10 ≤ 0.10; MAE 0.0142 ≤ 0.5 × 0.1746 | 재사용률, 해석 v1, 확증 10 cell | docs/research/TASK82.md @ 074aedc | blind_confirm | stack (값) / class (형태) | P02, F_b, F_c |
| t82_s51_sim | MAE sim 기본 0.0037, sim 관측 0.0036 | 재사용률, 확증 10 cell | docs/research/TASK82.md @ 074aedc | blind_confirm | untagged | P02, F_c |
| t82_s52_ratio_analytic | PASS 7/7·7/7; Σ 0.0483 / 0.1871 = 0.26 | 비용 비, 해석 v1 | docs/research/TASK82.md @ 074aedc | blind_confirm | stack (값) / class (형태) | P02, F_b, F_c |
| t82_s52_ratio_sim_default | PASS 7/7·7/7; skill 0.21 | 비용 비, sim 기본 | docs/research/TASK82.md @ 074aedc | blind_confirm | untagged | P02 |
| t82_s52_ratio_sim_obs | PASS 7/7·7/7; skill 0.17 | 비용 비, sim 관측 | docs/research/TASK82.md @ 074aedc | blind_confirm | untagged | P02 |
| t82_s53_ranking | PASS; 해소 7쌍 일치 (N=6 UNRESOLVED, N=8 4/4, N=10 3/3) | 구성 순위, 해석 | docs/research/TASK82.md @ 074aedc | blind_confirm | untagged | P05 |
| t82_s54_dp_vs_tuned | INCONCLUSIVE; 0.9920 [0.9857, 1.0050] | 짝 비 DP/TUNED, N = 8, 10 replicate | docs/research/TASK82.md @ 074aedc | blind_confirm | stack | — |
| t82_s54_pred | 해석 0.9958, sim 0.9890 (CI 안) | 예측 비 | docs/research/TASK82.md @ 074aedc | blind_confirm | stack | — |
| t82_batchonly_vs_dp | 1.0041 [1.0008, 1.0096] | 짝 비 BATCHONLY/DP, N = 8 | docs/research/TASK82.md @ 074aedc | blind_confirm | stack | P05 |
| t82_s55_hsim | SUPPORTED; 양수 1/7 (p 0.125); 중앙 \|e\| 0.0055 < 0.0130 | sim 비 오차, 7 cell | docs/research/TASK82.md @ 074aedc | blind_confirm | stack | — |
| t82_s56_h | PASS; TVD 중앙 0.061, 최대 0.074; 영 0.296 | h(n), 해석 B2 | docs/research/TASK82.md @ 074aedc | blind_confirm | stack (값) / class (형태) | — |
| t82_base_error | N8 −0.043, N10 −0.065, N12 −0.080; batch 16 ≤ 0.008 | 재사용 오차, 해석 v1 | docs/research/TASK82.md @ 074aedc | post_hoc | stack | F_c, F_d |
| t82_cell_diff | 관측 N8 0.10, N10 0.16; 해석 0.15·0.22; sim 0.10·0.16 | BASE 대 batch 16 재사용 차 | docs/research/TASK82.md @ 074aedc | post_hoc | untagged | F_b |
| t82_zero_predictor_level | 0.676 vs 0.70–0.92 | 영 예측기 vs steady-state 재사용 | docs/research/TASK82.md @ 074aedc | post_hoc | untagged | F_c |
| t82_n12_ratio | 관측 0.84·0.83 vs 예측 0.86–0.89 | 비용 비, N = 12 (탐색) | docs/research/TASK82.md @ 074aedc | exploratory | untagged | P02, F_b |
| t82_n12_base_reuse | 0.484 / 0.404 / 0.485 / 0.507 | BASE N = 12 재사용, 관측 / 해석 / sim 기본 / sim 관측 (탐색) | docs/research/TASK82.md @ 074aedc | exploratory | untagged | P02, F_b |
| t82_P_K_corr | 12/13 | cell, cov(P, K) > 0 | docs/research/TASK82.md @ 074aedc | exploratory | class | — |
| t82_W_base_n12 | +10 % | 간섭 W 독립 곱 과소, BASE N = 12 | docs/research/TASK82.md @ 074aedc | exploratory | class | — |
| t82_nonstationary_60s | 0.25–0.48 vs 0.10–0.24 | 전·후반 60 s h TVD vs replicate 간 120 s TVD | docs/research/TASK82.md @ 074aedc | exploratory | universal | — |

## 5. GPU multi-turn (GTASK11)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g11_validity | 55/55 유효, 재실행 0 | lifecycle | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | — |
| g11_lru_vs_fifo | LRU_SUPPORTED; d_L < d_F 8/9; Σd_L 0.148 vs Σd_F 0.937 | 분리 cell 9 | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | class (형태) / stack (값) | P04 |
| g11_partial_hit | 관측 0.9–7.4 % vs LRU 0.8–5.3 % vs FIFO 9.7–14.2 % | 부분 hit 비율, 9 cell | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | class (형태) / stack (값) | — |
| g11_orphan_evictions | 0 / 958,078 | KV events 고아 축출 / `BlockRemoved` | docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | class (형태) / stack (값) | — |
| g11_sim_lru_reuse | PASS; MAE 0.0173; skill 0.35 | 재사용률, sim LRU, 확증 9 cell (lo) | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P04, F_c |
| g11_sim_lru_ratio | PASS 6/6, 6/6; Σ 0.075 (0.36) | 비용 비, sim LRU, 6 cell (lo) | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P04, F_c |
| g11_sim_fifo | FAIL; MAE 0.1021 | 재사용률, sim FIFO | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | untagged | P04 |
| g11_analytic_reuse | FAIL; N24 BASE +0.138; MAE 0.0333; skill 0.66 | 재사용률, 해석 v1 | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | stack | P04, F_c, F_d |
| g11_analytic_ratio | FAIL; N24 \|예측 − m\| 0.046·0.053; Σ 0.146 (0.70) | 비용 비, 해석 v1 | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | stack | P04, F_c, F_d |
| g11_null_mae | 0.0502 (경계 0.05) | §5.1 영 예측기 0.84718 MAE | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | P04, F_c |
| g11_ranking | PASS N20·22·24 | 순위, 해석 | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | P05 |
| g11_pool_grid | INCONCLUSIVE ×3; 0.9985–0.9988 | POOL+GRID/POOL | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P05 |
| g11_h | PASS; TVD 중앙 0.081, 최대 0.184; 영 0.645 | h(n) decode-only (lo) | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | — |
| g11_h_reqs | FAIL (최대 0.212) | h(n) `reqs` 정의 (병기) | docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | untagged | — |
| g11_hsim_sign | lo 4/6, hi 6/6 음; 중앙 \|e\| 0.0135 | sim LRU 비 오차, H-sim 지표 (보고) | docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | stack | — |
| g11_collapse_curve | 관측 0.817 / 0.669 / 0.450 vs sim LRU (`lo`) 0.849 / 0.753 / 0.657 (GTASK11 발견 4 문장의 0.752는 lo·hi 평균, GTASK19 정정 기록) | BASE 재사용, N22 / 24 / 26 | docs/research/gpu/GTASK11.md @ 22b50f4; docs/research/gpu/GTASK19.md @ a99f23c | exploratory | class | P04, F_b |
| g11_n26 | BASE 0.450 vs 해석 0.786, sim LRU 0.657, sim FIFO 0.552; m 0.899 [0.806, 0.907] | N = 26 재사용, POOL/BASE 비 (탐색) | docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | class | P04, F_b |
| g11_direct_channel | 1.131 (0.973–1.156) | 직접 dispatch / 가격, 55 lifecycle 중앙 | docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | untagged | — |

## 6. 고부하 blind cell N = 14·16 (TASK87)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t87_validity | 30/30 유효, 재실행 0 | lifecycle | docs/research/TASK87.md @ a210be2 | blind_confirm | untagged | — |
| t87_config_effect | 평균 \|1 − m\| 0.253 (구성 효과 25 %); m 0.800 / 0.759 / 0.734 / 0.696 | BASE 대비 비, BATCHONLY N14 / TUNED N14 / BATCHONLY N16 / TUNED N16 | docs/research/TASK87.md @ a210be2 | blind_confirm | stack | P03, F_b |
| t87_ratio_underpredict | Σ\|오차\| v1.1 0.087, sim 0.189, v1 0.358 | 비용 비, 세 예측기 모두 과소 | docs/research/TASK87.md @ a210be2 | blind_fail | stack | P03, F_c |
| t87_ranking | PASS; 해소 6/6쌍 | N14·N16, 세 예측기 | docs/research/TASK87.md @ a210be2 | blind_confirm | untagged | P05 |
| t87_ranking_bo_tuned | 1.036 [1.031, 1.054] · 1.037 [1.014, 1.057] | BATCHONLY/TUNED, N14 · N16 | docs/research/TASK87.md @ a210be2 | blind_confirm | untagged | P05 |
| t87_sim_s51 | PASS 6/6; MAE 0.013 | 재사용률, sim | docs/research/TASK87.md @ a210be2 | blind_confirm | stack | P03, F_c |
| t87_sim_h | TVD 중앙 0.069 | h(n), sim | docs/research/TASK87.md @ a210be2 | blind_confirm | stack | — |
| t87_v11_s51 | FAIL 5/6; BASE N14 −0.125; skill PASS (MAE 0.049) | 재사용률, v1.1 | docs/research/TASK87.md @ a210be2 | blind_fail | untagged | P03, F_c, F_d |
| t87_v11_base_reuse | N14 0.173 vs 0.298; N16 0.068 vs 0.165 | BASE 재사용 v1.1 예측 vs 관측 | docs/research/TASK87.md @ a210be2 | blind_fail | stack | P03, F_b |
| t87_v11_s52 | FAIL 3/4; TUNED N16 \|0.732 − 0.696\| = 0.036 > 0.03; skill 0.09 | 비용 비, v1.1 | docs/research/TASK87.md @ a210be2 | blind_fail | untagged | P03 |
| t87_v11_vs_v1 | FAIL; 비 오차 합 0.087 vs 0.358; 재사용 MAE 0.049 vs 0.033 | v1.1 대 v1 | docs/research/TASK87.md @ a210be2 | blind_fail | untagged | P03 |
| t87_reuse_ratio_decoupled | 재사용 MAE v1.1 0.049 > v1 0.033; 비 Σ v1.1 0.087 < v1 0.358 | 두 지표 방향 불일치 (발견 4) | docs/research/TASK87.md @ a210be2 | post_hoc | universal | — |
| t87_v11_s56 | PASS; TVD 중앙 0.0989, 최대 0.171; 영 0.541 | h(n), v1.1 | docs/research/TASK87.md @ a210be2 | blind_confirm | untagged | — |
| t87_v1_s51 | FAIL 5/6; BASE N16 +0.140 | 재사용률, v1 | docs/research/TASK87.md @ a210be2 | blind_fail | untagged | P03 |
| t87_base_cost | v1.1 +1.3–1.6 %, sim 0 %, v1 −4 %·−8 % | BASE turn당 비용 예측 오차 | docs/research/TASK87.md @ a210be2 | exploratory | stack | — |
| t87_null_mae | 0.2245 | 재사용 영 예측기 MAE, 6 cell | docs/research/TASK87.md @ a210be2 | blind_confirm | untagged | P03 |

## 7. 모형 v1.1 / v1.2 (개발 집합)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t85_v11_reuse_mae | 0.041 → 0.026 | 재사용 MAE, v1 → v1.1, N = 12 개발 집합 | docs/research/TASK85.md @ ffd716f | dev_set | stack | — |
| t85_v11_ratio_error | 0.092 → 0.100 | 비 오차 합, v1 → v1.1, N = 12 개발 집합 | docs/research/TASK85.md @ ffd716f | dev_set | stack | — |
| t85_base_reuse_n12 | 0.404 → 0.436 (0.484) | BASE 재사용 v1 → v1.1 (관측), N = 12 | docs/research/TASK85.md @ ffd716f | dev_set | untagged | F_b |
| t85_completion_order | 0.29 vs 0.44 | BASE 재사용, random vs admission 완료 순서, N = 12 | docs/research/TASK85.md @ ffd716f | dev_set | stack | — |
| t85_chain_vs_mc | 8/8 \|차\| ≤ 0.012 (허용 0.02) | 연쇄 vs Monte Carlo | docs/research/TASK85.md @ ffd716f | code_check | untagged | — |
| t85_known_cells | 재사용 MAE 0.0142 → 0.0052; 비 Σ\|예측 − m\| 0.0483 → 0.0254 | N = 6·8·10 사후 대조 (blind 아님) | docs/research/TASK85.md @ ffd716f | post_hoc | untagged | F_c |
| t90_v12_not_frozen | 초과 cell v1.2 후보 8 (v1 8, v1.1 7, sim 6) | 동결 전 점검, 9 cell | docs/research/TASK90.md @ 338d3de | dev_set | untagged | P10 |
| t90_v12_metrics | 재사용 MAE 0.054; 비 Σ\|편향\| 0.132 | v1.2 후보 | docs/research/TASK90.md @ 338d3de | dev_set | untagged | P10 |
| t90_v11_freeze_mae | 0.0415 (원 표 0.042는 반올림 오기, 정정 기록) | 재사용 MAE v1.1, 동결 전 점검 9 cell | docs/research/TASK90.md @ f6ffd8f (정정 절), `freeze_check.json` | dev_set | untagged | P10 |
| t90_v12_base_bias | −0.130 / −0.162 / −0.109 | BASE 재사용 편향 v1.2 후보, N12 / 14 / 16 | docs/research/TASK90.md @ 338d3de | dev_set | stack | P10 |
| t90_rho | 0.733–0.743 | 완료 순서 ρ | docs/research/TASK90.md @ 338d3de | dev_set | stack | — |
| t90_sim_dev_mae | 0.012 | 재사용 MAE, sim, 9 cell | docs/research/TASK90.md @ 338d3de | dev_set | untagged | P10 |
| t90_sim_ratio_bias | +0.032–+0.059 (batch 16 6 cell 전부 > 0.015) | 비 편향, sim | docs/research/TASK90.md @ 338d3de | dev_set | stack | P10 |

## 8. 배타 prefill과 gap 모양 (TASK90 발견 1)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t90_gap_shape_exclusive | −0.395 / −0.450 | step 가중 running, gap 모양 (E−D), BASE N14 / N16 | docs/research/TASK90.md @ 338d3de | dev_set | class | P10 |
| t90_gap_shape_nonexclusive | +0.401 / +0.663 / −0.001 | 같은 변경, 비배타 (C′−C), BASE N12 / 14 / 16 | docs/research/TASK90.md @ 338d3de | dev_set | class | P10 |
| t90_exp_gap_b2_vs_sim | 6.62 vs 6.68; 7.50 vs 7.31 | 지수 gap: D vs B2, BASE N14 / N16 | docs/research/TASK90.md @ 338d3de | dev_set | class | P10 |
| t90_markov_insensitive | 6.647 / 7.370 vs D 6.615 / 7.500 | 엔진 Markov 연쇄, BASE N14 / N16 | docs/research/TASK90.md @ 338d3de | dev_set | stack | — |
| t90_phi_meanfield | +0.13–0.19 | (i) prefill 평균장 | docs/research/TASK90.md @ 338d3de | dev_set | untagged | — |
| t90_service_dist | −0.12–−0.18 | (iii) 서비스 분포 | docs/research/TASK90.md @ 338d3de | dev_set | untagged | — |
| t90_weighting_correction | N14 6.68 대 6.28, N16 7.31 대 6.87 (+0.40, +0.43) | v1 B2 평균 running, step 가중 (TASK87 6.95·7.55 정정) | docs/research/TASK90.md @ 338d3de | dev_set | universal | — |

## 9. 사건 재생 (두 기판)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g12_replay_hit | 16,794 / 16,794; 55/55 lifecycle 정확 일치율 1.000 | GPU 판정 모집단 turn ≥ 1 요청 | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | P06 |
| g12_replay_report_pop | 23,076 / 23,076 | GPU 보고 모집단 | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | P06 |
| g12_free_count | `LOOKUP` 27,652 / 27,652, `ALLOC` 27,652 / 27,652 | free block 수 | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_eviction_sequence | 958,078건 전부 같은 위치 | `BlockRemoved` 순서열 | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_n26_base | 1,366 / 1,366; 관측 0.450 vs sim LRU 0.657 | N26 BASE | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | class | P06 |
| g12_counterfactual | FIFO 0.627–0.837; 할당 후 조회 0.816–0.976; prompt만 캐시 0.091–0.608 | 대안 규칙 hit 정확 일치율 (판정 밖) | docs/research/gpu/GTASK12.md @ 3ddbba8 | exploratory | untagged | — |
| g12_release_lag | lag 1 free 1.000; lag 0 0.955; lag 2 0.142 | free 수 일치율 | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_two_substrate | NPU R5′ 1,298/1,298; GPU 16,794/16,794 | 사건 재생 두 기판 (발견 4) | docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | universal | P06 |

## 10. 운영 step 시간 척도와 채널 분해

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g13_x1210_n26 | +0.207 → +0.009 | N26 BASE 재사용 차, orig → x1.210 | docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07, F_b |
| g13_x1210_mae | 0.0173 → 0.0047 | 확증 9 cell 재사용 MAE, orig → x1.210 | docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07 |
| g13_x1131_ratio | 0.0745 → 0.0127 | 비용 비 Σ\|오차\| 6 cell, orig → x1.131 | docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07 |
| g13_explained_n26 | 66 % / 96 % / 84 % | 발견 4 차이 설명 비율, x1.131 / x1.210 / mode_dist, N26 BASE | docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | — |
| g13_nonlinear | N20 0.857 → 0.860; N26 0.198 하락 | 재사용, 21 % step 연장 | docs/research/gpu/GTASK13.md @ 02257ab | dev_set | class | P07, F_b |
| g14_wait_underrep | 대기 중앙 0.01–0.02 s vs 관측 0.60–0.69 s | N20, 원래 sim vs 관측 | docs/research/gpu/GTASK14.md @ cc6a97e | exploratory | stack | F_d |
| g14_alloc_during_idle | Spearman −0.95 (orig), −0.87 (변형 합산 44점) | idle 중 할당량 평균 차 vs 재사용 오차 차, 11 cell | docs/research/gpu/GTASK14.md @ cc6a97e | exploratory | class | — |
| g15_lag1_scale | 1.210 (lag 0 cap 1.116) | 합 / 가격, 55 lifecycle | docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_full_decode_share | 89.4 %; 1.224 | lag 1 초과분 비중; FULL decode lag 1 / 가격 | docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_per_request | d = 1 1.034 → d = 8 1.219; 요청당 약 0.35 ms | FULL decode 비, decode 폭 | docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_small_p_idle | 4.8 %; 0.0003 % | small-p eager 지연; idle 조각 (lag 1 초과분 비중) | docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| t91_decode_step_ratio | 1.084 / 1.076 / 1.085 / 1.069 | step 가중 관측/예측, BASE / BATCHONLY / TUNED / DP | docs/research/TASK91.md @ a210be2 | dev_set | stack | P07 |
| t91_decode_excess_range | 3–17 %; step 가중 1.07–1.09 | 운영 decode step 초과 | docs/research/TASK91.md @ a210be2 | dev_set | stack | P07 |
| t91_per_request_excess | 약 0.28 ms (관측 기울기 0.32 ms/요청 대 모형 0.041) | b8 decode step | docs/research/TASK91.md @ a210be2 | dev_set | stack | — |
| t91_two_substrate_shape | NPU 약 0.3 ms/요청, GPU 약 0.35 ms/요청 | 운영 step 초과 요청당 | docs/research/TASK91.md @ a210be2 | dev_set | class | — |
| t91_small_prefill | 1.32–1.35; 28.0 대 21.3 ms | ≤ 128 token 배타 prefill 관측/예측 | docs/research/TASK91.md @ a210be2 | dev_set | untagged | — |
| t91_sim_bias_explained | 48.5 % (Σ 0.262 → 0.135) | sim 비 편향, batch 16 6 cell | docs/research/TASK91.md @ a210be2 | dev_set | stack | P07 |
| t91_base_reuse_scaled | N12 +0.023 → −0.005, N14 +0.032 → −0.021, N16 +0.026 → +0.007 | BASE 재사용 편향, 시간 척도 적용 | docs/research/TASK91.md @ a210be2 | dev_set | untagged | P07 |
| t91_attribution | 20,166 요청 전부 일치, 건너뜀 0 | decode step 수 = `completion_tokens − 1` | docs/research/TASK91.md @ a210be2 | code_check | untagged | — |

## 11. 정상성

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t83_h | WEAK_EVIDENCE; q_h 중앙값 0.638; 10/13 (p = 0.046) | 13 cell h | docs/research/TASK83.md @ 339557a | retro_check | stack | P08 |
| t83_reuse_decline | NOT_NONSTATIONARY; q_Δ 중앙값 0.45; 9/13 (p = 0.133) | 13 cell 재사용 | docs/research/TASK83.md @ 339557a | retro_check | stack | P08 |
| t83_window_length | run 사이 0.17–0.45 vs run 안 0.25–0.48 | 같은 길이 60 s TVD | docs/research/TASK83.md @ 339557a | retro_check | universal | P08 |
| t83_by_load | N ≤ 8 0.64–0.72; N ≥ 10 0.33–0.61 | q_h | docs/research/TASK83.md @ 339557a | retro_check | stack | P08 |
| g16_h | NOT_NONSTATIONARY; q_h 중앙 0.43, k 4/11, p 0.89 | 11 cell h decode-only | docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |
| g16_reuse_decline | NOT_NONSTATIONARY; q_Δ 중앙 0.44, k 7/11, p 0.27 | 11 cell 재사용 | docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |
| g16_collapse_variability | \|D\| 중앙 0.20–0.22 vs 0.02–0.08 | 같은 위치 60 s 재사용, 붕괴 cell vs 기타 | docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |

## 12. 시뮬레이터 통합과 수치 수정

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t89_gpu_wrapper_exact | 44 항목 차이 0 | 11 cell × sim_lru·sim_fifo × lo·hi | docs/research/TASK89.md @ 1445aa1 | code_check | class | — |
| t89_npu_regression | 72 파일 차이 0; 105/105 run | NPU 회귀 | docs/research/TASK89.md @ 1445aa1 | code_check | untagged | — |
| t89_v11_nondeterminism | 17개 값 상대 ≤ 1e-13 | v1.1 `onenormest` | docs/research/TASK89.md @ 1445aa1 | code_check | untagged | — |
| t89_python_sum | ≈ 2e-14 상대 | Python 3.12 vs 3.10 `sum()` | docs/research/TASK89.md @ 1445aa1 | code_check | universal | — |
| t88_underflow_fix | 최대 절대 차 1.7e-13 | 685,638 호출, 평균 ≥ 600 | docs/research/TASK88.md @ c9a526c | code_check | universal | — |
| t88_non_underflow | 최대 차 0.0 | 1,434,722 호출, 평균 < 600 | docs/research/TASK88.md @ c9a526c | code_check | universal | — |
| t88_npu_regression | 72 파일 차이 0; 105/105 run | NPU 회귀 | docs/research/TASK88.md @ c9a526c | code_check | untagged | — |

## 13. 격자–h 되먹임 (TASK78)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t78_n12_cycle | 순환 (3격자) | N = 12 sim 경로 최선 응답 반복 | docs/research/TASK78.md @ c714b03 | exploratory | universal | — |
| t78_pred_gain | 1.8 % (N=6) → 0.65 % (N=12) | TUNED 대비 격자 의존 비용 | docs/research/TASK78.md @ c714b03 | exploratory | stack | — |

## 14. 해석 모형 적용 범위 입력 (그림 d)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| h86_b2_queue_depth | N12 0.058·0.08; N14 0.27·0.50; N16 0.51·1.24 | BASE P(대기 > 0)·E[대기], v1 B2 고정점, 측정 전 계산 | docs/research/HILOAD_PREREG.md @ f75c8e7 | exploratory | untagged | F_d |
| h86_batch16_no_queue | 대기 0 (N ≤ 16) | batch 16 구성 | docs/research/HILOAD_PREREG.md @ f75c8e7 | exploratory | untagged | F_d |
| t82_n12_ttft | 0.286 s (다른 cell 0.068–0.084 s) | BASE N = 12 turn ≥ 1 TTFT 중앙 | docs/research/TASK82.md @ 074aedc | exploratory | untagged | F_d |
| t87_base_n16_ttft | 1.589 s | BASE N16 turn ≥ 1 TTFT 중앙 | docs/research/TASK87.md @ a210be2 | exploratory | untagged | F_d |
| q96_obs_base | N6 0.013, N8 0.018, N10 0.044, N12 0.280, N13 0.420, N14 0.761, N16 1.802, N17 3.528, N20 6.820 | 관측 대기 Q 평균(client in-flight − `[BUCKET]` request_nums, decode step 가중), BASE | docs/research/TASK96.md @ f6ffd8f, `queue_depth_obs.py` | exploratory | untagged | F_d, P11 |
| q96_obs_floor | N ≤ 8 전 구성 0.013–0.018; batch 16 N10–16 0.022–0.040 | 관측 Q, 구조적 대기 0 cell — 전송·응답 종료 시간의 바닥값(요청률과 함께 증가) | docs/research/TASK96.md @ f6ffd8f | exploratory | untagged | F_d |
| q96_obs_batch16_n17_20 | N17 0.045 / 0.045, N20 0.099 / 0.096 | 관측 Q, BATCHONLY / TUNED (N > 16) | docs/research/TASK96.md @ f6ffd8f | exploratory | untagged | F_d, P11 |


## 16. 통합 시뮬레이터 blind cell N = 13·17·20과 운영 step 비용 (TASK92–95)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t92_short_ctx_decode | 관측/통제 artifact 중앙 1.009 / 1.000 / 1.002 / 0.994; n별 0.972–1.084 | 짧은 context 통제 부하 decode, BASE / BATCHONLY / TUNED / DP | docs/research/TASK92.md @ cc29e76 | exploratory | stack | — |
| t92_long_ctx_decode | 1.03–1.15 (n = 4: 1.110–1.146) | 긴 context(multi-turn형) 깨끗한 decode step 관측/통제 | docs/research/TASK92.md @ cc29e76 | exploratory | stack | — |
| t92_small_prefill | 통제 대비 1.23–1.48; 적합 대비 1.14–1.35 | ≤ 512 token 배타 prefill, 운영 경로 통제 부하 | docs/research/TASK92.md @ cc29e76 | exploratory | stack | — |
| t92_opcost_prefill_a | 22.70 / 23.39 / 22.93 / 23.06 ms (통제 21.2) | prefill chunk 비용 a, 운영 적합 | docs/research/TASK92.md @ cc29e76 | exploratory | stack | — |
| t92_reproducibility | n4 +0.7 %; n8 +2.4 % | 반복 lifecycle 중앙값 차, TUNED | docs/research/TASK92.md @ cc29e76 | exploratory | stack | — |
| t95_validity | 45/45 유효, 재실행 0 | lifecycle | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11 |
| t95_s51_simop | PASS; 8/8 ≤ 0.10; MAE 0.0161 ≤ 0.5 × 0.1899 | 재사용률, sim_op(주), 8 cell (BASE N20 정보 없음) | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11, F_b, F_c |
| t95_s51_sim | PASS; MAE 0.0132 | 재사용률, sim(원래 비용) | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11, F_c |
| t95_s52_simop | PASS; 기본 6/6, 강화 6/6; Σ 0.1086 ≤ 0.5 × 1.4400 | 비용 비, sim_op | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11, F_b, F_c |
| t95_s52_sim | FAIL; 기본 5/6 (TUNED N13 \|0.8942 − 0.8614\| = 0.0328 > 0.03) | 비용 비, sim | docs/research/TASK95.md @ e3697b0 | blind_fail | untagged | P11, F_c |
| t95_s53_ranking | PASS; 해소 8쌍 일치 (N20 BATCHONLY/TUNED 1.0244 [0.9945, 1.0411] 미해소) | 구성 순위 | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11 |
| t95_s56_h | PASS; TVD 중앙 0.060, 최대 0.119; 영 0.586 | h(n), sim_op, 9 cell (BASE N20 포함) | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | — |
| t95_simop_vs_sim | FAIL; 재사용 MAE 0.0161 > 0.0132, 비 Σ 0.1086 > 0.1017 | 운영 비용 sim 대 원래 비용 sim | docs/research/TASK95.md @ e3697b0 | blind_fail | untagged | P11 |
| t95_base_collapse | 관측 0.419 / 0.047 / 0.000 vs sim_op 0.427 / 0.068 / 0.000 | BASE 재사용, N13 / 17 / 20 | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11, F_b |
| t95_batch16_over_ceiling | 관측 0.750 / 0.757 / 0.584 / 0.597; \|오차\| ≤ 0.040 | batch 16 재사용, BATCHONLY / TUNED N17, N20 (N > 동시 실행 상한) | docs/research/TASK95.md @ e3697b0 | blind_confirm | untagged | P11, F_c |
| t95_config_effect | 평균 \|1 − m\| 0.240; m 0.6949–0.8746 | BASE 대비 비, 6 cell | docs/research/TASK95.md @ e3697b0 | blind_confirm | stack | P11, F_b |
| t95_v1_out_of_scope | 재사용 −0.05 – −0.21, 비 +0.09 – +0.18 | v1 오차, batch 16 N17·20 (범위 밖, 참고) | docs/research/TASK95.md @ e3697b0 | exploratory | untagged | P11, F_d |
| t95_prior_prediction | §5.2 사전 예측 빗나감 (FAIL 예측 → (1) PASS); 나머지 4항목 적중 | 사전 예측 대조 | docs/research/TASK95.md @ e3697b0 | blind_fail | untagged | — |


## 17. context 길이 step 비용과 사후 재예측 (TASK97–98)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t97_validity | 29/29 유효, 재실행 0; 재현성 +0.94 % / −0.55 % | lifecycle; TUNED n4 L1500 / n8 L3000 반복 | docs/research/TASK97.md @ 8b54b5a | exploratory | untagged | — |
| t97_ctx_slope | c 0.145 (BASE) / 0.149 (TUNED) µs/token; β −0.005 / −0.017 ms | F1 `f(b) + βn + c·ΣL`, decode step | docs/research/TASK97.md @ 8b54b5a | exploratory | stack | P12 |
| t97_fit_rms | F1 0.237 / 0.361 ms; F2 0.235 / 0.355; F3 0.240 / 0.396 | 형태별 RMS 잔차, BASE / TUNED | docs/research/TASK97.md @ 8b54b5a | exploratory | untagged | — |
| t97_ratio_L3000 | n8 1.249 / 1.249; n16 1.369 (TUNED) | L = 3,000 관측/통제, BASE / TUNED | docs/research/TASK97.md @ 8b54b5a | exploratory | stack | — |
| t97_ratio_L512 | 0.98–1.03 | L = 512 관측/통제 | docs/research/TASK97.md @ 8b54b5a | exploratory | stack | — |
| t97_operational_check | TASK91 모집단 1.095 / 1.096 (관측 1.084 / 1.085); TASK92 op-prefill-mt 1.113 / 1.100 (관측 1.113 / 1.107) | context 비용/통제 비용, step 가중, BASE / TUNED | docs/research/TASK97.md @ 8b54b5a | exploratory | stack | P12 |
| t98_finding4_bias | Σ 0.262 → sim_op 0.185, sim_ctx 0.174, sim_ctx_op 0.111; 평균 +0.044 → +0.018 | 비 오차, batch 16 N12·14·16 6 cell | docs/research/TASK98.md @ 8b54b5a | post_hoc | stack | — |
| t98_task95_cells | 비 Σ 0.102 → sim_ctx 0.041; 재사용 MAE 0.0132 → 0.0066 | TASK95 cell 사후 재예측 (판정 불변) | docs/research/TASK98.md @ 8b54b5a | post_hoc | untagged | — |
| t98_task87_cells | 비 Σ 0.189 → sim_ctx 0.109, sim_ctx_op 0.081 | TASK87 cell 사후 재예측 | docs/research/TASK98.md @ 8b54b5a | post_hoc | untagged | — |
| t98_regression | TASK93 `PREDICTIONS_SIM.json` byte 동일 | `decode_cost_fn` hook 추가 후 회귀 | docs/research/TASK98.md @ 8b54b5a | code_check | untagged | — |


## 18. BATCHONLY context 비용과 context 비용 시뮬레이터 blind cell N = 15·18 (TASK100–102)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| t100_batchonly_ctx | c 0.146 µs/token; β −0.069 ms; F1 RMS 0.461 ms; 재현성 +0.07 % | BATCHONLY decode step, F1 | docs/research/TASK100.md @ cb1eec4 | exploratory | stack | P12 |
| t100_rule_diff | ±0.15 ms (약 1 %) | TASK98 규칙값 − 실측, 대표 n·L step 시간 | docs/research/TASK100.md @ cb1eec4 | exploratory | untagged | — |
| t102_validity | 30/30 유효, 재실행 0 | lifecycle | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13 |
| t102_s51 | PASS; 6/6; MAE 0.0090 ≤ 0.5 × 0.2571 | 재사용률, sim_ctx_op(주), 6 cell | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13, F_b, F_c |
| t102_s52 | PASS; 기본 4/4, 강화 4/4; Σ 0.0491 ≤ 0.5 × 1.1086 | 비용 비, sim_ctx_op | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13, F_b, F_c |
| t102_s53 | PASS; 해소 5쌍 일치 (N18 BATCHONLY/TUNED 1.0286 [0.9978, 1.0608] 미해소) | 구성 순위 | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13 |
| t102_s56 | PASS; TVD 중앙 0.034, 최대 0.046 (sim 0.073); 영 0.588 | h(n), sim_ctx_op | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13 |
| t102_main_vs_sim | PASS; 재사용 MAE 0.0090 < 0.0093; 비 Σ 0.0491 < 0.0542 | context 비용 sim 대 원래 비용 sim | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P12, P13 |
| t102_sim_orig | §5.1 PASS (MAE 0.0093), §5.2 PASS (Σ 0.0542), §5.6 PASS (0.073) | 원래 비용 sim (2) | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P12, P13, F_c |
| t102_base_reuse | N15 관측 0.128 vs (1) 0.110 / (2) 0.156; N18 0.026 vs 0.045 / 0.026 | BASE 재사용 | docs/research/TASK102.md @ 15742d7 | blind_confirm | untagged | P13, F_b |
| t102_prior_prediction | §5.2 (2) 사전 예측 빗나감 (FAIL 예측 → PASS); 나머지 적중 | 사전 예측 대조 | docs/research/TASK102.md @ 15742d7 | blind_fail | untagged | — |

## 19. GPU 결과 요약 병합 (GTASK01–20, docs/research/gpu/GPU_RESULTS_SUMMARY.md)

### GTASK01 — inventory·source 감사

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g01_same_upstream | vllm 0.22.0 (CUDA 13.0 빌드); 인용 source 줄 위치 일치; model revision·byte 수 일치 | NPU `+cpu` 빌드 대비 source 감사 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_lookup_then_alloc | 조회 → hit `touch` → 할당; 같은 admission hit 축출 경로 없음 | `scheduler.py:594 → 721` | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_release_lru | release 시점 LRU, 요청 안 tail-first, 미사용 block 먼저 | block pool 회수 규칙 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | class (형태) / stack (세부) | — |
| g01_hit_formula_shape | `floor(min(shared, query−1)/B)·B`, B = 16, shared ≤ prompt + output − 1 | hit 공식 (NPU B = 128, prefill token만) | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | class (형태) / stack (값) | — |
| g01_preemption | recompute preemption 있음, 끌 수 없음, FCFS 최신 admission | preemption 경로 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_mixed_prefill | chunked prefill off에서도 decode와 같은 step | prefill 실행 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_grid_token_mapping | 격자 사상 = token 수; server 인자로 변경 | cudagraph capture size | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_runner_v2_metrics | Qwen3 기본 model runner v2; `--cudagraph-metrics` 없음 | 관측 수단 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_null_block | 비요청 KV 소비자 null block 1개 (상수) | KV 소비자 | docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |

### GTASK02 — Stage 0

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g02_stage0 | PASS; C0–C5 전부 충족 | 선등록 Stage 0 조건 (L2) | docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_pool_grid_args | override 16,034 → 2,048 block; 격자 [1,2,4,6,8] 반영; GPU 0 사용량 44,356 → 12,826 MiB | server 인자 고정·확인 | docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_hit_formula | 5/5 (두 lifecycle) | hit 공식 사례 | docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | class (형태) / stack (값) | — |
| g02_generated_token_cached | 1,024 hit (prompt만 캐시면 992) | H5: 1,000 prompt + 40 생성 재도착 | docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_v1_runner_blocked | v1 runner 기동 실패 (FlashInfer sampler JIT, `nvcc` 부재) | L3 관측 경로 | docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_no_double_blocks | `num_gpu_blocks` 2배 누적 없음 (2048) | frontend `cache_config_info` | docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_budget_unlogged | `max_num_batched_tokens` 로그·metric에 없음 | resolved config dump | docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_descriptor_fit_gaps | 11건 | `SubstrateDescriptor` 적합성 문제 | docs/research/gpu/GTASK02.md @ 2c4e732 | code_check | untagged | — |

### GTASK03 — 관측 수단·관문 G1–G3

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g03_g1_original | FAIL; (c)(d)(f) 실패 (warmup 2 step 미예상, endpoint 오류) | 관문 G1 의미론, 원 기준 | docs/research/gpu/GTASK03.md @ a95c20a | blind_fail | untagged | — |
| g03_g1_amended | PASS; (a)–(f); hit 23/23, 사상 375/375 | 관문 G1, 개정 1 | docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | stack | — |
| g03_g2_observer | PASS; 순차 15/15 동일, 시간 비 중앙 1.0018 (원 0.975); server CPU 차 0.01 s | 관문 G2 관찰자 효과 | docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | universal | — |
| g03_g3_recovery | PASS | 관문 G3 복구 | docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | untagged | — |
| g03_warmup_steps | non-dummy step 2개 (8 요청, 16·8 token), 첫 LOOKUP free 2,047 | server 기동 warmup | docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |
| g03_kv_events_content | seed prompt block 178/178 내용 복원 | KV events (ipc endpoint) | docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |
| g03_batch_nondeterminism | 재실행 5/8 동일 (첫 실행 8/8) | 동시 batch 생성 token | docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |

### GTASK05 — step 비용 (FULL·PIECEWISE·eager)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g05_full_decode | 13.3–14.4 ms | FULL decode step, n = 1–16 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | silicon / stack | — |
| g05_g_slope | 0.041 ms/요청 (n 1 → 16 약 7 %) | `F[b] + g·n` 적합 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | class (형태) / silicon (값) | — |
| g05_padding_vs_eager | padding +0.46 ms (+3.4 %) vs 격자 밖 eager +5.7–5.9 ms (+42 %) | n = 9 → 16 padding; n > 8 eager | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | class (형태) / silicon·stack (값) | — |
| g05_eager_dispatch_delay | 약 4 ms/step | eager dispatch 지연, prompt 길이 무관 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | stack | — |
| g05_lag1 | L = 1 (p = 2048 첫 chunk elevation L0 3.2 / L1 138.9 / L2 3.3 ms) | async scheduling dispatch 귀속 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | universal | — |
| g05_eager_increment | 12 → 138 ms | eager 증분, p = 256 → 2048 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | stack | — |
| g05_piecewise | UNKNOWN (dispatch 채널 분해능 약 2 ms 아래) | PIECEWISE 증분 | docs/research/gpu/GTASK05.md @ 3f5d930 | withheld | untagged | — |
| g05_prereg_analysis | 선등록 분석 실패 (p = 2048 chunk 분할) → 개정 2 (수치 확인 전) | 분석 방법 | docs/research/gpu/GTASK05.md @ 3f5d930 | blind_fail | untagged | — |
| g05_card_change | 6/6 lifecycle 유효 (측정 카드 `4485e769…`, 개정 1) | host 다운 후 재측정 | docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | untagged | — |

### GTASK06 — descriptor 구조 요구사항

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g06_rule_fields | 규칙 field 5개 (축출 기준, 창 시작, 요청 내부 손실 순서, 조회·할당 순서, 캐시 대상) | 두 기판 생존 규칙 차이 | docs/research/gpu/GTASK06.md @ a36bb67 | code_check | class | — |
| g06_requirement_groups | 11개 묶음 (A–K) | descriptor 구조 요구사항 | docs/research/gpu/GTASK06.md @ a36bb67 | code_check | untagged | — |
| g06_runtime_flags | pool·격자 = runtime flag (`value_source` 필요) | GPU 구성 파라미터 | docs/research/gpu/GTASK06.md @ a36bb67 | code_check | stack | — |

### GTASK07 — multi-turn 설계·wrapper

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g07_token_id_streaming | 6/6 (생성 token까지 hit 식 일치) | streaming token id 재도착 prompt | docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_sim_not_expressible | `continuum.sim` 전제 3개 불일치 → GPU wrapper | 시뮬레이터 표현 | docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_lru_underflow | Poisson 평균 > 745에서 전부 손실; 수정 전 pool 무감응 (N12 1,900·2,600 모두 0.913) | neutral `lru_block_survival` | docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_design_changes | 15개 항목 | NPU 설계 대비 변경 | docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | untagged | — |

### GTASK08 — 구성 blind 선정

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g08_preemption_bound | pool ≥ 1,857 → BASE 1,900, 격자 (1,2,4,8,16) | preemption 불가 하한 (최악 요청 3,712 token) | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |
| g08_confirm_n | N = 20 · 22 · 24; POOL 2,300; POOL+GRID (1,5,7,8,16) | blind 구성 선정 (측정 없음) | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |
| g08_rule5_amendment | 규칙 5 (상한 0.85) 해 없음 → 개정 1 (0.90) | POOL 선정 규칙 | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | untagged | — |
| g08_pressure_near_ceiling | BASE 재사용 < 0.85는 평균 running 7.1–7.7 (상한의 89–97 %) | 재사용 압력 조건 | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | class (형태) / stack (값) | — |
| g08_collapse_pred | sim N24 0.78 → N26 0.37 (spread 0.07 → 0.31); 해석 N26 0.78 | BASE 재사용 붕괴 예측 | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | class | — |
| g08_lru_fifo_gap | 0.13–0.17 | LRU − FIFO 재사용, BASE N = 20–24 | docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |

### GTASK09 — 본 실험 예측 선등록

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g09_prereg | plan 20 + 파일럿 3; 세 예측기 × 두 bound; `PREDICTIONS.json` SHA256 `1be9a991…` | 본 실험 선등록 | docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | untagged | — |
| g09_lru_fifo_pred | 0.08–0.17 (9/9 cell); 부분 hit FIFO 10–14 % vs LRU 1–6 % | LRU − FIFO 예측 재사용 차 | docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | stack | — |
| g09_piecewise_impact | ≤ 0.04 % | §2.1 PIECEWISE 구간의 turn당 비용 영향 | docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | stack | — |
| g09_pool_ratio_pred | 0.96–0.99 | POOL/BASE 예측 비 | docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | untagged | — |
| g09_id_join_fix | id join 오류 1건 수정 | 계기 점검 | docs/research/gpu/GTASK09.md @ 2bef619 | code_check | untagged | — |

### GTASK10 — 파일럿

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g10_validity | 12/12 유효, preemption 0 | 파일럿 lifecycle | docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | untagged | — |
| g10_streaming_equiv | EQUIVALENT; 중앙 1.0066, CI [0.994, 1.009] | streaming / non-streaming turn당 device time | docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | stack | — |
| g10_mode_agreement | 불일치 0 (12 lifecycle 전 step) | step mode 예측 대 `[GSTEP]` mode | docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | stack | — |
| g10_direct_channel | +10–13 %; 구성 간 짝 ratio 차 ≤ 0.005 | 직접 dispatch / 가격 채널 | docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | stack | — |
| g10_pair_spread | 0.025–0.038 | POOL/BASE 짝 ratio 산포 | docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | untagged | — |
| g10_lifecycle_time | 3.2–4.0 분 | lifecycle 길이 | docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | untagged | — |

### GTASK17 — 운영 조건 요인 분해

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g17_validity | 16/16 유효, 재실행 0; 반복 차 최대 0.019 ms (0.14 %) | 8 조건 × r2 lifecycle | docs/research/gpu/GTASK17.md @ 1799357 | exploratory | untagged | — |
| g17_observer_effect | 효과 없음; stream 0.9999, kv 0.9998, admlog 0.9999, 상호작용 0.9998–0.9999 | 2³ 요인 효과 비, FULL n = 1–8 평균 | docs/research/gpu/GTASK17.md @ 1799357 | exploratory | stack | — |
| g17_gtask11_condition | 1.001 → 1.009 (운영 1.034 → 1.219); 기울기 0.0615 ms/요청 | `s1k1a1` / 가격, n = 1 → 8 (context 64–320) | docs/research/gpu/GTASK17.md @ 1799357 | exploratory | stack | — |
| g17_prior_prediction | 사전 예측 빗나감 (streaming 최대 요인 예상) | 사전 예측 대조 | docs/research/gpu/GTASK17.md @ 1799357 | blind_fail | stack | — |
| g17_autocommit_failure | driver 자동 commit 미실행 (ignored `sequence.log`); 기록 `rc=0` 오보 | 자동 local commit | docs/research/gpu/GTASK17.md @ 1799357 | code_check | untagged | — |

### GTASK18 — context 길이 step 비용

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g18_control_context | GTASK05 64–192 (평균 128); GTASK17 64–320 (평균 192); 운영 plan 평균 1,810, p05 1,102, p95 2,551, 최대 3,273 | decode 중 요청당 context, decode step 가중 | docs/research/gpu/GTASK18.md @ f0d8000 | retro_check | untagged | P12 |
| g18_validity | 2/2 유효, 재실행 0; 반복 차 최대 0.028 ms | lifecycle × 18 cell | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | untagged | — |
| g18_ctx_slope | c = 0.212 µs/token; a = 13.432 / 13.285 / 13.265 / 13.414 ms; 잔차 최대 0.094 ms | F1 `t = a(n) + c·ΣL`, 균일 16 cell, n = 1 / 2 / 4 / 8 | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | class (형태) / stack (값) | P12 |
| g18_sum_not_max | n8mix 잔차 +0.002 ms (16.50 vs n·max L 18.57); n4mix +0.031 | 혼합 context cell | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | class | — |
| g18_per_n_slope | 0.259 / 0.224 / 0.213 / 0.210 µs/token | n별 c, n = 1 / 2 / 4 / 8 | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_ratio_L3000 | n1 1.057; n4 1.188; n8 1.364 | L = 3,000 / 가격 | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_ratio_L64 | 1.001–1.002 | L = 64 / 가격 | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_gtask15_repro | F1 1.030 / 1.058 / 1.081 / 1.108 / 1.132 / 1.160 / 1.185 / 1.210 vs 운영 1.034 … 1.219; 설명 81–96 % | GTASK15 운영 비율 재현, d = 1–8, plan 평균 L만 입력 | docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | P12 |
| g18_prior_prediction | 5개 중 c·L3000·혼합 적중; F1 ±0.03 7/8 (d = 7 −0.042); L64 n = 8 −0.74 % 빗나감 | 사전 예측 대조 | docs/research/gpu/GTASK18.md @ f0d8000 | blind_fail | untagged | — |

### GTASK19 — 정정 기록

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g19_n24_base_definition | `lo` 0.75318 (1,361/1,807) = 0.753; §5.5 bound 평균 0.75222 = 0.752; 판정 영향 없음 | GTASK11 N24 BASE sim LRU, 산출 파일 대조 | docs/research/gpu/GTASK19.md @ a99f23c | retro_check | untagged | P04 |

### GTASK20 — 붕괴 영역 blind N = 25·28

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g20_validity | 30/30 유효, 재실행 0 | lifecycle (2 N × 3 구성 × 5) | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | P14 |
| g20_s51_ctx | PASS; 6/6 ≤ 0.10; 평균 부호 +0.022 / +0.023; MAE 0.022 / 0.023 ≤ 0.5 × 0.233 | 재사용률, (1) ctx 주, 6 cell (lo / hi) | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P14, F_b, F_c |
| g20_s52_ctx | PASS; 기본 4/4, 강화 4/4; Σ 0.040 / 0.028 ≤ 0.5 × 0.392 / 0.406 | 비용 비, (1) ctx, 4 cell (lo / hi) | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P14, F_b, F_c |
| g20_s53_ranking | PASS N25·N28; BASE 포함 쌍 해소, POOL/POOL+GRID 1.002 · 1.000 미해소 | 구성 순위, (1) ctx | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | — |
| g20_s56_h | PASS; TVD 중앙 0.049 / 0.048, 최대 0.052 / 0.051; 균등 0.763 | h decode-only, (1) ctx, 6 cell | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | P14 |
| g20_ctx_vs_price | CONFIRMED; BASE 재사용 오차 0.075 / 0.084 vs 0.348 / 0.319; 비 Σ 0.040 / 0.028 vs 0.135 / 0.110 | 추가 확증 (1) ctx < (3) 가격 (lo / hi) | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P12, P14 |
| g20_price_fail | §5.1 FAIL (N25 BASE +0.22, MAE 0.108); §5.2 FAIL (기본 2/4) | (3) 가격 기준선 | docs/research/gpu/GTASK20.md @ 517cff8 | blind_fail | stack | P12, P14, F_c |
| g20_calibrated | §5.1·5.2·5.6 PASS; BASE 재사용 오차 0.031 / 0.012 (×1.210), 0.027 / 0.035 (mode_dist); 비 Σ 0.042 / 0.029, 0.024 / 0.035 | (2) 보정 예측 (GTASK11 관측으로 맞춤), 보고 | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P14, F_c |
| g20_base_collapse | 관측 0.475 / 0.366 vs ctx 0.514 / 0.403, ×1.210 0.494 / 0.353, 가격 0.696 / 0.494 | BASE 재사용, N25 / N28 (lo) | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P14, F_b |
| g20_config_effect | m 0.8933–0.9145 (lo); ctx 예측 0.8969–0.9047 | BASE 대비 비, 4 cell | docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | P14, F_b |
| g20_reuse_overpred | +0.005 – +0.049 (6/6 같은 방향) | (1) ctx 재사용 계통 편향 (G-08 결정: 추가 측정 없음) | docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | stack | — |
| g20_replicate_spread | N28 BASE 0.03–0.59; N25 BASE 0.23–0.63 | replicate별 재사용 (G-08 결정: 반복 없음) | docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | stack | — |
| g20_prior_prediction | §5.2 사전 예측 빗나감 (FAIL 예측 → PASS); 나머지 적중 | 사전 예측 대조 | docs/research/gpu/GTASK20.md @ 517cff8 | blind_fail | untagged | — |
| g20_direct_channel | 중앙 1.049 (0.930–1.144) | 직접 dispatch / 가격, 30 lifecycle | docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | untagged | P14 |


## 20. 예측 대기열 대 관측 대기열 (TASK109, 지시문 15 작업 E)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| q109_reproduced | 33/33 cell 재계산 재사용률 = 선등록 예측 파일 값 | 같은 입력·코드로 대기열 재계산의 동일성 확인 | paper/QUEUE_PRED_VS_OBS.md (TASK109 commit) | code_check | untagged | — |
| q109_corr_sim | Pearson 0.999, Spearman 0.820, MAE 0.058 (주 sim); 해석 모형 0.999 / 0.911 / 0.220 | 예측 대 관측 대기열, NPU 33 cell, decode step 가중 | paper/QUEUE_PRED_VS_OBS.md (TASK109 commit) | exploratory | untagged | — |
| q109_underpred | BASE N ≥ 12 예측/관측 중앙: 주 sim 0.876, 원래 비용 sim 0.830, 해석 0.656; GPU 원래 sim LRU 0.608 | 대기열 과소 예측 | paper/QUEUE_PRED_VS_OBS.md (TASK109 commit) | exploratory | untagged | — |
| q109_confusion | 문턱 Q = 0.1: 주 sim 33/33 같은 쪽(8 있음·25 없음); 해석 모형 32/33 (N12 BASE 관측 0.280, 예측 0.079) | 대기열 유무 분류 | paper/QUEUE_PRED_VS_OBS.md (TASK109 commit) | post_hoc | untagged | — |

## 15. 원고 수정 후보 ↔ id

| M id | source | result ids |
|---|---|---|
| M1 | docs/research/INDEX.md @ a210be2 (원고 수정 후보 표) | t72_R5prime, t72_73_failures, t72_all_failures_cause, t72_R5prime_alt_rules |
| M2 | docs/research/INDEX.md @ a210be2 | t72_R3, t72_R3_per_N_regret |
| M2′ | docs/research/INDEX.md @ a210be2 | t82_s54_dp_vs_tuned, t82_s54_pred, t82_batchonly_vs_dp, t82_s53_ranking |
| M3 | docs/research/INDEX.md @ a210be2 | t78_n12_cycle |
| M4 | docs/research/INDEX.md @ a210be2 | t83_h, t83_reuse_decline, t83_window_length, t83_by_load, t82_nonstationary_60s, g16_h, g16_reuse_decline |
| M5 | docs/research/INDEX.md @ a210be2 | t82_zero_predictor_level, t82_cell_diff, t82_s51_reuse |
