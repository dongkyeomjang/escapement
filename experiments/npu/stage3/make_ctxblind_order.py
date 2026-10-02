#!/usr/bin/env python3
"""Execution order of the context-cost simulator blind cells N = 15, 18 (TASK101).

Same rules as the main measurement (directive 05 §2.4): five rounds; round k
holds the blocks (N=14, r=k) and (N=16, r=k) in shuffled order; inside a block
the configurations run in a permutation that differs between replicates of
the same N (drawn without replacement). Seed 20261596 (unused before; 20261595 is ORDER_SIM, 20261590..94 the N = 19 rule).
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
SEED = 20261596
ROUNDS = 5
CFGS = {n: ("BASE", "BATCHONLY", "TUNED") for n in (15, 18)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=HERE / "plans" / "main" / "ORDER_CTX.json")
    a = ap.parse_args()
    rng = random.Random(SEED)
    perms = {n: rng.sample(list(itertools.permutations(c)), ROUNDS) for n, c in CFGS.items()}
    order = []
    for k in range(ROUNDS):
        blocks = [(n, k, perms[n][k]) for n in CFGS]
        rng.shuffle(blocks)
        for n, r, perm in blocks:
            for cfg in perm:
                order.append({"seq": len(order), "round": k, "n": n, "rep": r, "config": cfg,
                              "tag": f"{cfg}.n{n}.r{r}", "plan_id": f"main-n{n}-r{r}"})
    a.output.write_text(json.dumps({"seed": SEED, "lifecycles": len(order), "order": order},
                                   indent=1) + "\n")
    for e in order:
        print(e["seq"], e["tag"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
