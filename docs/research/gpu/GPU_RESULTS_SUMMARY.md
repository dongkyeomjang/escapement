# GPU_RESULTS_SUMMARY

작성: 2026-10-02, GPU 지시문 G-08. 열·kind·layer 규칙은 `paper/RESULTS_INDEX.md`(origin/main `58e67a6`)와 같다. 그 색인에 이미 있는 id의 행은 값을 그대로 옮겼다(g11_collapse_curve 비고만 GTASK19 반영).

kind: blind_confirm · blind_fail · withheld · post_hoc · dev_set · exploratory · retro_check · code_check / layer: universal · class · stack · silicon · untagged (원 GTASK 문서의 태그만) / source: `origin/gpu-a6000:<path> @ <commit>` / data: `results/tables/` 표·그림 id (NPU 색인에 있는 행만)

## GTASK01 — inventory·source 감사

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g01_same_upstream | vllm 0.22.0 (CUDA 13.0 빌드); 인용 source 줄 위치 일치; model revision·byte 수 일치 | NPU `+cpu` 빌드 대비 source 감사 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_lookup_then_alloc | 조회 → hit `touch` → 할당; 같은 admission hit 축출 경로 없음 | `scheduler.py:594 → 721` | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_release_lru | release 시점 LRU, 요청 안 tail-first, 미사용 block 먼저 | block pool 회수 규칙 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | class (형태) / stack (세부) | — |
| g01_hit_formula_shape | `floor(min(shared, query−1)/B)·B`, B = 16, shared ≤ prompt + output − 1 | hit 공식 (NPU B = 128, prefill token만) | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | class (형태) / stack (값) | — |
| g01_preemption | recompute preemption 있음, 끌 수 없음, FCFS 최신 admission | preemption 경로 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_mixed_prefill | chunked prefill off에서도 decode와 같은 step | prefill 실행 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_grid_token_mapping | 격자 사상 = token 수; server 인자로 변경 | cudagraph capture size | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_runner_v2_metrics | Qwen3 기본 model runner v2; `--cudagraph-metrics` 없음 | 관측 수단 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |
| g01_null_block | 비요청 KV 소비자 null block 1개 (상수) | KV 소비자 | origin/gpu-a6000:docs/research/gpu/GTASK01.md @ 7bb07f5 | code_check | stack | — |

## GTASK02 — Stage 0

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g02_stage0 | PASS; C0–C5 전부 충족 | 선등록 Stage 0 조건 (L2) | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_pool_grid_args | override 16,034 → 2,048 block; 격자 [1,2,4,6,8] 반영; GPU 0 사용량 44,356 → 12,826 MiB | server 인자 고정·확인 | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_hit_formula | 5/5 (두 lifecycle) | hit 공식 사례 | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | class (형태) / stack (값) | — |
| g02_generated_token_cached | 1,024 hit (prompt만 캐시면 992) | H5: 1,000 prompt + 40 생성 재도착 | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | blind_confirm | stack | — |
| g02_v1_runner_blocked | v1 runner 기동 실패 (FlashInfer sampler JIT, `nvcc` 부재) | L3 관측 경로 | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_no_double_blocks | `num_gpu_blocks` 2배 누적 없음 (2048) | frontend `cache_config_info` | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_budget_unlogged | `max_num_batched_tokens` 로그·metric에 없음 | resolved config dump | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | exploratory | stack | — |
| g02_descriptor_fit_gaps | 11건 | `SubstrateDescriptor` 적합성 문제 | origin/gpu-a6000:docs/research/gpu/GTASK02.md @ 2c4e732 | code_check | untagged | — |

## GTASK03 — 관측 수단·관문 G1–G3

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g03_g1_original | FAIL; (c)(d)(f) 실패 (warmup 2 step 미예상, endpoint 오류) | 관문 G1 의미론, 원 기준 | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | blind_fail | untagged | — |
| g03_g1_amended | PASS; (a)–(f); hit 23/23, 사상 375/375 | 관문 G1, 개정 1 | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | stack | — |
| g03_g2_observer | PASS; 순차 15/15 동일, 시간 비 중앙 1.0018 (원 0.975); server CPU 차 0.01 s | 관문 G2 관찰자 효과 | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | universal | — |
| g03_g3_recovery | PASS | 관문 G3 복구 | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | blind_confirm | untagged | — |
| g03_warmup_steps | non-dummy step 2개 (8 요청, 16·8 token), 첫 LOOKUP free 2,047 | server 기동 warmup | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |
| g03_kv_events_content | seed prompt block 178/178 내용 복원 | KV events (ipc endpoint) | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |
| g03_batch_nondeterminism | 재실행 5/8 동일 (첫 실행 8/8) | 동시 batch 생성 token | origin/gpu-a6000:docs/research/gpu/GTASK03.md @ a95c20a | exploratory | stack | — |

