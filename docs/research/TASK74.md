# TASK74 — 시뮬레이터 의미론 교정 스위치와 계통 오차 설명력

## 상태

DONE

## 날짜

2026-09-29

## 판정

**`PARTIAL`** (선등록 [SIM_SEMANTICS_PREREG.md](SIM_SEMANTICS_PREREG.md), commit `86dcf37c`, 2026-09-29 17:33:06 +0900 → 계산 시작 17:33:10 +0900).

| 기준 | 결과 |
|---|---|
| C1 평균 \|e\|(둘 다) < 평균 \|e\|(기존) | **성립** — 0.01674 < 0.01694 |
| C2 baseline 재사용 4건 중 3건 이상 차가 줄거나 같음 | **성립** — 4/4 같음(1, 0, 2, 1) |
| C3 평균 \|e\| 25 % 이상 감소 (≤ 0.01270) | **불성립** — 감소 1.2 % |

**실질 결론: release 규칙·dummy 의미론은 계통적 양의 오차의 원인이 아니다.** 두 스위치를 모두 켜도 8개 비교 전부 `e > 0`이고 평균 |e|가 1.2 %만 줄었다. 사전 예측(`FAIL`)은 판정 이름으로는 빗나갔으나(C1이 0.0002 차로 성립) 결론 방향은 같다.

**측정 0, device 0.** 시뮬레이터 기본값(`deferred`/`off`)은 바꾸지 않았다.

## 목적

Advisor 지시문 03 작업 B. [TASK72](TASK72.md)가 밝힌 시뮬레이터–기판 의미론 차이 두 곳(지연 release, dummy 모형)이 원고 IV-E의 계통적 양의 예측 오차(Table IX 8개 모두 `e > 0`)와 관련 있는지 확인한다.

## 배경

관련 TASK:

- [TASK72](TASK72.md) — 사건 재생: 즉시 release 1.000 대 지연 0.934, PRE_EVICT 1.000 대 RESERVED 0.847
- [TASK73](TASK73.md) — descriptor 의미론 필드
- [TASK24](TASK24.md) — 시뮬레이터 지연 release, [TASK63](TASK63.md)·[TASK69](TASK69.md) — dummy 관측과 `reserved` 스위치
- [TASK35](TASK35.md), [TASK36](TASK36.md) — 비교 8개와 실측 채널 A′, [TASK68](TASK68.md) — 재도착 되먹임

## 시작 상태

