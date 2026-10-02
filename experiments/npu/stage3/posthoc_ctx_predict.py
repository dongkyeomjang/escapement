#!/usr/bin/env python3
"""POST-HOC re-prediction with a context-length decode cost (TASK98,
directive 10 work B). The cells were already observed (TASK82 N = 12,
TASK87 N = 14/16, TASK95 N = 13/17/20): nothing here is a verdict and the
results go to the results index as ``post_hoc``.

Variants (time progression; device time per turn is always priced with the
original cost model, as channel A' prices the measurement):

* ``sim``        -- original costs (TASK13 decode, TASK22 prefill);
* ``sim_op``     -- TASK92 operational costs (``OPCOST_SIM.json``);
* ``sim_ctx``    -- decode step = TASK97 context-length cost
  (``CTXCOST_SIM.json``: per artifact ``t = f(b) + beta n + c sum_ctx``),
  prefill original;
* ``sim_ctx_op`` -- the same decode cost, TASK92 operational prefill.

Observed values are read only to report errors next to the predictions.
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
import predict_simblind as S  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
REPO = HERE.parents[2]
S3 = REPO / "results/npu/stage3"
CELLS = {12: ("INDEX.json", "TASK82"), 14: ("INDEX_HI.json", "TASK87"), 16: ("INDEX_HI.json", "TASK87"),
         13: ("INDEX_SIM.json", "TASK95"), 17: ("INDEX_SIM.json", "TASK95"), 20: ("INDEX_SIM.json", "TASK95")}
CFGS = ("BASE", "BATCHONLY", "TUNED")
VARIANTS = ("sim", "sim_op", "sim_ctx", "sim_ctx_op")


def load_plans(index: str, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / index).read_text())
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])][:5]


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
    plan = load_plans(CELLS[n][0], n)[rep]
    d_time = (S.op_descriptor(grid, batch, opcost["artifacts"][cfg]) if variant in ("sim_op", "sim_ctx_op")
              else Q.descriptor_v2(grid, batch))
    fn = CtxCost(ctxcost["artifacts"][cfg]) if variant.startswith("sim_ctx") else None
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
    price = (sum(d_price.step_time_s(s.running) for s in dec) + sum(pm.prefill_s(s.computed_tokens) for s in pre))
    return {"reuse": (sum(1 for r in later if r.cached_tokens > 0), len(later)), "h_counts": dict(h),
            "device_per_turn_s": price / len(reqs), "requests_in_window": len(reqs),
            "padding": sum(s.bucket - s.running for s in dec) / sum(s.bucket for s in dec),
            "W_per_turn_s": 0.0, "sim_time_device_per_turn_s": 0.0,
            "mean_wait_s": statistics.mean(r.admit_s - r.arrival_s for r in reqs)}


def observed() -> dict:
    out = {}
    mv = json.loads((S3 / "20260930-main/main_verdict.json").read_text())
    for cfg in CFGS:
        c = mv["cells"].get(f"{cfg}.n12")
        n12 = mv["n12"][cfg]
        out[f"{cfg}.n12"] = {"reuse": c["reuse_obs"] if c else n12.get("reuse_obs"),
                             "ratio": n12["ratio"]["m"] if "ratio" in n12 else None}
    for f, key in (("20261001-hiload/hiload_verdict.json", "hi"), ("20261002-simblind/simblind_verdict.json", "sim")):
        v = json.loads((S3 / f).read_text())
        for k, c in v["cells"].items():
            out[k] = {"reuse": c["reuse_obs"], "ratio": c["ratio"]["m"] if "ratio" in c else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctxcost", type=Path, default=PLAN_DIR / "CTXCOST_SIM.json")
    ap.add_argument("--opcost", type=Path, default=PLAN_DIR / "OPCOST_SIM.json")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    opcost = json.loads(a.opcost.read_text())
    ctxcost = json.loads(a.ctxcost.read_text())
    jobs = {(v, n, cfg): [(v, n, cfg, r, opcost, ctxcost) for r in range(5)]
            for v in VARIANTS for n in CELLS for cfg in CFGS}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {k: [ex.submit(run_one, j) for j in v] for k, v in jobs.items()}
        res = {k: S.pool([f.result() for f in v]) for k, v in futs.items()}
    obs = observed()
    cells = {}
    for n, (_, task) in CELLS.items():
        for cfg in CFGS:
            e = {"source": task, "obs": obs.get(f"{cfg}.n{n}")}
            for v in VARIANTS:
                p = res[(v, n, cfg)]
                base = res[(v, n, "BASE")]["device_per_turn_s"]
                e[v] = {"reuse": p["reuse_rate"], "ratio": p["device_per_turn_s"] / base,
                        "device_per_turn_s": p["device_per_turn_s"], "mean_running": p["mean_running"],
                        "mean_wait_s": p["mean_wait_s"], "h": p["h"]}
            cells[f"{cfg}.n{n}"] = e
    summary = {}
    for name, ns in (("finding4_N12_14_16", (12, 14, 16)), ("TASK87_N14_16", (14, 16)), ("TASK95_N13_17_20", (13, 17, 20))):
        rc = [f"{c}.n{n}" for n in ns for c in ("BATCHONLY", "TUNED")]
        uc = [f"{c}.n{n}" for n in ns for c in CFGS if not (c == "BASE" and n == 20)]
        summary[name] = {v: {"ratio_sum_abs_err": sum(abs(cells[k][v]["ratio"] - cells[k]["obs"]["ratio"]) for k in rc),
                             "ratio_mean_signed_err": statistics.mean(cells[k][v]["ratio"] - cells[k]["obs"]["ratio"] for k in rc),
                             "reuse_MAE": statistics.mean(abs(cells[k][v]["reuse"] - cells[k]["obs"]["reuse"]) for k in uc)}
                         for v in VARIANTS}
    out = {"post_hoc": True, "ctxcost_sha256": ctxcost.get("source_sha256"), "cells": cells, "summary": summary}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    for k, e in cells.items():
        print(k, "obs", e["obs"], {v: (round(e[v]["reuse"], 3), round(e[v]["ratio"], 4)) for v in VARIANTS})
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
