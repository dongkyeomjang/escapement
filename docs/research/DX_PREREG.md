# DX_PREREG — 독립 시간 계측·대기시간 상한·동일 자원 구성 선택 선등록 (Advisor 지시문 2026-10-08)

이 문서는 [TASK116](TASK116.md)의 측정 전 선등록이다. **이 문서를 담은 commit이 모든 측정(작업 A 개발 점검 포함)보다 앞선다.** 측정 시작 시각은 각 run 디렉터리의 `measurement-start.txt`와 `git-head.txt`로 확인한다. 이전 선등록 판정([CTXBLIND_PREREG.md](CTXBLIND_PREREG.md) 등)은 그대로 두며, 이 문서의 판정은 `results/npu/stage3/20261008-dx-*/` 아래 별도 파일에 둔다.

입력 근거의 실제 경로·hash·commit은 [dx/INPUT_MANIFEST.json](dx/INPUT_MANIFEST.json)에 있다(`experiments/npu/stage3/dx_manifest.py`로 생성). GPU 자료는 이번 작업에서 읽지 않았다. remote ref는 마지막 fetch 기준(`origin/main` `40d2c75`, `origin/gpu-a6000` `954dd03`, 2026-10-06)이며 다시 fetch하지 않았다.

## 1. 구성 역할과 artifact

| 역할 | artifact (`models/`) | batch / KV blocks | buckets(실물 `rbln_config.json`) | 지시문 표와 |
|---|---|---|---|---|
| BASE | `Qwen3-4B-rbln-b8-s8192-d4-mb` | 8 / 8 | 1,2,4,8 | 일치 |
| BATCHONLY | `Qwen3-4B-rbln-b16-s8192-d4-batchonly` | 16 / 16 | 1,2,4,8,16 | 일치 |
| TUNED | `Qwen3-4B-rbln-b16-s8192-d4-mb16` | 16 / 16 | 1,4,6,8,10,16 | 일치 |
| DP_N8 | `Qwen3-4B-rbln-b16-s8192-d4-dp8` | 16 / 16 | 1,2,3,4,6,16 | 일치 |

model·정밀도·`d4`(rbln0–3 한 card)·server 인자(`--enable-prefix-caching --enable-prompt-tokens-details`, `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1`)·runner·streaming은 기존과 같다(`run_dx_lifecycle.sh`는 `run_multiturn.sh`에 관측 스위치만 더한 사본). 새 compile 없음.

## 2. 채널과 계측 범위 (작업 A §3.1)

| 채널 | 사건·활동량 | 시간 값 |
|---|---|---|
| PRED | 동결한 통합 시뮬레이터(`dx_predict.py`) | 기존 동결 비용 함수(TASK13 decode, TASK22 prefill) |
| RECON | 실측 로그(`[BUCKET]` step, 평가 요청의 계산 token) | 같은 기존 동결 비용 함수 = `mt_measure.lifecycle_metrics` A′ |
| DIRECT_EXEC | RECON과 같은 step·요청 모집단 | step별 실측 경과시간(아래) |
| HW_ACTIVE | **측정하지 않는다** | `rebel.capture_reports()` device 시간은 `RBLN_RUNTIME_TIMER=1`일 때만 생기며 기존 run에 없었다. 켜면 runtime 경로가 바뀌므로 이번 범위에서 제외 |

### 2.1 현행 재구성 비용(RECON)에 들어 있는 것 (코드 확인)

- decode step = `f(bucket)` + `0.0413 ms × actual` + `0.501 ms`. `f(bucket)` = TASK13의 **device model span p50 + sampler p50**, 나머지 두 항 = 종단 ITL − 두 span의 회귀(engine overhead, step 사이 scheduler·IPC 포함) — `experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py` `STEP_COST`, `step_cost_measurement`.
- prefill = TASK22 적합 `21.206 ms × ceil(token/128)`형 + drift(`PREFILL_COST`), 배타 실행.
- 따라서 RECON은 model 실행·sampler·runtime/host overhead를 모두 포함한 **종단 step 시간**의 모형이다.

