# TASK89 — 시뮬레이터 통합: descriptor v2를 읽는 paged block pool 엔진, GPU wrapper와 정확 일치

## 상태

DONE

## 날짜

2026-10-01

## 목적

Advisor 지시문 07 작업 B. GPU GTASK07 발견 2: `continuum.sim`은 prefill 배타 실행, prompt token만 캐시, sequence slot pool을 전제로 해서 GPU를 표현할 수 없었고, GPU는 별도 wrapper(`gpu_mt_sim.py`)로 예측했다. 논문 주장("같은 시뮬레이터가 descriptor만 바꿔 두 기판을 예측")을 위해 GPU wrapper의 의미론을 **descriptor v2 field를 읽어 분기하는 형태로** `src/continuum/sim/`에 옮긴다. GPU 실제 인스턴스는 만들지 않고 테스트 전용 GPU descriptor로 검사한다.

**측정 0, device 0.**

## 배경

관련 TASK:

- GPU `GTASK07`(wrapper 작성, 발견 2), `GTASK09`(wrapper 예측 `PREDICTIONS.json`, SHA256 `1be9a991…`), `GTASK11`(sim LRU blind PASS) — `git archive 22b50f4` 읽기 전용 사본
- [TASK84](TASK84.md) — descriptor v2, `SimConfig.semantics`, 회귀 집합
- [TASK88](TASK88.md) — 같은 지시문의 작업 A

## 시작 상태

- [TASK88](TASK88.md)과 같은 작업 트리(작업 A 변경 위)

## 수행 내용

1. **descriptor v2 비용 class 3개**(`v2.py`): `FullGraphDecodeCost`(`F[b] + g·n`, ms), `PiecewiseMixedCost`(격자 안 혼합 step 증분, ms), `EagerStepCost`(격자 밖 decode 표와 prefill 증분 곡선, ms). 측정 채널의 단위(ms)로 담고 한 번만 초로 바꾼다 — 원 산출과 bit 단위로 맞추기 위해서다.
2. **paged 엔진** `src/continuum/sim/paged.py`: wrapper 알고리즘(step마다 running 먼저 → FCFS admission → 조회·hit touch → 할당 → 등록 → 반납)을 같은 연산 순서로 옮겼다. 분기는 전부 descriptor field: `prefill.execution`, 재사용 층의 `eviction_order`(`release_lru` / `allocation_fifo`, block 단위·tail 먼저)·`reserved_units`·`unit_tokens`·`capacity_units`, `semantics.{evictable_when, intra_request_loss, initial_free_order, resume_allocates_first, hit_protection, cacheable_tokens, kv_tokens_held, dummy_mode}`, `admission.{max_running, step_token_budget}`, `grid.{sizes, unit}`, `step_cost.{decode, mixed, eager}`. 구현 밖의 값은 `check_descriptor`가 거부한다. preemption이 필요해지면 `PreemptionNeeded`.
3. **`simulate()` dispatch**: v2 descriptor + `semantics="descriptor"` + `prefill.execution = mixed`면 paged 엔진, 그 밖은 기존 엔진(무변경). `SimConfig`에 `window_rule`·`slot_of`·`n_slots`(평가 구간 뒤 발행 중단, paged 엔진 전용; 기존 엔진은 거부).
4. **GPU 대조** `tests/gpu_sim_parity.py`: 테스트 전용 GPU descriptor(`test_descriptor_v2.gpu_test_descriptor` + GTASK05 비용 상수를 사본의 `gpu_cost.py`에서 import해 재입력 없음)로 GTASK09의 `sim_lru`·`sim_fifo` × `lo`·`hi` 예측을 모든 cell(N 20·22·24 × BASE·POOL·POOL+GRID, N 26 × BASE·POOL)에서 다시 계산하고 wrapper 산출과 field 단위 비교. 집계 정의는 wrapper의 `window_metrics`·`sim_cell` 재진술.
5. **NPU 회귀**: TASK84 회귀 집합 + TASK86 `PREDICTIONS_HI.json` 재계산.
6. [DESCRIPTOR_V2.md](DESCRIPTOR_V2.md) §7에 시뮬레이터가 읽는 field 표.

## 변경된 파일

- `src/continuum/substrate/v2.py`(비용 class 3개), `src/continuum/substrate/__init__.py`(export)
- `src/continuum/sim/paged.py`(신규), `src/continuum/sim/engine.py`(dispatch, `SimConfig` field 3개)
- `tests/gpu_sim_parity.py`(신규)
- `docs/research/DESCRIPTOR_V2.md`(§7), `docs/research/TASK89.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
git archive 22b50f4 experiments/gpu docs/research/gpu | tar -x -C <scratch>/gpu_repo
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 tests/gpu_sim_parity.py --gpu-root <scratch>/gpu_repo --out <scratch>/parity.json
bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_B
env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <scratch>/reg_base <scratch>/reg_B --semantics-check
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX_HI.json --ns 14,16 \
  --workers 30 --output <scratch>/reg_B/hiload_predictions.json      # == plans/main/PREDICTIONS_HI.json
env -u PYTHONPATH python3 tests/test_descriptor_v2.py
```

## 결과

### GPU wrapper 대비

