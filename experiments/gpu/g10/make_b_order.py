#!/usr/bin/env python3
"""G-10 B order (seed 20264160): N = 28 block (required) first, then N = 25
(extension); replicates r = 0..9 in a shuffled order per N; inside a
replicate the (GPU_BASE, GPU_KV) order is balanced -- 5 replicates per N get
each order, assigned at random. Runner configuration names: GPU_BASE ->
BASE (1,900), GPU_KV -> POOL (2,300), grid (1,2,4,8,16). Every lifecycle
streams and runs the exec-timing layer.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER_CFG = {"GPU_BASE": "BASE", "GPU_KV": "POOL"}
rng = random.Random(20264160)
order = []
for n in (28, 25):
    reps = list(range(10))
    rng.shuffle(reps)
    first = ["GPU_BASE"] * 5 + ["GPU_KV"] * 5
    rng.shuffle(first)
    for r, f in zip(reps, first):
        cs = [f, "GPU_KV" if f == "GPU_BASE" else "GPU_BASE"]
        for c in cs:
            order.append({"tag": f"n{n}.{c}.r{r}", "plan": str(HERE / "plans_b" / f"g10b-n{n}-r{r}.json"),
                          "config": RUNNER_CFG[c], "role": c, "n": n, "rep": r,
                          "block": "required" if n == 28 else "extension"})
(HERE / "plans_b" / "ORDER_B.json").write_text(json.dumps(order, indent=1) + "\n")
print(len(order))
