#!/usr/bin/env python3
"""G-10 C order (seed 20264260): the chosen N of PREDICTIONS_C.json; replicates
r = 0..4 in shuffled order; inside a replicate the four cells (SHORT_TOOL,
LONG_TOOL) x (GPU_LONG_BASE, GPU_LONG_KV) in a permutation, five distinct
permutations drawn without replacement from the 24. Every lifecycle streams
and runs the exec-timing layer.
"""
import itertools
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / "plans_c" / "PREDICTIONS_C.json").read_text())
n = P["chosen_n"]
cells = [(t, c) for t in ("SHORT_TOOL", "LONG_TOOL") for c in ("GPU_LONG_BASE", "GPU_LONG_KV")]
rng = random.Random(20264260)
perms = rng.sample(list(itertools.permutations(cells)), 5)
reps = list(range(5))
rng.shuffle(reps)
order = []
for r, perm in zip(reps, perms):
    for t, c in perm:
        f = HERE / "plans_c" / f"g10c-n{n}-r{r}-{t.split('_')[0].lower()}.json"
        order.append({"tag": f"n{n}.{t}.{c}.r{r}", "plan": str(f), "config": c, "tool": t, "n": n, "rep": r})
(HERE / "plans_c" / "ORDER_C.json").write_text(json.dumps(order, indent=1) + "\n")
print(len(order))
