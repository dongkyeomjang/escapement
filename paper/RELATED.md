# Related work — 문제 분류학으로 배치한다

이 절의 뼈대는 시스템 나열이 아니라 **문제 분류학**이다.

> **레버는 두 종류다. 분포 추정으로 충분한 레버와, 개별 draw를 맞혀야 하는 레버.**

- **분포로 충분한 레버**: "이 도구가 평균 얼마나 걸리는가"만 알면 값이 결정되는 레버. KV cache를 얼마나 붙들어 둘지(TTL pin), 어느 tier에 둘지, 어느 순서로 evict할지. **평균이나 그 상한이 틀려도 손해가 완만하고 방향이 유지된다.**
- **개별 draw가 필요한 레버**: "이 세션이 *언제* 돌아오는가"를 맞혀야 값이 결정되는 레버. 반환 시각 재배치, 보류-후-군집화. **draw를 못 맞히면 이득이 0이 아니라 음수가 된다.**

이 연구의 음성 결과([TASK27](../docs/research/TASK27.md)·[TASK31](../docs/research/TASK31.md)·[TASK32](../docs/research/TASK32.md))는 두 번째 종류의 레버를 대상으로 한 것이고, 선행 연구 대부분의 성공은 첫 번째 종류의 레버 위에 있다. **그러므로 우리 음성 결과는 그들의 접근을 반박하지 않고 설명한다** — 왜 그들이 거친 분포 추정으로도 잘 작동하는지, 그리고 왜 그 성공을 반환 재배치로 연장하면 무너지는지.

---

## 1. 최근접 선행 — 문제의식이 가장 가까운 두 편

아래 두 편은 이 연구와 **문제의식이 겹치는 지점이 가장 넓다.** 하나는 "구성을 골라야 한다"를, 다른 하나는 "agent serving을 시뮬레이션해야 한다"를 우리보다 먼저 또는 나란히 제기했다. **선행을 인정하고, 겹치지 않는 지점을 특정한다.**

### LENS — arXiv:2606.18042

*Latency Prediction for LLM Inference on NPU Systems*. Juhyun Park, Seungwoo Jeong, Jingyu Lee, Kyungyong Lee. v1 2026-06-16, v2 06-17. LENS = Latency Estimator for NPU Systems. microarchitecture·compiler 정보 없이 NPU 추론 지연을 예측하며 **bucketing이 유발하는 비선형 지연을 명시적으로 포착**한다. bucket당 end-to-end 측정 2회로 프로파일해 입력·출력 길이 조합을 합성하고, 여러 NPU 벤더·LLM에서 평균 오차 2.15 %.

| | |
|---|---|
| **공유하는 문제의식** | **NPU의 이산 bucket 격자가 성능을 비선형으로 만들고, 그 비선형성을 모르면 구성을 고를 수 없다.** LENS는 그 비선형성을 예측 가능하게 만들었고, 우리는 그 위에서 구성을 고른다. **격자가 일급 대상이라는 인식은 LENS가 우리보다 명시적으로 먼저 세웠다.** |
| **우리와 다른 것** | (i) 예측 대상이 **stateless 단일 요청 지연**이다 — 입력·출력 길이가 주어지면 값이 나온다. 우리 대상은 **여러 세션의 도착 과정이 만드는 동역학**이고, 입력은 길이가 아니라 동시 요청 **수의 시간 전개**다. (ii) 목적함수가 다르다 — LENS는 지연·throughput을, 우리는 **tool gap 아래에서의 device time**을 최소화한다. (iii) **KV slot = 캐시 생존 축이 LENS의 모형에 없다.** 요청 하나의 지연은 그 요청이 몇 번째 slot을 쓰는지에 의존하지 않기 때문이다. |
| **왜 그 차이가 본질적인가** | **우리 이득의 지배 인자가 stateless 관점에서 구조적으로 비가시이기 때문이다.** [TASK35](../docs/research/TASK35.md)의 절제는 `batch_size` 8→16의 +9.7 %에서 **+8.25 %p가 KV pool 크기**에서, 나머지가 격자 정합에서 온다고 말한다. 그런데 `batch_size`는 요청 하나의 지연을 거의 바꾸지 않는다 — 그것이 바꾸는 것은 **다른 세션의 캐시가 살아남는가**이고, 그 효과는 세션이 하나뿐인 모형에서는 정의되지 않는다. 즉 LENS의 축을 아무리 정밀하게 만들어도 우리 이득의 8할은 그 축에 나타나지 않는다. **두 결과는 경쟁하지 않고 직교한다.** |

