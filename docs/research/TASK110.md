# TASK110 — 외부 검토 2차 대응 자료: §5.5 오차 합 정의, 비용 모형 없는 활동 시간 비, GPU 재사용 보조표, 선등록 기준표 (지시문 16)

## 상태

DONE

## 날짜

2026-10-06

## 목적

Advisor 지시문 16(마감 2026-10-07). 외부 검토 2차 지적에 대한 원고 재료만 만든다: GTASK11 §5.5 Σd_L·Σd_F의 정확한 근거(A), 비용 모형 없이 관측 시간만으로 만든 실행 시간 비(B), GPU 반복별 재사용·token 비율·부분 재사용 표(C), 실험별 판정 기준표와 순위 쌍 집계표(D). **측정·새 예측·원고 문장·판정 변경 없음.**

**측정 0.**

## 배경

- [TASK109](TASK109.md) — `paper/` 자료 6문서(DEFINITIONS·STATISTICS·PREREG_TABLE 등)
- [TASK91](TASK91.md) — decode step 귀속 규칙, [TASK106](TASK106.md) — P04 대 GTASK19 정정값
- GTASK11(§5.5 LRU 대 FIFO), GTASK19(정정 표), GTASK20

## 시작 상태

- HEAD `ea674be`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 작업 A·C·D는 background subagent가 작성하고 주 agent가 검토했다. 작업 B는 주 agent가 계산했다.
2. **A**(`paper/DEFINITIONS.md` §8): GTASK11 Σd_L 0.148·Σd_F 0.937은 확증 분리 9 cell(N20·22·24 × 3 구성, N26 제외), 요청 단위 재사용률, 예측 = lo·hi 평균, 관측 = 반올림 전 hit/n에서 정확히 나온다(0.14841 / 0.93689; 주 agent가 `PREDICTIONS.json`과 GTASK11 §5.1 정수로 독립 재계산해 일치 확인). 선등록 §5.5 "예측은 두 bound의 평균"·`main_judge.py`와 같다. P04 표 값(lo, 3자리)으로는 0.155 / 0.919(외부 검토 값과 같음). 차이는 반올림(≤ 0.0006)이 아니라 bound(lo 대 평균) 때문이다. 후보 기준 9개와 P04 모두 8/9·Σd_L < Σd_F → `LRU_SUPPORTED` 불변.
3. **B**(`paper/ACTIVITY_TIME_RATIO.md`, `experiments/npu/analysis/activity_time_ratio.py`): A′ 모집단(평가 구간 요청과 그 첫·마지막 ALLOC 사이 `[BUCKET]` step)에 비용 모형 대신 관측 시간을 넣었다. decode = TASK91 귀속 step 간격(깨끗하지 않은 step은 같은 lifecycle·같은 `request_nums` 깨끗한 구간 중앙값으로 채움). 요청별 prefill 경과시간은 server log에 없어 대리값 두 개: `srv`(run 종료 `PREFILL METRICS` 평균 × 구간 요청 수, 주), `exc`(decode와 겹친 구간 − 채움 decode, 나머지는 `srv`). replicate 쌍 비(구성/BASE)의 중앙값과 최소–최대를 verdict의 재구성 A′ 비와 대조. 결과 색인 §21(post_hoc 5행).
4. **C**(`paper/STATISTICS.md` §5, `paper/DEFINITIONS.md` §9): GTASK11 11 cell 합산 재사용률, GTASK20 6 cell replicate별 값과 주 예측기 plan별 예측, token 비율 예측(관측은 N20 BASE 0.846만), 부분 재사용 관측 대 LRU/FIFO lo·hi·평균. 없는 값은 "GPU host 확인 필요".
5. **D**(`paper/PREREG_TABLE.md` §5·§6): TASK82·87·95·102, GTASK04·11 실험×지표별 판정 기준표(예측기, 오차식, 통과 문턱, null, cell, 기존 판정)와 순위 쌍 집계표.

## 변경된 파일

- `paper/DEFINITIONS.md`(§8·§9), `paper/STATISTICS.md`(§5), `paper/PREREG_TABLE.md`(§5·§6), `paper/RESULTS_INDEX.md`(§21)
- `paper/ACTIVITY_TIME_RATIO.md`(신규), `experiments/npu/analysis/activity_time_ratio.py`(신규)
- `docs/research/TASK110.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/activity_time_ratio.py --output results/npu/stage3/activity_time/activity_time.json
```

