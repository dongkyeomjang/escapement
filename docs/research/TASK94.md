# TASK94 — 결과 색인과 논문 표·그림 데이터 (원고 문장 없음)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 08 작업 D. 사용자가 원고를 쓸 때 수치를 찾아 확인할 수 있는 **데이터 색인**(`paper/RESULTS_INDEX.md`)과 **표·그림 데이터**(`results/tables/P*`, `results/tables/figures/F_*.csv`)를 만든다. **원고·원고용 문장(서술·캡션·초록·요약문)은 만들지 않는다.**

**측정 0.**

## 배경

- 기존 표 체계 `experiments/npu/analysis/make_tables.py`(TASK67: 표마다 함수 하나, 입력 artifact 명시, 기록값 대조 — 불일치는 보고만)
- GPU 쪽 수치: `origin/gpu-a6000` branch를 `git show`로만 읽었다(checkout·merge·GPU 파일 영역 수정 없음)

## 시작 상태

- HEAD `f812705`, 미commit 초안 `paper/RESULTS_INDEX.md`(163행, 이전 단계 subagent 작성). 작업은 [TASK93](TASK93.md) 측정과 병행했고 **측정 중 HEAD를 바꾸지 않기 위해 측정 종료 뒤 commit**했다.

## 수행 내용

1. 색인 초안 검증·수정(subagent 작업, 주 agent가 표본 대조): 행마다 출처 파일@commit에 수치가 문자 그대로 있는지 스크립트로 확인. 출처 commit이 수치가 생기기 전 선등록 commit을 가리키던 6건 정정(GTASK04 `87731c5`→`c7875fb`, GTASK11 `721e4d0`→`22b50f4`, GTASK12 `0973228`→`3ddbba8`, TASK34 `9c4e6f2`→`e24cf76`, TASK35 `e24cf76`→`3f8308e`, TASK87 `235bad2`→`a210be2`). 원문에 없던 "25–30 %"를 TASK87 원문 값(평균 |1 − m| 0.253, m 0.696–0.800)으로 교체. TASK13의 bucket 경계 두 서술은 출처 위치별 두 행으로 분리(조정하지 않음). 판정 종류 재확인: TASK20 N = 10·12 저하는 선등록 규칙 판정이라 `blind_confirm`, TASK14 문턱은 `exploratory`(예측 6 부분 실패는 별도 `blind_fail` 행). TASK91·GTASK14 등 누락 행 추가, 중복 2행 삭제. 각 행에 표·그림 데이터 위치 열(`data`) 추가.
2. `experiments/npu/analysis/make_paper_tables.py`(신규): P01–P10, 표마다 생성 명령·입력 경로(GPU는 branch 경로와 파일 commit)·기록값 대조. `make_tables.py`의 `Check`·`render_md` 재사용. `results/tables/README.md`에 P·F 목록 블록 추가(`make_tables.py --all`이 README 전체를 다시 쓰면 이 블록이 지워지므로 `make_paper_tables.py --all`을 뒤에 다시 실행).
3. 그림 데이터 CSV 4종: 각 행에 `population`(blind_confirm_cell, blind_exploratory_cell, dev_set, post_hoc, retro_check, code_check)과 `source` 열.
4. 원고 수정 후보 M1–M5·M2′ ↔ 색인 id 대응표(색인 §15).

## 변경된 파일

- `paper/RESULTS_INDEX.md`(신규), `experiments/npu/analysis/make_paper_tables.py`(신규)
- `results/tables/P01–P10.{md,csv}`, `results/tables/figures/F_{a_survival,b_reuse_ratio_vs_N,c_pred_vs_obs,d_applicability}.csv`, `results/tables/paper_manifest.json`(신규), `results/tables/README.md`
- `docs/research/TASK94.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all
```

입력은 기존 분석 산출(`results/npu/stage3/**/*.json`, 비추적)과 GPU branch의 commit된 문서·예측 파일뿐이다. 시뮬레이터·측정 실행 없음.

## 결과

### 색인 행 수 (186)

