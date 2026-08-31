#!/usr/bin/env python3
"""The null distribution of channel disagreement, from untreated repeats.

Every device-time judgement in this programme is gated on the two channels
agreeing to within ``tau(N) = max(0.02, r_BASE / B_BASE)``. The second term is
derived (TASK36); the 0.02 floor is a convention with no derivation anywhere in
the repository (TASK49). Neither term was ever compared against the thing a
tolerance is supposed to cover: how far the two channels drift apart when there
is no treatment at all.

This module measures that. One configuration, one fixed trace per N, run ten
times with nothing varying but the server process. For every unordered pair of
repeats it forms the same quantity a treated cell forms -- a ratio on each
channel, and the gap between them:

    gap(i, j) = | A_i / A_j  -  B_i / B_j |

Ten repeats give 45 pairs. Under the null both channels are measuring the same
unchanged workload, so a treated cell's gap has to clear this distribution
before it means anything.

Preregistered here, before the measurement, and not to be changed afterwards:

  * the quantile convention -- nearest rank, ``sorted[ceil(0.95 * n) - 1]``;
  * ``tau_null(N) = max(0.02, median_i(r_i / B_i))``, the tolerance the tau
    form would produce on this run, since a null run has no BASE/arm split;
  * the three-way comparison C1/C2/C3 in ``classify()``;
  * the validity rule: a repeat whose invariants fail is excluded and named,
    and an N with fewer than 8 valid repeats reports no distribution at all.

This script juxtaposes. It does not re-adjudicate any past verdict and does not
revise tau.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from config_device import CHANNEL_FLOOR, channel_a_prime, channel_b  # noqa: E402
from config_search import descriptor_for  # noqa: E402

#: The one configuration under test: the b8 baseline, unchanged.
ARM = "NULL"
BUCKETS = (1, 2, 4, 8)
BATCH_SIZE = 8

#: Minimum valid repeats for an N to report a distribution at all.
MIN_VALID = 8


def quantile(values: list[float], q: float) -> float:
    """Nearest-rank quantile. Preregistered so the convention cannot drift."""
    s = sorted(values)
    if not s:
        raise ValueError("empty")
    k = max(1, math.ceil(q * len(s)))
    return s[k - 1]


def descriptor():
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    return descriptor_for(D, BUCKETS, BATCH_SIZE)


def load_repeat(run: Path, n: int, rep: int, d) -> dict | None:
    """One repeat, or None if its artefacts are absent."""
    label = f"{ARM}.n{n}.b{rep}"
    util_p = run / f"util.{label}.json"
    rows_p = run / "probe" / f"requests.{label}.jsonl"
    if not util_p.exists() or not rows_p.exists():
        return None
    util = json.loads(util_p.read_text())
    rows = [json.loads(l) for l in rows_p.read_text().splitlines() if l.strip()]
    a, dec, pre = channel_a_prime(util, rows, d)
    b = channel_b(rows)
    turn2 = [r for r in rows if r["turn"] > 0]
    return {
        "rep": rep, "label": label,
        "valid": bool(util.get("valid", True)),
        "violations": util.get("invariant_violations", []),
        "a_prime_s": a, "decode_s": dec, "prefill_s": pre, "b_s": b,
        "residual_s": b - a, "residual_share": (b - a) / b,
        "reuse": sum(1 for r in turn2 if (r.get("cached_tokens") or 0) > 0),
        "resume": len(turn2),
        "steps": sum(util["pair_histogram"].values()),
    }


def classify(q95: float, tau_null: float) -> tuple[str, str]:
    """The preregistered three-way juxtaposition. No verdict on past tasks."""
    if q95 <= CHANNEL_FLOOR:
        return "C1", ("현행 하한 0.02가 무처치 변동의 95 분위수를 포괄한다")
    if q95 <= tau_null:
        return "C2", ("하한 0.02만으로는 포괄되지 않고 τ 형태가 포괄한다")
    return "C3", ("허용차가 무처치 변동보다 좁다")


def analyse(run: Path, n: int, reps: list[int]) -> dict:
    d = descriptor()
    loaded = [load_repeat(run, n, r, d) for r in reps]
    missing = [r for r, x in zip(reps, loaded) if x is None]
    present = [x for x in loaded if x is not None]
    invalid = [x for x in present if not x["valid"]]
    valid = [x for x in present if x["valid"]]

    out = {
        "N": n, "requested_reps": reps, "missing": missing,
        "invalid": [{"rep": x["rep"], "violations": x["violations"]} for x in invalid],
        "valid_count": len(valid), "repeats": present,
    }
    if len(valid) < MIN_VALID:
        out["status"] = "INVALID"
        out["reason"] = f"유효 반복 {len(valid)} < {MIN_VALID}"
        return out
    out["status"] = "VALID"

    pairs = []
    for i, j in itertools.combinations(range(len(valid)), 2):
        x, y = valid[i], valid[j]
        ra = x["a_prime_s"] / y["a_prime_s"]
        rb = x["b_s"] / y["b_s"]
        pairs.append({"i": x["rep"], "j": y["rep"], "a_ratio": ra,
                      "b_ratio": rb, "gap": abs(ra - rb)})
    gaps = [p["gap"] for p in pairs]
    shares = [x["residual_share"] for x in valid]
    tau_null = max(CHANNEL_FLOOR, statistics.median(shares))
    q95 = quantile(gaps, 0.95)
    cls, text = classify(q95, tau_null)

    a_vals = [x["a_prime_s"] for x in valid]
    b_vals = [x["b_s"] for x in valid]
    out.update({
        "pair_count": len(pairs), "pairs": pairs,
        "gap_median": statistics.median(gaps),
        "gap_q95": q95, "gap_max": max(gaps), "gap_min": min(gaps),
        "residual_s_median": statistics.median(x["residual_s"] for x in valid),
        "residual_s_min": min(x["residual_s"] for x in valid),
        "residual_s_max": max(x["residual_s"] for x in valid),
        "residual_share_median": statistics.median(shares),
        "residual_share_min": min(shares), "residual_share_max": max(shares),
        "tau_null": tau_null, "class": cls, "class_text": text,
        "a_mean_s": statistics.mean(a_vals), "a_sd_s": statistics.stdev(a_vals),
        "a_cv": statistics.stdev(a_vals) / statistics.mean(a_vals),
        "a_span": (max(a_vals) - min(a_vals)) / statistics.mean(a_vals),
        "b_mean_s": statistics.mean(b_vals), "b_sd_s": statistics.stdev(b_vals),
        "b_cv": statistics.stdev(b_vals) / statistics.mean(b_vals),
        "b_span": (max(b_vals) - min(b_vals)) / statistics.mean(b_vals),
    })
    return out


def report(r: dict) -> None:
    n = r["N"]
    print(f"\n{'=' * 74}\nN = {n}\n{'=' * 74}")
    if r["missing"]:
        print(f"  없는 반복: {r['missing']}")
    if r["invalid"]:
        for x in r["invalid"]:
            print(f"  INVALID 반복 r{x['rep']}: {x['violations']}")
    print(f"  유효 반복 {r['valid_count']}개  상태 {r['status']}")
    if r["status"] != "VALID":
        print(f"  {r['reason']} — 분포를 산출하지 않는다.")
        return

    print(f"\n  실행별 채널 값")
    print(f"    {'rep':>4}{'A′ (s)':>11}{'B (s)':>11}{'r = B−A′':>11}"
          f"{'r/B':>9}{'재사용':>9}{'step':>8}")
    for x in r["repeats"]:
        if not x["valid"]:
            continue
        print(f"    {x['rep']:>4}{x['a_prime_s']:>11.3f}{x['b_s']:>11.3f}"
              f"{x['residual_s']:>11.3f}{x['residual_share']:>9.4f}"
              f"{x['reuse']:>6}/{x['resume']:<2}{x['steps']:>8}")

    print(f"\n  짝 분포 ({r['pair_count']}쌍)  gap = |A_i/A_j − B_i/B_j|")
    print(f"    최솟값 {r['gap_min']:.4f}   중앙값 {r['gap_median']:.4f}   "
          f"95 분위 {r['gap_q95']:.4f}   최댓값 {r['gap_max']:.4f}")

    print(f"\n  잔차 r = B − A′")
    print(f"    {r['residual_s_min']:.3f} – {r['residual_s_max']:.3f} s, "
          f"중앙값 {r['residual_s_median']:.3f} s")
    print(f"    r/B  {r['residual_share_min']:.4f} – {r['residual_share_max']:.4f}, "
          f"중앙값 {r['residual_share_median']:.4f}")

    print(f"\n  채널 자체의 재현성 (부수 정보)")
    print(f"    A′  평균 {r['a_mean_s']:.3f} s  표준편차 {r['a_sd_s']:.3f} s  "
          f"CV {r['a_cv']:.4f}  전폭/평균 {r['a_span']:.4f}")
    print(f"    B   평균 {r['b_mean_s']:.3f} s  표준편차 {r['b_sd_s']:.3f} s  "
          f"CV {r['b_cv']:.4f}  전폭/평균 {r['b_span']:.4f}")

    print(f"\n  τ와의 병치 (판정 아님)")
    print(f"    하한 0.02          {'≥' if CHANNEL_FLOOR >= r['gap_q95'] else '<'} "
          f"95 분위 {r['gap_q95']:.4f}")
    print(f"    τ_null({n}) = max(0.02, {r['residual_share_median']:.4f}) "
          f"= {r['tau_null']:.4f}  "
          f"{'≥' if r['tau_null'] >= r['gap_q95'] else '<'} 95 분위")
    print(f"    → {r['class']}: {r['class_text']}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--sessions", default="6,8")
    p.add_argument("--reps", default="0,1,2,3,4,5,6,7,8,9")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    reps = [int(x) for x in args.reps.split(",")]
    out = []
    for n in (int(x) for x in args.sessions.split(",")):
        r = analyse(args.run, n, reps)
        report(r)
        out.append(r)
    if args.output:
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"\n산출: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
