#!/usr/bin/env python3
"""G-05 task E: stationarity, method docs/research/gpu/GPU_STATIONARITY_METHOD.md
(commit f61b4fd, NPU STATIONARITY_REANALYSIS.md sections 2-4).

usage: stationarity.py --run-dir <abs> --out <abs json>
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations, permutations
import json
from math import comb
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "obs"))
from parse_obs import parse  # noqa: E402

CELLS = [(n, c) for n in (20, 22, 24) for c in ("BASE", "POOL", "POOL+GRID")] + [(26, "BASE"), (26, "POOL")]


def tvd(a, b):
    ta, tb = sum(a.values()), sum(b.values())
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in set(a) | set(b))


def halves(run: Path) -> dict:
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    mid = w0 + 60.0
    log = (run / "server.log").read_text(errors="replace")
    details = "enable_prompt_tokens_details=True" in log or "'enable_prompt_tokens_details': True" in log \
        or "enable_prompt_tokens_details: True" in log
    ev = parse(run / "server.log")
    first = {}
    for e in ev:
        if e["kind"] == "ALLOC":
            first.setdefault(e["req"], e["line"])
    sid = {}
    for s in first:
        parts = s.split("-")
        for k in range(2, len(parts)):
            sid.setdefault("-".join(parts[:k]), s)
    inwin = [r for r in rows if w0 <= r["sent_s"] < w1]
    lines = [first[sid[r["request_id"]]] for r in inwin]
    lo, hi = min(lines), max(lines)
    split = min(first[sid[r["request_id"]]] for r in inwin if r["sent_s"] >= mid)
    hd = {"pre": Counter(), "post": Counter()}
    hr = {"pre": Counter(), "post": Counter()}
    allocs = 0
    for e in ev:
        if e["kind"] == "ALLOC":
            allocs += 1
        elif e["kind"] == "STEP":
            if lo <= e["line"] <= hi:
                part = "pre" if e["line"] < split else "post"
                d = e["reqs"] if e["maxq"] == 1 else max(0, e["reqs"] - max(1, allocs))
                if d >= 1:
                    hd[part][d] += 1
                hr[part][e["reqs"]] += 1
            allocs = 0
    reuse = {}
    for part, cond in (("pre", lambda r: r["sent_s"] < mid), ("post", lambda r: r["sent_s"] >= mid)):
        later = [r for r in inwin if r["turn"] > 0 and cond(r)]
        cached = [(r["cached_tokens"] if r["cached_tokens"] is not None else (0 if details else None))
                  for r in later]
        if any(c is None for c in cached):
            raise SystemExit(f"cached unknown in {run}")
        reuse[part] = sum(1 for c in cached if c > 0) / len(later)
    return {"h_decode": hd, "h_reqs": hr, "reuse": reuse}


def midrank(x, ref):
    return (sum(1 for y in ref if y < x) + 0.5 * sum(1 for y in ref if y == x)) / len(ref)


def cell_stats(H: list[dict], hkey: str) -> dict:
    W = [tvd(h[hkey]["pre"], h[hkey]["post"]) for h in H]
    B = [tvd(H[i][hkey][p], H[j][hkey][p]) for i, j in combinations(range(len(H)), 2) for p in ("pre", "post")]
    dl = [h["reuse"]["post"] - h["reuse"]["pre"] for h in H]
    D = [H[j]["reuse"][p] - H[i]["reuse"][p] for i, j in permutations(range(len(H)), 2) for p in ("pre", "post")]
    absD = [abs(x) for x in D]
    return {"median_W": statistics.median(W), "median_B": statistics.median(B),
            "q_h": statistics.mean(midrank(w, B) for w in W),
            "median_delta": statistics.median(dl), "median_absD": statistics.median(absD),
            "q_delta": statistics.mean(midrank(x, D) for x in dl),
            "q_absdelta": statistics.mean(midrank(abs(x), absD) for x in dl)}


def sign_p(k, n):
    return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n


def classify(vals, med_cond, frac_cond, n):
    k = sum(1 for v in vals if frac_cond(v))
    p = sign_p(k, n)
    a, b = med_cond(statistics.median(vals)), p < 0.05
    return {"median": statistics.median(vals), "k": k, "n": n, "p": p,
            "class": "NONSTATIONARY" if a and b else ("WEAK_EVIDENCE" if a or b else "NOT_NONSTATIONARY")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    out = {"cells": {}, "summary": {}}
    per = {}
    for n, c in CELLS:
        H = [halves(a.run_dir / f"n{n}.{c}.r{r}") for r in range(5)]
        per[(n, c)] = H
        out["cells"][f"{n}/{c}"] = {hk: cell_stats(H, hk) for hk in ("h_decode", "h_reqs")}
    for label, keys in (("all11", CELLS), ("conf9", CELLS[:9])):
        s = {}
        for hk in ("h_decode", "h_reqs"):
            s[f"h/{hk}"] = classify([out["cells"][f"{n}/{c}"][hk]["q_h"] for n, c in keys],
                                    lambda m: m > 0.75, lambda v: v > 0.5, len(keys))
        s["reuse_drop"] = classify([out["cells"][f"{n}/{c}"]["h_decode"]["q_delta"] for n, c in keys],
                                   lambda m: m < 0.25, lambda v: v < 0.5, len(keys))
        s["q_absdelta_median"] = statistics.median(out["cells"][f"{n}/{c}"]["h_decode"]["q_absdelta"]
                                                   for n, c in keys)
        out["summary"][label] = s
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for k, v in out["cells"].items():
        d, r = v["h_decode"], v["h_reqs"]
        print(f"{k:12s} W {d['median_W']:.3f} B {d['median_B']:.3f} q_h {d['q_h']:.3f} | reqs q_h {r['q_h']:.3f}"
              f" | dReuse {d['median_delta']:+.3f} |D| {d['median_absD']:.3f} q_d {d['q_delta']:.3f} q_|d| {d['q_absdelta']:.3f}")
    print(json.dumps(out["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
