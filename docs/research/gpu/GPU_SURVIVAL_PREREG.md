# GPU 순차 생존 곡선 선등록 — 첫 교차 기판 blind 예측

## 문서 성격

GPU 지시문 G-02 작업 C의 **선등록**이다. 이 문서, 예측 산출물([`predictions.json`](../../../experiments/gpu/survival/prediction/predictions.json), SHA256 `ee181fb2…85d1`), 예측·측정·판정 script를 담은 commit이 만들어진 뒤에 첫 trial의 server를 기동한다. 결과는 [GTASK04](GTASK04.md)에 쓴다. 측정 후 기준을 바꾸지 않는다.

**이 예측은 NPU 데이터로 만든 모형(`src/continuum/model/`, [TASK71](../TASK71.md)·[TASK73](../TASK73.md))을, GPU에서는 파라미터만 바꿔 측정 전에 계산한 것이다.** GPU 측 입력은 [GTASK01](GTASK01.md)(source-read)과 [GTASK02](GTASK02.md)(Stage 0)에서 확정된 값뿐이고, GPU에서 생존을 잰 데이터는 아직 없다. [TASK29](../TASK29.md)의 GPU 측 절제 수치는 조회 순서 가정(할당 후 조회)이 달라 **쓰지 않았다**(INDEX 결정 4 개정).

## 예측 방법 — 모형 코드에서 쓴 것과 wrapper가 덧붙인 것

| 구분 | 내용 | 위치 |
|---|---|---|
| **모형 코드 (import만, 무수정)** | `survival.sequential_window(target_units, background_units, resume_units, resume_allocates_first=False)` → `survival.reusable_tokens(hit_formula, granularity="block", capacity, window, unit_tokens, cached_prefix_tokens, query_tokens)`. 즉 v0 (B1-1)/(B1-2)의 block 단위 창 식: 넘친 단위 = `u_T + Σ u_bg − C`, T는 꼬리부터 잃고, hit = `HitFormula(16)`(`floor(min(shared, query−1)/16)·16`) | `src/continuum/model/survival.py` |
| **GPU 파라미터** | `C = num_gpu_blocks − 1 = 800`(null block), 단위 16 token, `resume_allocates_first=False`(조회 후 할당, hit 선보호) | GTASK01 항목 1·4·8, GTASK02 |
| **wrapper가 덧붙인 의미론 1: 생성 token 캐시** | 끝난 요청의 계산 token = `P + g − 1`(마지막 sampled token 제외). 점유 단위 `u = ceil((P+g−1)/16)`, 캐시 가능 prefix = `floor((P+g−1)/16)·16` | [`predict.py`](../../../experiments/gpu/survival/predict.py) `gpu_inputs` (GTASK02 H5) |
| **wrapper가 덧붙인 의미론 2: 미사용 block 우선 + release 순서 LRU** | 새 server의 free queue는 block ID 순이고 반납 block은 꼬리에 붙는다. 순차 프로토콜에서는 배경이 **미사용 block을 다 쓴 뒤에야** T의 block(꼬리부터)을 가져간다 → release 순서 LRU가 이 프로토콜에서 할당 순서 FIFO와 **같은 순서**로 축출하고, `d₀ = C − u_T`. 이 등가성 때문에 FIFO 창 식(모형 코드)을 그대로 쓸 수 있다. 모형 v1의 LRU 형태 `lru_block_survival`의 결정론 핵심(`lost = min(u_T, max(0, N_ev − d₀))`)과 같다. v1의 Poisson 층은 고정된 요청 계획에 해당하지 않아 쓰지 않는다 | `predict.py` docstring |
| **wrapper가 덧붙인 의미론 3: hit 선보호** | resume의 자기 할당이 조회 뒤라 창에 넣지 않는다(`resume_allocates_first=False`) | 모형 인자 |
| **독립 검산: block-exact replay** | vLLM free queue 규칙(null block, block ID 순 초기화, head pop + hash 제거, 꼬리 역순 반납, 조회 후 touch, `num_tokens − 1` 상한, 생성 token 캐시, budget별 chunk)을 block 단위로 재생 | [`gpu_pool_replay.py`](../../../experiments/gpu/survival/gpu_pool_replay.py) |

