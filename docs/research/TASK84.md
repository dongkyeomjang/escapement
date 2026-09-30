# TASK84 — SubstrateDescriptor v2: 층 목록·규칙 field·값 출처, legacy 회귀, GTASK04 무wrapper 재현

## 상태

DONE

## 날짜

2026-09-30

## 목적

Advisor 지시문 06 작업 B. GPU branch의 `DESCRIPTOR_REQUIREMENTS.md`(GTASK06)를 입력으로 `SubstrateDescriptor`를 개편해 두 기판(RBLN NPU, A6000 GPU)을 함께 표현한다. RBLN 인스턴스를 v2로 옮기고, 시뮬레이터·모형이 의미론을 descriptor에서 읽게 하되 원고 시점 동작은 `legacy` 설정으로 bit 단위로 보존한다. GPU 인스턴스는 만들지 않고(결정 7), 테스트 전용 descriptor로 GTASK04 60개 예측을 wrapper 없이 재현하는지 확인한다.

**측정 0, device 0.**

## 배경

관련 TASK:

- GPU `GTASK06`(요구사항 문서), `GTASK04`(첫 교차 기판 blind 예측 60/60, wrapper 사용), `GTASK01`·`GTASK02`(GPU 의미론·값) — `git show origin/gpu-a6000:`으로 읽음
- [TASK16](TASK16.md) — descriptor 도입, [TASK73](TASK73.md) — 의미론 field 3개, [TASK74](TASK74.md) — 시뮬레이터 의미론 스위치
- [TASK83](TASK83.md) — 결정 8-4(의미론은 descriptor v2로, `legacy` 보존)

## 시작 상태