**주의**: LENS의 2.15 %는 단일 요청 지연의 오차이고 우리 시뮬레이터의 0.0040은 pooled ratio의 오차다. **같은 양이 아니므로 나란히 비교하지 않는다.**

### AgentServeSim — arXiv:2606.09613

*AgentServeSim: A Hardware-aware Simulator for Multi-Turn LLM Agent Serving*. Rakibul Hasan Rajib, Mengxin Zheng, Qian Lou. v1 2026-06-08, v2 06-18. 다중 턴 agent의 실행 동역학을 프로그램 수준에서 모사한다 — 스케줄링, KV-cache 관리, 라우팅 정책, **턴 간 캐시 지역성과 tool gap 동안의 KV 잔존**을 담고, HBM ↔ host DRAM/CXL ↔ eviction의 메모리 계층을 추적하며 commodity CPU에서 돈다.

| | |
|---|---|
| **공유하는 문제의식** | **agent serving의 정책 질문은 실측으로 답하기에 조합이 너무 많으므로 시뮬레이터가 필요하다.** tool gap 동안의 KV 잔존을 모형의 일급 대상으로 삼은 것까지 같다. **"시뮬레이터가 필요하다"는 착상 자체는 우리 고유의 것이 아니다.** |
| **우리와 다른 것** | (i) **대상 substrate**가 다르다 — GPU의 동적 runtime(연속 batching, LRU/block 회수, 메모리 계층)이 대상인 반면, 우리 모형은 **compile 시점에 고정되는 기전**(이산 bucket 격자, 시퀀스 단위 FIFO slot, 배타 prefill)을 담는다. (ii) **검증 방식**이 다르다 — 우리는 **보정 파라미터 0개**로 선등록된 out-of-sample device 예측([TASK25](../docs/research/TASK25.md))과 **제어 개입이 들어간 조건의 예측**([TASK28](../docs/research/TASK28.md)·[TASK35](../docs/research/TASK35.md)·[TASK36](../docs/research/TASK36.md))을 통과시켰다. (iii) **용도**가 다르다 — 정책 비교가 아니라 **compile 구성 탐색**이며, 그 탐색 결과를 재compile로 실기기에 적용해 확증했다. |
| **왜 그 차이가 본질적인가** | **시뮬레이터의 신규성은 "있다"가 아니라 "무보정으로 device를 예측한다"에 있다.** 보정 파라미터가 있는 모형은 관측을 재현할 수 있어도, 아직 존재하지 않는 구성의 device time을 미리 말할 수 없다. 이 연구의 처방 절 전체가 그 능력에 서 있다 — 구성을 device 실측 없이 고르고, 고른 뒤 한 번 재compile해서 맞는지 확인했다. **AgentServeSim과 우리 모형은 같은 도구 범주에 있으나 서로 다른 주장을 지지한다.** |

---

## 2. 상보 배치 — Continuum / CacheTTL (핵심 대비 대상)

### Continuum (arXiv:2511.02230)

- Hanchen Li, Runyuan He, Qiuyang Mang, Qizheng Zhang, Huanzhi Mao, Xiaokun Chen, Hangrui Zhou, Alvin Cheung, Joseph Gonzalez, Ion Stoica (UC Berkeley / Stanford / Tensormesh / Tsinghua).
- v1 2025-11-04, **현재 v6 2026-05-25**. ICLR 2026 *Lifelong Agents* workshop poster.
- **명칭 주의 (서지 확인 결과)**: **v4에서 제목이 `CacheTTL: …`로 바뀌었다가 v5·v6에서 `Continuum: …`으로 되돌아왔다.** 즉 **현재 arXiv 최신판의 시스템 이름은 다시 `Continuum`이다.** 인용 시 어느 버전을 가리키는지 명시한다. (이 사실이 [결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌)의 명칭 충돌을 **여전히 살아 있는 것**으로 만든다.)
- 기여: 도구 호출 pause 동안 KV cache를 GPU에 붙들어 두는 **동적 TTL**과 program-level scheduling. JCT 최대 8배 개선.

