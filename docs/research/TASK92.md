# TASK92 — NPU 운영 조건 step 비용 재측정 (통제 부하, 같은 serving 경로)

## 상태

DONE

## 날짜

2026-10-01 – 2026-10-02

## 목적

Advisor 지시문 08 작업 B. [TASK91](TASK91.md)에서 multi-turn 운영 조건의 decode step이 통제 측정 비용([TASK13](TASK13.md))보다 길었으므로(|관측/예측 − 1| ≥ 0.05), multi-turn과 **같은 runner·server 인자·streaming 경로**에서 결과 관측과 독립된 통제 부하로 step 비용을 다시 잰다. 파라미터 측정이며 판정·예측이 없다. 재현성을 보고한다. 산출은 작업 C의 주 예측기 (1)이 시뮬레이터 시간 진행에 쓴다([TASK93](TASK93.md)).

## 배경

- [TASK91](TASK91.md) — 귀속 규칙(`step_audit.lifecycle`), decode 관측/예측 1.03–1.17(step 가중 1.07–1.09), 작은 prefill 1.2–1.35
- [TASK13](TASK13.md)·[TASK22](TASK22.md) — 통제 측정 비용 형태(decode `F[b] + β·n`, prefill `ceil(c/128)·(a + d·c)`)
- 설계 [STEPCOST_OP_DESIGN.md](STEPCOST_OP_DESIGN.md)(`6f0195a`, 개정 1 `8aa3801`, 개정 2 `f812705`)

## 시작 상태

- HEAD `a210be2`([TASK91](TASK91.md)), 설계 commit `6f0195a` 뒤 측정 시작

## 수행 내용

1. 설계 commit(`6f0195a`) 뒤 본 순서 50 lifecycle(decode 44 + prefill 4 + 재현 반복 2, seed 20261810 섞음) 측정: 2026-10-01 16:58:35 – 19:08:38, 평가 구간 40 s.
2. **n = 1(4 artifact)·DP n = 2 plan 소진**(10 세션 × 512 token이 warm-up + 40 s를 못 채움, `exhausted_slots`, 재실행도 같음). 개정 1: 30-세션 plan `op-decode-n{1,2}-s30`으로 5개 보충(00:08:16 – 00:19:29, 5/5 정상). **개정 1의 commit(`8aa3801`)이 보충 구동 시작보다 늦었다** — 문서 끝 빈 줄로 `git diff --check`가 실패해 commit이 빠진 채 구동이 시작됐다(run의 `git-head.txt` = `6f0195a`). 보충 plan 파일은 구동 전에 생성되어 바뀌지 않았고 sha256이 `INDEX_SUPP.json`에 있다. 판정 없는 파라미터 측정이라 선등록 대상 기준은 없다.
3. **`op-prefill` 설계 결함**: 모든 요청이 정확히 32 token을 생성해 4 slot이 같은 박자로 돌았다(prefill 4개 연속 → decode 31 step 공동 진행). 배타 prefill 표본이 BASE·BATCHONLY 각 60(거의 2,049–4,096 token), TUNED·DP 0. 개정 2(`f812705`, 측정 전 commit): multi-turn형 `op-prefill-mt`(4 slot, 4 turn, 첫 prompt U(64, 4096), 이후 8 token, 생성 U(8, 64), gap 0, 평가 120 s)를 4 artifact에 보충(00:21:29 – 00:35:06, 4/4 정상). 같은 개정에서 `step_audit.lifecycle`에 `eval_s` 인자(기본 120 = TASK91 경로 그대로)를 넣었다 — 첫 분석은 40 s 구간을 120 s로 읽었다.
4. **개정 2 뒤 분석 수정 1건(데이터를 본 뒤)**: 첫 재분석에서 `op-prefill-mt`의 깨끗한 decode step(긴 context)이 decode 적합에 섞여 들어갔다. 개정 2 문서의 "decode 적합은 바꾸지 않는다"와 설계 §3의 "decode lifecycle의 깨끗한 step 중앙값"대로 **decode 적합과 prefill 차감용 중앙값을 `op-decode*` lifecycle로 한정**했다. prefill lifecycle의 깨끗한 step은 따로 보고한다(아래 표 3).
5. 적합 산출을 `OPCOST_SIM.json`으로 동결(`make_opcost.py`, 원 산출 sha256 기록).

## 변경된 파일

