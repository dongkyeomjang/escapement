# results/tables — 보고된 표의 집계 파일

이 디렉터리의 파일 하나가 보고된 표 하나에 대응한다. 각 파일은
`experiments/npu/analysis/make_tables.py`의 이름 붙은 함수 하나가 만들고, 그 함수는
아래 「입력」 열의 artifact만 읽는다. 값이 기존 TASK 문서에 기록돼 있으면 각 파일의
「기존 TASK 기록과의 대조」 절에서 대조하며, **불일치는 보고만 하고 고치지 않는다.**

`results/`는 원칙적으로 git이 추적하지 않는다(원자료 보존). 이 디렉터리만 예외로
추적한다 — 여기 있는 것은 원자료가 아니라 원자료에서 나온 집계이고, 저장소 밖에서
관리되는 원고가 참조할 값이기 때문이다.

## 전체 생성

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

## 선행 명령 (원자료 → 분석 산출물)

`make_tables.py`는 아래 분석 산출물을 읽기만 한다. `results/` 아래 산출물은 추적되지
않으므로 없으면 먼저 만든다.

```bash
R=results/npu/stage2
env -u PYTHONPATH python3 experiments/npu/analysis/padding_ratio.py --output $R/padding_ratio.json
env -u PYTHONPATH python3 experiments/npu/analysis/padding_decompose.py --output $R/padding_decompose.json
env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py --output $R/layer_audit.json
env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py --json $R/reuse_cost.json
env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py \
    --run $R/20260908-133635-grid-paired --output $R/20260908-133635-grid-paired/grid_paired.json
env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py \
    --run $R/20260908-151119-step-cost --task54-run $R/20260908-133635-grid-paired \
    --output $R/20260908-151119-step-cost/grid_step_cost.json
env -u PYTHONPATH python3 experiments/npu/analysis/prefill_tax.py \
    --input-dir $R/20260821-220100-prefill-tax/probe --spike-factor 5.0 \
    --output $R/20260821-220100-prefill-tax/prefill_tax_result.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py \
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \
    --output $R/20260823-183505-final-confirm/config_device.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py \
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \
    --output $R/20260824-160028-n6-reconfirm/config_device.n6.json
env -u PYTHONPATH python3 experiments/npu/analysis/batch_curve.py \
    --run $R/20260824-222453-batch-saturation \
    --output $R/20260824-222453-batch-saturation/batch_curve.json
env -u PYTHONPATH python3 experiments/npu/analysis/null_channel.py \
    --run $R/20260901-020342-null-channel --sessions 6,8 \
    --output $R/20260901-020342-null-channel/null_channel.json
env -u PYTHONPATH python3 experiments/npu/analysis/recompile_variance.py analyze \
    --run $R/20260911-191300-recompile-variance \
    --output $R/20260911-191300-recompile-variance/recompile_variance.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py analyze \
    --run $R/20260912-134732-dummy-lifecycle \
    --output $R/20260912-134732-dummy-lifecycle/dummy_lifecycle.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config \
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \
    --output $R/20260823-183505-final-confirm/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config \
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \
    --output $R/20260824-160028-n6-reconfirm/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode saturation \
    --run $R/20260824-222453-batch-saturation --baseline B8 --arms B16,B24,B32 \
    --sessions 6,8,10 --output $R/20260824-222453-batch-saturation/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \
    --run $R/20260823-183505-final-confirm --fix-arrivals $R/20260823-183505-final-confirm \
    --sessions 6,8,10 --output $R/20260823-183505-final-confirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \
    --run $R/20260824-160028-n6-reconfirm --fix-arrivals $R/20260824-160028-n6-reconfirm \
    --sessions 6 --output $R/20260824-160028-n6-reconfirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \
    --output $R/20260823-183505-final-confirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \
    --output $R/20260824-160028-n6-reconfirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py \
    --sessions 6,8,10 --weight sum-seconds --top 20 --dummy-block \
    --output-dir $R/20260922-dummy-block/search-on
for W in sum-seconds per-n; do for S in 6,8 6,8,10 8,10; do
  env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py \
      --sessions "$S" --weight "$W" --top 20 \
      --output-dir $R/20260922-config-search-sensitivity/"${W}_$(echo $S | tr , _)"
done; done
```

## 표 ↔ 파일 ↔ 생성 명령


