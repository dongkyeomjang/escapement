#!/usr/bin/env python3
"""Model v1.1 on the declared development set (TASK82 N = 12) -- no verdict.

For each configuration: v1 (as preregistered, ``mt_predict.analytic``) and
v1.1 variants -- gap phases K in {1, 2, 3}, statistics pooled over the five
plans or computed per plan and averaged. Compared with the observed cell
values of TASK82 (reuse, BASE ratio, h TVD). Development-set numbers only.
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

import mt_measure as M  # noqa: E402
import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
from continuum.model import survival_v11 as V  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402

N = 12
VERDICT = HERE.parents[2] / "results/npu/stage3/20260930-main/main_verdict.json"


def plans_of(n: int):
    idx = json.loads((HERE / "plans/main/INDEX.json").read_text())
    return [MultiTurnPlan.from_json(json.loads((HERE / f"plans/main/{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])]


ORDER = "admission"


def job(args):
    variant, cfg, k = args
    grid, batch = P.CONFIGS[cfg]
    plans = plans_of(N)
    if variant == "v1":
        return variant, cfg, k, P.analytic(N, grid, batch, P.plan_stats(plans))
    if variant == "pooled":
        law = V.fit_gap_law(Q.plan_gaps(plans), k)
        return variant, cfg, k, Q.analytic_v11(N, grid, batch, P.plan_stats(plans), law,
                                               completion_order=ORDER)
    per = [Q.analytic_v11(N, grid, batch, P.plan_stats([pl]), V.fit_gap_law(Q.plan_gaps([pl]), k),
                          completion_order=ORDER) for pl in plans]
    keys = ("reuse_rate", "device_per_turn_s", "padding", "mean_running")
    out = {kk: statistics.mean(p[kk] for p in per) for kk in keys}
    hs = {}
    for p in per:
        for n_, v in p["h"].items():
            hs[n_] = hs.get(n_, 0.0) + v / len(per)
    out["h"] = hs
    out["per_plan_reuse"] = [p["reuse_rate"] for p in per]
    out["per_plan_device"] = [p["device_per_turn_s"] for p in per]
    return variant, cfg, k, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--ks", default="1,2,3")
    ap.add_argument("--order", default="admission", choices=("random", "admission"))
    a = ap.parse_args()
    global ORDER
    ORDER = a.order
    ks = [int(x) for x in a.ks.split(",")]
    jobs = [("v1", c, 0) for c in P.CONFIGS] + [(v, c, k) for v in ("pooled", "per_plan")
                                                for k in ks for c in P.CONFIGS]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 24)) as ex:
        res = list(ex.map(job, jobs))
    ver = json.loads(VERDICT.read_text())
    obs = {}
    for cfg in P.CONFIGS:
        c = ver["cells"][f"{cfg}.n{N}"]
        obs[cfg] = {"reuse": c["reuse_obs"], "h": {int(k): v for k, v in c["h_obs"].items()},
                    "a_prime_mean_s": c["a_prime_mean_s"],
                    "ratio_m": c["ratio"]["m"] if "ratio" in c else None}
    table = {}
    for variant, cfg, k, r in res:
        key = f"{variant}" + (f"_K{k}" if k else "")
        table.setdefault(key, {})[cfg] = {
            "reuse": r["reuse_rate"], "device_ms": r["device_per_turn_s"] * 1000,
            "h_tvd": M.tvd(obs[cfg]["h"], {int(x): y for x, y in r["h"].items()}),
            **({"per_plan_reuse": r["per_plan_reuse"]} if "per_plan_reuse" in r else {})}
    for key, cells in table.items():
        base = cells["BASE"]["device_ms"]
        for cfg, c in cells.items():
            c["ratio"] = c["device_ms"] / base
        cells["reuse_mae"] = statistics.mean(abs(cells[c]["reuse"] - obs[c]["reuse"]) for c in P.CONFIGS)
        cells["ratio_abs_err_sum"] = sum(abs(cells[c]["ratio"] - obs[c]["ratio_m"])
                                         for c in ("BATCHONLY", "TUNED"))
    out = {"observed": {c: {k: v for k, v in o.items() if k != "h"} for c, o in obs.items()},
           "predictions": table}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print("observed", {c: (round(o["reuse"], 3), o["ratio_m"] and round(o["ratio_m"], 3)) for c, o in obs.items()})
    for key, cells in table.items():
        print(key, {c: (round(cells[c]["reuse"], 3), round(cells[c]["ratio"], 3), round(cells[c]["h_tvd"], 3))
                    for c in P.CONFIGS},
              "reuseMAE", round(cells["reuse_mae"], 4), "ratioErr", round(cells["ratio_abs_err_sum"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
