#!/usr/bin/env python3
"""Run orders of the 2026-10-08 directive (DX_PREREG.md §2.4). Seeded,
balanced, fixed before measurement.

* ORDER_DXA  work A perturbation check: (BASE|TUNED) x (N6|N18 DEV plans),
             pair r = 0..4 of each condition = the same plan with OBS on and
             off. Round r runs the four conditions of pair r in a shuffled
             order; inside each pair the on/off order is a coin flip, balanced
             so that each condition has its "on first" in 2 or 3 of 5 pairs.
             Evaluation window 60 s.
* ORDER_DXB  work B required: N = 18, BASE / TUNED, r = 0..9, OBS on, 120 s;
             replicate r runs its two configs in a shuffled order, five
             replicates BASE first and five TUNED first.
* ORDER_DXC  work C: N = 14, (BASE|TUNED) x (cap 60|120), r = 0..4, OBS on,
             120 s; replicate r runs its four cells in a shuffled order
             (distinct permutations across replicates).
* ORDER_DXB8 work B extension: N = 8, as ORDER_DXB.
* ORDER_DXE  work E: N = 19, (BATCHONLY|TUNED|DP_N8), r = 0..9, OBS on, 120 s;
             each of the 6 permutations used at least once, then seeded.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
OUT = HERE / "plans" / "dx"
SEEDS = {"A": 20268002, "B": 20268003, "C": 20268004, "B8": 20268005, "E": 20268006}


def balanced_firsts(rng: random.Random, k: int, a, b) -> list:
    half = [a] * (k // 2) + [b] * (k - k // 2)
    rng.shuffle(half)
    return half


def order_a() -> list[dict]:
    rng = random.Random(SEEDS["A"])
    conds = [("BASE", 6), ("BASE", 18), ("TUNED", 6), ("TUNED", 18)]
    first = {c: balanced_firsts(rng, 5, 1, 0) for c in conds}
    out = []
    for r in range(5):
        cs = conds[:]
        rng.shuffle(cs)
        for cfg, n in cs:
            f = first[(cfg, n)][r]
            for obs in (f, 1 - f):
                out.append({"tag": f"A.{cfg}.n{n}.r{r}.{'on' if obs else 'off'}", "config": cfg,
                            "plan_id": f"dx-dev-n{n}-r{r}", "obs": obs, "eval_s": 60})
    return out


def order_pairs(key: str, n: int, role: str) -> list[dict]:
    rng = random.Random(SEEDS[key])
    firsts = balanced_firsts(rng, 10, "BASE", "TUNED")
    out = []
    for r in range(10):
        cs = ["BASE", "TUNED"] if firsts[r] == "BASE" else ["TUNED", "BASE"]
        for cfg in cs:
            out.append({"tag": f"{role}.{cfg}.n{n}.r{r}", "config": cfg, "plan_id": f"dx-b-n{n}-r{r}",
                        "obs": 1, "eval_s": 120})
    return out


def order_c() -> list[dict]:
    rng = random.Random(SEEDS["C"])
    cells = [(c, cap) for c in ("BASE", "TUNED") for cap in (60, 120)]
    perms = list(itertools.permutations(cells))
    pick = rng.sample(perms, 5)
    out = []
    for r in range(5):
        for cfg, cap in pick[r]:
            out.append({"tag": f"C.{cfg}.n14.cap{cap}.r{r}", "config": cfg,
                        "plan_id": f"dx-c-n14-cap{cap}-r{r}", "obs": 1, "eval_s": 120})
    return out


def order_e() -> list[dict]:
    rng = random.Random(SEEDS["E"])
    perms = list(itertools.permutations(("BATCHONLY", "TUNED", "DP_N8")))
    seq = perms[:] + [rng.choice(perms) for _ in range(4)]
    rng.shuffle(seq)
    out = []
    for r in range(10):
        for cfg in seq[r]:
            out.append({"tag": f"E.{cfg}.n19.r{r}", "config": cfg, "plan_id": f"dx-e-n19-r{r}",
                        "obs": 1, "eval_s": 120})
    return out


def main() -> int:
    for name, items in (("ORDER_DXA", order_a()), ("ORDER_DXB", order_pairs("B", 18, "B")),
                        ("ORDER_DXC", order_c()), ("ORDER_DXB8", order_pairs("B8", 8, "B")),
                        ("ORDER_DXE", order_e())):
        for i, e in enumerate(items):
            e["seq"] = i
        (OUT / f"{name}.json").write_text(json.dumps({"seed": SEEDS[name.replace("ORDER_DX", "") or "B"],
                                                      "order": items}, indent=1) + "\n")
        print(name, len(items), [e["tag"] for e in items[:4]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
