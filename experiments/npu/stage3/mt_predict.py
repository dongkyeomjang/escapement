#!/usr/bin/env python3
"""Predictions for the steady-state multi-turn experiment, from three predictors.

* ``analytic`` -- model v1: B2 occupancy (closed product form with the
  exclusive-prefill fixed point), B1 v1 survival (steady-state birth-death
  chain), B3 step costs, B4 interference. Reuse and prefill cost are solved
  together: the prefill share depends on how often a turn misses, and the
  miss rate depends on the occupancy.
* ``sim_default`` -- the step simulator with its default semantics.
* ``sim_observed`` -- the simulator with the substrate's observed semantics
  (``release_rule="immediate"``, ``dummy_mode="pre_evict"``; TASK72/TASK74).

Inputs are restricted to descriptor constants measured by TASK72 and the plan
files. Nothing measured in the multi-turn pilot is read here.

"Per turn" means per request admitted in the evaluation window. The window is
``WindowRule`` applied to the predictor's own completions (the simulator), or
the steady state itself (analytic).
"""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

from continuum.model import grid as G  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival_v1 as V1  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402
from config_search import descriptor_for  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

CONFIGS = {
    "BASE": ((1, 2, 4, 8), 8),
    "BATCHONLY": ((1, 2, 4, 8, 16), 16),
    "TUNED": ((1, 4, 6, 8, 10, 16), 16),
}


def descriptor(grid: tuple[int, ...], batch: int):
    return descriptor_for(D, tuple(grid), batch)


# -- workload statistics from a plan ------------------------------------------------

def plan_stats(plans: list[MultiTurnPlan]) -> dict:
    """Per-request averages the analytic path needs. Only sessions a run can
    plausibly reach are weighted equally; the plan lists more than a run uses,
    and the extra sessions are drawn from the same law."""
    gens, gaps, first, hit_q, full_l = [], [], [], [], []
    for plan in plans:
        for s in plan.slots:
            for x in s.sessions:
                ctx = 0
                prev_prompt = None
                for t in x.turns:
                    prompt = ctx + t.new_segment_tokens
                    gens.append(t.generation_tokens)
                    gaps.append(t.gap_after_s)   # final turn: 0 (renewal is immediate)
                    if t.index == 0:
                        first.append(prompt)
                    else:
                        cached = (min(prev_prompt, prompt - 1) // D.inner_block_tokens) \
                            * D.inner_block_tokens
                        hit_q.append(prompt - cached)
                        full_l.append(prompt)
                    prev_prompt = prompt
                    ctx = prompt + t.generation_tokens
    pm = D.prefill_cost_model
    n_first, n_later = len(first), len(hit_q)
    idle = [g for g in gaps if g > 0]
    return {
        "gen_mean": statistics.mean(gens),
        "think_mean_s": statistics.mean(gaps),
        "share_first": n_first / (n_first + n_later),
        "p_first_s": statistics.mean(pm.prefill_s(q) for q in first),
        "p_hit_s": statistics.mean(pm.prefill_s(q) for q in hit_q),
        "p_miss_s": statistics.mean(pm.prefill_s(q) for q in full_l),
        "idle_samples": [(g, 1.0) for g in idle] or [(0.0, 1.0)],
        "turns": plans[0].turns,
        "requests": n_first + n_later,
    }


def _compress(samples, bins=40):
    """Quantile-compress idle samples: the chain is evaluated per sample."""
    xs = sorted(g for g, _ in samples)
    if len(xs) <= bins:
        return [(x, 1.0) for x in xs]
    out = []
    for b in range(bins):
        lo = int(b * len(xs) / bins)
        hi = int((b + 1) * len(xs) / bins)
        chunk = xs[lo:hi]
        out.append((statistics.mean(chunk), float(len(chunk))))
    return out


# -- analytic path ---------------------------------------------------------------------

def analytic(n: int, grid: tuple[int, ...], batch: int, st: dict, *, iters: int = 30) -> dict:
    desc = descriptor(grid, batch)
    idle = _compress(st["idle_samples"])
    p_s = 0.9
    for _ in range(iters):
        ep = st["share_first"] * st["p_first_s"] + (1 - st["share_first"]) * (
            p_s * st["p_hit_s"] + (1 - p_s) * st["p_miss_s"])
        w = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                             think_mean_s=st["think_mean_s"], prefill_mean_s=ep,
                             max_running=batch)
        occ = O.solve_occupancy(w, desc.step_time_s)
        arr = O.arrival_running_distribution(w, desc.step_time_s)
        t_run = desc.step_time_s(max(1, round(occ.mean_running)))
        service = ep + (st["gen_mean"] - 1) * t_run / occ.phi
        lam = occ.throughput_per_s * (n - 1) / n
        new_ps = V1.steady_state_survival(
            capacity=batch, running_others_pmf=arr, lam=lam, mu=1.0 / service,
            s_active=service, idle_samples=idle)
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
    e_k = sum(k * p for k, p in arr.items())
    return {"reuse_rate": p_s, "h": {int(k): v for k, v in h.items()}, "padding": pad,
            "decode_per_turn_s": decode_s_per_s / x, "prefill_per_turn_s": ep,
            "device_per_turn_s": decode_s_per_s / x + ep,
            "W_per_turn_s": ep * e_k, "throughput_per_s": x,
            "cycle_s": st["think_mean_s"] + occ.mean_response_s,
            "mean_running": occ.mean_running, "phi": occ.phi}


