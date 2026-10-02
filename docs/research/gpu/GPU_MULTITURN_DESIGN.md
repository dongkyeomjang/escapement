# GPU multi-turn steady-state 실험 설계 (NPU 설계에서 바뀐 점)

작성: 2026-09-29, GPU 지시문 G-03 작업 A ([GTASK07](GTASK07.md)).

**이 문서의 범위**
- 설계만 다루며 예측과 판정 기준은 쓰지 않는다. 그것은 [GPU_MULTITURN_PREREG.md](GPU_MULTITURN_PREREG.md)(GTASK09)에서 정한다.
- 구성과 N은 [GTASK08](GTASK08.md)의 blind 선정 결과를 따른다.

**기본값**
- NPU 설계를 그대로 쓴다: [MULTITURN_DESIGN_DRAFT.md](../MULTITURN_DESIGN_DRAFT.md), [TASK76](../TASK76.md) 결정 D1–D7, [TASK77](../TASK77.md) runner, [MULTITURN_MAIN_PREREG.md](../MULTITURN_MAIN_PREREG.md).
- 이 문서는 **GPU 기판이라서 바뀌어야 하는 것만** 적는다.

## 1. 그대로 쓰는 것

| 항목 | 값 | 출처 |
|---|---|---|
| 세션 생성 규칙 | K = 8, 첫 prompt U(800,1600), 이후 segment 8, 생성 U(32,256), slot당 세션 16개, 첫 세대 turn 수 U{1..K} | `make_plan.build`, `generate_plan` (import, 무수정) |
| tool gap | TraceLab `toolmix`, 상한 60 s, turn마다 새로 뽑음 | 같은 `summary.json` — 이 host 경로 `/home/csdc/kyeom/Project/vllm-continuum/results/tracelab/summary.json`, SHA256 `25bb1b0f…` 일치 |
| 세션 갱신·엇갈린 시작 | slot i는 `i · cycle_s / N`에 시작, 세션이 끝나면 즉시 다음 세션 | `continuum.workload.multiturn` |
| 구간 규칙 | warm-up = max(3 · cycle, 모든 slot 2 turn 완료), 평가 120 s, 이후 발행 중단(drain), 요청은 발행 시각으로 구간에 귀속 | `WindowRule`(runner와 분석이 같은 함수) |
| replicate | 5 (plan을 구성 간 공유하는 짝 설계) | D7, [TASK19](../TASK19.md) |
| 구성 순서 | replicate 블록 안에서 무작위 | [MULTITURN_MAIN_PREREG.md](../MULTITURN_MAIN_PREREG.md) §2 |

## 2. GPU에서 바뀌는 것

