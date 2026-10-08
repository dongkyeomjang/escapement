# GTASK25 — 긴 도구 출력의 재사용·비용 예측 (G-10 작업 C)

## 상태

PARTIAL — 선등록 판정:
- 재사용 C1·C2: 기준 4개 중 2개 FAIL(LONG_TOOL에서 0.0502–0.0542로 문턱 0.05를 근소하게 넘음)
- skill C3: PASS
- 비용 C4·C5: `NA`([GTASK24](GTASK24.md)와 같은 DIRECT 겹침 검사 결함)

보정 규칙 아래 사후 진단에서 C4·C5는 PASS였다.

## 날짜

2026-10-08

## 목적

GPU 지시문 G-10 §5. 같은 논리 plan에서 도구 출력 길이만 다르게 한다(SHORT_TOOL 8 token / LONG_TOOL 512 token). 긴 문맥에서도 문맥 인지 시뮬레이터가 재사용(요청·token)과 KV pool 확대의 비용 비를 예측하는지 확인한다.

## 배경

- [GTASK20](GTASK20.md)·[GTASK24](GTASK24.md)의 plan은 이후 segment가 8 token이라 문맥이 짧다(평균 약 1,800). 에이전트 도구 출력은 길다.
- [GTASK18](GTASK18.md)의 context 비용 계수는 L ≤ 3,000에서 쟀다. LONG_TOOL 문맥은 그 범위를 넘으므로 지시문 §5.3대로 microbenchmark를 먼저 했다(함수 형태 고정, 계수만 갱신).
- 선등록 [G10_CTX_LONG_PREREG.md](G10_CTX_LONG_PREREG.md)(microbenchmark), [G10_C_PREREG.md](G10_C_PREREG.md)(본 측정)

## 시작 상태

- HEAD `954dd03`(GTASK22), branch `gpu-a6000`. microbenchmark는 exec 층 적용 전, 관측 patch만 있는 상태에서 했다.

## 수행 내용

1. **사전 단계 microbenchmark**: 선등록 `545f8f7` → 측정 08:10:49–08:20:59 UTC, 2/2 유효 → 결과 commit `228ce77`. 격자는 n {1,2,4,8} × L {64, 1500, 3000, 4500, 6000, 7000}, pool 4,400, seed 20264800+.
2. 용량 계산(W = 7,232 → GPU_LONG_BASE 3,617, GPU_LONG_KV 4,379)과 후보 N 24·28·32·36 예측을 했다. 선택 규칙으로 N = 24를 골랐다. plan, 동결 예측, 순서, driver, 판정 script를 측정 전에 commit했다(`c2f37d3`).
3. B가 끝난 뒤 `run_chain.sh`가 C를 시작했다(18:44:01 UTC). 20 lifecycle 모두 유효였고 preemption은 0이었다. DIRECT 겹침 검사 때문에 20개 모두 재측정했다(재측정도 모두 같은 결함).
4. `judge_c.py` 1회(21:05:00). driver가 `c_result/verdict.json`을 자동 commit했다(`089c7f4`).
5. 사후 진단(선등록 아님): float32 보정 겹침 규칙으로 판정을 다시 계산했다(`posthoc_f32.py`). 사건 재현(`replay_c.py`)과 시간 입력 비교(`posthoc_timing_c.py`)도 했다.

## 변경된 파일

- microbenchmark: `docs/research/gpu/G10_CTX_LONG_PREREG.md`, `experiments/gpu/g10/{make_ctx_long_order.py, ctx_long_order.json, ctx_long_run.py, ctx_long_analyze.py, run_ctx_long.sh}`(`545f8f7`), `ctx_long_result/summary.json`(`228ce77`)
- 선등록 `c2f37d3`: `docs/research/gpu/G10_C_PREREG.md`, `experiments/gpu/g10/{predict_c.py, make_c_order.py, run_c.sh, judge_c.py}`, `plans_c/*`, `experiments/gpu/multiturn/configs.py`(GPU_LONG_BASE·GPU_LONG_KV)
- 자동 commit `089c7f4`: `experiments/gpu/g10/c_result/verdict.json`
- 사후 진단 산출물 `fc10373`: `experiments/gpu/g10/{posthoc_timing_c.py, c_result/posthoc_f32.json, c_result/posthoc_replay.json, c_result/posthoc_timing.json}`(script `posthoc_f32.py`·`replay_c.py`는 `0b2fa48`·`fc10373`)
- 기록 commit: `docs/research/gpu/GTASK25.md`, `GPU_INDEX.md`, `GPU_RESULTS_SUMMARY.md`

## 실험 또는 검증 방법