- `experiments/npu/stage3/{make_stepcost_plans.py, run_stepcost_op.sh, run_stepcost_supp.sh, run_stepcost_supp2.sh, stepcost_op_analyze.py, make_opcost.py}`, `run_multiturn.sh`(선택 인자 6 `EVAL_S`), `step_audit.py`(`eval_s` 인자)
- `experiments/npu/stage3/plans/stepcost/`(op-decode 12, op-prefill, 보충 op-decode-n{1,2}-s30, op-prefill-mt, INDEX·INDEX_SUPP·INDEX_SUPP2), `plans/main/OPCOST_SIM.json`
- `docs/research/STEPCOST_OP_DESIGN.md`, `docs/research/TASK92.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
R=/home/rebel/continuum-npu/results/npu/stage3/20261001-stepcost-op
bash experiments/npu/stage3/run_stepcost_op.sh $R
bash experiments/npu/stage3/run_stepcost_supp.sh $R
bash experiments/npu/stage3/run_stepcost_supp2.sh $R
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/stepcost_op_analyze.py --run $R \
    --output results/npu/stage3/stepcost_op/stepcost_op.json
env -u PYTHONPATH python3 experiments/npu/stage3/make_opcost.py --source results/npu/stage3/stepcost_op/stepcost_op.json
```

Population: 유효 lifecycle 54(무효 11 = 소진된 n = 1·2 plan과 그 재실행; 재현 반복 2는 적합에서 빼고 재현성에만), 평가 구간 요청 3,788(귀속 불일치로 건너뜀 5). Unit: ms. Source: client streaming chunk 간격, server `[BUCKET]`·ALLOC 순서([TASK91](TASK91.md) 귀속 그대로). Device scope: `rbln0`–`rbln3` 한 server. 비교 기준 "통제" = descriptor 비용(TASK13, 미측정 bucket은 보간).

## 결과

### 1. decode — 운영 적합 (짧은 context: prompt 128 + 생성 512)

| artifact | F[b] ms | β ms/요청 | 관측/통제 (n별 중앙) min–max, 중앙 | 적합 잔차 최대 ms |
|---|---|---|---|---|
| BASE (1,2,4,8) | 10.362 / 10.878 / 11.436 / 12.920 | 0.1398 | 0.998–1.081, 1.009 | 0.43 |
| BATCHONLY (1,2,4,8,16) | 10.277 / 11.031 / 11.135 / 13.268 / 16.426 | 0.1312 | 0.974–1.084, 1.000 | 0.65 |
| TUNED (1,4,6,8,10,16) | 10.231 / 11.188 / 12.032 / 12.741 / 13.793 / 16.381 | 0.1376 | 0.972–1.026, 1.002 | 0.50 |
| DP (1,2,3,4,6,16) | 10.351 / 11.143 / 11.176 / 11.539 / 12.532 / 17.824 | 0.0135 | 0.973–1.015, 0.994 | 0.30 |

1.08대 두 점(BASE n = 4, BATCHONLY n = 8)은 lifecycle 하나의 값이다. 재현성(TUNED 반복 lifecycle의 중앙값 차): n4 `4/4` +0.7 %, n8 `8/8` +2.4 %(전이 구간 `6/6` +11.9 %는 표본이 적은 ramp 구간).

### 2. 배타 prefill — 운영 적합 (`op-prefill-mt`, 표본 1,070–1,101/artifact)

| artifact | a ms/chunk | d s/token | ≤128: 관측 / 적합 / 통제 ms | 129–512 | 513–1,024 | 1,025–2,048 | 2,049–4,096 |
|---|---|---|---|---|---|---|---|
| BASE | 22.70 | 2.23e-7 | 28.9 / 22.7 / 21.3 (580) | 52.8 / 45.5 / 42.6 | 134.2 / 137.1 / 129.8 | 292.3 / 299.8 / 289.1 | 605.9 / 609.0 / 605.2 |
| BATCHONLY | 23.39 | 5.39e-8 | 31.5 / 23.4 / 21.3 (576) | 56.4 / 46.8 / 42.6 | 136.0 / 140.6 / 129.8 | 293.5 / 305.2 / 288.6 | 609.7 / 612.7 / 604.8 |
| TUNED | 22.93 | 1.83e-7 | 29.9 / 22.9 / 21.3 (577) | 52.6 / 45.9 / 42.6 | 135.4 / 138.3 / 129.8 | 293.1 / 302.0 / 289.4 | 659.7 / 659.7 / 655.7 |
| DP | 23.06 | 1.36e-7 | 29.9 / 23.1 / 21.3 (601) | 53.6 / 46.2 / 42.6 | 133.8 / 138.9 / 129.7 | 292.9 / 302.5 / 288.6 | 660.7 / 658.9 / 655.7 |

(통제 a = 21.2 ms, d = 6.4e-7 s/token, TASK22.) 큰 prefill(> 512)은 통제와 1.00–1.05, 작은 prefill은 통제 대비 1.23–1.48·적합 대비 1.14–1.35 — **기존 형태로는 작은 prefill을 맞출 수 없다**(적합이 a를 7–10 % 올리고 d를 내려 타협).

### 3. 긴 context의 decode (탐색: `op-prefill-mt` lifecycle의 깨끗한 decode step, 적합에 쓰지 않음)