**60개 trial 전부에서 모형 코드 예측과 replay 예측이 같다**(`predict.py`가 불일치 시 중단하도록 assert). 예측값은 두 계산이 일치한 값이다.

## 실험 격자

| 요소 | 값 |
|---|---|
| server | `CUDA_VISIBLE_DEVICES=0`, `--revision 1cfa9a72… --dtype bfloat16 --max-model-len 8192 --seed 20260929 --generation-config vllm --enable-prompt-tokens-details --block-size 16 --num-gpu-blocks-override 801 --max-num-seqs 1 --max-num-batched-tokens 2048 --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 8, 16]}'` + KV events(ipc) + `ESCAPEMENT_OBS=1`(patch 적용 상태), async scheduling 기본(on) |
| preemption 구조적 불가 | 가용 800 block ≥ `max_num_seqs 1 × ceil(8192/16) = 512` ≥ 최대 요청 251 block |
| 프로토콜 | trial마다 **새 server**. target → 배경 m개 → resume, 동시성 1. 모든 요청 greedy, `ignore_eos`, token-id prompt(trial seed의 균등 난수 `[1000, 150000)`) |
| target | prompt 2,000 token. 생성 (i) 8, (ii) 24 |
| 배경 | 크기 {500, 1,000, 2,000, 4,000} token, 생성 8 |
| resume | (i) target prompt + 새 suffix 8 = 2,008 token (NPU TASK15와 같은 조건) / (ii) target prompt + **target 생성 24 token** + 새 suffix 8 = 2,032 token. 생성 8 |
| m 격자 | 500: 10, 20, 21, 22, 23(×3), 24, 25, 26, 30, 40 / 1,000: 5, 10–14, 20 / 2,000: 3, 5, 6(×3, (i)만), 7, 8, 10 / 4,000: 2–5 / 공통 m=0 |
| trial 수 | (i) 32, (ii) 28, **합 60** |
| 시간 추정 | trial당 server 기동 ≈ 36–50 s + 요청 ≤ 10 s + 종료 ≈ 5 s → **약 55–65분** |

**(ii)의 생성 길이를 24로 둔 이유**: target 2,000 = 125 block이 딱 맞아, 생성 8 token(계산 7)은 126번째 block을 채우지 못한다. 그러면 (i)과 (ii)의 예측이 모든 m에서 같아져 생성 token 캐시 효과를 볼 수 없다. 생성 24(계산 23)이면 126번째 block이 채워져 무손실 hit가 2,000 → 2,016으로 갈린다. 지시문의 "생성 8"은 배경과 조건 (i)에 그대로 적용했다.

## 예측표 (resume의 hit token, 정확한 정수)

`u_T`·`u_bg`: 점유 block, overflow: `u_T + m·u_bg − 800`(음수는 0), T blocks evicted: T의 hash된 block 중 resume 조회 전에 축출된 수.

