#!/usr/bin/env python3
"""G-10 post-hoc diagnosis (not a preregistered judgment): float32-aware overlap check.

[GEXEC] s is cudaEventElapsedTime from the process reference event, a float32
in ms. Past 2**17 ms its spacing is 0.015625 ms, larger than the
preregistered overlap tolerance 0.01 ms, so contiguous steps can look
"overlapping" by one quantum. This script recounts overlaps with tolerance
0.01 ms + float32 spacing at s (prep and run are short intervals, unaffected)
and reruns the unchanged judge (judge_b or judge_c) with that direct_ok.
The preregistered verdict files are not touched.

usage: posthoc_f32.py --judge b|c --run-dir <abs> --out <abs json> [--jobs N]
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "multiturn"))

import exec_measure as X  # noqa: E402

TOL = 0.01


def recount(run: Path) -> dict:
    steps, _, _ = X.window_steps(run)
    gx = X.gexec(run / "server.log")
    strict = f32 = 0
    worst = 0.0
    first_s = None
    pe = None
    for e, _, _ in steps:
        x = gx.get(X._tkey(e["t"]))
        if x is None:
            pe = None
            continue
        if pe is not None:
            gap = pe - x["s"]
            if x["s"] < pe - TOL:          # same comparison as exec_measure
                strict += 1
                first_s = x["s"] if first_s is None else first_s
            if gap > TOL + float(np.spacing(np.float32(x["s"]))):
                f32 += 1
            worst = max(worst, gap)
        pe = x["s"] + x["prep"] + x["run"]
    return {"overlaps_strict": strict, "overlaps_f32": f32, "max_overlap_ms": worst,
            "first_strict_overlap_s_ms": first_s}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=("b", "c"), required=True)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    J = importlib.import_module(f"judge_{a.judge}")
    orig = J.load
    counts: dict = {}

    def load(d: Path, *args, **kw):
        L = orig(d, *args, **kw)
        c = recount(d)
        counts[d.name] = c
        c["overlaps_exec_measure"] = L["x"]["overlaps"]   # must equal overlaps_strict
        L["direct_ok_strict"] = L["direct_ok"]
        L["direct_ok"] = (L["x"]["direct_complete"] and c["overlaps_f32"] == 0
                          and L["x"]["nonpositive"] == 0)
        return L

    J.load = load
    tmp = a.out.with_suffix(".judge.json")
    sys.argv = [f"judge_{a.judge}.py", "--run-dir", str(a.run_dir), "--out", str(tmp)]
    if a.judge == "b":
        sys.argv += ["--jobs", str(a.jobs)]
    rc = J.main()
    res = json.loads(tmp.read_text())
    tmp.unlink()
    out = {"status": "POST-HOC DIAGNOSIS (not preregistered; preregistered verdict unchanged)",
           "rule": "overlap if prev_end - s > 0.01 ms + float32 spacing(s)",
           "overlap_counts": counts, "judge_output": res}
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: (v["overlaps_strict"], v["overlaps_f32"], round(v["max_overlap_ms"], 4),
                          v["first_strict_overlap_s_ms"]) for k, v in sorted(counts.items())}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
