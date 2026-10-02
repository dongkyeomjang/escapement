# TASK102 — context 비용 시뮬레이터 blind cell N = 15·18 측정과 판정

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 11 작업 B의 측정과 일괄 판정. [TASK101](TASK101.md)에서 commit한 선등록([CTXBLIND_PREREG.md](CTXBLIND_PREREG.md))대로 30 lifecycle을 재고 `ctxblind_analyze.py`를 한 번 실행했다.

## 배경

- [TASK101](TASK101.md) — 선등록(`cb1eec4`), 주 예측기 `sim_ctx_op`
- [TASK97](TASK97.md)·[TASK100](TASK100.md) — context 비용, [TASK92](TASK92.md) — 운영 prefill
- [TASK95](TASK95.md) — 이전 blind cell(운영 비용 대 원래 비용 FAIL)

## 시작 상태

- HEAD `cb1eec4`(선등록), 측정 중 HEAD 불변, 다른 작업 없음

## 수행 내용

1. `run_ctxblind.sh`로 `ORDER_CTX.json` 순서 30 lifecycle 측정: 2026-10-02 18:02:44 – 20:03:37. **측정 중 다른 작업을 실행하지 않았다.**
2. 측정 종료 뒤 `ctxblind_analyze.py` 1회 실행(일괄 판정).

## 변경된 파일

- `docs/research/TASK102.md`(신규), `docs/research/INDEX.md`, `paper/RESULTS_INDEX.md`

## 실험 또는 검증 방법

```bash
R=/home/rebel/continuum-npu/results/npu/stage3/20261002-ctxblind
bash /home/rebel/continuum-npu/experiments/npu/stage3/run_ctxblind.sh $R
cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 ctxblind_analyze.py --run $R --output $R/ctxblind_verdict.json
```

Population: 30 lifecycle(2 N × 3 구성 × 5 replicate), 평가 구간 120 s. 정의·bootstrap은 [TASK95](TASK95.md)와 같다. Device scope: `rbln0`–`rbln3` 한 server.

## 결과

유효성: **30/30 유효, `INVALID` 0, 재실행 0, 빠진 replicate 0.**

### cell별 예측 대 관측

| cell | 재사용 관측 | (1) sim_ctx_op / (2) sim / (3) v1 | 비 m [95 % CI] | 비 (1) / (2) / (3) | running 평균 | TTFT 중앙 (s) |
|---|---|---|---|---|---|---|
| BASE N15 | 0.128 | 0.110 / 0.156 / 0.313† | — | — | 7.37 | 1.164 |
| BATCHONLY N15 | 0.792 | 0.786 / 0.797 / 0.783 | 0.7605 [0.7131, 0.8097] | 0.7486 / 0.7774 / 0.8430 | 6.87 | 0.083 |
| TUNED N15 | 0.793 | 0.787 / 0.792 / 0.774 | 0.7523 [0.7004, 0.7726] | 0.7302 / 0.7576 / 0.8217 | 6.66 | 0.083 |
| BASE N18 | 0.026 | 0.045 / 0.026 / 0.286† | — | — | 7.87 | 2.706 |
| BATCHONLY N18 | 0.734 | 0.733 / 0.745 / 0.540† | 0.7075 [0.6749, 0.7449] | 0.7011 / 0.7158 / 0.8791† | 8.94 | 0.088 |
| TUNED N18 | 0.730 | 0.733 / 0.739 / 0.643† | 0.6710 [0.6506, 0.7248] | 0.6797 / 0.6949 / 0.8140† | 8.63 | 0.087 |

† v1 범위 밖. 보고만 하는 `sim_ctx`(context 비용 + 원래 prefill): 재사용 0.137 / 0.790 / 0.793 / 0.043 / 0.730 / 0.742, 비 0.7561 / 0.7371 / 0.7054 / 0.6791.

### 판정

| 항목 | (1) sim_ctx_op (주) | (2) sim | sim_ctx (보고만) | (3) v1 (참고) |
|---|---|---|---|---|
| §5.1 재사용 (6 cell) | **PASS** — 6/6, 평균 부호 −0.001, MAE 0.0090 ≤ 0.5 × 0.2571(비 0.035) | PASS — MAE 0.0093 | 0.0072 | 3/6, MAE 0.126 |
| §5.2 비용 비 (4 cell) | **PASS** — 기본 4/4, 강화 4/4, Σ 0.0491 ≤ 0.5 × 1.1086(비 0.044) | PASS — Σ 0.0542 | Σ 0.0298 | 0/4, Σ 0.466 |
| §5.3 순위 | **PASS** — 해소 5쌍 전부 일치(N18 BATCHONLY/TUNED 1.0286 [0.9978, 1.0608] 미해소) | 같은 순서 | 같은 순서 | 같은 순서 |
| §5.6 h(n) | **PASS** — TVD 중앙 0.034, 최대 0.046; 영 0.588 | 0.073, 0.102 | 0.026, 0.062 | 0.065, 0.155 |
| (1) 대 (2) | **PASS** — 재사용 MAE 0.0090 < 0.0093, 비 Σ 0.0491 < 0.0542 | — | — | — |

