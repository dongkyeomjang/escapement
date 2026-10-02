# GTASK16 — GPU 정상성: 같은 길이(60 s) replicate 간 기준

## 상태

DONE

## 날짜

2026-10-01

## 목적

GPU 지시문 G-05 작업 E. **보고만 한다.**
- NPU 지시문 06 작업 A([TASK83](../TASK83.md))와 같은 방법으로 GTASK11 데이터의 평가 구간 전·후반 60 s 창을 비교한다.
- 비교 기준은 같은 cell의 다른 replicate의 같은 위치 창끼리의 차이 분포다.

## 배경

- NPU 방법 [STATIONARITY_REANALYSIS.md](../STATIONARITY_REANALYSIS.md)가 `main`에 있었다(`c7b444b`). merge `309871a`로 받았다.
- NPU 결과: h `WEAK_EVIDENCE`, 재사용 `NOT_NONSTATIONARY`

## 시작 상태

- HEAD `3ddbba8`

## 수행 내용

1. GPU 적용 방법 [GPU_STATIONARITY_METHOD.md](GPU_STATIONARITY_METHOD.md)를 계산 전에 commit했다(`f61b4fd`, 07:18:22 UTC).
   - NPU 방법 그대로이며 차이는 세 가지다.
     - 11 cell(부호 검정 `Bin(11, 0.5)`)
     - h는 decode-only(판정 정의), `reqs` 병기
     - 확증 9 cell 보조
2. `stationarity.py`로 계산했다(07:20:36 UTC, 한 번).

## 변경된 파일

- `docs/research/gpu/GPU_STATIONARITY_METHOD.md`(방법 commit), `experiments/gpu/multiturn/stationarity.py`(신규)
- `docs/research/gpu/GTASK16.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
python3 experiments/gpu/multiturn/stationarity.py --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z \
  --out <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/stationarity.json
```

- Population: 11 cell × r0–r4
- Unit: TVD(무차원), 재사용률
- Source: server `[GSTEP]`·`[GPFX]`, client `cached_tokens`

## 결과

| cell | median W (run 안) | median B (run 사이 60 s) | q_h (decode) | q_h (`reqs`) | median Δ reuse | median \|D\| | q_Δ | q_\|Δ\| |
|---|---|---|---|---|---|---|---|---|
| N20 BASE | 0.089 | 0.145 | 0.250 | 0.230 | +0.001 | 0.033 | 0.520 | 0.480 |
| N20 POOL | 0.117 | 0.176 | 0.350 | 0.350 | −0.010 | 0.026 | 0.435 | 0.370 |
| N20 POOL+GRID | 0.087 | 0.188 | 0.270 | 0.270 | +0.004 | 0.021 | 0.455 | 0.510 |
| N22 BASE | 0.198 | 0.170 | 0.540 | 0.540 | +0.025 | 0.046 | 0.535 | 0.470 |
| N22 POOL | 0.242 | 0.175 | 0.600 | 0.610 | −0.018 | 0.027 | 0.285 | 0.570 |
| N22 POOL+GRID | 0.270 | 0.194 | 0.600 | 0.600 | −0.022 | 0.023 | 0.315 | 0.490 |
| N24 BASE | 0.058 | 0.054 | 0.440 | 0.400 | +0.119 | 0.204 | 0.650 | 0.400 |
| N24 POOL | 0.042 | 0.035 | 0.430 | 0.440 | −0.013 | 0.039 | 0.400 | 0.420 |
| N24 POOL+GRID | 0.045 | 0.046 | 0.410 | 0.370 | −0.021 | 0.035 | 0.440 | 0.500 |
| N26 BASE | 0.005 | 0.006 | 0.420 | 0.350 | −0.220 | 0.216 | 0.420 | 0.600 |
| N26 POOL | 0.008 | 0.007 | 0.620 | 0.500 | +0.015 | 0.080 | 0.510 | 0.520 |

분류(방법 §4):

| | 11 cell | 확증 9 cell | NPU (13 cell) |
|---|---|---|---|
| h (decode-only) | **`NOT_NONSTATIONARY`**(q_h 중앙 0.43, k 4/11, p 0.89) | `NOT_NONSTATIONARY`(0.43, 3/9) | `WEAK_EVIDENCE`(0.638, 10/13) |
| h (`reqs`) | `NOT_NONSTATIONARY`(0.40, 3/11) | `NOT_NONSTATIONARY` | — |
| 재사용 후반 하락 | **`NOT_NONSTATIONARY`**(q_Δ 중앙 0.44, k 7/11, p 0.27) | `NOT_NONSTATIONARY`(0.44, 6/9) | `NOT_NONSTATIONARY`(0.45, 9/13) |
| q_\|Δ\| 중앙 | 0.49 | 0.48 | 0.49 |

## 핵심 발견

1. **`stack`** — **GPU multi-turn 평가 구간은 같은 길이 기준에서 비정상이라 부를 근거가 없다**(h·재사용 모두 `NOT_NONSTATIONARY`). run 안 전·후반 차이는 run 사이 같은 위치 창 차이와 같은 크기다(q_|Δ| 중앙 0.49). NPU의 약한 h 신호(저부하 N ≤ 8)는 GPU에서는 나타나지 않는다. GPU 확증 cell은 모두 고부하다.
2. **`stack`** — **붕괴 cell(N24·N26 BASE)은 run 안·run 사이 모두 재사용 요동이 크다**(같은 위치 |D| 중앙 0.20–0.22, 다른 cell 0.02–0.08). 다만 그 요동은 전·후반 방향으로 치우치지 않는다(q_Δ 0.65·0.42). 포화 근처의 되먹임이 60 s 해상도에서 큰 변동을 만든다는 관찰과 맞는다.
3. **`stack`** — 저부하 N20에서 q_h가 0.25–0.35로 0.5보다 낮다. run 안 두 창이 run 사이 같은 위치 창보다 **더 비슷하다**. run 사이 기준에 plan 차이가 들어 있어 보수적인 기준이라는 NPU의 주석과 같은 방향이다.

## 해석

- GTASK11의 120 s 합산 판정은 이 결과로 영향을 받지 않는다.
- 붕괴 cell의 큰 run 간 산포는 v1.1 blind 검증 설계(replicate 수, 판정 단위)에 들어가야 한다. cell 평균 하나로 붕괴를 판정하면 산포가 크다.

## 확인되지 않은 사항

- 붕괴 cell의 run 간 산포가 plan(seed) 차이에서 오는지 run 내부 되먹임의 우연에서 오는지(같은 plan 반복이 필요)

## 실패 / 무효 시도

- 없음

## 연구 원칙에 미치는 영향

- 없음(NPU TASK83 방법을 그대로 적용)

## 다음 작업

- 없음(보고)

## 재현 정보

- **방법 commit `f61b4fd7e874502ba9630c5d34ac32301cfceefd`(2026-10-01 07:18:22 UTC) → 계산 07:20:36 UTC**(선후 성립)
- 산출(비추적): `results/gpu/multiturn/main/20260930T1411Z/dynamics/stationarity.json`
