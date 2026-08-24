# 그림 검수표

이 host에 SVG 래스터라이저가 없어 **그림을 사람 눈으로 확인하지 못했다.** 이 문서가 그 자리를 부분적으로 메운다.

- **§1 수치 대조**는 [make_figures.py](make_figures.py)의 데이터 상수를 원 TASK 문서의 표에서 다시 읽어 자동 비교한다. 레이아웃이 멀쩡해도 값이 틀릴 수 있고, 그것을 잡는 것이 이 절이다.
- **§2 텍스트 목록**은 각 SVG에 실제로 들어간 문자열 전부를 위치와 함께 나열한다. 브라우저로 그림을 열고 이 목록과 대조하면 누락·오탈자를 짚을 수 있다.
- **여전히 확인되지 않는 것**: 요소가 서로 **겹치는지**. 그것은 눈으로만 확인된다.

생성: `env -u PYTHONPATH python3 paper/figures/verify_figures.py`

---

## 1. 수치 대조 — 그림의 상수 대 원 TASK 값

**138개 항목 중 138개 일치, 0개 불일치.**

**불일치 없음.** 8개 그림의 데이터 상수가 전부 원 TASK 문서의 표·문장과 일치한다.

### 그림별 대조 항목 수

| 그림 | 대조 항목 | 일치 | 출처 |
|---|---|---|---|
| ① | 5 | 5 | TASK14, TASK29 |
| ② | 11 | 11 | TASK24 |
| ③ | 24 | 24 | TASK22 |
| ④ | 22 | 22 | TASK25, TASK28, TASK35, TASK36 |
| ⑤ | 45 | 45 | TASK33 |
| ⑥ | 8 | 8 | TASK32 |
| ⑦ | 20 | 20 | TASK35 |
| ⑧ | 3 | 3 | TASK35 |

**대조하지 못한 것**: 그림 ①의 문턱은 TASK 문서에서 표가 아니라 문장으로 기술돼 있어 문장 일치로 확인했다(값 자체가 아니라 그 값을 말하는 문장의 존재를 확인한다). 그림 ⑧의 N=6 열은 [TASK36](../../docs/research/TASK36.md)의 측정 산출물 JSON을 직접 읽으므로 대조 대상이 아니라 원본이다.

---

## 2. 텍스트 목록 — 브라우저 대조용

### ① `fig1_survival_cliff.svg` — 680 × 452 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ① 재사용 절벽 — 문턱은 token 총량이 아니라 요청 개수다 | Reuse cliff: the threshold counts requests, not tokens |
| 36 | 74 | 11.5 | 층 2 = outer 8 slot × 8,192 token, FIFO. 2,000 token 요청, 12/12 재현 (TASK14·TASK15) | Layer 2 = 8 outer slots x 8,192 tokens, FIFO. 2,000-token requests, 12/12 reproduced (TASK14, TASK15) |
| 69 | 134 | 12 | B = 7 | B = 7 |
| 96 | 211 | 10.5 | 2,000 tok | 2,000 tok |
| 96 | 340 | 10.5 | 1,000 tok | 1,000 tok |
| 96 | 598 | 10.5 | 500 tok | 500 tok |
| 116 | 65 | 12 | 생존 | alive |
| 205 | 246 | 11.5 | metric은 hit이라 하고 | the metric reports a hit |
| 228 | 246 | 11.5 | device는 재계산한다 | while the device recomputes |
| 309 | 65 | 12 | 소멸 | gone |
| 359 | 74 | 12 | 0 | 0 |
| 359 | 134 | 12 | 7 | 7 |
| 359 | 211 | 12 | 16 | 16 |
| 359 | 357 | 12 | 33 | 33 |
| 359 | 598 | 12 | 61 | 61 |
| 388 | 107 | 12 | 실측 · 층 2 실제 재사용 (FIFO 8 slot) | measured - layer 2 actual reuse (FIFO, 8 slots) |
| 405 | 107 | 12 | `prefix_cache_hits_total` (층 1, LRU 512) | prefix_cache_hits_total (layer 1, LRU 512) |
| 422 | 107 | 12 | 절제(모형): LRU·block 단위 회수 (요청 크기별) | ablation (model): LRU, block-granular reclaim, by request size |
| 438 | 366 | 13 | gap 중 도착한 배경 요청 수 B | background requests arriving during the gap, B |