## GTASK04 — 순차 생존 blind

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g04_sequential_survival | 60/60 | resume hit token, 60 trial, 측정 전 예측 | origin/gpu-a6000:docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | universal | P01, F_a |
| g04_block_staircase | 손실 시작 674, 전손 800 | 누적 배경 block, 배경 크기 4종 | origin/gpu-a6000:docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | class | P01, F_a |
| g04_generated_token_cached | 2,016 hit; T hash block 126 | 조건 (ii) | origin/gpu-a6000:docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | stack | P01 |
| g04_four_channels | 60 trial 네 채널 일치 | 응답·admission 로그·counter·KV events | origin/gpu-a6000:docs/research/gpu/GTASK04.md @ c7875fb | blind_confirm | universal | — |

## GTASK05 — step 비용 (FULL·PIECEWISE·eager)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g05_full_decode | 13.3–14.4 ms | FULL decode step, n = 1–16 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | silicon / stack | — |
| g05_g_slope | 0.041 ms/요청 (n 1 → 16 약 7 %) | `F[b] + g·n` 적합 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | class (형태) / silicon (값) | — |
| g05_padding_vs_eager | padding +0.46 ms (+3.4 %) vs 격자 밖 eager +5.7–5.9 ms (+42 %) | n = 9 → 16 padding; n > 8 eager | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | class (형태) / silicon·stack (값) | — |
| g05_eager_dispatch_delay | 약 4 ms/step | eager dispatch 지연, prompt 길이 무관 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | stack | — |
| g05_lag1 | L = 1 (p = 2048 첫 chunk elevation L0 3.2 / L1 138.9 / L2 3.3 ms) | async scheduling dispatch 귀속 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | universal | — |
| g05_eager_increment | 12 → 138 ms | eager 증분, p = 256 → 2048 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | stack | — |
| g05_piecewise | UNKNOWN (dispatch 채널 분해능 약 2 ms 아래) | PIECEWISE 증분 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | withheld | untagged | — |
| g05_prereg_analysis | 선등록 분석 실패 (p = 2048 chunk 분할) → 개정 2 (수치 확인 전) | 분석 방법 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | blind_fail | untagged | — |
| g05_card_change | 6/6 lifecycle 유효 (측정 카드 `4485e769…`, 개정 1) | host 다운 후 재측정 | origin/gpu-a6000:docs/research/gpu/GTASK05.md @ 3f5d930 | exploratory | untagged | — |

## GTASK06 — descriptor 구조 요구사항

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g06_rule_fields | 규칙 field 5개 (축출 기준, 창 시작, 요청 내부 손실 순서, 조회·할당 순서, 캐시 대상) | 두 기판 생존 규칙 차이 | origin/gpu-a6000:docs/research/gpu/GTASK06.md @ a36bb67 | code_check | class | — |
| g06_requirement_groups | 11개 묶음 (A–K) | descriptor 구조 요구사항 | origin/gpu-a6000:docs/research/gpu/GTASK06.md @ a36bb67 | code_check | untagged | — |
| g06_runtime_flags | pool·격자 = runtime flag (`value_source` 필요) | GPU 구성 파라미터 | origin/gpu-a6000:docs/research/gpu/GTASK06.md @ a36bb67 | code_check | stack | — |

## GTASK07 — multi-turn 설계·wrapper

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g07_token_id_streaming | 6/6 (생성 token까지 hit 식 일치) | streaming token id 재도착 prompt | origin/gpu-a6000:docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_sim_not_expressible | `continuum.sim` 전제 3개 불일치 → GPU wrapper | 시뮬레이터 표현 | origin/gpu-a6000:docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_lru_underflow | Poisson 평균 > 745에서 전부 손실; 수정 전 pool 무감응 (N12 1,900·2,600 모두 0.913) | neutral `lru_block_survival` | origin/gpu-a6000:docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | stack | — |
| g07_design_changes | 15개 항목 | NPU 설계 대비 변경 | origin/gpu-a6000:docs/research/gpu/GTASK07.md @ 9af6af9 | code_check | untagged | — |

