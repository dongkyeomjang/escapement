# GTASK20 — 붕괴 영역 blind (N = 25·28), 세 비용 입력

## 상태

DONE

## 날짜

2026-10-02

## 목적

GPU 지시문 G-07 작업 C. 붕괴 영역의 새 seed·새 N(25·28)에서 sim LRU에 세 비용 입력을 넣고 blind로 판정한다.
- (1) GTASK18 context 길이 비용(주)
- (2) GTASK13 ×1.210과 mode_dist(GTASK11 관측으로 맞춘 보정 예측)
- (3) GTASK05 가격(기준선)

## 배경

- [GTASK11](GTASK11.md): N24·26 BASE 재사용 붕괴를 세 예측기 모두 과소 예측했다.
- [GTASK12](GTASK12.md)–[GTASK13](GTASK13.md): 의미론은 정확했다(사건 재생 `PASS`). 개발 집합에서는 시간 척도 ×1.210이 오차를 줄였다.
- [GTASK18](GTASK18.md): 운영 초과의 81–96 %는 context 길이 비용(c = 0.212 µs/token)이다.
- 선등록 [GPU_BLIND_COLLAPSE_PREREG.md](GPU_BLIND_COLLAPSE_PREREG.md)

## 시작 상태

- HEAD `b75c2b1`(GTASK18 기록), branch `gpu-a6000`

## 수행 내용

1. plan 10개, POOL+GRID 격자(규칙 6, N = 25·28 모두 (1,5,7,8,16)), 네 예측기 예측을 계산했다(`predict_blind.py` 1회). sim의 `step_cost` hook은 기존 예측과 정확히 같은 값을 내는 것으로 회귀 확인했다.
2. 예측·plan·순서·판정 script를 측정 전에 commit했다(`f0d8000`, 06:55:28 UTC).
3. `run_blind.sh`를 세션과 분리해 실행했다(06:55:28–08:48:24 UTC). **30/30 유효, 재실행 0**이었다.
4. `blind_judge.py`를 1회 실행했다(08:48:36). driver가 `blind_result/verdict.json`을 자동 commit했다(`bac3e63`). 측정 중 HEAD는 바뀌지 않았다.

## 변경된 파일

- 선등록 commit: `docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md`, `experiments/gpu/multiturn/{predict_blind.py, make_blind_order.py, blind_judge.py, run_blind.sh}`, `gpu_mt_sim.py`(`step_cost` hook, 기본 동작 불변), `configs.py`(blind 격자 읽기), `plans/blind/*`, `selection/blind_grids.json`
- 자동 commit: `experiments/gpu/multiturn/blind_result/verdict.json`
- `docs/research/gpu/GTASK20.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
R=<abs>/results/gpu/multiturn/blind/20261002T0655Z
setsid nohup experiments/gpu/multiturn/run_blind.sh $R > $R/outer.log 2>&1 &
```

- Population: 30 lifecycle(2 N × 3 구성 × r0–r4), 평가 구간 120 s, cell마다 turn ≥ 1 요청 1,336–1,512
- Unit: 재사용률(turn ≥ 1), turn당 A′-GPU 짝 비(중앙값, bootstrap 95 % CI), decode-only h의 TVD
- Source: server `[GSTEP]`·`[GPFX]`, client `cached_tokens`(`gpu_mt_measure`)
- Device: A6000 `4485e769…`

## 결과

### cell별 재사용 (관측 대 예측, lo)

| cell | 관측 | replicate별 관측 | (1) ctx | (2) ×1.210 | (2′) mode_dist | (3) 가격 | TTFT 중앙(s) |
|---|---|---|---|---|---|---|---|
| N25 BASE | **0.475** (650/1,367) | 0.56 0.63 0.23 0.49 0.44 | 0.514 | 0.494 | 0.490 | 0.696 | 3.27 |
| N25 POOL | 0.765 | 0.84 0.88 0.45 0.77 0.85 | 0.770 | 0.770 | 0.775 | 0.812 | 2.29 |
| N25 POOL+GRID | 0.762 | 0.84 0.88 0.43 0.76 0.85 | 0.772 | 0.782 | 0.774 | 0.813 | 2.33 |
| N28 BASE | **0.366** (489/1,336) | 0.16 0.51 0.48 0.03 0.59 | 0.403 | 0.353 | 0.379 | 0.494 | 3.12 |
| N28 POOL | 0.658 | 0.50 0.73 0.66 0.57 0.81 | 0.677 | 0.657 | 0.657 | 0.764 | 2.38 |
| N28 POOL+GRID | 0.658 | 0.53 0.72 0.66 0.58 0.78 | 0.682 | 0.662 | 0.663 | 0.755 | 2.29 |