### ② `fig2_grid_alignment.svg` — 680 × 400 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ② 격자 정렬이 gap 효과의 부호를 정한다 — 개입으로 확정 | Grid alignment sets the sign of the gap effect |
| 36 | 74 | 11.5 | 워크로드·seed·모델·slot 수를 고정하고 격자만 바꿨다 (TASK20·23·24·29) | Workload, seed, model and slot count fixed; only the grid changed (TASK20, 23, 24, 29) |
| 63 | 90 | 11 | 1 위 = gap이 오히려 이롭다 (역전) | above 1 = the gap helps (sign reversal) |
| 72 | 117 | 12 | 측정 격자 (1,2,4,8) | measured grid (1,2,4,8) |
| 86 | 65 | 12 | 1.15 | 1.15 |
| 89 | 117 | 12 | 개입 격자 (1,2,4,6,8) | intervened grid (1,2,4,6,8) |
| 106 | 117 | 12 | 동치 밴드 [0.98, 1.02] | equivalence band [0.98, 1.02] |
| 134 | 65 | 12 | 1.10 | 1.10 |
| 164 | 243 | 11 | 격자에 bucket 6만 추가 | add only bucket 6 to the grid |
| 183 | 65 | 12 | 1.05 | 1.05 |
| 183 | 243 | 11 | (재compile 개입) | (recompile intervention) |
| 193 | 18 | 13 | pooled utilization ratio (AGENTIC / CONVENTIONAL) | pooled utilization ratio (AGENTIC / CONVENTIONAL) |
| 221 | 549 | 11 | 연속 격자 → 1.0000 (절제, 모형) | continuous grid -> 1.0000 (ablation, model) |
| 231 | 65 | 12 | 1.00 | 1.00 |
| 279 | 65 | 12 | 0.95 | 0.95 |
| 327 | 65 | 12 | 0.90 | 0.90 |
| 361 | 113 | 12 | 3 | 3 |
| 361 | 152 | 12 | 4 | 4 |
| 361 | 191 | 12 | 5 | 5 |
| 361 | 230 | 12 | 6 | 6 |
| 361 | 269 | 12 | 7 | 7 |
| 361 | 308 | 12 | 8 | 8 |
| 361 | 386 | 12 | 10 | 10 |
| 361 | 463 | 12 | 12 | 12 |
| 361 | 619 | 12 | 16 | 16 |
| 386 | 366 | 13 | 동시 세션 수 N   (max_num_seqs = 8) | concurrent sessions N   (max_num_seqs = 8) |

### ③ `fig3_prefill_tax.svg` — 680 × 400 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ③ prefill은 시스템 비용이다 — 그 항을 넣으면 N 의존 편향이 사라진다 | Prefill is a system cost - adding its term removes the N-dependent bias |
| 36 | 74 | 11.5 | 스파이크/prefill = 1.012–1.140 (9/9 run). v1 0.565–0.855 → v2 0.973–1.039 (TASK22) | spike/prefill = 1.012-1.140 (9/9 runs). v1 0.565-0.855 -> v2 0.973-1.039 (TASK22) |
| 48 | 65 | 12 | 1.1 | 1.1 |
| 62 | 122 | 11.5 | v2 = decode + prefill 직렬화 항 | v2 = decode + prefill serialisation term |
| 72 | 403 | 12 | AGENTIC | AGENTIC |
| 89 | 403 | 12 | CONVENTIONAL | CONVENTIONAL |
| 99 | 65 | 12 | 1.0 | 1.0 |
| 106 | 403 | 12 | 속 빈 표식 = v1, 채운 표식 = v2 | hollow marker = v1, filled marker = v2 |
| 151 | 65 | 12 | 0.9 | 0.9 |
| 193 | 18 | 13 | 예측 ITL 합 / 실측 ITL 합 | predicted ITL sum / measured ITL sum |
| 202 | 65 | 12 | 0.8 | 0.8 |
| 254 | 65 | 12 | 0.7 | 0.7 |
| 305 | 65 | 12 | 0.6 | 0.6 |
| 314 | 122 | 11.5 | v1 = decode 항만 | v1 = decode term only |
| 361 | 114 | 12 | 4 | 4 |
| 361 | 195 | 12 | 6 | 6 |
| 361 | 275 | 12 | 8 | 8 |
| 361 | 356 | 12 | 10 | 10 |
| 361 | 436 | 12 | 12 | 12 |
| 361 | 598 | 12 | 16 | 16 |
| 386 | 366 | 13 | 동시 세션 수 N | concurrent sessions N |

