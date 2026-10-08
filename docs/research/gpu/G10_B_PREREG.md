# G-10 작업 B — 포화 구간 비용 비의 독립 시간 검증 선등록

작성: 2026-10-08. GPU 지시문 G-10 §4. 기록 TASK는 [GTASK24](GTASK24.md)다. **이 문서, plan, 예측 파일, 순서표, driver, 판정 script를 측정 전에 commit한다.** 측정은 작업 A의 계측 영향 점검([G10_A_PREREG.md](G10_A_PREREG.md))이 끝난 뒤 시작한다. 작업 A가 `EXCEEDS`로 끝나면 이 측정의 DIRECT 판정은 `BLOCKED`이며 그때는 이 문서를 개정해 다시 commit한 뒤에만 측정한다.

**지위**: 알려진 포화 조건(N = 28, 25; GTASK20과 같은 N)의 **새 seed 독립 시간 검증**이다. 새로운 동시성에 대한 blind 검증이 아니다.

## 1. 구성과 plan

| 역할 | runner 이름 | 동시 실행 상한 | KV blocks | decode grid (token 수 사상) |
|---|---|---:|---:|---|
| GPU_BASE | `BASE` | 8 | 1,900 | (1, 2, 4, 8, 16) = GTASK08 `base_grid` |
| GPU_KV | `POOL` | 8 | 2,300 | 같음 |

- "default grid"의 실제 값은 `--compilation-config {"cudagraph_capture_sizes": [1,2,4,8,16]}`이며 vLLM v2 runner는 step의 **scheduled token 수**를 그 이상 가장 작은 capture size로 올린다(GTASK02·05). NPU의 request 수 bucket과 다르다.
- 원고(사용자 작성)는 저장소에 없다. 저장소 설정과의 대조는 이 표와 `selection/selection.json`(`base_pool` 1,900, `pool_pool` 2,300, `base_grid`, `max_num_seqs` 8, budget 2,048)으로 한다.
- 공통: Qwen3-4B bf16(`1cfa9a72…`), 1 GPU(`GPU-4485e769…`), runner `gpu_mt_runner.py`(token-id prompt, streaming, 8 turn, 16-token block, `--exec-timing`), 관측 patch + exec 층.
- plan: `experiments/gpu/g10/plans_b/g10b-n{N}-r{r}.json`, N = 28(필수)·25(확장), r = 0..9, seed `20264100 + 10·k + r`(k = 0: N28, 1: N25). 생성 규칙은 GTASK09/20과 같다(첫 prompt U(800, 1600), 이후 segment 8, 생성 U(32, 256), toolmix gap 상한 60 s, `cycle_s` = 해석 POOL 예측). seed 20264000–20264999는 두 branch의 모든 plan·순서·bootstrap seed와 겹치지 않는다(확인: `base_seed` 전수, `origin/main` 상수).
- 구조적 zero-preemption: plan별 `1 + 8·⌈최대 문맥/16⌉` 최대 1,657 ≤ 1,899(GPU_BASE 사용 가능). 관측 preemption 0을 확인한다.
- 같은 replicate의 두 구성은 같은 plan을 쓴다. 재도착은 각 구성의 실제 완료 시각 + 계획 tool wait로 생긴다(측정값을 예측에 넣지 않는다).

## 2. 동결 예측 (`plans_b/PREDICTIONS_B.json`, SHA256 `0d1abec1c980c902…`)

- 예측기: 현행 문맥 인지 통합 시뮬레이터 = `gpu_mt_sim` LRU + GTASK20 예측기 (1) `ctx`(`predict_blind.StepCost("ctx")`, GTASK18 c = 2.120 × 10⁻⁴ ms/token). 두 prefill-cost 설정 lo / hi를 모두 동결한다. 작업 C의 `c_long`은 소급 적용하지 않는다.
- PRED 비용(원고 정의) = 시뮬레이션 window step의 `gpu_cost` 가격(같은 bound) 합 / window 요청 수. `R_PRED,i` = replicate i의 GPU_KV / GPU_BASE, 판정값은 그 median. 시뮬레이션 step 시간 합으로 만든 비(`simwall`)는 보고만 한다.

