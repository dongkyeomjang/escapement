#!/usr/bin/env python3
"""Development-set diagnosis for model v1.1 (directive 06 work C).

The development set is declared: the N = 12 cells of TASK82 (BASE,
BATCHONLY, TUNED x r0..r4). Nothing from N = 6, 8, 10 is read here. Results
are development-set numbers, not validation (A4 convention).

Per evaluation-window re-arrival R (turn >= 1) with its predecessor T:

* ``obs``      -- R reused (client/server ``cached > 0``);
* ``exact``    -- the reference replay (``FifoReplay``, descriptor semantics)
                  says T survived to R's lookup (a rule check);
* ``f0,a0,d0`` -- logged state at T's allocation;
* ``allocs``   -- other allocations logged between T's and R's allocation;
* ``wait``     -- R's measured queueing estimate: TTFT minus its prefill time;
* v1 variants: ``v1_ss`` (as predicted), ``v1_log`` (logged initial state,
  planned gap), ``v1_log_wait`` (logged state, gap + measured wait).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

import mt_predict as P  # noqa: E402
import model_v0_retro as R  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival_v1 as V1  # noqa: E402
from continuum.model.reference import FifoReplay  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_V2  # noqa: E402

RUN = REPO / "results/npu/stage3/20260930-main"
PLAN_DIR = HERE / "plans" / "main"
N = 12


def cell_params(grid, batch, st):
    """The analytic path's internals at its fixed point (mt_predict.analytic)."""
    desc = P.descriptor(grid, batch)
    p_s = 0.9
    for _ in range(30):
        ep = st["share_first"] * st["p_first_s"] + (1 - st["share_first"]) * (
            p_s * st["p_hit_s"] + (1 - p_s) * st["p_miss_s"])
        w = O.ClosedWorkload(sessions=N, decode_steps_per_request=st["gen_mean"] - 1,
                             think_mean_s=st["think_mean_s"], prefill_mean_s=ep, max_running=batch)
        occ = O.solve_occupancy(w, desc.step_time_s)
        arr = O.arrival_running_distribution(w, desc.step_time_s)
        t_run = desc.step_time_s(max(1, round(occ.mean_running)))
        service = ep + (st["gen_mean"] - 1) * t_run / occ.phi
        lam = occ.throughput_per_s * (N - 1) / N
        new = V1.steady_state_survival(capacity=batch, running_others_pmf=arr, lam=lam,
                                       mu=1.0 / service, s_active=service,
                                       idle_samples=P._compress(st["idle_samples"]))
        if abs(new - p_s) < 1e-7:
            p_s = new
            break
        p_s = 0.5 * (p_s + new)
    return {"desc": desc, "occ": occ, "arr": arr, "t_run": t_run, "service": service,
            "lam": lam, "mu": 1.0 / service, "p_s": p_s, "in_service": occ.in_service}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    idx = json.loads((PLAN_DIR / "INDEX.json").read_text())
    plans = {e["rep"]: MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
             for e in idx if e["n"] == N}
    st = P.plan_stats([plans[r] for r in sorted(plans)])
    pm = RBLN_CA25_V2.prefill.cost
    out = {"cells": {}}
    for cfg, (grid, batch) in P.CONFIGS.items():
        cp = cell_params(grid, batch, st)
        recs = []
        for r in range(5):
            tag = f"{cfg}.n{N}.r{r}"
            rows = [json.loads(l) for l in (RUN / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines()
                    if l.strip()]
            win = json.loads((RUN / "probe" / tag / f"windows.{tag}.json").read_text())
            w0, w1 = win["warmup_end_s"], win["warmup_end_s"] + 120.0
            ev = R.parse_log(RUN / f"server-{tag}.log")
            sid_of = {}
            for e in ev:
                if e[0] == "alloc":
                    sid_of.setdefault(e[1].rsplit("-", 2)[0], e[1])
            sess, joined = {}, {}
            for x in rows:
                sid = sid_of.get(x["request_id"])
                if sid:
                    sess[sid] = x["session"]
                    joined[(x["session"], x["turn"])] = sid
            lookup = {e[1]: e[2] for e in ev if e[0] == "partial"}
            for e in ev:
                if e[0] == "hit":
                    lookup.setdefault(e[1], None)
            ref = [("alloc", e[1]) if e[0] == "alloc" else ("free", e[1]) if e[0] == "free"
                   else ("decode", e[1]) if e[0] == "bucket" else ("skip",) for e in ev]
            rp = FifoReplay.for_descriptor(RBLN_CA25_V2.with_config(grid=grid, max_running=batch,
                                                                    reuse_capacity=batch)).run(
                ref, session_of=lambda k: sess.get(k, k))
            for x in rows:
                if x["turn"] < 1 or not (w0 <= x["sent_s"] < w1):
                    continue
                rid = joined.get((x["session"], x["turn"]))
                t_key = joined.get((x["session"], x["turn"] - 1))
                if rid is None or t_key is None:
                    continue
                cached = x["cached_tokens"]
                if cached is None:
                    cached = 0 if rid not in lookup else (lookup[rid] if lookup[rid] is not None else 1)
                obs = cached > 0
                t_pos, r_pos = rp.lookups[t_key].pos, rp.lookups[rid].pos
                exact = rp.lookups[rid].predicted_hit
                f0, a0, d0 = rp.lookups[t_key].state_at_alloc
                allocs = sum(1 for e in ref[t_pos + 1:r_pos] if e[0] == "alloc")
                prev = [y for y in rows if y["session"] == x["session"] and y["turn"] == x["turn"] - 1][0]
                gap = prev["gap_after_s"]
                ttft = (x["first_token_s"] - x["sent_s"]) if x.get("first_token_s") else None
                wait = max(0.0, ttft - pm.prefill_s(max(x["prompt_tokens"] - cached, 0))) if ttft else 0.0
                s_act = pm.prefill_s(prev["prompt_tokens"] - (prev["cached_tokens"] or 0)) + \
                    (prev["completion_tokens"] - 1) * cp["t_run"] / cp["occ"].phi
                base = dict(capacity=batch, f0=f0, a0=a0, d0=d0, lam=cp["lam"], mu=cp["mu"], s_active=s_act)
                recs.append({
                    "rep": r, "obs": obs, "exact": exact, "f0": f0, "a0": a0, "d0": d0,
                    "allocs": allocs, "gap": gap, "wait": wait, "s_active": s_act,
                    "v1_ss": V1.steady_state_survival(capacity=batch, running_others_pmf=cp["arr"],
                                                      lam=cp["lam"], mu=cp["mu"], s_active=s_act,
                                                      idle_samples=[(gap, 1.0)]),
                    "v1_log": V1.survival_probability_v1(V1.V1Inputs(**base, s_idle=gap)),
                    "v1_log_wait": V1.survival_probability_v1(V1.V1Inputs(**base, s_idle=gap + wait)),
                    "exp_allocs": cp["lam"] * (s_act + gap + wait)})
        agg = {k: statistics.mean(float(z[k]) for z in recs)
               for k in ("obs", "exact", "v1_ss", "v1_log", "v1_log_wait", "allocs", "exp_allocs",
                         "wait", "gap", "f0", "a0", "d0")}
        out["cells"][cfg] = {"n": len(recs), "exact_agree": sum(z["obs"] == z["exact"] for z in recs),
                             "mean": agg, "params": {k: cp[k] for k in ("t_run", "service", "lam", "mu", "p_s")},
                             "mean_running": cp["occ"].mean_running, "records": recs}
        print(cfg, len(recs), "exact agree", out["cells"][cfg]["exact_agree"],
              {k: round(v, 3) for k, v in agg.items()})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
