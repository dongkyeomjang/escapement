#!/usr/bin/env python3
"""Predictions of the unified-simulator blind cells N = 13, 17, 20 (directive 08
work C, TASK93, SIMBLIND_PREREG.md).

Predictors per (N, configuration):

* ``sim_op`` (1, main) -- the step simulator with the v2 descriptor's observed
  semantics whose *time* advances by the operational step costs of TASK92
  (``OPCOST_SIM.json``: decode ``F[b] + beta n``, exclusive prefill
  ``ceil(c/128)(a + d c)`` per artifact). The device time per turn is *priced*
  with the original cost model (TASK13 decode, TASK22 prefill), as channel A'
  prices the measurement: each simulated decode step at
  ``step_time_s(running)``, each prefill at ``prefill_s(computed)``.
* ``sim`` (2) -- the same simulator with the original costs for both
  (= ``predict_v11.sim_plan``).
* ``v1`` (3, reference) -- ``mt_predict.analytic`` on the cell's plans pooled.
  Labelled ``in_scope`` only when N <= the running ceiling (decision 10.1).

Inputs: descriptor constants, OPCOST_SIM.json and plan files. Nothing measured
in the multi-turn experiment is read; no TASK91 ratio and no TASK82/87
multiplier is an input.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.substrate.descriptor import PrefillCostModel, Provenance, StepCostModel  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
NS = (13, 17, 20)
CFGS = ("BASE", "BATCHONLY", "TUNED")


def load_plans(n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / "INDEX_SIM.json").read_text())
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])]


def op_descriptor(grid, batch, op: dict):
    """The v2 instance at this configuration with TASK92's operational costs."""
    d = Q.descriptor_v2(grid, batch)
    fixed = {int(b): v for b, v in op["decode"]["fixed_s_by_bucket"].items()}
    missing = set(grid) - set(fixed)
    if missing:
        raise ValueError(f"no operational fixed cost for widths {sorted(missing)}")
    dec = StepCostModel(fixed_s_by_bucket={b: fixed[b] for b in grid},
                        marginal_s_per_request=op["decode"]["marginal_s_per_request"], intercept_s=0.0)
    pre = PrefillCostModel(chunk_tokens=128, per_chunk_s=op["prefill"]["per_chunk_s"],
                           drift_s_per_token=op["prefill"]["drift_s_per_token"])
    prov = dict(d.provenance)
    note = "operational controlled-load fit (TASK92, OPCOST_SIM.json); time progression only"
    prov["step_cost.decode"] = Provenance(layer="stack", origin="TASK92", kind="measured", note=note)
    prov["prefill.cost"] = Provenance(layer="stack", origin="TASK92", kind="measured", note=note)
    return replace(d, step_cost={**d.step_cost, "decode": dec}, prefill=replace(d.prefill, cost=pre),
                   provenance=prov)


def sim_plan(plan: MultiTurnPlan, grid, batch, d_time, eval_s: float = 120.0) -> dict:
    """Simulate with ``d_time``; price device time with the original costs."""
    d_price = Q.descriptor_v2(grid, batch)
    pm = d_price.prefill.cost
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(d_time, sessions,
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
    dec_price = [d_price.step_time_s(s.running) for s in dec]
    pre_price = [pm.prefill_s(s.computed_tokens) for s in pre]
    n_req = len(reqs)
    waits = [r.admit_s - r.arrival_s for r in reqs]
    return {"reuse": (sum(1 for r in later if r.cached_tokens > 0), len(later)),
            "h_counts": dict(h),
            "padding": sum(s.bucket - s.running for s in dec) / sum(s.bucket for s in dec),
            "device_per_turn_s": (sum(dec_price) + sum(pre_price)) / n_req,
            "W_per_turn_s": sum(p * s.running for p, s in zip(pre_price, pre)) / n_req,
            "sim_time_device_per_turn_s": (sum(s.duration_s for s in dec) + sum(s.duration_s for s in pre)) / n_req,
            "mean_wait_s": statistics.mean(waits) if waits else 0.0,
            "requests_in_window": n_req}


def _job(args):
    n, cfg, rep, which, op = args
    grid, batch = P.CONFIGS[cfg]
    plan = load_plans(n)[rep]
    d = op_descriptor(grid, batch, op) if which == "sim_op" else Q.descriptor_v2(grid, batch)
    return sim_plan(plan, grid, batch, d)


def pool(per: list[dict]) -> dict:
    nreq = sum(p["requests_in_window"] for p in per)
    hits = sum(p["reuse"][0] for p in per)
    tot = sum(p["reuse"][1] for p in per)
    h: dict = defaultdict(float)
    for p in per:
        for k, v in p["h_counts"].items():
            h[k] += v
    ht = sum(h.values())

    def wmean(key):
        return sum(p[key] * p["requests_in_window"] for p in per) / nreq

    return {"reuse_rate": hits / tot, "reuse": [hits, tot],
            "h": {k: v / ht for k, v in sorted(h.items())},
            "mean_running": sum(k * v for k, v in h.items()) / ht,
            "padding": statistics.mean(p["padding"] for p in per),
            "device_per_turn_s": wmean("device_per_turn_s"),
            "W_per_turn_s": wmean("W_per_turn_s"),
            "sim_time_device_per_turn_s": wmean("sim_time_device_per_turn_s"),
            "mean_wait_s": wmean("mean_wait_s"),
            "per_rep_device_per_turn_s": [p["device_per_turn_s"] for p in per],
            "per_rep_reuse": [p["reuse"][0] / p["reuse"][1] for p in per]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--opcost", type=Path, default=PLAN_DIR / "OPCOST_SIM.json")
    ap.add_argument("--ns", default=",".join(map(str, NS)))
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    opcost = json.loads(a.opcost.read_text())
    out: dict = {"opcost_sha256": opcost.get("source_sha256"), "cells": {}}
    ns = [int(x) for x in a.ns.split(",")]
    jobs = {(n, cfg, w): [(n, cfg, r, w, opcost["artifacts"][cfg]) for r in range(len(load_plans(n)))]
            for n in ns for cfg in CFGS for w in ("sim_op", "sim")}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {k: [ex.submit(_job, j) for j in v] for k, v in jobs.items()}
        res = {k: [f.result() for f in v] for k, v in futs.items()}
    for n in ns:
        plans = load_plans(n)
        for cfg in CFGS:
            grid, batch = P.CONFIGS[cfg]
            e: dict = {"grid": list(grid), "batch": batch}
            e["sim_op"] = pool(res[(n, cfg, "sim_op")])
            e["sim"] = pool(res[(n, cfg, "sim")])
            e["v1"] = P.analytic(n, tuple(grid), batch, P.plan_stats(plans))
            e["v1"]["in_scope"] = n <= batch
            out["cells"].setdefault(str(n), {})[cfg] = e
            print(n, cfg, {p: round(e[p]["reuse_rate"], 3) for p in ("sim_op", "sim", "v1")},
                  {p: round(e[p]["device_per_turn_s"] * 1e3, 1) for p in ("sim_op", "sim", "v1")}, flush=True)
    for cells_n in out["cells"].values():
        for p in ("sim_op", "sim", "v1"):
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
