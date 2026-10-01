# TASK85 — 모형 v1.1: 대기열·부하 결합 생존 (개발 집합 N = 12)

## 상태

DONE

## 날짜

2026-10-01

## 목적

Advisor 지시문 06 작업 C(결정 8-3). 구성 선택의 차이가 가장 큰 영역(N = 12, 비 0.83–0.84)에서 모형이 가장 약했다. 동시 실행 상한 M이 있는 경우의 대기열 효과를 B1 생존에 넣는다. descriptor v2 위에서 기판 중립으로 만들고, [TASK82](TASK82.md) N = 12 데이터를 **개발 집합으로 선언**해 그 성적은 개발 집합 성적으로만 보고한다. n ≤ M 영역에서 v1과의 차이를 보고한다.

**측정 0, device 0.**

## 배경

관련 TASK:

- [TASK82](TASK82.md) — N = 12 탐색: 해석 BASE 재사용 0.404 대 관측 0.484, 비 과소, B2 가정 n ≤ M 파괴
- [TASK84](TASK84.md) — descriptor v2(v1.1이 `C`·`M`·의미론을 읽는 곳)
- [TASK73](TASK73.md) — v1(`(f, a, d)` 연쇄, 정확 추적기, `FifoReplay`)
- [MODEL_V0.md](MODEL_V0.md) B2 — `μ(min(n, M))`는 v0부터 있었다

## 시작 상태