## GTASK08 — 구성 blind 선정

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g08_preemption_bound | pool ≥ 1,857 → BASE 1,900, 격자 (1,2,4,8,16) | preemption 불가 하한 (최악 요청 3,712 token) | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |
| g08_confirm_n | N = 20 · 22 · 24; POOL 2,300; POOL+GRID (1,5,7,8,16) | blind 구성 선정 (측정 없음) | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |
| g08_rule5_amendment | 규칙 5 (상한 0.85) 해 없음 → 개정 1 (0.90) | POOL 선정 규칙 | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | untagged | — |
| g08_pressure_near_ceiling | BASE 재사용 < 0.85는 평균 running 7.1–7.7 (상한의 89–97 %) | 재사용 압력 조건 | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | class (형태) / stack (값) | — |
| g08_collapse_pred | sim N24 0.78 → N26 0.37 (spread 0.07 → 0.31); 해석 N26 0.78 | BASE 재사용 붕괴 예측 | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | class | — |
| g08_lru_fifo_gap | 0.13–0.17 | LRU − FIFO 재사용, BASE N = 20–24 | origin/gpu-a6000:docs/research/gpu/GTASK08.md @ cafbd95 | exploratory | stack | — |

## GTASK09 — 본 실험 예측 선등록

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g09_prereg | plan 20 + 파일럿 3; 세 예측기 × 두 bound; `PREDICTIONS.json` SHA256 `1be9a991…` | 본 실험 선등록 | origin/gpu-a6000:docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | untagged | — |
| g09_lru_fifo_pred | 0.08–0.17 (9/9 cell); 부분 hit FIFO 10–14 % vs LRU 1–6 % | LRU − FIFO 예측 재사용 차 | origin/gpu-a6000:docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | stack | — |
| g09_piecewise_impact | ≤ 0.04 % | §2.1 PIECEWISE 구간의 turn당 비용 영향 | origin/gpu-a6000:docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | stack | — |
| g09_pool_ratio_pred | 0.96–0.99 | POOL/BASE 예측 비 | origin/gpu-a6000:docs/research/gpu/GTASK09.md @ 2bef619 | exploratory | untagged | — |
| g09_id_join_fix | id join 오류 1건 수정 | 계기 점검 | origin/gpu-a6000:docs/research/gpu/GTASK09.md @ 2bef619 | code_check | untagged | — |

## GTASK10 — 파일럿

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g10_validity | 12/12 유효, preemption 0 | 파일럿 lifecycle | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | untagged | — |
| g10_streaming_equiv | EQUIVALENT; 중앙 1.0066, CI [0.994, 1.009] | streaming / non-streaming turn당 device time | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | stack | — |
| g10_mode_agreement | 불일치 0 (12 lifecycle 전 step) | step mode 예측 대 `[GSTEP]` mode | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | blind_confirm | stack | — |
| g10_direct_channel | +10–13 %; 구성 간 짝 ratio 차 ≤ 0.005 | 직접 dispatch / 가격 채널 | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | stack | — |
| g10_pair_spread | 0.025–0.038 | POOL/BASE 짝 ratio 산포 | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | untagged | — |
| g10_lifecycle_time | 3.2–4.0 분 | lifecycle 길이 | origin/gpu-a6000:docs/research/gpu/GTASK10.md @ 618cf27 | exploratory | untagged | — |

