#!/usr/bin/env python3
"""Break the two-channel comparisons out by repetition instead of pooling them.

Every configuration comparison in this programme reports one number per (N,
arm): the three repetition blocks are summed and the ratio is taken once, at
the top. That is the preregistered statistic and it stays the statistic. What
is missing is the view underneath it -- what each block contributed -- which
this file writes out for the two comparisons that carry a judgement and for
the batch_size saturation grid.

Nothing here judges anything. Per-block ratios are not the preregistered unit,
their spread is not an uncertainty, and no interval is computed from them:
TASK50 measured the no-treatment repeat distribution precisely so that block
scatter would not be read as one.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

import batch_curve as BC  # noqa: E402
from config_device import aggregate  # noqa: E402


def config_rows(run: Path, baseline: str, arms: list[str], ns: list[int],
                blocks: list[int]) -> list[dict]:
    """Per-block channel A' and B for each arm, against the same block's base."""
    out = []
    for n in ns:
        base = aggregate(run, baseline, n, blocks)
        base_by_block = {b["block"]: b for b in base["per_block"]}
        for arm in arms:
            agg = aggregate(run, arm, n, blocks)
            for blk in agg["per_block"]:
                bb = base_by_block[blk["block"]]
                ra = blk["a_prime_s"] / bb["a_prime_s"]
                rb = blk["b_s"] / bb["b_s"]
                out.append({
                    "N": n, "arm": arm, "block": blk["block"],
                    "base_a_prime_s": bb["a_prime_s"], "base_b_s": bb["b_s"],
                    "arm_a_prime_s": blk["a_prime_s"], "arm_b_s": blk["b_s"],
                    "arm_decode_s": blk["decode_s"], "arm_prefill_s": blk["prefill_s"],
                    "a_prime_ratio": ra, "b_ratio": rb,
                    "channel_gap": abs(ra - rb),
                    "X_a_prime": 1.0 - ra, "X_b": 1.0 - rb,
                })
            out.append({
                "N": n, "arm": arm, "block": "합산",
                "base_a_prime_s": base["a_prime_s"], "base_b_s": base["b_s"],
                "arm_a_prime_s": agg["a_prime_s"], "arm_b_s": agg["b_s"],
                "arm_decode_s": agg["decode_s"], "arm_prefill_s": agg["prefill_s"],
                "a_prime_ratio": agg["a_prime_s"] / base["a_prime_s"],
                "b_ratio": agg["b_s"] / base["b_s"],
                "channel_gap": abs(agg["a_prime_s"] / base["a_prime_s"]
                                   - agg["b_s"] / base["b_s"]),
                "X_a_prime": 1.0 - agg["a_prime_s"] / base["a_prime_s"],
                "X_b": 1.0 - agg["b_s"] / base["b_s"],
            })
    return out


def saturation_rows(run: Path, baseline: str, arms: list[str], ns: list[int],
                    blocks: list[int]) -> list[dict]:
    """Per-block channel A' and B across the batch_size grid."""
    out = []
    for n in ns:
        for blk in blocks:
            base = BC.cell(run, baseline, n, blk)
            if base is None:
                continue
            for arm in arms:
                c = BC.cell(run, arm, n, blk)
                if c is None:
                    continue
                out.append({
                    "N": n, "arm": arm, "block": blk,
                    "base_a_prime_s": base["a_prime_s"], "base_b_s": base["b_s"],
                    "arm_a_prime_s": c["a_prime_s"], "arm_b_s": c["b_s"],
                    "a_prime_ratio": c["a_prime_s"] / base["a_prime_s"],
                    "b_ratio": c["b_s"] / base["b_s"],
                    "reuse": c["reuse"], "resume": c["resume"],
                    "top_bucket": c["top_bucket"], "top_share": c["top_share"],
                })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("config", "saturation"), default="config")
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--baseline", default="BASE")
    p.add_argument("--arms", default="BATCHONLY,TUNED")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    ns = [int(x) for x in args.sessions.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    arms = args.arms.split(",")
    rows = (config_rows if args.mode == "config" else saturation_rows)(
        args.run, args.baseline, arms, ns, blocks)

    if args.mode == "config":
        print(f"{'N':>3} {'arm':<10} {'반복':>4} {'A′ 기준(s)':>10} {'A′ arm(s)':>10} "
              f"{'A′ 비':>8} {'B 비':>8} {'채널 차':>8} {'X(A′)':>8} {'X(B)':>8}")
        for r in rows:
            print(f"{r['N']:>3} {r['arm']:<10} {str(r['block']):>4} "
                  f"{r['base_a_prime_s']:>10.3f} {r['arm_a_prime_s']:>10.3f} "
                  f"{r['a_prime_ratio']:>8.4f} {r['b_ratio']:>8.4f} "
                  f"{r['channel_gap']:>8.4f} {100*r['X_a_prime']:>7.2f}% "
                  f"{100*r['X_b']:>7.2f}%")
    else:
        print(f"{'N':>3} {'arm':<5} {'반복':>4} {'A′ 비':>8} {'B 비':>8} "
              f"{'재사용':>8} {'최상위 bucket':>13} {'선택 비중':>9}")
        for r in rows:
            print(f"{r['N']:>3} {r['arm']:<5} {r['block']:>4} "
                  f"{r['a_prime_ratio']:>8.4f} {r['b_ratio']:>8.4f} "
                  f"{r['reuse']:>4}/{r['resume']:<3} {r['top_bucket']:>13} "
                  f"{100*r['top_share']:>8.1f}%")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