- plan: N = 24, 8 turn, 첫 prompt U(800, 1600), 생성 U(32, 256), toolmix gap. 이후 segment는 SHORT 8 / LONG 512 token이다. 두 조건의 세션별 첫 prompt·생성·tool wait·text seed는 같다.
- 구성: GPU_LONG_BASE 3,617 / GPU_LONG_KV 4,379 block(active preemption 구조적 불가), 격자 (1,2,4,8,16), `max_num_seqs` 8.
- 행렬: 2 도구 조건 × 2 구성 × 5 replicate = 20 lifecycle, 120 s 창, `--stream --exec-timing`.
- 예측기: `gpu_mt_sim` LRU + `StepCost("ctx")`(c_long = 2.1078 × 10⁻⁴ ms/token), lo/hi 동결.
- 참조 채널 R_ref: A `overall = OK`이므로 **DIRECT_EXEC**(결과 전 고정 규칙).
- Population: cell마다 창 안 turn ≥ 1 요청 971–1,623개(5 replicate 합).
- Unit: 요청 재사용률(cached > 0 비율), token 재사용률(Σ cached / Σ reusable), 호출당 비용 비.
- Device: A6000 `4485e769…`

## 결과

### microbenchmark (사전 단계)

- F1 `t = a(n) + c·ΣL`: **c_long = 2.1078 × 10⁻⁴ ms/token**(GTASK18 2.120 × 10⁻⁴). 24 cell 최대 |잔차| 0.103 ms. a(n) 13.29–13.53 ms.
- n = 8, L = 7,000: 25.35 ms(가격 13.6 ms의 1.86배). 함수 형태는 7,000 token까지 유지됐다.

### 재사용 (선등록 판정, 4 cell, lo / hi)

| cell | 요청 관측 | 요청 예측 lo / hi | 오차 lo / hi | token 관측 | token 예측 lo / hi | 오차 lo / hi |
|---|---|---|---|---|---|---|
| SHORT / BASE | 0.952 (1,528/1,605) | 0.955 / 0.953 | +0.003 / +0.001 | 0.951 | 0.954 / 0.951 | +0.003 / +0.001 |
| SHORT / KV | 0.973 (1,579/1,623) | 0.975 / 0.972 | +0.002 / −0.001 | 0.972 | 0.974 / 0.972 | +0.002 / +0.000 |
| LONG / BASE | 0.424 (412/971) | 0.474 / 0.476 | **+0.049 / +0.052** | 0.389 | 0.444 / 0.429 | **+0.054** / +0.039 |
| LONG / KV | 0.751 (832/1,108) | 0.780 / 0.776 | +0.029 / +0.025 | 0.708 | 0.758 / 0.741 | **+0.050** / +0.033 |

| 기준 | lo | hi |
|---|---|---|
| C1 요청 재사용 (모든 cell ≤ 0.05) | **PASS**(최대 0.0493, MAE 0.021) | **FAIL**(LONG/BASE 0.0521, MAE 0.020) |
| C2 token 재사용 (G-10 추가 기준) | **FAIL**(LONG/BASE 0.0542, LONG/KV 0.0502) | **PASS**(최대 0.0392) |
| C3 재사용 skill (기준선 0.84718) | PASS(Σ 0.083 ≤ 0.5 × 0.750) | PASS(Σ 0.079) |
| C3 token skill | `NA`(사전 기준선 없음) | `NA` |

- 오차의 부호는 8개 셀-설정 조합 모두 같은 방향(예측 ≥ 관측)이다. SHORT의 hi 요청 하나만 −0.0007이다.
- partial 비율: LONG/BASE 관측 0.059, 예측 0.052 / 0.091. LONG/KV 관측 0.071, 예측 0.049 / 0.056.
- 실제 prefill 계산 token(turn ≥ 1): LONG/BASE 관측 2,412,247, 예측 2,483,961(lo). 문맥 turn ≥ 1 prompt(r0): LONG 5/50/95 % = 1,724 / 3,575 / 5,600, 최대 6,652(microbenchmark 범위 7,000 안), SHORT 1,106 / 1,728 / 2,391. truncation 0.

### 비용 비 (선등록 판정: `NA`)

- DIRECT 판정 replicate 0: 20/20 본 측정과 20/20 재측정이 모두 겹침 > 0.01 ms였다. 원인은 GTASK24 사후 진단 1과 같다. 첫 겹침은 s ≥ 131,093 ms, 최대 0.0145 ms였고, 보정 규칙으로는 40/40 겹침 0이었다.
- C4·C5 `NA`(참조 채널은 결과 전에 DIRECT로 고정됐고 RECON으로 바꾸지 않는다).