## GTASK11 — multi-turn 본 측정

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g11_validity | 55/55 유효, 재실행 0 | lifecycle | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | — |
| g11_lru_vs_fifo | LRU_SUPPORTED; d_L < d_F 8/9; Σd_L 0.148 vs Σd_F 0.937 | 분리 cell 9 | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | class (형태) / stack (값) | P04 |
| g11_partial_hit | 관측 0.9–7.4 % vs LRU 0.8–5.3 % vs FIFO 9.7–14.2 % | 부분 hit 비율, 9 cell | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | class (형태) / stack (값) | — |
| g11_orphan_evictions | 0 / 958,078 | KV events 고아 축출 / `BlockRemoved` | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | class (형태) / stack (값) | — |
| g11_sim_lru_reuse | PASS; MAE 0.0173; skill 0.35 | 재사용률, sim LRU, 확증 9 cell (lo) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P04, F_c |
| g11_sim_lru_ratio | PASS 6/6, 6/6; Σ 0.075 (0.36) | 비용 비, sim LRU, 6 cell (lo) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P04, F_c |
| g11_sim_fifo | FAIL; MAE 0.1021 | 재사용률, sim FIFO | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | untagged | P04 |
| g11_analytic_reuse | FAIL; N24 BASE +0.138; MAE 0.0333; skill 0.66 | 재사용률, 해석 v1 | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | stack | P04, F_c, F_d |
| g11_analytic_ratio | FAIL; N24 \|예측 − m\| 0.046·0.053; Σ 0.146 (0.70) | 비용 비, 해석 v1 | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | stack | P04, F_c, F_d |
| g11_null_mae | 0.0502 (경계 0.05) | §5.1 영 예측기 0.84718 MAE | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | P04, F_c |
| g11_ranking | PASS N20·22·24 | 순위, 해석 | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | P05 |
| g11_pool_grid | INCONCLUSIVE ×3; 0.9985–0.9988 | POOL+GRID/POOL | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | stack | P05 |
| g11_h | PASS; TVD 중앙 0.081, 최대 0.184; 영 0.645 | h(n) decode-only (lo) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_confirm | untagged | — |
| g11_h_reqs | FAIL (최대 0.212) | h(n) `reqs` 정의 (병기) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | blind_fail | untagged | — |
| g11_hsim_sign | lo 4/6, hi 6/6 음; 중앙 \|e\| 0.0135 | sim LRU 비 오차, H-sim 지표 (보고) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | stack | — |
| g11_collapse_curve | 관측 0.817 / 0.669 / 0.450 vs sim LRU 0.849 / 0.752 / 0.657 (0.752 = bound 평균; `lo` 기준 0.753, GTASK19 정정) | BASE 재사용, N22 / 24 / 26 (발견 4 문장) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | class | P04, F_b |
| g11_n26 | BASE 0.450 vs 해석 0.786, sim LRU 0.657, sim FIFO 0.552; m 0.899 [0.806, 0.907] | N = 26 재사용, POOL/BASE 비 (탐색) | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | class | P04, F_b |
| g11_direct_channel | 1.131 (0.973–1.156) | 직접 dispatch / 가격, 55 lifecycle 중앙 | origin/gpu-a6000:docs/research/gpu/GTASK11.md @ 22b50f4 | exploratory | untagged | — |

## GTASK12 — 사건 재생

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g12_replay_hit | 16,794 / 16,794; 55/55 lifecycle 정확 일치율 1.000 | GPU 판정 모집단 turn ≥ 1 요청 | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | P06 |
| g12_replay_report_pop | 23,076 / 23,076 | GPU 보고 모집단 | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | P06 |
| g12_free_count | `LOOKUP` 27,652 / 27,652, `ALLOC` 27,652 / 27,652 | free block 수 | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_eviction_sequence | 958,078건 전부 같은 위치 | `BlockRemoved` 순서열 | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_n26_base | 1,366 / 1,366; 관측 0.450 vs sim LRU 0.657 | N26 BASE | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | class | P06 |
| g12_counterfactual | FIFO 0.627–0.837; 할당 후 조회 0.816–0.976; prompt만 캐시 0.091–0.608 | 대안 규칙 hit 정확 일치율 (판정 밖) | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | exploratory | untagged | — |
| g12_release_lag | lag 1 free 1.000; lag 0 0.955; lag 2 0.142 | free 수 일치율 | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | stack | — |
| g12_two_substrate | NPU R5′ 1,298/1,298; GPU 16,794/16,794 | 사건 재생 두 기판 (발견 4) | origin/gpu-a6000:docs/research/gpu/GTASK12.md @ 3ddbba8 | retro_check | universal | P06 |

## GTASK13 — 시간 척도 (개발 집합)

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g13_x1210_n26 | +0.207 → +0.009 | N26 BASE 재사용 차, orig → x1.210 | origin/gpu-a6000:docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07, F_b |
| g13_x1210_mae | 0.0173 → 0.0047 | 확증 9 cell 재사용 MAE, orig → x1.210 | origin/gpu-a6000:docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07 |
| g13_x1131_ratio | 0.0745 → 0.0127 | 비용 비 Σ\|오차\| 6 cell, orig → x1.131 | origin/gpu-a6000:docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | P07 |
| g13_explained_n26 | 66 % / 96 % / 84 % | 발견 4 차이 설명 비율, x1.131 / x1.210 / mode_dist, N26 BASE | origin/gpu-a6000:docs/research/gpu/GTASK13.md @ 02257ab | dev_set | stack | — |
| g13_nonlinear | N20 0.857 → 0.860; N26 0.198 하락 | 재사용, 21 % step 연장 | origin/gpu-a6000:docs/research/gpu/GTASK13.md @ 02257ab | dev_set | class | P07, F_b |

