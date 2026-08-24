# 그림 데이터 출처

생성: `env -u PYTHONPATH python3 paper/figures/make_figures.py` ([make_figures.py](make_figures.py), [svgplot.py](svgplot.py)).

matplotlib이 이 host에 없고 cairo도 없어 SVG·PDF를 직접 생성한다([TASK38](../../docs/research/TASK38.md), [TASK39](../../docs/research/TASK39.md)). 값은 전부 `make_figures.py`의 상수 표에 있고, 아래가 그 표의 출처다. **모형에서 나온 값은 그림 안에 "모형"·"절제"로 표시한다.**

## 산출물 3종

| 경로 | 언어 | 형식 | 용도 |
|---|---|---|---|
| `paper/figures/*.svg` | 국문 | SVG | 이 저장소의 국문 연구 문서와 함께 보는 **검토용** |
| `paper/figures/en/*.svg` | 영문 | SVG | 논문용 그림의 브라우저 확인 |
| `paper/figures/pdf/*.pdf` | 영문 | PDF | **LaTeX 원고에 넣는 것.** DejaVuSans 임베딩 |

영문 라벨은 [labels_en.py](labels_en.py)에 있다. **번역표에 없는 비-ASCII 라벨이 있으면 생성이 실패**하므로 국문 문자열이 영문 그림에 남을 수 없다. 검수 결과는 [INSPECTION.md](INSPECTION.md)에 있다.

| 그림 | 파일 | 값의 출처 | raw artifact 경로 |
|---|---|---|---|
| ① 생존 절벽 + LRU 절제 | `fig1_survival_cliff.svg` | 실측 문턱 B=7과 층 1 문턱 16 < B ≤ 33은 [TASK14](../../docs/research/TASK14.md), 12/12 재현은 [TASK15](../../docs/research/TASK15.md). LRU 절제 문턱 61/31/16(500/1,000/2,000 token)은 [TASK29](../../docs/research/TASK29.md) **계산** | `results/npu/stage2/20260819-181100-prefix-boundary/`, `20260819-204900-cliff-repro/` |
| ② N-ratio 곡선 + 격자 개입 | `fig2_grid_alignment.svg` | 측정 격자 9점은 [TASK20](../../docs/research/TASK20.md)(N=4·6·8·10·12·16)과 [TASK24](../../docs/research/TASK24.md) 관측 5(N=3·5·7). 개입 2점(N=6 0.9717, N=8 0.9508)은 [TASK23](../../docs/research/TASK23.md). 연속 격자 1.0000은 [TASK29](../../docs/research/TASK29.md) **절제 계산** | `20260820-165200-nslots-sweep/`, `20260821-231000-grid-intervene/` |
| ③ prefill 스파이크 + 모형 v2 | `fig3_prefill_tax.svg` | v1/v2 비 12칸은 [TASK22](../../docs/research/TASK22.md) "사후 대조" 표. 스파이크/prefill 1.012–1.140은 같은 TASK 판정 3 | `20260821-220100-prefill-tax/`, `20260820-165200-nslots-sweep/` |
| ④ 시뮬레이터 검증 산점도 | `fig4_simulator_validation.svg` | in-sample 11점 [TASK24](../../docs/research/TASK24.md) 관측 5 · OOS 3점 [TASK25](../../docs/research/TASK25.md) 게이트 표 · device+정책 2점 [TASK28](../../docs/research/TASK28.md) 확증 표 · device+구성 4점 [TASK35](../../docs/research/TASK35.md) 확증 표 · N=6 재확증 2점 [TASK36](../../docs/research/TASK36.md). **TASK36 점은 `results/.../config_device.n6.json`을 실제로 읽고, 파일이 없으면 TASK36.md 기록값으로 대체한다** | `20260822-160532-sim-oos/`, `20260822-171959-policy-device/`, `20260823-183505-final-confirm/`, `20260824-160028-n6-reconfirm/` |
| ⑤ headroom 분해 (조율 60 %) | `fig5_headroom_decomposition.svg` | 9칸 × 5축 [TASK33](../../docs/research/TASK33.md) "축별 분해" 표. 허구 이득 +4.32 % → −0.14 %도 같은 TASK | 계산 전용 (측정 없음). 입력 워크로드는 `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` |
| ⑥ 예측기 오차 vs σ* | `fig6_predictor_error.svg` | 도구별 오차 std와 `B(δ)`·`μ̂` 집계는 [TASK32](../../docs/research/TASK32.md). σ* = 1.056–1.823 s는 [TASK30](../../docs/research/TASK30.md) | 계산 전용. 도구 population은 위 tracelab summary |
| ⑦ compile 비용 모형 5점 | `fig7_compile_cost.svg` | [TASK06](../../docs/research/TASK06.md) 165.0 s/9.083 GiB · [TASK10](../../docs/research/TASK10.md) 349.0/11.501 · [TASK23](../../docs/research/TASK23.md) 416.0/12.306 · [TASK34](../../docs/research/TASK34.md) 480.0/13.202 · [TASK35](../../docs/research/TASK35.md) 407.0/12.378. 모형 `42.3 + 61.33 × models`는 [TASK10](../../docs/research/TASK10.md) | 각 run의 `compile/compile.log` |
| ⑨ batch_size 포화 곡선 | `fig9_batch_saturation.svg` | sim 점선은 [BATCH_SATURATION_PREREG.md](../../docs/research/BATCH_SATURATION_PREREG.md)의 선등록 예측표, 실선은 [TASK40](../../docs/research/TASK40.md) B-곡선. **실측은 `batch_curve.json`을 직접 읽고, 없으면 TASK40 기록값으로 대체** | `20260824-222453-batch-saturation/batch_curve.json` |
| ⑧ 최종 3-arm 결과 + 절제 | `fig8_final_result.svg` | N=8 열은 [TASK35](../../docs/research/TASK35.md) 확증 표와 X 표, N=6 열은 [TASK36](../../docs/research/TASK36.md). 채널 B와 선등록 예측도 같은 표 | `20260823-183505-final-confirm/`, `20260824-160028-n6-reconfirm/config_device.n6.json` |

## 재현

```bash
cd /home/rebel/continuum-npu
env -u PYTHONPATH python3 paper/figures/make_figures.py   # 국문 SVG 8 + 영문 SVG 8 + PDF 8
env -u PYTHONPATH python3 paper/figures/verify_figures.py # 수치 대조·넘침·PDF 검사
```

`results/`는 gitignore 대상이므로 clean checkout에서는 ④·⑧의 [TASK36](../../docs/research/TASK36.md) 점이 문서 기록값으로 대체된다. 그 경로는 `make_figures.py`의 `_task36_pairs()`에 명시돼 있다.
