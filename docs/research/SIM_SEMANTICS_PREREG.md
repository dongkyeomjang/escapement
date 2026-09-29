# 시뮬레이터 의미론 교정 스위치 — 계통 오차 설명력 선등록

작성: 2026-09-29, Advisor 지시문 03 작업 B. **이 문서와 스위치·계산 스크립트를 commit하기 전에는 아래 조합의 계산을 한 건도 하지 않았다.** 스위치를 넣은 뒤 한 일은 기본 설정에서 기존 표가 재현되는지의 회귀 확인뿐이다(`make_tables.py --all`: 표 28개 `.md`/`.csv` byte 동일, 대조 221건 불일치 0).

## 질문

[TASK72](TASK72.md)의 사건 재생은 이 기판의 의미론이 **즉시 release**와 **PRE_EVICT dummy**임을 보였고, 시뮬레이터는 **지연 release**(`OuterBlockPool`, [TASK24](TASK24.md))와 **dummy 없음**(또는 [TASK69](TASK69.md)의 `reserved`)으로 계산해 왔다. 원고 IV-E의 계통적 양의 예측 오차(Table IX 8개 비교 모두 `e > 0`)가 이 두 의미론 차이에서 오는가?

## 스위치 (기본값 = 기존 동작)

- `SimConfig.release_rule`: `deferred`(기본) / `immediate`
- `SimConfig.dummy_mode`: `off`(기본) / `reserved`(= 기존 `dummy_block=True`) / `pre_evict`(신규: `0 < running < max_running_requests`인 decode step마다, 빈 block이 없으면 가장 오래된 inactive block 축출; 다음 admission이 그 block을 가져간다)
- **결과와 관계없이 기본값은 바꾸지 않는다.** 기본값 변경은 별도 결정으로 올린다.

## 대상과 계산

- 비교 8개: seed 20261000 N=6·8·10과 seed 20261100 N=6, 각 arm `BATCHONLY`·`TUNED`의 device time 비(대 `BASE`), 블록 0·1·2 합. 실측은 채널 A′(`config_device.aggregate`), 시뮬레이터는 측정 plan(`sessions_from_plan`) — `dummy_block_effect.py`와 같은 경로.
- `e = 실측 비 − 시뮬레이터 비` (양수 = 시뮬레이터가 절감을 과대 예측; 원고 IV-E 부호).
- baseline 재사용 4건: `BASE`의 turn ≥ 1 재사용 수, 실측 15/18, 9/24, 9/30, 17/18.
- 조합: (`deferred`,`off`) 기존, (`immediate`,`off`), (`deferred`,`pre_evict`), (`immediate`,`pre_evict`) 둘 다, 참고로 (`deferred`,`reserved`) = TASK69.
- 스크립트: `experiments/npu/analysis/sim_semantics_effect.py`, 산출 `results/npu/stage3/sim_semantics/effect.json`(비추적).

## 기존 값 (계산 전 이미 기록됨, [S08](../../results/tables/S08.md))

기존 조합의 `e`: +0.0183, +0.0194, +0.0074, +0.0058, +0.0339, +0.0364, +0.0066, +0.0076 → **평균 |e| 0.01693, 양수 8/8.** baseline 시뮬레이터 재사용 14/18, 9/24, 7/30, 16/18 → 실측과의 차 1, 0, 2, 1.

## 사전 예측

근거: [TASK72](TASK72.md) 산출물에서 실제 일정 위의 재생으로 보면 지연 release는 `BASE` 재사용을 과대 예측하고(TASK35 N=8: 13 대 관측 9, N=10: 13 대 9) 즉시 release는 정확하다. 시뮬레이터는 이미 기존 조합에서 `BASE` 재사용을 약간 **과소** 예측한다(14/9/7/16 대 15/9/9/17). 즉시 release로 바꾸면 시뮬레이터 `BASE` 재사용이 **더 줄어** `BASE` 비용이 오르고, arm 비가 내려가 `e`가 **커질** 것으로 본다. arm 쪽은 재사용이 거의 포화(18/18, 24/24)라 영향이 작다. PRE_EVICT는 가득 찬 pool에서 축출 수를 바꾸지 않고 시점만 앞당기므로 효과가 작다.