| N | bound | R_PRED median (범위) | GPU_BASE 재사용 / token | GPU_KV 재사용 / token | 호출당 가격 BASE / KV (s) |
|---|---|---|---|---|---|
| 28 | lo | **0.8866** (0.834–0.957) | 0.243 / 0.215 | 0.628 / 0.592 | 0.3421 / 0.3027 |
| 28 | hi | **0.8795** (0.820–0.942) | 0.236 / 0.202 | 0.633 / 0.591 | 0.3494 / 0.3057 |
| 25 | lo | **0.8698** (0.795–0.985) | 0.466 / 0.422 | 0.799 / 0.773 | 0.3181 / 0.2817 |
| 25 | hi | **0.8672** (0.780–0.988) | 0.457 / 0.409 | 0.796 / 0.769 | 0.3228 / 0.2843 |

- simwall 비: N28 0.903 / 0.897, N25 0.889 / 0.887. 시뮬레이션 대기 평균(s): N28 BASE 4.26 / KV 3.48, N25 3.08 / 2.38(lo).
- 재사용 pooled 비율은 시뮬레이터 자체의 분자·분모 합이다(관측 요청 수로 가중하지 않음).

## 3. 측정

- 순서 `plans_b/ORDER_B.json`(seed 20264160, SHA256 `ff87ee697ccc3112…`): **N = 28 블록(필수) 20 lifecycle 뒤 N = 25 블록(확장) 20 lifecycle.** N마다 replicate 순서를 섞고, replicate 안 구성 순서는 5:5로 균형 배정.
- **확장 실시 결정(측정 전, 시간 예산)**: 마감 6시간 전 = 2026-10-10 05:59 UTC. 기존 lifecycle 3.2–4.0분(GTASK10·20) × 40 + 재실행·판정 30분 ≈ 3 h, 그 뒤 작업 C(20 lifecycle, 약 2 h)까지 마감 6시간 전보다 30시간 이상 먼저 끝난다. 따라서 **확장(N = 25)을 실시한다.** 필수 결과를 보고 바꾸지 않는다.
- driver `experiments/gpu/g10/run_b.sh <abs run dir>`: 측정 → 재실행 → `judge_b.py` 1회 → `b_result/verdict.json`만 local `gpu-a6000`에 commit(push 없음). 측정 중 HEAD를 바꾸지 않고 script를 고치지 않는다. 같은 GPU·공유 자원을 쓰는 다른 GPU 작업을 동시에 하지 않는다(두 번째 GPU 동시 사용 절차 없음).
- warm-up·120 s 평가창·세션 교체·lifecycle마다 서버 재기동은 GTASK11/20 절차 그대로.
- **INVALID**(실행 결함만): runner/측정 검사 실패(HTTP 오류, 생성 길이 불일치, 창 규칙 불일치, 외부 GPU process, 서버 id 없음 등). 순서를 다 돈 뒤 같은 plan으로 한 번 다시 잰다(`.retry1`). window의 `[GEXEC]` 누락·겹침(> 0.01 ms)·비양수 값은 **DIRECT만 INVALID**인 계측 결함이며 역시 한 번 다시 잰다. 재실행에서 DIRECT 완전한 유효 run이 있으면 그것을, 없으면 처음 유효 run을 쓴다.
- **preemption**: 관측되면 재실행하지 않고 그 lifecycle을 모형 범위 위반 결과로 보존한다. 그 N의 확증 판정은 `SCOPE_VIOLATION`으로 중단하고 원인을 보고한다.

## 4. 채널과 집계 (모든 채널에 같은 step·창·요청)

- 요청: runner 창 [w0, w0 + 120 s)에 보낸 요청(구성별로 같은 규칙, 요청 집합은 구성마다 다를 수 있다).
- step: 첫 창 요청의 `[GPFX] ALLOC` 줄부터 마지막 창 요청의 ALLOC 줄까지의 `[GSTEP]`(기존 A′-GPU 범위). 혼합 step은 한 번만 센다.
- RECON_b = Σ `gpu_cost.step_ms(d, p, b)` / 요청 수 (기존 `device_per_turn_s` 그대로, b = lo/hi).
- DIRECT_EXEC = Σ (prep + run) / 요청 수([G10_A_PREREG.md](G10_A_PREREG.md) §2). prep·run 성분 비도 보고.
- PRED_b: §2.
- `R_ch,i = 비용(GPU_KV, i) / 비용(GPU_BASE, i)`; median을 취한다. 두 구성 비용의 median을 먼저 나누지 않는다.
- **판정 replicate 집합** = 두 구성 모두 유효·preemption 0·DIRECT 완전. PRED·RECON median도 이 집합에서 계산한다(10개 전부의 PRED median과 유효 replicate 전부의 RECON median은 따로 보고).
- 요청 지연 합이나 전체 wall-clock을 장치 비용으로 쓰지 않는다.

