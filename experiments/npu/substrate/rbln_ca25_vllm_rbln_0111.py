#!/usr/bin/env python3
"""Measured substrate: RBLN CA25 + vllm-rbln 0.11.1 + optimum-rbln 0.11.1.

This is one *instance*. Every constant below was measured on `atom-max8` with
the `Qwen3-4B-rbln-b8-s8192-d4-mb` artifact; none of them may be carried to a
different accelerator, stack version, or compile configuration. The shapes
they instantiate live in `src/continuum/substrate/descriptor.py`.

Run this file to print the descriptor and its layer summary.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from continuum.substrate import (  # noqa: E402
    HitFormula,
    PrefillCostModel,
    Provenance,
    StepCostModel,
)
from continuum.substrate.v2 import (  # noqa: E402
    NA,
    Admission,
    Grid,
    Pipeline,
    PoolLayer,
    PrefillSpec,
    Semantics,
    SubstrateDescriptorV2,
)

# Bucket-determined part of a decode step: model forward p50 + sampler p50,
# both measured per bucket in TASK13. Values in seconds.
_FIXED_S_BY_BUCKET = {
    1: (9.51 + 0.36) / 1000.0,
    2: (10.05 + 0.37) / 1000.0,
    4: (10.355 + 0.47) / 1000.0,
    8: (12.4025 + 0.5675) / 1000.0,
}

STEP_COST = StepCostModel(
    fixed_s_by_bucket=_FIXED_S_BY_BUCKET,
    # Least-squares slope of the residual (end-to-end ITL minus the two spans
    # above) against actual request count, TASK13.
    marginal_s_per_request=0.0413 / 1000.0,
    intercept_s=0.501 / 1000.0,
)

HIT_FORMULA = HitFormula(block_tokens=128, reserve_last_query_token=True)

# Prefill runs exclusively on this stack, so its duration is charged to every
# session that was decoding at the time. Fitted in TASK22 on four points
# (500 / 2000 / 2008 / 6000 computed tokens); worst residual 2.4 ms.
PREFILL_COST = PrefillCostModel(
    chunk_tokens=128,
    per_chunk_s=0.021206,
    drift_s_per_token=6.399e-07,
)

_NOTES = (
    "Adding the prefill serialization term closes the TASK20 cost-model "
    "gap: predicted/measured ITL sum moves from 0.57-0.86 to 0.97-1.04 "
    "across every (N, arm) cell.",
    "Reuse cliff observed at background_requests = 7 and reproduced 12/12 "
    "in TASK15; survives_gap() encodes the law candidate that explains it.",
    "vllm:prefix_cache_hits_total reports the inner-block layer and can "
    "overstate actual reuse by 100%. Use vllm:prompt_tokens_cached_total "
    "or vllm:request_prefill_kv_computed_tokens for the outer layer.",
    "Measured with the TASK12 observation-only patch applied "
    "(model_base.py sha256 70942d16...).",
)

# Descriptor v2 (TASK84, directive 06): the source of truth. The v1 object
# every earlier script imports is derived from it below.
RBLN_CA25_V2 = SubstrateDescriptorV2(
    name="RBLN-CA25 / vllm-rbln 0.11.1 / Qwen3-4B b8 s8192 d4 multi-bucket",
    layers=(
        PoolLayer(name="inner_block", unit_tokens=128, capacity_units=512,
                  reserved_units=1, value_source="compile", eviction_order="release_lru"),
        PoolLayer(name="outer_slot", unit_tokens=8192, capacity_units=8,
                  reserved_units=0, value_source="compile", eviction_order="allocation_fifo"),
    ),
    reuse_layer=1,
    semantics=Semantics(
        evictable_when="immediate",
        window_start="allocation",
        intra_request_loss="all_or_nothing",
        initial_free_order=NA,
        active_pinned=True,
        resume_allocates_first=True,
        hit_protection=NA,
        failed_admission_evicts=None,
        cache_registration=None,
        kv_tokens_held="computed",
        cacheable_tokens="prefill_only",
        dummy_mode="pre_evict",
        dummy_ceiling=None,
        preemption="none",
    ),
    admission=Admission(max_running=8, max_running_source="compile"),
    grid=Grid(sizes=(1, 2, 4, 8), unit="requests", value_source="compile",
              above_top="impossible", mixed_step_graph=NA),
    hit_formula=HIT_FORMULA,
    step_cost={"decode": STEP_COST},
    step_cost_measurement="device model span p50 + sampler p50 per bucket; residual "
                          "(end-to-end ITL minus both) regressed on actual count",
    prefill=PrefillSpec(execution="exclusive", cost=PREFILL_COST, chunk_tokens=128),
    pipeline=Pipeline(),
    provenance={
        # -- pool layers
        "layers[0].unit_tokens": Provenance(
            "stack", "TASK08", "source-read",
            "cache_config.block_size = prefill_chunk_size = 128 on non-CR NPUs",
        ),
        "layers[0].capacity_units": Provenance(
            "stack", "TASK14", "source-read",
            "num_gpu_blocks - 1; the null block is reserved",
        ),
        "layers[0].reserved_units": Provenance(
            "stack", "TASK14", "source-read", "one null block",
        ),
        "layers[0].value_source": Provenance(
            "stack", "TASK08", "source-read",
            "num_gpu_blocks = batch_size * max_seq_len / 128 + 1, fixed by the compiled artifact",
        ),
        "layers[0].eviction_order": Provenance(
            "class", "TASK14", "source-read",
            "vLLM FreeKVCacheBlockQueue LRU ordering; shared by every vLLM build. "
            "This layer reports the hit metrics but does not decide reuse (TASK14/15)",
        ),
        "layers[1].unit_tokens": Provenance(
            "stack", "TASK08", "source-read",
            "kvcache_block_size defaults to max_seq_len for eager attention",
        ),
        "layers[1].capacity_units": Provenance(
            "stack", "TASK14", "source-read",
            "num_ob = ceil((num_gpu_blocks-1) / block_ratio) = ceil(512/64) = batch_size",
        ),
        "layers[1].reserved_units": Provenance(
            "stack", "TASK14", "derived",
            "no outer slot is held by a non-request consumer permanently; the dummy "
            "block is time-varying (semantics.dummy_mode)",
        ),
        "layers[1].value_source": Provenance(
            "stack", "TASK08", "source-read",
            "kvcache_num_blocks = batch_size at compile; changing it needs a recompile",
        ),
        "layers[1].eviction_order": Provenance(
            "stack", "TASK14", "source-read",
            "FIFOEvictionPolicy is hardcoded (LRUEvictionPolicy exists unused); the victim "
            "is the earliest-allocated inactive slot (TASK63 15/15, TASK64 5/5)",
        ),
        "reuse_layer": Provenance(
            "stack", "TASK15", "measured",
            "reuse is decided by the outer slot (cliff at 7 background requests, 12/12); "
            "the inner-block metric overstates reuse by up to 100 % (TASK14)",
        ),
        # -- semantics
        "semantics.evictable_when": Provenance(
            "stack", "TASK72", "derived",
            "event replay of 1,298 re-arrivals: immediate 1.000 vs deferred 0.934; "
            "consistent with TASK63 B.b0",
        ),
        "semantics.window_start": Provenance(
            "stack", "TASK14", "derived",
            "queue position is fixed at allocation (TASK14 finding 5); MODEL_V0 B1 window",
        ),
        "semantics.intra_request_loss": Provenance(
            "stack", "TASK15", "measured",
            "one outer slot per request up to 8,192 tokens: the prefix survives whole or "
            "not at all (cliff 1,920 -> 0, 12/12)",
        ),
        "semantics.initial_free_order": Provenance(
            "stack", "MODEL_V0", "derived",
            "with allocation-FIFO eviction the victim order is set by allocation, so the "
            "order free slots are handed out does not enter any survival rule",
        ),
        "semantics.active_pinned": Provenance(
            "stack", "TASK63", "measured",
            "running slots are skipped by eviction (K_pin); TASK72 replay 1,298/1,298",
        ),
        "semantics.resume_allocates_first": Provenance(
            "stack", "TASK15", "measured",
            "[PFX] ALLOC precedes MAPPING-SEARCH/CACHE-* for the same request; "
            "TASK72 R1 36/36 trials",
        ),
        "semantics.hit_protection": Provenance(
            "stack", "TASK15", "derived",
            "allocation precedes lookup, so no lookup result exists to protect",
        ),
        "semantics.kv_tokens_held": Provenance(
            "stack", "TASK08", "derived",
            "a request's slot holds the KV of every computed token (the slot is "
            "max_seq_len long); only the slot count enters, and it is 1 below 8,192",
        ),
        "semantics.cacheable_tokens": Provenance(
            "stack", "TASK24", "measured",
            "outer layer caches prefill tokens only: 271/271 re-arrivals",
        ),
        "semantics.dummy_mode": Provenance(
            "stack", "TASK63", "measured",
            "padding request per decode step with 0<n<ceiling; the next admission "
            "takes its slot (74/74). TASK72 replay: pre_evict 1.000 vs reserved 0.847",
        ),
        "semantics.preemption": Provenance(
            "stack", "TASK08", "derived",
            "one slot of max_seq_len per running request and slots = max_running, so a "
            "running request never needs another unit; no preemption observed in any run",
        ),
        # -- admission, grid, costs
        "admission.max_running": Provenance(
            "stack", "TASK08", "source-read",
            "max_num_seqs = compile batch_size",
        ),
        "admission.max_running_source": Provenance(
            "stack", "TASK08", "source-read", "compile batch_size",
        ),
        "grid.sizes": Provenance(
            "stack", "TASK13", "measured",
            "decoder_batch_sizes=[8,4,2,1] at compile; mapping 1->1 2->2 3->4 "
            "4->4 5->8 6->8 7->8 8->8 observed over 4,088 decode steps",
        ),
        "grid.unit": Provenance(
            "stack", "TASK13", "measured", "[BUCKET] request_nums -> padded_batch_size",
        ),
        "grid.value_source": Provenance(
            "stack", "TASK23", "measured",
            "changing the grid required a recompile (TASK23, TASK34, TASK81)",
        ),
        "grid.above_top": Provenance(
            "stack", "TASK08", "derived",
            "running <= batch_size = top grid size in every compiled artifact",
        ),
        "grid.mixed_step_graph": Provenance(
            "stack", "TASK22", "measured", "prefill runs exclusively; no mixed step exists",
        ),
        "hit_formula": Provenance(
            "class", "TASK11", "measured",
            "floor(min(shared, query-1)/128)*128 matched 10/10 conditions. The "
            "shape is vLLM's; the block size is instance level",
        ),
        "step_cost.decode": Provenance(
            "silicon", "TASK13", "measured",
            "model+sampler p50 per bucket; residual slope 0.0413 ms/request. "
            "Absolute values are hardware and model specific",
        ),
        "step_cost_measurement": Provenance(
            "stack", "TASK13", "measured", "channel definition of the decode curve",
        ),
        "prefill.execution": Provenance(
            "stack", "TASK22", "measured",
            "prefill stalls every concurrent decoder for its whole duration; "
            "spike/prefill_time 1.01-1.14 across three injection sizes",
        ),
        "prefill.cost": Provenance(
            "silicon", "TASK22", "measured",
            "ceil(n/128)*(0.021206 + 6.399e-7*n) fitted on four points; worst residual "
            "2.4 ms. Absolute timings are hardware and model specific",
        ),
        "prefill.chunk_tokens": Provenance(
            "stack", "TASK22", "measured", "128-token prefill chunks",
        ),
    },
    notes=_NOTES,
)

# v1 view, field for field what every script before TASK84 imported.
RBLN_CA25_VLLM_RBLN_0111 = RBLN_CA25_V2.legacy_view()


# TASK13 observed median end-to-end ITL per actual request count, in ms.
# Kept here so the descriptor stays falsifiable: if a future edit drifts from
# what was measured, main() shows it.
_OBSERVED_ITL_MS = {
    1: 10.379, 2: 10.975, 3: 11.482, 4: 11.569,
    5: 13.632, 6: 13.696, 7: 13.785, 8: 13.795,
}

# TASK14/TASK15 observed gap survival by background request count.
_OBSERVED_SURVIVAL = {0: True, 3: True, 5: True, 6: True, 7: False, 8: False}


def main() -> int:
    d = RBLN_CA25_VLLM_RBLN_0111
    print(f"substrate: {d.name}")
    print(f"  buckets            : {d.bucket_sizes}")
    print(f"  outer slots        : {d.outer_slot_count} x {d.outer_slot_tokens} tokens")
    print(f"  inner blocks       : {d.inner_block_count} x {d.inner_block_tokens} tokens")
    print(f"  block ratio        : {d.block_ratio}")
    print(f"  eviction           : outer={d.outer_eviction_policy} inner={d.inner_eviction_policy}")
    print(f"  kv pool            : {d.kv_pool_tokens:,} tokens")
    print(f"  min prefix for hit : {d.hit_formula.min_prefix_for_any_hit()} tokens")
    print()
    print(f"{'actual':>7} {'bucket':>7} {'padding':>8} {'model (ms)':>11} "
          f"{'observed':>9} {'resid':>7} {'crossing (ms)':>14}")
    worst = 0.0
    for actual in range(1, d.bucket_sizes[-1] + 1):
        predicted = d.step_time_s(actual) * 1000
        observed = _OBSERVED_ITL_MS[actual]
        resid = predicted - observed
        worst = max(worst, abs(resid))
        print(f"{actual:>7} {d.bucket_for(actual):>7} {d.padding_slots(actual):>8} "
              f"{predicted:>11.3f} {observed:>9.3f} {resid:>7.3f} "
              f"{d.bucket_crossing_cost_s(actual) * 1000:>14.3f}")
    print(f"  worst |residual| = {worst:.3f} ms")
    print()
    print("gap survival (target 2000 tok, resume 2008 tok):")
    for b in range(0, 9):
        live = d.survives_gap(background_requests=b, target_tokens=2000, resume_tokens=2008)
        obs = _OBSERVED_SURVIVAL.get(b)
        mark = "" if obs is None else ("  ok" if obs == live else "  MISMATCH")
        print(f"  B={b}: model={'live' if live else 'dead':<4}"
              f" observed={'-' if obs is None else ('live' if obs else 'dead'):<4}{mark}")
    print()
    print("layer summary:")
    for layer, names in d.layer_summary().items():
        print(f"  {layer:<9}: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
