# TASK96 — 지시문 09 결정 기록과 결과 색인·표·그림 데이터 갱신

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 09. TASK91–95 결정 요청에 대한 결정([결정 11](INDEX.md#결정-11--지시문-09-결정-task9195-결정-요청))을 기록하고, 결과 색인(`paper/RESULTS_INDEX.md`)·표·그림 데이터에 TASK93–95 결과, 판정 종류 수정, 관측 대기열 깊이를 반영한다. 측정, 비용 형태 변경, 모형·시뮬레이터 코드 수정, 원고·원고용 문장은 범위 밖이다.

**측정 0.**

## 배경

- [TASK94](TASK94.md) — 결과 색인과 P01–P10, 그림 CSV 4종
- [TASK95](TASK95.md) — 통합 시뮬레이터 blind cell 판정
- [TASK20](TASK20.md) — N/slots sweep 선등록 판정

## 시작 상태

- HEAD `e3697b0`(= `origin/main`), `git status --short`: `?? .idea/`만

## 수행 내용

1. **결정 11 기록**(INDEX 사용자 결정 절), 후속 연구 11(context 길이 의존 step 비용, 두 기판 공통 원인 후보 — GPU G-06까지 보류) 추가.
2. **TASK20 판정 종류**: 선등록 commit `f9cc106`의 commit 시각 2026-08-20T16:51:16+09:00, 측정 시작 16:51:32(TASK20 재현 정보). "저하 존재" 기준(전 블록 ratio < 1 이고 pooled < 0.97)은 선등록 문서 `NSLOTS_SWEEP_PREREG.md`(`f9cc106`)에 고정돼 있다 → **`blind_confirm` 유지**, 근거를 행에 적었다.
3. **`withheld` 종류 신설**: TASK34 채널 일치(판정 보류), TASK35 N = 6(2 보류) 두 행을 `blind_fail` → `withheld`.
4. **관측 대기열 깊이**(`experiments/npu/analysis/queue_depth_obs.py`, 신규): 평가 구간의 decode step마다 Q = (client에서 전송했고 응답이 끝나지 않은 요청 수) − (`[BUCKET]` request_nums). step 시각은 [TASK91](TASK91.md) 귀속(R의 ALLOC–FREE 사이 `[BUCKET]` = R의 decode step)으로 그 step에 속한 요청의 streaming chunk 두 시각의 중점. NPU는 prefill이 배타라 decode step 중에 prefill 중인 요청이 없으므로, 차이는 admission 대기 + 전송·응답 종료 중인 요청이다. step 가중 평균 Q, P(Q > 0), Q < 0 비율(시각 배치 오류 점검)을 lifecycle·cell별로 낸다. TASK82·87·95의 NPU 28 cell 전부(DP N8 10 replicate 포함). 시뮬레이터 값은 쓰지 않았다.
5. **표·그림 데이터**(`make_paper_tables.py`): P11(TASK95 cell) 신설; 그림 (b)·(c)·(d)에 N = 13·17·20 추가, 세 그림 모두 `cell_set` 열(TASK82 / TASK87 / TASK95 / GTASK11 / GTASK13)과 `population`(N20 BASE = `blind_no_information_cell`, v1은 `reference_in_scope` / `reference_out_of_scope`); 그림 (d)에 관측 열 `queue_mean_obs`·`queue_p_gt0_obs`·`queue_obs_source` — 기존 v1 B2 고정점 예측 열(HILOAD_PREREG)과 분리. P10의 v1.1 MAE 대조를 정정값 0.0415로, P04의 0.752 대조에 "GPU 쪽 정정 대기" 표기(불일치는 그대로 보고).
6. **결과 색인**: §16(TASK92–95, 19행), §14 관측 대기 3행, `t90_v11_freeze_mae` 0.0415, g11 0.752 행에 "GPU 쪽 정정 대기", `t95_simop_vs_sim`을 `blind_fail`.
7. **TASK90 정정 절** 추가(본문 표 수정 없음).

## 변경된 파일

- `experiments/npu/analysis/queue_depth_obs.py`(신규), `experiments/npu/analysis/make_paper_tables.py`
- `paper/RESULTS_INDEX.md`, `results/tables/P04.md`, `P10.md`, `P11.{md,csv}`(신규), 그 밖의 P 표 재생성, `results/tables/figures/F_{b,c,d}*.csv`, `results/tables/README.md`, `results/tables/paper_manifest.json`
- `docs/research/TASK90.md`(정정 절), `docs/research/TASK96.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/queue_depth_obs.py --output results/npu/stage3/queue_obs/queue_obs.json
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all
```

Population: TASK82·87·95 판정에 쓰인 lifecycle(cell당 5, DP N8 10), 평가 구간 decode step(cell당 17,611–82,814). Unit: 요청 수(step 가중). Source: client 요청 기록(`sent_s`, `done_s`)과 streaming chunk 시각, server `[BUCKET]`·ALLOC·FREE 순서. Device scope: 각 run의 한 server.

## 결과

### 관측 대기 Q (step 가중 평균 / P(Q > 0))

| N | BASE (M = 8) | BATCHONLY (M = 16) | TUNED (M = 16) | 출처 |
|---|---|---|---|---|
| 6 | 0.013 / 0.013 | 0.013 / 0.013 | 0.014 / 0.014 | TASK82 |
| 8 | 0.018 / 0.018 | 0.018 / 0.018 | 0.018 / 0.018 (DP 0.018) | TASK82 |
| 10 | **0.044 / 0.037** | 0.022 / 0.022 | 0.022 / 0.022 | TASK82 |
| 12 | 0.280 / 0.164 | 0.029 / 0.029 | 0.031 / 0.031 | TASK82 |
| 13 | 0.420 / 0.232 | 0.031 / 0.031 | 0.032 / 0.032 | TASK95 |
| 14 | 0.761 / 0.360 | 0.035 / 0.035 | 0.034 / 0.034 | TASK87 |
| 16 | 1.802 / 0.603 | 0.040 / 0.040 | 0.038 / 0.038 | TASK87 |
| 17 | 3.528 / 0.869 | 0.045 / 0.045 | 0.045 / 0.045 | TASK95 |
| 20 | 6.820 / 1.000 | 0.099 / 0.091 | 0.096 / 0.088 | TASK95 |

Q < 0 비율 ≤ 0.13 %(시각 배치 오류 작음). 산출 `queue_obs.json` SHA256 `0d859e94e0050a81…`.

### 결과 색인 (갱신 후 208행)

| 판정 종류 | 행 | 변화 |
|---|---|---|
| blind_confirm | 58 | +9 (TASK95) |
| exploratory | 42 | +9 (TASK92 5, 관측 대기 3, v1 범위 밖 1) |
| dev_set | 30 | +1 (TASK90 v1.1 MAE 0.0415) |
| retro_check | 22 | — |
| post_hoc | 21 | — |
| blind_fail | 17 | +3 (TASK95 sim §5.2, (1) 대 (2), 사전 예측 §5.2), −2 (→ withheld) |
| code_check | 16 | — |
| withheld | 2 | 신설 (TASK34 채널, TASK35 N = 6) |

### 표·그림 데이터

- P11 신설(대조 10건, 불일치 0). 전체 대조 153건, 불일치 1건(P04 GTASK11 0.752/0.753 — GPU 쪽 정정 대기). P10 불일치는 TASK90 정정으로 해소.
- 그림 행 수: F_a 133, F_b 228(+45), F_c 282(+60), F_d 130(+27).

## 핵심 발견

1. **BASE N = 10의 관측 대기는 작다**(Q 0.044, P(Q > 0) 0.037; 구조적 0 cell의 바닥값 0.022 수준보다 약간 위). 대기열은 N = 12에서 뚜렷해지고(0.28) N = 17·20에서 BASE가 포화한다(3.5, 6.8; P(Q > 0) 0.87, 1.00).
2. **바닥값이 0이 아니고 요청률과 함께 커진다**: 구조적으로 대기 0인 cell(N ≤ 8 전 구성, batch 16 N ≤ 16)에서 0.013–0.040. 이 측정의 해상도 한계다.
3. batch 16 구성은 N = 17에서 바닥값 수준(0.045), N = 20에서 처음 바닥값보다 커진다(0.096–0.099).

## 해석

- 관찰: 관측 Q는 BASE N ≥ 12에서 바닥값보다 확실히 크고 N에 따라 가파르게 커진다. 파생 해석: 해석 모형(v1)의 "동시 실행 상한 아래" 적용 범위([결정 10](INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정))는 관측으로도 BASE N ≤ 10, batch 16 N ≤ 17 정도에서 대기열이 거의 없는 영역과 일치한다.

## 확인되지 않은 사항

- 바닥값의 구성 요소(전송 지연 대 응답 종료 지연)는 가르지 않았다.
- GPU GTASK14의 관측 대기 길이와 정의가 같은지(GPU는 엔진 지표 기반일 수 있다) — 그림 (d)에 출처 열로 구분해 두었다.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 판정 종류에 `withheld`를 둔다: 판정 전제 조건(예: 채널 일치)이 충족되지 않아 판정하지 않은 것은 실패(`blind_fail`)가 아니다.

## 다음 작업

- GPU 쪽: GTASK11·12의 0.752/0.753 정정(GPU agent), G-06 결과 뒤 [후속 연구](INDEX.md#후속-연구) 11 재검토.

## 재현 정보

- 위 명령. 입력: TASK82·87·95 run 디렉터리(비추적). HEAD `e3697b0`에서 계산.
- 선등록 commit: 해당 없음(판정 없음).
