#!/usr/bin/env python3
"""Predicted vs observed waiting-queue length per cell (directive 15 work E).

Predictions: the prediction files committed before each measurement carry no
queue length, so the queue is recomputed from the SAME code and inputs
(plans, descriptors, cost files) -- no input or model is changed. The rerun is
checked against the committed prediction file: every cell's reuse rate must
equal the file's value exactly, otherwise the cell is reported as not
reproduced.

* simulator queue  = per decode step in the evaluation window, the number of
  requests that have arrived but are not yet admitted
  (#{arrival <= t} - #{admit <= t}), averaged over decode steps (step-weighted,
  the observed definition's population);
* analytic queue   = sum_n pi(n) max(0, n - M) from the occupancy distribution of
  the analytic model's final fixed-point iteration (time-stationary; M = batch);
* observed queue   = results/npu/stage3/queue_obs/queue_obs.json (TASK96/105):
  client in-flight - [BUCKET] request_nums per decode step, step-weighted.

Predictor columns per cell set (the set's preregistered predictors):
  TASK82 (PREDICTIONS.json):        analytic (main), sim_observed
  TASK87 (PREDICTIONS_HI.json):     v1 (analytic), sim (v1.1, the main, has no queue)
  TASK95 (PREDICTIONS_SIM.json):    sim_op (main), sim, v1
  TASK102 (PREDICTIONS_CTX.json):   sim_ctx_op (main), sim, v1
GPU cells are not recomputed here: GTASK14 records observed and original sim
LRU queue (same definition: requests sent but not yet looked up, per step).

usage: queue_pred_vs_obs.py --output <json>
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
S3 = REPO / "experiments/npu/stage3"
sys.path.insert(0, str(S3))

import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
import predict_simblind as S  # noqa: E402
import predict_ctxblind as B  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLANS = S3 / "plans/main"
SETS = {
    "TASK82": ("INDEX.json", "PREDICTIONS.json", (6, 8, 10, 12), {"sim_observed": "observed"}, "analytic"),
    "TASK87": ("INDEX_HI.json", "PREDICTIONS_HI.json", (14, 16), {"sim": "descriptor"}, "v1"),
    "TASK95": ("INDEX_SIM.json", "PREDICTIONS_SIM.json", (13, 17, 20), {"sim_op": "op", "sim": "descriptor"}, "v1"),
    "TASK102": ("INDEX_CTX.json", "PREDICTIONS_CTX.json", (15, 18), {"sim_ctx_op": "ctx_op", "sim": "descriptor"}, "v1"),
}
MAIN = {"TASK82": "analytic", "TASK87": "sim", "TASK95": "sim_op", "TASK102": "sim_ctx_op"}
CFGS = ("BASE", "BATCHONLY", "TUNED")


def plans_of(index: str, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLANS / index).read_text())
    return [MultiTurnPlan.from_json(json.loads((PLANS / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])][:5]


def run(args):
    index, n, cfg, rep, mode = args
    grid, batch = P.CONFIGS[cfg]
    plan = plans_of(index, n)[rep]
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    if mode == "observed":                     # mt_predict.simulate_plan(semantics="observed")
        d = P.descriptor(grid, batch)
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ,
                         release_rule="immediate", dummy_mode="pre_evict")
    elif mode == "descriptor":                 # predict_v11 / predict_simblind sim
        d = Q.descriptor_v2(grid, batch)
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ, semantics="descriptor")
    elif mode == "op":                         # predict_simblind sim_op
        op = json.loads((PLANS / "OPCOST_SIM.json").read_text())
        d = S.op_descriptor(grid, batch, op["artifacts"][cfg])
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ, semantics="descriptor")
    elif mode == "ctx_op":                     # predict_ctxblind sim_ctx_op
        op = json.loads((PLANS / "OPCOST_SIM.json").read_text())
        ctx = json.loads((PLANS / "CTXCOST_BLIND.json").read_text())
        d = S.op_descriptor(grid, batch, op["artifacts"][cfg])
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ, semantics="descriptor",
                         decode_cost_fn=B.CtxCost(ctx["artifacts"][cfg]))
    res = simulate(d, sessions, cfgk)
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=120.0)
    w0 = rule.warmup_end([(slot_of[r.session_index], r.finish_s) for r in res.requests], plan.n_slots)
    w1 = w0 + 120.0
    arr = sorted(r.arrival_s for r in res.requests)
    adm = sorted(r.admit_s for r in res.requests)
    steps = [s for s in res.decode_steps if w0 <= s.start_s < w1]
    qsum = sum(bisect_right(arr, s.start_s) - bisect_right(adm, s.start_s) for s in steps)
    later = [r for r in res.requests if w0 <= r.arrival_s < w1 and r.turn > 0]
    return {"steps": len(steps), "qsum": qsum, "hits": sum(1 for r in later if r.cached_tokens > 0),
            "later": len(later)}


def analytic_queue(n: int, cfg: str, plans) -> tuple[float, float, float]:
    grid, batch = P.CONFIGS[cfg]
    captured = {}
    orig = P.O.solve_occupancy

    def spy(w, t, **kw):
        occ = orig(w, t, **kw)
        captured["occ"], captured["w"] = occ, w
        return occ
    P.O.solve_occupancy = spy
    try:
        out = P.analytic(n, tuple(grid), batch, P.plan_stats(plans))
    finally:
        P.O.solve_occupancy = orig
    pi = captured["occ"].in_service
    q = sum(p * max(0, k - batch) for k, p in enumerate(pi))
    pw = sum(p for k, p in enumerate(pi) if k > batch)
    return q, pw, out["reuse_rate"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    obs = json.loads((REPO / "results/npu/stage3/queue_obs/queue_obs.json").read_text())["cells"]
    jobs = {}
    for task, (index, pfile, ns, sims, _) in SETS.items():
        for n in ns:
            for cfg in CFGS:
                for name, mode in sims.items():
                    jobs[(task, n, cfg, name)] = [(index, n, cfg, r, mode) for r in range(5)]
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {k: [ex.submit(run, j) for j in v] for k, v in jobs.items()}
        res = {k: [f.result() for f in v] for k, v in futs.items()}
    cells = []
    for task, (index, pfile, ns, sims, an_name) in SETS.items():
        pred = json.loads((PLANS / pfile).read_text())["cells"]
        for n in ns:
            plans = plans_of(index, n)
            for cfg in CFGS:
                row = {"set": task, "N": n, "config": cfg, "main": MAIN[task],
                       "obs_queue": obs[f"{cfg}.n{n}"]["mean_q"], "obs_p_q_gt0": obs[f"{cfg}.n{n}"]["p_q_gt0"],
                       "pred": {}, "reproduced": {}}
                for name in sims:
                    rs = res[(task, n, cfg, name)]
                    steps = sum(x["steps"] for x in rs)
                    reuse = sum(x["hits"] for x in rs) / sum(x["later"] for x in rs)
                    row["pred"][name] = sum(x["qsum"] for x in rs) / steps
                    row["reproduced"][name] = reuse == pred[str(n)][cfg][name]["reuse_rate"]
                q, pw, reuse = analytic_queue(n, cfg, plans)
                row["pred"][an_name] = q
                row["pred"][an_name + "_p_wait"] = pw
                row["reproduced"][an_name] = reuse == pred[str(n)][cfg][an_name]["reuse_rate"]
                cells.append(row)
                print(task, n, cfg, round(row["obs_queue"], 3),
                      {k: round(v, 3) for k, v in row["pred"].items()}, row["reproduced"], flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"cells": cells}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