### ④ `fig4_simulator_validation.svg` — 900 × 500 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 78 | 15 | ④ 무보정 시뮬레이터의 예측력 | Predictive power of the uncalibrated simulator |
| 36 | 78 | 11.5 | 선등록된 점(파랑·주황·빨강)은 전부 측정 전에 commit됐다 | Every preregistered point (blue, orange, red) was committed before measurement |
| 85 | 69 | 12 | 1.15 | 1.15 |
| 148 | 69 | 12 | 1.10 | 1.10 |
| 198 | 635 | 12 | in-sample 재현 (TASK24, 11점) | in-sample (TASK24, 11 pts) |
| 210 | 69 | 12 | 1.05 | 1.05 |
| 215 | 635 | 12 | out-of-sample 선등록 (TASK25, 3점) | out-of-sample prereg. (TASK25, 3 pts) |
| 232 | 635 | 12 | device + 정책 개입 (TASK28, 2점) | device + policy (TASK28, 2 pts) |
| 243 | 18 | 13 | 실측 ratio | measured ratio |
| 249 | 635 | 12 | device + compile 구성 (TASK35, 4점) | device + compile cfg (TASK35, 4 pts) |
| 266 | 635 | 12 | N=6 재확증 (TASK36, 2점) | N=6 reconfirm (TASK36, 2 pts) |
| 272 | 69 | 12 | 1.00 | 1.00 |
| 334 | 69 | 12 | 0.95 | 0.95 |
| 396 | 69 | 12 | 0.90 | 0.90 |
| 420 | 544 | 11 | ±0.03 밴드 | +/-0.03 band |
| 461 | 141 | 12 | 0.90 | 0.90 |
| 461 | 220 | 12 | 0.95 | 0.95 |
| 461 | 299 | 12 | 1.00 | 1.00 |
| 461 | 378 | 12 | 1.05 | 1.05 |
| 461 | 458 | 12 | 1.10 | 1.10 |
| 461 | 537 | 12 | 1.15 | 1.15 |
| 486 | 331 | 13 | 시뮬레이터 예측 ratio (보정 파라미터 0개) | simulator prediction ratio (zero fitted parameters) |

