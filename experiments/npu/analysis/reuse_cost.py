#!/usr/bin/env python3
"""What a lost reuse costs, priced two ways, over TASK54's re-arriving requests.

A re-arriving request whose KV survived recomputes only the tokens the cache
could not serve; one whose KV was released recomputes the reusable prefix C on
top of that. The extra prefill work a miss adds is therefore C tokens, and the
time it costs the device is that work priced by TASK22's ``PrefillCostModel``.

There are two ways to price it and they are not the same number:

  * the independent form ``T(C)`` -- what a prefill of C tokens on its own
    costs. This is the form every existing consumer of the cost model uses
    (``config_device.py`` and ``sim/engine.py`` both call ``prefill_s`` on the
    request's own computed-token count), and it does not depend on L;
  * the increment form ``T(L) - T(L - C)`` -- the difference between prefilling
    the whole re-arriving prompt and prefilling only its tail. Because the cost
    model has a ``ceil(n/128)`` term and a length drift term, this depends on
    the full re-arriving prompt length L as well as on C.

TASK59 section 2-5 registered that the code uses the independent form and that
the two differ by up to 27.8 ms over the ranges it tabulated. This module says
what the gap actually is on the measured population rather than on constructed
(L, C) pairs, because in this workload L and C are not free to vary
independently: C is derived from the previous turn's prompt, and the
re-arriving prompt is that prompt plus what the turn appended.

Recomputation only. No measurement and no new judgement: the reuse rule is
TASK24's, confirmed 95/95 in TASK57, and the cost model is TASK22's.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as SUBSTRATE  # noqa: E402

RUN = Path("results/npu/stage2/20260908-133635-grid-paired")
GRIDS = ("mb", "mb6")
ARMS = ("AGENTIC", "CONVENTIONAL")
NS = (6, 8)
REPS = (0, 1, 2)


def load_turns(run: Path) -> list[dict]:
    """Every re-arriving (turn 1) request, joined to the turn that preceded it."""
    by_turn: dict[tuple, dict] = {}
    for grid in GRIDS:
        for arm in ARMS:
            for n in NS:
                for rep in REPS:
                    path = run / grid / "probe" / f"requests.{arm}.n{n}.b{rep}.jsonl"
                    for line in path.read_text().splitlines():
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        key = (grid, arm, n, rep, row["session"], row["turn"])
                        by_turn[key] = row

    out = []
    for key, row in sorted(by_turn.items()):
        if key[-1] != 1:
            continue
        prev = by_turn[key[:-1] + (0,)]
        out.append({
            "grid": key[0], "arm": key[1], "n": key[2], "rep": key[3],
            "session": key[4],
            "prev_prompt_tokens": prev["prompt_tokens"],
            "L": row["prompt_tokens"],
            "cached_tokens": row["cached_tokens"],
        })
    return out


def reusable_tokens(rec: dict) -> int:
    """C -- what the cache could have served, by TASK24's rule."""
    return SUBSTRATE.hit_formula.hit_tokens(
        shared_prefix_tokens=rec["prev_prompt_tokens"], query_tokens=rec["L"]
    )


def priced(rec: dict) -> dict:
    pm = SUBSTRATE.prefill_cost_model
    c = reusable_tokens(rec)
    return {
        "C": c,
        "independent_ms": pm.prefill_s(c) * 1e3,
        "increment_ms": (pm.prefill_s(rec["L"]) - pm.prefill_s(rec["L"] - c)) * 1e3,
    }


