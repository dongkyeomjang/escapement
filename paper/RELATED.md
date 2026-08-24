# Related work — 문제 분류학으로 배치한다

이 절의 뼈대는 시스템 나열이 아니라 **문제 분류학**이다.

> **레버는 두 종류다. 분포 추정으로 충분한 레버와, 개별 draw를 맞혀야 하는 레버.**

- **분포로 충분한 레버**: "이 도구가 평균 얼마나 걸리는가"만 알면 값이 결정되는 레버. KV cache를 얼마나 붙들어 둘지(TTL pin), 어느 tier에 둘지, 어느 순서로 evict할지. **평균이나 그 상한이 틀려도 손해가 완만하고 방향이 유지된다.**
- **개별 draw가 필요한 레버**: "이 세션이 *언제* 돌아오는가"를 맞혀야 값이 결정되는 레버. 반환 시각 재배치, 보류-후-군집화. **draw를 못 맞히면 이득이 0이 아니라 음수가 된다.**

이 연구의 음성 결과([TASK27](../docs/research/TASK27.md)·[TASK31](../docs/research/TASK31.md)·[TASK32](../docs/research/TASK32.md))는 두 번째 종류의 레버를 대상으로 한 것이고, 선행 연구 대부분의 성공은 첫 번째 종류의 레버 위에 있다. **그러므로 우리 음성 결과는 그들의 접근을 반박하지 않고 설명한다** — 왜 그들이 거친 분포 추정으로도 잘 작동하는지, 그리고 왜 그 성공을 반환 재배치로 연장하면 무너지는지.

---

## 1. 상보 배치 — Continuum / CacheTTL (핵심 대비 대상)

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

## 2. GPU agentic KV 관리 계열 — 도구 유휴 구간을 자원 문제로 다룬다

| 시스템 | 서지 | 레버 | 이 연구와의 관계 |
|---|---|---|---|
| **MORI** | arXiv:2606.00866, *Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with MORI*, 2026 | 유휴도로 프로그램을 **순위 매겨** GPU HBM ↔ CPU DRAM 분할 경계를 움직인다. Claude Code 워크로드에서 throughput +20–71 %, TTFT −18–43 % | **분포로 충분한 레버.** "이 프로그램이 지금 얼마나 유휴한가"는 순위만 맞으면 되고 개별 복귀 시각을 요구하지 않는다. 우리 [TASK31](../docs/research/TASK31.md)이 실측한 "도구 호출의 71 %가 1초 미만"이라는 분포 성질이 이 계열의 전제를 직접 지지한다 |
| **KVFlow** | arXiv:2507.07400, Pan et al., **NeurIPS 2025** | agent step graph의 **steps-to-execution**으로 eviction을 점수화하고 prefetch를 겹친다. SGLang hierarchical radix cache 대비 1.83–2.19배 | **분포로 충분** + **구조 정보**. 미래 실행 *순서*는 그래프에서 오지 draw 추정에서 오지 않는다. 우리 기전 ②(생존)의 회수 정책 축을 바꾸는 접근이며, [TASK29](../docs/research/TASK29.md) 절제의 "LRU로 바꾸면 문턱이 크기에 반비례"와 같은 축에 있다 |
| **CacheScout** | arXiv:2608.14624, *Learning Agent Execution for KV-Cache Management in Agentic Serving*, Zhang, Kim, Feng, Du, Liu, Zhong, Ching, Jiang, Hu, 2026-07-16 | agent 실행 전이를 **online 학습**해 eviction과 prefetch를 유도한다. vLLM 위 구현, hit rate +10–18 %p, TTFT −18–45 % | **분포로 충분** — 학습 대상이 *전이 구조*이지 *지속시간 draw*가 아니다([TASK32](../docs/research/TASK32.md)의 음성 결과가 닿지 않는 종류의 학습이다). **그러나 이 계열 전체와 함께 하나의 전제 위에 서 있다: eviction 정책이 조정 가능하다는 전제다.** 이 연구의 substrate에서는 층 2 회수가 시퀀스 단위 **FIFO로 하드코딩**돼 있고(`LRUEvictionPolicy` 클래스는 존재하나 사용되지 않는다, [TASK14](../docs/research/TASK14.md)), **그 전제가 성립하지 않는다.** 그래서 같은 목표(재사용 보존)를 정책이 아니라 **pool 크기와 격자**로 사야 했고, 그것이 이 논문이 compile-time에 도달한 경로다 |
| **SAGA** | arXiv:2605.00528, *Workflow-Atomic Scheduling for AI Agent Inference on GPU Clusters*, Guo et al., 2026 | Agent Execution Graph 기반 workflow-atomic 스케줄링 + tool-aware TTL + task-level fairness | 구조 정보를 **프레임워크가 선언**해 주는 경우. 우리 연구는 그런 선언이 없는 조건을 다뤘고, [TASK33](../docs/research/TASK33.md)의 "조율" 항이 바로 이 선언이 채워 줄 수 있는 부분이다 |
| **ThunderAgent** | arXiv:2602.13692, Kang et al., **ICML 2026 Spotlight** | program-aware scheduler + tool resource manager. serving 1.5–3.6배, RL rollout 1.8–3.9배 | 위와 같은 계열. **2026 신규 경쟁작으로 재확인함** |
| **Leyline** | arXiv:2606.01065, *KV Cache Directives for Agentic Inference*, 2026 | 응용이 KV cache에 **directive**를 내리는 인터페이스 | 조율을 **응용에게 넘기는** 설계. [TASK33](../docs/research/TASK33.md)의 조율 축에 대한 또 하나의 답 |