- HEAD `c58daaf`([TASK84](TASK84.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. **개발 집합 진단**(`v11_dev.py`, N = 12 15 lifecycle만): 재도착마다 기준 재생(정확 추적기 BASE 918/918·BATCHONLY 1,029/1,029·TUNED 1,054/1,054 일치), 기록된 초기 상태·창 안 할당·대기 추정, v1의 세 변형. **v1 오차가 두 방향으로 상쇄**함을 찾았다(T 할당 시 `a0 ≤ 6`에서 과소, `a0 = 7`에서 과대).
2. 원인 분리: 창 안 할당이 λ 기대와 부하에 따라 어긋나고(`a0 = 2` 7.2 대 9.3, `a0 = 7` 13.1 대 11.7), plan 간 이질성이 크다(BASE r0 0.708 대 r1 0.286).
3. **v1.1 연쇄**(`survival_v11.py`): 다른 세션의 엔진 안 수 `m` + gap 위상 + `(a, d)`의 흡수 연쇄, FCFS 대기의 결합, T·R의 대기, gap 법칙(zero atom + 지수 혼합 EM), 완료 순서 선택. 수식·가정은 [MODEL_V1_1.md](MODEL_V1_1.md).
4. 첫 형태(지수 gap)는 개발 집합에서 부하–생존 관계의 **방향을 거꾸로** 냈다(한가한 순간 생존이 가장 낮음) → gap 위상 도입. 이어 **완료 순서**(`random` 대 `admission`)가 BASE 수준을 가른다는 것을 찾았다.
5. **정확성 self-check**: 같은 가정의 항목 단위 Monte Carlo(`tests/mc_survival_v11.py`)와 대조(`tests/test_survival_v11.py`).
6. **개발 집합 평가**(`v11_dev_eval.py`): 완료 순서 × gap 위상 K ∈ {1, 2, 3} × pooled/per-plan. **선택 규칙: 재사용 MAE 최소** → admission, K = 3, per-plan으로 **동결**.
7. **v1 대 v1.1 예측 비교**(`predict_v11.py`): N = 6·8·10(+DP8)·12.
8. `occupancy.others_in_engine_at_arrival`(공개 helper, 기존 함수 무변경) 추가, 분석 경로 `mt_predict_v11.analytic_v11`(v1 경로 복제 + 생존만 교체, `mt_predict.py` 무수정).

## 변경된 파일

- `src/continuum/model/survival_v11.py`(신규), `src/continuum/model/occupancy.py`(helper 추가)
- `experiments/npu/stage3/{mt_predict_v11.py, predict_v11.py, v11_dev.py, v11_dev_eval.py}`(신규)
- `tests/{mc_survival_v11.py, test_survival_v11.py}`(신규)
- `docs/research/{MODEL_V1_1.md, TASK85.md}`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev.py --output results/npu/stage3/v11_dev/diag.json
env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev_eval.py --ks 1,2,3 --order random --output results/npu/stage3/v11_dev/eval.json
env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev_eval.py --ks 2,3 --order admission --output results/npu/stage3/v11_dev/eval_admission.json
env -u PYTHONPATH python3 tests/test_survival_v11.py
env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX.json --ns 6,8,10,12 --with-dp8 \
  --predictors v1,v11 --workers 70 --output results/npu/stage3/predict/v11_main_predictions.json
```

(첫 `v11_dev_eval.py` 실행은 `--order` 옵션 추가 전이며 기본이 `random`이었다.)

## 결과

### 개발 집합 진단 (N = 12 BASE, 재도착 918)

| `a0` | n | 관측 생존 | v1(기록 상태) | 창 안 할당 관측 / λ 기대 | R 대기 추정 (s) |
|---|---|---|---|---|---|
| 2 | 69 | 0.783 | 0.520 | 7.17 / 9.35 | 0.035 |
| 4 | 120 | 0.717 | 0.459 | 8.76 / 9.27 | 0.057 |
| 6 | 133 | 0.481 | 0.392 | 11.72 / 11.35 | 0.166 |
| 7 | 314 | 0.175 | 0.435 | 13.08 / 11.69 | 0.515 |

v1 셀 합계: 기록 상태 0.443, 대기 추가 시 0.411(오히려 멀어짐), 관측 0.484. replicate별 BASE 관측 0.708 / 0.286 / 0.358 / 0.619 / 0.464, v1은 모두 0.43–0.46.

### 연쇄 정확성 (같은 가정의 Monte Carlo, 4,000 cycle)

| 완료 순서 | N, M, C, s_active, s_idle | 연쇄 | MC |
|---|---|---|---|
| random | 12, 8, 8, 3, 1 / 12, 8, 8, 3, 5 / 6, 8, 8, 2, 3 / 12, 16, 16, 3, 3 | 0.333 / 0.028 / 0.866 / 0.869 | 0.330 / 0.024 / 0.854 / 0.869 |
| admission | 같음 | 0.465 / 0.037 / 0.893 / 0.898 | 0.468 / 0.034 / 0.888 / 0.889 |

8/8 |차| ≤ 0.012(허용 0.02). gap 법칙 적합 평균 보존, LRU 기판 거부. `tests/test_survival_v11.py` PASS.

### 개발 집합 평가 (N = 12, 관측 재사용 BASE 0.484 · BATCHONLY 0.855 · TUNED 0.859, 비 0.844 · 0.830)

| 변형 | BASE 재사용 | 비 B / T | 재사용 MAE | 비 오차 합 | h TVD B / BO / T |
|---|---|---|---|---|---|
| v1 | 0.404 | 0.891 / 0.875 | 0.041 | 0.092 | 0.142 / 0.101 / 0.103 |
| random K1 / K2 / K3 (per-plan) | 0.262 / 0.282 / 0.288 | 0.852 / 0.838 … 0.858 / 0.844 | 0.085 / 0.080 / 0.078 | 0.016 / 0.026 / 0.029 | 0.124 / 0.091 / 0.096 |
| admission K2 (pooled / per-plan) | 0.427 / 0.430 | 0.895 / 0.880, 0.893 / 0.878 | 0.030 / 0.029 | 0.101 / 0.097 | — |
| **admission K3 per-plan (동결)** | **0.436** | 0.894 / 0.879 | **0.026** | 0.100 | 0.114 / 0.091 / 0.096 |

전체 표는 [MODEL_V1_1.md](MODEL_V1_1.md) §4.

### v1 대 v1.1 예측 (n ≤ M 영역 포함)

| N | BASE 재사용 v1 → v1.1 (관측) | batch 16 재사용 차 | 비 B / T v1 → v1.1 (관측 m) |
|---|---|---|---|
| 6 | 0.825 → 0.833 (0.820) | ≤ 0.001 | 0.983 / 0.988 → 0.985 / 0.989 (0.990 / 0.983) |
| 8 | 0.736 → 0.770 (0.778) | ≤ 0.001 | 0.972 / 0.969 → 0.978 / 0.975 (0.980 / 0.972) |
| 10 | 0.634 → 0.697 (0.699) | ≤ 0.002 | 0.953 / 0.945 → 0.966 / 0.958 (0.963 / 0.952) |
| 12(개발) | 0.404 → 0.436 (0.484) | ≤ 0.007 | 0.891 / 0.875 → 0.894 / 0.879 (0.844 / 0.830) |

사후 대조(N = 6·8·10, 개발에 쓰지 않았으나 이미 알려진 관측 — **blind 아님**): 재사용 MAE 0.0142 → 0.0052, 비 Σ|예측 − m| 0.0483 → 0.0254.

- `requested_condition` 등: 해당 없음(분석·코드)

## 핵심 발견

1. **`class`** — **동시 실행 상한 아래의 FIFO slot pool에서 생존을 정하는 것은 평균 할당률이 아니라 할당과 부하의 결합이다**: 대기열이 있으면 할당이 완료와 짝을 이루어 older release가 여유를 만들지 못하고, heavy-tailed gap에서는 지금 엔진에 있는 세션이 이후 할당의 대부분을 내 부하가 지속된다. 두 효과가 상수율 Poisson 근사의 오차를 반대 방향으로 만들어 셀 평균에서 상쇄한다(N = 12 BASE: `a0 ≤ 6` 과소, `a0 = 7` 과대). 근거: 결합은 FCFS 대기와 allocation-FIFO 축출의 산술이고, 부하 지속성은 gap 분포의 모양(길이 편향)에서 나오며 둘 다 기판 구현에 의존하지 않는다. 크기는 이 부하의 것이다.
2. **`stack`** — **PS에서 서비스 길이가 비슷하면(생성 U(32, 256)) 완료 순서가 admission 순서에 가깝고, 그것이 T보다 오래된 항목의 release 시점을 정해 생존 수준을 크게 바꾼다**(N = 12 BASE 0.29 대 0.44). 지수 서비스 가정은 older 항목을 오래 붙잡아 생존을 과소 예측한다.
3. **`stack`** — v1.1은 개발 집합에서 재사용 MAE를 0.041 → 0.026으로 줄였으나 **비용 비 오차는 줄이지 못했다**(0.092 → 0.100). 남은 비 오차는 batch 16 구성의 평균 running 과소(B2)에서 온다 — 대기열 항 밖이다.

## 해석

- 사후 대조(N = 6·8·10)에서 v1.1이 v1보다 재사용·비 모두 좋았다는 것은 고무적이지만, 그 관측을 이미 알고 있었으므로 증거로 쓰지 않는다. blind 검증은 N = 14·16([TASK86](TASK86.md))이다.
- v1.1은 v1보다 입력이 많다(plan의 gap 분포 모양). 여전히 측정값은 쓰지 않는다 — gap 법칙은 plan(workload)에서 맞춘다.

## 확인되지 않은 사항

- 완료 순서의 중간 경우(서비스 CV가 0과 1 사이)의 정확한 확률 — 모형은 두 극단 중 하나를 고른다.
- batch 16 구성의 평균 running 과소의 원인(B2: 배타 prefill 동기화 또는 gap 모양과 무관하다는 무감응성 가정).
- LRU block pool(GPU)의 대기열 형태 — 거부로 남김.

## 실패 / 무효 시도

- **지수 gap v1.1**(첫 형태): N = 12 BASE 0.256(v1 0.404보다 나쁨). 초기 부하별 생존이 관측과 반대 방향 → 폐기하고 gap 위상 도입.
- **random 완료 순서**: 비용 비는 좋아 보였으나(0.016–0.034) BASE 재사용을 0.26–0.29로 크게 과소 — BASE를 비싸게 봐서 비가 맞은 것이라 채택하지 않음.
- **과다 thread**: 병렬 예측에서 numpy/scipy가 프로세스마다 64 thread를 띄워 load average 738까지 올랐다. `OMP_NUM_THREADS=1` 등으로 다시 실행했다(결과 무관, 시간만 손실).
- **KNOWN_PITFALLS 2 재발**: 과다 thread 예측 작업을 멈춘 뒤 남은 worker 확인에 `pgrep -f predict_v11.py | xargs kill`을 썼고, 명령 shell 자신이 pattern에 걸려 exit 144로 끝났다. 남은 worker는 이미 없었고 다른 프로세스 피해는 없었다. 올바른 방식(자기가 띄운 PID로 종료, task 중지 도구)을 두고 pattern을 쓴 실수다. device 작업이 아니어서 결과 영향은 없다.
- 두 예측 작업을 한 줄로 병렬 실행할 때 셸 변수 범위 실수로 두 번째 작업이 시작되지 않았다 → 따로 다시 실행.

## 연구 원칙에 미치는 영향

- 병렬 수치 계산은 BLAS thread를 1로 고정한다.
- KNOWN_PITFALLS 2는 device 밖의 계산 작업에서도 지킨다(이번 재발 기록).

## 다음 작업

- 작업 D: N = 14·16 blind 선등록과 측정([TASK86](TASK86.md) 예정).

## 재현 정보

- 위 명령. 산출(비추적) SHA256: `v11_dev/diag.json` `fd62c174…`, `v11_dev/eval.json`(random) `58fa1f91…`, `v11_dev/eval_admission.json` `0be96e13…`, `predict/v11_main_predictions.json` `5d94d892…`.
- 선등록 commit: 해당 없음(개발 집합, 판정 없음). v1.1 동결은 이 commit이며 N = 14·16 측정 전이다.
