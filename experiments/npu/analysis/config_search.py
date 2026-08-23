#!/usr/bin/env python3
"""Pick a compile configuration from workload statistics alone.

Two things are fixed when the model is compiled and cannot be changed at run
time: which decode batch widths exist, and how many sequences the KV pool
holds. TASK33 found that most of the remaining headroom is coordination --
something no per-session runtime policy can reach -- and a compile
configuration is coordination decided once, in advance, for everybody.

Configurations are scored by device time on the workload, and the cost of
compiling each one is carried alongside so a choice can be made against a
budget rather than in the abstract. Exploration and evaluation seeds are kept
apart: TASK27 and TASK33 both produced several percent of imaginary gain from
tuning and scoring on the same plans.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from continuum.sim import SimConfig, simulate  # noqa: E402
import foresight as F  # noqa: E402

#: TASK10's compile cost model, confirmed to a third point in TASK23:
#: time ~ 42.3 + 61.33 * (compiled models), size ~ 8.276 + 0.806 * (buckets) GiB.
COMPILE_TIME_INTERCEPT_S = 42.3
COMPILE_TIME_PER_MODEL_S = 61.33
ARTIFACT_BASE_GIB = 8.276
ARTIFACT_PER_BUCKET_GIB = 0.806


def compile_cost(buckets: tuple[int, ...]) -> tuple[float, float]:
    """(seconds, GiB) predicted for compiling this bucket set."""
    models = len(buckets) + 1          # decoders plus the prefill graph
    return (COMPILE_TIME_INTERCEPT_S + COMPILE_TIME_PER_MODEL_S * models,
            ARTIFACT_BASE_GIB + ARTIFACT_PER_BUCKET_GIB * len(buckets))


def descriptor_for(base, buckets: tuple[int, ...], batch_size: int):
    """A descriptor for a configuration that was never compiled.

    Step costs for widths this substrate has not measured are interpolated
    between the ones it has, and extrapolated beyond them from the outermost
    pair. Anything computed from an unmeasured width is a model twice over.

    ``batch_size`` sets the KV pool: TASK08 established
    ``kvcache_num_blocks = batch_size`` for eager attention, so it is the outer
    slot count and the scheduler's admission ceiling at once.
    """
    fixed = dict(base.step_cost_model.fixed_s_by_bucket)
    known = sorted(fixed)
    for b in buckets:
        if b in fixed:
            continue
        lo = max((x for x in known if x < b), default=None)
        hi = min((x for x in known if x > b), default=None)
        if lo is None:
            lo, hi = known[0], known[1]
        elif hi is None:
            lo, hi = known[-2], known[-1]
        fixed[b] = fixed[lo] + (b - lo) / (hi - lo) * (fixed[hi] - fixed[lo])
    return replace(
        base,
        bucket_sizes=tuple(sorted(buckets)),
        step_cost_model=replace(base.step_cost_model, fixed_s_by_bucket=fixed),
        outer_slot_count=batch_size,
        kv_pool_tokens=batch_size * base.outer_slot_tokens,
    )


def score(descriptor, cells, max_running: int) -> float:
    return sum(simulate(descriptor, F.plan(*c),
                        SimConfig(max_running_requests=max_running)).busy_s
               for c in cells)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gap", default="toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60")
    p.add_argument("--explore-seeds", default="20260910,20260921,20260932")
    p.add_argument("--eval-seeds", default="20260943,20260954,20260965")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--max-buckets", type=int, default=6)
    p.add_argument("--compile-budget-s", type=float, default=1800.0)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    print(f"gap 법칙: {F.set_gap(args.gap)}")
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D

    explore = [int(x) for x in args.explore_seeds.split(",")]
    evals = [int(x) for x in args.eval_seeds.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    ns = [int(x) for x in args.sessions.split(",")]

    # The space: bucket sets that always contain 1 (a lone decoder must run)
    # and the top width, over batch sizes that can hold the offered load.
    candidates = []
    for batch in (8, 10, 12, 16):
        widths = [w for w in range(2, batch + 1)]
        import itertools
        for k in range(0, args.max_buckets):
            for mid in itertools.combinations(widths[:-1], k):
                buckets = (1,) + tuple(mid) + (batch,)
                if len(set(buckets)) != len(buckets):
                    continue
                t, g = compile_cost(tuple(sorted(set(buckets))))
                if t > args.compile_budget_s:
                    continue
                candidates.append((tuple(sorted(set(buckets))), batch))
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    print(f"구성 후보 {len(uniq)}개 "
          f"(bucket 최대 {args.max_buckets}개, compile 예산 {args.compile_budget_s:.0f} s)")

    base_desc = descriptor_for(D, (1, 2, 4, 8), 8)
    results = []
    for buckets, batch in uniq:
        d = descriptor_for(D, buckets, batch)
        row = {"buckets": list(buckets), "batch_size": batch}
        t, g = compile_cost(buckets)
        row["compile_s"], row["artifact_gib"] = t, g
        for tag, seeds in (("explore", explore), ("eval", evals)):
            tot = base = 0.0
            per_n = {}
            for n in ns:
                cells = [(n, b, s) for s in seeds for b in blocks]
                # A configuration cannot admit more than its pool holds.
                v = score(d, cells, max_running=batch)
                bv = score(base_desc, cells, max_running=8)
                per_n[n] = v / bv
                tot += v
                base += bv
            row[f"{tag}_ratio"] = tot / base
            row[f"{tag}_per_n"] = per_n
        results.append(row)

    results.sort(key=lambda r: r["explore_ratio"])
    print(f"\n=== 탐색 seed 기준 상위 12 구성 (ratio < 1 이 개선) ===")
    print(f"{'buckets':<26} {'batch':>6} {'탐색 ratio':>11} {'평가 ratio':>11} "
          f"{'compile(s)':>11} {'artifact(GiB)':>13}")
    for r in results[:12]:
        print(f"{str(tuple(r['buckets'])):<26} {r['batch_size']:>6} {r['explore_ratio']:>11.4f} "
              f"{r['eval_ratio']:>11.4f} {r['compile_s']:>11.0f} {r['artifact_gib']:>13.2f}")

    best = results[0]
    print(f"\n탐색 seed 최적: buckets={tuple(best['buckets'])} batch_size={best['batch_size']}")
    print(f"  평가 seed ratio {best['eval_ratio']:.4f} "
          f"(절감 {100*(1-best['eval_ratio']):+.2f}%)")
    print(f"  N별 평가 ratio: " +
          "  ".join(f"N={n} {v:.4f}" for n, v in best["eval_per_n"].items()))
    print(f"  예상 compile {best['compile_s']:.0f} s, artifact {best['artifact_gib']:.2f} GiB")

    if args.output:
        args.output.write_text(json.dumps(
            {"candidates": len(uniq), "results": results}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