### ⑤ `fig5_headroom_decomposition.svg` — 700 × 448 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ⑤ headroom의 절반 이상은 조율의 몫이고 지식으로 살 수 없다 | Most of the headroom is coordination, and knowledge cannot buy it |
| 36 | 74 | 11.5 | 막대 위 숫자 = 조율의 비중 (a−e)/a. 중앙 60 %, 범위 49–73 %. 현실 tool latency 워크로드 (TASK33) | Bar label = coordination share (a-e)/a; median 60 %, range 49-73 % (TASK33) |
| 52 | 376 | 10.5 | 49 % | 49 % |
| 55 | 633 | 10.5 | 71 % | 71 % |
| 70 | 335 | 12 | (e) 전지적 지식 · 세션별 독립 결정 | (e) omniscient, per-session decisions |
| 87 | 335 | 12 | (a)−(e) 조율의 몫 — 어떤 per-session 정책도 닿을 수 없다 | (a)-(e) coordination - no per-session policy reaches it |
| 92 | 65 | 12 | 8 % | 8 % |
| 92 | 569 | 10.5 | 60 % | 60 % |
| 104 | 183 | 10.5 | 69 % | 69 % |
| 104 | 335 | 12 | (b) 반환 시각만 | (b) return times only |
| 121 | 335 | 12 | (c) 생성 길이만 | (c) generation lengths only |
| 124 | 440 | 10.5 | 55 % | 55 % |
| 138 | 335 | 12 | (d) 둘 다 | (d) both |
| 146 | 65 | 12 | 6 % | 6 % |
| 168 | 504 | 10.5 | 56 % | 56 % |
| 172 | 248 | 10.5 | 50 % | 50 % |
| 201 | 65 | 12 | 4 % | 4 % |
| 208 | 18 | 13 | device time 절감 (%) | device time saved (%) |
| 240 | 119 | 10.5 | 73 % | 73 % |
| 241 | 312 | 10.5 | 60 % | 60 % |
| 256 | 65 | 12 | 2 % | 2 % |
| 310 | 65 | 12 | 0 % | 0 % |
| 360 | 306 | 11 | 탐색 seed에서 +4.32 % → 평가 seed에서 −0.14 %: | +4.32 % on exploration seeds -> -0.14 % on held-out seeds: |
| 365 | 65 | 12 | -2 % | -2 % |
| 374 | 306 | 11 | 자유 파라미터 2개·20조합 탐색이 만든 허구 이득 | phantom gain from 2 free parameters, 20-config search |
| 391 | 119 | 12 | ε=1 | eps=1 |
| 391 | 183 | 12 | ε=1 | eps=1 |
| 391 | 248 | 12 | ε=1 | eps=1 |
| 391 | 312 | 12 | ε=2 | eps=2 |
| 391 | 376 | 12 | ε=2 | eps=2 |
| 391 | 440 | 12 | ε=2 | eps=2 |
| 391 | 504 | 12 | ε=5 | eps=5 |
| 391 | 569 | 12 | ε=5 | eps=5 |
| 391 | 633 | 12 | ε=5 | eps=5 |
| 404 | 119 | 12 | N=6 | N=6 |
| 404 | 183 | 12 | N=8 | N=8 |
| 404 | 248 | 12 | N=10 | N=10 |
| 404 | 312 | 12 | N=6 | N=6 |
| 404 | 376 | 12 | N=8 | N=8 |
| 404 | 440 | 12 | N=10 | N=10 |
| 404 | 504 | 12 | N=6 | N=6 |
| 404 | 569 | 12 | N=8 | N=8 |
| 404 | 633 | 12 | N=10 | N=10 |

### ⑥ `fig6_predictor_error.svg` — 700 × 420 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 132 | 15 | ⑥ 예측기는 문턱을 5.6–9.7배 초과하고, 표본을 늘려도 줄지 않는다 | The predictor misses the threshold by 5.6-9.7x |
| 36 | 132 | 11.5 | 표본 10 → 100,000에서 std 8.4 → 10.5 s. 상한도 점추정도 같은 벽에 부딪힌다 (TASK32) | Samples 10 -> 100,000: std 8.4 -> 10.5 s; bound and point estimate hit one wall (TASK32) |
| 70 | 123 | 12 | 30 | 30 |
| 89 | 500 | 10.5 | 17.85 | 17.85 |
| 95 | 437 | 10.5 | 16.05 | 16.05 |
| 120 | 564 | 10.5 | 10.20 | 10.20 |
| 120 | 627 | 10.5 | 10.19 | 10.19 |
| 130 | 123 | 12 | 10 | 10 |
| 181 | 373 | 10.5 | 3.32 | 3.32 |
| 186 | 18 | 13 | 수렴 후 예측 오차 std (s, 로그 축) | converged prediction error std (s, log axis) |
| 196 | 123 | 12 | 3 | 3 |
| 224 | 246 | 10.5 | 1.50 | 1.50 |
| 223 | 310 | 10.5 | 1.54 | 1.54 |
| 234 | 665 | 11.5 | σ* = 1.06–1.82 s | sigma* = 1.06-1.82 s |
| 256 | 123 | 12 | 1 | 1 |
| 289 | 183 | 10.5 | 0.46 | 0.46 |
| 322 | 123 | 12 | 0.3 | 0.3 |
| 340 | 179 | 11 | Read | Read |
| 340 | 242 | 11 | apply_patch | apply_patch |
| 340 | 306 | 11 | TaskUpdate | TaskUpdate |
| 340 | 369 | 11 | exec | exec |
| 340 | 433 | 11 | Bash | Bash |
| 340 | 496 | 11 | write_stdin | write_stdin |
| 340 | 560 | 11 | B(δ) — 논문 그대로 | B(delta) - as published |
| 340 | 623 | 11 | μ̂ — 점추정 | mu-hat - point estimate |
| 402 | 140 | 11.5 | 『Bash』가 27 ms일지 300 s일지는 명령이 정하고, 도구 이름은 그것을 담지 않는다 | Whether 'Bash' takes 27 ms or 300 s is set by the command; the tool name does not carry it |

