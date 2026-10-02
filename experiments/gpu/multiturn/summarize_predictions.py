#!/usr/bin/env python3
"""Print the prereg tables from PREDICTIONS.json (GTASK09). Read-only.

usage: summarize_predictions.py <abs PREDICTIONS.json>
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

P = ("analytic", "sim_lru", "sim_fifo")


def main() -> int:
    d = json.loads(Path(sys.argv[1]).read_text())
    cells = d["cells"]
    print("## reuse rate (lo | hi) and token ratio (lo)")
    for n, c in cells.items():
        for cfg, e in c.items():
            print(n, cfg, " | ".join(
                f"{p} {e[p + '/lo']['reuse_rate']:.3f}/{e[p + '/hi']['reuse_rate']:.3f} "
                f"tok {e[p + '/lo']['token_reuse_ratio']:.3f}" for p in P))
    print("## hit shape (sim lo)")
    for n, c in cells.items():
        for cfg, e in c.items():
            print(n, cfg, {p: {k: round(v, 3) for k, v in e[p + "/lo"]["hit_shape_share"].items()}
                           for p in ("sim_lru", "sim_fifo")})
    print("## device ms/turn (lo/hi) and ratio to BASE (lo/hi)")
    for n, c in cells.items():
        for cfg, e in c.items():
            print(n, cfg, " | ".join(
                f"{p} {1e3 * e[p + '/lo']['device_per_turn_s']:.1f}/{1e3 * e[p + '/hi']['device_per_turn_s']:.1f} "
                f"r {e[p + '/lo']['ratio_to_base']:.4f}/{e[p + '/hi']['ratio_to_base']:.4f} "
                f"rank {e[p + '/lo']['rank']}/{e[p + '/hi']['rank']}" for p in P))
    print("## per-rep ratio to BASE (sim_lru lo)")
    for n, c in cells.items():
        for cfg, e in c.items():
            if cfg != "BASE":
                print(n, cfg, [round(x, 4) for x in e["sim_lru/lo"]["per_rep_ratio_to_base"]])
    print("## interference ms/turn (lo/hi), padding, analytic mean running")
    for n, c in cells.items():
        for cfg, e in c.items():
            print(n, cfg, " | ".join(
                f"{p} {1e3 * e[p + '/lo']['interference_per_turn_s']:.2f}/{1e3 * e[p + '/hi']['interference_per_turn_s']:.2f}"
                f" pad {e[p + '/lo']['padding']:.4f}" for p in P),
                  f"run {e['analytic/lo']['mean_running']:.2f}")
    print("## LRU - FIFO reuse gap (lo, hi)")
    for n, c in cells.items():
        for cfg, e in c.items():
            print(n, cfg, round(e["sim_lru/lo"]["reuse_rate"] - e["sim_fifo/lo"]["reuse_rate"], 3),
                  round(e["sim_lru/hi"]["reuse_rate"] - e["sim_fifo/hi"]["reuse_rate"], 3))
    print("## PIECEWISE interval impact")
    for k, v in d["piecewise_interval_impact"].items():
        print(k, {kk: round(vv, 4) for kk, vv in v.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
