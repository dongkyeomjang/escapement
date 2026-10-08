#!/usr/bin/env python3
"""G-10 A: order of the exec-timing ON/OFF development check (seed 20264901).

20 pairs = 2 loads x 2 configurations x 5; pairs shuffled; ON/OFF order inside a
pair drawn per pair. Pair index k (0..4) of a condition sets the prompt seeds.
"""
import json
import random
from pathlib import Path

rng = random.Random(20264901)
pairs = [(load, cfg, k) for load in ("low", "sat") for cfg in ("GPU_BASE", "GPU_KV") for k in range(5)]
rng.shuffle(pairs)
order = []
for load, cfg, k in pairs:
    arms = [0, 1]
    rng.shuffle(arms)
    for x in arms:
        order.append({"tag": f"{load}.{cfg}.p{k}.exec{x}", "load": load, "config": cfg, "pair": k, "exec": x})
Path(__file__).with_name("exec_check_order.json").write_text(json.dumps(order, indent=1) + "\n")
print(len(order))