- HEAD `339557a`([TASK83](TASK83.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. **변경 전 회귀 기준 산출**(`descriptor_v2_regression.sh` → scratch `reg_base`): 표 전부, `predict_main.py`·`predict_ext.py`, `model_v0_retro.py`(R1–R5′·R4·R5), `model_v1_dev.py`(A4), self-check, `sim_semantics_effect.py`. 저장된 산출과 대조해 기준 자체가 재현됨을 확인(표·예측·A4 byte 동일, R1–R5 시각 key 외 동일).
2. **`src/continuum/substrate/v2.py`**(신규): `SubstrateDescriptorV2`(`PoolLayer` 목록 + `reuse_layer`, `Semantics`, `Admission`, `Grid`, mode별 `step_cost`, `PrefillSpec`, `Pipeline`), 점 경로 provenance 강제, `None` = 미확정, `NA` = 해당 없음(값), `unknown_paths()`, `with_config()`(보간 규칙은 `config_search.descriptor_for`와 bit 동일), `legacy_view()`(v1 객체).
3. **RBLN 인스턴스 이전**: `rbln_ca25_vllm_rbln_0111.py`에 `RBLN_CA25_V2`(모든 field provenance)를 두고, 기존 이름 `RBLN_CA25_VLLM_RBLN_0111`은 `RBLN_CA25_V2.legacy_view()`로 바꿨다. v1 field는 provenance 문구 외 전부 같다(pickle 대조). 파일 실행 출력 동일.
4. **시뮬레이터**: `SimConfig.semantics`(`"legacy"` 기본 | `"descriptor"`). `descriptor`는 v1·v2 모두에서 규칙을 읽고, 구현하지 않은 규칙은 거부한다. `simulate`가 v2 descriptor를 받는다.
5. **모형**: `FifoReplay.for_descriptor`가 v2를 받는다. 신규 `continuum.model.protocol.sequential_protocol` — 순차 프로토콜의 생존·hit를 v2 규칙만으로 계산(기존 `survival` 함수 import, `survival.py` 무수정).
6. **테스트** `tests/test_descriptor_v2.py`(pytest 없이 실행): v1 view, 구성 변형, RBLN 절벽, GPU 테스트 descriptor로 GTASK04 60 trial, 시뮬레이터 거부, replay 동일, provenance 강제.
7. **변경 후 회귀**와 비교(`descriptor_v2_compare.py`), 문서 [DESCRIPTOR_V2.md](DESCRIPTOR_V2.md)(구조·요구사항 대응표·사용법).

## 변경된 파일

- `src/continuum/substrate/v2.py`(신규), `src/continuum/substrate/__init__.py`(v2 export)
- `src/continuum/model/protocol.py`(신규), `src/continuum/model/__init__.py`(export), `src/continuum/model/reference.py`(`for_descriptor` v2)
- `src/continuum/sim/engine.py`(`SimConfig.semantics`, `_descriptor_rules`, v2 입력)
- `experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py`(v2 인스턴스, v1은 파생)
- `experiments/npu/analysis/{descriptor_v2_regression.sh, descriptor_v2_compare.py}`(신규)
- `tests/test_descriptor_v2.py`(신규)
- `docs/research/{DESCRIPTOR_V2.md, TASK84.md}`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_base     # 변경 전 (HEAD 339557a)
bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_after2   # 변경 후 (최종 코드)
env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <base> <after> --semantics-check
env -u PYTHONPATH python3 tests/test_descriptor_v2.py
```

## 결과

### 회귀 (지시문 06 §4.4)

| 대상 | 결과 |
|---|---|
| `legacy` 설정 표 `results/tables/` 59개(T·S·A·B·M 계열, md·csv·README) | **byte 동일** |
| 표 `manifest.json` | 생성 시각·HEAD·dirty 외 동일 |
| TASK80 `PREDICTIONS.json`(세 예측기) 재계산 | **byte 동일**(저장본과도) |
| TASK81 `PREDICTIONS_EXT.json` 재계산 | **byte 동일** |
| TASK72 R1–R5′·R4·R5 JSON 6개 + `run_meta` | 파일 안의 `computed_at`·`seconds`·`started` 외 **내용 동일** |
| TASK73 A4 `dev.json` | **byte 동일** |
| TASK74 sim 의미론 산출 | **byte 동일** |
| model self-check | 소요 시간 key(`*_seconds`) 외 동일, `SELF-CHECK PASS` |
| 합계 | 72 파일: 63 byte 동일, 9 시각·소요 시간 key만 다름(원리상 byte 동일 불가) |
| `semantics="descriptor"`(RBLN v2) 대 명시적 관측 스위치(`immediate`+`pre_evict`) | **75/75 run 동일**(step·요청·축출 기록) |

byte 동일이 아닌 결과 산출은 없다 → 작업 C로 진행 가능.

### GTASK04 60개 재현 (지시문 06 §4.2)

GPU 테스트 descriptor(요구사항 문서 GPU 열, `num_gpu_blocks` 801, `max_num_seqs` 1) + `sequential_protocol` — **wrapper 없이 60/60 일치**: 예측 hit token, T의 캐시 block 축출 수, `u_T`, `u_bg`, overflow 다섯 값 모두. wrapper가 넣던 입력이 descriptor field로 옮겨졌다: 생성 token 보유(`kv_tokens_held = computed`), 캐시 대상(`cacheable_tokens = computed`), release LRU의 FIFO 등가(`eviction_order = release_lru` + `initial_free_order = never_used_first`), 꼬리부터 손실(`intra_request_loss = tail_first`), 조회 후 할당과 hit 보호(`resume_allocates_first = False`, `hit_protection = touch_before_alloc`).

### 테스트 `tests/test_descriptor_v2.py`

17항목 전부 ok: v1 view(스칼라·step·prefill·provenance key), `with_config` = `descriptor_for` 3구성, RBLN 절벽(배경 500·1,000·2,000·4,000 token 모두 B = 7에서 1,920 → 0), GTASK04 60/60, 시뮬레이터가 GPU 규칙 6개를 명시적으로 거부, `FifoReplay` v1 = v2, RBLN 미확정 field 목록, provenance 누락 거부.

### RBLN v2 미확정 field (`None`)

`semantics.failed_admission_evicts`, `semantics.cache_registration`, `semantics.dummy_ceiling`, `admission.step_token_budget`, `admission.admission_requires_full_prompt`, `pipeline.in_flight_batches`, `pipeline.startup_nonrequest_steps`.

- `requested_condition` 등: 해당 없음(코드·회귀)

## 핵심 발견

1. **`class`** — **두 기판의 순차 생존 차이는 descriptor 규칙 field 7개(축출 순서, 초기 free 순서, 요청 내부 손실, 조회·할당 순서, hit 보호, 보유 token, 캐시 대상)로 모두 적히고, 같은 모형 코드가 그 field만 읽어 두 기판의 관측을 재현한다**(RBLN 절벽 4 배경 크기, GPU 60/60). 근거: field는 가속기가 아니라 serving stack의 pool 설계 선택(할당 대 release 순서, slot 대 block, 조회 순서)이며, 코드에 기판 이름이나 기판별 분기가 없다. GTASK06 발견 1(5개)에 초기 free 순서·보유 token이 더해졌다.
2. **`universal`** — **규칙을 descriptor로 옮기면서 기존 동작을 `legacy` 설정으로 격리하면 과거 산출을 bit 단위로 보존할 수 있다**(63/72 byte 동일, 나머지는 시각 key). 새 코드 경로(`descriptor`)가 옛 명시 스위치와 75/75 동일함을 함께 보여야 두 경로의 등가가 선다.

## 해석

- 결정 8-4는 "시뮬레이터가 descriptor를 읽는다"이지만, 기본값을 `descriptor`로 바꾸면 30개 넘는 과거 script가 조용히 다른 의미론으로 돈다. 그래서 **코드 기본값은 `legacy`로 두고**, 새 예측 코드가 `semantics="descriptor"`를 명시하도록 했다. 이것이 결정 8-4의 의도와 맞는지 Advisor 확인이 필요하다(결정 요청 1).
- 시뮬레이터는 GPU 규칙을 구현하지 않는다. GPU steady-state 시뮬레이션이 필요해지면 release LRU·tail-first·혼합 prefill을 새로 구현해야 한다(범위 밖).

## 확인되지 않은 사항

- NPU 미확정 field 7개(측정 TASK 미개설).
- GPU 테스트 descriptor의 step·prefill 비용(GTASK05 값은 GPU 인스턴스 몫이라 넣지 않았다).

## 실패 / 무효 시도

- 첫 설계에서 `eviction_order`를 `Semantics`에 두었다가, 층 0(inner LRU)과 층 1(outer FIFO)의 순서가 달라 v1 view의 `inner_eviction_policy`를 표현할 수 없어 `PoolLayer`로 옮겼다(작성 중 수정).
- `reuse_layer`의 provenance 누락을 생성자가 거부했다 — 강제 규칙이 의도대로 동작했다.
- 시뮬레이터가 GPU descriptor를 거부하긴 했으나 v1 변환 오류로 먼저 실패해 거부 사유가 부정확했다 → 규칙 검사를 변환 앞으로 옮겼다.
- 첫 비교에서 `run_meta.json`·self-check가 달랐다 — 둘 다 실행 시각·소요 시간 key였다. 비교 규칙에 시각 key 예외를 명시하고 byte 동일 파일 수를 따로 셌다.

## 연구 원칙에 미치는 영향

- 새 기판 값은 v2 인스턴스로 기록하고, 모든 값에 점 경로 provenance를 단다. 미확정은 `None`, 해당 없음은 `NA` 값.
- 새 시뮬레이터 예측은 `SimConfig(semantics="descriptor")`로 한다.

## 다음 작업

- 작업 C: 모형 v1.1 대기열 항([TASK85](TASK85.md) 예정), v2 위에서.

## 재현 정보

- 위 명령. 회귀 산출은 scratch(비추적). 변경 전 기준은 HEAD `339557a`에서 산출.
- 선등록 commit: 해당 없음(측정·판정 없음)
