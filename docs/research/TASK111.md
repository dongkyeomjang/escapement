# TASK111 — 비용 집계의 경계 효과 민감도 (지시문 17)

## 상태

DONE

## 날짜

2026-10-06

## 목적

Advisor 지시문 17(마감 2026-10-07). 외부 검토가 지적한 A′ 집계의 경계 효과(시작 경계에서 평가 구간 이전 요청의 decode가 섞이고, 끝 경계에서 평가 요청의 남은 decode가 빠짐)의 크기를 기존 로그로 잰다: 평가 구간 길이 민감도(A), 경계 잔여 작업량과 보정 비(B). **측정·새 예측·모형 수정·원고 문장·기존 판정 변경 없음.**

**측정 0.**

## 배경

- A′ 정의: `mt_measure.lifecycle_metrics`(MULTITURN_MAIN_PREREG 개정 2), [TASK109](TASK109.md) `paper/DEFINITIONS.md`
- 귀속·소속 규칙: [TASK91](TASK91.md)
- 순위 쌍 해소 여부: [TASK110](TASK110.md) `paper/PREREG_TABLE.md` §6

## 시작 상태

- HEAD `0ffe15c`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. `experiments/npu/analysis/boundary_sensitivity.py` 작성. 관측: 각 lifecycle(verdict `selection`)의 A′를 같은 w0에서 창 L ∈ {60, 90, 120} s로 다시 집계하고 replicate 쌍 비 중앙값을 냈다. 예측: 각 묶음의 시뮬레이터 예측기(TASK82 `sim_observed` — 주 예측기인 해석 모형은 창 개념이 없음, TASK87 `sim`, TASK95 `sim_op`, TASK102 `sim_ctx_op`)를 commit된 예측 파일과 같은 코드 경로·입력으로 다시 돌려 창별로 집계했다.
2. **재현 점검**: L = 120에서 관측 22/22 cell이 verdict `per_rep`와, 예측 22/22가 예측 파일 `ratio_to_base`와 정확히 같았다.
3. 작업 B: TASK91 소속 규칙(ALLOC–FREE 사이 `[BUCKET]` 줄)으로 step 비용을 구성원에게 균등 분배해 시작 잔여 S와 끝 잔여 E를 계산하고, 보정 A′ = (총합 − S + E)/요청 수로 보정 비를 냈다. 모든 step에서 구성원 수 = `request_nums`(불일치 0 / 954,953 step).
4. 150 s 창은 불가: runner가 w0 + 120 s에서 발행을 멈춘다. GPU(GTASK11·20) 로그는 이 host에 없다(`results/gpu/` 부재).
5. 표 생성 중 순위 해소 여부 서술을 PREREG_TABLE §6과 대조해 고쳤다(N10 BATCHONLY/TUNED는 해소 쌍).

## 변경된 파일

- `experiments/npu/analysis/boundary_sensitivity.py`(신규), `paper/BOUNDARY_SENSITIVITY.md`(신규), `paper/RESULTS_INDEX.md`(§22)
- `docs/research/TASK111.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/boundary_sensitivity.py --output results/npu/stage3/boundary/boundary_sensitivity.json
```

## 결과

| 항목 | 값 |
|---|---|
| 창 폭(max − min, 60/90/120 s), 관측 | 0.0038–0.0512, 중앙 0.0218 (N12 탐색 0.0883·0.0993 제외) |
| 창 폭, 예측 | 0.0037–0.0338, 중앙 0.0197 |
| BATCHONLY·TUNED 순서가 창에 따라 바뀌는 N | 관측 3/11(TASK82 N6·8·10), 예측 1/11(TASK82 N8); BASE는 항상 최대 |
| 시작 잔여 S / 끝 잔여 E (L = 120, 총합 대비) | 0.24–1.31 % / 1.64–2.73 %; E − S 전 cell 양수(+0.69–+1.64 %) |
| 보정 비 − 원래 비 (L = 120), 쌍별 차 중앙 | 22 cell 모두 \|·\| ≤ 0.0076 |
| 중앙값끼리 차 > 0.01 (L = 120) | 4 cell: TASK82 N6 BATCHONLY −0.0188, N10 TUNED +0.0156, N12 BATCHONLY(탐색) −0.0185, TASK102 N18 TUNED +0.0119(0.6710 → 0.6830) |
| replicate 110쌍 \|보정 − 원래\| | 중앙 0.0036, 최대 0.0234, > 0.01 8쌍 |

cell × 창 전체 표: `paper/BOUNDARY_SENSITIVITY.md` §2.

## 핵심 발견

- 끝 잔여가 시작 잔여보다 모든 cell에서 크다(A′는 평가 요청 작업을 약 0.7–1.6 % 덜 센다). 구성 간 차이는 같은 N에서 최대 0.8 %p라 비에 미치는 영향은 대부분 0.01 미만이다 **[post_hoc]**.
- 순위가 창에 따라 바뀌는 곳은 절감 1–5 %인 TASK82 N6·8·10뿐이다. N10의 해소 쌍(BATCHONLY/TUNED)도 90 s 창에서 관측 순서가 바뀐다.
- "최대 33 %" 후보(TASK102 N18 TUNED 0.6710)는 경계 보정하면 중앙 0.6830이 된다(중앙 replicate r3 자체가 +0.012 움직임). 쌍별 차 중앙은 −0.0010이다.

## 해석

- 없음(민감도 수치만). 관측과 예측의 decode 모집단 규칙이 다르다는 점(관측 = 평가 요청 ALLOC 범위 step, 시뮬레이터 = 시작 시각이 [w0, w1)인 step)을 문서 §3.5에 기록했다.

## 확인되지 않은 사항

- GPU 로그(GTASK11·20)의 같은 분석 — host에 로그 없음.
- 예측 쪽 경계 보정(작업 B는 관측만).
- 150 s 창(로그에 없음).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음. 기존 판정 변경 없음.

## 다음 작업

- (Advisor) "최대 33 %" 후보 표기에서 경계 보정 값(0.683)을 함께 쓸지, GPU host에서 같은 분석을 할지.

## 재현 정보

- 위 명령, HEAD `0ffe15c`. 산출 `boundary_sensitivity.json`(비추적). 예측 재실행은 `plans/main/INDEX*.json`, `OPCOST_SIM.json`, `CTXCOST_BLIND.json`(변경 없음).