### 2.2 DIRECT_EXEC 계측 (patch `steptime`, [STEPTIME.md](../../patches/vllm_rbln-0.11.1/STEPTIME.md))

- **위치**: `vllm_rbln/v1/worker/optimum_model_runner.py` — `execute_model` 진입(`t_exec`), 기존 `model_start_time`(`t_model0`), model forward 반환(`t_model1`), 기존 `sampler_start_time`(`t_samp0`), sampler 반환(`t_samp1`), `sample_tokens` 반환 직전(`t_end`). 한 step당 `[STEPTIME]` 1줄.
- **clock·단위**: EngineCore process 하나의 host `time.perf_counter()`, 초(소수 6자리 = 1 µs).
- **완료 의미**: `rebel` runtime은 `PyRblnSyncRuntime.run()`(동기, `rebel/sync_runtime.py`) — 반환 시 출력이 host에 있다. 새 동기화를 넣지 않았고, 기존 실행 순서와 같다.
- **장치 범위**: 4 devices(rbln0–3)에 걸친 단일 instance의 step 경과시간 하나. 장치별 시간을 더하지 않는다.
- **step 연결**: decode는 같은 step의 forward 안에서 먼저 찍히는 `[BUCKET]` 줄과 순서로 1:1 짝(`dx_steps.py`). prefill은 `n_reqs=1`이고 `req_ids`가 server 요청 id(= `[PFX] [ALLOC]` id)다. `cached`는 prefill의 재사용 token(`cached_length`), `n_tokens`는 계산 token.
- **DIRECT_EXEC 값**: step마다 `t_end − t_exec`(입력 구성·prefix KV 복사·forward·logits·sampler·bookkeeping). **step 사이의 scheduler·IPC·출력 처리(`t_exec[k+1] − t_end[k]`)는 포함하지 않는다** — RECON의 `0.501 ms` 절편에 해당하는 부분이며, 같은 구간의 합과 중앙값을 따로 보고한다. 구성요소 model / sampler / pre / post를 함께 보고한다. 따라서 RECON과 DIRECT_EXEC의 **절대값**은 범위가 달라 직접 비교하지 않고(차이는 범위 차로 기록), 판정은 **구성 간 비용 비**로 한다.
- **모집단**: RECON과 같다 — 평가 구간 [w0, w1)에 보낸 요청, 그 첫·마지막 ALLOC 사이의 모든 `[BUCKET]` step(공유 step은 한 번), 그 요청들의 prefill step. 도구 대기·유휴 구간은 step이 없으므로 들어가지 않는다.
- **귀속 완전성**: 집계 범위의 모든 `[BUCKET]` step이 같은 요청 수의 `[STEPTIME]`과 짝지어지고, 모든 평가 요청에 prefill step이 있으며, 해석 불가 줄이 0이어야 한다. 아니면 lifecycle `INVALID`(§3.5). 누락을 비용 모형이나 chunk 간격으로 메우지 않는다.
- **smoke 확인(개발, 판정 아님)**: `results/npu/stage3/20261008-dx-smoke` TUNED N6 30 s — 귀속 누락 0, decode 1,905 step 전부 짝, step 사이 간격 중앙 0.49 ms.

## 3. 공통 절차

### 3.1 plan

`make_dx_plans.py`(규칙 = `make_ctxblind_plans.py`: `make_plan.build`, 원고 workload, cycle = plan의 v1 해석 TUNED 예측). 새 seed `20268000 + 10·N + r`(B·C·E), `20268900 + 10·N + r`(작업 A 개발용). `git grep`으로 20268xxx 중 기존 사용은 GPU survival `20268001` 하나이며 이 규칙은 그 값을 만들지 않는다. 모든 plan의 SHA256은 `plans/dx/INDEX_DX.json`.

