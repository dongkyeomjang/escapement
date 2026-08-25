# ⑧ Related work

<!-- 편집 주석: RELATED.md의 배치를 본문 분량으로 압축. 새 주장을 만들지 않는다. -->

## 8.1 A taxonomy of levers

Levers in this area divide by what they need to know. **Distribution levers** are decided by aggregate statistics: how long a tool takes on average, how idle a program is relative to others, which agent runs next in a declared graph. **Draw levers** need the individual realisation: when *this* session will return. The distinction matters because the failure modes differ — a distribution lever degrades gracefully when the estimate is wrong, while a draw lever whose estimate is wrong produces a negative gain rather than a smaller one. <!-- CLAIMS 2.4, 2.9 -->

This paper's negative results (§⑤) are about draw levers. Most prior successes are distribution levers. **The negative results therefore explain rather than contradict them.**

## 8.2 Nearest prior work

**LENS** [@lens2026] predicts NPU inference latency without microarchitecture or compiler information and explicitly captures the non-linearity that bucketing induces. It shares this paper's premise that the discrete grid is a first-class object, and states it earlier and more explicitly. It differs in what it predicts: a **stateless single-request latency**, whereas the quantity here is a multi-session dynamic. The difference is structural rather than incidental — `batch_size` barely changes any single request's latency; what it changes is whether *other* sessions' caches survive, an axis undefined in a one-session model. **Four fifths of the gain reported here is invisible from that vantage point.** <!-- CLAIMS 3.6, 3.8 -->

**AgentServeSim** [@agentservesim2026] simulates multi-turn agent serving including KV residency across tool gaps, on the same reasoning that motivates §④: the policy space is too large to measure. It targets a **dynamic GPU runtime**. This paper's model targets what a recompile freezes. The distinguishing claim is not that a simulator exists but that this one predicts, with **zero fitted parameters** and from predictions committed before measurement, the device time of a configuration that has not yet been compiled. <!-- CLAIMS 1.15, 3.14 -->

## 8.3 KV-cache management for agentic serving

A family of systems manages the cache across tool gaps: TTL-based retention [@continuum2025], idleness-ranked offloading between memory tiers [@mori2026], workflow-graph-scored eviction with prefetch [@kvflow2025], online-learned agent transitions [@cachescout2026a; @cachescout2026b] (one system), application-issued cache directives [@leyline2026], workflow-atomic scheduling [@saga2026], and program-aware scheduling with tool-resource management [@thunderagent2026]. Power, rather than time, is the objective in [@kairos2026], which nonetheless tunes per-instance concurrency and so meets this paper's axis.

**These share a premise: that the reclaim policy can be changed.** On the substrate studied here the lower cache layer's reclaim is a hardcoded sequence-granular FIFO — the class implementing an alternative exists in the source and is unused. That premise does not hold, which is what pushed this work from the policy axis onto the configuration axis. <!-- CLAIMS 1.1, 3.1 -->

The TTL line deserves a specific note because this paper borrows its estimator. TTL is a distribution lever: the bound on a mean is enough. Return rescheduling is a draw lever. Measuring the same estimator against a draw-lever threshold is how §5.4 obtains its negative result, and the finding that a bound and a point estimate hit the same wall is precisely the statement that the estimator is adequate for the first task and structurally inadequate for the second. <!-- CLAIMS 2.9 -->

## 8.4 Converging independent evidence

ConServe [@conserve2026] argues that raising the scheduling unit from the turn to the conversation converts turn-level irregularity into observable structure and removes the need for prediction. It reaches a compatible conclusion from a different substrate and a different method. This paper adds *why* the prediction fails — an irreducible variance that more samples do not reduce — and *where* a lever survives without it. <!-- CLAIMS 2.8 -->

## 8.5 Scheduling and batch composition

Program-level scheduling that removes head-of-line blocking [@autellix2025] and session-centric scheduling [@smetric2026] operate above the layer studied here; the latter is the server-side coordination position that §5.3 identifies and this work did not open. Chunked prefill [@sarathi2024] is the direct counterpart of §3.3 and is exactly the design whose ablation in §7.2 removes the stall while increasing device time. Multi-core NPU serving [@multicorenpu2025] studies the layer below: core placement and parallelism, held fixed throughout this work.
