#!/usr/bin/env python3
"""Predictions of the frozen model v1.1 and of the reference predictors
(TASK85, TASK86).

Predictors per (N, configuration):

* ``v1``   -- ``mt_predict.analytic`` on the cell's plans pooled (the TASK80
  procedure, unchanged).
* ``v11``  -- frozen v1.1 (TASK85): per plan, gap law = zero atom + 3
  exponential phases fitted to that plan's gaps, completion in admission
  order, survival from the queue-aware load chain inside the v1 analytic
  fixed point; the cell value is the mean over plans (reuse, device time per
  turn, padding, h averaged by plan).
* ``sim``  -- the step simulator with the v2 descriptor's observed semantics
  (``SimConfig(semantics="descriptor")``), pooled over plans as
  ``predict_main.py`` pools them.

Inputs: descriptor constants and plan files only. Nothing measured is read.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
from continuum.model import survival_v11 as V  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
V11_PHASES = 3
V11_ORDER = "admission"


def load_plans(index: str, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / index).read_text())
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])]


def v11_plan(args):
    n, grid, batch, plan = args
    law = V.fit_gap_law(Q.plan_gaps([plan]), V11_PHASES)
    r = Q.analytic_v11(n, tuple(grid), batch, P.plan_stats([plan]), law, completion_order=V11_ORDER)
    r["gap_law"] = {"zero_prob": law.zero_prob, "probs": law.probs, "means": law.means}
    return r


def sim_plan(plan: MultiTurnPlan, grid, batch, eval_s: float = 120.0) -> dict:
    """``mt_predict.simulate_plan`` with the descriptor's semantics."""
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(Q.descriptor_v2(grid, batch), sessions,
                   SimConfig(max_running_requests=batch, session_start_s=start, successor=succ,
                             semantics="descriptor"))
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=eval_s)
    w0 = rule.warmup_end([(slot_of[r.session_index], r.finish_s) for r in res.requests], plan.n_slots)
    w1 = w0 + eval_s
    reqs = [r for r in res.requests if w0 <= r.arrival_s < w1]
    later = [r for r in reqs if r.turn > 0]
    dec = [s for s in res.decode_steps if w0 <= s.start_s < w1]
    pre = [s for s in res.prefill_steps if w0 <= s.start_s < w1]
    h: dict[int, float] = defaultdict(float)
    for s in dec:
        h[s.running] += 1
    n_req = len(reqs)
    return {"reuse": (sum(1 for r in later if r.cached_tokens > 0), len(later)),
            "h_counts": dict(h),
            "padding": sum(s.bucket - s.running for s in dec) / sum(s.bucket for s in dec),
            "device_per_turn_s": (sum(s.duration_s for s in dec) + sum(s.duration_s for s in pre)) / n_req,
            "W_per_turn_s": sum(s.duration_s * s.running for s in pre) / n_req,
            "requests_in_window": n_req}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, help="INDEX.json | INDEX_HI.json")
    ap.add_argument("--ns", required=True)
    ap.add_argument("--configs", default="BASE,BATCHONLY,TUNED")
    ap.add_argument("--dp-grids", type=Path, default=PLAN_DIR / "DP_GRIDS.json")
    ap.add_argument("--with-dp8", action="store_true", help="add DP(8) at N = 8 (compiled grid)")
    ap.add_argument("--predictors", default="v1,v11,sim")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    preds = a.predictors.split(",")
    dp = json.loads(a.dp_grids.read_text())
    cells = []
    for n in (int(x) for x in a.ns.split(",")):
        plans = load_plans(a.index, n)
        cfgs = {c: P.CONFIGS[c] for c in a.configs.split(",")}
        if a.with_dp8 and n == 8:
            cfgs["DP"] = (tuple(dp["8"]), 16)
        for cfg, (grid, batch) in cfgs.items():
            cells.append((n, cfg, grid, batch, plans))
    out: dict = {"v11": {"phases": V11_PHASES, "completion_order": V11_ORDER, "per_plan": True},
                 "cells": {}}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {}
        for n, cfg, grid, batch, plans in cells:
            if "v11" in preds:
                futs[(n, cfg)] = [ex.submit(v11_plan, (n, grid, batch, pl)) for pl in plans]
        for n, cfg, grid, batch, plans in cells:
            e: dict = {"grid": list(grid), "batch": batch}
            if "v1" in preds:
                e["v1"] = P.analytic(n, tuple(grid), batch, P.plan_stats(plans))
            if "sim" in preds:
                per = [sim_plan(pl, grid, batch) for pl in plans]
                nreq = sum(p["requests_in_window"] for p in per)
                hits = sum(p["reuse"][0] for p in per)
                tot = sum(p["reuse"][1] for p in per)
                h: dict = defaultdict(float)
                for p in per:
                    for k, v in p["h_counts"].items():
                        h[k] += v
                ht = sum(h.values())
                e["sim"] = {"reuse_rate": hits / tot, "reuse": [hits, tot],
                            "h": {k: v / ht for k, v in sorted(h.items())},
                            "padding": statistics.mean(p["padding"] for p in per),
                            "device_per_turn_s": sum(p["device_per_turn_s"] * p["requests_in_window"]
                                                     for p in per) / nreq,
                            "W_per_turn_s": sum(p["W_per_turn_s"] * p["requests_in_window"]
                                                for p in per) / nreq,
                            "per_rep_device_per_turn_s": [p["device_per_turn_s"] for p in per]}
            if "v11" in preds:
                per = [f.result() for f in futs[(n, cfg)]]
                h = defaultdict(float)
                for p in per:
                    for k, v in p["h"].items():
                        h[int(k)] += v / len(per)
                e["v11"] = {"reuse_rate": statistics.mean(p["reuse_rate"] for p in per),
                            "device_per_turn_s": statistics.mean(p["device_per_turn_s"] for p in per),
                            "padding": statistics.mean(p["padding"] for p in per),
                            "W_per_turn_s": statistics.mean(p["W_per_turn_s"] for p in per),
                            "mean_running": statistics.mean(p["mean_running"] for p in per),
                            "h": dict(sorted(h.items())),
                            "per_plan": [{k: p[k] for k in ("reuse_rate", "device_per_turn_s",
                                                            "mean_running", "gap_law")} for p in per]}
            out["cells"].setdefault(str(n), {})[cfg] = e
            print(n, cfg, {p: round(e[p]["reuse_rate"], 3) for p in preds if p in e}, flush=True)
    for n, cells_n in out["cells"].items():
        for p in preds:
            base = cells_n["BASE"][p]["device_per_turn_s"] if "BASE" in cells_n else None
            order = sorted(cells_n, key=lambda c: cells_n[c][p]["device_per_turn_s"])
            for c, e in cells_n.items():
                if base:
                    e[p]["ratio_to_base"] = e[p]["device_per_turn_s"] / base
                e[p]["rank"] = order.index(c) + 1
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