### ⑦ `fig7_compile_cost.svg` — 680 × 400 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ⑦ 재compile은 7분이다 — 두 점으로 세운 모형이 다섯 번째 점에서도 맞는다 | A recompile costs seven minutes |
| 36 | 74 | 11.5 | Qwen3-4B, max_seq_len 8192, num_devices 4. 마지막 점 오차 시간 −0.7 %, 크기 +0.6 % | Qwen3-4B, max_seq_len 8192, num_devices 4. Last point: -0.7 % time, +0.6 % size |
| 55 | 65 | 12 | 530 | 530 |
| 72 | 117 | 12 | 모형을 세운 관측점 (TASK06·TASK10) | points the model was built on (TASK06, TASK10) |
| 71 | 593 | 10 | TASK34 | TASK34 |
| 89 | 117 | 12 | 모형을 시험한 관측점 (TASK23·TASK34·TASK35) | points that tested the model (TASK23, TASK34, TASK35) |
| 94 | 505 | 11 | 같은 bucket 수의 두 점 → 재현 오차 시간 2.2 %, 크기 0.6 % | two points at the same bucket count -> repeat error 2.2 % time, 0.6 % size |
| 108 | 593 | 10 | 13.20 GiB | 13.20 GiB |
| 112 | 65 | 12 | 450 | 450 |
| 116 | 500 | 10 | TASK23 | TASK23 |
| 123 | 500 | 10 | TASK35 | TASK35 |
| 121 | 584 | 11.5 | 42.3 + 61.33 × compiled model 수 | 42.3 + 61.33 x (compiled models) |
| 153 | 500 | 10 | 12.31 GiB | 12.31 GiB |
| 164 | 408 | 10 | TASK10 | TASK10 |
| 160 | 500 | 10 | 12.38 GiB | 12.38 GiB |
| 183 | 65 | 12 | 350 | 350 |
| 193 | 18 | 13 | compile wall-clock (s) | compile wall-clock (s) |
| 201 | 408 | 10 | 11.50 GiB | 11.50 GiB |
| 254 | 65 | 12 | 250 | 250 |
| 294 | 130 | 10 | TASK06 | TASK06 |
| 325 | 65 | 12 | 150 | 150 |
| 331 | 130 | 10 | 9.08 GiB | 9.08 GiB |
| 361 | 130 | 12 | 2 | 2 |
| 361 | 408 | 12 | 5 | 5 |
| 361 | 500 | 12 | 6 | 6 |
| 361 | 593 | 12 | 7 | 7 |
| 386 | 366 | 13 | compiled model 수 (decoder bucket 수 + prefill graph 1) | compiled models (decoder buckets + 1 prefill graph) |

### ⑧ `fig8_final_result.svg` — 700 × 448 px

