# TASK108 — 논문 그림 3장 생성 (F_a, F_b, F_d)

## 상태

DONE

## 날짜

2026-10-03

## 목적

Advisor 지시문 14. [TASK105](TASK105.md)·[TASK96](TASK96.md)의 그림 데이터 CSV(`results/tables/figures/F_a, F_b, F_d`)만으로 원고가 참조하는 벡터 PDF 3장을 만든다. 측정·재계산·원고·캡션 작성 없음.

**측정 0.**

## 배경

- `results/tables/figures/*.csv`(TASK94·96·105), `paper/figures/svgplot.py`(TASK39의 의존성 없는 plotter — DejaVuSans embed PDF)

## 시작 상태

- HEAD `04b941a`(= `origin/main`), `?? .idea/`만. matplotlib 미설치 — 의존성 설치 없이 저장소의 `svgplot.py`를 썼다.

## 수행 내용

1. `experiments/npu/analysis/make_paper_figures.py`(신규): 머리 주석에 CSV 열 → 시각 요소 대응. `svgplot` 위에 여러 패널·로그 축(log10 변환 후 눈금 표기)·속 빈 마커·범례를 얹었다. 폭 496 pt(17.5 cm), 축 레이블 9 pt, 눈금·범례·음영 표기 8 pt, F_d 점의 N 표기 7 pt. Okabe–Ito 색, 예측기는 선 모양, 구성은 색과 마커 모양, 관측은 마커.
2. 범례 표기는 지시문 표대로 바꿨다(Baseline·Larger KV·Larger KV + grid·Analytical model·Simulator·Simulator (context-aware cost)·Simulator (short-context cost)·Null predictor).
3. 미리보기: PDF 렌더러가 없어 같은 도형 목록을 Pillow로 래스터화해(scratch 스크립트) 눈으로 확인하며 범례 겹침·표기 충돌을 고쳤다.

## 변경된 파일

- `experiments/npu/analysis/make_paper_figures.py`(신규)
- `results/tables/figures/pdf/{F_a_survival, F_b_reuse_ratio_vs_N, F_d_applicability}.pdf`(신규)
- `docs/research/TASK108.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_figures.py
```

## 결과

| PDF | 크기 (pt) | 읽은 CSV 열 | SHA256 앞 16자리 |
|---|---|---|---|
| `F_a_survival.pdf` | 496 × 272 | substrate, condition, bg_tokens, m_background, pred_hit_tokens, obs_hit_tokens, obs_survive_frac | `901c2a8cc4757a5a` |
| `F_b_reuse_ratio_vs_N.pdf` | 496 × 396 | substrate, N, config, metric, predictor, value, ci_lo, ci_hi, population, cell_set | `24ee68f095dc9498` |
| `F_d_applicability.pdf` | 496 × 236 | substrate, N, config, predictor, queue_mean_obs, reuse_error, cell_set | `294dbbdfd1f87922` |

- 재실행 byte 동일(두 번 생성 후 SHA256 비교 일치). PDF에 생성 시각 없음, DejaVuSans(일반·굵게) embed.
- F_c(선택)는 만들지 않았다.

### 그림에 넣지 못했거나 처리 방식을 정한 데이터

1. **F_a (a) NPU 관측**: CSV에 NPU 관측이 token 수가 아니라 생존 비율(`obs_survive_frac`, 모든 행 0 또는 1)로만 있다. 같은 CSV의 예측 행 m = 0 full-hit 값 1,920 token을 곱해 token으로 표시했다. NPU 예측은 배경 크기 4종이 같은 계단(m = 7에서 1,920 → 0)이라 한 선만 그렸다.
2. **F_a (b) GPU**: 조건 (i)·(ii)(생성 token 캐시 여부, full hit 2,000 대 2,016)를 같은 선 모양으로 함께 그렸다.
3. **F_b 재사용률 반복 범위**: CSV에 재사용률의 replicate 범위 열이 없다(`ci_lo`·`ci_hi` 비어 있음) — 세로 막대를 그리지 못했다.
4. **F_b 예측기 선택**: Simulator = NPU `sim_observed`(TASK82)·`sim_descriptor`(TASK87·95·102), GPU `sim_lru`(GTASK11)·`sim_lru_price`(GTASK20, 범례 "short-context cost"). 그리지 않은 것: v1.1, `sim_default`, `sim_opcost`, `sim_ctxcost_origprefill`, `sim_fifo`, GPU 보정·개발 집합 행, DP 구성(NPU N = 8 한 cell).
5. **F_b 해석 모형 범위 밖 표시**: NPU는 지시대로 N ≥ 12를 옅게, GPU는 모든 cell이 N > `max_num_seqs` = 8이라 전부 옅게 그렸다.
6. **F_d GPU 대기열**: GTASK20 cell(N = 25·28)은 `queue_mean_obs`가 비어 있어 제외했다(스크립트 주석). GPU 값(GTASK14 관측)과 NPU 값(`queue_depth_obs.py`)은 정의가 다르므로 x축 이름을 "Observed queue length (requests)"로 중립적으로 두었다.

## 핵심 발견

- 없음(그림 생성).

## 해석

- 없음.

## 확인되지 않은 사항

- 실제 PDF 뷰어 렌더(이 host에 렌더러가 없어 같은 도형의 Pillow 래스터로만 확인).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 원고 빌드에서 PDF 확인(사용자).

## 재현 정보

- 위 명령, 입력 CSV는 HEAD `04b941a`의 `results/tables/figures/`.

## 개정 1 (2026-10-03, 사용자 지시: F_b 수정 2건)

1. GPU 패널 (b)·(d): N ≥ 25에서 문맥 반영 시뮬레이터(`sim_ctxcost`, GTASK20 주 예측기)를 주 예측기로 그렸다 — (d) 비용 비 패널에도 구성별 dash-dot 선을 추가했다. 짧은 문맥 비용 시뮬레이터 선은 N = 24 이후 옅게 그렸다.
2. 범례에 "Observed, exploratory cell"(속 빈 마커) 항목을 추가했다.

F_a·F_d는 바뀌지 않았다(SHA256 동일). F_b 새 SHA256 앞 16자리 `2487577c5ceea7a2`, 크기 496 × 422 pt, 재실행 byte 동일.
