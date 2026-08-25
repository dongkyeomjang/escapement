# ⑥ Compile-time configuration

## 6.1 Why this is the remaining lever, and what we call the answer

We call the resulting procedure **Escapement**: the zero-fitted-parameter substrate model of Section~④ together with the distribution-driven configuration search built on it. The name is used from here on for that pair, not for a runtime component — Escapement produces a compiled artifact and then gets out of the way.



Section ⑤ closed the runtime path by a branch defined before the computation was run: if generation-length or return-time knowledge had recovered at least half the headroom, a prediction-based runtime policy would have remained a candidate. It recovered at most a small fraction, so **compile-time configuration is what is left** — coordination decided once, in advance, for everybody. <!-- CLAIMS 3.1 --> This verdict is about this substrate under a preregistered branch; a server-side scheduler remains an open path that this work did not take. <!-- CLAIMS 2.6 -->

## 6.2 Choosing a configuration without touching the device

Candidate configurations are scored by the uncalibrated model on **exploration** seeds and confirmed on **evaluation** seeds. The only workload facts entering the choice are the gap distribution and the concurrency ceiling; no device measurement enters the selection loop. <!-- CLAIMS 3.2 --> A sensitivity analysis says the choice is insensitive to the gap distribution and responds only to the concurrency ceiling — **that is the one statistic worth re-measuring before reconfiguring.** <!-- CLAIMS 3.9 -->

The cost of acting on the choice is a recompile, and it is small: compile time is linear in the number of compiled graphs. The model was fitted to the first two observations alone; at the fifth, sixth and seventh points its predictions held to within +3.0 % on compile time and +1.6 % on artifact size [[fig:fig7]]. On this model and device the fitted expression puts a six-rung artifact at 7.9 minutes, and the two six-rung artifacts actually built took 8.1 and 7.9 minutes; we round to **eight minutes** elsewhere in the paper. <!-- CLAIMS 3.3 -->

**Figure ⑦.**

## 6.3 Confirmation on device

Predictions were committed before measurement, together with the judgement rule and the channel definition. Against a baseline of `batch_size = 8` on grid `(1,2,4,8)`, a tuned configuration (`batch_size = 16`, grid `(1,4,6,8,10,16)`) recovered **+9.72 % / +10.07 %** of device time on the two channels at N=8 concurrent sessions <!-- CLAIMS 3.4 -->, and **+2.11 % / +2.74 %** at N=6 on a fresh seed under a corrected channel-agreement rule <!-- CLAIMS 3.5 -->.

A device-side ablation separates the two axes. Changing only `batch_size` yields +8.25 %; adding grid alignment on top adds a further 1.3–1.5 percentage points at these two cells. The two arms' **prefill ratios are identical in measurement** (0.678 / 0.678), which is what makes the ablation interpretable: with the same pool size the cache survives identically, so the arms can differ only in the decode term. <!-- CLAIMS 3.6, 3.7 --> The causal chain closes: `batch_size` sets the KV block count, that sets cache survival, and survival sets prefill recomputation [[fig:fig8]]. <!-- CLAIMS 3.8 -->

**Figure ⑧.**

## 6.4 The gain is proportional to what is left to recover

The ablation's ordering held on a fresh seed but the **magnitudes reversed**: where the baseline already reused 17 of 18 resumptions, changing only `batch_size` bought +0.59 % — inside the equivalence band — and nearly all of the remaining gain came from grid alignment instead. <!-- CLAIMS 3.10 --> The reading of §6.3 is therefore not "`batch_size` dominates" but **"the dominant factor is recoverable cache loss, and `batch_size` is the lever that buys it."** The model predicted this reversal before measurement.

## 6.5 Where the lever stops

<!-- 편집 주석: [SWEEP-PENDING] 자리. TASK40으로 채움. -->

If a larger pool recovers cache, the obvious rebuttal is to make it much larger. We tested it directly: `batch_size` ∈ {8, 16, 24, 32}, with the grid held at `(1,4,6,8,10,B)` so that **only the top rung changes** between adjacent configurations, over three concurrency levels and three blocks.

The gain **saturates at 16**. Judged by the bootstrap CI of the median per-cell ratio, both controlled steps are equivalence: 16 → 24 gives 0.9999 (CI [0.9808, 1.0000]) and 24 → 32 gives 1.0002 (CI [0.9999, 1.0015], width 0.0016) [[fig:fig9]]. <!-- CLAIMS 3.11 -->