| # | 항목 | NPU (TASK75–80) | GPU (이 설계) | 이유 |
|---|---|---|---|---|
| 1 | **prompt 형식** | 텍스트. 재도착 prompt = 이전 prompt 텍스트 + 응답 텍스트 + segment 텍스트 | **token id 목록**. 재도착 prompt = 이전 prompt id + 응답의 생성 id + segment id | GPU는 생성 token까지 캐시한다(GTASK02 H5). 텍스트로 이어 붙이면 재토큰화 경계에서 token이 합쳐져 hit가 경계 block에서 끊길 수 있다. NPU는 prefill token만 캐시해 응답 부분이 hit와 무관했다. |
| 2 | segment 내용 | `build_exact`로 만든 단어 텍스트 | `Random(text_seed)`로 뽑은 id, [1000, 150000) 범위(GTASK04 `rand_ids` 규칙) | token id로 보내므로 tokenizer가 필요 없다. 내용은 step 비용·hit 산술과 무관하다. |
| 3 | 생성 길이 | `max_tokens`, temperature 0 (EOS에서 일찍 끝날 수 있음) | **`ignore_eos: true`** — 길이 = plan 값 | 생성 **내용**은 동시 batch에서 run마다 달라질 수 있다(GTASK03 발견 5). 길이를 고정하면 내용이 달라도 hit 산술과 step 수는 결정적이다. |
| 4 | 생성 id 수신 | 응답 텍스트 | `return_token_ids: true`. 비streaming은 `choices[0].token_ids`, streaming은 chunk마다 delta `token_ids` | source 확인: `entrypoints/openai/completion/protocol.py:142`(field), `serving.py:380·567`(delta·전체). 기능 확인 6/6(GTASK07). |
| 5 | server | RBLN compile artifact를 `vllm serve` | `launch.lifecycle`: server 인자로 pool·`max_num_seqs`·capture 격자를 고정한다. 관측 patch(`[GSTEP]`, `[GPFX]`)와 KV events collector를 켠다. | GTASK03 관측 수단. 카드는 uuid `GPU-4485e769…` 한 장으로 고정한다(G-03 §1). |
| 6 | lifecycle 유효성 | runner exit, 구간, HTTP 오류, plan SHA | 왼쪽 항목 모두 + **카드 uuid 일치**, **`vllm:num_preemptions_total` 증분 0**, GPU에 다른 process 없음, 생성 id 수 = 요청 값 | GPU에는 recompute preemption이 있고 끌 수 없다. 구성으로 구조적으로 막고(§3), run마다 확인한다. |
| 7 | 구성 | compile artifact(BASE (1,2,4,8)/b8, BATCHONLY, TUNED, DP) | **server 인자**: KV pool(`--num-gpu-blocks-override`), `--max-num-seqs`, `cudagraph_capture_sizes`. 재compile 없이 바뀌므로 **N별 격자**도 비용 없이 넣는다. | GTASK02: pool과 격자가 runtime flag다. |
| 8 | N 격자 | 6, 8, 10 (+12 탐색) | **GTASK08 선정**(아래 §3) | preemption 불가 조건(pool ≥ `max_num_seqs` × 최대 요청 block)을 지키면서 재사용이 0.4–0.85에 들어오는 N이 NPU보다 크다. |
| 9 | turn당 device time (채널 A′) | `[BUCKET]` × TASK13 step 비용 + `prefill_s(prompt − cached)` | **`[GSTEP]` step 모양 × GTASK05 비용 모형**(`gpu_cost`). 혼합 step 증분은 구간이므로 **하한·상한 두 값**을 쓴다. | GPU는 prefill을 decode step에 섞는다. 비용은 step 단위로 매기고 prefill 비용은 그 step의 증분이다. |
| 10 | prefill 간섭 | W = streaming 정지 시간(배타 prefill이 decode를 멈춤) | **혼합 step의 decode 지연 증분**: Σ(혼합 step 시간 − 같은 폭 decode 기준선) × 그 step의 decode 수 / 요청 수. §2.1 구간을 붙인다. | GPU에는 정지가 없다. decode가 멈추지 않고 그 step이 길어진다. |
| 11 | 재사용 지표 | 요청 단위 재사용률 | 재사용률 + **재사용 token 비율**(hit token / 재사용 가능 token) + **hit 분포**(0 / 부분 / 전체) | GPU는 tail부터 block 단위로 잃는다(부분 손실). |
| 12 | `cached` 출처 | client `cached_tokens`, 없으면 server `[PFX]` 조회 줄 | client `cached_tokens`(flag 확인 후 부재 = 0, TASK79). server `[GPFX] LOOKUP hit=`로 교차 확인하고, 불일치는 보고한다. KV events로 축출 순서를 기록한다. | 관측 수단이 다르다(GTASK03). |
| 13 | 예측기 | 해석 v1, sim 기본, sim 관측 의미론(`continuum.sim`) | 해석 v1 GPU 인스턴스(`gpu_mt_model`), **GPU 의미론 시뮬레이터**(`gpu_mt_sim`, LRU), **반사실 FIFO 시뮬레이터**(같은 코드, 축출 순서만 할당 순서) | `continuum.sim`은 prefill 배타·prompt만 캐시·sequence slot pool을 전제로 한다. GPU 의미론(혼합 chunked prefill, 생성 token 캐시, 조회 후 할당, 16-token block)은 옵션으로 표현할 수 없어 `experiments/gpu/`에 새로 썼다(§4). |
| 14 | plan seed | 격자 선정 `20261200+10N+r`, 파일럿 `20261300–02`, 본 `20261400+10N+r` | 선정 `20262100 + i`, 본 `20262300 + i`, 파일럿 `20262500 + i`(i = 순번) | NPU seed와 겹치지 않는다. TASK80 권고대로 N에 곱하지 않는다. |
| 15 | streaming | 파일럿 판정 `EQUIVALENT` → 본 실험 streaming | GPU에서 **따로 파일럿**한다(G-03 §6). host·stack이 다르다. | 관찰자 효과는 `stack` 태그 결과였다(TASK79 발견 1). |