- B: N = 18 r0–9(seed 20268180–89), N = 8 r0–9(20268080–89).
- C: N = 14 r0–4(20268140–44). 상한별 두 파일(`dx-c-n14-cap60-rK`, `-cap120-rK`)이 **같은 내부 `plan_id`**(`dx-c-n14-rK`, session seed의 원천)와 같은 cycle(60 s plan의 규칙값)을 쓴다. `ToolMix.draw`는 draw 후 자르므로 두 상한의 prompt·출력·호출 수·세션 교체가 같고 대기만 `min(g_raw, cap)`으로 다르다. `gap_stats()`가 plan 파일이 `min(g_raw, cap)`과 정확히 같음을 확인했다(`plan_files_match` true/true).
- E: N = 19 r0–9(20268190–99). **N = 19는 NPU에서 측정·예측된 적이 없다**(plans/main에 n19 없음, SIMBLIND는 20261590–94를 N = 19 규칙값이라 피했을 뿐 사용하지 않음).
- 개발(A): N = 6 r0–4(20268960–64), N = 18 r0–4(20269080–84) — B와 seed가 다르다.

### 3.2 실행 순서 (`make_dx_order.py`, 고정 seed)

| 순서표 | 내용 | lifecycle | seed |
|---|---|---:|---|
| `ORDER_DXA` | A: (BASE·TUNED) × (N6·N18) × 쌍 5, 쌍 = 같은 plan의 OBS on/off, 평가창 60 s | 40 | 20268002 |
| `ORDER_DXB` | B 필수: N18 BASE·TUNED × r0–9, OBS on, 120 s | 20 | 20268003 |
| `ORDER_DXC` | C: N14 (BASE·TUNED) × (60·120) × r0–4, OBS on | 20 | 20268004 |
| `ORDER_DXB8` | B 확장: N8, B와 같은 방식 | 20 | 20268005 |
| `ORDER_DXE` | E: N19 (BATCHONLY·TUNED·DP_N8) × r0–9, OBS on | 30 | 20268006 |

replicate 안 구성 순서는 seed로 섞되 B는 BASE 먼저 5회·TUNED 먼저 5회, C는 replicate마다 다른 순열, E는 6개 순열을 모두 한 번 이상 쓴다. A는 각 조건에서 on 먼저 2–3회. 실행 순서: **A → (A 판정) → B → C → B 확장 → E.** lifecycle마다 server 재기동(`run_dx.sh`), 동시 실행 없음. 측정 중 다른 무거운 작업을 하지 않는다(작업 D는 `taskset -c 64-95 nice -n 19` 단일 process로 분리).

### 3.3 확장 시작 규칙 (시간만으로 결정)

B 확장(`ORDER_DXB8`)과 E(`ORDER_DXE`)는 각각 시작 직전에 `시작 시각 + lifecycle 수 × 4.5 분 + 2 h(검증·집계) ≤ 2026-10-10 14:59 KST`(마감 6 시간 전)일 때만 시작한다. 필수 실험의 결과는 이 결정에 쓰지 않는다. 시작한 순서표의 반복 수는 바꾸지 않으며 시간 부족으로 끝나지 못하면 미완료로 보고한다.

### 3.4 정상상태·평가창

기존 그대로: `WindowRule`(warm-up 3 cycle·세션당 2 turn 이상), 평가창 120 s(A만 60 s), 세션 교체 16 session/slot, runner `--stream`.

### 3.5 유효성 (`dx_check.py`)

VALID ⇔ runner exit 0, window로 종료, 고갈 slot 없음, online window = offline 재계산, 평가 종료 뒤 발송 0, HTTP 오류 0, plan 파일·내용 SHA256 = `INDEX_DX.json`, 모든 평가 요청이 server id와 `prompt_tokens`로 연결, lifecycle 기록에 steptime patch `patched`, OBS on이면 §2.2 귀속 완전성. `INVALID`는 이런 실행 결함에 한정한다(큰 예측 오차·긴 대기열·예상과 다른 절감은 유효한 결과). `INVALID`는 원본을 보존하고 같은 plan으로 1회 재실행(`<tag>.retry1`); 두 번째도 `INVALID`면 그 replicate를 빼고 보고한다.

### 3.6 통계