| artifact | n = 1 | n = 2 | n = 3 | n = 4 (표본) |
|---|---|---|---|---|
| BASE | 1.037 | 1.062 | 1.093 | 1.116 (16,212) |
| BATCHONLY | 1.096 | 1.092 | 1.120 | 1.146 (15,785) |
| TUNED | — | 1.030 | 1.082 | 1.110 (16,379) |
| DP | — | 1.059 | 1.086 | 1.119 (16,467) |

관측/통제. 같은 serving 경로·같은 n에서 context가 짧으면 1.00 근처, multi-turn형 긴 context(최대 4,283 token)면 1.03–1.15이고 n에 따라 커진다 — [TASK91](TASK91.md)의 운영 초과(n = 3 1.07, n = 4 1.09)와 같은 크기·모양이다.

## 핵심 발견

1. **같은 runner·server 인자·streaming 경로의 짧은 context 통제 부하에서 decode step 비용은 TASK13 통제 비용과 같다**(n별 중앙 관측/통제 0.97–1.08, artifact 중앙 0.994–1.009). TASK91의 운영 초과는 serving 경로가 아니다.
2. **같은 경로에서 긴 context(multi-turn 모양)의 decode는 1.03–1.15배**이고 running 수에 따라 커진다(탐색). 즉 TASK91의 초과는 **context 길이 의존 decode 비용**과 모양이 같다. 기존 decode 비용 형태(`F[b] + β·n`)에는 context 항이 없다.
3. **작은 prefill(≤ 512)의 운영 초과(통제 대비 1.23–1.48)는 이 통제 부하에서도 재현된다** — 작은 prefill은 대부분 긴 cache된 context 위의 continuation이다. 기존 prefill 형태(`ceil(c/128)·(a + d·c)`)에도 context 항이 없어 적합이 이를 흡수하지 못한다.
4. 결과적으로 작업 C 주 예측기 (1)의 운영 비용은 통제 비용과 decode에서 거의 같고 prefill chunk 비용만 7–10 % 크다.

## 해석

- 관찰: 짧은 context 1.00, 긴 context 1.03–1.15, 작은 prefill 1.23–1.48. 파생 해석: 운영 초과의 주 원인은 cache된 context 길이(attention 길이)이며 serving 경로(streaming, runner) 몫은 측정 해상도(±2–3 %) 아래다. 가설(미검증): context 길이 항을 가진 비용 형태라면 TASK91의 초과와 TASK90 발견 4의 남은 편향을 더 설명할 수 있다 — 형태 변경은 이번 설계 밖(새 자유도)이라 하지 않았다.
- 통제 decode 측정(TASK13)은 짧은 context에서 이뤄졌으므로 multi-turn 시뮬레이터의 시간 척도로는 context 길이만큼 짧다. 이것은 GPU GTASK13의 "운영 시간 척도" 결론과 같은 방향이다.

## 확인되지 않은 사항

- context 길이 의존의 정량 형태(선형 여부, 요청별 vs batch 최대 context): 요청별 context를 step마다 기록하지 않았다.
- 긴 context decode의 n = 5 이상(4 slot plan이라 없음).

## 실패 / 무효 시도

- n = 1·DP n = 2 plan 소진(설계의 세션 수 계산 실수) → 개정 1 보충.
- `op-prefill` 같은 박자 결함(고정 생성 길이) → 개정 2 보충. `op-prefill` 표본은 적합에 쓰지 않았다(기록: BASE 60, BATCHONLY 60).
- 개정 1 commit이 보충 구동 시작보다 늦음(수행 내용 2).
- 첫 재분석의 decode 적합 오염(수행 내용 4).

## 연구 원칙에 미치는 영향

- 통제 부하는 운영 workload의 **context 길이 분포**까지 맞춰야 운영 비용을 재현한다. 짧은 prompt의 통제 부하는 serving 경로만 통제한다.
- 고정 생성 길이·같은 시각 시작의 plan은 slot이 같은 박자로 돌아 배타 prefill 간섭을 관측하지 못한다.

## 다음 작업

- 작업 C 선등록과 측정([TASK93](TASK93.md)): 주 예측기 (1)이 `OPCOST_SIM.json`을 쓴다.
- (Advisor 결정 사항) context 길이 항을 가진 비용 형태를 측정·도입할지.

## 재현 정보

- 설계 `6f0195a`(2026-10-01, 측정 시작 16:58:35 이전), 개정 1 `8aa3801`(보충 시작 00:08:16 **이후** commit), 개정 2 `f812705`(보충 2 시작 00:21:29 이전).
- run: `results/npu/stage3/20261001-stepcost-op`(비추적), `git-head.txt` = `6f0195a`, `6f0195a`, `f812705`.
- 산출(비추적) `stepcost_op/stepcost_op.json` SHA256 `4ca494a7ced59e64…`, `OPCOST_SIM.json` `29b96b8a14850f6c…`.
- package: vllm 0.22.0+cpu, vllm-rbln 0.11.1(patched `model_base.py`), model Qwen3-4B, artifact 4종(새 compile 없음), device RBLN CA25 `rbln0`–`rbln3`.
