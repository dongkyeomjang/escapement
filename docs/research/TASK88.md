# TASK88 — `lru_block_survival` underflow 수정 (log 공간)

## 상태

DONE

## 날짜

2026-10-01

## 목적

Advisor 지시문 07 작업 A. GPU GTASK07 발견 3: neutral `continuum.model.survival_v1.lru_block_survival`은 Poisson 평균이 약 745를 넘으면 `exp(-mean)`이 0으로 underflow되어, `d0`가 얼마든 "전부 손실"을 낸다. GPU 입력(할당률 × 수십 초 gap)이 이 영역에 들어간다. log 공간 계산으로 고친다.

**측정 0, device 0.**

## 배경

관련 TASK:

- GPU `GTASK07`(발견 3, wrapper의 log 공간 `lru_survival`), `GTASK09`(그 입력이 쓰인 예측) — `git archive 22b50f4`로 읽기 전용 사본을 꺼내 실행만 함
- [TASK73](TASK73.md) — `lru_block_survival` 도입(검증 없음, LRU block 형태)
- [TASK84](TASK84.md) — 회귀 집합

## 시작 상태

- HEAD `235bad2`([TASK87](TASK87.md), `origin/main`과 같음), `git status --short`: `?? .idea/`만
- `origin/gpu-a6000` `22b50f4`(GTASK11)

## 수행 내용

1. `lru_block_survival`: Poisson 평균 < 600(`_LOG_SPACE_MEAN`, wrapper와 같은 문턱)이면 **기존 점화식을 그대로**, 이상이면 항마다 `exp(-mean + k·log mean − lgamma(k+1))`로 계산. 꼬리 질량을 마지막 항에 더하는 규칙과 손실 사상은 그대로.
2. NPU 회귀: TASK84 회귀 집합 재생성·비교.
3. GPU 대조: wrapper(`gpu_mt_model.py` 사본)의 해석 경로를 GTASK09 plan 20개 × 모든 구성 × `lo`·`hi`로 돌리며 `lru_survival` 호출마다 입력·wrapper 출력을 기록하고, 고친 neutral 함수 출력과 비교(`scratch/underflow_check.py`).

## 변경된 파일

- `src/continuum/model/survival_v1.py`(`lru_block_survival` 분기, `_LOG_SPACE_MEAN`)
- `docs/research/TASK88.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_A
env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <scratch>/reg_base <scratch>/reg_A --semantics-check
git archive 22b50f4 experiments/gpu docs/research/gpu | tar -x -C <scratch>/gpu_repo     # 읽기 전용 사본
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 <scratch>/underflow_check.py
```

## 결과

| 회귀 | 결과 |
|---|---|
| NPU TASK84 회귀 집합(표·예측·R1–R5′·A4·self-check·sim 의미론) | **72 파일 차이 0**(시각 key 예외 규칙 그대로), `descriptor` = 관측 스위치 105/105 run |
| 비-underflow 영역(평균 < 600): 수정 전 = 수정 후 | 같은 코드 경로 — wrapper 출력과 **최대 차 0.0**(1,434,722 호출) |
| underflow 영역(평균 ≥ 600, 최대 8,918): 수정 후 대 wrapper log 공간 | **최대 절대 차 1.7e-13**(685,638 호출) |

NPU 산출물은 `lru_block_survival`을 쓰지 않는다(호출처 grep 0) — byte 동일은 예상대로다.

- `requested_condition` 등: 해당 없음(코드)

## 핵심 발견

1. **`universal`** — **neutral 모형 함수의 수치 영역은 기판 입력으로 다시 확인해야 한다.** NPU 입력(slot 단위, 작은 λ)에서 드러나지 않던 underflow가 GPU block 단위 입력(평균 수천)에서 결과를 "전부 손실"로 바꿨다(GTASK07 발견 3). 함수의 정의역을 입력 크기 기준으로 시험해야 한다.

## 해석

- wrapper와의 1.7e-13 차는 wrapper가 `k < d0 − 4000` 항을 생략하는 근사(그 항은 underflow로 0)와 합 순서에서 온다.

## 확인되지 않은 사항

없음.

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- GPU wrapper의 log 공간 우회는 이제 필요 없다(GPU 에이전트가 neutral 함수로 되돌릴 수 있음, GPU 쪽 결정).

## 다음 작업

- 작업 B: 시뮬레이터 통합([TASK89](TASK89.md)).

## 재현 정보

- 위 명령. scratch 산출(비추적). GPU 사본은 `22b50f4`.
- 선등록 commit: 해당 없음(측정·판정 없음)