replicate 단위만 쓴다(요청을 표본으로 bootstrap하지 않음). 비용 비 = 같은 replicate의 `구성 / 기준` 호출당 비용, 표의 비 = 그 paired ratio의 **median**(`median(TUNED)/median(BASE)`가 아님). 구간 = paired ratio median의 nominal 95 % percentile bootstrap, 10,000회, seed 20268007. 정확 sign test(양측)와 방향 일치 횟수를 함께 낸다. 5회 반복의 구간은 극값과 같을 수 있고 5/5 일치를 5 % 유의성으로 부르지 않는다. 판정 PASS/FAIL은 동결 기준의 수치 정확도이며 통계적 동등성 검정이 아니다.

## 4. 작업 A — 계측 영향 점검 (개발용, 검증 결과 아님)

- 신호(on·off 양쪽에 있는 것만): 처리율 = 평가창 안 완료 수 / 창 길이(client), **공통 범위 실행시간** = run 끝 `VLLM_RBLN_METRICS` MODEL tracker DECODE 평균 지연(호출별 forward `perf_counter` 구간, 기존 run 전부에 있음), 보조로 MODEL PREFILL·SAMPLER DECODE 평균, client ITL 중앙(streaming chunk), 요청 지연 중앙, RECON A′, 창 안 decode step 수·h 분포·재사용(구조 변화 확인). `[STEPTIME]`처럼 on에만 있는 신호로 on/off를 비교하지 않는다.
- 판정: 조건별 5쌍의 `on/off − 1` paired median이 **처리율 또는 공통 범위 실행시간(MODEL DECODE 평균)에서 |·| > 0.01**이면 `PERTURBATION`, 아니면 `WITHIN_1PCT`. 쌍별 값·최소·최대·표준편차를 함께 보고하며, 1 % 이하라는 점 추정만으로 영향이 없다고 단정하지 않는다.
- `PERTURBATION`이면: 계측을 경량화(예: `req_ids`를 prefill step에만 기록)한 patch를 다시 승인받아 같은 순서표로 점검을 반복한다. 해소되지 않으면 B의 직접 판정은 `BLOCKED: instrumentation perturbation`으로 두고 C(RECON)·D를 계속한다. 대리 지표를 DIRECT_EXEC로 승격하지 않는다.
- 독립 대조: 계측 코드(patch)와 집계 코드(`dx_steps.py`)를 공유 step 중복(짝은 bucket 1개당 step 1개, 같은 step 두 번 세지 않음), prefill/decode 귀속(`prefill` 필드), 시간 단위(초), 경계 요청(평가 요청의 ALLOC 범위)으로 대조한다 — smoke에서 `decode_size_mismatch` 0, `unpaired` 0, `orphan_bucket` 0.

## 5. 작업 B — 최대 절감 조건의 독립 시간 검증

**지위: 이미 알려진 조건(TASK102 N18 TUNED 0.671)에 대한 새 seed의 독립 시간 검증.** 미사용 동시성에 대한 blind 검증이 아니다.

- 행렬: 필수 N18 BASE·TUNED × 10 paired replicate(20 lifecycle), 확장 N8 같은 방식(§3.3).
- 집계: 같은 run의 PRED·RECON·DIRECT_EXEC에 같은 요청 선택·시간 경계를 쓴다. 주 분석 = 기존 평가창 정의. 보조 = TASK111 경계 보정(시작 잔여 S 제거·끝 잔여 E 추가, 소속 = ALLOC–FREE 사이 `[BUCKET]` step, step 비용을 `request_nums`로 균등 분배)을 RECON과 DIRECT_EXEC에 **같은 규칙으로** 적용하고 전후를 모두 남긴다. PRED에는 경계 보정을 하지 않는다(시뮬레이터 창은 시작 시각 기준 — TASK111 §3.5).
- `R_ch,i = TUNED_i / BASE_i`.
- 판정(0.03은 비용 비의 **절대 차이**):
  1. 재구성 일치: 각 N에서 `|median(R_RECON) − median(R_DIRECT_EXEC)| ≤ 0.03`.
  2. 사전 예측 일치: 각 N에서 `|median(R_PRED) − median(R_DIRECT_EXEC)| ≤ 0.03`.
  3. 예측 skill: B에 포함된 비용 비들의 `Σ|median R_PRED − median R_DIRECT|` ≤ 0.5 × `Σ|1 − median R_DIRECT|`. 기준선 합 ≤ 1e-12면 NA(자동 통과 아님).
  4. 절감 확인: `R_DIRECT_EXEC` paired median의 bootstrap 구간 상한 < 1이면 `개선 확인`, 1을 포함하면 `INCONCLUSIVE`. sign test와 방향 일치 횟수 함께.