## GTASK14 — 대기열 동역학

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g14_wait_underrep | 대기 중앙 0.01–0.02 s vs 관측 0.60–0.69 s | N20, 원래 sim vs 관측 | origin/gpu-a6000:docs/research/gpu/GTASK14.md @ cc6a97e | exploratory | stack | F_d |
| g14_alloc_during_idle | Spearman −0.95 (orig), −0.87 (변형 합산 44점) | idle 중 할당량 평균 차 vs 재사용 오차 차, 11 cell | origin/gpu-a6000:docs/research/gpu/GTASK14.md @ cc6a97e | exploratory | class | — |

## GTASK15 — 채널 분해

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g15_lag1_scale | 1.210 (lag 0 cap 1.116) | 합 / 가격, 55 lifecycle | origin/gpu-a6000:docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_full_decode_share | 89.4 %; 1.224 | lag 1 초과분 비중; FULL decode lag 1 / 가격 | origin/gpu-a6000:docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_per_request | d = 1 1.034 → d = 8 1.219; 요청당 약 0.35 ms | FULL decode 비, decode 폭 | origin/gpu-a6000:docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |
| g15_small_p_idle | 4.8 %; 0.0003 % | small-p eager 지연; idle 조각 (lag 1 초과분 비중) | origin/gpu-a6000:docs/research/gpu/GTASK15.md @ a5086b3 | exploratory | stack | — |

## GTASK16 — 정상성

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g16_h | NOT_NONSTATIONARY; q_h 중앙 0.43, k 4/11, p 0.89 | 11 cell h decode-only | origin/gpu-a6000:docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |
| g16_reuse_decline | NOT_NONSTATIONARY; q_Δ 중앙 0.44, k 7/11, p 0.27 | 11 cell 재사용 | origin/gpu-a6000:docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |
| g16_collapse_variability | \|D\| 중앙 0.20–0.22 vs 0.02–0.08 | 같은 위치 60 s 재사용, 붕괴 cell vs 기타 | origin/gpu-a6000:docs/research/gpu/GTASK16.md @ e820f48 | retro_check | stack | P08 |

## GTASK17 — 운영 조건 요인 분해

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g17_validity | 16/16 유효, 재실행 0; 반복 차 최대 0.019 ms (0.14 %) | 8 조건 × r2 lifecycle | origin/gpu-a6000:docs/research/gpu/GTASK17.md @ 1799357 | exploratory | untagged | — |
| g17_observer_effect | 효과 없음; stream 0.9999, kv 0.9998, admlog 0.9999, 상호작용 0.9998–0.9999 | 2³ 요인 효과 비, FULL n = 1–8 평균 | origin/gpu-a6000:docs/research/gpu/GTASK17.md @ 1799357 | exploratory | stack | — |
| g17_gtask11_condition | 1.001 → 1.009 (운영 1.034 → 1.219); 기울기 0.0615 ms/요청 | `s1k1a1` / 가격, n = 1 → 8 (context 64–320) | origin/gpu-a6000:docs/research/gpu/GTASK17.md @ 1799357 | exploratory | stack | — |
| g17_prior_prediction | 사전 예측 빗나감 (streaming 최대 요인 예상) | 사전 예측 대조 | origin/gpu-a6000:docs/research/gpu/GTASK17.md @ 1799357 | blind_fail | stack | — |
| g17_autocommit_failure | driver 자동 commit 미실행 (ignored `sequence.log`); 기록 `rc=0` 오보 | 자동 local commit | origin/gpu-a6000:docs/research/gpu/GTASK17.md @ 1799357 | code_check | untagged | — |

