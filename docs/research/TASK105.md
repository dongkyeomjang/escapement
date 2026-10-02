# TASK105 — 결과 색인 GPU 병합과 표·그림 갱신 (TASK100–102, GTASK18·20)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 12 작업 C. GPU 결과 요약표를 결과 색인에 합치고, TASK100–102·GTASK18·20 결과를 표·그림 데이터에 넣으며, 두 장비의 context 비용 비교 표를 만든다. **데이터만 — 원고 문장 없음.**

**측정 0.**

## 배경

- [TASK104](TASK104.md) — GPU branch 통합(GPU 문서가 main 작업 트리에 있음)
- [TASK94](TASK94.md)·[TASK96](TASK96.md) — 결과 색인, `make_paper_tables.py`, 그림 (a)–(d)
- `docs/research/gpu/GPU_RESULTS_SUMMARY.md`(GTASK21, 130행)

## 시작 상태

- HEAD `29dbdd3`(TASK104), 작업은 subagent가 수행하고 주 agent가 검토·보완했다.

## 수행 내용

1. **결과 색인 병합**: 요약표 130행 중 43행은 이미 있었다(42행은 값·종류·출처 일치 → 한 행만 유지). 86행은 새 §19(GTASK별). **값 충돌 1건**(`g11_collapse_curve`: 기존 "0.752: GPU 쪽 정정 대기" 대 요약 "0.752 = bound 평균; `lo` 0.753, GTASK19 정정") — 기존 행을 바꾸지 않고 보고. id 중복 0. 출처 자리표시 "(TASKnn commit)" 14곳을 실제 commit으로 바꿨다(TASK96·90 정정 `f6ffd8f`, TASK97·98 `8b54b5a`).
2. **관측 대기열**: `queue_depth_obs.py`에 TASK102 run 추가 — BASE N15 1.612, N18 3.852; batch 16 0.037–0.048(바닥값 수준).
3. **표·그림**(`make_paper_tables.py`):
   - 그림 (b)·(c): NPU N = 15·18(`cell_set` TASK102; 예측기 `sim_ctxcost`(주), `sim_descriptor`, `sim_ctxcost_origprefill`(보고만), `analytic_v1`(범위 표시)), GPU N = 25·28(`cell_set` GTASK20; `sim_ctxcost`, `sim_lru_price`, `sim_lru_x1.210`·`sim_lru_mode_dist`(population `dev_calibrated`), `lo` bound).
   - 그림 (d): NPU TASK102 6 cell에 관측 대기 Q. GPU N25·28은 대기 기록이 없어 "기록 없음"(시뮬레이터 값으로 채우지 않음).
   - **P12 두 장비 context 비용 비교**(장비·구성·항목·값·모집단·출처): c, 통제 측정 context 범위, 운영 context(NPU는 TASK82·87·95 run 로그의 깨끗한 decode step에서 계산: 평균 1,806–1,811, p05 1,113, p95 2,521–2,534), 운영 비율 재현, blind에서 원래 비용 대비 차이.
   - **P13** TASK102 cell(대조 81건), **P14** GTASK20 cell(대조 72건, 지시 외 추가 — GTASK20 문서 대조용).
4. 표 전체 재생성·대조.

## 변경된 파일

- `paper/RESULTS_INDEX.md`, `experiments/npu/analysis/{make_paper_tables.py, queue_depth_obs.py}`
- `results/tables/P12–P14.{md,csv}`(신규), `P04.md`, `README.md`, `paper_manifest.json`, `figures/F_{b,c,d}*.csv`
- `docs/research/TASK105.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/queue_depth_obs.py --output results/npu/stage3/queue_obs/queue_obs.json
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all
```

## 결과

### 결과 색인 (병합 후 315행)

| 판정 종류 | 행 |
|---|---|
| exploratory | 89 |
| blind_confirm | 85 |
| code_check | 36 |
| dev_set | 30 |
| blind_fail | 24 |
| post_hoc | 24 |
| retro_check | 24 |
| withheld | 3 |

### 표·그림

| 산출 | 행 | 대조 | 불일치 |
|---|---|---|---|
| P12 두 장비 context 비용 비교 | 29 | 72 | 2 |
| P13 NPU context 비용 시뮬레이터 blind N = 15·18 | 6 | 81 | 0 |
| P14 GPU 붕괴 영역 blind N = 25·28 | 6 | 72 | 1 |
| 전체 P01–P14 | — | 380 | 4 |
| F_b / F_c / F_d | 300 / 382 / 178 (기존 행 변경 없음, 추가만) | — | — |

불일치(보고만, 고치지 않음):
1. P04 GTASK11 `BASE.n24` sim LRU 재계산 0.753 대 기록 0.752 — GTASK19가 "0.752 = lo/hi 평균(0.75222), 0.753 = `lo`(0.75318)"로 설명. GTASK19 대조 2건은 통과. 원 대조는 남김.
2. P12 GTASK18 "설명 몫" d = 1: 재계산 90 % 대 기록 89 %(정확값 89.66).
3. P12 같은 열 d = 5: 재계산 89 % 대 기록 90 %(정확값 89.48) — 그 열 8값을 모두 재현하는 반올림 규칙이 없다.
4. P14 GTASK20 `BASE.n28` TTFT: verdict 3.1149(→ 3.11) 대 기록 3.12.

## 핵심 발견

- P12 보고: NPU blind에서 context 비용 sim은 전체 재사용 MAE는 작지만(0.0090 대 0.0093) BASE 재사용 오차 합은 원래 비용보다 크다(0.0377 대 0.0289).

## 해석

- 없음(데이터 작업).

## 확인되지 않은 사항

- TASK91 모집단 F1 비(1.095 / 1.096)는 JSON에 직접 저장되지 않아 P12 대조는 TASK82·87 값의 표본 가중 근사로 했다(근사 표시).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- (Advisor) P04 원 대조를 GTASK19 대조로 바꿀지, GPU 출처 표기를 `origin/gpu-a6000:` 경로에서 main 경로로 바꿀지(내용 동일 확인됨).

## 재현 정보

- 위 명령. 생성 시 HEAD `29dbdd3`. GPU 입력은 `origin/gpu-a6000`(= merge된 트리와 내용 동일).
