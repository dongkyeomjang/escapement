# ② Background: the substrate, and what it fixes at compile time

<!-- 편집 주석: 이 절은 주장을 세우지 않는다. 뒤 절이 쓰는 용어와 "무엇이 compile 시점에 굳는가"만 정의한다. -->

## The stack

Measurements are on an RBLN CA25 NPU (four devices per model instance) running `vllm 0.22.0+cpu` with `vllm-rbln 0.11.1` and artifacts compiled by `optimum-rbln 0.11.1`. The model is Qwen3-4B at `max_seq_len = 8192`, whose 36 layers are all full attention, so KV per token is a single expression. **Every absolute constant below belongs to this instance and is not carried elsewhere**; the paper marks each claim with the layer at which it is asserted.

An observation-only patch exposes one line per decode step giving the actual running count and the padded batch width the runner selected; it adds a single debug log call, changes no control flow, and is guarded by a hash of the target file that every run records, with the full justification — target version, before/after hashes, the argument that scheduler, batch selection and KV allocation are untouched, and the apply/revert commands — given in Appendix C.

## Two things a recompile fixes

**Compiled decode widths.** The decoder is compiled for an explicit set of batch widths. At run time the actual running count is rounded **up** to the smallest compiled width that is at least as large, and the model executes at that width. Widths that were not compiled do not exist. <!-- CLAIMS 1.5 -->

**KV pool size.** With eager attention, the number of KV blocks equals the compile-time `batch_size`, and the block size defaults to `max_seq_len`. One block therefore holds one sequence, and `batch_size` *is* the number of sequence-granular slots. <!-- CLAIMS 3.8 -->

These two are the whole of what this paper later chooses. Both are frozen when the artifact is built; neither can be changed at run time.

## Two cache layers, counted differently

The stack keeps two ledgers. The upper one is vLLM's block table — 128-token blocks under LRU. The lower one is the runtime's own pool of 8,192-token outer slots under **FIFO**, and it is the one that actually holds the tensors. The two disagree after the lower layer evicts: the upper layer keeps reporting hits for a prefix whose tensors are gone, so `prefix_cache_hits_total` can overstate real reuse by 100 % [[fig:fig1]]. Reuse in this paper always means the lower layer, read from `vllm:prompt_tokens_cached_total` or from the per-request `cached_tokens` field. <!-- CLAIMS 1.4 -->

A second property of the lower layer matters later: it holds only what **prefill** computed. Tokens produced by decode are not cached, so a session's turn *k* can reuse at most the prompt of turn *k−1*. <!-- CLAIMS 1.12 -->

## Workload

Sessions alternate between an LLM turn and a tool gap. Gap durations are drawn from a measured tool-latency population rather than a synthetic law. <!-- CLAIMS 2.3 -->

**Where the tool latencies come from.** The population is a trace of coding-agent sessions collected by the authors from their own use of two agent front-ends, instrumented at the client so that each record carries the request's token counts and the wall-clock duration of the tool call that followed. It contains **665,453 records over 8,058 sessions**, from which the gap sampler keeps the **43 tools** that appear often enough to have a stable duration distribution, capped at 60 s. Latency is taken from the client's own wall clock where the front-end reports it and from the front-end's internal timing otherwise; the split is recorded with the trace.

We release the **per-tool duration distributions** that the sampler consumes, which is what is needed to reproduce every gap draw in this paper. We do not release the raw records: they contain the prompts and outputs of the authors' working sessions, which cannot be published without disclosing unrelated third-party material. <!-- NEEDS-EVIDENCE: 배포 형식(별도 아카이브 vs repo 내 파일)이 정해지면 여기에 적는다 --> Prompts, generation lengths and gaps are generated from a seed plus a block id, so every arm of a comparison runs the **identical plan** and differs only in the compiled configuration.

## How device time is measured

Two independent channels. **Channel A′** reconstructs device time from two measured cost models — the step trace priced by a per-width decode cost, plus each request's actually computed prefill tokens priced by a prefill cost model. **Channel B** is the union of the intervals in which at least one request was in flight, taken from the client's own timestamps and depending on no model at all. A judgement is withheld unless the two agree within a tolerance that carries the residual channel B has and A′ structurally cannot. <!-- CLAIMS 4.5 -->
