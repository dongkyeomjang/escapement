# TASK97 — NPU context 길이 step 비용 측정 (decode 전용 통제 부하)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 10 작업 A. 통제 step 비용([TASK13](TASK13.md))이 짧은 context로 재졌기 때문에 운영 중 step 초과([TASK91](TASK91.md) 1.07–1.09)가 생겼다는 가설을, context 길이를 통제 변수로 둔 decode 전용 부하로 잰다. GPU G-07과 같은 형태. 파라미터 측정이며 판정 없음, 재현성만 보고.

## 배경

- [TASK91](TASK91.md) — 운영 decode step 관측/통제 step 가중 1.084(BASE)·1.085(TUNED), 요청당 약 0.3 ms 초과
- [TASK92](TASK92.md) — 같은 serving 경로에서 짧은 context는 통제와 같고 긴 context 1.03–1.15(탐색)
- [결정 11](INDEX.md#결정-11--지시문-09-결정-task9195-결정-요청)-2, 후속 연구 11
- 설계 [CTXCOST_DESIGN.md](CTXCOST_DESIGN.md)(`dfd908d`)

## 시작 상태

- HEAD `f6ffd8f`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 설계·plan·구동 스크립트 commit(`dfd908d`, 2026-10-02T15:38:32+09:00) 직후 측정 시작(15:38:32), 종료 16:42:17. 29 lifecycle(BASE n ∈ {1,2,4,8} × L ∈ {512, 1,500, 3,000}, TUNED n ∈ {1,2,4,8,16} × L, 재현 반복 2) **전부 유효, 재실행 0**. TASK92의 두 결함은 설계에서 미리 피했다(소진 검사 여유 1.48–4.57, 같은 박자는 의도).
2. `ctxcost_analyze.py`(측정 뒤 작성, 정의는 설계 문서 고정): [TASK91](TASK91.md) 귀속으로 깨끗한 decode step마다 (b, n, ΣL = running 요청의 prompt + 생성 token 합, 간격)을 만들고, 64-token 평균 context 구간 중앙값으로 F1·F2·F3 적합. [TASK92](TASK92.md) `op-decode`(prompt 128) 짧은 context step을 함께 썼다.
3. 운영 비율 재현 검사: 적합 비용을 TASK82·87·95 run과 TASK92 `op-prefill-mt`의 **decode step 구조**(b, n, ΣL — 로그에서)에 적용해 step 가중 "context 비용 / 통제 비용"을 계산(TASK91 방식: (b, n)별 중앙값 비를 표본 가중). 그 run들의 step 시간은 읽지 않았다.
4. 작업 C의 background agent가 측정 도중(15:43–16:00경) 저장소 scan과 export 시험을 했다 — CPU 부하가 작았지만 측정과 겹쳤음을 기록한다.

## 변경된 파일

- `experiments/npu/stage3/{make_ctxcost_plans.py, run_ctxcost.sh, ctxcost_analyze.py}`, `plans/ctxcost/`(15 plan + INDEX)
- `docs/research/CTXCOST_DESIGN.md`, `docs/research/TASK97.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
R=/home/rebel/continuum-npu/results/npu/stage3/20261002-ctxcost
bash /home/rebel/continuum-npu/experiments/npu/stage3/run_ctxcost.sh $R
cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 ctxcost_analyze.py --run $R \
    --output /home/rebel/continuum-npu/results/npu/stage3/ctxcost/ctxcost.json
```

Population: 29 lifecycle의 평가 구간(40 s) 깨끗한 decode step 67,527 + TASK92 짧은 context step(BASE 24,842, TUNED 39,620). Unit: ms(step 시간 중앙값), token(ΣL). Source: client streaming chunk 간격, server `[BUCKET]`·ALLOC·FREE 순서. Device scope: `rbln0`–`rbln3` 한 server.

## 결과

### 1. n·L별 decode step 시간 (중앙값 ms, 괄호 = 관측/통제)

| n | BASE L 512 | 1,500 | 3,000 | TUNED L 512 | 1,500 | 3,000 |
|---|---|---|---|---|---|---|
| 1 | 10.50 (1.009) | 10.70 (1.027) | 10.91 (1.048) | 10.51 (1.009) | 10.62 (1.020) | 10.92 (1.049) |
| 2 | 11.07 (1.006) | 11.49 (1.044) | 12.03 (1.093) | 11.39 (0.998) | 11.97 (1.049) | 12.26 (1.074) |
| 4 | 11.59 (1.009) | 12.44 (1.082) | 13.33 (1.160) | 11.75 (1.023) | 12.27 (1.068) | 13.38 (1.165) |
| 8 | 13.78 (0.998) | 15.08 (1.092) | 17.24 (1.249) | 13.85 (1.003) | 14.95 (1.083) | 17.24 (1.249) |
| 16 | — | — | — | 18.07 (0.981) | 19.70 (1.069) | 25.22 (1.369) |

한 lifecycle 안에서 context가 L → L + 255로 늘 때 step 시간도 늘었다(예: TUNED n16 L3000 64-step 구간 24.80 → 25.61 ms). 재현성(TUNED 반복 lifecycle의 중앙값 차): n4 L1500 +0.94 %, n8 L3000 −0.55 %.

### 2. 형태

| 형태 | BASE c (µs/token) | β (ms) | RMS / 최대 잔차 (ms) | TUNED c | β | RMS / 최대 |
|---|---|---|---|---|---|---|
| **F1** `f(b) + βn + c·ΣL` | **0.145** | −0.005 | 0.237 / 0.796 | **0.149** | −0.017 | 0.361 / 1.458 |
| F2 c를 bucket별 | 0.135–0.168 | −0.004 | 0.235 / 0.769 | −0.072–0.191 | −0.017 | 0.355 / 1.453 |
| F3 `c·b·L̄`(padding 포함) | 0.145 | +0.053 | 0.240 / 0.794 | 0.143 | +0.096 | 0.396 / 1.479 |

F1의 f(b) ms: BASE 10.45 / 11.03 / 11.57 / 13.46 (b = 1/2/4/8), TUNED 10.40 / 11.45 / 12.57 / 13.46 / 14.73 / 17.46 (b = 1/4/6/8/10/16). **F1이 맞는다** — F2는 잔차를 거의 줄이지 못하고 TUNED에서 표본이 적은 bucket(6, 10: 짧은 context만)의 c가 불안정하며, F3(padding slot까지 context 비용)은 TUNED에서 더 나쁘다. **β ≈ 0**: 요청당 비용은 context 항이 거의 전부다.

### 3. 운영 비율 재현 검사 (적합 비용 / 통제 비용, step 가중)

| 적용 대상 | BASE F1 | TUNED F1 | 관측(비교) |
|---|---|---|---|
| TASK82 run 구조 | 1.084 | 1.083 | — |
| TASK82 + 87 run 구조 (TASK91 모집단) | **1.095** | **1.096** | TASK91 관측 **1.084 / 1.085** |
| TASK87 | 1.115 | 1.114 | — |
| TASK95 | 1.116 | 1.122 | — |
| TASK92 `op-prefill-mt` | **1.113** | **1.100** | TASK92 관측(같은 방식) **1.113 / 1.107** |

## 핵심 발견

1. **decode step 시간은 running 요청의 context 합에 선형으로 늘어난다**: c ≈ 0.145–0.149 µs/token(1,000 context token당 약 0.15 ms). 짧은 context(L = 512)에서는 통제 비용과 같고(0.98–1.03), L = 3,000에서 n = 8 1.25배, n = 16 1.37배.
2. **지시문 형태 F1이 맞고 β ≈ 0** — [TASK91](TASK91.md)의 "요청당 약 0.3 ms 초과"는 context 항(multi-turn 평균 context 약 1,800–2,000 token × 0.15 µs ≈ 0.3 ms)과 같은 크기다.
3. **운영 비율을 재현한다**: 이 비용을 운영 run의 step 구조에 적용하면 TASK91 모집단에서 1.095·1.096(관측 1.084·1.085, 약 1 %p 과대), TASK92 multi-turn형 run에서 1.113·1.100(관측 1.113·1.107). 통제 측정이 짧은 context로 쟀다는 것이 NPU 운영 초과의 주 원인이라는 가설과 맞는다.

## 해석

- 관찰: context 합에 선형인 decode 비용이 운영 비를 1 %p 이내로 재현한다. 파생 해석: NPU의 운영 step 초과는 serving 경로가 아니라 context 길이(KV attention 길이)의 비용이다. GPU G-07이 같은 형태를 보이면 두 기판 공통 원인 후보가 된다(후속 연구 11). 기존 판정에 소급 적용하지 않는다.
- TASK91 모집단에서 1 %p 과대인 이유는 확인하지 않았다(TASK87 고부하 run의 context가 길어 그쪽 비가 1.11대).

## 확인되지 않은 사항

- TUNED 최대 잔차 1.46 ms의 위치(구간별 잔차를 저장하지 않음).
- L > 3,256 context와 n > 16(측정하지 않음).
- BATCHONLY·DP artifact(측정하지 않음).

## 실패 / 무효 시도

- 없음(29/29 유효).

## 연구 원칙에 미치는 영향

- 통제 step 비용은 workload의 context 분포에서 재야 운영 시간 척도가 된다([TASK92](TASK92.md)의 교훈과 같은 방향, 이번에 형태와 계수로 확인).

## 다음 작업

- 작업 B 사후 재예측([TASK98](TASK98.md)).
- (Advisor) GPU G-07 결과와 비교, 비용 형태 채택 여부.

## 재현 정보

- 설계 commit `dfd908d`(15:38:32) → 측정 시작 15:38:32(같은 shell, commit 뒤 구동; `git-head.txt` = `dfd908d`), 종료 16:42:17. 측정 중 HEAD 불변.
- 산출(비추적) `ctxcost/ctxcost.json` SHA256 `3a06553c89e85d54…`.
- package: vllm 0.22.0+cpu, vllm-rbln 0.11.1(patched), Qwen3-4B artifact BASE·TUNED(새 compile 없음), device RBLN CA25.