### 왜 상보인가

| 축 | Continuum | 이 연구 |
|---|---|---|
| 레버의 종류 | **분포로 충분** — TTL pin. `τ*`를 도구별 경험적 CDF에서 고른다(§4.2) | **개별 draw가 필요** — 반환 시각 재배치 |
| 필요한 추정 | 평균의 상한 `B(δ)` 정도 | 개별 반환 시각 |
| 추정이 틀렸을 때 | TTL이 조금 길거나 짧을 뿐, 손해가 완만 | 이득이 **음수**가 된다([TASK28](../docs/research/TASK28.md): X = −105 %·−70 %) |
| 우리 실측 | §4.2의 추정자를 **그대로 차용**해 재보니 오차가 문턱을 5.6–9.7배 초과하고 표본을 4자릿수 늘려도 줄지 않는다([TASK32](../docs/research/TASK32.md)) | — |
| 결론 | **모순이 아니다.** `B(δ)`와 `μ̂`의 오차 std가 같다(10.196 대 10.185)는 우리 관측이 바로 "평균 추정으로는 충분하고 draw 추정으로는 부족하다"는 뜻이다 | — |

**본문에 넣을 한 문장**: "이 논문의 음성 결과는 Continuum의 접근을 반박하는 것이 아니라 **그것이 왜 통하는지를 설명한다** — TTL은 분포의 문제이고 반환 재배치는 draw의 문제이며, 같은 추정자가 앞에서는 충분하고 뒤에서는 원리적으로 부족하다."

**substrate 차이도 명시한다**: Continuum은 GPU·chunked prefill·LRU/block 회수 위에 있고, 이 연구는 NPU·배타 prefill·시퀀스 단위 FIFO 위에 있다. [TASK29](../docs/research/TASK29.md)의 절제가 그 세 축의 차이가 결과를 어디까지 바꾸는지 계산했다.

---

## 3. GPU agentic KV 관리 계열 — 도구 유휴 구간을 자원 문제로 다룬다

