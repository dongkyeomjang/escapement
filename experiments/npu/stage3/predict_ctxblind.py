#!/usr/bin/env python3
"""Predictions of the context-cost simulator blind cells N = 15, 18
(directive 11 work B, TASK101, CTXBLIND_PREREG.md).

Predictors per (N, configuration):

* ``sim_ctx_op`` (1, main) -- the step simulator (v2 descriptor, observed
  semantics) whose time advances with the context-length decode cost
  ``f(b) + beta n + c sum_ctx`` (TASK97 BASE/TUNED, TASK100 BATCHONLY;
  ``CTXCOST_BLIND.json``) and TASK92's operational exclusive-prefill cost
  (``OPCOST_SIM.json``); device time per turn priced with the original cost
  model, as channel A' prices the measurement.
* ``sim_ctx`` -- the same decode cost with the original prefill (reported
  only; the other candidate for (1), not judged).
* ``sim`` (2) -- original costs (= TASK93 predictor (2)).
* ``v1`` (3, reference) -- ``mt_predict.analytic``; out of scope when N > the
  running ceiling.

Inputs: descriptor constants, the two cost files and plan files. Nothing
measured in a multi-turn run is read.
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
import predict_simblind as S  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
NS = (15, 18)
CFGS = ("BASE", "BATCHONLY", "TUNED")
VARIANTS = ("sim_ctx_op", "sim_ctx", "sim")


def load_plans(n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / "INDEX_CTX.json").read_text())
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])]


class CtxCost:
    """Picklable ``(bucket, running, sum_ctx) -> s``."""

    def __init__(self, p: dict):
        self.f = {int(b): v for b, v in p["f_s_by_bucket"].items()}
        self.beta = p["beta_s"]
        self.c = p["c_s_per_token"]

    def __call__(self, b: int, n: int, ctx: int) -> float:
        return self.f[b] + self.beta * n + self.c * ctx


def run_one(args):
    variant, n, cfg, rep, opcost, ctxcost = args
    grid, batch = P.CONFIGS[cfg]
    plan = load_plans(n)[rep]
    d_time = (S.op_descriptor(grid, batch, opcost["artifacts"][cfg]) if variant == "sim_ctx_op"
              else Q.descriptor_v2(grid, batch))
    fn = CtxCost(ctxcost["artifacts"][cfg]) if variant in ("sim_ctx_op", "sim_ctx") else None
    d_price = Q.descriptor_v2(grid, batch)
    pm = d_price.prefill.cost
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(d_time, sessions, SimConfig(max_running_requests=batch, session_start_s=start, successor=succ,
                                               semantics="descriptor", decode_cost_fn=fn))
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=120.0)
    w0 = rule.warmup_end([(slot_of[r.session_index], r.finish_s) for r in res.requests], plan.n_slots)
    w1 = w0 + 120.0
    reqs = [r for r in res.requests if w0 <= r.arrival_s < w1]
    later = [r for r in reqs if r.turn > 0]
    dec = [s for s in res.decode_steps if w0 <= s.start_s < w1]
    pre = [s for s in res.prefill_steps if w0 <= s.start_s < w1]
    h: dict[int, float] = defaultdict(float)
    for s in dec:
        h[s.running] += 1
    pre_price = [pm.prefill_s(s.computed_tokens) for s in pre]
    n_req = len(reqs)
    return {"reuse": (sum(1 for r in later if r.cached_tokens > 0), len(later)), "h_counts": dict(h),
            "padding": sum(s.bucket - s.running for s in dec) / sum(s.bucket for s in dec),
            "device_per_turn_s": (sum(d_price.step_time_s(s.running) for s in dec) + sum(pre_price)) / n_req,
            "W_per_turn_s": sum(p * s.running for p, s in zip(pre_price, pre)) / n_req,
            "sim_time_device_per_turn_s": (sum(s.duration_s for s in dec) + sum(s.duration_s for s in pre)) / n_req,
            "mean_wait_s": statistics.mean(r.admit_s - r.arrival_s for r in reqs) if reqs else 0.0,
            "requests_in_window": n_req}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctxcost", type=Path, default=PLAN_DIR / "CTXCOST_BLIND.json")
    ap.add_argument("--opcost", type=Path, default=PLAN_DIR / "OPCOST_SIM.json")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    opcost = json.loads(a.opcost.read_text())
    ctxcost = json.loads(a.ctxcost.read_text())
    jobs = {(v, n, cfg): [(v, n, cfg, r, opcost, ctxcost) for r in range(len(load_plans(n)))]
            for v in VARIANTS for n in NS for cfg in CFGS}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {k: [ex.submit(run_one, j) for j in v] for k, v in jobs.items()}
        res = {k: S.pool([f.result() for f in v]) for k, v in futs.items()}
    out: dict = {"main": "sim_ctx_op", "ctxcost_sha256": ctxcost.get("source_sha256"),
                 "opcost_sha256": opcost.get("source_sha256"), "cells": {}}
    for n in NS:
        plans = load_plans(n)
        for cfg in CFGS:
            grid, batch = P.CONFIGS[cfg]
            e: dict = {"grid": list(grid), "batch": batch}
            for v in VARIANTS:
                e[v] = res[(v, n, cfg)]
            e["v1"] = P.analytic(n, tuple(grid), batch, P.plan_stats(plans))
            e["v1"]["in_scope"] = n <= batch
            out["cells"].setdefault(str(n), {})[cfg] = e
            print(n, cfg, {p: round(e[p]["reuse_rate"], 3) for p in VARIANTS + ("v1",)},
                  {p: round(e[p]["device_per_turn_s"] * 1e3, 1) for p in VARIANTS + ("v1",)}, flush=True)
    for cells_n in out["cells"].values():
        for p in VARIANTS + ("v1",):
            base = cells_n["BASE"][p]["device_per_turn_s"]
            order = sorted(cells_n, key=lambda c: cells_n[c][p]["device_per_turn_s"])
            for c, e in cells_n.items():
                e[p]["ratio_to_base"] = e[p]["device_per_turn_s"] / base
                e[p]["rank"] = order.index(c) + 1
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