**The concurrency of ten is exploratory, not confirmatory.** Section~④ withholds confirmation above the scheduler's admission ceiling because reproduction quality degrades there, and that rule is applied here without exception: the N=10 cells are reported for what they show and are excluded from the confirmation. The saturation verdict rests on the six cells at concurrencies six and eight; the N=10 cells happen to agree with it, and the one place the plateau leaks is also there.

Two mechanisms make the plateau, and the data shows both. **Survival saturates**: at `batch_size = 16` reuse already reaches 18/18 and 24/24 at the two lower concurrencies, so a larger pool has no cache left to save. <!-- CLAIMS 3.10 --> **And the widest rung is never selected**: the mapping table places rung 16, 24 and 32 at a concurrency of eleven, which this grid never reaches, and the step trace confirms a 0.0 % share for the top rung in every cell. A rung that is never selected can neither save nor cost anything — **without this second mechanism the curve would have reversed**, since the extrapolated step cost of the widest rung is roughly twice that of rung 8. <!-- CLAIMS 3.12 -->

The plateau leaks in exactly one place, and it leaks where the law of §6.4 says it should. At N=10 the baseline pool reached only 28/30 survival, and there — and only there — 16 → 24 still bought about 2 %. <!-- CLAIMS 3.10 -->

The practical consequence is the point of the section. Device memory on this instance is `2.1 + 0.28125·B` GiB per device (a three-point fit), so the 15.7 GiB ceiling is reached near `B = 46` — **an extrapolation, not a measurement**. The gain ends at one third of that. **The optimal `batch_size` is set by the workload distribution, not by what the hardware can hold.** <!-- CLAIMS 3.13 -->

One further result belongs here because of what it tests. The uncalibrated model predicted this plateau **before measurement**, and at the two lower concurrencies its six cells were accurate to 0.0003–0.0026 — the tightest agreement in this project. Predicting the *absence* of an effect is a different kind of evidence from predicting its size: there is little room for a null prediction to be right by accident. <!-- CLAIMS 3.14 -->

**Figure ⑨.**

## 6.6 What it does to the tail

Device time is the quantity this paper optimised and confirmed, and a configuration that lowers it could still hurt the latency a user waits through. We checked, by re-reading the per-request completion times already recorded in the confirmation runs — no new measurement.

<!-- TABLECOLS: p{1.1cm}p{1.9cm}p{1.9cm}p{2.5cm} -->
<!-- TABLELABEL: tail -->
<!-- TABLE: Request completion time of the tuned configuration relative to the baseline, from the per-request records of runs already taken. Lower is better. This was not preregistered; it is reported because the question is fair and the records were already on disk. -->

| N | p50 ratio | p99 ratio | run |
|---|---|---|---|
| 6 | 0.915 | 0.956 | confirmation |
| 8 | 0.895 | 0.841 | confirmation |
| 6 | 0.954 | 0.954 | reconfirmation, fresh seed |
| 10 | 0.937 | 0.716 | exploratory |

The tail moves the same way as device time, and further: at every cell the p99 ratio is at least as good as the p50 ratio, and the gap between them widens with concurrency (Table~[[tab:tail]]). <!-- CLAIMS 3.15 --> The mechanism accounts for it — the requests in the tail are the ones that had to recompute a prefix, and the configuration's whole effect is to make fewer of them do so.

**Two limits on this paragraph.** It was **not preregistered**: unlike every judgement in Sections~④–⑥ it is a post-hoc reading of existing records, and we report it as such rather than as a confirmed result. And it covers only the arms and cells whose per-request records exist; nothing was re-run to fill a gap.

## 6.7 The prescription

Putting §6.2–§6.5 together: **measure the workload's concurrency ceiling, choose the smallest pool at which the cache survives at that ceiling, and stop.** Grid alignment is a real but secondary gain on top. Nothing in this procedure requires predicting an individual tool call — only its distribution. **The step that chooses is model-derived**: the ranking of candidate configurations comes from the simulator, and only the chosen configuration was built and measured. What the device confirms is that the chosen one delivers; that the model ranked the field correctly is supported by the ablation of Section~⑥-C, not established for candidates never compiled.
