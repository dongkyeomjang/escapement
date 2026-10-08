#!/usr/bin/env python3
"""G-10 C post-hoc diagnosis: timing input. Per lifecycle, observed host wall
per call over the window steps (last - first [GSTEP] t / eval requests) vs
the frozen simulator's simwall_per_turn_s; per step type, DIRECT vs price
(RECON lo) per step. Not a preregistered judgment.

usage: posthoc_timing_c.py --run-dir <abs> --posthoc <posthoc_f32.json> --out <abs json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "multiturn"))
import exec_measure as X  # noqa: E402
import gpu_mt_measure as M  # noqa: E402
import g10_common as G  # noqa: E402

PRED = HERE / "plans_c" / "PREDICTIONS_C.json"
TOOLS = ("SHORT_TOOL", "LONG_TOOL")
CFGS = ("GPU_LONG_BASE", "GPU_LONG_KV")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--posthoc", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    P = json.loads(PRED.read_text())["cells"]["24"]
    cost = json.loads(a.posthoc.read_text())["judge_output"]["cost"]
    out: dict = {"status": "POST-HOC DIAGNOSIS (not preregistered)", "cells": {}}
    for t in TOOLS:
        for c in CFGS:
            rows = []
            for r in range(5):
                run = a.run_dir / f"n24.{t}.{c}.r{r}"
                steps, n, _ = X.window_steps(run)
                m = M.lifecycle_metrics(run)
                q = G.admission_delay(run)
                pl, ph = P[t]["lo"][c]["per_rep"][r], P[t]["hi"][c]["per_rep"][r]
                wall = (steps[-1][0]["t"] - steps[0][0]["t"]) / n
                rows.append({"rep": r, "eval_requests": n, "pred_requests": [pl["requests_in_window"],
                                                                             ph["requests_in_window"]],
                             "wall_per_call_s": wall,
                             "sim_wall_per_call_s": [pl["simwall_per_turn_s"], ph["simwall_per_turn_s"]],
                             "wall_ratio_lo": wall / pl["simwall_per_turn_s"],
                             "reuse_obs": m["reuse"][0] / m["reuse"][1],
                             "reuse_pred": [pl["reuse_rate"], ph["reuse_rate"]],
                             "admission_delay_obs_s": q["mean_s"],
                             "queue_wait_pred_s": [pl["queue_wait_mean_s"], ph["queue_wait_mean_s"]]})
            agg: dict = {}
            for row in cost[t]["rows"]:
                for ty, b in row["abs"][c]["by_type"].items():
                    x = agg.setdefault(ty, {"steps": 0, "direct_s": 0.0, "recon_lo_s": 0.0})
                    x["steps"] += b["steps"]
                    x["direct_s"] += b["direct_s"]
                    x["recon_lo_s"] += b["recon_lo_s"]
            for x in agg.values():
                x["direct_ms_per_step"] = x["direct_s"] / x["steps"] * 1e3
                x["price_lo_ms_per_step"] = x["recon_lo_s"] / x["steps"] * 1e3
            out["cells"][f"{t}/{c}"] = {"rows": rows, "wall_ratio_lo_median": statistics.median(
                x["wall_ratio_lo"] for x in rows), "by_type": agg}
            print(t, c, round(out["cells"][f"{t}/{c}"]["wall_ratio_lo_median"], 3),
                  {k: (v["steps"], round(v["direct_ms_per_step"], 2), round(v["price_lo_ms_per_step"], 2))
                   for k, v in agg.items()})
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
