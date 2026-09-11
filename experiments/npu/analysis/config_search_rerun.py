#!/usr/bin/env python3
"""Re-run the compile-configuration search and keep every candidate's ledger.

COMPILE_CONFIG_PREREG.md records that 2,077 candidates were ranked on
exploration seeds and the winner scored on evaluation seeds, but neither the
command that produced the ranking nor the per-candidate results were kept, so
the claim that the chosen configuration was the search minimum could not be
checked independently. This script repeats that search and writes the ledger
that was missing.

Nothing about the model is changed. Scoring goes through ``config_search``'s own
``compile_cost``, ``descriptor_for`` and ``score``, and ratios are accumulated
in the same order ``config_search.main`` uses, so a deterministic simulator
must reproduce its floats bit for bit. Only the enumeration is written out
again, from the preregistration's wording rather than from the committed loop:
the committed loop takes ``--max-buckets`` as a limit on the *middle* buckets
plus one, so its default of 6 admits seven-bucket sets. Both counts are
reported.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_search import compile_cost, descriptor_for, score  # noqa: E402
import foresight as F  # noqa: E402

#: What the preregistration recorded (COMPILE_CONFIG_PREREG.md, TASK34).
RECORDED_COUNT = 2077
RECORDED_CHOICE = ((1, 4, 6, 8, 10, 16), 16)
RECORDED_EVAL_RATIO = 0.9066
RECORDED_ATTRIBUTION = {           # eval ratios of the attribution table
    ((1, 2, 4, 8, 16), 16): 0.9279,
    ((1, 4, 6, 8), 8): 0.9929,
    ((1, 2, 4, 8), 8): 1.0000,
}
BASELINE = ((1, 2, 4, 8), 8)
BATCH_SIZES = (8, 10, 12, 16)


def prereg_candidates(max_total_buckets: int, budget_s: float):
    """The space as the preregistration words it.

    Every set contains 1 and ``batch_size``; the rest are integers strictly
    between them; at most ``max_total_buckets`` in all; predicted compile time
    within budget. Order: batch size, then number of middle buckets, then
    lexicographic -- the order the committed loop visits them in.
    """
    out = []
    for batch in BATCH_SIZES:
        middle = range(2, batch)
        for k in range(0, max_total_buckets - 1):
            for mid in itertools.combinations(middle, k):
                buckets = (1,) + mid + (batch,)
                if compile_cost(buckets)[0] <= budget_s:
                    out.append((buckets, batch))
    return out


def committed_loop_candidates(max_buckets: int, budget_s: float):
    """``config_search.main``'s enumeration, restated only to count it."""
    seen, out = set(), []
    for batch in BATCH_SIZES:
        widths = list(range(2, batch + 1))
        for k in range(0, max_buckets):
            for mid in itertools.combinations(widths[:-1], k):
                buckets = (1,) + tuple(mid) + (batch,)
                if len(set(buckets)) != len(buckets):
                    continue
                key = (tuple(sorted(set(buckets))), batch)
                if compile_cost(key[0])[0] > budget_s or key in seen:
                    continue
                seen.add(key)
                out.append(key)
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gap", default="toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60")
    p.add_argument("--explore-seeds", default="20260910,20260921,20260932")
    p.add_argument("--eval-seeds", default="20260943,20260954,20260965")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--max-total-buckets", type=int, default=6)
    p.add_argument("--compile-budget-s", type=float, default=1800.0)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()

    started = dt.datetime.now().astimezone()
    t0 = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    gap_desc = F.set_gap(args.gap)
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D

    explore = [int(x) for x in args.explore_seeds.split(",")]
    evals = [int(x) for x in args.eval_seeds.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    ns = [int(x) for x in args.sessions.split(",")]

    cands = prereg_candidates(args.max_total_buckets, args.compile_budget_s)
    committed_default = committed_loop_candidates(6, args.compile_budget_s)
    committed_mb5 = committed_loop_candidates(5, args.compile_budget_s)
    counts = {
        "prereg_definition": len(cands),
        "recorded": RECORDED_COUNT,
        "committed_loop_default_max_buckets_6": len(committed_default),
        "committed_loop_max_buckets_5": len(committed_mb5),
        "prereg_equals_committed_mb5_as_ordered_list": cands == committed_mb5,
        "per_batch_size": {b: sum(1 for _, x in cands if x == b) for b in BATCH_SIZES},
        "max_predicted_compile_s": max(compile_cost(c[0])[0] for c in cands),
    }
    print(f"gap 법칙: {gap_desc}")
    print(f"후보 수: 선등록 정의 {len(cands)} / 기록 {RECORDED_COUNT} / "
          f"commit된 loop 기본값(--max-buckets 6) {len(committed_default)} / "
          f"--max-buckets 5 {len(committed_mb5)}")

    # The baseline never changes, so it is simulated once per cell group; the
    # determinism check (a second process, and config_search.py itself, which
    # re-simulates it for every candidate) covers the assumption.
    base_desc = descriptor_for(D, *BASELINE)
    cells_of = {tag: {n: [(n, b, s) for s in seeds for b in blocks] for n in ns}
                for tag, seeds in (("explore", explore), ("eval", evals))}
    base_busy = {tag: {n: score(base_desc, cells_of[tag][n], max_running=8)
                       for n in ns} for tag in cells_of}

    rows = []
    for idx, (buckets, batch) in enumerate(cands):
        d = descriptor_for(D, buckets, batch)
        t_s, g = compile_cost(buckets)
        row = {"enum_index": idx, "buckets": list(buckets), "batch_size": batch,
               "compile_s": t_s, "artifact_gib": g}
        for tag in ("explore", "eval"):
            tot = base = 0.0
            per_n, busy_n = {}, {}
            for n in ns:
                v = score(d, cells_of[tag][n], max_running=batch)
                bv = base_busy[tag][n]
                per_n[n] = v / bv
                busy_n[n] = v
                tot += v
                base += bv
            row[f"{tag}_busy_s"] = tot
            row[f"{tag}_base_busy_s"] = base
            row[f"{tag}_ratio"] = tot / base
            row[f"{tag}_per_n_ratio"] = per_n
            row[f"{tag}_per_n_busy_s"] = busy_n
        rows.append(row)
        if (idx + 1) % 250 == 0:
            print(f"  {idx + 1}/{len(cands)}  {time.perf_counter() - t0:.1f} s", flush=True)

    # Same ranking rule as config_search.main: stable sort on the exploration
    # ratio, so exact ties keep enumeration order.
    ranked = sorted(rows, key=lambda r: r["explore_ratio"])
    for rank, r in enumerate(ranked, 1):
        r["explore_rank"] = rank
    best = ranked[0]
    tied_min = [r for r in ranked if r["explore_ratio"] == best["explore_ratio"]]
    by_key = {(tuple(r["buckets"]), r["batch_size"]): r for r in rows}
    rec = by_key.get(RECORDED_CHOICE)

    elapsed = time.perf_counter() - t0
    finished = dt.datetime.now().astimezone()

    comparison = {
        "argmin": {"buckets": best["buckets"], "batch_size": best["batch_size"],
                   "explore_ratio": best["explore_ratio"], "eval_ratio": best["eval_ratio"]},
        "argmin_equals_recorded": (tuple(best["buckets"]), best["batch_size"]) == RECORDED_CHOICE,
        "tied_at_min": [(r["buckets"], r["batch_size"]) for r in tied_min],
        "recorded_choice_rank": rec["explore_rank"] if rec else None,
        "recorded_choice_eval_ratio": rec["eval_ratio"] if rec else None,
        "recorded_eval_ratio": RECORDED_EVAL_RATIO,
        "eval_ratio_round4_matches": (round(rec["eval_ratio"], 4) == RECORDED_EVAL_RATIO) if rec else None,
        "eval_ratio_minus_recorded": (rec["eval_ratio"] - RECORDED_EVAL_RATIO) if rec else None,
        "attribution": [
            {"buckets": list(k[0]), "batch_size": k[1], "recorded_eval_ratio": v,
             "rerun_eval_ratio": by_key[k]["eval_ratio"],
             "round4_matches": round(by_key[k]["eval_ratio"], 4) == v}
            for k, v in RECORDED_ATTRIBUTION.items()],
    }

    tracked = ["experiments/npu/analysis/config_search_rerun.py",
               "experiments/npu/analysis/config_search.py",
               "experiments/npu/analysis/foresight.py",
               "experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py",
               "src/continuum/sim/engine.py", "src/continuum/sim/cache.py",
               "src/continuum/sim/__init__.py",
               "src/continuum/workload/agentic.py", "src/continuum/workload/tools.py",
               "src/continuum/workload/paired.py"]
    gap_path = Path(args.gap.split(":", 2)[1]) if args.gap.startswith("toolmix:") else None
    meta = {
        "command": [sys.executable, *sys.argv],
        "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "elapsed_s": elapsed,
        "git_head": git("rev-parse", "HEAD"),
        "git_dirty_tracked_inputs": git("status", "--porcelain", "--", *tracked),
        "sha256": {f: sha256(REPO / f) for f in tracked},
        "gap_spec": args.gap, "gap_law": gap_desc,
        "gap_file_sha256": sha256(gap_path) if gap_path else None,
        "python": sys.version, "platform": platform.platform(),
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        "explore_seeds": explore, "eval_seeds": evals, "blocks": blocks, "sessions": ns,
        "max_total_buckets": args.max_total_buckets,
        "compile_budget_s": args.compile_budget_s,
        "baseline": {"buckets": list(BASELINE[0]), "batch_size": BASELINE[1],
                     "base_busy_s": base_busy},
    }

    # The ledger holds only computed values so two runs can be compared byte
    # for byte; everything run-specific lives in meta.json.
    (args.output_dir / "ledger.json").write_text(json.dumps(
        {"counts": counts, "baseline_busy_s": base_busy, "rows": rows}, indent=2) + "\n")
    with (args.output_dir / "ledger.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["enum_index", "explore_rank", "buckets", "batch_size",
                    "compile_s", "artifact_gib", "explore_busy_s", "explore_ratio",
                    "eval_busy_s", "eval_ratio"]
                   + [f"explore_ratio_n{n}" for n in ns] + [f"eval_ratio_n{n}" for n in ns])
        for r in rows:
            w.writerow([r["enum_index"], r["explore_rank"],
                        " ".join(map(str, r["buckets"])), r["batch_size"],
                        repr(r["compile_s"]), repr(r["artifact_gib"]),
                        repr(r["explore_busy_s"]), repr(r["explore_ratio"]),
                        repr(r["eval_busy_s"]), repr(r["eval_ratio"])]
                       + [repr(r["explore_per_n_ratio"][n]) for n in ns]
                       + [repr(r["eval_per_n_ratio"][n]) for n in ns])
    (args.output_dir / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    (args.output_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"\n=== 탐색 seed 기준 상위 {args.top} (ratio < 1 이 개선) ===")
    print(f"{'순위':>4} {'buckets':<24} {'batch':>5} {'탐색 ratio':>11} {'평가 ratio':>11} "
          f"{'탐색 busy(s)':>13} {'평가 busy(s)':>13}")
    for r in ranked[:args.top]:
        print(f"{r['explore_rank']:>4} {str(tuple(r['buckets'])):<24} {r['batch_size']:>5} "
              f"{r['explore_ratio']:>11.6f} {r['eval_ratio']:>11.6f} "
              f"{r['explore_busy_s']:>13.4f} {r['eval_busy_s']:>13.4f}")
    print(f"\n탐색 최소: {tuple(best['buckets'])} batch {best['batch_size']} "
          f"(동률 {len(tied_min)}개) — 기록과 일치: {comparison['argmin_equals_recorded']}")
    if rec:
        print(f"기록 선정 구성: 탐색 순위 {rec['explore_rank']}, 평가 ratio {rec['eval_ratio']:.6f} "
              f"(기록 {RECORDED_EVAL_RATIO}, 차 {rec['eval_ratio'] - RECORDED_EVAL_RATIO:+.6f})")
    print(f"소요 {elapsed:.1f} s → {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
