# Appendices

<!-- 편집 주석: OUTLINE.md의 부록 A–D. C가 §②의 참조 대상이므로 문자 순서를 맞추려면 A·B·D도 존재해야 한다. A·B는 짧게 실물로 쓰고 D는 §4.2와 저장소 기록을 가리킨다. -->

## Appendix A: Substrate descriptor and layer tags

Every constant this paper uses about the substrate is held in one typed record, and each field carries a provenance triple: the **layer** at which it holds, the task that established it, and how (measured, source-read, or derived). Construction fails if a field lacks one.

The layers are: `silicon` for values specific to this accelerator (absolute step times, prefill constants), `stack` for values specific to this software stack and compiled artifact (grid, slot count, block sizes, eviction order), `class` for the *shape* of a law that follows from a design category rather than an implementation, and `universal` for methodological facts. **A `class` tag is attached to a law's form and never to its value** — "eight outer slots" is never `class`.

Claims in this paper carry the same tags. Where a claim's form is `class` and its value is `stack`, the two are made as separate statements.

## Appendix B: Preregistration record

Every measurement in this paper registered its decision criteria, predictions and experimental grid in a commit **before** measurement began, and each task records the preregistration hash alongside the time measurement started. The registrations relevant to the results reported here are:

<!-- TABLECOLS: p{2.2cm}p{2.35cm}p{2.7cm} -->
<!-- TABLENOTE: $^{\mathrm{a}}$Commit \texttt{28dd252} registered the judgement code (bootstrap procedure, resample count, CI width bound) before measurement began. -->
<!-- TABLE: Preregistration record. Each commit fixed the decision criteria, predictions and experimental grid before the corresponding measurement began. -->

| Registration | Commit | Covers |
|---|---|---|
| Decode step cost | `241b7b8` | §③ step cost decomposition |
| Reuse cliff reproduction | `2d79431` | §③ survival threshold |
| Prefill serialisation | `ba6ee2b` | §③ exclusive prefill |
| Grid intervention | `d5dfc7f` | §③ the recompile intervention |
| Simulator out-of-sample | `41fd96f` | §④ prediction gate |
| Policy on device | `980f0c7` | §⑤ causal policy |
| Real-workload transfer | `f61bafe` | §④, §⑤ workload change |
| Compile configuration | `4e12b30`, `745317e` | §⑥ confirmation |
| N=6 reconfirmation | `3e55240` | §⑥ corrected channel rule |
| `batch_size` saturation | `492abe2`, `28dd252`^a^ | §6.5 |

**No criterion was relaxed after measurement.** Where one was corrected — the channel-agreement rule, whose ratio-only band was structurally unfair to light loads — the original criterion's failure is reported alongside the corrected result, and the corrected run passed the original criterion as well. <!-- CLAIMS 4.5 -->

## Appendix C: The observation-only patch

The stack computes, per decode step, both the actual number of running requests and the padded batch width it will execute at, but exposes neither. Section ③'s attribution depends on that pair, so a patch was applied under a written policy whose seven requirements are answered here.

**1. Target package and exact version.** `vllm-rbln` `0.11.1`, on the default execution path (`VLLM_RBLN_USE_VLLM_MODEL=False`). The apply script re-checks the version on every invocation and exits non-zero on a mismatch.

**2. Upstream path and hashes.** `vllm_rbln/model_executor/models/optimum/model_base.py`, function `RBLNOptimumDecoderMixin.preprocess_for_decoder`. SHA256 before `46ce1675…`, after `70942d16…`. The diff adds nine lines (five code, four comment); no existing line is modified or deleted.

**3. Why scheduler, batch selection and KV allocation are unchanged.** The added code is a single `logger.debug` call. It introduces no branch, loop or exception path and only reads a value the runtime has already computed. It does not touch the bucket selection function — which is memoised, so *wrapping* it would have captured only the first call and would also have perturbed the cache; reading at the call site avoids both. It does not touch the scheduler, the KV cache manager, the padding routine or the block table.

**4. Observation-only alternatives were exhausted first.** Four exposure routes were searched before the patch was written — the full DEBUG server log, all 122 `/metrics` entries, the vendor metrics environment variable, and other read-only paths. None exposes the per-step pair. The computation already exists on the execution path; the patch exports it rather than creating it.

**5. Apply and revert.** Both are single commands in the patch directory, and the patch is a plain diff against the recorded pre-image.

**6. Fail-loud on drift.** The apply script compares the target's hash against the recorded value and exits non-zero if either the version or the hash differs, so a package upgrade stops the experiment instead of silently changing what is measured.

**7. Provenance in run metadata.** Every measurement run records the output of the patch status command, so each result carries the hash of the file it was produced under. The runs behind every number in this paper record `70942d16…`.

**Effect at default log level: none.** The call is at DEBUG, so an unmodified run produces no output.

## Appendix D: Simulator validation detail

Section ④ summarises four gates. Per-cell predicted-versus-measured tables for each — including the block-level breakdown, the invariant checks that made each run valid, and the raw artifact paths — are recorded in the project's research history, released at `github.com/dongkyeomjang/escapement`. The preregistration commits of Appendix~B index into the same repository.