- 함께 보고: 차이 `R_RECON − R_DIRECT`, `R_PRED − R_DIRECT`의 replicate별 값과 median 구간, 구성별 절대 호출당 시간(PRED·RECON·DIRECT, 범위 차이 명시; 이것으로 모형을 다시 맞추지 않음), phase·bucket·actual_n별 decode 시간, 누락률, step 사이 host 시간. 절감 크기의 목표나 33 %에 맞추는 기준은 없다.
- **사전 예측(PRED, `PREDICTIONS_DX.json`)**:

| N | PRED 재사용 BASE / TUNED | PRED `R` replicate별 (r0–9) | median |
|---|---|---|---:|
| 18 | 0.023 / 0.733 | 0.685 0.732 0.674 0.679 0.662 0.683 0.664 0.688 0.675 0.676 | **0.6774** |
| 8 | 0.797 / 0.888 | 0.984 0.995 0.968 0.958 0.958 1.004 1.011 0.991 0.941 0.984 | **0.9838** |

- 작업자 사전 기대(판정에 쓰지 않음): N18에서 1·2 PASS 쪽, 4 `개선 확인` 쪽. DIRECT_EXEC는 step 사이 시간을 빼므로 절대값은 RECON보다 작거나 비슷하고, smoke(TUNED N6)에서는 오히려 4 % 컸다 — 비에는 상쇄될 것으로 본다. N8은 절감이 작아(약 2 %) 4가 `INCONCLUSIVE`일 수 있다.

## 6. 작업 C — 대기시간 상한 60 s 대 120 s

**지위: 기존 동시성(N = 14, TASK87에서 측정)에서 새 대기시간 조건을 검사하는 선등록 검증.**

- 설계 §3.1. 대기 분포(`GAPSTATS_DXC.json`, C plan 5개 전체 7,594 대기):

| | 평균 | p50 | p90 | p99 | 최대 | 합 | 잘린 대기 비율 | 잘린 합 / 원래 합 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| g_raw | 6.95 | 0.165 | 11.43 | 173.99 | 662.2 | 52,787 | — | — |
| cap 60 | 4.32 | 0.165 | 11.43 | 60 | 60 | 32,839 | 2.63 % | **37.8 %** |
| cap 120 | 5.49 | 0.165 | 11.43 | 120 | 120 | 41,667 | 1.42 % | 21.1 % |

  잘리는 대기 수는 적지만 대기시간 합의 38 %·21 %가 잘린다. 생성기는 측정 분위수 p99까지 정의돼 있어(상위 1 %는 p99 값) 60 s 이후 꼬리를 새로 만들지 않았다 — C는 `BLOCKED`가 아니다.
- 예측: 현행 문맥 인지 통합 시뮬레이터(§9), 측정 결과로 보정하지 않음.

| cell | PRED 재사용 (pooled) | PRED `R`(TUNED/BASE) replicate별 | median | PRED 평균 대기 s | PRED 완료/s |
|---|---|---|---:|---:|---:|
| cap 60 BASE | 0.3005 (281/935) | — | — | 0.61 | 1.775 |
| cap 60 TUNED | 0.8095 (935/1155) | 0.781 0.840 0.787 0.742 0.810 | **0.7869** | 0.02 | 2.203 |
| cap 120 BASE | 0.4067 (377/927) | — | — | 0.37 | 1.757 |
| cap 120 TUNED | 0.8283 (902/1089) | 0.801 0.893 0.873 0.790 0.828 | **0.8275** | 0.02 | 2.072 |