## GTASK18 — context 길이 step 비용

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g18_control_context | GTASK05 64–192 (평균 128); GTASK17 64–320 (평균 192); 운영 plan 평균 1,810, p05 1,102, p95 2,551, 최대 3,273 | decode 중 요청당 context, decode step 가중 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | retro_check | untagged | — |
| g18_validity | 2/2 유효, 재실행 0; 반복 차 최대 0.028 ms | lifecycle × 18 cell | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | untagged | — |
| g18_ctx_slope | c = 0.212 µs/token; a = 13.432 / 13.285 / 13.265 / 13.414 ms; 잔차 최대 0.094 ms | F1 `t = a(n) + c·ΣL`, 균일 16 cell, n = 1 / 2 / 4 / 8 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | class (형태) / stack (값) | — |
| g18_sum_not_max | n8mix 잔차 +0.002 ms (16.50 vs n·max L 18.57); n4mix +0.031 | 혼합 context cell | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | class | — |
| g18_per_n_slope | 0.259 / 0.224 / 0.213 / 0.210 µs/token | n별 c, n = 1 / 2 / 4 / 8 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_ratio_L3000 | n1 1.057; n4 1.188; n8 1.364 | L = 3,000 / 가격 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_ratio_L64 | 1.001–1.002 | L = 64 / 가격 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_gtask15_repro | F1 1.030 / 1.058 / 1.081 / 1.108 / 1.132 / 1.160 / 1.185 / 1.210 vs 운영 1.034 … 1.219; 설명 81–96 % | GTASK15 운영 비율 재현, d = 1–8, plan 평균 L만 입력 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | exploratory | stack | — |
| g18_prior_prediction | 5개 중 c·L3000·혼합 적중; F1 ±0.03 7/8 (d = 7 −0.042); L64 n = 8 −0.74 % 빗나감 | 사전 예측 대조 | origin/gpu-a6000:docs/research/gpu/GTASK18.md @ f0d8000 | blind_fail | untagged | — |

## GTASK19 — 정정 기록

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g19_n24_base_definition | `lo` 0.75318 (1,361/1,807) = 0.753; §5.5 bound 평균 0.75222 = 0.752; 판정 영향 없음 | GTASK11 N24 BASE sim LRU, 산출 파일 대조 | origin/gpu-a6000:docs/research/gpu/GTASK19.md @ a99f23c | retro_check | untagged | — |

## GTASK20 — 붕괴 영역 blind N = 25·28

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g20_validity | 30/30 유효, 재실행 0 | lifecycle (2 N × 3 구성 × 5) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | — |
| g20_s51_ctx | PASS; 6/6 ≤ 0.10; 평균 부호 +0.022 / +0.023; MAE 0.022 / 0.023 ≤ 0.5 × 0.233 | 재사용률, (1) ctx 주, 6 cell (lo / hi) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_s52_ctx | PASS; 기본 4/4, 강화 4/4; Σ 0.040 / 0.028 ≤ 0.5 × 0.392 / 0.406 | 비용 비, (1) ctx, 4 cell (lo / hi) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_s53_ranking | PASS N25·N28; BASE 포함 쌍 해소, POOL/POOL+GRID 1.002 · 1.000 미해소 | 구성 순위, (1) ctx | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | — |
| g20_s56_h | PASS; TVD 중앙 0.049 / 0.048, 최대 0.052 / 0.051; 균등 0.763 | h decode-only, (1) ctx, 6 cell | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | untagged | — |
| g20_ctx_vs_price | CONFIRMED; BASE 재사용 오차 0.075 / 0.084 vs 0.348 / 0.319; 비 Σ 0.040 / 0.028 vs 0.135 / 0.110 | 추가 확증 (1) ctx < (3) 가격 (lo / hi) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_price_fail | §5.1 FAIL (N25 BASE +0.22, MAE 0.108); §5.2 FAIL (기본 2/4) | (3) 가격 기준선 | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_fail | stack | — |
| g20_calibrated | §5.1·5.2·5.6 PASS; BASE 재사용 오차 0.031 / 0.012 (×1.210), 0.027 / 0.035 (mode_dist); 비 Σ 0.042 / 0.029, 0.024 / 0.035 | (2) 보정 예측 (GTASK11 관측으로 맞춤), 보고 | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_base_collapse | 관측 0.475 / 0.366 vs ctx 0.514 / 0.403, ×1.210 0.494 / 0.353, 가격 0.696 / 0.494 | BASE 재사용, N25 / N28 (lo) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_config_effect | m 0.8933–0.9145 (lo); ctx 예측 0.8969–0.9047 | BASE 대비 비, 4 cell | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_confirm | stack | — |
| g20_reuse_overpred | +0.005 – +0.049 (6/6 같은 방향) | (1) ctx 재사용 계통 편향 (G-08 결정: 추가 측정 없음) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | stack | — |
| g20_replicate_spread | N28 BASE 0.03–0.59; N25 BASE 0.23–0.63 | replicate별 재사용 (G-08 결정: 반복 없음) | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | stack | — |
| g20_prior_prediction | §5.2 사전 예측 빗나감 (FAIL 예측 → PASS); 나머지 적중 | 사전 예측 대조 | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | blind_fail | untagged | — |
| g20_direct_channel | 중앙 1.049 (0.930–1.144) | 직접 dispatch / 가격, 30 lifecycle | origin/gpu-a6000:docs/research/gpu/GTASK20.md @ 517cff8 | exploratory | untagged | — |