| 시스템 | 서지 | 레버 | 이 연구와의 관계 |
|---|---|---|---|
| **MORI** | arXiv:2606.00866, *Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with MORI*, 2026 | 유휴도로 프로그램을 **순위 매겨** GPU HBM ↔ CPU DRAM 분할 경계를 움직인다. Claude Code 워크로드에서 throughput +20–71 %, TTFT −18–43 % | **분포로 충분한 레버.** "이 프로그램이 지금 얼마나 유휴한가"는 순위만 맞으면 되고 개별 복귀 시각을 요구하지 않는다. 우리 [TASK31](../docs/research/TASK31.md)이 실측한 "도구 호출의 71 %가 1초 미만"이라는 분포 성질이 이 계열의 전제를 직접 지지한다 |
| **KVFlow** | arXiv:2507.07400, Pan et al., **NeurIPS 2025** | agent step graph의 **steps-to-execution**으로 eviction을 점수화하고 prefetch를 겹친다. SGLang hierarchical radix cache 대비 1.83–2.19배 | **분포로 충분** + **구조 정보**. 미래 실행 *순서*는 그래프에서 오지 draw 추정에서 오지 않는다. 우리 기전 ②(생존)의 회수 정책 축을 바꾸는 접근이며, [TASK29](../docs/research/TASK29.md) 절제의 "LRU로 바꾸면 문턱이 크기에 반비례"와 같은 축에 있다 |
| **CacheScout** (2편, **같은 시스템**) | arXiv:**2605.27744** *A Policy-Driven Runtime Layer for Agentic LLM Serving*(Zhang·Kim·Hu, 2026-05-26, rev 07-30)가 `observe / score / predict / act` 네 primitive의 **runtime 계층 구조**를 제시하고, arXiv:**2608.14624** *Learning Agent Execution for KV-Cache Management in Agentic Serving*(Zhang, Kim, Feng, Du, Liu, Zhong, Ching, Jiang, Hu, 2026-07-16)가 그 위의 **학습된 전이**를 다룬다. **두 편을 별개 시스템으로 세지 않는다** | agent 실행 전이를 **online 학습**해 eviction과 prefetch를 유도한다. vLLM 위 구현, hit rate +10–18 %p, TTFT −18–45 % | **분포로 충분** — 학습 대상이 *전이 구조*이지 *지속시간 draw*가 아니다([TASK32](../docs/research/TASK32.md)의 음성 결과가 닿지 않는 종류의 학습이다). **그러나 이 계열 전체와 함께 하나의 전제 위에 서 있다: eviction 정책이 조정 가능하다는 전제다.** 이 연구의 substrate에서는 층 2 회수가 시퀀스 단위 **FIFO로 하드코딩**돼 있고(`LRUEvictionPolicy` 클래스는 존재하나 사용되지 않는다, [TASK14](../docs/research/TASK14.md)), **그 전제가 성립하지 않는다.** 그래서 같은 목표(재사용 보존)를 정책이 아니라 **pool 크기와 격자**로 사야 했고, 그것이 이 논문이 compile-time에 도달한 경로다 |
| **SAGA** | arXiv:2605.00528, *Workflow-Atomic Scheduling for AI Agent Inference on GPU Clusters*, Guo et al., 2026 | Agent Execution Graph 기반 workflow-atomic 스케줄링 + tool-aware TTL + task-level fairness | 구조 정보를 **프레임워크가 선언**해 주는 경우. 우리 연구는 그런 선언이 없는 조건을 다뤘고, [TASK33](../docs/research/TASK33.md)의 "조율" 항이 바로 이 선언이 채워 줄 수 있는 부분이다 |
| **ThunderAgent** | arXiv:2602.13692, *A Simple, Fast and Program-Aware Agentic Inference System*, Kang, Li, Xu, Yang, Chen, Wang, Chen, Krishna, Xu, Arora. v1 2026-02-14, v3 06-30 | program-aware scheduler + tool resource manager. serving 1.5–3.6배, RL rollout 1.8–3.9배 | 위와 같은 계열. **ICML 2026 virtual 목록에 등재돼 있으나 arXiv abs 페이지에는 채택 등급 표기가 없다 — "Spotlight"는 확인되지 않아 쓰지 않는다** |
| **Leyline** | arXiv:2606.01065, *KV Cache Directives for Agentic Inference*, 2026 | 응용이 KV cache에 **directive**를 내리는 인터페이스 | 조율을 **응용에게 넘기는** 설계. [TASK33](../docs/research/TASK33.md)의 조율 축에 대한 또 하나의 답 |

| **KAIROS** | arXiv:2604.16682, *KAIROS: Stateful, Context-Aware Power-Efficient Agentic Inference Serving*, Yuan·Chowdhury·Talati, 2026-04-17 | agent context를 일급 제어 변수로 삼아 **GPU 주파수·인스턴스별 동시성·요청 배치**를 함께 조정한다. 성능 목표를 지키며 평균 27 %(최대 39.8 %) 전력 절감 | **목적함수가 다른 계열** — device time이 아니라 **전력**이다. 그러나 조정 대상 중 하나가 **인스턴스별 동시성**이어서 이 연구의 `max_num_seqs`·`batch_size` 축과 만난다. **동시성이 성능뿐 아니라 전력의 레버이기도 하다는 것은 이 연구가 재지 않은 축이며 한계 절에 적는다** |

**이 계열 전체에 대한 한 문장**: 이들은 모두 **회수·배치 정책을 바꿀 수 있다**는 전제 위에 있다. KVFlow는 eviction 점수를, CacheScout는 학습된 전이를, MORI는 tier 경계를, Leyline은 응용의 directive를 쓴다. 이 연구의 substrate는 그 전제를 주지 않는다 — 층 2 회수가 시퀀스 단위 FIFO로 고정돼 있다. **그 제약이 이 연구를 정책 축에서 밀어내 구성 축으로 보냈고, 그래서 이 논문의 결론은 그들과 경쟁하는 것이 아니라 그들의 전제가 없을 때 무엇이 남는지에 대한 답이다.**