## 5. 판정 기준 (수치 정확도 판정; 통계적 동등성 검정이 아니다)

| 항목 | 기준 |
|---|---|
| 1 재구성 일치 | 각 N, 각 b: \|median(R_RECON_b) − median(R_DIRECT)\| ≤ 0.03 |
| 2 예측 일치 | 각 N, 각 b: \|median(R_PRED_b) − median(R_DIRECT)\| ≤ 0.03. **lo·hi 둘 다 만족해야 통과** |
| 3 예측 skill | b마다 Σ_N \|R_PRED_b − R_DIRECT\| ≤ 0.5 × Σ_N \|1 − R_DIRECT\|(항상 1.0을 예측하는 기준선). 기준선 합 ≤ 1e-12이면 `NA`(자동 통과 아님) |
| 4 감소 확인 | N마다 R_DIRECT median의 nominal 95 % percentile bootstrap 구간(replicate 단위 재표집 10,000회, `random.Random(20264150)`): 상한 < 1 → `CONFIRMED`, 1 포함 → `INCONCLUSIVE`, 하한 > 1 → `INCREASE`. 정확한 양측 sign test와 방향 일치 수 병기 |

- 판정 범위: `required` = N28만, `all_B` = N28 + N25(확장). 둘 다 보고한다.
- 반복별 차이(PRED − DIRECT, RECON − DIRECT)와 구간을 함께 낸다. 5/5 또는 10/10 방향 일치를 "5 % 유의"라고 부르지 않는다. 개별 요청을 재표집하지 않는다.
- 보고(판정 없음): 각 구성의 절대 호출당 시간(RECON lo/hi, DIRECT, DIRECT prep/run, PRED lo/hi), 직접 계측과 원고 비용의 범위 차이 표시, step 종류(순수 decode / 순수 prefill / mixed)별 개수·DIRECT·RECON, 재사용률·token 재사용률·decode-only h(TVD)·대기(관측 proxy: 첫 ALLOC wall − client 송신 wall, HTTP 지연 포함) 대 예측, 누락률.
- **보조 분석(Appendix G 규칙, 판정 없음)**: 시작·끝 잔여 작업 보정(GTASK22 `boundary_sensitivity` 규칙: step 값을 decode 몫 `decode_ms(d)`와 prefill 몫으로 나누고, 창 밖 요청 몫 S를 빼고 창 요청의 범위 밖 몫 E를 더함)을 RECON lo/hi, DIRECT(같은 비율로 분배), PRED lo/hi(시뮬레이터 step member 기록, 동작 불변 확인)에 같은 규칙으로 적용. 보정 전후 비를 모두 남긴다.
- 오차가 생기면 관측 사건 재현으로 규칙 불일치와 사건 생성/시간 입력 문제를 구분하는 **사후 진단**을 별도로 한다. 실패한 예측 파일은 바꾸지 않는다.

## 6. 사전 예측 (기록용, 판정 아님)

- 2 예측 일치: **FAIL 쪽**. 원고 비용(가격)은 context 항이 없는데 DIRECT는 실제 실행이라 문맥 비용을 포함한다. GPU_KV는 재사용이 많아 prefill이 적지만 decode 문맥은 비슷하므로, DIRECT 비가 가격 비보다 1에 가깝게(약 0.90–0.92) 나올 것이다. 차이는 0.02–0.04로 문턱 근처.
- 1 재구성 일치: 같은 이유로 문턱 근처(0.01–0.04 차).
- 3 skill: PASS(비용 효과 약 0.1 대비 오차가 작음).
- 4 감소: N28·N25 모두 `CONFIRMED`(GTASK20 RECON 비 CI가 1 미만이었다).
- DIRECT/RECON 절대값: 포화 decode에서 DIRECT ≈ dispatch 주기(smoke run: 폭 8 FULL 16.94 대 16.96 ms), RECON(가격 13.6 ms)보다 15–25 % 큼.
