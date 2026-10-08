#!/usr/bin/env python3
"""PRED channel of the 2026-10-08 directive (DX_PREREG.md §3): the current
integrated simulator, frozen before any measurement of this directive.

Simulator = decision 13: one simulator whose decode time advances with the
context-length cost measured at the predicted context lengths (F1
``f(b) + beta n`` in ``step_cost["decode"]`` plus ``context_cost`` c per token,
the TASK103 descriptor path; values CTXCOST_BLIND.json, TASK97 BASE/TUNED,
TASK100 BATCHONLY), original exclusive prefill cost (operational prefill not
adopted, decision 13 item 2), observed descriptor semantics. This is the
``sim_ctx`` combination of TASK101/102 expressed through the descriptor.

DP_N8 (grid 1,2,3,4,6,16) has no context-cost measurement. Rule fixed here,
before measurement, in the manner of TASK98's BATCHONLY rule: f(1), f(4),
f(6), f(16) = TUNED (batch-16 artifact), f(2) = BATCHONLY (batch-16 artifact),
f(3) = linear between this f(2) and f(4); beta, c = mean of the three fits.

Per plan: the simulated lifecycle is windowed exactly as in predict_ctxblind
(WindowRule warm-up, 120 s, steps / requests starting in the window) and
priced with the original cost model (TASK13 decode, TASK22 prefill), as
channel A' prices a measurement. Reuse is pooled from the simulator's own
numerators and denominators. Ratios are per plan (same plan, config / ref) and
their median, matching the paired-ratio median of the observation.

usage: dx_predict.py --output plans/dx/PREDICTIONS_DX.json [--workers 24]
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

import mt_predict_v11 as Q  # noqa: E402
from dx_steps import CONFIGS  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.substrate import ContextCost, Provenance, StepCostModel  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "dx"
CTX_FILE = HERE / "plans" / "main" / "CTXCOST_BLIND.json"
ROLE_CFGS = {"B": ("BASE", "TUNED"), "C": ("BASE", "TUNED"), "E": ("BATCHONLY", "TUNED", "DP_N8")}
ROLE_REF = {"B": "BASE", "C": "BASE", "E": "BATCHONLY"}


def ctx_params(cfg: str, ctx: dict) -> dict:
    art = ctx["artifacts"]
    if cfg != "DP_N8":
        p = art[cfg]
        return {"f": {int(b): v for b, v in p["f_s_by_bucket"].items()}, "beta": p["beta_s"],
                "c": p["c_s_per_token"], "rule": p.get("rule")}
    t = {int(b): v for b, v in art["TUNED"]["f_s_by_bucket"].items()}
    bo = {int(b): v for b, v in art["BATCHONLY"]["f_s_by_bucket"].items()}
    f = {1: t[1], 2: bo[2], 4: t[4], 6: t[6], 16: t[16]}
    f[3] = (f[2] + f[4]) / 2
    fits = [art[c] for c in ("BASE", "BATCHONLY", "TUNED")]
    return {"f": f, "beta": statistics.mean(p["beta_s"] for p in fits),
            "c": statistics.mean(p["c_s_per_token"] for p in fits),
            "rule": "DX rule: f(1,4,6,16) TUNED, f(2) BATCHONLY, f(3) linear 2-4; beta, c mean of 3 fits"}


def time_descriptor(cfg: str, ctx: dict):
    _, grid, batch = CONFIGS[cfg]
    d = Q.descriptor_v2(grid, batch)
    p = ctx_params(cfg, ctx)
    dec = StepCostModel(fixed_s_by_bucket={b: p["f"][b] for b in grid}, marginal_s_per_request=p["beta"],
                        intercept_s=0.0)
    prov = dict(d.provenance)
    prov["step_cost.decode"] = Provenance("stack", "TASK97/TASK100", "measured", f"F1 f(b) + beta n; {p['rule']}")
    prov["context_cost"] = Provenance("class", "TASK97/TASK100", "measured", "c per context token (F1)")
    return replace(d, step_cost={**d.step_cost, "decode": dec},
                   context_cost=ContextCost(per_token=p["c"], unit="s"), provenance=prov)


def load_plan(pid: str) -> MultiTurnPlan:
    return MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{pid}.json").read_text()))


def run_one(args):
    pid, cfg, ctx = args
    _, grid, batch = CONFIGS[cfg]
    plan = load_plan(pid)
    d_time = time_descriptor(cfg, ctx)
    d_price = Q.descriptor_v2(grid, batch)
    pm = d_price.prefill.cost
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(d_time, sessions, SimConfig(max_running_requests=batch, session_start_s=start, successor=succ,
                                               semantics="descriptor"))
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
    n_req = len(reqs)
    dev = sum(d_price.step_time_s(s.running) for s in dec) + sum(pm.prefill_s(s.computed_tokens) for s in pre)
    return {"plan_id": pid, "config": cfg, "reuse": [sum(1 for r in later if r.cached_tokens > 0), len(later)],
            "h_counts": {int(k): v for k, v in sorted(h.items())},
            "device_per_turn_s": dev / n_req, "requests_in_window": n_req,
            "sim_time_per_turn_s": (sum(s.duration_s for s in dec) + sum(s.duration_s for s in pre)) / n_req,
            "mean_wait_s": statistics.mean(r.admit_s - r.arrival_s for r in reqs) if reqs else 0.0,
            "completions_per_s": n_req / 120.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    ctx = json.loads(CTX_FILE.read_text())
    index = json.loads((PLAN_DIR / "INDEX_DX.json").read_text())
    jobs = [(e["plan_id"], cfg, ctx) for e in index if e["role"] in ROLE_CFGS for cfg in ROLE_CFGS[e["role"]]]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        per = list(ex.map(run_one, jobs))
    by = {(p["plan_id"], p["config"]): p for p in per}
    cells: dict = {}
    for e in index:
        if e["role"] not in ROLE_CFGS:
            continue
        key = f"{e['role']}.n{e['n']}" + (f".cap{e['cap_s']}" if e["role"] == "C" else "")
        cells.setdefault(key, {"role": e["role"], "n": e["n"], "cap_s": e["cap_s"], "plans": []})["plans"].append(
            (e["rep"], e["plan_id"]))
    for key, c in cells.items():
        c["plans"].sort()
        ref = ROLE_REF[c["role"]]
        c["configs"] = {}
        for cfg in ROLE_CFGS[c["role"]]:
            rows = [by[(pid, cfg)] for _, pid in c["plans"]]
            hits, tot = sum(r["reuse"][0] for r in rows), sum(r["reuse"][1] for r in rows)
            h: dict = defaultdict(float)
            for r in rows:
                for k, v in r["h_counts"].items():
                    h[k] += v
            ratios = [by[(pid, cfg)]["device_per_turn_s"] / by[(pid, ref)]["device_per_turn_s"]
                      for _, pid in c["plans"]]
            c["configs"][cfg] = {
                "reuse_pooled": hits / tot, "reuse": [hits, tot],
                "h": {k: v / sum(h.values()) for k, v in sorted(h.items())},
                "per_rep_device_per_turn_s": [r["device_per_turn_s"] for r in rows],
                "per_rep_ratio_to_ref": ratios, "ratio_median": statistics.median(ratios),
                "mean_wait_s": statistics.mean(r["mean_wait_s"] for r in rows),
                "completions_per_s": statistics.mean(r["completions_per_s"] for r in rows)}
        c["ref"] = ref
        print(key, {cfg: (round(v["reuse_pooled"], 3), round(v["ratio_median"], 4))
                    for cfg, v in c["configs"].items()}, flush=True)
    out = {"simulator": "integrated simulator, context decode cost (descriptor context_cost) + original prefill, "
                        "descriptor semantics (decision 13)",
           "ctxcost_source_sha256": ctx.get("source_sha256"),
           "dp_n8_rule": ctx_params("DP_N8", ctx), "cells": cells, "per_plan": per}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
