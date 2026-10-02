# TASK91 — NPU 운영 조건 step 시간 감사 (개발 집합)

## 상태

DONE

## 날짜

2026-10-01

## 목적

Advisor 지시문 08 작업 A. GPU에서 통제 측정 step 비용이 운영 중 실제 step보다 약 21 % 짧았고 그 차이가 decode 폭에 비례했다(GTASK13–15). [TASK90](TASK90.md) 발견 4(시뮬레이터도 batch 16 구성의 비용 비를 +0.03–0.06 편향)가 같은 종류의 원인인지, TASK82·87 multi-turn run의 기록으로 본다. **개발 집합 분석, 판정 없음.**

**측정 0, device 0.**

## 배경

관련 TASK:

- [TASK13](TASK13.md) — decode step 비용 `f(b) + α + β·n`(end-to-end ITL 채널), [TASK22](TASK22.md) — 배타 prefill 비용
- [TASK82](TASK82.md)·[TASK87](TASK87.md) — 운영 run(105 lifecycle)
- [TASK90](TASK90.md) — 발견 4
- GPU `GTASK13`(운영 step 1.21배), `GTASK15`(귀속 lag) — `git show origin/gpu-a6000:`로 읽음

## 시작 상태

- HEAD `338d3de`([TASK90](TASK90.md), `origin/main`과 같음), `git status --short`: `?? .idea/`만

## 수행 내용

1. **귀속 규칙을 먼저 정했다**(`step_audit.py` docstring). 요청 R의 ALLOC과 FREE 사이 `[BUCKET]`이 R의 decode step이고(수 = `completion_tokens − 1`, 105 lifecycle 20,166 요청 전부 일치, 건너뜀 0), R의 streaming chunk `k → k+1` 간격이 decode step `k`의 시간이다. 두 `[BUCKET]` 사이에 다른 요청의 ALLOC이 없으면 **깨끗한 decode step**, 정확히 하나면 그 요청의 배타 prefill이 낀 간격(간격 − 같은 구성·(b, n)의 깨끗한 step 중앙값 = 관측 prefill). NPU는 prefill이 배타라 GPU의 async lag 문제(GTASK15)가 없다 — 사건 순서가 server 로그에 그대로 있다. 채널은 TASK13의 적합과 같은 client end-to-end ITL이다.
2. 구성(artifact)·bucket·n별 관측 중앙값을 descriptor 비용(측정 bucket은 TASK13 값, 미측정은 보간·외삽)과 비교.
3. **발견 4 설명 비율**(`step_audit_explain.py`): 시뮬레이터의 시간 진행만 관측/예측 비로 늘리고(decode는 구성·n별, prefill은 계산 token 구간별), step 가격은 원래 비용 모형으로 매겨(A′ 채널과 같은 가격) N = 12·14·16의 비용 비 편향을 다시 계산.

## 변경된 파일

- `experiments/npu/stage3/{step_audit.py, step_audit_explain.py}`(신규)
- `docs/research/TASK91.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/step_audit.py --output results/npu/stage3/step_audit/audit.json
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/step_audit_explain.py --output results/npu/stage3/step_audit/explain.json
```

Population: TASK82·87의 105 lifecycle, 평가 구간 요청 20,166. Unit: ms. Source: client streaming chunk 시각, server `[BUCKET]`·`[PFX]` 순서. Device scope: `rbln0`–`rbln3` 한 server.

## 결과

### decode step (관측 중앙 / 예측, 깨끗한 step; 표본 = step × running 요청)

| n | BASE (1,2,4,8) | BATCHONLY (…,16) | TUNED (1,4,6,8,10,16) | DP (1,2,3,4,6,16) |
|---|---|---|---|---|
| 1 | — | 1.030 | 1.028 | 1.031 |
| 2 | — | 1.056 | 1.041 (b4) | 1.057 |
| 3 | 1.068 | 1.071 | 1.070 | 1.068 (b3†) |
| 4 | 1.091 | 1.095 | 1.094 | 1.095 |
| 5 | 1.054 | 1.058 | 1.045 (b6†) | 1.049 (b6†) |
| 6 | 1.076 | 1.081 | 1.086 (b6†) | 1.100 (b6†) |
| 7 | 1.104 | 1.107 | 1.111 | 1.022 (b16†) |
| 8 | 1.114 | 1.114 | 1.120 | 1.038 (b16†) |
| 9–10 | | 1.040–1.052 (b16†) | 1.151–1.168 (b10†) | |
| 11–14 | | 1.062–1.143 (b16†) | 1.091–1.132 (b16†) | |
| **step 가중** | **1.084** | **1.076** | **1.085** | **1.069** |

