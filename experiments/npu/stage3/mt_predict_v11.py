#!/usr/bin/env python3
"""Analytic path of model v1.1 (TASK85): v1's path with the survival term
replaced by the queue-aware load chain (``continuum.model.survival_v11``).

Everything else is ``mt_predict.analytic`` unchanged: B2 occupancy (already
``mu(min(n, M))`` with FCFS waiting above ``M``), the reuse / prefill fixed
point, B3 step costs, B4 interference. The substrate is read from the v2
descriptor -- capacity from the reuse layer, ``M`` from ``admission``, the
lookup order from ``semantics`` -- and nothing accelerator specific is here.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival_v11 as V11  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_V2  # noqa: E402


def descriptor_v2(grid: tuple[int, ...], batch: int):
    """The RBLN v2 instance at a compile configuration: grid, and batch size as
    both the running ceiling and the outer-slot count (TASK08)."""
    return RBLN_CA25_V2.with_config(grid=tuple(grid), max_running=batch, reuse_capacity=batch)


def plan_gaps(plans) -> list[float]:
    """Every tool gap the plans list (final turns: 0, the successor starts at once)."""
    return [t.gap_after_s for plan in plans for s in plan.slots for x in s.sessions for t in x.turns]


def analytic_v11(n: int, grid: tuple[int, ...], batch: int, st: dict, gap_law,
                 *, completion_order: str = "admission", iters: int = 30) -> dict:
    d2 = descriptor_v2(grid, batch)
    V11.check_substrate(d2)
    m_run = d2.max_running
    cap = d2.reuse_pool.capacity_units
    desc = P.descriptor(grid, batch)          # numeric v1 view, as the v1 path uses
    assert desc.step_cost_model == d2.legacy_view().step_cost_model
    idle = P._compress(st["idle_samples"])
    p_s = 0.9
    for _ in range(iters):
        ep = st["share_first"] * st["p_first_s"] + (1 - st["share_first"]) * (
            p_s * st["p_hit_s"] + (1 - p_s) * st["p_miss_s"])
        w = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                             think_mean_s=st["think_mean_s"], prefill_mean_s=ep,
                             max_running=m_run)
        occ = O.solve_occupancy(w, desc.step_time_s)
        others = O.others_in_engine_at_arrival(w, desc.step_time_s)
        t_run = desc.step_time_s(max(1, round(occ.mean_running)))
        service = ep + (st["gen_mean"] - 1) * t_run / occ.phi
        phi = occ.phi
        g = st["gen_mean"] - 1
        inp = V11.LoadChainInputs(
            sessions=n, max_running=m_run, capacity=cap, gap=gap_law,
            completion_rate=lambda r, phi=phi, g=g: phi / (g * desc.step_time_s(min(r, m_run))),
            others_at_arrival=others, s_active=service,
            own_alloc=bool(d2.semantics.resume_allocates_first),
            completion_order=completion_order)
        new_ps = V11.survival_probability_v11(inp, idle)
        if abs(new_ps - p_s) < 1e-7:
            p_s = new_ps
            break
        p_s = 0.5 * (p_s + new_ps)
    ep = st["share_first"] * st["p_first_s"] + (1 - st["share_first"]) * (
        p_s * st["p_hit_s"] + (1 - p_s) * st["p_miss_s"])
    x = occ.throughput_per_s
    decode_s_per_s = sum(occ.step_share[r] * desc.step_time_s(r) for r in occ.step_share) \
        * occ.steps_per_s
    h = occ.step_share
    pad = sum(v * (desc.bucket_for(r) - r) for r, v in h.items()) / \
        sum(v * desc.bucket_for(r) for r, v in h.items())
    arr = O.arrival_running_distribution(w, desc.step_time_s)
    e_k = sum(k * p for k, p in arr.items())
    return {"reuse_rate": p_s, "h": {int(k): v for k, v in h.items()}, "padding": pad,
            "decode_per_turn_s": decode_s_per_s / x, "prefill_per_turn_s": ep,
            "device_per_turn_s": decode_s_per_s / x + ep,
            "W_per_turn_s": ep * e_k, "throughput_per_s": x,
            "cycle_s": st["think_mean_s"] + occ.mean_response_s,
            "mean_running": occ.mean_running, "phi": occ.phi}
