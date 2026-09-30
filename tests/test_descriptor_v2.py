#!/usr/bin/env python3
"""Descriptor v2 checks (TASK84, directive 06 work B). Runs without pytest:

    env -u PYTHONPATH python3 tests/test_descriptor_v2.py [--gtask04 <predictions.json>]

1. The RBLN CA25 v2 instance's v1 view equals the v1 instance every earlier
   script used, field for field (provenance texts aside).
2. ``with_config`` reproduces ``config_search.descriptor_for`` bit for bit.
3. The model's v2 entry point reproduces the RBLN sequential cliff (TASK14/15).
4. A TEST-ONLY GPU descriptor built from the GPU column of
   DESCRIPTOR_REQUIREMENTS.md reproduces GTASK04's 60 blind predictions with
   no wrapper: model code + descriptor only. The GPU instance proper belongs to
   the GPU file area (decision 7); this one exists to show v2 can express it.
5. The simulator refuses rules it does not implement, and the reference replay
   builds identically from v1 and v2.

GTASK04's prediction file is read from ``origin/gpu-a6000`` with ``git show``
unless a path is given (the GPU file area is read-only here).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

from continuum.model import protocol as PR  # noqa: E402
from continuum.model.reference import FifoReplay  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.substrate import (  # noqa: E402
    NA, Admission, Grid, HitFormula, Pipeline, PoolLayer, PrefillSpec, Provenance,
    Semantics, SubstrateDescriptorV2,
)
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_V2, RBLN_CA25_VLLM_RBLN_0111  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        FAILS.append(label)


# -- 4. test-only GPU descriptor -------------------------------------------------

def _p(origin: str, kind: str, note: str, layer: str = "stack") -> Provenance:
    return Provenance(layer, origin, kind, note)


def gpu_test_descriptor(num_gpu_blocks: int = 801, max_num_seqs: int = 1) -> SubstrateDescriptorV2:
    """GPU column of DESCRIPTOR_REQUIREMENTS.md (GTASK01-06). TEST ONLY."""
    return SubstrateDescriptorV2(
        name="TEST ONLY -- A6000 / vllm 0.22.0 values from DESCRIPTOR_REQUIREMENTS.md",
        layers=(PoolLayer(name="block_pool", unit_tokens=16, capacity_units=num_gpu_blocks - 1,
                          reserved_units=1, value_source="server_arg",
                          eviction_order="release_lru"),),
        reuse_layer=0,
        semantics=Semantics(
            evictable_when="immediate", window_start="release", intra_request_loss="tail_first",
            initial_free_order="never_used_first", active_pinned=True,
            resume_allocates_first=False, hit_protection="touch_before_alloc",
            failed_admission_evicts=False, cache_registration="at_allocation",
            kv_tokens_held="computed", cacheable_tokens="computed",
            dummy_mode="none", dummy_ceiling=NA, preemption="recompute",
            preemption_trigger="running demand for a new block exceeds free blocks",
            preemption_victim="fcfs: last admitted running request",
            preemption_disableable=False, preempted_keeps_cache=True),
        admission=Admission(max_running=max_num_seqs, max_running_source="server_arg",
                            step_token_budget=2048, admission_requires_full_prompt=True),
        grid=Grid(sizes=(1, 2, 4, 8, 16), unit="tokens", value_source="server_arg",
                  above_top="eager", mixed_step_graph="piecewise"),
        hit_formula=HitFormula(block_tokens=16, reserve_last_query_token=True),
        step_cost={"decode": None, "mixed": None, "eager": None},
        step_cost_measurement=None,
        prefill=PrefillSpec(execution="mixed", cost=None, chunk_tokens=2048),
        pipeline=Pipeline(in_flight_batches=2, startup_nonrequest_steps=2),
        provenance={
            "layers[0].unit_tokens": _p("GTASK02", "measured", "block_size 16; hits multiples of 16"),
            "layers[0].capacity_units": _p("GTASK02", "measured", "--num-gpu-blocks-override minus null"),
            "layers[0].reserved_units": _p("GTASK01", "source-read", "null block, block_pool.py:176"),
            "layers[0].value_source": _p("GTASK02", "measured", "server argument"),
            "layers[0].eviction_order": _p("GTASK01", "source-read", "free queue by release", "class"),
            "reuse_layer": _p("GTASK04", "measured", "single layer; four channels agree"),
            "semantics.evictable_when": _p("GTASK01", "source-read", "scheduler.py:1480->1862"),
            "semantics.window_start": _p("GTASK01", "source-read", "blocks enter the queue at release"),
            "semantics.intra_request_loss": _p("GTASK01", "source-read", "reversed(req_blocks)"),
            "semantics.initial_free_order": _p("GTASK04", "measured", "never-used blocks first"),
            "semantics.active_pinned": _p("GTASK01", "source-read", "ref_cnt > 0 is off the queue"),
            "semantics.resume_allocates_first": _p("GTASK01", "source-read", "scheduler.py:594->721"),
            "semantics.hit_protection": _p("GTASK01", "source-read", "kv_cache_manager.py:397->404"),
            "semantics.failed_admission_evicts": _p("GTASK01", "source-read", "kv_cache_manager.py:387"),
            "semantics.cache_registration": _p("GTASK01", "source-read", "kv_cache_manager.py:421-425"),
            "semantics.kv_tokens_held": _p("GTASK02", "measured", "prompt + output - 1 (H5)"),
            "semantics.cacheable_tokens": _p("GTASK04", "measured", "resume hit 2,016 > 2,000"),
            "semantics.dummy_mode": _p("GTASK01", "source-read", "padding uses PAD_SLOT_ID"),
            "semantics.dummy_ceiling": _p("GTASK01", "source-read", "no dummy consumer"),
            "semantics.preemption": _p("GTASK01", "source-read", "recompute, no swap"),
            "semantics.preemption_trigger": _p("GTASK01", "source-read", "block demand > free"),
            "semantics.preemption_victim": _p("GTASK01", "source-read", "FCFS last running"),
            "semantics.preemption_disableable": _p("GTASK01", "source-read", "no switch"),
            "semantics.preempted_keeps_cache": _p("GTASK01", "source-read", "hash kept"),
            "admission.max_running": _p("GTASK04", "measured", "--max-num-seqs"),
            "admission.max_running_source": _p("GTASK02", "measured", "server argument"),
            "admission.step_token_budget": _p("GTASK02", "measured", "--max-num-batched-tokens"),
            "admission.admission_requires_full_prompt": _p("GTASK01", "source-read",
                                                          "scheduler_reserve_full_isl"),
            "grid.sizes": _p("GTASK02", "measured", "cudagraph_capture_sizes"),
            "grid.unit": _p("GTASK01", "source-read", "scheduled tokens"),
            "grid.value_source": _p("GTASK02", "measured", "server argument"),
            "grid.above_top": _p("GTASK01", "source-read", "eager above the top size"),
            "grid.mixed_step_graph": _p("GTASK01", "source-read", "PIECEWISE"),
            "hit_formula": _p("GTASK02", "measured", "floor(min(shared, query-1)/16)*16", "class"),
            "prefill.execution": _p("GTASK01", "source-read", "mixed even with chunking off"),
            "prefill.chunk_tokens": _p("GTASK02", "measured", "max_num_batched_tokens 2048"),
            "pipeline.in_flight_batches": _p("GTASK01", "source-read", "async scheduling"),
            "pipeline.startup_nonrequest_steps": _p("GTASK03", "measured", "warmup 2 steps"),
        },
    )


def gtask04(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text())
    blob = subprocess.run(
        ["git", "-C", str(REPO), "show",
         "origin/gpu-a6000:experiments/gpu/survival/prediction/predictions.json"],
        check=True, capture_output=True, text=True).stdout
    return json.loads(blob)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtask04", help="path to GTASK04 predictions.json (default: git show)")
    a = ap.parse_args()

    # 1. v1 view
    v1 = RBLN_CA25_VLLM_RBLN_0111
    expect = dict(bucket_sizes=(1, 2, 4, 8), outer_slot_count=8, outer_slot_tokens=8192,
                  inner_block_tokens=128, inner_block_count=512, outer_eviction_policy="fifo",
                  inner_eviction_policy="lru", kv_pool_tokens=65536, release_rule="immediate",
                  dummy_mode="pre_evict", resume_allocates_first=True)
    check(all(getattr(v1, k) == v for k, v in expect.items()), "RBLN v1 view scalar fields")
    check(v1.step_cost_model.fixed_s_by_bucket == {1: (9.51 + 0.36) / 1000.0, 2: (10.05 + 0.37) / 1000.0,
                                                   4: (10.355 + 0.47) / 1000.0,
                                                   8: (12.4025 + 0.5675) / 1000.0}
          and v1.step_cost_model.marginal_s_per_request == 0.0413 / 1000.0
          and v1.step_cost_model.intercept_s == 0.501 / 1000.0, "RBLN v1 view step cost")
    check(v1.prefill_cost_model.per_chunk_s == 0.021206
          and v1.prefill_cost_model.drift_s_per_token == 6.399e-07, "RBLN v1 view prefill cost")
    check(set(v1.provenance) == {f for f in expect} | {"step_cost_model", "hit_formula",
                                                         "prefill_cost_model"},
          "RBLN v1 view provenance keys")

    # 2. configuration variants
    from config_search import descriptor_for
    for grid, batch in (((1, 4, 6, 8, 10, 16), 16), ((1, 2, 3, 4, 6, 16), 16), ((1, 2, 4, 8, 16), 16)):
        old = descriptor_for(v1, grid, batch)
        new = RBLN_CA25_V2.with_config(grid=grid, max_running=batch, reuse_capacity=batch)
        nv = new.legacy_view()
        same = (nv.step_cost_model == old.step_cost_model and nv.bucket_sizes == old.bucket_sizes
                and nv.outer_slot_count == old.outer_slot_count
                and nv.kv_pool_tokens == old.kv_pool_tokens)
        check(same, f"with_config {grid} b{batch} == config_search.descriptor_for")

    # 3. RBLN sequential cliff: target 2000 (8 generated), backgrounds of 8 tokens generated
    for bg in (500, 1000, 2000, 4000):
        alive = [PR.sequential_protocol(RBLN_CA25_V2, target_prompt=2000, target_generated=8,
                                        backgrounds=[(bg, 8)] * m, resume_prompt=2008).hit_tokens
                 for m in range(9)]
        check(alive == [1920] * 7 + [0, 0], f"RBLN cliff at B = 7, background {bg} tokens")

    # 4. GTASK04 reproduction
    pred = gtask04(a.gtask04)
    gpu = gpu_test_descriptor(num_gpu_blocks=pred["num_gpu_blocks"])
    check(gpu.reuse_pool.capacity_units == pred["capacity"], "GPU test descriptor capacity 800")
    mism = []
    for t in pred["trials"]:
        gen = pred["target_gen"][t["cond"]]
        resume = pred["target_prompt"] + (gen if t["cond"] == "ii" else 0) + pred["suffix"]
        r = PR.sequential_protocol(gpu, target_prompt=pred["target_prompt"], target_generated=gen,
                                   backgrounds=[(t["bg"], pred["bg_gen"])] * t["m"],
                                   resume_prompt=resume)
        got = (r.hit_tokens, r.cacheable_units_evicted, r.target_units,
               r.background_units[0] if r.background_units else t["u_bg"], r.overflow_units)
        want = (t["pred_hit"], t["pred_target_blocks_evicted"], t["u_target"], t["u_bg"],
                t["overflow_units"])
        if got != want:
            mism.append((t["cond"], t["bg"], t["m"], got, want))
    check(len(pred["trials"]) == 60 and not mism,
          f"GTASK04 {len(pred['trials'])} trials reproduced with no wrapper "
          f"(hit, T blocks evicted, u_T, u_bg, overflow); mismatches {len(mism)}")
    for m in mism[:10]:
        print("   ", m)

    # 5. refusals and replay
    try:
        simulate(gpu, [], SimConfig(max_running_requests=1, semantics="descriptor"))
        check(False, "simulator refuses the GPU rules")
    except ValueError as e:
        check("does not implement" in str(e) or "legacy" in str(e), f"simulator refuses GPU rules ({e})")
    r1 = FifoReplay.for_descriptor(v1)
    r2 = FifoReplay.for_descriptor(RBLN_CA25_V2)
    check((r1.capacity, r1.ceiling, r1.release, r1.dummy, r1.allocate_before_lookup)
          == (r2.capacity, r2.ceiling, r2.release, r2.dummy, r2.allocate_before_lookup),
          "FifoReplay from v1 == from v2")
    check(RBLN_CA25_V2.unknown_paths() == [
        "semantics.failed_admission_evicts", "semantics.cache_registration",
        "semantics.dummy_ceiling", "admission.step_token_budget",
        "admission.admission_requires_full_prompt", "pipeline.in_flight_batches",
        "pipeline.startup_nonrequest_steps"], "RBLN unknown fields are exactly the UNKNOWN list")
    try:
        SubstrateDescriptorV2(**{**RBLN_CA25_V2.__dict__,
                                 "provenance": {k: v for k, v in RBLN_CA25_V2.provenance.items()
                                                if k != "semantics.window_start"}})
        check(False, "missing provenance refused")
    except ValueError:
        check(True, "missing provenance refused")

    print("FAIL" if FAILS else "PASS", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