## G-10 — GTASK23–25 (2026-10-08)

상태 표기(G-10 지시): `[선등록 검증]` 측정 전 commit된 기준의 판정, `[사후 진단]` 측정·판정 뒤 계산(판정 아님), `[보고]` 판정 없는 측정값. 문서는 `docs/research/gpu/GTASK23.md`–`GTASK25.md`.

| id | value | population/unit | source | kind | layer | data |
|---|---|---|---|---|---|---|
| g23_exec_overhead | [선등록 검증] `OK`; 처리율·w* 간격 \|중앙 ON/OFF − 1\| ≤ 0.12 % (low/BASE −0.06·+0.07, low/KV 0.00·+0.02, sat/BASE −0.01·−0.02, sat/KV +0.12·−0.01 %) | 계측 영향, 2 부하 × 2 구성 × 5 pair (개발 점검) | origin/gpu-a6000:experiments/gpu/g10/exec_check_result/summary.json @ fc10373 | dev_set | stack | — |
| g23_exec_checks | [선등록 검증] 누락 0, 겹침 0, 비양수 0, DIRECT 합/device 범위 ≤ 0.99978, OFF `[GEXEC]` 0 | ON run 20개 window step | origin/gpu-a6000:experiments/gpu/g10/exec_check_result/summary.json @ fc10373 | code_check | stack | — |
| g23_direct_vs_dispatch | [보고] FULL decode DIRECT / dispatch 0.998–1.001 (low 14.2, sat 16.9 ms); 사전 예측 0.85–0.98 빗나감 | DIRECT 대 host dispatch 주기 | origin/gpu-a6000:experiments/gpu/g10/exec_check_result/summary.json @ fc10373 | exploratory | stack | — |
| g24_prereg_na | [선등록 검증] `NA` (판정 replicate 0); 80/80 lifecycle 겹침 > 0.01 ms; 유효 80/80, preemption 0, 누락 0 | B DIRECT 판정 1–4, N28·N25 | origin/gpu-a6000:experiments/gpu/g10/b_result/verdict.json @ 935d9d6 | withheld | untagged | — |
| g24_recon_pred | [보고] R_RECON lo/hi N28 0.8819/0.8779, N25 0.8590/0.8545; R_PRED lo/hi N28 0.8866/0.8795, N25 0.8698/0.8672 | 호출당 비용 비 KV/BASE, replicate 10 중앙 | origin/gpu-a6000:experiments/gpu/g10/b_result/verdict.json @ 935d9d6 | exploratory | stack | — |
| g24_f32_cause | [사후 진단] 첫 겹침 s ≥ 131,095 ms (2¹⁷), 최대 0.0146 ms ≤ float32 간격 0.0156; 보정 허용치로 80/80 겹침 0 | `[GEXEC]` s 양자화 | origin/gpu-a6000:experiments/gpu/g10/b_result/posthoc_f32.json @ 0b2fa48 | post_hoc | stack | — |
| g24_direct_ratio | [사후 진단] R_DIRECT N28 0.8957 (CI 0.856–0.929), N25 0.8751 (0.836–0.947), sign 10/0; RECON−DIRECT −0.014/−0.018, −0.016/−0.021; PRED−DIRECT −0.009/−0.016, −0.005/−0.008; skill PASS | 보정 규칙 아래 B 기준 1–4 | origin/gpu-a6000:experiments/gpu/g10/b_result/posthoc_f32.json @ 0b2fa48 | post_hoc | stack | — |
| g24_direct_abs | [보고] DIRECT/RECON lo 1.187–1.211 (N28 BASE 0.415 대 0.350 s/호출); decode 16.5 대 가격 13.62 ms | 절대 호출당 시간 | origin/gpu-a6000:experiments/gpu/g10/b_result/posthoc_f32.json @ 0b2fa48 | exploratory | stack | — |
| g24_reuse_report | [보고] 관측/예측 lo: N28 BASE 0.215/0.243, KV 0.608/0.628; N25 BASE 0.425/0.466, KV 0.788/0.799; h TVD 0.047–0.052 | 요청 재사용 (판정 아님) | origin/gpu-a6000:experiments/gpu/g10/b_result/verdict.json @ 935d9d6 | exploratory | stack | — |
| g24_replay | [사후 진단] 11,194/11,194 일치, KV 축출 1,202,315 일치 | 사건 재현, B 40 lifecycle | origin/gpu-a6000:experiments/gpu/g10/b_result/posthoc_replay.json @ fc10373 | retro_check | stack | — |
| g25_ctx_long | [보고] c_long 2.1078e-4 ms/token (GTASK18 2.120e-4), \|잔차\| ≤ 0.103 ms, L ≤ 7,000 | decode step, n {1,2,4,8} × 6 L | origin/gpu-a6000:experiments/gpu/g10/ctx_long_result/summary.json @ 228ce77 | exploratory | stack | — |
| g25_reuse_req | [선등록 검증] C1 lo PASS (최대 0.0493), hi FAIL (LONG/BASE 0.0521) | 요청 재사용, 4 cell | origin/gpu-a6000:experiments/gpu/g10/c_result/verdict.json @ 089c7f4 | blind_fail | stack | — |
| g25_reuse_tok | [선등록 검증] C2 lo FAIL (LONG/BASE 0.0542, LONG/KV 0.0502), hi PASS (0.0392) | token 재사용, 4 cell (G-10 추가 기준) | origin/gpu-a6000:experiments/gpu/g10/c_result/verdict.json @ 089c7f4 | blind_fail | stack | — |
| g25_reuse_skill | [선등록 검증] C3 PASS lo Σ 0.083 / hi 0.079 ≤ 0.5 × 0.750 | 재사용 skill (기준선 0.84718) | origin/gpu-a6000:experiments/gpu/g10/c_result/verdict.json @ 089c7f4 | blind_confirm | stack | — |
| g25_short_reuse | [선등록 검증] SHORT \|오차\| ≤ 0.003 (BASE 0.952, KV 0.973) | SHORT_TOOL 재사용 | origin/gpu-a6000:experiments/gpu/g10/c_result/verdict.json @ 089c7f4 | blind_confirm | stack | — |
| g25_cost_na | [선등록 검증] C4·C5 `NA` (DIRECT 판정 replicate 0, 40/40 겹침 결함) | 비용 비, 참조 DIRECT | origin/gpu-a6000:experiments/gpu/g10/c_result/verdict.json @ 089c7f4 | withheld | untagged | — |
| g25_cost_posthoc | [사후 진단] R_DIRECT SHORT 0.9927, LONG 0.8770; PRED lo/hi − DIRECT SHORT +0.001/+0.006, LONG −0.011/−0.015; C5 Σ 0.012/0.021 ≤ 0.5 × 0.130 | 보정 규칙 아래 C4·C5 | origin/gpu-a6000:experiments/gpu/g10/c_result/posthoc_f32.json @ fc10373 | post_hoc | stack | — |
| g25_replay | [사후 진단] 5,307/5,307 일치, KV 축출 429,653 일치 | 사건 재현, C 20 lifecycle | origin/gpu-a6000:experiments/gpu/g10/c_result/posthoc_replay.json @ fc10373 | retro_check | stack | — |
| g25_timing_input | [사후 진단] 관측 wall/sim wall LONG 1.125·1.115, SHORT 1.019·1.021; LONG mixed DIRECT 142.0/120.2 대 가격 108.5/87.7 ms, decode 19.4 ≈ ctx 모형 | 재사용 오차의 원인 분해 (prefill context 의존은 추정) | origin/gpu-a6000:experiments/gpu/g10/c_result/posthoc_timing.json @ fc10373 | post_hoc | stack | — |

## 집계

| kind | 행 |
|---|---|
| exploratory | 56 |
| blind_confirm | 34 |
| code_check | 20 |
| retro_check | 14 |
| blind_fail | 12 |
| dev_set | 6 |
| withheld | 3 |
| post_hoc | 4 |
| 합계 | 149 |
