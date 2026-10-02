#!/usr/bin/env python3
"""GTASK18: analysis of FULL decode step time vs context length.

Prereg: docs/research/gpu/GPU_STEPCOST_CTX_PREREG.md section 4.
Step time = dispatch gap between two consecutive ``[GSTEP]`` that are both
``maxq == 1, reqs == n, mode FULL`` inside a ``CTX`` segment, first and last
TRIM dropped per batch (GTASK17 rule). Cell value per lifecycle = median over
its batches; cell value = median of the lifecycle values.

Sigma L of a cell = sum over requests of (prompt + GEN/2) (mean context during
the decode steps). Forms reported (no verdict):
  F1  t = a(n) + c * SigmaL           (one c, a per n)
  per-n  t = a_n + c_n * SigmaL       (separate slope per n)
Reproduction of GTASK15 operating ratios from the plan context distribution
(GTASK11 confirmation plans N20/22/24, decode-step weighted, all sessions):
  d in {1,2,4,8}: (a) F1 at SigmaL = d * Lbar; (b) per-n linear interpolation of
  the measured uniform-L cells at L = Lbar (model free).
  d in {3,5,6,7}: F1 with a(d) = GTASK17 s1k1a1 curve(d) - c * d * (64 + 128).

usage: stepcost_ctx_analyze.py --run-dir <abs> --out <abs json> --md <abs md>
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
import glob
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(HERE.parent / "multiturn"))
from parse_obs import parse  # noqa: E402
import gpu_cost as C  # noqa: E402

TRIM, GEN = 3, 128
GRID = (1, 2, 4, 8, 16)
NS = (1, 2, 4, 8)
LS = (64, 512, 1500, 3000)
GTASK15_RATIO = {1: 1.034, 2: 1.064, 3: 1.100, 4: 1.123, 5: 1.147, 6: 1.172, 7: 1.227, 8: 1.219}
GTASK17 = REPO / "experiments/gpu/stepcost/op_result/summary.json"


def plan_context() -> dict:
    ctx = []
    for N in (20, 22, 24):
        for f in sorted(glob.glob(str(REPO / f"experiments/gpu/multiturn/plans/main/gmain-n{N}-r*.json"))):
            d = json.loads(Path(f).read_text())
            for sl in d["slots"]:
                for s in sl["sessions"]:
                    tot = 0
                    for t in s["turns"]:
                        tot += t["new_segment_tokens"]
                        ctx += [tot + j for j in range(1, t["generation_tokens"])]
                        tot += t["generation_tokens"]
    ctx.sort()
    q = lambda p: ctx[int(p * (len(ctx) - 1))]  # noqa: E731
    return {"steps": len(ctx), "mean": statistics.fmean(ctx),
            "p05": q(.05), "p25": q(.25), "p50": q(.5), "p75": q(.75), "p95": q(.95), "max": ctx[-1]}


def cell_times(run: Path) -> dict:
    ev = [e for e in parse(run / "server.log") if e["kind"] == "STEP"]
    walls = [e["wall"] for e in ev]
    marks = json.loads((run / "events.json").read_text())
    starts = {m["tag"][:-6]: m["wall"] for m in marks if m["tag"].endswith(" start")}
    ends = {m["tag"][:-4]: m["wall"] for m in marks if m["tag"].endswith(" end")}
    out: dict = {}
    for tag, w0 in starts.items():
        name = tag.split()[1]
        n = int(tag.split("n=")[1].split()[0])
        i0, i1 = bisect_left(walls, w0), bisect_left(walls, ends[tag])
        seg = ev[i0:i1]
        ok = [k for k in range(len(seg) - 1)
              if all(s["maxq"] == 1 and s["reqs"] == n and s["mode"] == "FULL" for s in (seg[k], seg[k + 1]))]
        ok = ok[TRIM:len(ok) - TRIM]
        out.setdefault(name, []).append([(seg[k + 1]["t"] - seg[k]["t"]) * 1e3 for k in ok])
    return out


def lstsq(X: list, y: list) -> list:
    """Normal equations with Gauss-Jordan (small systems)."""
    m = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(m)] + [sum(r[i] * v for r, v in zip(X, y))] for i in range(m)]
    for i in range(m):
        p = max(range(i, m), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        for r in range(m):
            if r != i:
                f = A[r][i] / A[i][i]
                A[r] = [x - f * z for x, z in zip(A[r], A[i])]
    return [A[i][m] / A[i][i] for i in range(m)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--md", required=True, type=Path)
    a = ap.parse_args()
    order = json.loads((HERE / "ctx_order.json").read_text())
    cdef = {c["cell"]: c for c in order["cells"]}
    lifes = {}
    for d in sorted(a.run_dir.iterdir()):
        if d.is_dir() and (d / "summary.json").exists():
            s = json.loads((d / "summary.json").read_text())
            lifes[d.name] = (s, cell_times(d) if s["valid"] else None)
    per: dict = {}
    for name, (s, ct) in lifes.items():
        if ct is None:
            continue
        for cell, batches in ct.items():
            allv = [x for b in batches for x in b]
            if allv:
                per.setdefault(cell, []).append({"life": name, "median": statistics.median(allv), "steps": len(allv)})
    cells = {}
    for cell, v in per.items():
        c = cdef[cell]
        cells[cell] = {"n": c["n"], "L": c["L"], "sigmaL": sum(x + GEN / 2 for x in c["lens"]),
                       "t_ms": statistics.median(x["median"] for x in v),
                       "rep_range_ms": max(x["median"] for x in v) - min(x["median"] for x in v),
                       "lifecycles": v, "price_ms": C.decode_ms(c["n"], GRID)}
        cells[cell]["over_price"] = cells[cell]["t_ms"] / cells[cell]["price_ms"]
    uni = {k: v for k, v in cells.items() if v["L"] != "mix"}
    # F1: a(n) per n + common c, fitted on the uniform-L cells
    ns = sorted({v["n"] for v in uni.values()})
    X = [[1.0 if v["n"] == n else 0.0 for n in ns] + [v["sigmaL"]] for v in uni.values()]
    y = [v["t_ms"] for v in uni.values()]
    beta = lstsq(X, y) if len(set(ns)) == len(NS) and len(y) == len(NS) * len(LS) else None
    f1 = None
    if beta:
        an = dict(zip(ns, beta[:-1]))
        c = beta[-1]
        resid = {k: v["t_ms"] - (an[v["n"]] + c * v["sigmaL"]) for k, v in cells.items()}
        f1 = {"a_ms": an, "c_ms_per_token": c, "resid_ms": resid,
              "max_abs_resid_uniform_ms": max(abs(resid[k]) for k in uni),
              "resid_mix_ms": {k: resid[k] for k in cells if cells[k]["L"] == "mix"}}
    pern = {}
    for n in ns:
        pts = sorted((v["sigmaL"], v["t_ms"]) for v in uni.values() if v["n"] == n)
        b = lstsq([[1.0, x] for x, _ in pts], [t for _, t in pts])
        pern[n] = {"a_ms": b[0], "c_ms_per_token": b[1],
                   "max_abs_resid_ms": max(abs(t - b[0] - b[1] * x) for x, t in pts)}
    pc = plan_context()
    lbar = pc["mean"]
    repro = {}
    g17 = json.loads(GTASK17.read_text())["curve_ms"]["s1k1a1"]
    for d in range(1, 9):
        price = C.decode_ms(d, GRID)
        r = {"gtask15": GTASK15_RATIO[d], "price_ms": price}
        if f1:
            ad = f1["a_ms"][d] if d in f1["a_ms"] else g17[str(d)] - f1["c_ms_per_token"] * d * (64 + 128)
            r["F1"] = (ad + f1["c_ms_per_token"] * d * lbar) / price
        if d in NS:
            pts = sorted((v["L"] + GEN / 2, v["t_ms"]) for v in uni.values() if v["n"] == d)
            for (x0, t0), (x1, t1) in zip(pts, pts[1:]):
                if x0 <= lbar <= x1:
                    r["interp"] = (t0 + (t1 - t0) * (lbar - x0) / (x1 - x0)) / price
        repro[d] = r
    out = {"lifecycles": {k: v[0] for k, v in lifes.items()}, "cells": cells, "F1": f1, "per_n": pern,
           "plan_context": pc, "reproduction": repro}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    L = ["# GTASK18 stepcost_ctx summary (machine generated)", "",
         "valid: " + ", ".join(f"{k}={v[0]['valid']}" for k, v in lifes.items()), "",
         "t (ms) / over price:", "", "| n | " + " | ".join(f"L={x}" for x in LS) + " | mix |", "|---" * (len(LS) + 2) + "|"]
    for n in NS:
        row = []
        for x in list(LS) + ["mix"]:
            k = f"n{n}L{x}" if x != "mix" else f"n{n}mix"
            row.append(f"{cells[k]['t_ms']:.3f} / {cells[k]['over_price']:.3f}" if k in cells else "")
        L.append(f"| {n} | " + " | ".join(row) + " |")
    L += ["", "max rep range ms: %.4f" % max(v["rep_range_ms"] for v in cells.values()), ""]
    if f1:
        L.append("F1: c = %.3e ms/token, a = %s, max |resid| uniform %.3f ms, mix resid %s" % (
            f1["c_ms_per_token"], json.dumps({k: round(v, 3) for k, v in f1["a_ms"].items()}),
            f1["max_abs_resid_uniform_ms"], json.dumps({k: round(v, 3) for k, v in f1["resid_mix_ms"].items()})))
    L.append("per-n: " + json.dumps({n: {"c": "%.3e" % v["c_ms_per_token"], "maxres": round(v["max_abs_resid_ms"], 3)} for n, v in pern.items()}))
    L.append("plan context: " + json.dumps({k: round(v, 1) for k, v in pc.items()}))
    L += ["", "| d | GTASK15 | F1 | interp |", "|---|---|---|---|"]
    for d, r in repro.items():
        L.append(f"| {d} | {r['gtask15']:.3f} | {r.get('F1', float('nan')):.3f} | {r.get('interp', float('nan')):.3f} |")
    a.md.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
