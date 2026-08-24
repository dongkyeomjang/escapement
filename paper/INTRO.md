# Introduction 초고

시스템 명칭 **`Escapement`**. 구조는 [OUTLINE.md](OUTLINE.md)의 3막을 따르고, 각 문단이 지지하는 주장은 [CLAIMS.md](CLAIMS.md)의 번호를 단다.

**이 문서의 현재 상태**: §4 포지셔닝 문단만 완고이고 나머지는 골격이다. 포지셔닝을 먼저 쓴 이유는 [RELATED.md §1](RELATED.md#1-최근접-선행--문제의식이-가장-가까운-두-편)의 최근접 선행 재조사가 **서론이 무엇을 주장할 수 있는지의 경계를 바꿨기** 때문이다.

---

## §1. 문제 — (골격)

Agentic 워크로드가 LLM 호출 사이에 도구 실행을 끼워 넣고, 그 구간이 끝난 뒤 세션이 *언제* 돌아오는가가 서빙 비용을 정한다. 주장 1.1–1.13.

## §2. 이 논문이 재는 것 — (골격)

반환 도착 과정을 실기기에서 세 기전으로 분해하고, 그 위에서 headroom의 도달 가능성을 정보 축으로 가른 뒤, 도달 가능한 유일한 지점을 집행한다. 주장 2.1–2.6, 3.1–3.9.

## §3. 기여 — (골격)

(i) 세 기전의 실기기 분해와 재compile 개입에 의한 인과 확정, (ii) 보정 파라미터 0개 시뮬레이터의 선등록 out-of-sample 검증, (iii) headroom의 정보 분해와 per-session runtime 정책의 원리적 한계, (iv) compile-time 구성의 device 확증.

---

## §4. 선행 연구와의 위치 — **완고**

### 국문

이 논문이 딛고 선 두 인식은 이미 문헌에 있다. **LENS**(arXiv:2606.18042)는 NPU의 이산 bucket 격자가 지연을 비선형으로 만든다는 것을 명시하고 그 비선형성을 예측 가능하게 만들었으며, **AgentServeSim**(arXiv:2606.09613)은 다중 턴 agent serving의 정책 질문이 실측으로 답하기에 조합이 너무 많다는 이유로 tool gap 동안의 KV 잔존까지 담는 시뮬레이터를 세웠다. **격자가 일급 대상이라는 인식도, agent serving을 시뮬레이션해야 한다는 착상도 이 논문의 것이 아니다.** 그런데 두 결과는 서로 다른 축에서 멈춘다. LENS는 격자를 보되 **요청 하나**를 보므로, 한 세션의 KV slot 점유가 *다른* 세션의 캐시 생존을 정하는 축이 그 모형에 정의되지 않는다. AgentServeSim은 다중 세션 동역학을 보되 **GPU의 동적 runtime**(연속 batching, 조정 가능한 회수 정책, 메모리 계층)을 대상으로 하므로, 회수 정책이 시퀀스 단위 FIFO로 **compile 시점에 굳어 있는** substrate에서 무엇이 남는지를 묻지 않는다. **이 논문의 자리는 그 교차점이다** — NPU의 compile-static 격자와 다중 세션 도착 과정이 만나는 곳. 그 교차점이 비어 있다는 것이 이 연구의 여지였고, 실제로 이 논문이 회수한 device time의 8할은 정확히 거기서 나온다: `batch_size`가 KV slot 수를 정하고, slot 수가 캐시 생존을, 생존이 prefill 재계산을 정하는 사슬은 **단일 요청 모형에도, 회수 정책을 바꿀 수 있다고 전제하는 모형에도 나타나지 않는다.** 우리 시뮬레이터의 기여 역시 "시뮬레이터가 있다"가 아니라 **보정 파라미터 없이, 측정 전에 commit한 예측으로, 아직 compile되지 않은 구성의 device time을 맞힌다**는 데 있다 — 그것이 device 실측을 선택 루프에서 빼는 유일한 근거이기 때문이다.

### English

Two of the ideas this paper stands on are already in the literature. **LENS** (arXiv:2606.18042) makes explicit that an NPU's discrete bucket grid renders latency non-linear, and makes that non-linearity predictable; **AgentServeSim** (arXiv:2606.09613) builds a simulator for multi-turn agent serving — KV residency across tool gaps included — precisely because the policy space is too large to measure. **Neither treating the grid as a first-class object nor simulating agent serving originates here.** The two stop on different axes, however. LENS sees the grid but sees *one request*, so the axis along which one session's KV-slot occupancy decides *another* session's cache survival is undefined in its model. AgentServeSim sees multi-session dynamics but targets a **dynamic GPU runtime** — continuous batching, tunable reclaim, a memory hierarchy — and so does not ask what remains when reclaim is a sequence-granular FIFO frozen at compile time. **This paper sits at the intersection**: an NPU's compile-static grid meeting a multi-session arrival process. That the intersection was empty is what left room for this work, and it is where four fifths of the device time we recover comes from: the chain from `batch_size` to KV slot count to cache survival to prefill recomputation appears **neither in a single-request model nor in one that presumes reclaim policy can be changed**. Our simulator's contribution is likewise not that a simulator exists, but that it predicts the device time of a configuration **that has not yet been compiled, with zero fitted parameters, from predictions committed before measurement** — which is the only thing that licenses taking device measurement out of the selection loop.

### 이 문단이 지키는 규칙

- **선행을 회피하지 않는다.** 첫 두 문장이 두 선행의 기여를 그대로 인정하고, "우리 것이 아니다"를 명시한다.
- **공백은 주장이 아니라 위치로 특정한다.** "아무도 안 했다"가 아니라 **두 축의 교차점**이라고 적고, 그 교차점에서 이득이 나온다는 것을 수치가 아니라 기전(사슬)으로 말한다.
- **시뮬레이터 기여를 존재가 아니라 능력으로 진술한다** ([CLAIMS.md](CLAIMS.md) 전수 점검 표의 해당 항목).
- 수치는 "8할" 하나뿐이고 그것도 조건([TASK35](../docs/research/TASK35.md)의 절제)과 함께만 본문에서 전개한다.

---

## §5. 논문의 구성 — (골격)

막 1 진단(§?), 막 2 불가능성(§?), 막 3 처방(§?), 일반성(§?), 한계(§?).