### 사전 예측 대조

| 항목 | 사전 예측 | 결과 |
|---|---|---|
| §5.1 | PASS 쪽 | PASS(적중) |
| §5.2 (1) / (2) | PASS 쪽(경계) / FAIL 쪽 | PASS(적중) / **PASS(빗나감)** |
| §5.3 | PASS | PASS(적중) |
| §5.6 | PASS 쪽 | PASS(적중) |
| (1) 대 (2) | PASS 쪽, 확신 낮음 | PASS(적중) |

## 핵심 발견

1. **context 비용 시뮬레이터가 처음 보는 대기열 영역 cell에서 개정 2 기준 네 항목과 추가 확증을 모두 통과했다.** 주 예측기 (1)은 사전에 정한 조합이다.
2. **추가 확증 (1) 대 (2)의 차이는 작다**: 재사용 MAE 0.0090 대 0.0093(차 0.0003), 비 Σ 0.049 대 0.054. 두 예측기 모두 네 항목을 통과했다. 이 cell에서는 원래 비용 시뮬레이터의 비 오차가 TASK98(사후, N14·16)에서처럼 크지 않았다.
3. **점유 분포는 뚜렷하게 나아졌다**: h TVD 중앙 0.073 → 0.034, batch 16 구성 N18에서 0.10 → 0.03. 비 예측도 batch 16 4 cell 중 3 cell에서 (1)이 관측에 더 가깝다 — |오차| (1) BATCHONLY/TUNED N15 0.012/0.022, N18 0.006/0.009; (2) 0.017/0.005, 0.008/0.024(TUNED N15만 (2)가 가깝다).
4. BASE N18 재사용 관측 0.026은 (2)의 예측(0.026)과 같고, (1)(0.045)은 0.019 높다. N15 BASE는 (1)이 0.018 낮고 (2)가 0.028 높다.

## 해석

- 관찰: context 비용으로 시간을 진행한 시뮬레이터가 blind cell에서 원래 비용보다 두 지표 모두 근소하게 낫고, 점유 분포는 절반 이하 오차로 맞는다. 파생 해석: 결과와 독립된 통제 측정으로 정한 비용 수정이 처음 보는 조건의 예측을 개선했다 — [TASK95](TASK95.md)의 운영 비용 대 원래 비용(FAIL)과 달리 이번 수정은 decode의 context 항을 담는다.
- 다만 재사용 MAE 차(0.0003)는 replicate 산포보다 훨씬 작다. 추가 확증의 PASS는 기준 문자 그대로의 결과이며, "재사용 예측이 의미 있게 좋아졌다"는 근거로 쓰기는 약하다. 비용 비와 점유 분포의 개선이 더 분명하다.

## 확인되지 않은 사항

- `sim_ctx`(원래 prefill)가 이 cell에서 세 지표 모두 (1)보다 작았다(보고만, 판정 없음). prefill 운영 비용의 기여는 TASK98(사후)과 이번 blind에서 방향이 갈린다.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 사후 개선(TASK98)을 blind로 확인하는 절차가 작동했다. 주 예측기를 사후 최선이 아니라 사전 근거로 고른 경우에도 통과했다.

## 다음 작업

- Advisor 결정: 논문에서 context 비용 시뮬레이터의 위치(주 도구 교체 여부), prefill 운영 비용 사용 여부, 결과 색인·그림 데이터 반영.

## 재현 정보

- 선등록 commit `cb1eec4`(2026-10-02T18:02:44+09:00) → 측정 시작 18:02:44(같은 shell에서 commit 뒤 구동; `git-head.txt` = `cb1eec4`), 종료 20:03:37. 측정 중 HEAD 불변, 병행 작업 없음.
- run: `results/npu/stage3/20261002-ctxblind`(비추적), 판정 `ctxblind_verdict.json` SHA256 `e6f7b4a098a69762…`.
- package: vllm 0.22.0+cpu, vllm-rbln 0.11.1(patched), Qwen3-4B artifact BASE·BATCHONLY·TUNED(새 compile 없음), device RBLN CA25.