def summarise(records: list[dict], run: Path) -> dict:
    rows = []
    for rec in records:
        rows.append({**rec, **priced(rec)})

    hit = [r for r in rows if r["cached_tokens"] > 0]
    miss = [r for r in rows if r["cached_tokens"] == 0]
    consistent = sum(1 for r in rows if r["cached_tokens"] in (0, r["C"]))

    by_c = {}
    for c in sorted({r["C"] for r in rows}):
        grp = [r for r in rows if r["C"] == c]
        inc = [r["increment_ms"] for r in grp]
        by_c[c] = {
            "requests": len(grp),
            "hits": sum(1 for r in grp if r["cached_tokens"] > 0),
            "L_min": min(r["L"] for r in grp),
            "L_max": max(r["L"] for r in grp),
            "independent_ms": grp[0]["independent_ms"],
            "increment_min_ms": min(inc),
            "increment_max_ms": max(inc),
            "increment_spread_ms": max(inc) - min(inc),
            "L_values": sorted({r["L"] for r in grp}),
        }

    gaps = [r["increment_ms"] - r["independent_ms"] for r in rows]
    return {
        "run": str(run),
        "requests": len(rows),
        "hits": len(hit),
        "misses": len(miss),
        "cached_tokens_consistent_with_rule": consistent,
        "prev_prompt_tokens_range": [min(r["prev_prompt_tokens"] for r in rows),
                                     max(r["prev_prompt_tokens"] for r in rows)],
        "L_range": [min(r["L"] for r in rows), max(r["L"] for r in rows)],
        "L_minus_C_range": [min(r["L"] - r["C"] for r in rows),
                            max(r["L"] - r["C"] for r in rows)],
        "L_minus_C_median": statistics.median([r["L"] - r["C"] for r in rows]),
        "C_values": sorted({r["C"] for r in rows}),
        "independent_range_ms": [min(r["independent_ms"] for r in rows),
                                 max(r["independent_ms"] for r in rows)],
        "increment_range_ms": [min(r["increment_ms"] for r in rows),
                               max(r["increment_ms"] for r in rows)],
        "increment_minus_independent_ms": [min(gaps), max(gaps)],
        "max_increment_spread_within_C_ms": max(v["increment_spread_ms"] for v in by_c.values()),
        "by_C": by_c,
        "prefill_cost_model": {
            "chunk_tokens": SUBSTRATE.prefill_cost_model.chunk_tokens,
            "per_chunk_s": SUBSTRATE.prefill_cost_model.per_chunk_s,
            "drift_s_per_token": SUBSTRATE.prefill_cost_model.drift_s_per_token,
            "fit_range_tokens": [500, 6000],
        },
    }


def render(summary: dict) -> str:
    lines = [
        f"re-arriving requests: {summary['requests']} "
        f"(hit {summary['hits']}, miss {summary['misses']})",
        f"cached_tokens is 0 or exactly C: "
        f"{summary['cached_tokens_consistent_with_rule']}/{summary['requests']}",
        f"previous prompt L0: {summary['prev_prompt_tokens_range'][0]}"
        f"-{summary['prev_prompt_tokens_range'][1]} tokens",
        f"re-arriving prompt L: {summary['L_range'][0]}-{summary['L_range'][1]} tokens",
        f"L - C: {summary['L_minus_C_range'][0]}-{summary['L_minus_C_range'][1]} tokens "
        f"(median {summary['L_minus_C_median']:.0f})",
        "",
        f"{'C':>6} {'n':>4} {'hits':>5} {'L range':>14} {'T(C)':>9} "
        f"{'T(L)-T(L-C)':>18} {'spread':>8}",
    ]
    for c, v in summary["by_C"].items():
        lines.append(
            f"{c:>6} {v['requests']:>4} {v['hits']:>5} "
            f"{v['L_min']:>6}-{v['L_max']:<7} {v['independent_ms']:>8.2f} "
            f"{v['increment_min_ms']:>8.2f}-{v['increment_max_ms']:<9.2f} "
            f"{v['increment_spread_ms']:>7.2f}"
        )
    lo, hi = summary["increment_minus_independent_ms"]
    lines += [
        "",
        f"increment - independent: {lo:.2f} to {hi:.2f} ms",
        f"largest spread of the increment form within one C: "
        f"{summary['max_increment_spread_within_C_ms']:.2f} ms",
        "all values in ms; the cost model was fitted on "
        f"[{summary['prefill_cost_model']['fit_range_tokens'][0]}, "
        f"{summary['prefill_cost_model']['fit_range_tokens'][1]}] computed tokens",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=RUN)
    ap.add_argument("--json", type=Path, help="write the summary here")
    args = ap.parse_args()

    summary = summarise(load_turns(args.run), args.run)
    print(render(summary))
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
