# TASK73 — 모형 v1: 기준 의미론, 상태 변수 d 근사, 개발 집합 보정

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 03 작업 A·C를 집행한다. (A1) descriptor에 생존 의미론 필드 3개를 추가하고, (A2) [TASK72](TASK72.md)에서 1,298/1,298을 맞힌 사건 재생을 모형 패키지의 **기준 의미론**으로 옮기며, (A3) v0 닫힌 형태의 두 결함을 상태 변수 하나로 다루는 **v1 근사**를 만들고, (A4) 개발 집합에서 보정만 보고한다. (C) KNOWN_PITFALLS와 원고 수정 후보를 기록한다.

**측정 0, device 0, compile 0. 판정 없음(A4는 개발 집합).** 시뮬레이터 동작 변경 0.

## 배경

관련 TASK:

- [TASK72](TASK72.md) — R5′ 사건 재생 1,298/1,298, 닫힌 형태 0.833, 즉시 release·PRE_EVICT 판별
- [TASK71](TASK71.md) — 모형 v0, [MODEL_V0.md](MODEL_V0.md)
- [TASK24](TASK24.md) — 지연 release(시뮬레이터 구현), [TASK63](TASK63.md) — dummy 관측, [TASK15](TASK15.md) — 할당 후 조회
- [TASK54](TASK54.md) — 원고 III-B-a 실패 73건의 run

## 시작 상태

