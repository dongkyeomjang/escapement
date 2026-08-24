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

## 2. 도구 유휴 구간을 자원 문제로 다루는 계열

| 시스템 | 서지 | 레버 | 이 연구와의 관계 |
|---|---|---|---|
| **MORI** | arXiv:2606.00866, *Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with MORI*, 2026 | 유휴도로 프로그램을 **순위 매겨** GPU HBM ↔ CPU DRAM 분할 경계를 움직인다. Claude Code 워크로드에서 throughput +20–71 %, TTFT −18–43 % | **분포로 충분한 레버.** "이 프로그램이 지금 얼마나 유휴한가"는 순위만 맞으면 되고 개별 복귀 시각을 요구하지 않는다. 우리 [TASK31](../docs/research/TASK31.md)이 실측한 "도구 호출의 71 %가 1초 미만"이라는 분포 성질이 이 계열의 전제를 직접 지지한다 |
| **KVFlow** | arXiv:2507.07400, Pan et al., **NeurIPS 2025** | agent step graph의 **steps-to-execution**으로 eviction을 점수화하고 prefetch를 겹친다. SGLang hierarchical radix cache 대비 1.83–2.19배 | **분포로 충분** + **구조 정보**. 미래 실행 *순서*는 그래프에서 오지 draw 추정에서 오지 않는다. 우리 기전 ②(생존)의 회수 정책 축을 바꾸는 접근이며, [TASK29](../docs/research/TASK29.md) 절제의 "LRU로 바꾸면 문턱이 크기에 반비례"와 같은 축에 있다 |
| **SAGA** | arXiv:2605.00528, *Workflow-Atomic Scheduling for AI Agent Inference on GPU Clusters*, Guo et al., 2026 | Agent Execution Graph 기반 workflow-atomic 스케줄링 + tool-aware TTL + task-level fairness | 구조 정보를 **프레임워크가 선언**해 주는 경우. 우리 연구는 그런 선언이 없는 조건을 다뤘고, [TASK33](../docs/research/TASK33.md)의 "조율" 항이 바로 이 선언이 채워 줄 수 있는 부분이다 |
| **ThunderAgent** | arXiv:2602.13692, Kang et al., **ICML 2026 Spotlight** | program-aware scheduler + tool resource manager. serving 1.5–3.6배, RL rollout 1.8–3.9배 | 위와 같은 계열. **2026 신규 경쟁작으로 재확인함** |
| **Leyline** | arXiv:2606.01065, *KV Cache Directives for Agentic Inference*, 2026 | 응용이 KV cache에 **directive**를 내리는 인터페이스 | 조율을 **응용에게 넘기는** 설계. [TASK33](../docs/research/TASK33.md)의 조율 축에 대한 또 하나의 답 |

---

## 3. 프로그램 단위 스케줄링 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Autellix** | arXiv:2502.13965, *An Efficient Serving Engine for LLM Agents as General Programs*, Luo·Shi et al., 2025 | 프로그램을 일급 시민으로 두고 HoL blocking을 없앤다. vLLM 대비 throughput 4–15배. **이 연구의 층 아래** — 우리는 스케줄링 순서가 아니라 그 순서가 부딪히는 **compiled 격자와 slot 회계**를 다룬다 |
| **SMetric** | arXiv:2607.08565, *Rethink LLM Scheduling for Serving Agents with Balanced Session-centric Scheduling* | session-centric 스케줄링. [TASK33](../docs/research/TASK33.md)이 "조율이 가능한 유일한 runtime 위치"로 지목한 server-side scheduler 계열이며, **우리가 열지 않은 경로**다 |
| **CacheScout** | arXiv:2608.14624, *Learning Agent Execution for KV-Cache Management in Agentic Serving*, Zhang et al., 2026-07-16 | agent 실행 전이를 **online 학습**해 eviction·prefetch를 유도. hit rate +10–18 %p, TTFT −18–45 %. 우리 [TASK32](../docs/research/TASK32.md)의 음성 결과와 **대비 지점**: 학습 대상이 *전이 구조*이지 *지속시간 draw*가 아니라는 것이 차이다 |

---

## 4. 예측을 쓰지 않는 방향 — 우리 결론과 수렴하는 독립 결과

**ConServe** — arXiv:2606.01839, *Observation, Not Prediction: Conversation-Level Disaggregated Scheduling for Agentic Serving*, Ding, Hosseini, Gholami, Xiang, Hoffmann, 2026-06-01.

- 주장: 스케줄링 단위를 turn에서 **conversation으로 올리면** turn 단위 불규칙성이 안정된 2상 구조로 바뀌고, 예측 없이 **관측 가능한 양**(첫 turn 입력 길이, KV 점유)만으로 스케줄링할 수 있다. p95 latency −51 %.
- **이 연구와의 관계**: 서로 다른 substrate·다른 방법으로 **같은 방향의 결론**에 도달한 독립 결과다. 우리는 "개별 draw는 예측 불가"를 예측기 실측으로([TASK32](../docs/research/TASK32.md)), 그들은 "예측이 불필요하도록 단위를 바꾼다"로 답한다. **본문에서 이 논문을 우리 음성 결과의 독립 지지로 인용하고, 우리가 더한 것이 무엇인지 분명히 한다**: 우리는 *왜* 못 맞히는지(환원 불가 분산, 도구 이름이 명령을 담지 않음)와 *못 맞혀도 되는 레버가 어디 있는지*(compile-time)를 제시한다.

---

## 5. 배치 구조와 prefill 계열

| 시스템 | 서지 | 배치 |
|---|---|---|
| **Sarathi-Serve** | arXiv:2403.02310, Agrawal et al., **OSDI '24** | chunked prefill로 stall-free schedule을 만든다. **이 연구의 기전 ③과 정확히 반대 방향의 설계**이고, [TASK29](../docs/research/TASK29.md)의 절제가 그 반대 방향을 계산했다: 정지 항은 0이 되지만 device time이 3–10 % **늘어난다**. 배타 실행의 일부가 강제 동기화를 통한 batching 보조금이었기 때문이다. **본문에서 이 대비를 명시적으로 세운다** |

---

## 6. 서지 확인 상태

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
| **LENS** | **`UNKNOWN`.** 지시문이 지목한 `LENS`를 web 검색으로 특정하지 못했다. LLM serving·KV cache·agentic 축의 어느 결과를 가리키는지 **Advisor의 정확한 서지가 필요하다.** 후보로 나온 인접 결과: `ContextPilot`(arXiv:2511.03475, context reuse), `IntentKV`(arXiv:2606.09916) |
| **KV-RM** | **`PARTIAL`.** 이름 그대로의 시스템을 찾지 못했다. 설명이 가장 가까운 것은 **CacheScout**(arXiv:2608.14624, "Learning Agent Execution for **KV-Cache Management**")이며 이 문서는 잠정적으로 그것으로 배치했다. **Advisor 확인 필요** |

**2026 신규 경쟁작 재확인 결과**: ThunderAgent(ICML 2026 Spotlight), SAGA, MORI, CacheScout, ConServe, SMetric, Leyline이 2026년에 새로 나왔다. **그중 어느 것도 "반환 시각 재배치"를 레버로 삼지 않는다** — 전부 배치·회수·offload·스케줄링 단위 쪽이다. **이 연구의 음성 결과가 겹치는 선행 결과는 없으며, ConServe만이 같은 방향의 독립 증거다.**
