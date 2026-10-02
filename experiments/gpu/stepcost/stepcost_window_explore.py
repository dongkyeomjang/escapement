#!/usr/bin/env python3
"""GTASK05 exploratory (NOT preregistered): per-lag deltas and a 3-step window
increment sum(Delta_{k..k+2}) - 3 * decode baseline for isolated steps.

Written after the preregistered analysis showed negative lag-1 increments for
small eager steps. Uses the amendment-2 probe matching (--chunk-budget 2048).
usage: stepcost_window_explore.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stepcost_analyze import lifecycle_cells  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for d in sorted(Path(a.run_dir).iterdir()):
        if not (d / "events.json").exists():
            continue
        _, iso = lifecycle_cells(d, None, 2048)
        for (phase, dd, pp), c in sorted(iso.items()):
            if not c["baseline"] or not all(c["lagged"][L] for L in (0, 1, 2)):
                continue
            b = statistics.median(c["baseline"])
            lag = [statistics.median(c["lagged"][L]) for L in (0, 1, 2)]
            out.setdefault(f"{d.name[:2]}/{phase}/d{dd}/p{pp}", []).append(
                {"lifecycle": d.name, "mode": c["mode"], "baseline_ms": 1e3 * b,
                 "lag_ms": [1e3 * v for v in lag], "window3_increment_ms": 1e3 * (sum(lag) - 3 * b)})
    for v in out.values():
        w = [x["window3_increment_ms"] for x in v]
        v.append({"median_window3_increment_ms": statistics.median(w),
                  "range_ms": max(w) - min(w)})
    Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