### BASE 대비 비용 비 (lo; hi도 같은 판정)

| cell | m [95 % CI] | (1) ctx | (2) ×1.210 | (2′) mode_dist | (3) 가격 |
|---|---|---|---|---|---|
| N25 POOL | 0.8966 [0.8516, 0.9374] | 0.9047 | 0.9041 | 0.8966 | 0.9565 ✗ |
| N25 POOL+GRID | 0.8933 [0.8535, 0.9428] | 0.9039 | 0.9012 | 0.8981 | 0.9575 ✗ |
| N28 POOL | 0.9040 [0.8659, 0.9345] | 0.8969 | 0.8955 | 0.9009 | 0.9077 |
| N28 POOL+GRID | 0.9145 [0.8660, 0.9411] | 0.9005 | 0.8968 | 0.8988 | 0.9073 |

### 판정 (두 bound 모두)

| 항목 | (1) ctx (주) | (2) ×1.210 | (2′) mode_dist | (3) 가격 |
|---|---|---|---|---|
| §5.1 재사용 | **PASS** — 6/6 ≤ 0.10, 평균 부호 +0.022 / +0.023, MAE 0.022 / 0.023 ≤ 0.5 × 0.233 | PASS(MAE 0.011 / 0.012) | PASS(0.010 / 0.008) | **FAIL**(N25 BASE +0.22, MAE 0.108) |
| §5.2 비용 비 | **PASS** — 기본 4/4, 강화 4/4, Σ 0.040 / 0.028 ≤ 0.5 × 0.392 / 0.406 | PASS(Σ 0.042 / 0.029) | PASS(0.024 / 0.035) | **FAIL**(기본 2/4, N25 +0.06) |
| §5.3 순위 | **PASS** — N25·N28 모두 BASE 포함 두 쌍 해소, 순서 일치. POOL 대 POOL+GRID 미해소(1.002·1.000) | | | |
| §5.6 h (decode-only) | **PASS** — TVD 중앙 0.049 / 0.048, 최대 0.052 / 0.051, 균등 0.763 | PASS(0.046 / 0.051) | PASS(0.049 / 0.050) | PASS(0.028 / 0.029) |
| **추가 확증 (1) < (3)** | **`CONFIRMED`** — BASE 재사용 오차 0.075 / 0.084 대 0.348 / 0.319, 비 Σ 0.040 / 0.028 대 0.135 / 0.110 | | | |

보고(판정 없음), (1) 대 (2):

| 지표 (lo / hi) | (1) ctx | (2) ×1.210 | (2′) mode_dist |
|---|---|---|---|
| BASE 재사용 오차 Σ | 0.075 / 0.084 | 0.031 / 0.012 | 0.027 / 0.035 |
| 비 Σ 오차 | 0.040 / 0.028 | 0.042 / 0.029 | 0.024 / 0.035 |

- 직접/가격 채널 비(lifecycle 30개): 중앙 1.049, 범위 0.930–1.144

### 사전 예측 대조

| 항목 | 사전 예측 | 결과 |
|---|---|---|
| §5.1 (1) | PASS 쪽 | PASS(적중) |
| §5.2 (1) | 기본 기준 FAIL 쪽 | **PASS**(빗나감, 네 cell 모두 0.015 안) |
| §5.3 | PASS, POOL 대 POOL+GRID 미해소 | 적중 |
| §5.6 (1) | PASS 쪽 | PASS(적중) |
| 추가 확증 | CONFIRMED 쪽 | CONFIRMED(적중) |
| (1) 대 (2) | 차이는 replicate 산포보다 작음 | 적중(BASE 차 0.04–0.07, replicate 범위 0.4–0.56). 다만 재사용은 (2)가 더 가깝다 |

## 핵심 발견

