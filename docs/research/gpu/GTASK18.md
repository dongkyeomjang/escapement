# GTASK18 — context 길이 step 비용 측정

## 상태

DONE

## 날짜

2026-10-02

## 목적

GPU 지시문 G-07 작업 B. FULL decode step 비용을 decode 폭 n × 요청당 context 길이 L에서 재서, GTASK15 운영 초과가 context 길이에서 오는지 본다. **파라미터 측정, 판정 없음.**

## 배경

- [GTASK17](GTASK17.md): 관측 수단에 의한 관찰자 효과는 없었다. 짧은 context 통제 부하의 step은 가격과 같았다(n = 8에서 1.009).
- NPU [TASK92](../TASK92.md): 짧은 context에서는 decode가 통제 비용과 같았고, 긴 context에서는 1.03–1.15배였다.
- 설계 [GPU_STEPCOST_CTX_PREREG.md](GPU_STEPCOST_CTX_PREREG.md)

## 시작 상태

- HEAD `1799357`(GTASK17), branch `gpu-a6000`

## 수행 내용

1. G-07 작업 A: `git fetch` 후 `git merge origin/main` → merge commit `5f69657`(충돌 없음, TASK88–96 반영). TASK91·92·95를 읽었다.
2. 통제 부하의 context 길이를 기록에서 확인했다(설계 §2).
3. 설계와 측정·분석 코드를 측정 전에 commit했다(`b64eff3`, 06:39:39 UTC). 분석 코드는 합성 데이터로 실행 경로만 시험했다.
4. `run_stepcost_ctx.sh`를 세션과 분리해 실행했다(06:39:44–06:45:57 UTC). 2 lifecycle 모두 유효였고 재실행은 0이었다.
5. driver가 요약을 자동으로 local commit했다(`809a767`). 고친 자동 commit이 정상 동작했다.

## 변경된 파일

- `docs/research/gpu/GPU_STEPCOST_CTX_PREREG.md`, `experiments/gpu/stepcost/{stepcost_ctx_run.py, stepcost_ctx_analyze.py, run_stepcost_ctx.sh, ctx_order.json}`(선등록 commit)
- `experiments/gpu/stepcost/ctx_result/{summary.json, summary.md}`(driver 자동 commit)
- `docs/research/gpu/GTASK18.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
R=<abs>/results/gpu/stepcost_ctx/20261002T0639Z
setsid nohup experiments/gpu/stepcost/run_stepcost_ctx.sh $R > $R/driver.log 2>&1 &
```

- Population: 2 lifecycle × 3 round × 18 cell. cell마다 lifecycle당 FULL 간격 330–360개(앞뒤 3개 제외)
- Unit: ms, 연속 두 `[GSTEP]`(`maxq = 1, reqs = n, FULL`)의 dispatch 간격
- Source: server `[GSTEP]`, Prometheus delta(preemption 0, prefix cache hit 0)
- Device: A6000 `4485e769…`, GTASK11 BASE 인자, 조건 `s1k1a1`
- Σ L = Σ(prompt + 64)

## 결과

### 1. 통제 부하의 context 길이 (작업 B-1)

| 측정 | decode 중 요청당 context |
|---|---|
| GTASK05 FULL(가격) | 64–192(평균 128) |
| GTASK17 | 64–320(평균 192) |
| GTASK11 plan(운영, decode step 가중) | 평균 1,810, p05 1,102, 중앙 1,796, p95 2,551, 최대 3,273 |

### 2. n·L별 step 시간 (ms / GTASK05 가격 대비)

| n | L = 64 | L = 512 | L = 1,500 | L = 3,000 | 혼합(512·3,000 반반) |
|---|---|---|---|---|---|
| 1 | 13.434 / 1.002 | 13.491 / 1.006 | 13.759 / 1.026 | 14.176 / 1.057 | |
| 2 | 13.309 / 1.002 | 13.474 / 1.014 | 14.015 / 1.055 | 14.603 / 1.099 | |
| 4 | 13.363 / 1.001 | 13.751 / 1.030 | 14.605 / 1.094 | 15.862 / 1.188 | 14.839 / 1.111 |
| 8 | 13.639 / 1.001 | 14.389 / 1.057 | 16.100 / 1.182 | 18.571 / 1.364 | 16.503 / 1.212 |

- 재현성: 두 lifecycle의 차이는 최대 0.028 ms(0.2 %)다.

### 3. 형태

- **F1 `t = a(n) + c · Σ L`**
  - c = **2.12 × 10⁻⁴ ms/token**(0.212 µs/token)
  - a = 13.432 / 13.285 / 13.265 / 13.414 ms(n = 1/2/4/8). 이 값은 가격 F[b] + g·n(13.41 / 13.29 / 13.35 / 13.62)과 0.2 ms 안이다.
  - 균일 16 cell 잔차 최대 0.094 ms(0.7 %)
- **혼합 cell 잔차**: n8mix +0.002 ms, n4mix +0.031 ms. **비용은 Σ L을 따른다.** n · max L 형태라면 n8mix는 n8L3000과 같은 18.57 ms여야 하는데, 관측은 16.50 ms다.
- **n별 따로 적합**: c_n = 0.259 / 0.224 / 0.213 / 0.210 µs/token(n = 1/2/4/8). n = 1에서 조금 크고(+22 %) n ≥ 2에서는 거의 같다.