| y | x | 크기 | 국문 (검토용 SVG) | 영문 (논문용 SVG·PDF) |
|---|---|---|---|---|
| 20 | 74 | 15 | ⑧ compile 구성이 device time을 회수한다 — 그리고 그 출처는 조건부다 | Compile configuration recovers device time |
| 36 | 74 | 11.5 | 채널 A′(막대) · 채널 B(속 빈 원) · 선등록 예측(×). 두 N 모두 확증 PASS (TASK35·TASK36) | Channel A' (bars), B (hollow), prereg. prediction (x). Both N: PASS (TASK35, 36) |
| 70 | 403 | 12 | ② BATCHONLY — batch_size만 (KV pool 8 → 16) | (2) BATCHONLY - batch_size only (8 -> 16) |
| 87 | 403 | 12 | ③ TUNED — batch_size + bucket 격자 | (3) TUNED - batch_size + bucket grid |
| 104 | 403 | 12 | 격자가 더한 몫 | what the grid adds |
| 110 | 65 | 12 | 1.00 | 1.00 |
| 121 | 403 | 12 | 선등록 sim 예측 | preregistered sim prediction |
| 128 | 195 | 11 | +0.59 % | +0.59 % |
| 130 | 287 | 10 | 격자 +1.52 %p | grid +1.52 pp |
| 138 | 403 | 12 | 채널 B (모형 무의존) | channel B (model-free) |
| 155 | 287 | 11 | +2.11 % | +2.11 % |
| 182 | 65 | 12 | 0.96 | 0.96 |
| 200 | 18 | 13 | device time ratio (arm / BASE) — 1보다 작으면 개선 | device time ratio (arm / BASE) - below 1 is an improvement |
| 253 | 65 | 12 | 0.92 | 0.92 |
| 264 | 465 | 11 | +8.25 % | +8.25 % |
| 267 | 557 | 10 | 격자 +1.47 %p | grid +1.47 pp |
| 290 | 557 | 11 | +9.72 % | +9.72 % |
| 324 | 65 | 12 | 0.88 | 0.88 |
| 375 | 241 | 12 | N=6 | N=6 |
| 375 | 511 | 12 | N=8 | N=8 |
| 388 | 241 | 12 | seed 20261100 | seed 20261100 |
| 388 | 511 | 12 | seed 20261000 | seed 20261000 |
| 401 | 241 | 12 | (TASK36) | (TASK36) |
| 401 | 511 | 12 | (TASK35) | (TASK35) |
| 416 | 82 | 11 | N=8에서는 batch_size가 이득의 대부분(+8.25 %)을 낸다. | At N=8, batch_size supplies most of the gain (+8.25 %). |
| 431 | 82 | 11 | N=6(신규 seed)에서는 BASE가 이미 17/18을 재사용해 batch_size 레버에 살 것이 남아 있지 않다. | At N=6 (fresh seed) BASE already reuses 17/18, so the batch_size lever has nothing left to buy. |

---

## 4. 영문 그림 넘침 검사

영문 라벨은 국문보다 길어지는 경우가 많아 캔버스를 넘칠 수 있다. 각 문자열의 폭을 PDF와 같은 폰트 폭 표로 계산해 캔버스 안에 드는지 확인한다.

**넘침 0건.** 8개 영문 그림의 모든 문자열이 캔버스 안에 든다.

---

## 3. PDF 변환 검사 — 영문판

LaTeX는 SVG를 직접 넣지 못하므로 영문 그림을 PDF로도 낸다. 아래는 각 PDF의 **구조 검사**(header·xref offset 전건·trailer·font 임베딩)와, 그 PDF가 그리는 텍스트를 SVG가 그리는 텍스트와 대조한 **변환 손실 검사**다.

| 그림 | PDF 크기 | 구조 | SVG 문자열 | PDF 문자열 | 일치 |
|---|---|---|---|---|---|
| ① | 717 KB | OK | 19 | 19 | OK |
| ② | 718 KB | OK | 26 | 26 | OK |
| ③ | 718 KB | OK | 21 | 21 | OK |
| ④ | 718 KB | OK | 22 | 22 | OK |
| ⑤ | 719 KB | OK | 43 | 43 | OK |
| ⑥ | 717 KB | OK | 26 | 26 | OK |
| ⑦ | 717 KB | OK | 27 | 27 | OK |
| ⑧ | 718 KB | OK | 26 | 26 | OK |

**8/8 구조 정상, 문자열 전건 일치.** 변환 손실 없음.

**여전히 확인되지 않는 것**: 글자 위치·겹침·잘림. PDF와 SVG는 같은 좌표와 같은 폰트 폭 표를 쓰지만, 그것이 보기 좋다는 뜻은 아니다.
