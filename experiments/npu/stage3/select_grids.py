#!/usr/bin/env python3
"""Blind per-N grid selection for the multi-turn experiment (directive 04 §4).

The grid is chosen from the *predicted* running-count histogram, never from a
measured multi-turn one, so the later measurement of that grid is a blind test
of model-based configuration selection.

For each N in 6, 8, 10, 12, three plans are generated with the main
experiment's rule but their own seeds (``20261200 + 10*N + r``; the pilot and
main experiment use other ranges). Two paths, both starting from TUNED and
iterating grid -> predicted h -> DP grid (batch_size 16, at most 6 widths)
until a fixed point:

* analytic (primary): B2 + v1 + B3 (``mt_predict.analytic``);
* simulator (secondary): default-semantics simulator, evaluation window only.

The analytic path's grid is the compile candidate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_plan as MP  # noqa: E402
import mt_predict as P  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402

TUNED = P.CONFIGS["TUNED"][0]
SEED_BASE = 20261200


def plans_for(n: int, reps: int = 3) -> list[MultiTurnPlan]:
    out = []
    for r in range(reps):
        seed = SEED_BASE + 10 * n + r
        pid = f"gridsel-n{n}-r{r}"
        provisional = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=6.0)
        st = P.plan_stats([provisional])
        cyc = P.analytic(n, TUNED, 16, st)["cycle_s"]
        out.append(MP.build(n=n, seed=seed, plan_id=pid, cycle_s=round(cyc, 3)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default="6,8,10,12")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    result = {"seed_base": SEED_BASE, "tuned": list(TUNED), "cells": {}}
    for n in (int(x) for x in a.ns.split(",")):
        plans = plans_for(n)
        st = P.plan_stats(plans)

        def h_analytic(grid, st=st, n=n):
            return P.analytic(n, grid, 16, st)["h"]

        def h_sim(grid, plans=plans):
            acc = defaultdict(float)
            for pl in plans:
                for k, v in P.simulate_plan(pl, grid, 16)["h_counts"].items():
                    acc[k] += v
            return dict(acc)

        chain_a, status_a = P.best_response_chain(h_analytic, TUNED)
        chain_s, status_s = P.best_response_chain(h_sim, TUNED)
        ga, gs = chain_a[-1], chain_s[-1]
        fixed = P.G.interpolated_fixed_costs(P.D.step_cost_model.fixed_s_by_bucket, range(1, 17))

        def rel(grid, h):
            return P.G.grid_fixed_cost(grid, h, fixed)

        ha, hs = h_analytic(ga), h_sim(gs)
        result["cells"][str(n)] = {
            "plans": [{"plan_id": p.plan_id, "seed": p.base_seed, "sha256": p.sha256(),
                       "cycle_s": p.spec["cycle_s"]} for p in plans],
            "analytic": {"chain": [list(g) for g in chain_a], "status": status_a,
                         "grid": list(ga), "equals_tuned": ga == TUNED,
                         "h_at_grid": {str(k): v for k, v in sorted(ha.items())},
                         "gain_vs_tuned_on_own_h": (rel(TUNED, ha) - rel(ga, ha)) / rel(TUNED, ha)},
            "simulator": {"chain": [list(g) for g in chain_s], "status": status_s,
                          "grid": list(gs), "equals_tuned": gs == TUNED,
                          "h_at_grid": {str(k): v for k, v in sorted(hs.items())},
                          "gain_vs_tuned_on_own_h": (rel(TUNED, hs) - rel(gs, hs)) / rel(TUNED, hs)},
            "paths_agree": ga == gs,
        }
        print(n, "analytic", ga, status_a, "| sim", gs, status_s)
    compile_list = [n for n, c in result["cells"].items() if not c["analytic"]["equals_tuned"]]
    result["compile_candidates"] = {n: result["cells"][n]["analytic"]["grid"] for n in compile_list}
    distinct = sorted({tuple(g) for g in result["compile_candidates"].values()})
    result["distinct_new_grids"] = [list(g) for g in distinct]
    result["within_limit_3"] = len(distinct) <= 3
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print("new grids:", distinct, "within limit:", len(distinct) <= 3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