### 4. GTASK15 운영 비율 재현 (plan 평균 L̄ = 1,810만 입력)

| d | GTASK15 운영 | F1 | 보간(모형 없음) | F1 − 운영 | 운영 초과 중 F1이 설명하는 몫 |
|---|---|---|---|---|---|
| 1 | 1.034 | 1.030 | 1.031 | −0.004 | 89 % |
| 2 | 1.064 | 1.058 | 1.062 | −0.006 | 90 % |
| 3 | 1.100 | 1.081 | — | −0.019 | 81 % |
| 4 | 1.123 | 1.108 | 1.109 | −0.014 | 88 % |
| 5 | 1.147 | 1.132 | — | −0.015 | 90 % |
| 6 | 1.172 | 1.160 | — | −0.012 | 93 % |
| 7 | 1.227 | 1.185 | — | −0.042 | 82 % |
| 8 | 1.219 | 1.210 | 1.212 | −0.009 | 96 % |

### 5. 사전 예상 대조

| 예상 | 결과 |
|---|---|
| c ≈ 0.2–0.25 µs/token | 0.212(적중) |
| n = 8, L = 3,000이 가격의 약 1.35–1.4배 | 1.364(적중) |
| F1 재현값이 GTASK15와 ±0.03 안 | 7/8 적중, d = 7은 −0.042(빗나감) |
| 혼합 cell은 Σ L 형태 | 적중 |
| L = 64 cell이 GTASK17 곡선과 0.5 % 안 | n = 1·2·4는 0.1–0.4 % 안이고, **n = 8은 −0.74 %로 빗나감**. 평균 context 차이(GTASK17 192, 이번 128)를 F1로 환산하면 8 × 64 × 0.212 µs = 0.11 ms로, 차이 0.10 ms와 같은 크기다 |

## 핵심 발견

1. **`class`** — **decode step 비용은 running 요청들의 context 길이 합(Σ L)에 비례해 늘어난다.** F1 `t = a(n) + c · Σ L`이 16 cell을 0.7 % 안에서 맞히고, 혼합 cell이 n · max L이 아닌 Σ L 형태를 가른다. `class`인 근거: paged attention의 decode 비용은 요청별 KV 길이 합에 비례하는 구조이며, NPU([TASK92](../TASK92.md))에서도 같은 방향(긴 context 1.03–1.15배)이 관측됐다. 상수 c(0.212 µs/token)는 이 기판의 값(`stack`)이다.
2. **`stack`** — **GTASK15의 운영 초과(요청 수에 비례하는 약 22 %)는 context 길이로 대부분 설명된다.** plan의 평균 context 하나만 넣은 F1이 d = 1–8에서 운영 비율의 81–96 %를 재현했다(GTASK11·13 관측은 입력이 아님). "요청당 약 0.35 ms"는 요청당 평균 context 1,810 × 0.212 µs = 0.38 ms와 같은 크기다.
3. **`stack`** — 남은 차이는 모두 같은 방향(F1이 1–4 % 낮음)이다. 가설(미검증): 운영 중 동시에 달리는 요청의 context가 plan 전체 평균보다 길다(포화 cell에서 긴 turn이 오래 남음). 또는 a(n)이 운영 조건에서 조금 다르다.
4. 짧은 context(L = 64)에서는 a(n)이 가격과 같다. GTASK05·17의 통제 측정은 짧은 context만 쟀으므로 운영 시간 척도보다 짧았던 것이다.

## 해석

- GTASK13의 "운영 step = 가격 × 1.21"은 원인을 모른 채 맞춘 배율이었다. 이번 측정은 그것을 **결과와 독립된 통제 측정 + plan의 context 분포**로 재현한다. 두 기판에서 같은 원인이라면 논문의 일반 교훈은 이렇다: 처리 비용은 실제 부하와 같은 context 길이에서 재야 한다.
- 이 측정은 FULL decode만 다룬다. 혼합 step(prefill + decode)의 decode 부분과 prefill attention의 context 의존(NPU TASK92의 작은 prefill 초과)은 재지 않았다.

## 확인되지 않은 사항

- 운영 중 동시 실행 요청들의 context 분포(평가 구간, 포화 cell)와 plan 평균의 차이
- 혼합 step과 eager step의 context 의존
- c의 n = 1 증가(0.259)의 원인

## 실패 / 무효 시도

- 없음

## 연구 원칙에 미치는 영향

- step 비용 측정은 운영 workload의 context 길이 분포를 함께 덮어야 한다(NPU TASK92 원칙과 같음).

## 다음 작업

- G-07 작업 C: 붕괴 영역 blind N = 25·28, 예측기 (1)은 F1 context 비용을 쓴다.

## 재현 정보

- **선등록 commit `b64eff35bdb5489ae68f964226775bdcca4e2f43`(2026-10-02 06:39:39 UTC) → 측정 시작 06:39:44 UTC**. run의 `start_commit.txt` = `b64eff3`.
- 결과 자동 commit `809a767`(06:45:57 UTC)
- run dir(비추적): `results/gpu/stepcost_ctx/20261002T0639Z/`(`sequence.log`, `r0/`, `r1/`, `summary.json`)
- 환경: venv `/home/csdc/kyeom/envs/vllm-0.22.0`, `vllm 0.22.0`, `Qwen/Qwen3-4B@1cfa9a72…`, 관측 patch 적용 상태
