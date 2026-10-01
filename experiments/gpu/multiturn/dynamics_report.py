#!/usr/bin/env python3
"""G-05 task C (report only): queue dynamics, observed vs sim LRU variants,
per cell, and the cross-cell Spearman correlation between each quantity's
sim - observed difference and the reuse prediction error.

usage: dynamics_report.py --obs <abs obs.json> --sim <abs sim.json>
                          --timescale <abs timescale_report.json> --out <abs json>
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from step_classes import step_class  # noqa: E402

QTY = ("qlen_mean", "qlen_p90", "wait_med", "wait_p90", "ttft_med", "idle_med", "idle_mean",
       "others_med", "others_mean", "others_per_idle_s", "step_full_med", "step_wall_over_price")


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def summarize(qlen, reqs, steps_full, wall_over_price) -> dict:
    later = [r for r in reqs if r.get("turn", 1) > 0]
    idle = [r["idle_s"] for r in later if r.get("idle_s") is not None]
    oth = [r["others_alloc"] for r in later if r.get("others_alloc") is not None]
    rate = [r["others_alloc"] / r["idle_s"] for r in later
            if r.get("others_alloc") is not None and r.get("idle_s")]
    return {"qlen_mean": statistics.mean(qlen), "qlen_p90": q(qlen, 0.9),
            "wait_med": statistics.median(r["wait_s"] for r in later),
            "wait_p90": q([r["wait_s"] for r in later], 0.9),
            "ttft_med": statistics.median(r["ttft_s"] for r in later if r.get("ttft_s") is not None),
            "idle_med": statistics.median(idle), "idle_mean": statistics.mean(idle),
            "others_med": statistics.median(oth), "others_mean": statistics.mean(oth),
            "others_per_idle_s": statistics.median(rate),
            "step_full_med": statistics.median(steps_full) if steps_full else None,
            "step_wall_over_price": wall_over_price}


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("obs", "sim", "timescale", "out"):
        ap.add_argument(f"--{k}", required=True, type=Path)
    a = ap.parse_args()
    obs = json.loads(a.obs.read_text())
    sim = json.loads(a.sim.read_text())
    ts = json.loads(a.timescale.read_text())
    cells = {}
    acc = defaultdict(lambda: {"qlen": [], "reqs": [], "full": [], "dt": 0.0, "price": 0.0})
    for L in obs:
        n, c, _ = L["run"].split(".")
        k = f"{n[1:]}/{c}"
        A = acc[k]
        A["qlen"] += L["queue_len"]
        A["reqs"] += L["requests"]
        st = L["steps"]
        for i, s in enumerate(st):
            if i + 1 < len(st) and st[i + 1]["dt"] is not None:
                A["dt"] += st[i + 1]["dt"]
                A["price"] += s["lo"]
                if step_class(s["mode"], s["d"], s["p"]) == "DEC_FULL":
                    A["full"].append(st[i + 1]["dt"])
    cells["observed"] = {k: summarize(A["qlen"], A["reqs"], A["full"], A["dt"] / A["price"])
                         for k, A in acc.items()}
    for v in sim["meta"]["variants"]:
        acc = defaultdict(lambda: {"qlen": [], "reqs": [], "full": [], "wall": 0.0, "price": 0.0})
        for r in sim["runs"]:
            if r["variant"] != v:
                continue
            A = acc[f"{r['n']}/{r['config']}"]
            A["qlen"] += r["qlen"]
            A["reqs"] += r["per_req"]
            A["wall"] += r["wall_window_s"]
            A["price"] += r["price_per_turn_s"] * r["requests_in_window"]
            f = r["step_ms_by_class"].get("DEC_FULL")
            if f:
                A["full"] += [f[0]] * f[1]
        cells[v] = {k: summarize(A["qlen"], A["reqs"], A["full"], A["wall"] / A["price"])
                    for k, A in acc.items()}
    keys = sorted(cells["observed"], key=lambda s: (int(s.split("/")[0]), s))
    corr = {}
    pooled = defaultdict(lambda: ([], []))
    for v in sim["meta"]["variants"]:
        err = [ts["variants"][v]["reuse_minus_obs"][k] for k in keys]
        corr[v] = {}
        for f in QTY:
            d = [cells[v][k][f] - cells["observed"][k][f] for k in keys]
            corr[v][f] = spearman(d, err)
            pooled[f][0].extend(d)
            pooled[f][1].extend(err)
    corr["pooled_variants"] = {f: spearman(*pooled[f]) for f in QTY}
    out = {"cells": cells, "spearman_vs_reuse_error": corr, "keys": keys}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for f in QTY:
        print(f, " ".join(f"{k}:" + "/".join(
            f"{cells[v][k][f]:.3g}" if cells[v][k][f] is not None else "-"
            for v in ("observed", *sim["meta"]["variants"])) for k in keys))
    print("spearman", json.dumps({v: {f: (round(x, 2) if x is not None else None) for f, x in c.items()}
                                  for v, c in corr.items()}, indent=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
