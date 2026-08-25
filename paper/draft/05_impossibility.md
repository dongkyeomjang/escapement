# ⑤ What runtime policy cannot reach

## 5.1 There is headroom, and utilization does not measure it

An offline bound over return schedules finds real room: with a budget of 2 s under the measured tool-latency distribution, 5.0–6.9 % of device time. <!-- CLAIMS 2.3 --> The bound comes from local search and is therefore a **lower** bound. <!-- CLAIMS 2.2 -->

Before using it we have to discard the metric this project had been judging by. Under a rescheduling that preserves total work, slot occupancy and device time move in **opposite** directions: the schedule that maximises utilization spends 11–37 % more device time, and in measured arm comparisons the two disagree in direction in 5 of 11 cells. <!-- CLAIMS 2.1 --> Utilization remains a valid observable; it is not a cost function.

## 5.2 What a causal policy does with it

The offline optimum does not hold sessions back evenly. It releases most of them immediately and detains a few — and *which* few depends on when the others will return. Every causal policy we evaluated, seeing only the present state, produced a negative mean saving; the best was −0.44 %. <!-- CLAIMS 2.4 --> On device this reproduced: the recovery fraction was −105 % and −70 % in the two confirmation cells — the policy increased device time rather than reducing it. **The intuition "wait a moment and go together" is not merely unhelpful here; it costs about as much as the headroom is worth.** <!-- CLAIMS 2.4 -->

## 5.3 Most of the headroom is coordination, and knowledge cannot buy it

We decompose the headroom by information rather than by policy. If every session is given **omniscient** knowledge of the future but each is required to decide **independently**, 27–51 % of the bound is recovered, and the remaining **median 60 % (range 49–73 %) disappears**. <!-- CLAIMS 2.5 -->

That share is not lost to ignorance. It is lost to the decision structure: when the gain comes from several sessions riding the same batch, *which* group forms cannot be decided by any one session from its own information. **No per-session runtime policy can reach it, in principle.** The only mechanisms that can achieve coordination are a scheduler that sees every session, or a configuration that freezes the coordination at build time for everybody. <!-- CLAIMS 2.6 -->

**Figure ⑤.**

## 5.4 And the reachable remainder is not reachable in practice

Two independent reasons close it.

**The value of return-time information is workload-specific.** Under a synthetic gap law, knowing exactly when peers return recovers 86–88 % of the bound and defines an accuracy threshold of the same order as the gap standard deviation. Under the *measured* tool-latency distribution the same information is worth −1.20 % to +0.99 %, and no threshold is definable. The opportunity to co-schedule is similar in both (73.6 % vs 81.9 % at a 2 s budget) — **it is not the opportunity that is missing but its value.** <!-- CLAIMS 2.7 -->

**And the prediction is not available anyway.** Borrowing the tool-duration estimator of [@continuum2025] verbatim, the converged error exceeds the accuracy threshold by 5.6–9.7×, and growing per-tool samples by four orders of magnitude moves the error standard deviation from 8.4 s to 10.5 s — in the wrong direction. <!-- CLAIMS 2.8 --> The bound and the point estimate hit the same wall (10.196 vs 10.185 s), which locates the problem: not a weaker estimator but weaker **conditioning**. Whether `Bash` takes 27 ms or 300 s is decided by the command, and the tool name does not carry the command. <!-- CLAIMS 2.9 -->

**Figure ⑥.**

## 5.5 A methodological warning that applies to us too

Two free parameters and a twenty-configuration search manufacture a +4.32 % gain on exploration seeds that becomes −0.14 % on held-out seeds; an earlier instance with a larger search showed up to 34 % before the sign reversed. <!-- CLAIMS 2.10 --> Everything in §⑥ is therefore selected on one set of seeds, evaluated on another, and confirmed against predictions committed before measurement.