## 3. 구성과 preemption 불가 조건

- 모든 구성에서 `max_num_seqs` = 8, `--max-num-batched-tokens` = 2048, block 16이다.
- **preemption 불가 조건**은 `pool − 1 ≥ 8 × ceil(최대 요청 token / 16)`이다.
  - 이 workload 법칙의 최악 요청은 1,600 + 8 × (8 + 256) = 3,712 token = 232 block이다.
  - 따라서 **pool ≥ 1,857**이다.
  - 생성한 plan은 각자의 실제 최댓값으로도 검사한다.
- pool 크기와 N은 GTASK08이 모형으로 고른다(blind).

## 4. 예측기의 GPU 의미론 (코드 위치)

| 파일 | 내용 | import하는 neutral 코드 |
|---|---|---|
| `experiments/gpu/multiturn/gpu_cost.py` | GTASK05 step 비용. FULL `F[b] + g·n`, 격자 밖 eager decode, PIECEWISE 증분 [0, 1.5] ms, eager 혼합 증분 [lag-1(≥0), 3-step 창] | — |
| `experiments/gpu/multiturn/gpu_mt_sim.py` | vLLM v1 scheduler·block pool 의미론 시뮬레이터(LRU·FIFO) | `continuum.workload.multiturn`(plan, 갱신, `WindowRule`) |
| `experiments/gpu/multiturn/gpu_mt_model.py` | 해석 v1 GPU 인스턴스. B2 `occupancy`, B1 `lru_block_survival`, B3 `optimal_grid`, B4 | `continuum.model.{occupancy, survival_v1, grid}` |
| `experiments/gpu/multiturn/gpu_mt_runner.py` | GPU runner(token id prompt, lifecycle, uuid·preemption 검사) | `continuum.workload.multiturn` |

**neutral 코드의 수치 한계 (보고, `src/` 무수정)**
- `survival_v1.lru_block_survival`은 Poisson pmf를 `exp(-mean)`에서 시작한다. 그래서 `mean > ≈ 745`이면 underflow가 나고, 모든 확률이 "전부 손실"로 간다.
- GPU 입력(할당률 × 수십 초 gap)은 이 영역에 들어간다.
- wrapper `gpu_mt_model.lru_survival`은 같은 식을 log 공간에서 계산한다. `mean < 600`에서는 neutral 함수를 그대로 부르며, 두 계산의 일치를 `_self_check`로 확인한다.

## 5. 측정 정의 (GPU)

| 지표 | 정의 | 원천 |
|---|---|---|
| 재사용률 | 평가 구간 turn ≥ 1 요청 중 `cached > 0` 비율 | client `cached_tokens`(부재 = 0, flag 확인), server `[GPFX] LOOKUP hit=` 교차 |
| 재사용 token 비율 | Σ cached / Σ 재사용 가능 token. 재사용 가능 = `min(floor((이전 prompt + 이전 생성 − 1)/16), floor((prompt − 1)/16)) × 16` | client + plan |
| hit 분포 | turn ≥ 1 요청을 0 / 부분(0 < cached < 재사용 가능) / 전체로 분류 | 같음 |
| h(n)·padding | 평가 구간 server 창의 `[GSTEP]` step 가중 `reqs` 분포, padding = Σ(padded − toks)/Σ padded | server |
| turn당 device time (A′-GPU) | server 창 `[GSTEP]` step마다 `gpu_cost.step_ms`(decode 수, prefill token 수, 격자). 창 합 / 평가 구간 요청 수. 하한·상한 | server + GTASK05 |
| 직접 채널 (탐색) | 창 안 연속 dispatch 간격의 합 / 요청 수(engine idle 구간 제외 규칙은 선등록에서 정함) | server `[GSTEP]` `t` |
| 혼합 step 간섭 | §2 #10 | server + GTASK05 |
| turn ≥ 1 TTFT | `first_token_s − sent_s` 중앙값(streaming, 보고만) | client |

**server 창**: 평가 구간에 발행된 첫 요청의 `[GPFX] ALLOC`부터 마지막 요청의 `ALLOC`까지이며, NPU `mt_measure`와 같은 정의다. client와 server의 시계를 맞출 필요가 없다.

## 6. 남은 결정

§3의 pool·N·격자 선정 결과와 Advisor 결정 사항은 [GTASK08](GTASK08.md)에 적는다.
