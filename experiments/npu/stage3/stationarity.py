#!/usr/bin/env python3
"""Stationarity reanalysis with a same-length baseline (STATIONARITY_REANALYSIS.md).

Within-run: first vs second 60 s half of the evaluation window. Baseline:
the same half position across different replicates of the same cell. Window
and split definitions are TASK82's (``main_analyze.halves``). Report only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations, permutations
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_measure as M  # noqa: E402

CELLS = [(n, c) for n in (6, 8, 10, 12) for c in ("BASE", "BATCHONLY", "TUNED")] + [(8, "DP")]


def halves(run: Path, tag: str) -> dict:
    rows = [json.loads(l) for l in (run / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines()
            if l.strip()]
    win = json.loads((run / "probe" / tag / f"windows.{tag}.json").read_text())
    w0 = win["warmup_end_s"]
    w1 = w0 + 120.0
    mid = w0 + 60.0
    ev = M.parse_server(run / f"server-{tag}.log")
    alloc_pos, lookup = {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            alloc_pos.setdefault(e[1], i)
        elif e[0] in ("hit", "partial"):
            lookup[e[1]] = e[2]
    sid_of = {}
    for sid in alloc_pos:
        sid_of.setdefault(sid.rsplit("-", 2)[0], sid)
    win_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
    pos = {r["request_id"]: alloc_pos[sid_of[r["request_id"]]] for r in win_rows}
    second = [r for r in win_rows if r["sent_s"] >= mid]
    lo, hi = min(pos.values()), max(pos.values())
    cut = min(pos[r["request_id"]] for r in second)
    h = (Counter(), Counter())
    for i in range(lo, hi + 1):
        e = ev[i]
        if e[0] == "bucket":
            h[0 if i < cut else 1][e[1]] += 1
    reuse = []
    for part in (0, 1):
        later = [r for r in win_rows if r["turn"] > 0 and ((r["sent_s"] < mid) == (part == 0))]
        hits = 0
        for r in later:
            c = r["cached_tokens"]
            if c is None:
                c = lookup.get(sid_of[r["request_id"]], 0)
            hits += c > 0
        reuse.append((hits, len(later)))
    return {"h": [dict(h[0]), dict(h[1])], "reuse": reuse}


def midrank(x: float, dist: list[float]) -> float:
    below = sum(1 for d in dist if d < x)
    equal = sum(1 for d in dist if d == x)
    return (below + 0.5 * equal) / len(dist)


def sign_p(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    out = {"cells": {}}
    for n, cfg in CELLS:
        reps = range(10) if (n == 8 and cfg in ("TUNED", "DP")) else range(5)
        hv = {r: halves(a.run, f"{cfg}.n{n}.r{r}") for r in reps}
        rate = {r: [x[0] / x[1] for x in hv[r]["reuse"]] for r in reps}
        W = [M.tvd(hv[r]["h"][0], hv[r]["h"][1]) for r in reps]
        B = [M.tvd(hv[r]["h"][p], hv[s]["h"][p]) for r, s in combinations(reps, 2) for p in (0, 1)]
        dlt = [rate[r][1] - rate[r][0] for r in reps]
        D = [rate[s][p] - rate[r][p] for r, s in permutations(reps, 2) for p in (0, 1)]
        absD = [abs(x) for x in D]
        out["cells"][f"{cfg}.n{n}"] = {
            "replicates": len(reps),
            "W": W, "B_n": len(B), "median_W": statistics.median(W), "median_B": statistics.median(B),
            "q_h": statistics.mean(midrank(w, B) for w in W),
            "delta": dlt, "median_delta": statistics.median(dlt), "median_abs_D": statistics.median(absD),
            "q_delta": statistics.mean(midrank(x, D) for x in dlt),
            "q_abs_delta": statistics.mean(midrank(abs(x), absD) for x in dlt),
            "steps_halves": [[sum(hv[r]["h"][0].values()), sum(hv[r]["h"][1].values())] for r in reps],
            "reuse_halves": {r: hv[r]["reuse"] for r in reps}}
    c = out["cells"].values()
    qh = [x["q_h"] for x in c]
    qd = [x["q_delta"] for x in c]
    kh = sum(q > 0.5 for q in qh)
    kd = sum(q < 0.5 for q in qd)
    h_a, h_b = statistics.median(qh) > 0.75, sign_p(kh, len(qh)) < 0.05
    d_a, d_b = statistics.median(qd) < 0.25, sign_p(kd, len(qd)) < 0.05
    cls = lambda x, y: "NONSTATIONARY" if x and y else ("WEAK_EVIDENCE" if x or y else "NOT_NONSTATIONARY")
    out["summary"] = {
        "h": {"median_q_h": statistics.median(qh), "cells_q_gt_half": kh, "sign_p": sign_p(kh, len(qh)),
              "class": cls(h_a, h_b)},
        "reuse": {"median_q_delta": statistics.median(qd), "cells_q_lt_half": kd, "sign_p": sign_p(kd, len(qd)),
                  "class": cls(d_a, d_b),
                  "median_q_abs_delta": statistics.median(x["q_abs_delta"] for x in c)}}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1))
    for k, x in out["cells"].items():
        print(k, x["replicates"], round(x["median_W"], 3), round(x["median_B"], 3), round(x["q_h"], 3),
              round(x["median_delta"], 3), round(x["median_abs_D"], 3), round(x["q_delta"], 3),
              round(x["q_abs_delta"], 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
