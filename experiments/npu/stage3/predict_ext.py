#!/usr/bin/env python3
"""Blind predictions for the extra N = 8 plans (directive 05 §2.3).

Same three predictors and the same definitions as ``predict_main.py``, for the
TUNED and DP(8) configurations only, over (a) the extra plans r5..r9 and (b)
all ten N = 8 plans r0..r9 pooled -- the population of the DP-vs-TUNED
comparison (§5.4 of the preregistration, revision 2). Nothing measured is read.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402

N = 8


def load(plan_dir: Path, index: str) -> dict[int, MultiTurnPlan]:
    idx = json.loads((plan_dir / index).read_text())
    return {e["rep"]: MultiTurnPlan.from_json(json.loads((plan_dir / f"{e['plan_id']}.json").read_text()))
            for e in idx if e["n"] == N}


def predict(plans: list[MultiTurnPlan], grid, batch) -> dict:
    st = P.plan_stats(plans)
    entry = {"analytic": P.analytic(N, grid, batch, st)}
    for sem in ("default", "observed"):
        per = [P.simulate_plan(pl, grid, batch, semantics=sem) for pl in plans]
        nreq = sum(p["requests_in_window"] for p in per)
        hits = sum(p["reuse"][0] for p in per)
        tot = sum(p["reuse"][1] for p in per)
        h = defaultdict(float)
        for p in per:
            for k, v in p["h_counts"].items():
                h[k] += v
        ht = sum(h.values())
        entry[f"sim_{sem}"] = {
            "reuse_rate": hits / tot if tot else None, "reuse": [hits, tot],
            "h": {k: v / ht for k, v in sorted(h.items())},
            "device_per_turn_s": sum(p["device_per_turn_s"] * p["requests_in_window"] for p in per) / nreq,
            "per_rep_device_per_turn_s": [p["device_per_turn_s"] for p in per],
            "requests_in_window": nreq}
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-dir", type=Path, default=HERE / "plans" / "main")
    ap.add_argument("--dp-grids", type=Path, default=HERE / "plans" / "main" / "DP_GRIDS.json")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    dp = tuple(json.loads(a.dp_grids.read_text())[str(N)])
    cfgs = {"TUNED": P.CONFIGS["TUNED"], "DP": (dp, 16)}
    base = load(a.plan_dir, "INDEX.json")
    ext = load(a.plan_dir, "INDEX_EXT.json")
    pops = {"r5_r9": [ext[r] for r in sorted(ext)],
            "r0_r9": [base[r] for r in sorted(base)] + [ext[r] for r in sorted(ext)]}
    out = {"n": N, "dp_grid": list(dp), "populations": {}}
    for pop, plans in pops.items():
        cell = {name: predict(plans, g, b) for name, (g, b) in cfgs.items()}
        cell["DP_over_TUNED"] = {
            pred: cell["DP"][pred]["device_per_turn_s"] / cell["TUNED"][pred]["device_per_turn_s"]
            for pred in ("analytic", "sim_default", "sim_observed")}
        for sem in ("sim_default", "sim_observed"):
            cell["DP_over_TUNED"][f"{sem}_per_rep"] = [
                d / t for d, t in zip(cell["DP"][sem]["per_rep_device_per_turn_s"],
                                      cell["TUNED"][sem]["per_rep_device_per_turn_s"])]
        out["populations"][pop] = cell
        print(pop, {k: round(v, 4) for k, v in cell["DP_over_TUNED"].items() if not k.endswith("per_rep")})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