- HEAD `e1f791e`([TASK72](TASK72.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. **A1**: `SubstrateDescriptor`에 `release_rule`·`dummy_mode`·`resume_allocates_first`를 `_OPTIONAL`로 추가(`None` = 측정 안 됨, 값이 있으면 provenance 필수, 값 검증). RBLN CA25 인스턴스에 `immediate`/`pre_evict`/`True`를 provenance(TASK72·TASK63·TASK15)와 함께 채웠다. 시뮬레이터는 읽지 않는다.
2. **A2**: `src/continuum/model/reference.py`(`FifoReplay`) 신설. 대조 스크립트의 재생 구현을 **삭제**하고 어댑터로 import하게 바꿨다. R1·R5′ 재실행 결과 산출 JSON이 계산 시각 외 **완전히 동일**.
3. **A3**: `src/continuum/model/survival_v1.py` — 상태 `(f, a, d)`의 정확한 추적기 `track_target`, 흡수 birth–death 근사 `survival_probability_v1`(균일화), steady-state 평균 `steady_state_survival`, LRU·block 형태 `lru_block_survival`. 명세 [MODEL_V1.md](MODEL_V1.md).
4. self-check 확장(v1 3항목), A4 스크립트 [`model_v1_dev.py`](../../experiments/npu/analysis/model_v1_dev.py), 표 M06.
5. **C**: [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 6번(runner `cached_tokens` 0 채움), INDEX 원고 수정 후보 2건.

## 변경된 파일

- `src/continuum/substrate/descriptor.py`, `experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py`
- `src/continuum/model/reference.py`, `src/continuum/model/survival_v1.py` (신규)
- `experiments/npu/analysis/model_v0_retro.py` (재생 → import), `model_v0_selfcheck.py` (v1 검사), `model_v1_dev.py` (신규), `make_tables.py` (M06)
- `results/tables/M06.{md,csv}`, `README.md`, `manifest.json`
- `docs/research/MODEL_V1.md` (신규), `KNOWN_PITFALLS.md`, `TASK73.md` (신규), `INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py
env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_retro.py --items r1,r5p --out-dir <scratch>   # 회귀
env -u PYTHONPATH python3 experiments/npu/analysis/model_v1_dev.py
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

## 결과

### A2 회귀

| 항목 | 이동 전 | 이동 후 |
|---|---|---|
| R1 | P1 29/29, P2 36/36, P3·P4 140/140 | 동일 (JSON 동일) |
| R5′ | 1,298/1,298, RESERVED 0.8475, 닫힌 형태 0.8328 | 동일 (JSON 동일) |

### A3 self-check (합성 입력)

| 검사 | 결과 |
|---|---|
| 정확 추적기 = 참조 재생 (무작위 일정 400개, dummy none·pre_evict) | **5,133/5,133** target 일치, 정의 불가 일정 0 |
| 퇴화 근사 = v0 Poisson 법칙 | 최대 차 2.2e-16 |
| 퇴화 결정론 = v0 (B1-1) | C 4종 × A 20개 전건 일치 |
| 기존 self-check (DP 1,200/1,200 등) | 전부 PASS |

### A4 개발 집합 (판정 없음)

실제 로그에 정확 추적기를 적용: **1,298/1,298**. 근사 평가는 gap이 있는 cell 998건(관측 재사용 675):

| 모형 | Brier | 예측 합 |
|---|---|---|
| 기후값 | 0.2189 | — |
| v1 기록된 초기 상태 | 0.1358 | 663.0 |
| v1 steady state | **0.1335** | 659.8 |
| v0 binomial | 0.1629 | 670.7 |
| v0 poisson | 0.1433 | 681.5 |

구간별 보정표는 `results/tables/M06.md`. v0 binomial은 0.1–0.4 구간에서 관측이 0.52–0.67로 역전돼 있고, v1은 그 구간이 0.12–0.52로 단조에 가깝다.

- `requested_condition`: 기존 artifact 재분석, `observed_condition`: 결손 0, `condition_reached`: `YES`

## 핵심 발견

1. **`universal`** — **생존은 상태 `(f, a, d)` 위의 전이로 정확히 쓰인다**: 가장 오래된 inactive 항목을 축출한다는 규칙만으로 `d`의 증감·T의 보호·흡수가 결정된다. 합성 5,133 target과 실제 1,298 재도착에서 참조 재생과 전건 일치한다. FIFO 대기열 산술이므로 기판 무관하다.
2. **`universal`** — **v0 닫힌 형태의 두 오류(T active 동안의 보호, 축출 순간의 `K_pin`)는 같은 변수 `d`의 두 경계 효과다** — `d = 0`에서 T가 active인지 아닌지, 그리고 `d`가 release로 늘어나는 시점.
3. **`class`** — **free-queue LRU에서는 `a ≡ 0`이고 `d`는 순수 사멸 과정이 된다**(release 순서, running block은 queue 밖). 근거: 설계 범주(할당 순서 대 release 순서)에서 나온다. 수치 검증은 없다.
4. **`stack`** — 이 기판의 의미론 3종(즉시 release, PRE_EVICT, 할당 후 조회)이 descriptor에 provenance와 함께 기록됐다.

## 해석

- 개발 집합에서 v1의 Brier 이득(0.134 대 v0 최선 0.143)은 작다. 동시 시작 workload에서 λ 일정 가정이 깨지므로 예상된 범위다. v1이 기여하는 것은 성적보다 **정확한 추적기와 같은 구조를 공유하는 근사**라는 점이다 — 근사 오차의 원인이 전이 규칙이 아니라 할당 과정(Poisson, λ 일정)에 있다고 특정할 수 있다.
- 실제 초기 상태를 넣은 v1(0.1358)이 steady-state 초기 상태의 v1(0.1335)보다 오히려 약간 나쁘다. 초기 상태가 아니라 λ·μ 가정(Poisson, 일정률)이 오차를 지배한다는 뜻으로 읽는다(hypothesis).

## 확인되지 않은 사항

- LRU·block 형태(`lru_block_survival`)의 수치 타당성 — GPU 데이터 없음
- v1의 steady-state 성적 — multi-turn 실험 전까지 `UNKNOWN`

## 실패 / 무효 시도

self-check 초안이 `V1.track_target` 대신 자체 재구현을 호출하고 있어 고쳤다(모듈 함수를 직접 검사하도록). 결과는 같았다.

## 연구 원칙에 미치는 영향

- KNOWN_PITFALLS 6번 추가. `AGENTS.md`의 "함정 5종" 문구는 이번에 고치지 않았다(agent 규칙 파일 — 사용자 판단 사항으로 보고).

## 다음 작업

- 지시문 03 작업 B(시뮬레이터 의미론 스위치, 선등록 후 계산), 작업 D(multi-turn 설계 초안).

## 재현 정보

- 위 명령. 산출 `results/npu/stage3/model_v1_dev/dev.json`(비추적), 표 `results/tables/M06`.
- 선등록 commit: 해당 없음(판정 없는 개발 집합 평가).
