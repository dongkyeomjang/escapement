# ⑦ Generality: ablations, and what transfers

Every absolute constant in this paper belongs to one instance. This section separates which statements are about the **shape** of a law and which are about its **value**, using ablations in the validated model and direct reads of the serving stack's source.

## 7.1 The grid law does not vanish on GPUs

The expectation this project started with was that the grid-alignment law is an NPU artefact. It is not. vLLM's default CUDA-graph capture sizes at an admission ceiling of eight are `[1,2,4,8,16]`, whose effective portion is identical to the NPU grid studied here, and the pooled ratio computed on it agrees to four decimals [[fig:fig2]]. <!-- CLAIMS 4.1 --> This is a **model statement supported by a source read**, not a GPU measurement; the promotion condition is a single GPU run at a matched admission ceiling.

The corollary reframes any cross-accelerator comparison: **the axis to vary is not the accelerator but the admission ceiling.** <!-- CLAIMS 4.2 -->

## 7.2 What the ablations do and do not establish

Three mechanisms, three ablations. Removing the discrete grid collapses the alignment law to exactly 1.0000. <!-- CLAIMS 1.7 --> Replacing sequence-granular FIFO with block-granular LRU removes the count threshold and makes it size-dependent instead. <!-- CLAIMS 1.3 --> Making prefill chunked removes the stall entirely — and **increases** device time by 3–10 %, because the exclusive prefill had been forcing a synchronisation that widened subsequent batches. Part of what looked like a pure tax was a batching subsidy. <!-- CLAIMS 1.11 --> **This is a model-derived, substrate-conditional statement**: it says what happens to *this* substrate's device time when the stall is removed from *this* model, holding everything else fixed. It is **not** a claim about chunked prefill on GPUs, where chunking also overlaps computation and the comparison is a different one [@sarathi2024].

The last of these is the one that most changes how the paper should be read against prior work, since chunked prefill is standard practice elsewhere.

An ablation tests **attribution, not existence**: it says what happens to a result when a property is removed from the model, not that hardware with that property will produce the same number. <!-- CLAIMS 4.3 -->

## 7.3 A methodological transfer

Two rules generalise beyond this substrate. Metrics must be validated by **which layer they count**, not by what they are named — two metrics with similar names counted different layers here and disagreed only after eviction. <!-- CLAIMS 4.4 --> And when a model-based channel is checked against a model-free one, the tolerance must carry the **absolute** residual and not only a ratio: a fixed overhead of one to two seconds is a few percent of a large run and six percent of a small one, so a ratio-only band is structurally unfair to light loads. <!-- CLAIMS 4.5 -->
