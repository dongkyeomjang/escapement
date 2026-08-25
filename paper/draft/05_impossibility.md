# ⑤ What runtime policy cannot reach

## 5.1 There is headroom, and utilization does not measure it

An offline bound over return schedules finds real room: with a budget of 2 s under the measured tool-latency distribution, 5.0–6.9 % of device time. <!-- CLAIMS 2.3 --> The bound comes from local search and is therefore a **lower** bound. <!-- CLAIMS 2.2 -->

Before using it we have to discard the metric this project had been judging by. Under a rescheduling that preserves total work, slot occupancy and device time move in **opposite** directions: the schedule that maximises utilization spends 11–37 % more device time, and in measured arm comparisons the two disagree in direction in 5 of 11 cells. <!-- CLAIMS 2.1 --> Utilization remains a valid observable; it is not a cost function.

## 5.2 Four ways to try, and what closes each

The policies one might build differ along two axes: whether a single component decides for everyone (**centralised**) or each session decides for itself (**decentralised**), and whether the decision uses only the present (**causal**) or also the future (**omniscient**). That gives four combinations, and this paper closes three of them by different means.

<!-- TABLECOLS: p{1.5cm}p{3.0cm}p{3.0cm} -->
<!-- TABLELABEL: twobytwo -->
<!-- TABLE: The four ways to reach the rescheduling headroom, and what closes each. Only the centralised-omniscient cell is not closed by a result in this paper; it is closed by the unpredictability established in Section V-D. -->

| | causal (present only) | omniscient (uses the future) |
|---|---|---|
| **centralised** | **closed empirically** — measured on device, recovery fraction −105 % and −70 % | **not closed by a result** — this is the offline bound itself; unreachable because the future is not predictable |
| **decentralised** | **closed empirically** — every candidate had a negative mean saving | **closed structurally** — omniscient but independent decisions lose a median 60 % of the bound |

**The centralised-causal cell was measured, not assumed.** The policy evaluated on device runs at the gateway that sits between the sessions and the engine, and that position **holds the right to release a return**: it decides when each returning turn is handed to the engine. A server-side scheduler decides the order in which already-submitted work runs, which is a subset of that authority — it cannot hold a return that has already arrived any longer than the gateway chose to. <!-- CLAIMS 2.11 --> So the device result bounds the centralised-causal family, and it bounds it at a **negative** recovery.

What remains is the top-right cell, and Section~⑤-D closes it by showing that the information it would need does not exist to be had.

## 5.3 What a causal policy does with it

The offline optimum does not hold sessions back evenly. It releases most of them immediately and detains a few — and *which* few depends on when the others will return. Every causal policy we evaluated, seeing only the present state, produced a negative mean saving; the best was −0.44 %. <!-- CLAIMS 2.4 --> On device this reproduced: the recovery fraction was −105 % and −70 % in the two confirmation cells — the policy increased device time rather than reducing it. **The intuition "wait a moment and go together" is not merely unhelpful here; it costs about as much as the headroom is worth.** <!-- CLAIMS 2.4 -->

## 5.4 Most of the headroom is coordination, and knowledge cannot buy it

We decompose the headroom by information rather than by policy. If every session is given **omniscient** knowledge of the future but each is required to decide **independently**, 27–51 % of the bound is recovered, and the remaining **median 60 % (range 49–73 %) disappears** [[fig:fig5]]. <!-- CLAIMS 2.5 -->

**A note on what this number is.** The 60 % is computed from **aggregate device time** — the total the schedule spends, summed over sessions. Section~④ disqualified this model's *session-level attribution* (which session's prefix was the one that survived), and that disqualification does not reach here: the decomposition never asks which session recovered what, only how much total device time each information level buys. The two are different quantities, and the aggregate is the one the model reproduces most accurately. <!-- CLAIMS 2.5 -->

That share is not lost to ignorance. It is lost to the decision structure: when the gain comes from several sessions riding the same batch, *which* group forms cannot be decided by any one session from its own information. **No per-session runtime policy can reach it, in principle.** The only mechanisms that can achieve coordination are a centralised decision point or a configuration that freezes the coordination at build time for everybody — and Table~[[tab:twobytwo]] has already closed the centralised one under causal information. <!-- CLAIMS 2.6 -->

**Figure ⑤.**

## 5.5 And the reachable remainder is not reachable in practice

Two independent reasons close it.

**The value of return-time information is workload-specific.** Under a synthetic gap law, knowing exactly when peers return recovers 86–88 % of the bound and defines an accuracy threshold of the same order as the gap standard deviation. Under the *measured* tool-latency distribution the same information is worth −1.20 % to +0.99 %, and no threshold is definable. The opportunity to co-schedule is similar in both (73.6 % vs 81.9 % at a 2 s budget) — **it is not the opportunity that is missing but its value.** <!-- CLAIMS 2.7 -->

**And the prediction is not available anyway.** Borrowing the tool-duration estimator of [@continuum2025] verbatim, the converged error exceeds the accuracy threshold by 5.6–9.7×, and growing per-tool samples by four orders of magnitude moves the error standard deviation from 8.4 s to 10.5 s — in the wrong direction [[fig:fig6]]. <!-- CLAIMS 2.8 --> The bound and the point estimate hit the same wall (10.196 vs 10.185 s), which locates the problem: not a weaker estimator but weaker **conditioning**. Whether `Bash` takes 27 ms or 300 s is decided by the command, and the tool name does not carry the command. <!-- CLAIMS 2.9 -->

**Figure ⑥.**

## 5.6 A methodological warning that applies to us too

Two free parameters and a twenty-configuration search manufacture a +4.32 % gain on exploration seeds that becomes −0.14 % on held-out seeds; an earlier instance with a larger search showed up to 34 % before the sign reversed. <!-- CLAIMS 2.10 --> Everything in §⑥ is therefore selected on one set of seeds, evaluated on another, and confirmed against predictions committed before measurement.