## 결과

### B: 관측 활동 시간 비 대 재구성 A′ 비 (구성/BASE 중앙, k = 5)

| 묶음 | `exc` − A′ (중앙) | `srv` − A′ (중앙) | 귀속 불가 step 비율 |
|---|---|---|---|
| TASK82 N6·8·10 | +0.008 – +0.024 | −0.006 – +0.014 | 0.015–0.022 |
| TASK87 N14·16 | −0.019 – +0.015 | +0.018 – +0.058 | 0.034–0.045 |
| TASK95 N13·17·20 | −0.012 – +0.002 | −0.007 – +0.051 | 0.030–0.063 |
| TASK102 N15·18 | −0.011 – +0.001 | +0.028 – +0.050 | 0.038–0.052 |

예: TASK102 N18 TUNED — `exc` 0.672 [0.650–0.718], `srv` 0.721 [0.701–0.769], A′ 0.671 [0.651–0.725]. cell별 전체 표는 `paper/ACTIVITY_TIME_RATIO.md` §2.

- 귀속 가능한 실행 요청이 전혀 없는 step ≤ 0.26 %(cell 최대); 채움 fallback 3 step / 860,584.
- decode만의 비는 N20 외 0.969–1.114 — 감소는 prefill 쪽에서 온다.

### A·C·D

- A: 위 수행 내용 2. GPU host 확인 필요 항목은 C 참조.
- C의 "GPU host 확인 필요": GTASK11 11 cell replicate별 재사용률, token 비율 관측 10 cell, N26 부분 재사용 관측, GTASK20 replicate 분모·token 비율·부분 재사용(`blind_judge.py` 미기록), replicate별 부분 재사용(GTASK11·20). GTASK20 예측 파일에는 token·부분 필드가 없다(host 문제 아님).
- D: 순위 쌍 NPU 판정 예측기 33쌍 중 결정 26·일치 26·미결정 7, GPU(lo) 15쌍 중 결정 10·일치 10·미결정 5(STATISTICS §2.3과 같음).

## 핵심 발견

- 비용 모형 없이 관측 step 간격과 배타 prefill 추정(`exc`)으로 만든 비가 20 cell 모두 재구성 A′ 비와 0.025 이내로 맞는다 **[post_hoc]**.
- 주 대리값 `srv`(run 전체 model forward 평균)는 N ≥ 14에서 감소 폭을 0.02–0.06 작게 보인다.

## 해석

- `srv`의 차이 원인 후보는 (i) 워밍업이 섞인 run 전체 평균(BASE는 평가 구간 prefill이 구간 밖보다 큼, TASK102 N18 r0에서 확인)과 (ii) `exc`가 덮지 못한 prefill 모집단 차. 몫은 분해하지 않았다(UNKNOWN). `srv`는 model forward만, `exc`·decode는 step 간격(host overhead 포함)이라 시계 정의도 다르다.

## 확인되지 않은 사항

- 요청별 prefill 경과시간(server log에 없음).
- C의 GPU host 확인 필요 항목(위).

## 실패 / 무효 시도

- 없음. 주 대리값(`srv`)은 결과 확인 전 스크립트에 정했고, `exc`가 A′와 더 가깝다는 것은 결과를 본 뒤의 관찰이다.

## 연구 원칙에 미치는 영향

- 기록 불일치 보고(고치지 않음): GTASK11 §5.5 문장 "(관측 0.669, LRU 0.752, FIFO 0.611)"은 LRU는 bound 평균, FIFO는 lo(평균이면 0.610)다. GTASK19의 "FIFO 0.611도 평균(0.6097)의 반올림"은 틀렸다(0.6097 → 0.610). 판정 영향 없음.

## 다음 작업

- (Advisor) GTASK19 설명 정정 여부, GPU host 확인 필요 항목을 GPU 작업자에게 요청할지.

## 재현 정보

- 위 명령, HEAD `ea674be`. 산출 `activity_time.json`(비추적). A의 독립 재계산은 `experiments/gpu/multiturn/plans/PREDICTIONS.json` + GTASK11 §5.1 hit/분모 정수.
