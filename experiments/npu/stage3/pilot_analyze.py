#!/usr/bin/env python3
"""Verdict for the streaming observer-effect pilot (STREAMING_PILOT_PREREG.md)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_measure as M  # noqa: E402

CONFIGS = {"BASE": ((1, 2, 4, 8), 8), "TUNED": ((1, 4, 6, 8, 10, 16), 16)}
WIDTH_CAP = 0.04
BOOT = 10_000
BOOT_SEED = 20261310


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    cells = {}
    for cfg, (grid, batch) in CONFIGS.items():
        for mode in ("stream", "nostream"):
            for r in range(3):
                tag = f"{cfg}.{mode}.r{r}"
                cells[tag] = M.lifecycle_metrics(a.run, tag, grid, batch)
    pairs = []
    for cfg in CONFIGS:
        for r in range(3):
            s, n = cells[f"{cfg}.stream.r{r}"], cells[f"{cfg}.nostream.r{r}"]
            ok = s["valid"] and n["valid"]
            pairs.append({
                "config": cfg, "rep": r, "valid": ok,
                "ratio": s["a_prime_per_turn_s"] / n["a_prime_per_turn_s"] if ok else None,
                "reuse_stream": s["reuse"], "reuse_nostream": n["reuse"],
                "h_tvd": M.tvd({int(k): v for k, v in s["h_counts"].items()},
                               {int(k): v for k, v in n["h_counts"].items()}),
                "throughput_ratio": s["throughput_per_s"] / n["throughput_per_s"]})
    ratios = [p["ratio"] for p in pairs if p["valid"]]
    med = statistics.median(ratios)
    rng = random.Random(BOOT_SEED)
    boots = sorted(statistics.median(rng.choices(ratios, k=len(ratios))) for _ in range(BOOT))
    lo, hi = boots[int(0.025 * BOOT)], boots[int(0.975 * BOOT) - 1]
    verdict = "EQUIVALENT" if (lo <= 1.0 <= hi and hi - lo <= WIDTH_CAP) else "NOT_EQUIVALENT"
    per_cfg = {c: statistics.median(p["ratio"] for p in pairs if p["config"] == c and p["valid"])
               for c in CONFIGS}
    out = {"verdict": verdict, "median_ratio": med, "ci95": [lo, hi], "ci_width": hi - lo,
           "width_cap": WIDTH_CAP, "valid_pairs": len(ratios), "per_config_median": per_cfg,
           "decision": "main experiment streaming" if verdict == "EQUIVALENT"
           else "main experiment non-streaming + streaming auxiliary",
           "pairs": pairs, "cells": cells}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("cells", "pairs")}, indent=2))
    for p in pairs:
        print(p["config"], p["rep"], p["valid"], p["ratio"], p["reuse_stream"], p["reuse_nostream"],
              round(p["h_tvd"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
