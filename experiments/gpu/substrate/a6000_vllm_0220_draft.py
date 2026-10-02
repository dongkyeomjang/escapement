#!/usr/bin/env python3
"""DRAFT substrate fields: RTX A6000 + vLLM 0.22.0 (CUDA 13.0) + Qwen3-4B bf16.

GTASK02 (GPU directive G-01, task E). This is *not* a SubstrateDescriptor
instance and deliberately cannot become one yet:

* Only fields settled by source-read (GTASK01) and confirmed by the Stage 0
  function check (GTASK02) are filled. Nothing measured-for-cost is filled --
  step cost and prefill cost need a measurement TASK with its own prereg.
* ``SubstrateDescriptor`` requires ``step_cost_model`` and an outer/inner
  two-layer pool. The GPU substrate has no measured step cost yet and has a
  single block layer, so constructing a descriptor would mean inventing
  values. ``main()`` shows the constructor refusing instead.
* ``src/continuum/`` is read-only on this branch (directive G-01 section 0).
  The fields the neutral dataclass lacks are listed in ``FIT_GAPS`` and in
  GTASK02, as a report -- not as a patch.

Configuration-dependent values (pool size, capture grid) are functions of the
server arguments, because on this stack they are runtime flags, not compile
artifacts.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from continuum.substrate import HitFormula, Provenance, SubstrateDescriptor  # noqa: E402

STACK = "RTX A6000 / vllm 0.22.0 (torch 2.11.0+cu130) / Qwen3-4B@1cfa9a72 bf16 / model runner v2"

BLOCK_TOKENS = 16
DEFAULT_CAPTURE_SIZES_MAX_NUM_SEQS_8 = (1, 2, 4, 8, 16)


def default_capture_sizes(max_num_seqs: int, max_num_batched_tokens: int) -> tuple[int, ...]:
    """vllm/config/vllm.py:1647-1708 restated (balanced mode, no spec decode)."""
    top = min(min(max_num_seqs * 2, 512), max_num_batched_tokens)
    sizes = [s for s in (1, 2, 4) if s <= top]
    if top >= 8:
        sizes += list(range(8, min(top + 1, 256), 8))
    if top >= 256:
        sizes += list(range(256, top + 1, 16))
    if max_num_batched_tokens <= top and max_num_batched_tokens not in sizes:
        sizes.append(max_num_batched_tokens)
    return tuple(sorted(set(sizes)))


def padded_size(num_tokens: int, capture_sizes: tuple[int, ...]) -> int | None:
    """Smallest capture size >= num_tokens; None means eager (no cudagraph).

    The unit is scheduled *tokens*, not requests (v1/worker/gpu/cudagraph_utils.py
    :171-177, :256-269). For a decode-only step the two coincide.
    """
    for s in sorted(capture_sizes):
        if s >= num_tokens:
            return s
    return None


def draft_fields(*, num_gpu_blocks: int = 2048,
                 capture_sizes: tuple[int, ...] = DEFAULT_CAPTURE_SIZES_MAX_NUM_SEQS_8) -> dict:
    """Fields that GTASK01/GTASK02 settled, with provenance.

    ``num_gpu_blocks`` is the ``--num-gpu-blocks-override`` value; block 0 is
    the permanent null block, so the evictable pool is ``num_gpu_blocks - 1``.
    """
    usable = num_gpu_blocks - 1
    fields = {
        "bucket_sizes": tuple(sorted(capture_sizes)),
        "inner_block_tokens": BLOCK_TOKENS,
        "inner_block_count": usable,
        "inner_eviction_policy": "lru-by-release/tail-first",
        "hit_formula": HitFormula(block_tokens=BLOCK_TOKENS, reserve_last_query_token=True),
        "kv_pool_tokens": usable * BLOCK_TOKENS,
    }
    provenance = {
        "bucket_sizes": Provenance(
            "stack", "GTASK01", "source-read",
            "cudagraph capture sizes; default [1,2,4,8,16] at max_num_seqs=8 "
            "(config/vllm.py:1647-1708), user list via compilation_config. Runtime "
            "confirmed in GTASK02 L1 ([1,2,4,8,16]) and L2 ([1,2,4,6,8]). Mapping "
            "unit is scheduled tokens; > max runs eager. A server flag, not a compile artifact",
        ),
        "inner_block_tokens": Provenance(
            "stack", "GTASK02", "measured",
            "CacheConfig.DEFAULT_BLOCK_SIZE=16 kept by FLASH_ATTN (source-read GTASK01); "
            "cache_config_info block_size=16 and hit cases H1-H4b/H5 all multiples of 16 (GTASK02)",
        ),
        "inner_block_count": Provenance(
            "stack", "GTASK02", "measured",
            "= --num-gpu-blocks-override minus the null block (block_pool.py:176). "
            "Override applied: log 'Overriding num_gpu_blocks=16034 with "
            "num_gpu_blocks_override=2048' (GTASK02 L2). Profiled default at gpu_memory_utilization "
            "0.92 was 16,034 (L1)",
        ),
        "inner_eviction_policy": Provenance(
            "class", "GTASK01", "source-read",
            "free queue ordered by release (append on free, popleft on alloc); within a "
            "request tail block first (single_type_kv_cache_manager.py:350); never-used "
            "blocks first. Shape is class (paged prefix cache), tie-breaks are stack",
        ),
        "hit_formula": Provenance(
            "class", "GTASK02", "measured",
            "floor(min(shared, query-1)/16)*16 matched 5/5 cases on L1 and L2 plus H5. "
            "shared counts KV-computed tokens of the earlier request INCLUDING generated "
            "tokens (prompt + output - 1); H5 observed 1,024, prompt-only reading gives 992",
        ),
        "kv_pool_tokens": Provenance(
            "stack", "GTASK02", "derived",
            "(num_gpu_blocks - 1) * 16 evictable-pool tokens. vLLM's 'GPU KV cache size' "
            "log is max_concurrency * max_model_len = num_gpu_blocks * 16 (32,768 at 2048)",
        ),
    }
    return {"fields": fields, "provenance": provenance}


# Values this substrate needs but that are NOT filled, because they must be measured.
NOT_FILLED_MEASUREMENT_REQUIRED = (
    "step_cost_model (decode-only FULL-graph step cost per capture size; mixed "
    "prefill+decode PIECEWISE/eager step cost)",
    "prefill_cost_model (and it is not exclusive here; see FIT_GAPS)",
)

# Where the neutral SubstrateDescriptor does not fit this substrate (report only).
FIT_GAPS = (
    "outer_slot_count / outer_slot_tokens / outer_eviction_policy are required, but "
    "this stack has one block layer. Any value (e.g. outer = inner) would make "
    "block_ratio, outer_slots_for and survives_gap compute an allocation-FIFO "
    "count law that the source does not implement",
    "no field for lookup/allocate order (resume_allocates_first: RBLN True, here "
    "False with hit blocks touched before allocation)",
    "no field for when an entry becomes evictable / which event starts the survival "
    "window (RBLN: allocation order; here: release order). A policy string cannot "
    "carry tail-first and never-used-first tie-breaks",
    "no field for preemption (exists here: recompute, FCFS victim = latest admitted, "
    "trigger = running demand > usable blocks; cannot be disabled)",
    "no field for non-request KV consumers (RBLN: per-step dummy block, PRE_EVICT; "
    "here: one constant null block)",
    "HitFormula has no notion of which tokens are cacheable (RBLN layer 2: prefill "
    "tokens only; here: every KV-computed token incl. generated)",
    "bucket_for() maps request counts and raises above the top bucket; here the "
    "unit is scheduled tokens and anything above the top capture size runs eager "
    "(no padding). A mixed prefill+decode step has no bucket in the RBLN sense",
    "StepCostModel is one curve keyed by bucket; here FULL (uniform decode), "
    "PIECEWISE (mixed <= top) and eager (> top) steps need separate curves",
    "PrefillCostModel assumes exclusive prefill (stall = prefill_s x decoders). "
    "Here prefill mixes into decode steps even with chunked prefill disabled; "
    "there is no stall term, only a mixed-step cost. Needs a prefill_exclusive flag",
    "no fields for admission gates: max_num_seqs, max_num_batched_tokens (token "
    "budget per step), full-prompt-must-fit (scheduler_reserve_full_isl)",
    "kv_pool_tokens does not say physical vs usable (null block) capacity",
)


def main() -> int:
    d = draft_fields()
    print(f"DRAFT substrate: {STACK}")
    for name, value in d["fields"].items():
        prov = d["provenance"][name]
        print(f"  {name:<22} = {value!r}  [{prov.layer}/{prov.kind}/{prov.origin}]")
    print(f"  default grid at max_num_seqs=8, budget 2048: {default_capture_sizes(8, 2048)}")
    print("  padding (tokens -> graph size) on [1,2,4,8,16]:",
          {n: padded_size(n, DEFAULT_CAPTURE_SIZES_MAX_NUM_SEQS_8) for n in range(1, 18)})
    print("\nnot filled (measurement required):")
    for item in NOT_FILLED_MEASUREMENT_REQUIRED:
        print(f"  - {item}")
    print("\nconstructor check (expected to refuse):")
    try:
        SubstrateDescriptor(
            name=STACK, step_cost_model=None,  # type: ignore[arg-type]
            outer_slot_count=None, outer_slot_tokens=None,  # type: ignore[arg-type]
            outer_eviction_policy=None,  # type: ignore[arg-type]
            provenance=d["provenance"], **d["fields"],
        )
        print("  UNEXPECTED: descriptor constructed")
        return 1
    except (TypeError, ValueError) as exc:
        print(f"  refused: {type(exc).__name__}: {exc}")
    print("\nfit gaps (report to Advisor; src/continuum/ not modified):")
    for i, gap in enumerate(FIT_GAPS, 1):
        print(f"  {i:>2}. {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