† 미측정 bucket(보간·외삽값). 절대값 예: BASE b8 n8 관측 15.37 ms 대 예측 13.80 ms. 같은 bucket 안에서 n이 클수록 비가 커진다(b4: n3 1.07 → n4 1.09, b8: n5 1.05 → n8 1.11) — GPU GTASK15 발견 2(요청당 초과)와 같은 모양이다. 요청당 초과는 b8에서 (15.37 − 14.42)/3 − 0.041 ≈ 0.28 ms(관측 기울기 0.32 ms/요청 대 모형 0.041).

### 배타 prefill (관측 / 예측)

| 계산 token | BASE | BATCHONLY | TUNED | DP |
|---|---|---|---|---|
| ≤ 128 | 1.32 | 1.35 | 1.34 | 1.33 |
| 129–512 | 1.20 | 1.21 | 1.21 | 1.21 |
| 513–1,024 | 1.02 | 1.03 | 1.03 | 1.03 |
| 1,025–2,048 | 1.01 | 1.02 | 1.02 | 1.01 |
| > 2,048 | 1.01 | 1.01 | 1.01 | 1.01 |

(구간 중앙 비의 중앙값.) 작은 prefill에 약 7 ms의 고정 초과가 있다(28.0 대 21.3 ms).

### TASK90 발견 4 설명 비율

| cell | sim 비 편향(원래) | 시간 척도 적용 | 설명 비율 |
|---|---|---|---|
| BATCHONLY N12 | +0.0387 | +0.0226 | 42 % |
| TUNED N12 | +0.0341 | +0.0176 | 48 % |
| BATCHONLY N14 | +0.0321 | +0.0138 | 57 % |
| TUNED N14 | +0.0516 | +0.0285 | 45 % |
| BATCHONLY N16 | +0.0468 | +0.0229 | 51 % |
| TUNED N16 | +0.0589 | +0.0297 | 50 % |
| **Σ\|편향\|** | **0.262** | **0.135** | **48.5 %** |

같은 적용에서 BASE 재사용 편향: N12 +0.023 → −0.005, N14 +0.032 → −0.021, N16 +0.026 → +0.007. 원래 시간 재현은 TASK90의 sim 편향과 일치(예: +0.0387).

- `requested_condition` 등: 해당 없음(기존 데이터)

## 핵심 발견

1. **`stack`** — **NPU 운영 조건의 decode step은 통제 측정 비용보다 3–17 % 길고(step 가중 1.07–1.09), 초과가 running 요청 수에 비례해 커진다**(요청당 약 0.3 ms). 값은 이 기판·runner의 것이다.
2. **`class`** — **운영 step 초과가 요청 수에 비례한다는 모양은 두 기판에서 같다**(NPU 약 0.3 ms/요청, GPU 약 0.35 ms/요청, GTASK15). 근거: streaming 출력·응답 처리처럼 요청마다 붙는 host 작업이 step 경로에 들어가는 구조는 serving stack 범주의 것이다(원인 미확인, 가설).
3. **`stack`** — **이 시간 척도 차이가 시뮬레이터 비용 비 편향의 약 절반(48.5 %)을 설명한다.** 가격은 그대로 두고 동역학만 바뀐 결과다 — 실제 step이 길면 대기·batch 폭이 달라지고 구성 간 차이가 커진다. 나머지 절반은 다른 원인(미측정 bucket 비용, 작은 prefill 초과의 가격 쪽 영향 등, 미확인)이다.

## 해석

- 차이가 0.05를 넘으므로(어느 구성이든 1.05–1.17) 지시문 08 §4 작업 B(운영 조건 step 비용 재측정)를 한다([TASK92](TASK92.md) 예정).
- 이 비율은 개발 집합에서 얻었으므로 blind 예측의 입력으로 쓰지 않는다(지시문 08 §5.2). 작업 C의 주 예측기는 작업 B의 독립 통제 측정 비용을 쓴다.

## 확인되지 않은 사항

- 요청당 초과의 원인(streaming chunk 전송, usage 계산, 관측 log).
- 비용 비 편향의 나머지 절반.

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- 통제 측정 비용(가격)과 운영 시간 척도(동역학)는 다를 수 있다 — 시뮬레이터는 시간 진행에 운영 조건의 비용을 써야 한다(GPU GTASK13과 같은 결론).

## 다음 작업

- 작업 B: 운영 조건 step 비용 재측정 설계 commit → 측정([TASK92](TASK92.md)).

## 재현 정보

- 위 명령. 산출(비추적) SHA256: `step_audit/audit.json` `a367872f…`, `step_audit/explain.json` `8a3228e1…`.
- 선등록 commit: 해당 없음(개발 집합, 판정 없음)
