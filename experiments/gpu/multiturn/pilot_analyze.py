#!/usr/bin/env python3
"""Verdict for the GPU streaming observer-effect pilot (GPU_MT_PILOT_PREREG.md).

Pairs: same (configuration, replicate), streaming / non-streaming turn-level
device time (A'-GPU). Equivalence (principle 17): the median of the 6 pair
ratios has a 95 % percentile bootstrap CI (10,000 resamples of the pairs,
seed 20262510) that contains 1 and is at most 0.04 wide -- at **both** cost
bounds. Also reported: the direct dispatch channel's pair ratios, and the
run-to-run spread of the POOL/BASE paired ratio (the main experiment's
quantity) per mode.

usage: pilot_analyze.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_mt_measure as M  # noqa: E402

CONFIGS = ("BASE", "POOL")
REPS = 3
WIDTH_CAP = 0.04
BOOT, BOOT_SEED = 10_000, 20262510


def boot_ci(xs: list[float]) -> tuple[float, float]:
    rng = random.Random(BOOT_SEED)
    bs = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(BOOT))
    return bs[int(0.025 * BOOT)], bs[int(0.975 * BOOT) - 1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    cells = {}
    for c in CONFIGS:
        for mode in ("stream", "nostream"):
            for r in range(REPS):
                tag = f"{c}.{mode}.r{r}"
                d = a.run_dir / tag
                cells[tag] = M.lifecycle_metrics(d) if (d / "windows.json").exists() else {"valid": False,
                                                                                              "missing": True}
    verdicts = {}
    pairs = []
    for c in CONFIGS:
        for r in range(REPS):
            s, n = cells[f"{c}.stream.r{r}"], cells[f"{c}.nostream.r{r}"]
            ok = s.get("valid") and n.get("valid")
            p = {"config": c, "rep": r, "valid": bool(ok)}
            if ok:
                for b in ("lo", "hi"):
                    p[f"ratio_{b}"] = s["device_per_turn_s"][b] / n["device_per_turn_s"][b]
                p["ratio_direct"] = s["direct_per_turn_s"] / n["direct_per_turn_s"]
                p["reuse_stream"], p["reuse_nostream"] = s["reuse"], n["reuse"]
                p["h_tvd"] = M.tvd({int(k): v for k, v in s["h_counts"].items()},
                                   {int(k): v for k, v in n["h_counts"].items()})
                p["throughput_ratio"] = s["throughput_per_s"] / n["throughput_per_s"]
            pairs.append(p)
    for key in ("ratio_lo", "ratio_hi", "ratio_direct"):
        xs = [p[key] for p in pairs if p["valid"]]
        if len(xs) < 2:
            verdicts[key] = {"verdict": "INSUFFICIENT", "n": len(xs)}
            continue
        lo, hi = boot_ci(xs)
        verdicts[key] = {"median": statistics.median(xs), "ci95": [lo, hi], "width": hi - lo,
                         "n": len(xs), "verdict": "EQUIVALENT" if lo <= 1 <= hi and hi - lo <= WIDTH_CAP
                         else "NOT_EQUIVALENT"}
    primary = ("EQUIVALENT" if all(verdicts[k].get("verdict") == "EQUIVALENT" for k in ("ratio_lo", "ratio_hi"))
               else "NOT_EQUIVALENT")
    spread = {}
    for mode in ("stream", "nostream"):
        rs = []
        for r in range(REPS):
            b, p = cells[f"BASE.{mode}.r{r}"], cells[f"POOL.{mode}.r{r}"]
            if b.get("valid") and p.get("valid"):
                rs.append(p["device_per_turn_s"]["lo"] / b["device_per_turn_s"]["lo"])
        spread[mode] = {"pool_over_base_lo": rs,
                        "range": (max(rs) - min(rs)) if len(rs) > 1 else None}
    out = {"verdict": primary, "decision": "main experiment streaming" if primary == "EQUIVALENT"
           else "main experiment non-streaming + streaming auxiliary",
           "verdicts": verdicts, "pairs": pairs, "spread": spread,
           "runner_checks": {k: {"valid": v.get("valid"), **(v.get("checks") or {}),
                                 "invalid_reasons": v.get("invalid_reasons")} for k, v in cells.items()},
           "cells": cells}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"verdict": primary, "verdicts": verdicts, "spread": spread}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