| 표 | 제목 | 파일 | 생성 명령 | 근거 TASK | 대조 | 불일치 |
|---|---|---|---|---|---|---|
| T01 | padding 비율과 decode device time (N별) | `T01.md` / `T01.csv` | `make_tables.py --table T01` | TASK52, TASK53 | 2 | 0 |
| T02 | bucket 6 개입의 짝 비교 | `T02.md` / `T02.csv` | `make_tables.py --table T02` | TASK54 | 4 | 0 |
| T03 | slot 8→16 개입의 재사용과 계산량 | `T03.md` / `T03.csv` | `make_tables.py --table T03` | TASK35, TASK58 | 44 | 0 |
| T04 | prefill 주입과 병행 세션의 정지 | `T04.md` / `T04.csv` | `make_tables.py --table T04` | TASK22 | 36 | 0 |
| T05 | N=6의 seed 간 상충 | `T05.md` / `T05.csv` | `make_tables.py --table T05` | TASK35, TASK36 | 10 | 0 |
| T06 | decode step 비용 계수 | `T06.md` / `T06.csv` | `make_tables.py --table T06` | TASK13, TASK55 | 5 | 0 |
| T07 | 검증 구성의 비용 비 예측 | `T07.md` / `T07.csv` | `make_tables.py --table T07` | TASK33, TASK35, TASK36 | 8 | 0 |
| T08 | 채널별 device time | `T08.md` / `T08.csv` | `make_tables.py --table T08` | TASK35, TASK36 | 18 | 0 |
| T09 | 구성 선택의 절감률 X | `T09.md` / `T09.csv` | `make_tables.py --table T09` | TASK35, TASK36 | 12 | 0 |
| T10 | 추가 slot의 포화 | `T10.md` / `T10.csv` | `make_tables.py --table T10` | TASK40 | 3 | 0 |
| T11 | 컴파일 비용과 artifact 크기 | `T11.md` / `T11.csv` | `make_tables.py --table T11` | TASK06, TASK10, TASK23, TASK40, TASK62 | 6 | 0 |
| T12 | 무처치 반복의 채널 차 분포 (S1) | `T12.md` / `T12.csv` | `make_tables.py --table T12` | TASK50 | 0 | 0 |
| T13 | N ∈ {3,4,7}의 6블록 짝 비교 (S4) | `T13.md` / `T13.csv` | `make_tables.py --table T13` | TASK23, TASK25 | 21 | 0 |
| T14 | 개입의 padding 하락 분해 (S5) | `T14.md` / `T14.csv` | `make_tables.py --table T14` | TASK56 | 5 | 0 |
| A01 | 재사용 실패의 추가 비용: 두 정의 | `A01.md` / `A01.csv` | `make_tables.py --table A01` | TASK66 | 4 | 0 |
| S02 | 재compile 변동과 회차 간 변동 (S2) | `S02.md` / `S02.csv` | `make_tables.py --table S02` | TASK62 | 2 | 0 |
| S03 | dummy block 생애 주기 직접 관측 (S3) | `S03.md` / `S03.csv` | `make_tables.py --table S03` | TASK63 | 5 | 0 |
| S06a | 검증 비교·절감률의 반복별 분해 (S6) | `S06a.md` / `S06a.csv` | `make_tables.py --table S06a` | TASK35, TASK36 | 6 | 0 |
| S06b | 추가 slot 포화의 N×반복별 분해 (S6) | `S06b.md` / `S06b.csv` | `make_tables.py --table S06b` | TASK40 | 1 | 0 |
| S07 | 재도착 재계산을 껐을 때의 예측 오차 | `S07.md` / `S07.csv` | `make_tables.py --table S07` | TASK35, TASK36, TASK68 | 8 | 0 |
| S08 | dummy block 모형 반영 전후 | `S08.md` / `S08.csv` | `make_tables.py --table S08` | TASK58, TASK63, TASK69 | 10 | 0 |
| M01 | 모형 v0 대조 판정 요약 (R1–R5′) | `M01.md` / `M01.csv` | `make_tables.py --table M01` | TASK72 | 4 | 0 |
| M02 | 모형 v0 R1: 순차 run 생존·축출 산술 | `M02.md` / `M02.csv` | `make_tables.py --table M02` | TASK72 | 1 | 0 |
| M03 | 모형 v0 R3: 격자 DP 대 선정 격자 | `M03.md` / `M03.csv` | `make_tables.py --table M03` | TASK72 | 0 | 0 |
| M04 | 모형 v0 R4: 점유 분포 예측 대 관측 (탐색) | `M04.md` / `M04.csv` | `make_tables.py --table M04` | TASK72 | 0 | 0 |
| M05 | 모형 v0 R5′·R5: 동시 run 재사용 | `M05.md` / `M05.csv` | `make_tables.py --table M05` | TASK72 | 3 | 0 |
| M06 | 모형 v1 개발 집합 보정 (판정 없음) | `M06.md` / `M06.csv` | `make_tables.py --table M06` | TASK73 | 1 | 0 |
| M07 | 시뮬레이터 의미론 스위치와 계통 오차 | `M07.md` / `M07.csv` | `make_tables.py --table M07` | TASK74 | 2 | 0 |
| B01 | 구성 선정의 N 집합·score 민감도 | `B01.md` / `B01.csv` | `make_tables.py --table B01` | TASK61 | 2 | 0 |

대조 합계 223건, 불일치 **0건**.

생성 시각과 commit은 `manifest.json`에 있다.