| cond | bg | m | reps | u_T | u_bg | overflow | T blocks evicted | **pred hit** |
|---|---|---|---|---|---|---|---|---|
| i | 0 | 0 | 1 | 126 | 1 | 0 | 0 | **2000** |
| i | 500 | 10 | 1 | 126 | 32 | 0 | 0 | **2000** |
| i | 500 | 20 | 1 | 126 | 32 | 0 | 0 | **2000** |
| i | 500 | 21 | 1 | 126 | 32 | 0 | 0 | **2000** |
| i | 500 | 22 | 1 | 126 | 32 | 30 | 29 | **1536** |
| i | 500 | 23 | 3 | 126 | 32 | 62 | 61 | **1024** |
| i | 500 | 24 | 1 | 126 | 32 | 94 | 93 | **512** |
| i | 500 | 25 | 1 | 126 | 32 | 126 | 125 | **0** |
| i | 500 | 26 | 1 | 126 | 32 | 158 | 125 | **0** |
| i | 500 | 30 | 1 | 126 | 32 | 286 | 125 | **0** |
| i | 500 | 40 | 1 | 126 | 32 | 606 | 125 | **0** |
| i | 1000 | 5 | 1 | 126 | 63 | 0 | 0 | **2000** |
| i | 1000 | 10 | 1 | 126 | 63 | 0 | 0 | **2000** |
| i | 1000 | 11 | 1 | 126 | 63 | 19 | 18 | **1712** |
| i | 1000 | 12 | 1 | 126 | 63 | 82 | 81 | **704** |
| i | 1000 | 13 | 1 | 126 | 63 | 145 | 125 | **0** |
| i | 1000 | 14 | 1 | 126 | 63 | 208 | 125 | **0** |
| i | 1000 | 20 | 1 | 126 | 63 | 586 | 125 | **0** |
| i | 2000 | 3 | 1 | 126 | 126 | 0 | 0 | **2000** |
| i | 2000 | 5 | 1 | 126 | 126 | 0 | 0 | **2000** |
| i | 2000 | 6 | 3 | 126 | 126 | 82 | 81 | **704** |
| i | 2000 | 7 | 1 | 126 | 126 | 208 | 125 | **0** |
| i | 2000 | 8 | 1 | 126 | 126 | 334 | 125 | **0** |
| i | 2000 | 10 | 1 | 126 | 126 | 586 | 125 | **0** |
| i | 4000 | 2 | 1 | 126 | 251 | 0 | 0 | **2000** |
| i | 4000 | 3 | 1 | 126 | 251 | 79 | 78 | **752** |
| i | 4000 | 4 | 1 | 126 | 251 | 330 | 125 | **0** |
| i | 4000 | 5 | 1 | 126 | 251 | 581 | 125 | **0** |
| ii | 0 | 0 | 1 | 127 | 1 | 0 | 0 | **2016** |
| ii | 500 | 10 | 1 | 127 | 32 | 0 | 0 | **2016** |
| ii | 500 | 20 | 1 | 127 | 32 | 0 | 0 | **2016** |
| ii | 500 | 21 | 1 | 127 | 32 | 0 | 0 | **2016** |
| ii | 500 | 22 | 1 | 127 | 32 | 31 | 30 | **1536** |
| ii | 500 | 23 | 1 | 127 | 32 | 63 | 62 | **1024** |
| ii | 500 | 24 | 1 | 127 | 32 | 95 | 94 | **512** |
| ii | 500 | 25 | 1 | 127 | 32 | 127 | 126 | **0** |
| ii | 500 | 26 | 1 | 127 | 32 | 159 | 126 | **0** |
| ii | 500 | 30 | 1 | 127 | 32 | 287 | 126 | **0** |
| ii | 500 | 40 | 1 | 127 | 32 | 607 | 126 | **0** |
| ii | 1000 | 5 | 1 | 127 | 63 | 0 | 0 | **2016** |
| ii | 1000 | 10 | 1 | 127 | 63 | 0 | 0 | **2016** |
| ii | 1000 | 11 | 1 | 127 | 63 | 20 | 19 | **1712** |
| ii | 1000 | 12 | 1 | 127 | 63 | 83 | 82 | **704** |
| ii | 1000 | 13 | 1 | 127 | 63 | 146 | 126 | **0** |
| ii | 1000 | 14 | 1 | 127 | 63 | 209 | 126 | **0** |
| ii | 1000 | 20 | 1 | 127 | 63 | 587 | 126 | **0** |
| ii | 2000 | 3 | 1 | 127 | 126 | 0 | 0 | **2016** |
| ii | 2000 | 5 | 1 | 127 | 126 | 0 | 0 | **2016** |
| ii | 2000 | 6 | 1 | 127 | 126 | 83 | 82 | **704** |
| ii | 2000 | 7 | 1 | 127 | 126 | 209 | 126 | **0** |
| ii | 2000 | 8 | 1 | 127 | 126 | 335 | 126 | **0** |
| ii | 2000 | 10 | 1 | 127 | 126 | 587 | 126 | **0** |
| ii | 4000 | 2 | 1 | 127 | 251 | 0 | 0 | **2016** |
| ii | 4000 | 3 | 1 | 127 | 251 | 80 | 79 | **752** |
| ii | 4000 | 4 | 1 | 127 | 251 | 331 | 126 | **0** |
| ii | 4000 | 5 | 1 | 127 | 251 | 582 | 126 | **0** |