**이 계열 전체에 대한 한 문장**: 이들은 모두 **회수·배치 정책을 바꿀 수 있다**는 전제 위에 있다. KVFlow는 eviction 점수를, CacheScout는 학습된 전이를, MORI는 tier 경계를, Leyline은 응용의 directive를 쓴다. 이 연구의 substrate는 그 전제를 주지 않는다 — 층 2 회수가 시퀀스 단위 FIFO로 고정돼 있다. **그 제약이 이 연구를 정책 축에서 밀어내 구성 축으로 보냈고, 그래서 이 논문의 결론은 그들과 경쟁하는 것이 아니라 그들의 전제가 없을 때 무엇이 남는지에 대한 답이다.**

---

## 3. 프로그램 단위 스케줄링 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Autellix** | arXiv:2502.13965, *An Efficient Serving Engine for LLM Agents as General Programs*, Luo·Shi et al., 2025 | 프로그램을 일급 시민으로 두고 HoL blocking을 없앤다. vLLM 대비 throughput 4–15배. **이 연구의 층 아래** — 우리는 스케줄링 순서가 아니라 그 순서가 부딪히는 **compiled 격자와 slot 회계**를 다룬다 |
| **SMetric** | arXiv:2607.08565, *Rethink LLM Scheduling for Serving Agents with Balanced Session-centric Scheduling* | session-centric 스케줄링. [TASK33](../docs/research/TASK33.md)이 "조율이 가능한 유일한 runtime 위치"로 지목한 server-side scheduler 계열이며, **우리가 열지 않은 경로**다 |

---

## 4. 같은 substrate 계열 — 격자와 정적 그래프를 다루는 결과

이 절의 두 논문은 위 세 절과 층이 다르다. agentic 워크로드가 아니라 **NPU·정적 그래프 substrate 자체**를 다루며, 이 연구가 기전 ①(격자 정렬)과 기전 ②(slot 회계)를 세운 바로 그 지반 위에 있다.

### LENS (arXiv:2606.18042) — **상보 배치**

- Juhyun Park, Seungwoo Jeong, Jingyu Lee, Kyungyong Lee. *Latency Prediction for LLM Inference on NPU Systems*. 2026-06-16 (v2 06-17). LENS = Latency Estimator for NPU Systems.
- 기여: microarchitecture나 compiler 정보 없이 NPU 추론 지연을 예측한다. **bucketing이 유발하는 비선형 지연을 명시적으로 포착**하며, bucket당 end-to-end 측정 2회로 프로파일해 입력·출력 길이 조합 전체를 합성한다. 여러 NPU 벤더·LLM에서 평균 예측 오차 2.15 %.
- **상보인 이유 — 같은 bucket 구조를 서로 다른 축에서 본다.**

