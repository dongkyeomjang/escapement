#!/usr/bin/env python3
"""G-10 C: fit of the long-context FULL decode step cost (GTASK18 form F1).

Prereg: docs/research/gpu/G10_CTX_LONG_PREREG.md section 3. Step time per cell
exactly as GTASK18 (``stepcost_ctx_analyze.cell_times``: dispatch gap of two
consecutive FULL decode-only steps of width n inside the cell, 3 trimmed at
each end, median per lifecycle, median of lifecycles). Sigma L = sum over
requests of (L + GEN/2).

F1  t = a(n) + c * Sigma L on all 24 cells -> ``c_long`` (the only number
passed to the C predictions; the predictor's form is GTASK20 ``ctx``:
price + c * (decode context - decodes * 128)).
Reported without verdict: per-n slopes, residuals by L, GTASK18 c.

usage: ctx_long_analyze.py --run-dir <abs> --out <abs json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stepcost"))
sys.path.insert(0, str(HERE.parent / "multiturn"))
from stepcost_ctx_analyze import cell_times, lstsq  # noqa: E402
import gpu_cost as C  # noqa: E402

GEN = 128
GRID = (1, 2, 4, 8, 16)
C_GTASK18 = 2.120e-4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    order = json.loads((HERE / "ctx_long_order.json").read_text())
    cdef = {c["cell"]: c for c in order["cells"]}
    lifes, per = {}, {}
    for d in sorted(a.run_dir.iterdir()):
        if d.is_dir() and (d / "summary.json").exists():
            s = json.loads((d / "summary.json").read_text())
            lifes[d.name] = s
            if not s["valid"]:
                continue
            for cell, batches in cell_times(d).items():
                allv = [x for b in batches for x in b]
                if allv:
                    per.setdefault(cell, []).append({"life": d.name, "median": statistics.median(allv),
                                                     "steps": len(allv)})
    cells = {}
    for cell, v in per.items():
        c = cdef[cell]
        cells[cell] = {"n": c["n"], "L": c["L"], "sigmaL": sum(x + GEN / 2 for x in c["lens"]),
                       "t_ms": statistics.median(x["median"] for x in v),
                       "rep_range_ms": max(x["median"] for x in v) - min(x["median"] for x in v),
                       "lifecycles": v, "price_ms": C.decode_ms(c["n"], GRID)}
    complete = len(cells) == len(cdef)
    ns = sorted({v["n"] for v in cells.values()})
    X = [[1.0 if v["n"] == n else 0.0 for n in ns] + [v["sigmaL"]] for v in cells.values()]
    y = [v["t_ms"] for v in cells.values()]
    beta = lstsq(X, y)
    an, c = dict(zip(ns, beta[:-1])), beta[-1]
    resid = {k: v["t_ms"] - (an[v["n"]] + c * v["sigmaL"]) for k, v in cells.items()}
    pern = {}
    for n in ns:
        pts = sorted((v["sigmaL"], v["t_ms"]) for v in cells.values() if v["n"] == n)
        b = lstsq([[1.0, x] for x, _ in pts], [t for _, t in pts])
        pern[n] = {"a_ms": b[0], "c_ms_per_token": b[1],
                   "max_abs_resid_ms": max(abs(t - b[0] - b[1] * x) for x, t in pts)}
    # what the GTASK20 ctx predictor (GTASK18 c) would have said for these cells
    old = {k: C.decode_ms(v["n"], GRID) + C_GTASK18 * (v["sigmaL"] - v["n"] * 128) for k, v in cells.items()}
    new = {k: C.decode_ms(v["n"], GRID) + c * (v["sigmaL"] - v["n"] * 128) for k, v in cells.items()}
    out = {"complete": complete, "lifecycles": lifes, "cells": cells,
           "F1": {"a_ms": an, "c_ms_per_token": c, "resid_ms": resid,
                  "max_abs_resid_ms": max(abs(r) for r in resid.values())},
           "per_n": pern, "c_gtask18": C_GTASK18,
           "predictor_vs_measured": {k: {"t_ms": cells[k]["t_ms"], "ctx_gtask18_ms": old[k],
                                         "ctx_long_ms": new[k]} for k in cells}}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"complete {complete} c_long {c:.4e} ms/token (GTASK18 {C_GTASK18:.4e}), "
          f"max |resid| {out['F1']['max_abs_resid_ms']:.3f} ms")
    for n in ns:
        print(n, {v["L"]: round(v["t_ms"], 3) for v in sorted(cells.values(), key=lambda v: v["L"]) if v["n"] == n})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
