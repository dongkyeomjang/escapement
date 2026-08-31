#!/usr/bin/env python3
"""Post-hoc: the same null gap formed at the aggregation the verdicts used.

NOT PREREGISTERED. The preregistered analysis lives in ``null_channel.py`` and
its numbers are the ones this task reports as its result. This file exists
because the preregistration compared two things that are not aggregated alike,
and saying so is better than leaving the mismatch implicit.

A treated cell in TASK35/36/40 forms its ratio from sums over three blocks:

    ratio = (arm_b0 + arm_b1 + arm_b2) / (BASE_b0 + BASE_b1 + BASE_b2)

The preregistered null forms its ratio from single runs. Summing three runs
averages run-to-run noise down, so a single-run null gap is the wrong scale to
hold against a tolerance that gates three-block sums.

This recomputes the null gap between two *disjoint* three-run aggregates, which
is the shape a treated cell actually has. From ten repeats there are
C(10,3) * C(7,3) / 2 = 2100 such pairs, enumerated exactly -- no sampling, no
seed. The quantile convention is the preregistered one, imported rather than
restated.

It changes no verdict and revises no tolerance.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from null_channel import (ARM, CHANNEL_FLOOR, analyse, classify,  # noqa: E402
                          quantile)


def aggregate_pairs(valid: list[dict]) -> list[dict]:
    """Every unordered pair of disjoint 3-run aggregates."""
    idx = list(range(len(valid)))
    pairs = []
    seen = set()
    for left in itertools.combinations(idx, 3):
        rest = [i for i in idx if i not in left]
        for right in itertools.combinations(rest, 3):
            key = frozenset((left, right))
            if key in seen:
                continue
            seen.add(key)
            la = sum(valid[i]["a_prime_s"] for i in left)
            lb = sum(valid[i]["b_s"] for i in left)
            ra = sum(valid[i]["a_prime_s"] for i in right)
            rb = sum(valid[i]["b_s"] for i in right)
            pairs.append({"left": [valid[i]["rep"] for i in left],
                          "right": [valid[i]["rep"] for i in right],
                          "a_ratio": la / ra, "b_ratio": lb / rb,
                          "gap": abs(la / ra - lb / rb)})
    return pairs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--sessions", default="6,8")
    p.add_argument("--reps", default="0,1,2,3,4,5,6,7,8,9")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    reps = [int(x) for x in args.reps.split(",")]
    out = []
    print("사후 진단 — 선등록 판정 아님. 선등록 결과는 null_channel.py에 있다.\n")
    for n in (int(x) for x in args.sessions.split(",")):
        r = analyse(args.run, n, reps)
        if r["status"] != "VALID":
            print(f"N={n}: {r['status']} — 건너뜀")
            continue
        valid = [x for x in r["repeats"] if x["valid"]]
        pairs = aggregate_pairs(valid)
        gaps = [x["gap"] for x in pairs]
        q95 = quantile(gaps, 0.95)
        cls, text = classify(q95, r["tau_null"])
        row = {"N": n, "pair_count": len(pairs),
               "gap_min": min(gaps), "gap_median": statistics.median(gaps),
               "gap_q95": q95, "gap_max": max(gaps),
               "tau_null": r["tau_null"], "class": cls, "class_text": text,
               "prereg_gap_median": r["gap_median"],
               "prereg_gap_q95": r["gap_q95"], "prereg_class": r["class"]}
        out.append(row)
        print(f"{'=' * 74}\nN = {n}   3-run 합 대 3-run 합, 서로소 {len(pairs)}쌍\n{'=' * 74}")
        print(f"  최솟값 {row['gap_min']:.4f}   중앙값 {row['gap_median']:.4f}   "
              f"95 분위 {q95:.4f}   최댓값 {row['gap_max']:.4f}")
        print(f"  선등록(1-run 대 1-run, 45쌍): 중앙값 {r['gap_median']:.4f}  "
              f"95 분위 {r['gap_q95']:.4f}  → {r['class']}")
        print(f"  τ_null({n}) = {r['tau_null']:.4f}  "
              f"{'≥' if r['tau_null'] >= q95 else '<'} 95 분위  → {cls}: {text}")
        print(f"  하한 0.02 {'≥' if CHANNEL_FLOOR >= q95 else '<'} 95 분위\n")
    if args.output:
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"산출: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