보고(DIRECT 불필요): median R_RECON lo / hi는 SHORT 0.9914 / 0.9911, LONG 0.8596 / 0.8570이다. median R_PRED lo / hi는 SHORT 0.9935 / 0.9990, LONG 0.8657 / 0.8623이다.

### 사후 진단 1: 보정 겹침 규칙의 비용 판정 (`c_result/posthoc_f32.json`, 선등록 판정 아님)

| 도구 조건 | median R_DIRECT | DIRECT CI | sign | R_PRED lo − DIRECT | R_PRED hi − DIRECT | R_RECON lo / hi |
|---|---|---|---|---|---|---|
| SHORT | 0.9927 | [0.987, 0.999] | 5/0, p = 0.0625 | +0.0007 | +0.0063 | 0.9914 / 0.9911 |
| LONG | 0.8770 | [0.759, 0.936] | 5/0, p = 0.0625 | −0.0113 | −0.0147 | 0.8596 / 0.8570 |

- C4 lo·hi PASS(≤ 0.03).
- C5 skill: lo Σ 0.012, hi 0.021, 기준선 0.130 → 둘 다 PASS.

### 사후 진단 2: 사건 재현 (`c_result/posthoc_replay.json`)

- GTASK12 replay(무수정), 20 lifecycle: 창 안 turn ≥ 1 요청 **5,307/5,307 일치**, 결정 불가 0, free 수 분기 0, KV 축출 순서 429,653/429,653 일치.
- 따라서 LONG_TOOL의 재사용 과대 예측은 block 재사용 규칙(조회·할당·LRU·tail-first·생성 token 캐시) 오류가 **아니다**.

### 사후 진단 3: 시간 입력 (`c_result/posthoc_timing.json`)

| cell | 관측 wall/호출 ÷ sim wall/호출 (lo, replicate 중앙 (범위)) | 창 요청 수 관측 / 예측 lo (5 rep 범위, turn 0 포함) | 대기 관측 proxy / 예측 lo (s) |
|---|---|---|---|
| SHORT / BASE | 1.019 (1.010–1.027) | 355–373 / 367–389 | 1.78 / 1.63 |
| SHORT / KV | 1.021 (1.014–1.025) | 361–376 / 369–388 | 1.75 / 1.60 |
| LONG / BASE | **1.125** (1.100–1.174) | 185–254 / 216–279 | 5.27 / 4.33 |
| LONG / KV | **1.115** (1.040–1.151) | 215–280 / 240–294 | 4.15 / 3.41 |

step 종류별 (5 rep 합, ms/step, DIRECT 대 가격 lo; 가격에는 context 항이 없다):

| cell | decode step | decode DIRECT / 가격 | mixed step | mixed DIRECT / 가격 |
|---|---|---|---|---|
| SHORT / BASE | 31,745 | 16.51 / 13.61 | 1,779 | 38.1 / 29.8 |
| LONG / BASE | 17,941 | 19.39 / 13.62 | 1,827 | 142.0 / 108.5 |
| LONG / KV | 20,904 | 19.35 / 13.62 | 1,627 | 120.2 / 87.7 |

- LONG_TOOL에서는 실제 시간이 시뮬레이터보다 중앙 11–13 %(replicate 4–17 %) 느리게 흘렀다(SHORT는 1–3 %). 그 결과 창 요청이 적고 대기가 길며, 세션 재도착 사이에 다른 요청이 할당하는 양이 커진다(GTASK14의 오차 상관 변수). 이것이 재사용 과대 예측과 같은 방향이다.
- decode step: 문맥 인지 시간(가격 + c_long·(Σ문맥 − 128·d), LONG 평균 문맥 약 3,650 × 8에서 약 19.6 ms)이 DIRECT 19.4 ms와 거의 같다. decode 시간 입력은 맞다.
- mixed step: 시뮬레이터 시간 = 가격 + decode 몫 context 항(약 6 ms) ≈ 114 ms인데, DIRECT는 142 ms다. 약 28 ms × replicate당 약 365 step ≈ 창 120 s 중 10 s로, 관측된 시간 초과(중앙 11–13 %)의 대부분과 크기가 같다.
- **추정(미검증)**: 긴 prefix 위에서 하는 prefill(512 token 도구 출력 + 생성 응답)의 attention 비용이 가격 함수(prefill token 수만 씀)에 없는 것이 남은 시간 입력 오차의 주원인이다. mixed step 안 prefill 몫을 분리하는 신호가 없어 확인하지 못했다. 이는 G-08 결정 1의 원인 후보 "혼합·eager step과 prefill의 context 의존"과 같다.