**예측된 형태**: NPU의 개수 절벽이 아니라 **16 token 단위 계단**이다. 손실 시작은 `m·u_bg > C − u_T`(여기서 > 674 block), 전손은 `m·u_bg ≥ C`(800 block)이며 둘 다 **token 총량**의 함수다. 배경 500 token에서는 한 요청(32 block)마다 512 token씩 네 계단(2,000 → 1,536 → 1,024 → 512 → 0)으로, 4,000 token에서는 한 번의 부분 손실(752) 뒤 전손으로 내려간다.

## 판정 기준

- **관측 채널 (trial마다, resume 요청)**: ch1 응답 `cached_tokens`(부재는 server 로그의 `enable_prompt_tokens_details: True`일 때만 0), ch2 `[GPFX] LOOKUP hit`, ch3 resume 구간의 `vllm:prompt_tokens_cached_total`·`vllm:prefix_cache_hits_total` 증분, ch4 KV events(첫 배경 `LOOKUP` 전에 저장된 T block 중 resume `LOOKUP` 전에 `BlockRemoved`된 수).
- **trial 유효성**: lifecycle 유효(GPU 0 외 process 없음), `num_preemptions` 증분 0, `ALLOC_FAIL` 0, `LOOKUP` 수 = 요청 수, flag True. 무효 trial은 확증에 들지 않는다.
- **채널 일치**: ch1 = ch2 = ch3(둘 다), ch4 = 예측 T blocks evicted.
- **확증 (`CONFIRMED`)**: **60/60 trial이 유효하고, 채널이 일치하며, ch1 = 예측 hit(정확한 정수).** 허용 오차 없음.
- **허용 범위를 두지 않는 근거**: 순차 프로토콜에서 client는 응답을 받은 뒤 다음 요청을 보내고, 끝난 요청의 block 반납(`scheduler.py:1480` → `:1862`)은 그 응답을 내보내기 전 같은 `update_from_output` 안에서 일어난다. async scheduling은 step 겹침만 바꾸고 block 순서 규칙은 바꾸지 않는다. warmup step은 KV pool을 쓰지 않는다(GTASK03: 첫 `LOOKUP` 시 free = 가용 전량). 따라서 source 상 비결정 경로를 찾지 못했다.

## 실패 시 결론 (사전 기록)

- **불일치가 하나라도 있으면 `CONFIRMED`가 아니다.** 그 trial의 사건 순서(`[GPFX]` LOOKUP/ALLOC와 free block 수, KV events의 저장·축출 순서)로 어느 가정이 깨졌는지 특정한다: (a) 미사용 block 우선(초기 queue 순서), (b) release 역순(tail-first), (c) 생성 token 캐시·`P+g−1` 계산량, (d) 조회 후 할당·hit 선보호, (e) chunk/budget에 따른 할당 시점. 예측을 사후에 고쳐 맞히지 않는다.
- 계단의 **위치**만 어긋나고 형태(16 token 계단, token 총량 문턱)가 맞으면 "형태 확증·상수 실패"로 보고한다. 형태까지 어긋나면 LRU·block 단위라는 GPU 의미론 읽기가 틀린 것이다.
- ch1과 다른 채널이 어긋나면 해당 trial은 관측 채널 문제(`INVALID`)이며 모형 판정에 쓰지 않는다.

## 실행 절차

```bash
bash experiments/gpu/patches/vllm-0.22.0/apply.sh apply     # hash guard
RUN=/home/csdc/kyeom/Project/escapement/results/gpu/survival/<UTC>
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/survival/survival_run.py --out-dir "$RUN"
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/survival/survival_judge.py \
  --run-dir "$RUN" --pred <repo>/experiments/gpu/survival/prediction/predictions.json --out "$RUN/verdict.json"
```

trial 실패(예외)는 기록하고 재시도하지 않는다. 실행 중 script를 편집하지 않는다(KNOWN_PITFALLS 5).