# -- simulator path --------------------------------------------------------------------

def simulate_plan(plan: MultiTurnPlan, grid: tuple[int, ...], batch: int, *,
                  semantics: str = "default", eval_s: float = 120.0) -> dict:
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    kw = {}
    if semantics == "observed":
        kw = {"release_rule": "immediate", "dummy_mode": "pre_evict"}
    res = simulate(descriptor(grid, batch), sessions,
                   SimConfig(max_running_requests=batch, session_start_s=start,
                             successor=succ, **kw))
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=eval_s)
    comp = [(slot_of[r.session_index], r.finish_s) for r in res.requests]
    w0 = rule.warmup_end(comp, plan.n_slots)
    if w0 is None:
        raise RuntimeError("simulated run never left warm-up")
    w1 = w0 + eval_s
    # A request belongs to the window by its send (= arrival) time, as in the runner.
    reqs = [r for r in res.requests if w0 <= r.arrival_s < w1]
    later = [r for r in reqs if r.turn > 0]
    decode = [s for s in res.decode_steps if w0 <= s.start_s < w1]
    pre = [s for s in res.prefill_steps if w0 <= s.start_s < w1]
    h: dict[int, float] = defaultdict(float)
    for s in decode:
        h[s.running] += 1
    tot = sum(h.values())
    n_req = len(reqs)
    pad_num = sum(s.bucket - s.running for s in decode)
    pad_den = sum(s.bucket for s in decode)
    return {"reuse_rate": sum(1 for r in later if r.cached_tokens > 0) / len(later) if later else None,
            "reuse": (sum(1 for r in later if r.cached_tokens > 0), len(later)),
            "h_counts": dict(h), "h": {k: v / tot for k, v in h.items()} if tot else {},
            "padding": pad_num / pad_den if pad_den else None,
            "decode_per_turn_s": sum(s.duration_s for s in decode) / n_req,
            "prefill_per_turn_s": sum(s.duration_s for s in pre) / n_req,
            "device_per_turn_s": (sum(s.duration_s for s in decode)
                                  + sum(s.duration_s for s in pre)) / n_req,
            "W_per_turn_s": sum(s.duration_s * s.running for s in pre) / n_req,
            "requests_in_window": n_req, "warmup_end_s": w0,
            "throughput_per_s": n_req / eval_s}


# -- grid selection -------------------------------------------------------------------

def dp_grid(h: dict[int, float], *, top: int = 16, k: int = 6) -> tuple[int, ...]:
    fixed = G.interpolated_fixed_costs(D.step_cost_model.fixed_s_by_bucket, range(1, top + 1))
    hh = {n: v for n, v in h.items() if 1 <= n <= top and v > 0}
    return G.optimal_grid(hh, top=top, max_buckets=k, fixed=fixed).grid


def best_response_chain(h_of_grid, start: tuple[int, ...], *, max_iter: int = 5):
    """Iterate grid -> predicted h -> DP grid until a fixed point or a cycle."""
    chain = [tuple(start)]
    cur = tuple(start)
    for _ in range(max_iter):
        nxt = dp_grid(h_of_grid(cur))
        if nxt == cur:
            return chain, "fixed_point"
        if nxt in chain:
            chain.append(nxt)
            return chain, "cycle"
        chain.append(nxt)
        cur = nxt
    return chain, "no_convergence"