- HEAD `a2d6f1f`([TASK73](TASK73.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. `SimConfig.release_rule`(`deferred` 기본 / `immediate`), `SimConfig.dummy_mode`(`off` 기본 / `reserved` / `pre_evict`)와 `OuterBlockPool.immediate_release`·`pre_evict()`를 추가했다. 기존 `dummy_block=True`는 `reserved`와 같다.
2. **회귀**: 기본값에서 `make_tables.py --all`의 표 28개 `.md`/`.csv`가 **byte 동일**(T07·S07·S08 포함), 대조 221건 불일치 0. self-check PASS.
3. 선등록 문서·스크립트·스위치를 commit(`86dcf37`)한 뒤 `sim_semantics_effect.py`를 1회 실행했다.
4. 표 M07 등록.

## 변경된 파일

선등록 commit `86dcf37`: `src/continuum/sim/cache.py`, `src/continuum/sim/engine.py`, `experiments/npu/analysis/sim_semantics_effect.py`(신규), `docs/research/SIM_SEMANTICS_PREREG.md`(신규)

기록 commit: `experiments/npu/analysis/make_tables.py`(M07), `results/tables/M07.{md,csv}`·`README.md`·`manifest.json`, `docs/research/TASK74.md`, `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/sim_semantics_effect.py
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

## 결과

`e = 실측 A′ 비 − 시뮬레이터 비`(양수 = 절감 과대 예측). 블록 0·1·2 합.

| seed | N | arm | 실측 비 | 기존 | immediate | pre_evict | **둘 다** | reserved(TASK69) |
|---|---|---|---|---|---|---|---|---|
| 20261000 | 6 | BATCHONLY | 0.9793 | +0.0183 | +0.0260 | +0.0183 | +0.0183 | +0.0217 |
| 20261000 | 6 | TUNED | 0.9660 | +0.0194 | +0.0270 | +0.0194 | +0.0194 | +0.0228 |
| 20261000 | 8 | BATCHONLY | 0.9175 | +0.0074 | +0.0070 | +0.0074 | +0.0070 | +0.0330 |
| 20261000 | 8 | TUNED | 0.9028 | +0.0058 | +0.0054 | +0.0058 | +0.0054 | +0.0310 |
| 20261000 | 10 | BATCHONLY | 0.9552 | +0.0339 | +0.0396 | +0.0339 | +0.0335 | +0.0515 |
| 20261000 | 10 | TUNED | 0.9264 | +0.0364 | +0.0419 | +0.0364 | +0.0360 | +0.0534 |
| 20261100 | 6 | BATCHONLY | 0.9941 | +0.0066 | +0.0068 | +0.0066 | +0.0066 | +0.0066 |
| 20261100 | 6 | TUNED | 0.9789 | +0.0076 | +0.0077 | +0.0076 | +0.0076 | +0.0076 |
| **평균 \|e\|** | | | | **0.01694** | 0.02017 | 0.01694 | **0.01674** | 0.02845 |
| 양수 e | | | | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |

`BASE` 재사용(시뮬레이터, 괄호는 `BASE` 축출 수) 대 실측:

| seed | N | 실측 | 기존 | immediate | pre_evict | 둘 다 | reserved |
|---|---|---|---|---|---|---|---|
| 20261000 | 6 | 15/18 | 14 (12) | 12 (12) | 14 (15) | 14 (15) | 13 (12) |
| 20261000 | 8 | 9/24 | 9 (24) | 9 (24) | 9 (27) | 9 (27) | 6 (24) |
| 20261000 | 10 | 9/30 | 7 (36) | 5 (36) | 7 (39) | 7 (39) | 6 (36) |
| 20261100 | 6 | 17/18 | 16 (12) | 15 (12) | 16 (15) | 16 (15) | 16 (13) |

사전 예측 대조: `immediate`만 — 평균 |e| 증가 **적중**, baseline 이하 **적중**. `pre_evict`만 — 변화 < 0.003 **적중**(0 변화). **둘 다 — "평균 |e| 증가" 예측은 빗나감**(0.0002 감소). 종합 `FAIL` 예측 대 판정 `PARTIAL`.

- `requested_condition`: 등록된 5 조합 × 4 셀 × 3 arm × 3 블록 시뮬레이션
- `observed_condition`: 전부 완료, 예외 0
- `condition_reached`: `YES`

## 핵심 발견

1. **`stack`** — **이 기판의 관측 의미론(즉시 release + PRE_EVICT)으로 시뮬레이터를 돌려도 계통적 양의 오차는 남는다**(8/8 양수, 평균 |e| 0.0169 → 0.0167). 원인은 다른 곳에 있다.
2. **`stack`** — **두 의미론은 서로를 상쇄한다.** 즉시 release만 켜면 `BASE` 재사용이 줄고(15→12 계열 방향, N=10 7→5) 오차가 커지지만, PRE_EVICT를 함께 켜면 재사용이 기존 값으로 돌아온다. PRE_EVICT는 `BASE`마다 축출을 블록당 1건(trailing) 늘릴 뿐 재사용은 바꾸지 않는다(+3 = 3 블록) — [TASK58](TASK58.md)의 `+1` 산술과 같다.
3. **`stack`** — **관측 의미론에서도 시뮬레이터 `BASE` 재사용은 실측보다 적다**(14/9/7/16 대 15/9/9/17). 재사용 부족은 `BASE` 비용 과대 → arm 비 과소 → `e > 0`으로 직결되므로, **계통 오차의 유력 경로는 의미론이 아니라 시뮬레이터 일정(도착·admission 순서·시각)**이다(hypothesis).
4. **`stack`** — `reserved`(TASK69)는 모든 셀에서 오차를 키운다(평균 0.0284) — TASK72의 RESERVED 기각과 같은 방향이다.

## 해석

- [TASK72](TASK72.md)에서 **실제 일정** 위의 재생은 즉시 release를 요구했지만, **시뮬레이터 일정** 위에서는 즉시 release 단독이 재사용을 줄였다. 같은 규칙이 다른 일정에서 다른 결과를 낸다 — 시뮬레이터의 일정이 실제와 다르다는 독립 증거다.
- 다음 후보 순서(선등록 그대로): (1) `BASE` 재사용 부족의 원인 — 동시 도착 admission 순서 가정과 client overhead 0, (2) 미측정 bucket 비용, (3) 채널 A′ 고정 오버헤드, (4) 재도착 되먹임. (1)은 R5′ 재생 도구로 실제 admission 순서를 시뮬레이터 `admission_priority`에 넣어 바로 시험할 수 있다(새 측정 불필요).

## 확인되지 않은 사항

- 기본값을 관측 의미론으로 바꿀지 — **별도 결정 사항**(결과가 거의 같아 예측 수치에는 영향이 작다: 8개 비의 변화 ≤ 0.0004)
- `BASE` 재사용 부족의 실제 원인

## 실패 / 무효 시도

없음. 계산 1회, 재실행 없음.

## 연구 원칙에 미치는 영향

- 판정 이름(`PARTIAL`)과 실질 결론(원인 아님)이 갈린 사례다. C1이 거의 0인 차이로도 성립하도록 설계된 최소 기준 대신 C3(25 %)를 함께 둔 것이 결론을 분명하게 만들었다.

## 다음 작업

- (결정 요청) 시뮬레이터 기본 의미론을 관측값으로 바꿀지.
- (권고) 후보 (1) 시험: TASK72 재생에서 얻은 실제 admission 순서를 `admission_priority`로 넣어 `BASE` 재사용과 `e`를 재계산(선등록 대상).

## 재현 정보

- 위 명령. 산출 `results/npu/stage3/sim_semantics/effect.json`(비추적), 표 `results/tables/M07`.
- **선등록 commit: `86dcf37c25863fa2aa2623d3548659b1e3884644` (2026-09-29 17:33:06 +0900). 계산 시작 17:33:10 +0900 — 선등록 이후.**