---

## 4. 프로그램 단위 스케줄링 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Autellix** | arXiv:2502.13965, *An Efficient Serving Engine for LLM Agents as General Programs*, Luo·Shi et al., 2025 | 프로그램을 일급 시민으로 두고 HoL blocking을 없앤다. vLLM 대비 throughput 4–15배. **이 연구의 층 아래** — 우리는 스케줄링 순서가 아니라 그 순서가 부딪히는 **compiled 격자와 slot 회계**를 다룬다 |
| **SMetric** | arXiv:2607.08565, *Rethink LLM Scheduling for Serving Agents with Balanced Session-centric Scheduling* | session-centric 스케줄링. [TASK33](../docs/research/TASK33.md)이 "조율이 가능한 유일한 runtime 위치"로 지목한 server-side scheduler 계열이며, **우리가 열지 않은 경로**다 |

---

## 5. 같은 substrate 계열 — NPU와 정적 그래프

이 절의 두 논문은 위 세 절과 층이 다르다. agentic 워크로드가 아니라 **NPU·정적 그래프 substrate 자체**를 다루며, 이 연구가 기전 ①(격자 정렬)과 기전 ②(slot 회계)를 세운 바로 그 지반 위에 있다.

### 다중 코어 NPU serving 체계 연구 (arXiv:2510.05632)

- Tianhao Zhu, Dahu Feng, Erhu Feng, Yubin Xia. *From Principles to Practice: A Systematic Study of LLM Serving on Multi-core NPUs*. 2025-10-07.
- 기여: 다중 코어 NPU를 위한 **다층 시뮬레이션 프레임워크**(transaction 수준 + 성능 모형 수준)를 세우고, tensor parallelism 전략·코어 배치 정책·메모리 관리·PD-disaggregation 대 PD-fusion을 체계적으로 비교한다. SOTA 대비 1.32–6.03배.
- **관계**: 우리보다 **한 층 아래**를 다룬다 — 코어 배치와 병렬화 전략이 대상이고, 이 연구는 그 아래를 고정한 채(`num_devices=4`, 고정 배치) **워크로드 도착 과정과 compile 격자의 상호작용**을 본다. **NPU의 경직성(SIMT 대비 유연성 부족)이 성능을 정한다는 진단은 공유**하며, 그 진단이 이 연구에서는 "격자와 slot 회계를 compile 시점에 고르는 문제"로 나타난다.
- **[TASK29](../docs/research/TASK29.md)의 일반성 절과의 관계**: 이 논문이 세운 축(코어 배치·병렬화)은 우리 절제가 건드리지 않은 축이다. **우리 결과의 이식성 논의에서 열린 축으로 명시한다.**

### KV-RM (arXiv:2605.09735) — **인용하되 결과에 기대지 않는다**

- Zhiqing Zhong, Zhijing Ye, Jian Zhang, Weijian Zheng, Bolun Sun, Xiaodong Yu. *KV-RM: Regularizing KV-Cache Movement for Static-Graph LLM Serving*. v1 2026-05-10.
- 기여(주장): 정적 그래프 decoder 아래에서 KV-cache 이동을 정규화한다. 논리적 KV 이력과 물리 저장을 분리하고 block pager로 활성 상태를 추적해, 파편화된 KV 사상을 transfer group으로 합쳐 **고정 shape attention kernel**에 넣는다. 가변 요청 길이와 비동기 완료를 정적 그래프가 흡수하게 만든다는 설계다. 평가는 A100 2장.
- **⚠️ 이 논문은 저자에 의해 철회됐다** (v2, 2026-06-30 철회. 사유: 결과 해석과 주요 결론의 근거에 영향을 주는 실질적 오류).
- **그러므로 이 논문의 *수치*나 *성능 주장*은 인용하지 않는다.** 인용하는 것은 **문제 설정**뿐이다 — "고정 shape 커널 위에서 가변 길이와 비동기 완료를 어떻게 흡수할 것인가"는 이 연구가 마주한 것과 같은 문제이고, KV-RM은 그것을 **runtime의 KV 이동 정규화**로 풀려 했다.
- **대비**: 이 연구는 같은 문제에 대해 runtime 경로가 아니라 **compile 시점의 격자·pool 선택**으로 답한다. [TASK33](../docs/research/TASK33.md)이 runtime 회수 경로가 닫힘을 정보 분해로 보인 것이 그 선택의 근거다. 철회된 결과가 어느 방향으로 틀렸는지는 알 수 없으므로 **"runtime 정규화가 실패한다"는 근거로 쓰지 않는다** — 우리 근거는 우리 자신의 [TASK27](../docs/research/TASK27.md)·[TASK28](../docs/research/TASK28.md)·[TASK33](../docs/research/TASK33.md)이다.