### 사전 예측 대조

| 예측 | 결과 |
|---|---|
| C1 SHORT 통과, LONG/BASE 과대 예측 0.03–0.08 → FAIL 쪽 | 적중: hi FAIL(0.052), lo는 0.049로 간신히 PASS |
| C2 C1과 같은 방향, 문턱 근처 | 적중: lo FAIL(0.054 / 0.050), hi PASS |
| C3 PASS | 적중 |
| C4 LONG DIRECT 비가 가격 비보다 1에 가까움, 차 0.03 근처 FAIL 쪽 | 방향 적중(DIRECT 0.877 대 PRED 0.866), 크기 빗나감(사후 차 0.011–0.015, PASS) |
| C5 불확실 | 사후 PASS |

## 핵심 발견

1. 긴 도구 출력(문맥 중앙 3,575, 최대 6,652)에서도 block 재사용 규칙은 사건 단위로 정확하다(5,307/5,307).
2. 재사용 예측은 LONG_TOOL에서 0.025–0.054 과대다(8개 셀-설정 조합 모두 같은 방향). 문턱 0.05를 lo token과 hi 요청에서 근소하게 넘었다. SHORT_TOOL은 0.003 이하다.
3. 오차는 시간 입력에서 온다. LONG_TOOL에서 실제 시간이 시뮬레이터보다 중앙 11–13 % 느리고, decode가 아니라 긴 문맥 mixed(prefill) step이 가격보다 훨씬 비싸다(142 대 108 ms).
4. 비용 비는 사후 진단에서 맞는다(LONG |차| ≤ 0.015). 그러나 선등록 판정은 GTASK24와 같은 검사 결함으로 `NA`다.

## 해석

- 문맥 인지 시뮬레이터의 decode 시간은 7,000 token 문맥까지 맞는다. prefill 비용에 context 의존이 없는 것이 긴 도구 출력에서 재사용 예측을 0.03–0.05 높게 만든다(추정). 원고 문구는 고치지 않는다. 이 한계를 반영할지는 Advisor 결정이다.

## 확인되지 않은 사항

- mixed step 안 prefill 몫의 context 의존(분리 신호 없음). 지시문 범위 밖이라 새 함수 형태를 만들어 같은 데이터로 재검증하지 않았다.
- 대기 proxy는 HTTP 지연을 포함한다.
- 비용 판정의 사후 보정 규칙 인정 여부(GTASK24와 같음).

## 실패 / 무효 시도

- INVALID lifecycle 0. preemption 0(구조적 불가 설계대로).
- DIRECT 계측 결함 판정 40/40(본 측정과 재측정 모두)으로 C4·C5 `NA`다.

## 연구 원칙에 미치는 영향

- 측정 후 참조 채널을 RECON으로 바꾸거나 기준을 완화하지 않았다. 원래 기준의 실패와 `NA`를 그대로 보고한다.
- 동결 예측 파일은 바꾸지 않았다. 사후 진단은 판정과 분리해 기록했다.

## 다음 작업

- Advisor 결정: (1) C4·C5의 사후 보정 판정을 쓸지 여부. (2) LONG_TOOL 재사용 FAIL(0.05 근소 초과)의 원고 반영 방식. (3) prefill context 비용을 후속 연구로 둘지(지시문상 이번 범위 밖).

## 재현 정보

- microbenchmark: **선등록 `545f8f712d7d85fb97877fac53ab466a14993fb0`(08:10:49 UTC) → 측정 시작 08:10:49**(같은 초, `start_commit.txt` = `545f8f7`). 결과 commit `228ce77`(08:21:06).
- 본 측정: **선등록 `c2f37d39efc1c47a216f79d4dd93e81325ccf338`(2026-10-08 12:32:09 UTC) → 측정 시작 18:44:01 UTC**(`start_commit.txt` = `935d9d6`, B 판정 자동 commit). 측정 종료·판정 21:05:00, 자동 commit `089c7f4`. 사후 진단은 그 뒤에 했다.
- 예측 `plans_c/PREDICTIONS_C.json` SHA256 `be0536f7…`, `plans_c/CONFIGS.json` `558a2a12…`, 순서 `plans_c/ORDER_C.json`(seed 20264260), bootstrap seed 20264250
- run dir(비추적): `results/gpu/g10/c/chain_20261008T1232Z/`, microbenchmark `results/gpu/g10/ctx_long/20261008T0810Z/`, 사후 진단 원본 `results/gpu/g10/c/posthoc/`
- 환경: [GTASK23](GTASK23.md)와 같다(exec 층 적용).
