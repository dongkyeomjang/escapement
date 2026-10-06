#!/usr/bin/env python3
"""Boundary effects of the A' cost aggregation (directive 17; post_hoc).
Read-only over existing run logs and committed plans / cost files; nothing is
measured and no input or model is changed.

A' of a lifecycle (mt_measure.lifecycle_metrics): the requests sent in
[w0, w1), their prefill priced with the TASK22 prefill model, plus every
``[BUCKET]`` step between the first and the last of their ALLOC lines priced
with the TASK13 step model, divided by the request count.

Work A -- window length. The same w0, w1 = w0 + L for L in {60, 90, 120} s
(the runner stops sending at w0 + 120 s, so longer windows do not exist in the
logs). Observed: A' per lifecycle and the paired ratio (config / BASE, same
replicate) median, the verdict's lifecycles. Predicted: each set's main
simulator predictor is rerun with the same code path and inputs as the
committed prediction file and re-aggregated per window (steps and requests
with start / arrival in [w0, w1), pooled over plans); at L = 120 the pooled
ratio must equal the file's ``ratio_to_base`` (reproduction check). TASK82's
main predictor is the analytic model, which has no window; its simulator
predictor ``sim_observed`` is used instead.

Work B -- boundary residuals (observed). TASK91 membership: request R is in
every ``[BUCKET]`` line between its ALLOC and FREE. A step's priced cost is
split equally over its ``request_nums`` members. Per lifecycle:
  S (start) = cost share, inside the A' step range, of members sent before w0;
  E (end)   = cost share, after the last window ALLOC, of window members;
  corrected A' = (A' total - S + E) / requests.
Reported as S / total and E / total, and corrected paired ratio - original.

usage: boundary_sensitivity.py --output <json>
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
S3 = REPO / "experiments/npu/stage3"
sys.path.insert(0, str(S3))

import mt_measure as M  # noqa: E402
import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
import predict_simblind as S  # noqa: E402
import predict_ctxblind as B  # noqa: E402
from mt_check import CONFIGS  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

RES = REPO / "results/npu/stage3"
PLANS = S3 / "plans/main"
# set -> run dir, verdict, Ns, plan index, prediction file, predictor, sim mode
SETS = {
    "TASK82": (RES / "20260930-main", "main_verdict.json", (6, 8, 10, 12), "INDEX.json", "PREDICTIONS.json",
               "sim_observed", "observed"),
    "TASK87": (RES / "20261001-hiload", "hiload_verdict.json", (14, 16), "INDEX_HI.json", "PREDICTIONS_HI.json",
               "sim", "descriptor"),
    "TASK95": (RES / "20261002-simblind", "simblind_verdict.json", (13, 17, 20), "INDEX_SIM.json",
               "PREDICTIONS_SIM.json", "sim_op", "op"),
    "TASK102": (RES / "20261002-ctxblind", "ctxblind_verdict.json", (15, 18), "INDEX_CTX.json",
                "PREDICTIONS_CTX.json", "sim_ctx_op", "ctx_op"),
}
CFGS = ("BASE", "BATCHONLY", "TUNED")
WINDOWS = (60.0, 90.0, 120.0)
_FREE = re.compile(r"\[PFX\] \[FREE-REQUEST\] REQUEST=(\S+)")


# -- observed ----------------------------------------------------------------------

def parse(path: Path) -> list[tuple]:
    ev = []
    with path.open(errors="replace") as fh:
        for line in fh:
            m = M._ALLOC.search(line)
            if m:
                ev.append(("alloc", m.group(1)))
                continue
            m = M._HIT.search(line)
            if m:
                ev.append(("hit", m.group(1), int(m.group(2)) * M.D.inner_block_tokens))
                continue
            m = M._PART.search(line)
            if m:
                ev.append(("partial", m.group(1), int(m.group(2))))
                continue
            m = M._BUCKET.search(line)
            if m:
                ev.append(("bucket", int(m.group(1)), int(m.group(2))))
                continue
            m = _FREE.search(line)
            if m:
                ev.append(("free", m.group(1)))
    return ev


def lifecycle(run: Path, tag: str) -> dict:
    cfg = tag.split(".")[0]
    _, grid, batch = CONFIGS[cfg]
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0 = win["warmup_end_s"]
    ev = parse(run / f"server-{tag}.log")
    desc = M.descriptor_for(M.D, tuple(grid), batch)
    sc, pm = desc.step_cost_model, desc.prefill_cost_model
    pos_a, pos_f, lookup = {}, {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            pos_a.setdefault(e[1], i)
        elif e[0] == "free":
            pos_f.setdefault(e[1], i)
        elif e[0] in ("hit", "partial"):
            lookup[e[1]] = e[2]
    sid_of = {}
    for s in pos_a:
        sid_of.setdefault(s.rsplit("-", 2)[0], s)
    cost = [sc.step_time_s(bucket=e[2], actual=e[1]) if e[0] == "bucket" else 0.0 for e in ev]
    # membership: per bucket line, the sent_s of every member
    members = defaultdict(list)
    for r in rows:
        s = sid_of.get(r["request_id"])
        if s is None or s not in pos_f:
            continue
        for i in range(pos_a[s], pos_f[s]):
            if ev[i][0] == "bucket":
                members[i].append(r["sent_s"])
    out = {"tag": tag, "windows": {}}
    for L in WINDOWS:
        w1 = w0 + L
        win_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
        prefill = 0.0
        pos = []
        for r in win_rows:
            sid = sid_of[r["request_id"]]
            pos.append(pos_a[sid])
            cached = r["cached_tokens"] if r["cached_tokens"] is not None else lookup.get(sid, 0)
            prefill += pm.prefill_s(max(r["prompt_tokens"] - cached, 0))
        lo, hi = min(pos), max(pos)
        steps = [i for i in range(lo, hi + 1) if ev[i][0] == "bucket"]
        decode = sum(cost[i] for i in steps)
        total = decode + prefill
        st = en = 0.0
        mismatch = 0
        for i in steps:
            ms = members.get(i, [])
            if len(ms) != ev[i][1]:
                mismatch += 1
            st += cost[i] * sum(1 for t in ms if t < w0) / ev[i][1]
        for i in range(hi + 1, len(ev)):
            if ev[i][0] == "bucket":
                ms = members.get(i, [])
                en += cost[i] * sum(1 for t in ms if w0 <= t < w1) / ev[i][1]
        n = len(win_rows)
        out["windows"][str(int(L))] = {
            "requests": n, "steps": len(steps), "a_prime_per_turn_s": total / n,
            "total_s": total, "start_resid_s": st, "end_resid_s": en,
            "corrected_per_turn_s": (total - st + en) / n, "membership_mismatch_steps": mismatch}
    return out


# -- predicted ---------------------------------------------------------------------

def plans_of(index: str, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLANS / index).read_text())
    return [MultiTurnPlan.from_json(json.loads((PLANS / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])][:5]


def sim_windows(args) -> dict:
    index, n, cfg, rep, mode = args
    grid, batch = P.CONFIGS[cfg]
    plan = plans_of(index, n)[rep]
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    price = None
    if mode == "observed":        # mt_predict.simulate_plan(semantics="observed"): sim step durations
        d = P.descriptor(grid, batch)
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ,
                         release_rule="immediate", dummy_mode="pre_evict")
    elif mode == "descriptor":    # predict_v11.sim_plan: sim step durations
        d = Q.descriptor_v2(grid, batch)
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ, semantics="descriptor")
    else:                         # predict_simblind sim_op / predict_ctxblind sim_ctx_op: priced with v2 costs
        op = json.loads((PLANS / "OPCOST_SIM.json").read_text())
        d = S.op_descriptor(grid, batch, op["artifacts"][cfg])
        fn = None
        if mode == "ctx_op":
            fn = B.CtxCost(json.loads((PLANS / "CTXCOST_BLIND.json").read_text())["artifacts"][cfg])
        cfgk = SimConfig(max_running_requests=batch, session_start_s=start, successor=succ, semantics="descriptor",
                         decode_cost_fn=fn)
        price = Q.descriptor_v2(grid, batch)
    res = simulate(d, sessions, cfgk)
    out = {}
    for L in WINDOWS:
        rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=L)
        w0 = rule.warmup_end([(slot_of[r.session_index], r.finish_s) for r in res.requests], plan.n_slots)
        w1 = w0 + L
        nreq = sum(1 for r in res.requests if w0 <= r.arrival_s < w1)
        dec = [s for s in res.decode_steps if w0 <= s.start_s < w1]
        pre = [s for s in res.prefill_steps if w0 <= s.start_s < w1]
        if price is None:
            dev = sum(s.duration_s for s in dec) + sum(s.duration_s for s in pre)
        else:
            dev = (sum(price.step_time_s(s.running) for s in dec)
                   + sum(price.prefill.cost.prefill_s(s.computed_tokens) for s in pre))
        out[str(int(L))] = (dev, nreq)
    return out


# -- main ----------------------------------------------------------------------------

def med_ratio(lc, cfg, n, task, key, L):
    xs = []
    for r in range(5):
        a, b = lc.get((task, n, cfg, r)), lc.get((task, n, "BASE", r))
        if a and b:
            xs.append(a["windows"][L][key] / b["windows"][L][key])
    return xs


def order_of(vals: dict) -> str:
    return " < ".join(sorted(vals, key=vals.get))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    obs_jobs, sim_jobs, verdicts = {}, {}, {}
    for task, (run, vfile, ns, index, _, _, mode) in SETS.items():
        v = json.loads((run / vfile).read_text())
        verdicts[task] = v
        for n in ns:
            for cfg in CFGS:
                for r in range(5):
                    used = v["selection"][f"{cfg}.n{n}.r{r}"]["used"]
                    if used:
                        obs_jobs[(task, n, cfg, r)] = (run, used)
                    sim_jobs[(task, n, cfg, r)] = (index, n, cfg, r, mode)
    with ProcessPoolExecutor(a.workers) as ex:
        of = {k: ex.submit(lifecycle, *j) for k, j in obs_jobs.items()}
        sf = {k: ex.submit(sim_windows, j) for k, j in sim_jobs.items()}
        lc = {k: f.result() for k, f in of.items()}
        sm = {k: f.result() for k, f in sf.items()}
    cells, groups = [], []
    Ls = [str(int(L)) for L in WINDOWS]
    for task, (run, vfile, ns, index, pfile, pred_name, mode) in SETS.items():
        pfile_cells = json.loads((PLANS / pfile).read_text())["cells"]
        for n in ns:
            pred_dev = {}
            for cfg in CFGS:
                pred_dev[cfg] = {L: sum(sm[(task, n, cfg, r)][L][0] for r in range(5))
                                 / sum(sm[(task, n, cfg, r)][L][1] for r in range(5)) for L in Ls}
            g = {"set": task, "N": n, "obs_order": {}, "pred_order": {}}
            for cfg in CFGS:
                xs = [lc[(task, n, cfg, r)] for r in range(5) if (task, n, cfg, r) in lc]
                row = {"set": task, "N": n, "config": cfg, "replicates": len(xs), "windows": {}}
                for L in Ls:
                    tot = sum(x["windows"][L]["total_s"] for x in xs)
                    w = {"a_prime_mean_s": statistics.mean(x["windows"][L]["a_prime_per_turn_s"] for x in xs),
                         "requests": sum(x["windows"][L]["requests"] for x in xs),
                         "start_resid_share": sum(x["windows"][L]["start_resid_s"] for x in xs) / tot,
                         "end_resid_share": sum(x["windows"][L]["end_resid_s"] for x in xs) / tot,
                         "start_resid_share_range": [min(x["windows"][L]["start_resid_s"] / x["windows"][L]["total_s"]
                                                         for x in xs),
                                                     max(x["windows"][L]["start_resid_s"] / x["windows"][L]["total_s"]
                                                         for x in xs)],
                         "end_resid_share_range": [min(x["windows"][L]["end_resid_s"] / x["windows"][L]["total_s"]
                                                       for x in xs),
                                                   max(x["windows"][L]["end_resid_s"] / x["windows"][L]["total_s"]
                                                       for x in xs)],
                         "membership_mismatch_steps": sum(x["windows"][L]["membership_mismatch_steps"] for x in xs),
                         "steps": sum(x["windows"][L]["steps"] for x in xs),
                         "pred_device_per_turn_s": pred_dev[cfg][L]}
                    if cfg != "BASE":
                        o = med_ratio(lc, cfg, n, task, "a_prime_per_turn_s", L)
                        c = med_ratio(lc, cfg, n, task, "corrected_per_turn_s", L)
                        w["obs_ratio_per_rep"] = o
                        w["obs_ratio_median"] = statistics.median(o)
                        w["corrected_ratio_median"] = statistics.median(c)
                        w["corrected_ratio_per_rep"] = c
                        w["paired_diff_median"] = statistics.median(y - x for x, y in zip(o, c))
                        w["corrected_minus_original"] = statistics.median(c) - statistics.median(o)
                        w["pred_ratio"] = pred_dev[cfg][L] / pred_dev["BASE"][L]
                    row["windows"][L] = w
                if cfg != "BASE":
                    vr = verdicts[task]["cells"][f"{cfg}.n{n}"]["ratio"]
                    row["reproduced_obs_120"] = row["windows"]["120"]["obs_ratio_per_rep"] == vr["per_rep"]
                    row["reproduced_pred_120"] = (row["windows"]["120"]["pred_ratio"]
                                                  == pfile_cells[str(n)][cfg][pred_name]["ratio_to_base"])
                    obs_r = [row["windows"][L]["obs_ratio_median"] for L in Ls]
                    pred_r = [row["windows"][L]["pred_ratio"] for L in Ls]
                    row["obs_span"] = max(obs_r) - min(obs_r)
                    row["pred_span"] = max(pred_r) - min(pred_r)
                cells.append(row)
            for L in Ls:
                obs_v = {"BASE": 1.0}
                pred_v = {"BASE": 1.0}
                for row in cells[-3:]:
                    if row["config"] != "BASE":
                        obs_v[row["config"]] = row["windows"][L]["obs_ratio_median"]
                        pred_v[row["config"]] = row["windows"][L]["pred_ratio"]
                g["obs_order"][L] = order_of(obs_v)
                g["pred_order"][L] = order_of(pred_v)
            g["obs_order_changes"] = len(set(g["obs_order"].values())) > 1
            g["pred_order_changes"] = len(set(g["pred_order"].values())) > 1
            groups.append(g)
            print(task, n, g["obs_order"], g["pred_order"], flush=True)
    for row in cells:
        if row["config"] == "BASE":
            continue
        print(row["set"], row["N"], row["config"], "repro", row["reproduced_obs_120"], row["reproduced_pred_120"],
              {L: (round(row["windows"][L]["obs_ratio_median"], 4), round(row["windows"][L]["pred_ratio"], 4))
               for L in Ls}, "corr-orig@120", round(row["windows"]["120"]["corrected_minus_original"], 4), flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"windows_s": list(WINDOWS), "cells": cells, "groups": groups}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