- 재사용률 = 재도착 요청(turn > 0) 중 `cached_tokens > 0`인 요청의 pooled 비율(관측은 `mt_measure` 그대로, 예측은 시뮬레이터 자신의 분자·분모 합).
- 판정:
  1. **주 재사용**: 4 cell 각각 `|예측 − 관측| ≤ 0.05`(모두 만족하면 PASS).
  2. **skill**: `Σ|오차|` ≤ 0.5 × `Σ|0.6764 − 관측|`. 0.6764 = 최신 독립 검증(TASK101) 사전 기준선 `NULL_PREDICTORS_CTX.json` `reuse_null`(675/998) 그대로.
  3. **주 비용**: 각 상한에서 `|median PRED R − median RECON R| ≤ 0.03` — **"공통 비용 모형 아래 검증"**. A가 `WITHIN_1PCT`이고 귀속이 완전하면 DIRECT_EXEC 기준 오차를 별도 열로 보고(판정 아님).
  - cell별 오차·MAE·최대오차, BASE·TUNED 오차를 따로 보고한다.
  - 진단(판정 없음): h 분포 TVD, 평균 running, 처리율·시간당 완료 호출 수, TTFT, 경계 잔여, 예측 대기. 상한 민감도 = 같은 replicate의 cap120/cap60 RECON 비와 재사용 차(관측·예측).
- 정확도와 민감도를 분리한다. 실패하면 보존하며 상한·N을 바꿔 다시 재지 않는다.
- 작업자 사전 기대(판정 외): 예측이 cap 120에서 BASE 재사용 +0.11, TUNED 비 +0.04를 말하므로 민감도가 작지 않을 것. 주 재사용 BASE cell은 대기열 영역이라 0.05 안이 어렵다고 본다(TASK95·102 BASE 오차 0.02–0.03).

## 7. 작업 D — 기존 검증 데이터의 단순 근사 비교

장치 측정 없음, **사후 기전 분석(`post_hoc`)**. 개발에서 이미 비교한 구현·계수만 쓰고 새 근사를 설계하지 않는다. 결과는 `docs/research/dx/D_SIMPLE_APPROX.md`. 선등록 blind 결과로 쓰지 않는다.

## 8. 작업 E — 동일 자원 그리드 선택

**지위: 미사용 조건(N = 19)·새 seed의 사전 선택 검증.** 세 후보 모두 batch·KV 16.

- 예측(`PREDICTIONS_DX.json`), 목적 = BATCHONLY 대비 호출당 비용 비의 paired median 최소:

| 후보 | PRED 재사용 | PRED `R` replicate별 | median |
|---|---|---|---:|
| BATCHONLY | 0.669 | 1 × 10 | 1.0000 |
| TUNED | 0.683 | 0.968 0.979 0.958 0.942 0.977 0.994 0.952 0.971 0.995 0.943 | **0.9696** |
| DP_N8 | 0.664 | 1.041 0.980 1.019 0.999 1.049 1.022 1.023 1.028 1.025 1.014 | 1.0225 |

- **선택: TUNED**(`SELECTION_DXE.json`), 10개 plan 전체에 하나. tie 규칙(|R − min R| ≤ 1e-6이면 동률, 우선순위 BATCHONLY > TUNED > DP_N8)은 적용되지 않았다. 예측 폭 5.5 % > 1 %라 예측 단계의 낮은 판별력 표시는 없다.
- DP_N8은 context 비용을 잰 적이 없다. 규칙(측정 전 고정, TASK98 BATCHONLY 규칙과 같은 방식): f(1,4,6,16) = TUNED, f(2) = BATCHONLY, f(3) = f(2)·f(4) 선형, β·c = 세 적합 평균. **DP_N8 예측은 규칙 추정을 포함한다.**
- 관측 주 채널: **A가 `WITHIN_1PCT`이고 E lifecycle의 귀속이 완전하면 DIRECT_EXEC, 아니면 RECON**(측정 전에 이 조건으로 고정). 다른 채널은 보조.
- `R_c = median_i(cost_c,i / cost_BATCHONLY,i)`; 손실 = `R_TUNED / min_c R_c − 1`(관측 최저 후보 대비, 참 최적의 증명 아님). bootstrap은 세 후보의 같은 replicate 행을 함께 재표집하고 선택은 고정.
- 판정: 손실 ≤ 0.01이면 PASS. 세 후보의 관측 `R`이 모두 1 % 이내면 `낮은 판별력` 표시. 기본 그리드 대비 이점은 `TUNED/BATCHONLY` paired 구간 상한 < 1일 때만 `이점 확인`, 아니면 `동률 또는 INCONCLUSIVE`.