---

## 6. 예측을 쓰지 않는 방향 — 우리 결론과 수렴하는 독립 결과

**ConServe** — arXiv:2606.01839, *Observation, Not Prediction: Conversation-Level Disaggregated Scheduling for Agentic Serving*, Ding, Hosseini, Gholami, Xiang, Hoffmann, 2026-06-01.

- 주장: 스케줄링 단위를 turn에서 **conversation으로 올리면** turn 단위 불규칙성이 안정된 2상 구조로 바뀌고, 예측 없이 **관측 가능한 양**(첫 turn 입력 길이, KV 점유)만으로 스케줄링할 수 있다. p95 latency −51 %.
- **이 연구와의 관계**: 서로 다른 substrate·다른 방법으로 **같은 방향의 결론**에 도달한 독립 결과다. 우리는 "개별 draw는 예측 불가"를 예측기 실측으로([TASK32](../docs/research/TASK32.md)), 그들은 "예측이 불필요하도록 단위를 바꾼다"로 답한다. **본문에서 이 논문을 우리 음성 결과의 독립 지지로 인용하고, 우리가 더한 것이 무엇인지 분명히 한다**: 우리는 *왜* 못 맞히는지(환원 불가 분산, 도구 이름이 명령을 담지 않음)와 *못 맞혀도 되는 레버가 어디 있는지*(compile-time)를 제시한다.

---

## 7. 배치 구조와 prefill 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Sarathi-Serve** | arXiv:2403.02310, Agrawal et al., **OSDI '24** | chunked prefill로 stall-free schedule을 만든다. **이 연구의 기전 ③과 정확히 반대 방향의 설계**이고, [TASK29](../docs/research/TASK29.md)의 절제가 그 반대 방향을 계산했다: 정지 항은 0이 되지만 device time이 3–10 % **늘어난다**. 배타 실행의 일부가 강제 동기화를 통한 batching 보조금이었기 때문이다. **본문에서 이 대비를 명시적으로 세운다** |

---

## 8. 서지 확인 상태

