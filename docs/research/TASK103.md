# TASK103 — context 길이 비용의 공유 코드 반영 (descriptor `context_cost`)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 12 작업 A. [TASK98](TASK98.md)의 `SimConfig.decode_cost_fn` hook 대신 context 길이 비용을 **descriptor의 step 비용 형태**로 넣는다. NPU는 bucket 기준(F1 `f(b) + βn + c·ΣL`), GPU는 기존 token 수·mode 기준 가격에 context 항을 더한다. 계수에는 출처(TASK97·100, GTASK18)를 provenance로 붙이고, 값이 없으면 기존 동작 그대로여야 한다.

**측정 0.**

## 배경

- [결정 13](INDEX.md#결정-13--지시문-12-결정-시뮬레이터-위치와-통합): 권장 비용 입력 = 예측 대상과 같은 context 길이에서 잰 decode 비용
- [TASK97](TASK97.md)·[TASK100](TASK100.md)(NPU c), GTASK18(GPU c = 0.212 µs/token), GTASK20(GPU blind, `gpu_mt_sim.py`의 `step_cost` hook)
- [TASK89](TASK89.md)(통합 시뮬레이터, GTASK09 parity), [TASK84](TASK84.md)(descriptor v2 회귀)

## 시작 상태

- HEAD `d2bde33`(= `origin/main`), `?? .idea/`만. GPU branch `origin/gpu-a6000` = `614a4c4`.

## 수행 내용

1. 변경 전 HEAD 코드로 회귀 기준 산출(`descriptor_v2_regression.sh` → `reg_base`)을 먼저 만들었다(import 완료 확인 후 코드 수정 시작).
2. `substrate/v2.py`: `ContextCost(per_token, unit ∈ {s, ms}, reference_tokens_per_decode = 0)`와 `SubstrateDescriptorV2.context_cost`(기본 `None`, `unknown_paths()`에 나오지 않음, 값이 있으면 provenance `"context_cost"` 필요). `substrate/__init__.py` export.
3. `substrate/descriptor.py` `StepCostModel`: 음의 `marginal_s_per_request` 허용 — 모든 bucket에서 `fixed + intercept + marginal·bucket > 0`일 때만(NPU F1 β가 −0.005 – −0.069 ms). 양수 값의 기존 검사는 그대로.
4. `sim/engine.py`(배타 prefill 엔진, 단위 s): decode step = `step_time_s(n) + c·(Σ(prompt + 생성) − n·ref)`. `sim/paged.py`(혼합 prefill 엔진, 단위 ms): decode 요청이 있는 step = `(step_ms + c·(Σcomputed − decodes·ref)) / 1e3`. 단위가 엔진과 다르면 거부한다. `decode_cost_fn`은 TASK98·101 commit된 script 재현용으로 남기고(deprecated 표기), `context_cost`와 함께 쓰면 오류.
5. 회귀·재계산 검사(아래), `DESCRIPTOR_V2.md` §8 추가.

## 변경된 파일

- `src/continuum/substrate/{v2.py, descriptor.py, __init__.py}`, `src/continuum/sim/{engine.py, paged.py}`
- `tests/ctx_descriptor_npu.py`, `tests/gpu_ctx_parity.py`(신규)
- `docs/research/DESCRIPTOR_V2.md`(§2, §8), `docs/research/TASK103.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
SP=<scratch>
bash experiments/npu/analysis/descriptor_v2_regression.sh $SP/reg_base      # 변경 전 HEAD d2bde33
bash experiments/npu/analysis/descriptor_v2_regression.sh $SP/reg_B         # 변경 후
env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py $SP/reg_base $SP/reg_B
cd experiments/npu/stage3
python3 predict_v11.py --index INDEX_HI.json --ns 14,16 --workers 30 --output $SP/r_hi.json   # vs PREDICTIONS_HI.json
python3 predict_simblind.py --output $SP/r_sim.json                                             # vs PREDICTIONS_SIM.json
python3 predict_ctxblind.py --output $SP/r_ctx.json                                             # vs PREDICTIONS_CTX.json
cd -
python3 tests/test_descriptor_v2.py
git archive 22b50f4 experiments/gpu docs/research/gpu | tar -x -C $SP/gpu_repo09
python3 tests/gpu_sim_parity.py --gpu-root $SP/gpu_repo09 --out $SP/parity09.json
git archive origin/gpu-a6000 experiments/gpu docs/research/gpu | tar -x -C $SP/gpu_repo
python3 tests/gpu_ctx_parity.py --gpu-root $SP/gpu_repo --out $SP/gpu_ctx_parity.json
python3 tests/ctx_descriptor_npu.py
```

(모두 `OMP_NUM_THREADS=1 env -u PYTHONPATH`.)

## 결과

| 검사 | 결과 |
|---|---|
| TASK84·89 회귀 집합(표, multi-turn 예측, R1–R5′, 개발 집합, self-check, sim 의미론) | **72 파일 차이 0** |
| TASK93 `PREDICTIONS_SIM.json`, TASK101 `PREDICTIONS_CTX.json` 재생성 | **byte 동일** |
| TASK86 `PREDICTIONS_HI.json` 재생성 | v1·sim 필드 동일. v1.1 필드 17개가 상대 5e-14 이내로 다름 — 알려진 SciPy `onenormest` 비결정성(파일은 TASK90의 결정적 `_expm` 수정 전에 계산됨, [결정 10](INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정)-3). v1.1은 시뮬레이터를 쓰지 않아 이번 변경과 무관 |
| `tests/test_descriptor_v2.py` | PASS(RBLN unknown field 목록 그대로) |
| GTASK09 parity(context 없음, paged 엔진) | **44 cell 차이 0** |
| **NPU**: TASK101 주 예측기를 descriptor 경로(F1 decode `StepCostModel` + `context_cost` unit s)로 재계산 | **6 cell 모든 field 정확 일치** |
| **GPU**: GTASK20 주 예측기(`ctx`, N = 25·28 × lo·hi)를 통합 시뮬레이터 + 테스트 GPU descriptor + `context_cost`(2.120e-4 ms/token, ref 128)로 재계산 | **12 cell 모든 field 정확 일치**(재사용, 가격 turn당, replicate별, h_decode, wall/price, BASE 대비 비, 순위) |

## 핵심 발견

1. 두 기판의 context 비용이 같은 descriptor field 하나(`context_cost`)로 표현되고, 각 기판의 blind 주 예측기를 bit 단위로 재현한다. 차이는 기본 decode 비용(NPU: context 항과 함께 적합한 F1, 기준 0; GPU: 짧은 context 가격, 기준 128)과 단위뿐이다.

## 해석

- 없음(코드 작업).

## 확인되지 않은 사항

- 없음.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 시뮬레이터 비용 입력은 descriptor field로만 바꾼다(실험 script의 hook이 아니라). `decode_cost_fn`은 재현용으로만 남는다.

## 다음 작업

- GPU branch 통합([TASK104](TASK104.md)), 결과 색인·표·그림([TASK105](TASK105.md)).

## 재현 정보

- 위 명령. 기준 산출은 변경 전 HEAD `d2bde33`, GPU parity 입력은 `22b50f4`(GTASK09)·`614a4c4`(GTASK20) archive 복사본.