1. **`stack`** — **결과와 독립된 통제 측정(context 길이 비용)만으로 시간을 진행한 sim LRU가 붕괴 영역 blind cell에서 네 항목을 모두 통과했다.** BASE 재사용 붕괴(N25 0.475, N28 0.366)와 구성 비용 효과(약 10 %)를 맞혔다. GTASK11의 붕괴 과소 예측은 의미론이 아니라 시간 척도에서 왔고, 그 시간 척도는 context 길이 비용으로 측정할 수 있다는 것이 blind로 확인됐다.
2. **`stack`** — **가격(짧은 context 통제 측정)으로 진행하면 붕괴를 크게 과소 예측한다**(N25 BASE +0.22, §5.1·§5.2 FAIL). 추가 확증 `CONFIRMED`: (1)은 (3)보다 BASE 재사용 오차가 약 1/4, 비 오차가 약 1/3이다.
3. **`stack`** — (1)은 재사용을 6/6 cell에서 조금 높게 예측했다(+0.005 – +0.049). 보정 예측 (2)·(2′)이 재사용에서는 더 가깝다(BASE 오차 Σ 0.01–0.03 대 0.08). (1)의 wall/가격 비(1.15–1.18)가 운영 1.21보다 작은 것, 즉 GTASK18 발견 3의 남은 1–4 %와 같은 방향이다. 비용 비에서는 세 시간 척도 입력의 차이가 없다.
4. **`stack`** — 붕괴 cell은 replicate 간 재사용 산포가 매우 크다(N28 BASE 0.03–0.59, N25 r2는 세 구성 모두 낮음). cell 합산 판정은 통과했지만, plan 하나 단위의 예측은 불확실하다(GTASK16과 같음).

## 해석

- 관찰: (1)·(2)·(2′)은 모두 PASS이고 (3)은 FAIL이다. 파생 해석: 붕괴 영역 예측에 필요한 것은 운영 조건의 step 시간이다. 그 시간은 GTASK11 관측으로 맞추지 않아도(1) 통제 측정 + plan context 분포로 얻을 수 있다. NPU [TASK95](../TASK95.md)에서는 운영 비용 (1)이 원래 비용 (2)보다 낫지 않았다. NPU 운영 비용에는 context 항이 없어 통제 비용과 거의 같았기 때문이다. GPU의 이번 결과는 context 항을 넣었을 때의 차이를 보여 준다.
- (1)이 재사용에서 (2)보다 조금 덜 맞는 것은 판정 밖 보고다. 원인 후보(가설)는 두 가지다. (a) 혼합·eager step의 context 의존을 재지 않았다(GTASK18 범위 밖). (b) prefill attention의 context 의존(NPU TASK92의 작은 prefill 초과)이 빠졌다.

## 확인되지 않은 사항

- (1)의 재사용 과대(+0.02)가 혼합 step과 prefill의 context 비용에서 오는지
- 붕괴 cell의 replicate 산포가 plan 차이인지 run 내부 우연인지(같은 plan 반복 필요)
- 직접/가격 채널 비 중앙 1.049가 GTASK11(1.131)보다 작은 이유(lag 0 cap, GTASK15)

## 실패 / 무효 시도

- 없음

## 연구 원칙에 미치는 영향

- 시뮬레이터 시간 진행에는 운영 workload의 context 길이를 반영한 통제 측정 비용을 쓴다. 짧은 context 가격은 포화 영역 동역학을 틀리게 만든다.

## 다음 작업

- Advisor 결정 대기(GPU_INDEX 다음 작업)

## 재현 정보

- **선등록 commit `f0d8000ee905d8ba71afec93db489b74c17930e7`(2026-10-02 06:55:28 UTC) → 측정 시작 06:55:28 UTC**. 같은 초이나 driver의 `start_commit.txt` = `f0d8000`이므로 commit이 먼저다. 측정 종료 08:48:24, 판정 08:48:36, 자동 commit `bac3e63`
- 예측 `plans/blind/PREDICTIONS_BLIND.json` SHA256 `ee6ddc0734aedc85…`, 순서 `ORDER.json` `ef31b5febf373b30…`, mode_dist 입력 GTASK13 `obs.json` `200c08be40b545f6…`(비추적)
- run dir(비추적): `results/gpu/multiturn/blind/20261002T0655Z/`(`sequence.log`, lifecycle 30개, `verdict.json`, `judge.stdout`)
- 환경: venv `/home/csdc/kyeom/envs/vllm-0.22.0`, `vllm 0.22.0`, `Qwen/Qwen3-4B@1cfa9a72…`, 관측 patch, KV events
