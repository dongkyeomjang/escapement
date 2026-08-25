# ⑨ Limitations

**Single substrate, single stack version.** All absolute constants are from one accelerator and one set of package versions. The observation patch is hash-guarded and observation-only, but a version change can move the grid, the accounting and the metric layering together.

**Single model, single sequence length.** Qwen3-4B at `max_seq_len = 8192`, 36 full-attention layers. Hybrid, sliding-window and MLA attention account for KV differently, and the chain from `batch_size` to slot count assumes eager attention's `kvcache_num_blocks = batch_size`. <!-- CLAIMS 3.8 -->

**One workload trace.** Tool latencies come from a single code-agent trace of 43 tools. This project has already demonstrated that this limitation bites: the value of return-time information reversed when the gap distribution was replaced. <!-- CLAIMS 2.7 -->

**The validated envelope is narrower than the paper's reach.** Confirmation is claimed at concurrencies at or below eight, on one grid family and one workload (§④). Model accuracy degrades above the scheduler's admission ceiling — utilization error within 0.004 below it, 0.011–0.023 above — and cells there are reported as exploratory throughout, never used for confirmation.

**The saturation curve's N=10 cells are exploratory.** They are reported and they agree with the verdict, but the confirmation rests on concurrencies six and eight (Section~⑥-E).

**The saturation curve does not cover the reversal regime.** The widest compiled rung engages at a concurrency of eleven, and the sweep ran to ten, so the rung's step cost was never charged. **We expect a reversal beyond that point and did not measure it.** For the same reason the step costs of the wide rungs remain unmeasured, and the model interpolates them — harmlessly here only because they were never selected. <!-- CLAIMS 3.11, 3.12 -->

**`batch_size` beyond 32 is not measured.** The KV ceiling near `B = 46` is a three-point extrapolation of device memory, not an observation. <!-- CLAIMS 3.13 -->

**GPU results are model statements.** The claim that the grid law survives on GPUs rests on a source read of default capture sizes plus a computation, not on a GPU run. The minimum promotion experiment is one survival curve at a matched admission ceiling. <!-- CLAIMS 4.1, 4.3 -->

**A systematic residual is unexplained.** Across five device confirmations the measured ratio exceeded the prediction every time, in the conservative direction (the device delivered slightly less than predicted). Every error fell inside the preregistered tolerance, so no verdict turns on it, but the sign is systematic and the responsible term is not identified. <!-- CLAIMS 1.18 -->

**The server-side scheduler path is untried.** §5.3 identifies it as the one runtime location where coordination can live. It falls outside this work's patch policy. **The claim is not "runtime is impossible" but "per-session runtime is impossible and server-side is unmeasured."** <!-- CLAIMS 2.6 -->

**Power is not measured.** Concurrency is a lever for power as well as for time, and this work priced only time.
