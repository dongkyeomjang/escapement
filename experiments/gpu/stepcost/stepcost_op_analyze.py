#!/usr/bin/env python3
"""GTASK17: analysis of the serving-condition FULL decode curves.

Prereg: docs/research/gpu/GPU_STEPCOST_OP_PREREG.md section 4.
Step time of a width-n FULL step k = t_{k+1} - t_k (dispatch gap) for steps
k inside a ``FULL n=.. k=..`` segment where k and k+1 are both
``maxq == 1, reqs == n, mode FULL``; the first and last TRIM such steps of each
batch are dropped. Cell value = median over the lifecycle's three batches.

usage: stepcost_op_analyze.py --run-dir <abs> --out <abs json> --md <abs md>
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from itertools import product
import json
from math import exp, log
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(HERE.parent / "multiturn"))
from parse_obs import parse  # noqa: E402
import gpu_cost as C  # noqa: E402

TRIM = 3
NS = list(range(1, 9))
GRID = (1, 2, 4, 8, 16)
GTASK15_RATIO = {1: 1.034, 2: 1.064, 3: 1.100, 4: 1.123, 5: 1.147, 6: 1.172, 7: 1.227, 8: 1.219}


def cell_times(run: Path) -> dict:
    ev = [e for e in parse(run / "server.log") if e["kind"] == "STEP"]
    walls = [e["wall"] for e in ev]
    marks = json.loads((run / "events.json").read_text())
    starts = {m["tag"][:-6]: m["wall"] for m in marks if m["tag"].endswith(" start")}
    ends = {m["tag"][:-4]: m["wall"] for m in marks if m["tag"].endswith(" end")}
    out = {}
    for tag, w0 in starts.items():
        n = int(tag.split("n=")[1].split()[0])
        i0, i1 = bisect_left(walls, w0), bisect_left(walls, ends[tag])
        seg = ev[i0:i1]
        ok = [k for k in range(len(seg) - 1)
              if all(s["maxq"] == 1 and s["reqs"] == n and s["mode"] == "FULL" for s in (seg[k], seg[k + 1]))]
        ok = ok[TRIM:len(ok) - TRIM]
        out.setdefault(n, []).append([(seg[k + 1]["t"] - seg[k]["t"]) * 1e3 for k in ok])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--md", required=True, type=Path)
    a = ap.parse_args()
    lifes = {}
    for d in sorted(a.run_dir.iterdir()):
        if d.is_dir() and (d / "summary.json").exists():
            s = json.loads((d / "summary.json").read_text())
            lifes[d.name] = (s, cell_times(d) if s["valid"] else None)
    cells = {}
    for name, (s, ct) in lifes.items():
        if ct is None:
            continue
        for n, batches in ct.items():
            allv = [x for b in batches for x in b]
            cells.setdefault(s["condition"], {}).setdefault(n, []).append(
                {"rep": s["rep"], "median": statistics.median(allv), "steps": len(allv),
                 "batch_medians": [statistics.median(b) for b in batches if b]})
    curve = {c: {n: statistics.median(x["median"] for x in v) for n, v in sorted(d.items())}
             for c, d in cells.items()}
    rep_range = {c: {n: max(x["median"] for x in v) - min(x["median"] for x in v)
                     for n, v in d.items()} for c, d in cells.items()}
    price = {n: C.decode_ms(n, GRID) for n in NS}
    fits = {}
    for c, cv in curve.items():
        xs = [n for n in NS if n in cv]
        ys = [cv[n] for n in xs]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        g = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        fits[c] = {"slope_ms_per_req": g, "intercept_ms": my - g * mx}
    # factorial effects on log step time, per n and averaged over n
    full = all(f"s{s}k{k}a{d}" in curve for s, k, d in product((0, 1), repeat=3))
    effects = {}
    if full:
        def L(s, k, d, n):
            return log(curve[f"s{s}k{k}a{d}"][n])
        for n in NS + ["mean"]:
            ns = NS if n == "mean" else [n]
            def avg(f):
                return statistics.mean(f(n_) for n_ in ns)
            e = {}
            for name, idx in (("stream", 0), ("kv", 1), ("admlog", 2)):
                def me(n_, idx=idx):
                    on = [L(*[1 if i == idx else b for i, b in enumerate(t)], n_) for t in product((0, 1), repeat=3) if t[idx] == 0]
                    off = [L(*t, n_) for t in product((0, 1), repeat=3) if t[idx] == 0]
                    return statistics.mean(on) - statistics.mean(off)
                e[name] = exp(avg(me))
            for (n1, i1), (n2, i2) in (((("stream", 0), ("kv", 1))), (("stream", 0), ("admlog", 2)), (("kv", 1), ("admlog", 2))):
                def ia(n_, i1=i1, i2=i2):
                    vals = []
                    for t in product((0, 1), repeat=3):
                        sign = (1 if t[i1] else -1) * (1 if t[i2] else -1)
                        vals.append(sign * L(*t, n_))
                    return sum(vals) / 4
                e[f"{n1}x{n2}"] = exp(avg(ia))
            def ia3(n_):
                return sum((1 if t[0] else -1) * (1 if t[1] else -1) * (1 if t[2] else -1) * L(*t, n_)
                           for t in product((0, 1), repeat=3)) / 4
            e["stream x kv x admlog"] = exp(avg(ia3))
            effects[str(n)] = e
    op = curve.get("s1k1a1", {})
    repro = {n: {"gtask11_cond_over_price": op[n] / price[n], "gtask15_operating_ratio": GTASK15_RATIO[n]}
             for n in NS if n in op}
    out = {"lifecycles": {k: v[0] for k, v in lifes.items()}, "cells": cells, "curve_ms": curve,
           "rep_range_ms": rep_range, "price_ms": price, "fits": fits, "effects_ratio": effects,
           "gtask11_condition_vs_operating": repro}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    lines = ["# GTASK17 stepcost_op summary (machine generated)", "",
             "valid: " + ", ".join(f"{k}={v[0]['valid']}" for k, v in lifes.items()), "",
             "| condition | " + " | ".join(f"n={n}" for n in NS) + " | slope ms/req |",
             "|---" * (len(NS) + 2) + "|"]
    for c in sorted(curve):
        lines.append(f"| {c} | " + " | ".join(f"{curve[c].get(n, float('nan')):.3f}" for n in NS)
                     + f" | {fits[c]['slope_ms_per_req']:.4f} |")
    lines += ["", "| price (GTASK05) | " + " | ".join(f"{price[n]:.3f}" for n in NS) + " | |", ""]
    if effects:
        lines.append("effects (ratio, mean over n): " + json.dumps({k: round(v, 4) for k, v in effects["mean"].items()}))
    lines.append("")
    lines.append("s1k1a1 / price vs GTASK15: " + json.dumps({n: [round(v["gtask11_cond_over_price"], 3), v["gtask15_operating_ratio"]] for n, v in repro.items()}))
    a.md.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
