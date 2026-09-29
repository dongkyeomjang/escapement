#!/usr/bin/env python3
"""Blind predictions for the multi-turn main experiment (directive 04 §6.2).

For every (N, configuration) and three predictors -- ``analytic`` (model v1 +
B2 + B3 + B4), ``sim_default``, ``sim_observed`` (immediate release +
pre-evict) -- predict: reuse rate of turn >= 1 requests in the evaluation
window, step-weighted h(n) and padding ratio, decode / prefill / total device
time per turn (channel A' definition), ratio to BASE, rank within N, and the
prefill interference W per turn.

Inputs: descriptor constants measured up to TASK72 and the plan files in
``plans/main``. Nothing measured in the pilot is read.
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


def load_plans(plan_dir: Path, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((plan_dir / "INDEX.json").read_text())
    out = []
    for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"]):
        out.append(MultiTurnPlan.from_json(json.loads((plan_dir / f"{e['plan_id']}.json").read_text())))
    return out


def configs_for(n: int, dp: dict) -> dict[str, tuple[tuple[int, ...], int]]:
    c = dict(P.CONFIGS)
    g = dp.get(str(n))
    if g is not None:
        c["DP"] = (tuple(g), 16)
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-dir", type=Path, default=HERE / "plans" / "main")
    ap.add_argument("--dp-grids", type=Path, required=True,
                    help="JSON {N: grid} of the compiled per-N DP grids")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    dp = json.loads(a.dp_grids.read_text())
    out = {"cells": {}}
    for n in (6, 8, 10, 12):
        plans = load_plans(a.plan_dir, n)
        st = P.plan_stats(plans)
        cfgs = configs_for(n, dp)
        cell = {}
        for name, (grid, batch) in cfgs.items():
            an = P.analytic(n, grid, batch, st)
            entry = {"grid": list(grid), "batch": batch, "analytic": an}
            for sem in ("default", "observed"):
                per = [P.simulate_plan(pl, grid, batch, semantics=sem) for pl in plans]
                hits = sum(p["reuse"][0] for p in per)
                tot = sum(p["reuse"][1] for p in per)
                nreq = sum(p["requests_in_window"] for p in per)
                h = defaultdict(float)
                for p in per:
                    for k, v in p["h_counts"].items():
                        h[k] += v
                ht = sum(h.values())
                entry[f"sim_{sem}"] = {
                    "reuse_rate": hits / tot if tot else None, "reuse": [hits, tot],
                    "h": {k: v / ht for k, v in sorted(h.items())},
                    "padding": sum(p["padding"] * 1 for p in per) / len(per),
                    "decode_per_turn_s": sum(p["decode_per_turn_s"] * p["requests_in_window"] for p in per) / nreq,
                    "prefill_per_turn_s": sum(p["prefill_per_turn_s"] * p["requests_in_window"] for p in per) / nreq,
                    "device_per_turn_s": sum(p["device_per_turn_s"] * p["requests_in_window"] for p in per) / nreq,
                    "W_per_turn_s": sum(p["W_per_turn_s"] * p["requests_in_window"] for p in per) / nreq,
                    "per_rep_device_per_turn_s": [p["device_per_turn_s"] for p in per],
                    "requests_in_window": nreq}
            cell[name] = entry
        for pred in ("analytic", "sim_default", "sim_observed"):
            base = cell["BASE"][pred]["device_per_turn_s"]
            for name in cell:
                cell[name][pred]["ratio_to_base"] = cell[name][pred]["device_per_turn_s"] / base
            order = sorted(cell, key=lambda k: cell[k][pred]["device_per_turn_s"])
            for name in cell:
                cell[name][pred]["rank"] = order.index(name) + 1
        out["cells"][str(n)] = cell
        print(n, {k: {p: round(v[p]["ratio_to_base"], 4) for p in ("analytic", "sim_default", "sim_observed")}
                  for k, v in cell.items()})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
