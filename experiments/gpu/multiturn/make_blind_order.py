#!/usr/bin/env python3
"""G-07 C blind order (GPU_BLIND_COLLAPSE_PREREG.md), GTASK11 layout.

5 rounds; round k runs the blocks (N, r = k) for N = 25, 28 in a random block
order; inside a block the five replicates of each N get five different
permutations of (BASE, POOL, POOL+GRID) drawn without replacement from the
six. Seed 20263010. All lifecycles stream.

usage: make_blind_order.py --out <abs json>
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random

PLANS = Path(__file__).resolve().parent / "plans" / "blind"
NS = (25, 28)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    rng = random.Random(20263010)
    perms = {n: rng.sample(list(itertools.permutations(("BASE", "POOL", "POOL+GRID"))), 5) for n in NS}
    order = []
    for k in range(5):
        blocks = list(NS)
        rng.shuffle(blocks)
        for n in blocks:
            for c in perms[n][k]:
                order.append({"tag": f"n{n}.{c}.r{k}", "plan": str(PLANS / f"gblind-n{n}-r{k}.json"),
                              "config": c, "n": n, "stream": True})
    a.out.write_text(json.dumps(order, indent=1) + "\n")
    print(len(order), hashlib.sha256(a.out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
