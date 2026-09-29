#!/usr/bin/env python3
"""Execution order of the multi-turn main measurement (directive 05 §2.4).

Five rounds k = 0..4. Round k holds the blocks (N=6, r=k), (N=8, r=k),
(N=10, r=k), (N=12, r=k) and the extra DP-vs-TUNED block (N=8, r=k+5); the
block order inside a round is shuffled. Inside a block the configurations run
in a permutation that differs from replicate to replicate of the same N
(permutations drawn without replacement), so no configuration always runs
first or last. Seed 20261410 (preregistration §2).
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
SEED = 20261410
ROUNDS = 5
CFGS = {6: ("BASE", "BATCHONLY", "TUNED"), 8: ("BASE", "BATCHONLY", "TUNED", "DP"),
        10: ("BASE", "BATCHONLY", "TUNED"), 12: ("BASE", "BATCHONLY", "TUNED")}
EXT_CFGS = ("DP", "TUNED")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=HERE / "plans" / "main" / "ORDER.json")
    a = ap.parse_args()
    rng = random.Random(SEED)
    perms = {n: rng.sample(list(itertools.permutations(c)), ROUNDS) for n, c in CFGS.items()}
    ext_perms = [EXT_CFGS if k % 2 == 0 else EXT_CFGS[::-1] for k in range(ROUNDS)]
    order = []
    for k in range(ROUNDS):
        blocks = [(n, k, perms[n][k]) for n in CFGS] + [(8, k + 5, ext_perms[k])]
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
