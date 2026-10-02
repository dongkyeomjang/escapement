#!/usr/bin/env python3
"""Pre-freeze check of the model v1.2 candidate (directive 07 §5.3, TASK90).

Development set: TASK82 N = 12 and TASK87 N = 14, 16 (all observed). For every
cell, the bias of each predictor against the observation -- reuse
(prediction - observed) and cost ratio to BASE (prediction - m) -- and whether
it exceeds half the confirmatory tolerance (reuse 0.05, ratio 0.015).

Predictors: v1 (TASK80 procedure), v1.1 as frozen (admission order), and the
v1.2 candidate (v1.1 chain with the plan-derived pairwise completion order
``rho``; B2 unchanged -- the TASK90 diagnosis found no plan-derived Markov
correction). The simulator's bias is listed for reference.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import b2_diag as B  # noqa: E402
import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
from continuum.model import survival_v11 as V  # noqa: E402

REUSE_HALF, RATIO_HALF = 0.05, 0.015
CFGS = ("BASE", "BATCHONLY", "TUNED")
NS = (12, 14, 16)


def one(args):
    n, cfg, r, variant = args
    grid, batch = P.CONFIGS[cfg]
    pl = B.plans_of(n)[r]
    st = P.plan_stats([pl])
    law = V.fit_gap_law(Q.plan_gaps([pl]), 3)
    if variant == "v11":
        res = Q.analytic_v11(n, grid, batch, st, law, completion_order="admission")
    else:
        rho = V.pairwise_rho([t.generation_tokens - 1 for s in pl.slots for x in s.sessions
                              for t in x.turns])
        res = Q.analytic_v11(n, grid, batch, st, law, completion_order="pairwise", rho=rho)
        res["rho"] = rho
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    jobs = [(n, c, r, v) for n in NS for c in CFGS for r in range(5) for v in ("v11", "v12")]
    with ProcessPoolExecutor(max_workers=60) as ex:
        res = dict(zip(jobs, ex.map(one, jobs)))
        v1 = {(n, c): ex.submit(P.analytic, n, P.CONFIGS[c][0], P.CONFIGS[c][1],
                                P.plan_stats(B.plans_of(n))) for n in NS for c in CFGS}
        v1 = {k: f.result() for k, f in v1.items()}
    import pickle
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with open(a.output.with_suffix(".raw.pkl"), "wb") as fh:   # keep the expensive part
        pickle.dump({"res": res, "v1": v1}, fh)
    pred_sim = {12: json.loads((HERE / "plans/main/PREDICTIONS.json").read_text())["cells"]["12"],
                14: json.loads((HERE / "plans/main/PREDICTIONS_HI.json").read_text())["cells"]["14"],
                16: json.loads((HERE / "plans/main/PREDICTIONS_HI.json").read_text())["cells"]["16"]}
    table = {}
    for n in NS:
        ver = json.loads(B.RUNS[n].read_text())["cells"]
        preds = {}
        for c in CFGS:
            preds[c] = {
                "v1": {"reuse": v1[(n, c)]["reuse_rate"], "device": v1[(n, c)]["device_per_turn_s"]},
                "v11": {"reuse": statistics.mean(res[(n, c, r, "v11")]["reuse_rate"] for r in range(5)),
                        "device": statistics.mean(res[(n, c, r, "v11")]["device_per_turn_s"] for r in range(5))},
                "v12": {"reuse": statistics.mean(res[(n, c, r, "v12")]["reuse_rate"] for r in range(5)),
                        "device": statistics.mean(res[(n, c, r, "v12")]["device_per_turn_s"] for r in range(5)),
                        "rho": [res[(n, c, r, "v12")]["rho"] for r in range(5)]},
                "sim": {"reuse": pred_sim[n][c]["sim_observed" if n == 12 else "sim"]["reuse_rate"],
                        "device": pred_sim[n][c]["sim_observed" if n == 12 else "sim"]["device_per_turn_s"]}}
        for c in CFGS:
            row = {"obs_reuse": ver[f"{c}.n{n}"]["reuse_obs"]}
            if c != "BASE":
                row["obs_ratio"] = ver[f"{c}.n{n}"]["ratio"]["m"]
            for pr in ("v1", "v11", "v12", "sim"):
                e = {"reuse_bias": preds[c][pr]["reuse"] - row["obs_reuse"]}
                if c != "BASE":
                    e["ratio_bias"] = preds[c][pr]["device"] / preds["BASE"][pr]["device"] - row["obs_ratio"]
                e["reuse_bias"] = float(e["reuse_bias"])
                if "ratio_bias" in e:
                    e["ratio_bias"] = float(e["ratio_bias"])
                e["over_half"] = bool(abs(e["reuse_bias"]) > REUSE_HALF
                                      or abs(e.get("ratio_bias", 0.0)) > RATIO_HALF)
                row[pr] = e
            table[f"{c}.n{n}"] = row
    summary = {pr: {"cells_over_half": [k for k, v in table.items() if v[pr]["over_half"]],
                    "reuse_mae": statistics.mean(abs(v[pr]["reuse_bias"]) for v in table.values()),
                    "ratio_sum_abs": sum(abs(v[pr]["ratio_bias"]) for v in table.values()
                                         if "ratio_bias" in v[pr])}
               for pr in ("v1", "v11", "v12", "sim")}
    out = {"table": table, "summary": summary, "half_tolerance": {"reuse": REUSE_HALF, "ratio": RATIO_HALF},
           "freeze_v12": not summary["v12"]["cells_over_half"]}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n")
    for k, v in table.items():
        print(k, round(v["obs_reuse"], 3), {pr: (round(v[pr]["reuse_bias"], 3),
                                                 round(v[pr].get("ratio_bias", 0), 3), v[pr]["over_half"])
                                            for pr in ("v1", "v11", "v12", "sim")})
    print(json.dumps(summary, indent=1))
    print("FREEZE v1.2:", out["freeze_v12"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