| 축 | LENS | 이 연구 |
|---|---|---|
| 예측 대상 | **단일 요청의 latency**. 입력·출력 길이가 주어졌을 때 bucketing이 만드는 비선형 지연 | **시스템 거동**. 그 bucket 구조가 **agentic 도착 과정과 상호작용**할 때 device time이 어떻게 움직이는가 |
| 입력 | 요청의 길이 | 동시 요청 **수**의 시간 전개(= 반환 도착 과정) |
| bucket의 역할 | 예측해야 할 **비선형성의 원인** | 워크로드와 **정렬되거나 어긋나는 격자**이며, 그 정렬이 gap 효과의 **부호**를 정한다 ([TASK23](../docs/research/TASK23.md)) |
| 개입 여부 | 없음(예측기) | **격자를 재compile로 바꾸는 개입**으로 인과를 확정하고, 그 격자를 처방으로 되돌린다 |

**본문에 넣을 한 문장**: "LENS는 bucket이 **한 요청의 지연**에 무엇을 하는지를 예측 가능하게 만들었다. 이 논문은 그 같은 bucket 구조가 **여러 세션의 도착 과정과 만날 때** 무엇을 하는지를 묻고, 답이 부호까지 바뀌는 격자 정렬 효과임을 개입으로 보인다. 두 결과는 같은 substrate 성질의 서로 다른 결과이며 어느 쪽도 다른 쪽을 함의하지 않는다."

**주의**: LENS의 2.15 % 오차는 **단일 요청 latency**에 대한 값이다. 이 연구의 시뮬레이터 오차(pooled ratio 최대 0.0040)와 **같은 양이 아니므로 나란히 비교하지 않는다.**

### KV-RM (arXiv:2605.09735) — **인용하되 결과에 기대지 않는다**

- Zhiqing Zhong, Zhijing Ye, Jian Zhang, Weijian Zheng, Bolun Sun, Xiaodong Yu. *KV-RM: Regularizing KV-Cache Movement for Static-Graph LLM Serving*. v1 2026-05-10.
- 기여(주장): 정적 그래프 decoder 아래에서 KV-cache 이동을 정규화한다. 논리적 KV 이력과 물리 저장을 분리하고 block pager로 활성 상태를 추적해, 파편화된 KV 사상을 transfer group으로 합쳐 **고정 shape attention kernel**에 넣는다. 가변 요청 길이와 비동기 완료를 정적 그래프가 흡수하게 만든다는 설계다. 평가는 A100 2장.
- **⚠️ 이 논문은 저자에 의해 철회됐다** (v2, 2026-06-30 철회. 사유: 결과 해석과 주요 결론의 근거에 영향을 주는 실질적 오류).
- **그러므로 이 논문의 *수치*나 *성능 주장*은 인용하지 않는다.** 인용하는 것은 **문제 설정**뿐이다 — "고정 shape 커널 위에서 가변 길이와 비동기 완료를 어떻게 흡수할 것인가"는 이 연구가 마주한 것과 같은 문제이고, KV-RM은 그것을 **runtime의 KV 이동 정규화**로 풀려 했다.
- **대비**: 이 연구는 같은 문제에 대해 runtime 경로가 아니라 **compile 시점의 격자·pool 선택**으로 답한다. [TASK33](../docs/research/TASK33.md)이 runtime 회수 경로가 닫힘을 정보 분해로 보인 것이 그 선택의 근거다. 철회된 결과가 어느 방향으로 틀렸는지는 알 수 없으므로 **"runtime 정규화가 실패한다"는 근거로 쓰지 않는다** — 우리 근거는 우리 자신의 [TASK27](../docs/research/TASK27.md)·[TASK28](../docs/research/TASK28.md)·[TASK33](../docs/research/TASK33.md)이다.

---

## 5. 예측을 쓰지 않는 방향 — 우리 결론과 수렴하는 독립 결과

**ConServe** — arXiv:2606.01839, *Observation, Not Prediction: Conversation-Level Disaggregated Scheduling for Agentic Serving*, Ding, Hosseini, Gholami, Xiang, Hoffmann, 2026-06-01.

