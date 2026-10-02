#!/usr/bin/env python3
"""Regression (TASK103): the TASK101 main predictor (``sim_ctx_op``) recomputed
through the descriptor path -- the context-length decode cost carried by the
v2 descriptor (``step_cost["decode"]`` = F1 ``f(b) + beta n``,
``context_cost`` = ``c`` per token, unit s, reference 0) instead of
``SimConfig.decode_cost_fn`` -- must equal ``PREDICTIONS_CTX.json`` exactly.

usage: ctx_descriptor_npu.py [--workers 24]
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
S3 = REPO / "experiments/npu/stage3"
sys.path.insert(0, str(S3))

import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
import predict_ctxblind as B  # noqa: E402
import predict_simblind as S  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.substrate import ContextCost, Provenance, StepCostModel  # noqa: E402
from continuum.workload.multiturn import WindowRule, to_sim_inputs  # noqa: E402
from collections import defaultdict  # noqa: E402
import statistics  # noqa: E402

PLAN_DIR = S3 / "plans/main"


def ctx_descriptor(cfg: str, opcost: dict, ctxcost: dict):
    """TASK101 time-progression descriptor: TASK92 operational prefill, F1
    decode, context term."""
    grid, batch = P.CONFIGS[cfg]
    d = S.op_descriptor(grid, batch, opcost["artifacts"][cfg])
    p = ctxcost["artifacts"][cfg]
    f = {int(b): v for b, v in p["f_s_by_bucket"].items()}
    dec = StepCostModel(fixed_s_by_bucket={b: f[b] for b in grid}, marginal_s_per_request=p["beta_s"],
                        intercept_s=0.0)
    prov = dict(d.provenance)
    origin = "TASK100" if cfg == "BATCHONLY" else "TASK97"
    prov["step_cost.decode"] = Provenance("stack", origin, "measured", "F1 f(b) + beta n (CTXCOST_BLIND.json)")
    prov["context_cost"] = Provenance("class", origin, "measured",
                                      "c per context token, F1 (CTXCOST_BLIND.json); form class, value stack")
    return replace(d, step_cost={**d.step_cost, "decode": dec},
                   context_cost=ContextCost(per_token=p["c_s_per_token"], unit="s"), provenance=prov)


def run_one(args):
    n, cfg, rep, opcost, ctxcost = args
    grid, batch = P.CONFIGS[cfg]
    plan = B.load_plans(n)[rep]
    d_time = ctx_descriptor(cfg, opcost, ctxcost)
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
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    opcost = json.loads((PLAN_DIR / "OPCOST_SIM.json").read_text())
    ctxcost = json.loads((PLAN_DIR / "CTXCOST_BLIND.json").read_text())
    pred = json.loads((PLAN_DIR / "PREDICTIONS_CTX.json").read_text())["cells"]
    jobs = {(n, c): [(n, c, r, opcost, ctxcost) for r in range(5)] for n in B.NS for c in B.CFGS}
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {k: [ex.submit(run_one, j) for j in v] for k, v in jobs.items()}
        ours = {k: S.pool([f.result() for f in v]) for k, v in futs.items()}
    diffs = 0
    for (n, c), o in ours.items():
        ref = {k: v for k, v in pred[str(n)][c]["sim_ctx_op"].items() if k not in ("ratio_to_base", "rank")}
        mine = json.loads(json.dumps(o, default=float))
        bad = [k for k in ref if ref[k] != mine.get(k)]
        diffs += len(bad)
        print(n, c, "identical" if not bad else f"differs: {bad}")
    print("NPU DESCRIPTOR PATH", "PASS" if diffs == 0 else "FAIL")
    return 0 if diffs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
