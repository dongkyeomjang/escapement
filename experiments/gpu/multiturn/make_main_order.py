#!/usr/bin/env python3
"""GTASK11 main-experiment order (GPU_MULTITURN_PREREG.md amendment 1, item 5).

5 rounds; round k runs the blocks (N, r = k) for N = 20, 22, 24, 26 in a
random block order. Inside a block the configuration order is a permutation
of that N's configurations; for N = 20, 22, 24 the five replicates get five
*different* permutations of (BASE, POOL, POOL+GRID) drawn without
replacement from the six; N = 26 (BASE, POOL) alternates. Seed 20262410.
All lifecycles stream (pilot verdict EQUIVALENT, GTASK10).

usage: make_main_order.py --out <abs json>
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random

PLANS = Path(__file__).resolve().parent / "plans" / "main"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    rng = random.Random(20262410)
    perms = {n: rng.sample(list(itertools.permutations(("BASE", "POOL", "POOL+GRID"))), 5)
             for n in (20, 22, 24)}
    perms[26] = [("BASE", "POOL") if r % 2 == 0 else ("POOL", "BASE") for r in range(5)]
    order = []
    for k in range(5):
        blocks = [20, 22, 24, 26]
        rng.shuffle(blocks)
        for n in blocks:
            for c in perms[n][k]:
                order.append({"tag": f"n{n}.{c}.r{k}", "plan": str(PLANS / f"gmain-n{n}-r{k}.json"),
                              "config": c, "n": n, "stream": True})
    a.out.write_text(json.dumps(order, indent=1) + "\n")
    print(len(order), hashlib.sha256(a.out.read_bytes()).hexdigest())
    for e in order[:11]:
        print(e["tag"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