- 주장: 스케줄링 단위를 turn에서 **conversation으로 올리면** turn 단위 불규칙성이 안정된 2상 구조로 바뀌고, 예측 없이 **관측 가능한 양**(첫 turn 입력 길이, KV 점유)만으로 스케줄링할 수 있다. p95 latency −51 %.
- **이 연구와의 관계**: 서로 다른 substrate·다른 방법으로 **같은 방향의 결론**에 도달한 독립 결과다. 우리는 "개별 draw는 예측 불가"를 예측기 실측으로([TASK32](../docs/research/TASK32.md)), 그들은 "예측이 불필요하도록 단위를 바꾼다"로 답한다. **본문에서 이 논문을 우리 음성 결과의 독립 지지로 인용하고, 우리가 더한 것이 무엇인지 분명히 한다**: 우리는 *왜* 못 맞히는지(환원 불가 분산, 도구 이름이 명령을 담지 않음)와 *못 맞혀도 되는 레버가 어디 있는지*(compile-time)를 제시한다.

---

## 6. 배치 구조와 prefill 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Sarathi-Serve** | arXiv:2403.02310, Agrawal et al., **OSDI '24** | chunked prefill로 stall-free schedule을 만든다. **이 연구의 기전 ③과 정확히 반대 방향의 설계**이고, [TASK29](../docs/research/TASK29.md)의 절제가 그 반대 방향을 계산했다: 정지 항은 0이 되지만 device time이 3–10 % **늘어난다**. 배타 실행의 일부가 강제 동기화를 통한 batching 보조금이었기 때문이다. **본문에서 이 대비를 명시적으로 세운다** |

---

## 7. 서지 확인 상태

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
| **LENS** arXiv:2606.18042 | **확인** (Advisor 제공 서지로 특정, 2026-08-25). *Latency Prediction for LLM Inference on NPU Systems*, Park·Jeong·Lee·Lee, LENS = Latency Estimator for NPU Systems. §4에 **상보 배치** |
| **KV-RM** arXiv:2605.09735 | **확인, 단 철회됨** (Advisor 제공 서지로 특정, 2026-08-25). *KV-RM: Regularizing KV-Cache Movement for Static-Graph LLM Serving*, Zhong·Ye·Zhang·Zheng·Sun·Yu, v1 2026-05-10. **v2가 2026-06-30에 저자에 의해 철회**(결과 해석과 주요 결론의 근거에 영향을 주는 실질적 오류). §4에 배치하되 **수치·성능 주장은 인용하지 않고 문제 설정만 인용**한다 |
| ~~KV-RM = CacheScout 잠정 동일시~~ | **정정됨.** [TASK37](../docs/research/TASK37.md)이 서지를 특정하지 못해 CacheScout로 잠정 배치했던 것은 **오류**다. 둘은 서로 다른 논문이며 각각 §4·§2에 별도 배치했다 |

**2026 신규 경쟁작 재확인 결과**: ThunderAgent(ICML 2026 Spotlight), SAGA, MORI, CacheScout, ConServe, SMetric, Leyline, LENS, KV-RM(철회)이 2026년에 새로 나왔다. **그중 어느 것도 "반환 시각 재배치"를 레버로 삼지 않는다** — 전부 배치·회수·offload·스케줄링 단위, 또는 단일 요청 지연 예측 쪽이다. **이 연구의 음성 결과가 겹치는 선행 결과는 없으며, ConServe만이 같은 방향의 독립 증거다.**

**두 개의 전제 차이가 이 연구를 다른 자리에 놓는다.** (1) §2 계열은 **회수 정책을 바꿀 수 있다**고 전제하는데 이 substrate의 층 2는 FIFO로 고정돼 있다. (2) §1의 TTL 계열은 **분포 추정으로 충분한 레버**를 쓰는데 이 연구가 겨눈 반환 재배치는 **개별 draw**를 요구한다. 두 전제가 모두 없을 때 남는 것이 무엇인지가 이 논문의 답이고, 그 답이 compile-time 구성이다.