| 조합 | 평균 \|e\| | 양수 e 수 | baseline 재사용 |
|---|---|---|---|
| `immediate`/`off` | **증가** | 8/8 | 4건 모두 기존 이하, 실측과의 차는 N=8·10에서 커짐 |
| `deferred`/`pre_evict` | 변화 < 0.003 | 8/8 | 기존과 같거나 ±1 |
| `immediate`/`pre_evict` | **증가** | 8/8 | 실측과의 차가 4건 중 2건 이상에서 커짐 |

**종합 예측: 판정 `FAIL`** — 두 의미론 차이는 계통 오차를 설명하지 않는다. 확신 중간(시뮬레이터 일정이 실제 일정과 달라 재생 결과를 그대로 옮길 수 없다).

## 판정 기준

`off` = (`deferred`,`off`), `both` = (`immediate`,`pre_evict`).

- **C1** `mean|e|(both) < mean|e|(off)` (= 0.01693).
- **C2** baseline 재사용 4건 중 **3건 이상**에서 `|sim − 실측|(both) ≤ |sim − 실측|(off)`.
- **C3 (더 엄격, 제안)** `mean|e|(both) ≤ 0.75 · mean|e|(off)` — 평균 |e|를 **25 % 이상** 줄여야 한다. 근거: C1만으로는 소수 넷째 자리의 감소로도 통과하는데, 질문은 "계통 오차의 **원인**인가"이므로 오차의 상당 부분을 없애야 한다. 25 %는 8개 중 2개 비교 몫에 해당하는 크기다.
- **`PASS` ⇔ C1 ∧ C2 ∧ C3.** C1 ∧ C2만 성립하면 `PARTIAL`(방향은 맞지만 원인의 작은 일부), 그 밖은 `FAIL`.
- 보고만: 조합별 평균 |e|, 평균 부호 있는 e, 양수 e 수, baseline 재사용과 축출 수, TASK69 `reserved` 참고 조합.

## 실패 시 결론

계통적 양의 오차의 원인은 release 규칙·dummy 의미론이 **아니다**. 다음에 볼 후보(순서 = 제안 순서):

1. **`BASE`의 시뮬레이터 재사용 부족** — 기존 조합에서 이미 실측보다 1–2건 적다(14/7/16 대 15/9/17). 원인 후보는 동시 도착의 admission 순서 가정([TASK24](TASK24.md) `arrival_order`)과 client overhead 0(재도착 시각이 실제보다 이르다). 재사용이 적으면 `BASE` 비용이 과대 → `e > 0`으로 직결된다.
2. **미측정 bucket 비용** — `TUNED`는 6·10, N=10의 `BATCHONLY`는 16을 쓰며 보간·외삽값이다([TASK55](TASK55.md) C(6) 보간 오차 2.00 %). `BASE`는 측정 bucket만 쓰므로 arm 쪽 비용만 편향된다.
3. **채널 A′의 고정 오버헤드**([TASK35](TASK35.md): 1.2–1.7 s가 A′에 빠짐) — 두 arm·`BASE`에 같은 크기로 들어가면 비를 1 쪽으로 당긴다.
4. **재도착 되먹임**([TASK68](TASK68.md)) — 고정 도착 시각 모형이 탐색 구간에서 더 작은 오차를 냈다.

## 실행 절차

commit 후 `env -u PYTHONPATH python3 experiments/npu/analysis/sim_semantics_effect.py` 1회. 실행 중 스크립트를 편집하지 않는다(KNOWN_PITFALLS 5).

## 개정 이력

- 2026-09-29 초판 (계산 전).
