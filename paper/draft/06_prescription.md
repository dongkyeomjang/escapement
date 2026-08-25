# ⑥ Compile-time configuration

## 6.1 Why this is the remaining lever

Section ⑤ closed the runtime path by a branch defined before the computation was run: if generation-length or return-time knowledge had recovered at least half the headroom, a prediction-based runtime policy would have remained a candidate. It recovered at most a small fraction, so **compile-time configuration is what is left** — coordination decided once, in advance, for everybody. <!-- CLAIMS 3.1 --> This verdict is about this substrate under a preregistered branch; a server-side scheduler remains an open path that this work did not take. <!-- CLAIMS 2.6 -->

## 6.2 Choosing a configuration without touching the device

Candidate configurations are scored by the uncalibrated model on **exploration** seeds and confirmed on **evaluation** seeds. The only workload facts entering the choice are the gap distribution and the concurrency ceiling; no device measurement enters the selection loop. <!-- CLAIMS 3.2 --> A sensitivity analysis says the choice is insensitive to the gap distribution and responds only to the concurrency ceiling — **that is the one statistic worth re-measuring before reconfiguring.** <!-- CLAIMS 3.9 -->

The cost of acting on the choice is a recompile, and it is small: compile time is linear in the number of compiled graphs, and a model built from two observations held at the fifth, sixth and seventh points to within +3.0 % on time and +1.6 % on size. On this model and device a six-rung artifact takes about eight minutes. <!-- CLAIMS 3.3 -->

**Figure ⑦.**

## 6.3 Confirmation on device

Predictions were committed before measurement, together with the judgement rule and the channel definition. Against a baseline of `batch_size = 8` on grid `(1,2,4,8)`, a tuned configuration (`batch_size = 16`, grid `(1,4,6,8,10,16)`) recovered **+9.72 % / +10.07 %** of device time on the two channels at N=8 concurrent sessions <!-- CLAIMS 3.4 -->, and **+2.11 % / +2.74 %** at N=6 on a fresh seed under a corrected channel-agreement rule <!-- CLAIMS 3.5 -->.

A device-side ablation separates the two axes. Changing only `batch_size` yields +8.25 %; adding grid alignment on top adds a further 1.3–1.5 percentage points. The two arms' **prefill ratios are identical in measurement** (0.678 / 0.678), which is what makes the ablation interpretable: with the same pool size the cache survives identically, so the arms can differ only in the decode term. <!-- CLAIMS 3.6, 3.7 --> The causal chain closes: `batch_size` sets the KV block count, that sets cache survival, and survival sets prefill recomputation. <!-- CLAIMS 3.8 -->

**Figure ⑧.**

## 6.4 The gain is proportional to what is left to recover

The ablation's ordering held on a fresh seed but the **magnitudes reversed**: where the baseline already reused 17 of 18 resumptions, changing only `batch_size` bought +0.59 % — inside the equivalence band — and nearly all of the remaining gain came from grid alignment instead. <!-- CLAIMS 3.10 --> The reading of §6.3 is therefore not "`batch_size` dominates" but **"the dominant factor is recoverable cache loss, and `batch_size` is the lever that buys it."** The model predicted this reversal before measurement.

## 6.5 Where the lever stops

<!-- 편집 주석: [SWEEP-PENDING] 자리. TASK40으로 채움. -->

If a larger pool recovers cache, the obvious rebuttal is to make it much larger. We tested it directly: `batch_size` ∈ {8, 16, 24, 32}, with the grid held at `(1,4,6,8,10,B)` so that **only the top rung changes** between adjacent configurations, over three concurrency levels and three blocks.

The gain **saturates at 16**. Judged by the bootstrap CI of the median per-cell ratio, both controlled steps are equivalence: 16 → 24 gives 0.9999 (CI [0.9808, 1.0000]) and 24 → 32 gives 1.0002 (CI [0.9999, 1.0015], width 0.0016) — at N ≤ 10 under this workload. <!-- CLAIMS 3.11 -->

Two mechanisms make the plateau, and the data shows both. **Survival saturates**: at `batch_size = 16` reuse already reaches 18/18 and 24/24 at the two lower concurrencies, so a larger pool has no cache left to save. <!-- CLAIMS 3.10 --> **And the widest rung is never selected**: the mapping table places rung 16, 24 and 32 at a concurrency of eleven, which this grid never reaches, and the step trace confirms a 0.0 % share for the top rung in every cell. A rung that is never selected can neither save nor cost anything — **without this second mechanism the curve would have reversed**, since the extrapolated step cost of the widest rung is roughly twice that of rung 8. <!-- CLAIMS 3.12 -->

The plateau leaks in exactly one place, and it leaks where the law of §6.4 says it should. At N=10 the baseline pool reached only 28/30 survival, and there — and only there — 16 → 24 still bought about 2 %. <!-- CLAIMS 3.10 -->

The practical consequence is the point of the section. Device memory on this instance is `2.1 + 0.28125·B` GiB per device (a three-point fit), so the 15.7 GiB ceiling is reached near `B = 46` — **an extrapolation, not a measurement**. The gain ends at one third of that. **The optimal `batch_size` is set by the workload distribution, not by what the hardware can hold.** <!-- CLAIMS 3.13 -->

One further result belongs here because of what it tests. The uncalibrated model predicted this plateau **before measurement**, and at the two lower concurrencies its six cells were accurate to 0.0003–0.0026 — the tightest agreement in this project. Predicting the *absence* of an effect is a different kind of evidence from predicting its size: there is little room for a null prediction to be right by accident. <!-- CLAIMS 3.14 -->

**Figure ⑨.**

## 6.6 The prescription

Putting §6.2–§6.5 together: **measure the workload's concurrency ceiling, choose the smallest pool at which the cache survives at that ceiling, and stop.** Grid alignment is a real but secondary gain on top. Nothing in this procedure requires predicting an individual tool call — only its distribution.