## 9. 예측기 (PRED)

결정 13의 통합 시뮬레이터: decode 시간을 예측 대상 context 길이의 decode 비용(F1 `f(b) + βn` + descriptor `context_cost` c/token, TASK97·100 `CTXCOST_BLIND.json`)으로 진행, 운영 prefill 비용은 채택하지 않음(원래 prefill), descriptor 의미론. 창 = 시뮬레이터 lifecycle의 `WindowRule`, 120 s, 시작 시각 기준; 가격 = 원래 비용 모형. **재현 점검**: 같은 코드로 TASK101 plan을 다시 돌려 `PREDICTIONS_CTX.json`의 `sim_ctx` 6 cell 재사용률·호출당 비용이 차이 0으로 일치했다. 측정한 대기열·처리시간·재사용으로 보정하지 않으며, 새 계측값으로 비용 모형을 보정하지 않는다.

## 10. 산출물

- `plans/dx/`: `INDEX_DX.json`, plan 50개, `ORDER_DX*.json` 5개, `PREDICTIONS_DX.json`, `GAPSTATS_DXC.json`, `SELECTION_DXE.json`.
- 코드: `make_dx_plans.py`, `make_dx_order.py`, `dx_predict.py`, `dx_steps.py`, `dx_check.py`, `dx_analyze.py`, `run_dx.sh`, `run_dx_lifecycle.sh`, `dx_manifest.py`; patch `steptime_observe.patch`·`apply_steptime.sh`·`STEPTIME.md`.
- run: `results/npu/stage3/20261008-dx-{a,b,c,b8,e}/`(비추적), 판정 `dx_verdict_{a,b,c,e}.json`.

## 11. 개정 1 (2026-10-08, 작업 A 판정 뒤·C 측정 전)

- 작업 A 판정(`results/npu/stage3/20261008-dx-a/dx_verdict_a.json`, 40/40 유효): **`PERTURBATION`** — TUNED N6 처리율 paired median −0.0152, TUNED N18 MODEL DECODE 평균 −0.0133(|·| > 0.01). 다른 두 조건은 1 % 이내. 부호는 계측 on 쪽이 더 빠른 방향이 4조건 중 다수이고 쌍별 표준편차 0.006–0.03이다(해석은 TASK117). 기준은 바꾸지 않는다.
- §4에 따라: (i) 계측을 경량화한 patch v2(step마다 로그 쓰기 대신 메모리 buffer, 1 s마다 1줄로 flush, decode는 요청 id 생략)를 사용자 승인 후 적용해 **같은 `ORDER_DXA` 설계로 점검을 반복**한다(새 run 디렉터리). (ii) 해소되기 전까지 B의 직접 판정은 보류하고, **C를 먼저** 잰다.
- **C는 계측 끔(OBS=0)으로 잰다**(`ORDER_DXC_OBSOFF.json` — 순서·plan·판정 기준은 `ORDER_DXC.json`과 같고 `obs`만 0). §6 판정 3이 DIRECT_EXEC 열을 A `WITHIN_1PCT`일 때만 보고하므로, 계측을 켤 이유가 없고 끄면 C의 RECON 판정에서 계측 영향 의심이 사라진다. 이전 모든 run과 같은 상태(steptime patch 적용, flag 꺼짐)다.
- `run_dx_chain.sh`의 C 순서표를 `ORDER_DXC_OBSOFF.json`으로 바꾼다. B·B 확장·E는 반복 점검 결과에 따라 개정 2로 정한다.