| 비교 | 결과 |
|---|---|
| 44 항목(11 cell × `sim_lru`·`sim_fifo` × `lo`·`hi`), 비교 field: 재사용 수·률, token 재사용 비, hit 모양, h(n), padding, turn당 device 시간, 간섭, PIECEWISE·eager 혼합 step 수, mode 수, replicate별 6값, BASE 대비 비, replicate별 비, 순위 | **차이 0 — 전부 정확히 일치** |
| 첫 시험(한 plan): 이산 값 전부 일치, turn당 device 시간만 마지막 자리 차(≈ 2e-14 상대) | step 12,551개가 bit 단위로 같았고, 같은 wrapper를 이 host에서 돌리면 통합 시뮬레이터와 같은 값 → 차이는 **Python 3.12(GPU venv)의 보정 합 `sum()`** 대 3.10(이 host). 대조 harness가 3.12의 Neumaier 합을 재진술하자 정확 일치 |

사건 단위 차이: **없음**. wrapper와 통합 엔진이 어긋난 사건이 하나도 없으므로 "어느 쪽이 descriptor·source 감사에 맞는가"를 가를 사례도 없다.

### NPU 회귀

| 대상 | 결과 |
|---|---|
| TASK84 회귀 집합(표·`PREDICTIONS.json`·`PREDICTIONS_EXT.json`·R1–R5′·A4·self-check·sim 의미론) | 72 파일 차이 0, `descriptor` = 관측 스위치 105/105 run |
| TASK86 `PREDICTIONS_HI.json`(v1·v1.1·sim) 재계산 | **v1·sim 전 field byte 동일.** v1.1 17개 값이 마지막 자리(상대 ≤ 1e-13)만 달랐다 — 원인은 작업 B가 아니라 v1.1(TASK85) 코드 자체의 **비결정성**: SciPy `expm_multiply`의 1-norm 추정(`onenormest`)이 seed 없는 전역 `np.random`으로 시작 벡터를 뽑는다. 같은 코드를 두 번 실행해 0.21760915036481682 / 0.21760915036482772로 갈렸고, seed를 고정하면 같다. 저장된 값은 그 중 하나다. 판정 영향 없음(TASK87 오차 0.1 단위). 수정은 [TASK90](TASK90.md)(seed 고정 + 전역 상태 복원) |
| `tests/test_descriptor_v2.py` | 17/17 |

- `requested_condition` 등: 해당 없음(코드)

## 핵심 발견

1. **`class`** — **같은 시뮬레이터 코드가 descriptor field만 바꿔 두 기판(배타 prefill·slot pool의 NPU, 혼합 prefill·release LRU block pool의 GPU)을 예측한다.** GPU wrapper의 blind 예측 44 항목을 field 단위로 정확히 재현했고 NPU 산출은 그대로다. 근거: 분기 조건이 모두 serving stack의 설계 범주 field(prefill 실행 방식, 축출 순서, 조회 순서, 캐시 대상, 격자 단위)이고 기판 이름이 코드에 없다.
2. **`universal`** — **재현성 대조에서 인터프리터의 수치 의미론도 provenance다.** Python 3.12는 float `sum()`을 보정 합으로 바꿨다. 같은 코드·같은 입력이 3.10과 3.12에서 마지막 자리가 다르다. bit 단위 대조는 합 함수까지 맞춰야 한다.

## 해석

- GPU 에이전트는 실제 인스턴스로 `tests/gpu_sim_parity.py`의 `descriptor()`를 바꿔 같은 대조를 다시 할 수 있다(지시문 07 §4.4). 그 뒤 GPU 쪽 wrapper는 통합 시뮬레이터로 대체 가능하다(GPU 쪽 결정).
- paged 엔진은 preemption을 시뮬레이션하지 않는다. GPU 붕괴 영역(GTASK11 N = 26)에서 preemption이 생기는 구성이면 예측을 거부한다 — wrapper와 같은 범위다.

## 확인되지 않은 사항

- 실제 GPU 인스턴스로의 재확인(GPU 에이전트 몫)
- paged 엔진의 `allocation_fifo`는 GTASK09의 반사실 FIFO(hit가 순서를 바꾸지 않음)와 같은 정의다. 실제 FIFO 기판은 없다.

## 실패 / 무효 시도

- 첫 GPU 대조에서 마지막 자리 차 — 원인은 Python 합 의미론(위). 시뮬레이터 수정 없이 harness의 합 함수만 맞췄다.
- B2 진단 중 지시문 07 진행에서 `pgrep -f` 패턴을 감시 조건에 한 번 더 썼다(감시가 자기 자신과 일치해 끝나지 않음, 프로세스 종료는 없음). 바로 멈추고 작업 완료 알림으로 바꿨다 — KNOWN_PITFALLS 2의 확인 쪽 재발([TASK90](TASK90.md)에도 기록).

## 연구 원칙에 미치는 영향

- bit 단위 대조를 주장할 때 Python 버전과 합 의미론을 provenance에 적는다.

## 다음 작업

- 작업 C: B2 진단과 모형 v1.2([TASK90](TASK90.md)).

## 재현 정보

- 위 명령. GPU 사본 `22b50f4`, wrapper `PREDICTIONS.json` SHA256 `1be9a99129d245646b493e95b6fd3e7c71a45f9a64a8dd6fc917da30601e3a56`. 대조 산출 scratch(비추적).
- 선등록 commit: 해당 없음(측정·판정 없음)