| 판정 종류 | 행 |
|---|---|
| blind_confirm | 49 |
| exploratory | 33 |
| dev_set | 29 |
| retro_check | 22 |
| post_hoc | 21 |
| blind_fail | 16 |
| code_check | 16 |

한 행에 판정 종류는 하나이고 blind와 개발 집합 값을 한 행에 섞지 않았다.

### 표 (기록값 대조 143건, 불일치 2건)

| 표 | 내용 | 대조 | 불일치 |
|---|---|---|---|
| P01 | 순차 생존: NPU 절벽(사후 재생) / GPU 계단(blind) | 4 | 0 |
| P02 | TASK82 cell별 재사용·비용 비, 세 예측기, 영 | 14 | 0 |
| P03 | TASK87 N = 14·16 | 11 | 0 |
| P04 | GTASK11 GPU multi-turn | 63 | 1 |
| P05 | 구성 순위, 두 기판 | 4 | 0 |
| P06 | 사건 재생, 두 기판(R5′, GTASK12) | 7 | 0 |
| P07 | 운영 step 시간 척도(개발 집합): GTASK13, TASK91 | 11 | 0 |
| P08 | 같은 길이 정상성: TASK83, GTASK16 | 6 | 0 |
| P09 | descriptor 규칙 field 7개와 두 기판 재현 | 6 | 0 |
| P10 | TASK90 B2 진단과 v1.2 동결 전 점검(개발 집합) | 17 | 1 |

### 그림 데이터

| 파일 | 행 | 내용 |
|---|---|---|
| `F_a_survival.csv` | 133 | (a) 순차 생존 NPU 절벽 대 GPU 계단, 예측 = 관측 |
| `F_b_reuse_ratio_vs_N.csv` | 183 | (b) N별 BASE 재사용·구성 비용 비, NPU N = 6–16 / GPU N = 20–26, 예측기별 + 영 |
| `F_c_pred_vs_obs.csv` | 222 | (c) 예측 대 관측(재사용, 비용 비), 영 예측기 포함 |
| `F_d_applicability.csv` | 103 | (d) 대기열 깊이 대 오차 |

## 핵심 발견

1. **기록 불일치 2건(보고만, 고치지 않음)**: (i) GTASK11 N24 BASE sim LRU — §5.5·발견 4 문장은 0.752, §5.1 표·GTASK13·`PREDICTIONS.json` `lo`(1361/1807)는 0.753(`hi` 0.7513). GTASK12도 0.752를 반복. (ii) [TASK90](TASK90.md) 동결 전 점검 표의 v1.1 재사용 MAE 0.042 — `freeze_check.json`은 0.04150(반올림 0.041).
2. 그림 (d)의 NPU BASE N ≤ 10 cell은 대기열 깊이가 어디에도 기록돼 있지 않아 "기록 없음"(관측 TTFT만)으로 두었다 — 새 계산은 하지 않았다.

## 해석

- 없음(데이터 색인 작업).

## 확인되지 않은 사항

- GPU 원자료는 이 host에 없어 GPU 관측값은 GTASK 문서 표의 자릿수(3자리, §5.2는 4자리)다.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 출처 commit은 수치가 처음 기록된 commit 이후여야 한다 — 선등록 commit을 결과 출처로 적으면 그 commit에는 수치가 없다.

## 다음 작업

- (Advisor 결정) 아래 결정 요청. [TASK95](TASK95.md)의 blind cell 결과를 색인·그림 데이터에 넣을지.

## 재현 정보

- 위 명령, 생성 시 HEAD `f812705`(`paper_manifest.json`), GPU branch head `e820f48`.
- 결정 요청: (1) TASK20 N = 10·12 저하를 `blind_confirm`으로 둘지, (2) 보류 판정(TASK34 채널, TASK35 N = 6)을 `blind_fail`로 둘지 별도 종류를 둘지, (3) 그림 (d)의 NPU BASE N ≤ 10 대기열 깊이를 v1 B2 고정점으로 새로 계산할지, (4) GTASK11·12의 0.752/0.753을 GPU agent가 정리할지.
