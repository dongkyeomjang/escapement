#!/usr/bin/env python3
"""Which workload statistic would change the compile configuration.

A configuration chosen from measurements is only as stable as the measurements
are. This asks the operational question directly: perturb one property of the
workload, re-run the selection, and see whether the answer moves. What comes
out is a list of things worth re-measuring before recompiling -- and, just as
usefully, a list of things that are not.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from config_search import compile_cost, descriptor_for, score  # noqa: E402
import foresight as F  # noqa: E402


def best_config(descriptor_base, cells, candidates, max_running_of):
    best = None
    for buckets, batch in candidates:
        d = descriptor_for(descriptor_base, buckets, batch)
        v = score(d, cells, max_running=max_running_of(batch))
        if best is None or v < best[2]:
            best = (buckets, batch, v)
    return best


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gap", default="toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60")
    p.add_argument("--seeds", default="20260910,20260921,20260932")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D

    seeds = [int(x) for x in args.seeds.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]

    # A deliberately small, readable candidate set: the axes that mattered.
    CANDS = [((1, 2, 4, 8), 8), ((1, 4, 6, 8), 8), ((1, 2, 4, 6, 8), 8),
             ((1, 2, 4, 8, 10), 10), ((1, 4, 6, 8, 10), 10),
             ((1, 2, 4, 8, 12), 12), ((1, 4, 6, 8, 10, 12), 12),
             ((1, 2, 4, 8, 16), 16), ((1, 4, 8, 16), 16),
             ((1, 4, 6, 8, 10, 16), 16)]

    SCENARIOS = [
        ("기준 (현실 trace, N 6/8/10)", args.gap, (6, 8, 10)),
        ("부하가 작다 (N 4/6)", args.gap, (4, 6)),
        ("부하가 크다 (N 10/12/16)", args.gap, (10, 12, 16)),
        ("gap이 합성 uniform:1:5", "uniform:1:5", (6, 8, 10)),
        ("gap 꼬리 절단 (cap 5 s)",
         args.gap.rsplit(":", 1)[0] + ":5", (6, 8, 10)),
        ("gap 꼬리 확장 (cap 300 s)",
         args.gap.rsplit(":", 1)[0] + ":300", (6, 8, 10)),
    ]

    rows = []
    print(f"{'시나리오':<28} {'선택 buckets':<24} {'batch':>6} {'기준 구성 대비':>14}")
    ref = None
    for name, gap, ns in SCENARIOS:
        F.set_gap(gap)
        cells = [(n, b, s) for s in seeds for n in ns for b in blocks]
        buckets, batch, v = best_config(D, cells, CANDS, lambda b: b)
        # Score the reference configuration under the same scenario.
        ref_d = descriptor_for(D, (1, 4, 6, 8, 10, 16), 16)
        ref_v = score(ref_d, cells, max_running=16)
        rows.append({"scenario": name, "gap": gap, "sessions": list(ns),
                     "buckets": list(buckets), "batch_size": batch,
                     "best_busy_s": v, "reference_busy_s": ref_v,
                     "reference_penalty": ref_v / v - 1})
        if ref is None:
            ref = (buckets, batch)
        same = "동일" if (buckets, batch) == ref else "**변경**"
        print(f"{name:<28} {str(buckets):<24} {batch:>6} {same:>14}"
              f"   기준 구성 손해 {100*(ref_v/v-1):+.2f}%")

    print("\n선택을 바꾸는 통계:")
    for r in rows[1:]:
        if (tuple(r["buckets"]), r["batch_size"]) != ref:
            print(f"  - {r['scenario']}: {tuple(r['buckets'])} batch={r['batch_size']}"
                  f" (기준 구성을 쓰면 {100*r['reference_penalty']:+.2f}%)")
    if all((tuple(r["buckets"]), r["batch_size"]) == ref for r in rows[1:]):
        print("  없음 — 시험한 모든 교란에서 같은 구성이 선택된다")

    if args.output:
        args.output.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
