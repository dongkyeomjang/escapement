# TASK100 — BATCHONLY context 길이 step 비용 측정

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 11 작업 A. [TASK98](TASK98.md)은 BATCHONLY의 context 비용을 측정하지 않고 BASE·TUNED 적합값에서 규칙으로 정했다. blind 검증([TASK101](TASK101.md))의 입력에 규칙 추정이 섞이지 않도록 BATCHONLY artifact를 [TASK97](TASK97.md)과 같은 설계로 잰다. 파라미터 측정, 판정 없음.

## 배경

- [TASK97](TASK97.md) — 설계 [CTXCOST_DESIGN.md](CTXCOST_DESIGN.md), BASE·TUNED F1(c 0.145·0.149 µs/token, β ≈ 0)
- [TASK98](TASK98.md) — BATCHONLY 규칙: f(b) TUNED(b = 1,4,8,16)·BASE(b = 2), β·c = 두 적합의 평균

## 시작 상태

- HEAD `58e67a6`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 설계 개정 1(CTXCOST_DESIGN.md) + `run_ctxcost_bo.sh` commit(`f91b8e2`, 2026-10-02T17:01:26+09:00) 직후 측정 시작(17:01:26), 종료 17:36:47. TASK97의 plan `ctx-n{n}-L{L}` 15개 + 재현 반복 1(n8 L3000) = 16 lifecycle **전부 유효, 재실행 0**. **측정 중 다른 작업을 실행하지 않았다**(분석 스크립트 편집만, 실행 없음).
2. `ctxcost_analyze.py`에 BATCHONLY와 여러 run 디렉터리 입력을 추가했다. BASE·TUNED 적합은 TASK97과 동일함을 확인했다(F1 값 일치).

## 변경된 파일

- `experiments/npu/stage3/run_ctxcost_bo.sh`(신규), `ctxcost_analyze.py`(BATCHONLY, `--run` 여러 개), `make_ctxcost_sim.py`(측정된 BATCHONLY는 자기 적합 사용)
- `docs/research/CTXCOST_DESIGN.md`(개정 1), `docs/research/TASK100.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
R=/home/rebel/continuum-npu/results/npu/stage3
bash /home/rebel/continuum-npu/experiments/npu/stage3/run_ctxcost_bo.sh $R/20261002-ctxcost-bo
cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 ctxcost_analyze.py \
    --run $R/20261002-ctxcost $R/20261002-ctxcost-bo --output $R/ctxcost/ctxcost_v2.json
```

Population: 16 lifecycle의 깨끗한 decode step + TASK92 BATCHONLY 짧은 context step 33,137. Unit: ms, token. Device scope: `rbln0`–`rbln3` 한 server.

## 결과

### n·L별 decode step 시간 (중앙값 ms, 괄호 = 관측/통제)

| n | L 512 | 1,500 | 3,000 |
|---|---|---|---|
| 1 | 10.39 (0.997) | 10.62 (1.020) | 10.85 (1.042) |
| 2 | 11.21 (1.019) | 11.47 (1.042) | 12.01 (1.092) |
| 4 | 11.74 (1.022) | 12.42 (1.081) | 13.29 (1.156) |
| 8 | 13.90 (1.007) | 14.95 (1.083) | 17.21 (1.247) |
| 16 | 18.15 (0.985) | 19.70 (1.070) | 25.16 (1.366) |

재현성(n8 L3000 반복): +0.07 %.

### 형태

| 형태 | c (µs/token) | β (ms) | RMS / 최대 잔차 (ms) |
|---|---|---|---|
| **F1** | **0.146** | −0.069 | 0.461 / 1.898 |
| F2 | 0.119–0.168 | −0.069 | 0.457 / 1.917 |
| F3 | 0.145 | −0.012 | 0.468 / 1.884 |

F1 f(b) ms: 10.42 / 11.27 / 11.67 / 14.08 / 18.30 (b = 1/2/4/8/16). 운영 비율 재현 검사(F1/통제): TASK82 1.085, TASK87 1.112, TASK95 1.120, TASK92 `op-prefill-mt` 1.101.

### TASK98 규칙값과의 차이

| | 규칙(TASK98) | 실측 F1 |
|---|---|---|
| c (µs/token) | 0.1472 | 0.1460 |
| β (ms) | −0.011 | −0.069 |
| f(b) ms (1/2/4/8/16) | 10.40 / 11.03 / 11.45 / 13.46 / 17.46 | 10.42 / 11.27 / 11.67 / 14.08 / 18.30 |

대표 조건에서의 step 시간 차(규칙 − 실측, ΣL = n·(L + 128)):

| n | L 512 | 1,500 | 3,000 |
|---|---|---|---|
| 1 | +0.03 | +0.03 | +0.04 |
| 2 | −0.13 | −0.12 | −0.12 |
| 4 | +0.02 | +0.02 | +0.03 |
| 8 | −0.14 | −0.13 | −0.11 |
| 16 | +0.10 | +0.12 | +0.15 |

## 핵심 발견

1. **BATCHONLY의 context 기울기 c = 0.146 µs/token은 BASE(0.145)·TUNED(0.149)와 같다** — artifact에 무관한 값이다.
2. **TASK98 규칙값은 step 시간에서 ±0.15 ms(약 1 %) 이내로 실측과 맞았다.** f(b)와 β가 개별로는 다르지만(β −0.011 대 −0.069), 그 차이가 서로 상쇄한다. 따라서 TASK98의 BATCHONLY 사후 결과는 규칙 추정 때문에 크게 달라지지 않았을 것이다(재계산하지 않음).

## 해석

- 관찰: 세 artifact에서 c가 같다. 파생 해석: context 비용은 compile 구성(격자·batch)과 무관한 attention 길이 비용이고, f(b)만 구성마다 다르다.

## 확인되지 않은 사항

- BATCHONLY F1 최대 잔차 1.90 ms의 위치(구간별 잔차를 저장하지 않음).

## 실패 / 무효 시도

- 없음(16/16 유효).

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- blind cell 선등록과 측정([TASK101](TASK101.md)).

## 재현 정보

- 설계 commit `f91b8e2`(17:01:26) → 측정 시작 17:01:26(같은 shell, commit 뒤 구동; `git-head.txt` = `f91b8e2`), 종료 17:36:47.
- 산출(비추적) `ctxcost/ctxcost_v2.json` SHA256 `ad74845c961ace30…`. blind 입력 `CTXCOST_BLIND.json` `a6a3a614ecc6dd66…`.