| 항목 | 상태 |
|---|---|
| Continuum / CacheTTL 버전별 제목 | **확인** (v1–v3·v5·v6 = Continuum, v4 = CacheTTL). arXiv abs·html 직접 확인 |
| Continuum 저자·소속·ICLR 2026 workshop | **확인** |
| KVFlow NeurIPS 2025 | **확인** |
| ThunderAgent ICML 2026 Spotlight, arXiv:2602.13692 | **확인** |
| Sarathi-Serve OSDI '24 | **확인** |
| Autellix arXiv:2502.13965 | **확인** |
| MORI arXiv:2606.00866 | **확인** |
| SAGA arXiv:2605.00528 | **확인** (저자 전체 목록은 미확인) |
| CacheScout arXiv:2608.14624 | **확인** |
| ConServe arXiv:2606.01839 | **확인** |
| **LENS** arXiv:2606.18042 | **확인** (Advisor 제공 서지로 특정, 2026-08-25). *Latency Prediction for LLM Inference on NPU Systems*, Park·Jeong·Lee·Lee, LENS = Latency Estimator for NPU Systems. **§1 최근접 선행으로 승격 배치** |
| **KV-RM** arXiv:2605.09735 | **확인, 단 철회됨** (Advisor 제공 서지로 특정, 2026-08-25). *KV-RM: Regularizing KV-Cache Movement for Static-Graph LLM Serving*, Zhong·Ye·Zhang·Zheng·Sun·Yu, v1 2026-05-10. **v2가 2026-06-30에 저자에 의해 철회**(결과 해석과 주요 결론의 근거에 영향을 주는 실질적 오류). §5에 배치하되 **수치·성능 주장은 인용하지 않고 문제 설정만 인용**한다 |
| **AgentServeSim** arXiv:2606.09613 | **확인** (2026-08-25). *A Hardware-aware Simulator for Multi-Turn LLM Agent Serving*, Rajib·Zheng·Lou, v1 2026-06-08 / v2 06-18. **§1 최근접 선행** |
| **KAIROS** arXiv:2604.16682 | **확인** (2026-08-25). *Stateful, Context-Aware Power-Efficient Agentic Inference Serving*, Yuan·Chowdhury·Talati, 2026-04-17. §3 |
| **CacheScout 2편이 같은 시스템** arXiv:2605.27744 · 2608.14624 | **확인** (2026-08-25). 저자(Zhang·Kim·Hu)가 겹치고 2605.27744가 runtime 계층 구조를, 2608.14624가 그 위의 학습된 전이를 다룬다. **별개 시스템으로 세지 않는다** |
| **다중 코어 NPU serving 연구** arXiv:2510.05632 | **확인** (2026-08-25). *From Principles to Practice: A Systematic Study of LLM Serving on Multi-core NPUs*, Zhu·Feng·Feng·Xia, 2025-10-07. §5 |
| **ThunderAgent 채택 등급** | **`PARTIAL` — 정정.** ICML 2026 virtual 목록 등재는 확인되나 **arXiv abs 페이지에 채택 등급 표기가 없다.** [TASK38](../docs/research/TASK38.md)이 검색 요약을 근거로 적은 "Spotlight (top 2.2 %)"는 **1차 출처로 확인되지 않아 삭제**했다 |
| ~~KV-RM = CacheScout 잠정 동일시~~ | **정정됨.** [TASK37](../docs/research/TASK37.md)이 서지를 특정하지 못해 CacheScout로 잠정 배치했던 것은 **오류**다. 둘은 서로 다른 논문이며 각각 §4·§2에 별도 배치했다 |

**2026 신규 경쟁작 재확인 결과**: ThunderAgent, SAGA, MORI, CacheScout(2편), ConServe, SMetric, Leyline, LENS, AgentServeSim, KAIROS, KV-RM(철회)이 2026년에 새로 나왔다. **그중 어느 것도 "반환 시각 재배치"를 레버로 삼지 않는다** — 전부 배치·회수·offload·스케줄링 단위, 또는 단일 요청 지연 예측 쪽이다. **이 연구의 음성 결과가 겹치는 선행 결과는 없으며, ConServe만이 같은 방향의 독립 증거다.**

**가장 가까운 두 편과의 교차점이 이 연구의 공백이다.** LENS는 **NPU 격자를** 일급으로 보되 **단일 요청**을 보고, AgentServeSim은 **다중 세션 동역학을** 일급으로 보되 **GPU 동적 runtime**을 본다. **"NPU의 compile-static 격자 × 다중 세션 도착 과정"이라는 교차점을 다룬 선행이 없고, 이 연구의 이득이 정확히 그 교차점에서 나온다** — KV slot 수가 캐시 생존을 정하고 캐시 생존이 prefill 재계산을 정하는 사슬은 단일 요청 모형에도, 동적 회수를 전제하는 모형에도 나타나지 않는다.

**두 개의 전제 차이가 이 연구를 다른 자리에 놓는다.** (1) §2 계열은 **회수 정책을 바꿀 수 있다**고 전제하는데 이 substrate의 층 2는 FIFO로 고정돼 있다. (2) §1의 TTL 계열은 **분포 추정으로 충분한 레버**를 쓰는데 이 연구가 겨눈 반환 재배치는 **개별 draw**를 요구한다. 두 전제가 모두 없을 때 남는 것이 무엇인지가 이 논문의 답이고, 그 답이 compile-time 구성이다.
