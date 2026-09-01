# 실행 모델 명칭의 문헌 조사

이 문서는 **compile 시점에 그래프·shape·자원이 고정되는 가속기 실행 모델**을 기존
문헌이 어떤 용어로 부르는지 정리한다. 기록: [TASK51](TASK51.md).

## 조사 방법과 그 한계

web 검색으로 후보 용어를 찾고, **채택한 정의 문장은 전부 1차 출처에서 직접
가져왔다**(arXiv abs/HTML, 공식 문서, 로컬 site-packages 소스). 검색 요약에만
나오고 1차 출처에서 확인하지 못한 문장은 이 표에 넣지 않았다.

**한계를 먼저 적는다.** 이것은 proceedings 전수 조사가 아니라 keyword 검색이므로
**"없다"는 약한 증거**다. 지시가 지정한 6개 학회(OSDI / SOSP / MLSys / ASPLOS /
ATC / EuroSys) 최근 3년에서 **1차 출처로 확인한 논문은 1편**(llm.npu, ASPLOS '25)
뿐이며, 나머지 근거는 arXiv 프리프린트와 벤더 공식 문서다. 표를 채우기 위해
확인하지 못한 논문을 추가하지 않았다.

## 1. 용어 표

| 용어 | 정의 문장 원문 (1차 출처 확인) | 출처 | 발표처 |
|---|---|---|---|
| **static shapes** | "Mobile NPUs typically support only inference on static shapes, while LLM prompt length is dynamic" / "before the compute graph can be executed on the mobile NPU, it must be built and optimized, a process taking tens of seconds" | llm.npu — *Fast On-device LLM Inference with NPUs*, Xu, Zhang, Yang, Liu, Huang, Xu, Liu, arXiv:2407.05858 | **ASPLOS '25** |
| **fixed at compile time** (+ **bucketing**) | "With Inferentia, the shape of every input must be fixed at compile time." / "Bucketing refers to compiling your model multiple times with different target input shapes to create 'bucketed models.'" | AWS Neuron, *Running inference on variable input shapes with bucketing* | 벤더 공식 문서 |
| **static input shape** | "Autobucketing is a feature that enables you to use multiple bucket models. Each bucket model accepts a static input shape and a bucket kernel function." | AWS Neuron, *Autobucketing for Inference (torch-neuronx)* | 벤더 공식 문서 |
| **static model** | "The resulting module produced by `trace()` will contain a static model that will consume a predictable amount of Neuron device memory and will never require recompilation based on input changes." / "In contrast, since XLA device inference performs just-in-time compilation, it can be more difficult to predict memory utilization…" | AWS Neuron, *Comparison of Traced Inference versus XLA Lazy Tensor Inference* | 벤더 공식 문서 |
| **dynamicity / recompilation** (static shape를 반대편에서 정의) | "Dynamicity, resulting from changing input shapes or dynamic ops, can lead to multiple recompilations, causing a longer training time and reducing performance." / "If there is a large amount of variability in the input data, data padding and/or data bucketing can be used." | Intel Gaudi, *Handling Dynamic Shapes* | 벤더 공식 문서 |
| **bucketing** (지연 비선형성의 원인으로) | "latency non-linearity induced by bucketing" | LENS — *Latency Prediction for LLM Inference on NPU Systems*, Park, Jeong, Lee, Lee, arXiv:2606.18042 | arXiv (2026-06) |
| **cudagraph capture sizes** | 눈금이 코드에 열거된다: `[1, 2, 4] + list(range(8, 256, 8)) + list(range(256, max_cudagraph_capture_size + 1, 16))`. `cudagraph_capture_sizes` = "Sizes to capture cudagraph." | vLLM `config/compilation.py` (이 host의 `vllm 0.22.0+cpu`) | 구현 소스 |
| **static pre-allocation** | "While static pre-allocation preserves memory contiguity, it incurs significant overhead due to worst-case provisioning." | ODMA — *On-Demand Memory Allocation Strategy for LLM Serving on LPDDR-Class Accelerators*, Zou, Wang, Zheng, Yin, Han, arXiv:2512.09427 | arXiv (2025-12, 2026-04 개정) |
| **static batching** (느슨한 용법) | "Deploying LLMs with hundreds of billions of parameters on memory-constrained GPUs exposes significant limitations in static batching methods." | Pang, Li, Wang, arXiv:2503.05248 | arXiv (2025-03) |

### 후보 용어 중 확인되지 않은 것

지시가 제시한 후보 중 아래 넷은 **6개 학회 최근 3년에서 확립된 명칭으로 쓰인 1차
출처를 찾지 못했다.** 일반 컴파일러 용어로는 널리 쓰이지만 이 실행 모델의 *이름*
으로 정착한 근거를 확인하지 못했다는 뜻이다. `UNKNOWN`.

- `AOT-compiled` — 벤더 문서·일반 컴파일러 문맥에서는 쓰이나 서빙 실행 모델의
  명칭으로 확인 실패
- `compiled inference` — 확인 실패
- `graph-captured` — vLLM 문서가 "CUDA graph capture" 동작은 기술하나 실행 모델을
  가리키는 명사구로는 확인 실패
- `compiler-scheduled` — Groq TSP 계열에서 "statically scheduled" / "software-scheduled"
  가 쓰이나 이는 **명령 타이밍의 정적 스케줄링**이지 서빙 구성 고정이 아니며,
  ISCA 2020으로 지시가 정한 학회·기간 밖이다

## 2. 각 용어의 범위 — 그래프 실행만인가, 자원 배분까지인가

| 용어 | 그래프·shape | 자원 배분 (메모리 예약·batch 구성) | 근거 |
|---|---|---|---|
| static shapes (llm.npu) | **○** | ✕ | 입력 shape와 compute graph만 다룬다 |
| fixed at compile time / bucketing (Neuron) | **○** | ✕ | 컴파일 대상은 입력 shape 집합이다 |
| static input shape (Neuron autobucketing) | **○** | ✕ | bucket model당 shape 하나 |
| **static model (Neuron `trace()`)** | **○** | **△** | "predictable amount of Neuron device memory" — **소비량의 예측 가능성**을 명시한다. 다만 서빙 수준의 pool 크기 결정이 아니라 **모형 하나의 메모리 발자국**이다 |
| dynamicity / recompilation (Gaudi) | **○** | ✕ | 재compile 유발 조건만 |
| bucketing (LENS) | **○** | ✕ | 지연 예측을 위한 shape 눈금 |
| cudagraph capture sizes (vLLM) | **○** | **△** | 눈금은 shape이지만 눈금 수가 capture 시점 메모리를 정하고, 기본 상한이 `min(max_num_seqs*2, 512)`로 **동시성 설정에 묶여 있다** |
| **static pre-allocation (ODMA)** | ✕ | **○** | 유일하게 **자원 쪽만** 가리킨다 — "worst-case provisioning" |
| static batching (느슨한 용법) | ✕ | **○**(batch 구성) | 아래 §3 참조 |

**정리**: 확인된 용어들은 **그래프·shape 축**(다수)과 **자원 축**(ODMA)으로 갈리며,
**둘을 하나로 묶어 부르는 확립된 명칭을 찾지 못했다.** 둘을 동시에 언급하는 데
가장 가까운 것은 Neuron의 `static model` 한 문장이지만, 그것도 자원 축이 "모형
하나의 메모리 소비 예측 가능성"에 그친다.

## 3. "static batching"과의 충돌 — 실재하며, 우리에겐 오독을 부른다

**서로 다른 두 뜻이 동시에 유통된다.**

**(가) 주류 뜻 — 실행 시간 성질.** batch 구성이 **그 batch의 수명 동안 고정**되어
전원이 끝나야 다음 batch가 뜨는 방식으로, continuous batching의 반대말이다. Orca
(OSDI '22)가 이 방식을 **request-level scheduling**이라 부르고 자신의 대안을
**iteration-level scheduling**이라 부른다. "static batching"은 Orca 이후의 통속적
호칭으로 보이며, **Orca 본문에 그 표현이 있는지는 확인하지 못했다**(USENIX가
자동 조회를 403으로 차단). `UNKNOWN`.

**(나) 느슨한 뜻 — 설정 값이 고정.** arXiv:2503.05248은 "static batching methods"를
**batch 크기 hyper-parameter가 고정되어 실시간으로 적응하지 못한다**는 뜻으로 쓴다.
이쪽이 우리 용법에 가깝다.

**충돌의 실제 피해**: 우리 substrate를 "static batching"이라 부르면 **(가)로 읽혀
사실과 반대가 된다.** 이 substrate는 compile 시점에 고정된 상한(`batch_size`) *안에서*
**iteration 단위로 계속 batching한다** — `[BUCKET]` step 로그의 `request_nums`가 step
마다 달라지는 것이 그 직접 증거다([TASK12](TASK12.md), [TASK13](TASK13.md)).
고정된 것은 batch **구성**이 아니라 batch **상한과 그에 묶인 KV pool**이다.

**결론: 우리 실행 모델을 `static batching`으로 부르지 않는다.**

## 4. 가장 가까운 기존 용어와 우리가 더 담는 것

**가장 가까운 확립 용어: `static shapes`** (llm.npu, ASPLOS '25 — 지시가 정한 6개
학회에서 1차 출처로 확인한 유일한 용례). 벤더 문서 계열의 `fixed at compile time` /
`bucketing`이 같은 대상을 가리킨다.

**차이 (한 줄)**: `static shapes`는 **텐서 shape만** 고정한다고 말하는 반면, 우리의
`compile-time-static serving substrate`는 그 위에 **서빙 수준의 자원 배분** — compile
인자 `batch_size`가 `kvcache_num_blocks`를 정하고([TASK08](TASK08.md)) 그것이 동시
상주 세션 수와 캐시 생존을 정하는 사슬 — 까지 compile 시점에 고정된다는 것을 담는다.

보조로: `static pre-allocation`(ODMA)이 자원 축을 정확히 가리키지만 **그래프·shape
축이 없고**, 그쪽 문헌은 그 예약을 **runtime에 바꿀 수 있는 것**으로 전제한다. 우리
substrate에서는 재compile 없이 바꿀 수 없다는 점이 그 용어와 갈리는 지점이다.

## 인용 가능한 정의 문장 (1차 출처 확인 완료)

논문에서 그대로 인용할 수 있는 문장만 모았다.

1. **llm.npu, ASPLOS '25** (arXiv:2407.05858) — "Mobile NPUs typically support only
   inference on static shapes, while LLM prompt length is dynamic"
2. **AWS Neuron bucketing app note** — "With Inferentia, the shape of every input must
   be fixed at compile time."
3. **AWS Neuron trace vs XLA** — "The resulting module produced by `trace()` will
   contain a static model that will consume a predictable amount of Neuron device
   memory and will never require recompilation based on input changes."
4. **Intel Gaudi, Handling Dynamic Shapes** — "Dynamicity, resulting from changing input
   shapes or dynamic ops, can lead to multiple recompilations, causing a longer training
   time and reducing performance."
5. **ODMA** (arXiv:2512.09427) — "While static pre-allocation preserves memory
   contiguity, it incurs significant overhead due to worst-case provisioning."

## 확인되지 않은 사항

- Orca (OSDI '22) 본문의 "static batching" 사용 여부 — USENIX 403. `UNKNOWN`
- 6개 학회 최근 3년의 **전수** 조사는 하지 않았다. 확인된 학회 논문 1편은 "그 용어가
  드물다"의 증거가 아니라 "이 검색으로는 하나만 나왔다"의 기록이다
- `AOT-compiled` / `compiled inference` / `graph-captured` / `compiler-scheduled`의
  학회 용례 — 확인 실패, `UNKNOWN`
- LENS(arXiv:2606.18042)와 ODMA(arXiv:2512.09427)의 학회 게재 여부 — comments에
  기재 없음. `UNKNOWN`

## 출처 URL

- https://arxiv.org/abs/2407.05858 (llm.npu, ASPLOS '25)
- https://arxiv.org/abs/2606.18042 (LENS)
- https://arxiv.org/abs/2512.09427 (ODMA)
- https://arxiv.org/abs/2503.05248 (static batching 느슨한 용법)
- https://awsdocs-neuron.readthedocs-hosted.com/en/v1.19.1/neuron-guide/appnotes/perf/bucketing-app-note.html
- https://awsdocs-neuron.readthedocs-hosted.com/en/latest/frameworks/torch/torch-neuronx/programming-guide/inference/autobucketing-dev-guide.html
- https://awsdocs-neuron.readthedocs-hosted.com/en/latest/frameworks/torch/torch-neuronx/programming-guide/inference/trace-vs-xla-lazytensor.html
- https://docs.habana.ai/en/latest/PyTorch/Model_Optimization_PyTorch/Dynamic_Shapes.html
- https://www.usenix.org/conference/osdi22/presentation/yu (Orca — 403, 본문 미확인)
