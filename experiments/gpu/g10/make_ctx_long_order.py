#!/usr/bin/env python3
"""G-10 C: cell order of the long-context FULL decode step-cost microbenchmark.

Same protocol as GTASK18 (``stepcost/stepcost_ctx_run.py``), context lengths
extended to the LONG_TOOL range. Calibration only: prompt ids are random draws
with their own seeds (20264800 + 100000 * rep + ...), disjoint from every plan.
"""
import json
import random
from pathlib import Path

NS = (1, 2, 4, 8)
LS = (64, 1500, 3000, 4500, 6000, 7000)
SEED = 20264800
cells = [{"cell": f"n{n}L{L}", "n": n, "L": L, "lens": [L] * n} for n in NS for L in LS]
rng = random.Random(SEED)
life = {}
for rep in (0, 1):
    rounds = []
    for _ in range(3):
        names = [c["cell"] for c in cells]
        rng.shuffle(names)
        rounds.append(names)
    life[str(rep)] = rounds
out = {"seed": SEED, "note": "G-10 C long-context cell order (GTASK18 protocol); 3 rounds per lifecycle",
       "cells": cells, "lifecycles": life}
Path(__file__).with_name("ctx_long_order.json").write_text(json.dumps(out, indent=1) + "\n")
