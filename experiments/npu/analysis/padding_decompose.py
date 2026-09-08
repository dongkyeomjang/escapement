#!/usr/bin/env python3
"""Where the CONVENTIONAL padding drop of the grid intervention comes from.

TASK54 measured the same trace under both compiled grids. In the CONVENTIONAL
arm the gaps are zero, arrivals are deterministic, and the decode step column
turns out to be *identical* between the two grids -- same number of steps, same
histogram of actual request counts (TASK54 observation 5). Only the mapping
from actual to padded batch width changes: 5 -> 8 and 6 -> 8 on the base grid
become 5 -> 6 and 6 -> 6 once bucket 6 exists.

That makes the padding drop exactly attributable. This module splits

    p = sum(b_t - n_t) / sum(b_t)

by actual request count n, two ways, because the two answer different
questions:

  * the numerator split -- of the padding slots that disappeared, how many
    came from n=6 steps and how many from n=5 steps. Exact, no interaction;
  * the exact split of the *ratio* drop. p has the padded width in its
    denominator, so removing padding at n=6 also shrinks the denominator and
    thereby raises the padding share of every other n. That interaction is
    real and has to go somewhere. It is assigned by Shapley value over the two
    changed groups, which for two players is exact, order independent, and
    sums to the total drop with no residual. The denominator effect is also
    reported on its own line so the interaction is visible rather than buried.

Recomputation only. No measurement, no new judgement: TASK54's Delta p and
TASK23's verdicts stand as they are. Pooled totals come from
padding_ratio.arm_totals, imported rather than restated, so this shares
TASK52's computation path exactly.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from padding_ratio import arm_totals  # noqa: E402

GRIDS = {"mb": (1, 2, 4, 8), "mb6": (1, 2, 4, 6, 8)}
REPS = (0, 1, 2)
TOL = 5e-5


def bucket_for(n: int, grid: tuple[int, ...]) -> int:
    return min(b for b in grid if b >= n)


def actual_histogram(run: Path, grid: str, arm: str, n: int, reps) -> dict[int, int]:
    """Steps by actual request count, pooled over the repetitions."""
    hist: dict[int, int] = {}
    for rep in reps:
        util = json.loads((run / grid / f"util.{arm}.n{n}.b{rep}.json").read_text())
        if not util.get("valid", True):
            raise SystemExit(f"INVALID {grid}/{arm}.n{n}.b{rep}")
        for key, count in util["pair_histogram"].items():
            a, b = (int(x) for x in key.split("->"))
            if b != bucket_for(a, GRIDS[grid]):
                raise SystemExit(f"{grid}/{arm}.n{n}.b{rep}: {a}->{b} contradicts grid")
            hist[a] = hist.get(a, 0) + count
    return hist


def p_of(hist: dict[int, int], mapping: dict[int, int]) -> float:
    pad = sum(c * (mapping[a] - a) for a, c in hist.items())
    tot = sum(c * mapping[a] for a, c in hist.items())
    return pad / tot


def shapley(hist: dict[int, int], base: dict[int, int], new: dict[int, int],
            players: list[int]) -> dict[int, float]:
    """Exact split of p(base) - p(new) among the n whose bucket changed.

    Coalition S uses the new mapping for the n in S and the base mapping
    elsewhere; the drop is p(base) - p(S). Averaging each player's marginal
    contribution over every ordering is the Shapley value, which is exact and
    order independent, so the parts sum to the whole with nothing left over.
    """
    def p_of_coalition(S: frozenset[int]) -> float:
        m = {a: (new[a] if a in S else base[a]) for a in hist}
        return p_of(hist, m)

    out = {q: 0.0 for q in players}
    orders = list(itertools.permutations(players))
    for order in orders:
        S: set[int] = set()
        prev = p_of_coalition(frozenset(S))
        for q in order:
            S.add(q)
            cur = p_of_coalition(frozenset(S))
            out[q] += prev - cur     # this player's share of the drop
            prev = cur
    return {q: v / len(orders) for q, v in out.items()}


def analyse(run: Path, n: int, arm: str) -> dict:
    h_mb = actual_histogram(run, "mb", arm, n, REPS)
    h_mb6 = actual_histogram(run, "mb6", arm, n, REPS)
    if h_mb != h_mb6:
        raise SystemExit(
            f"N={n} {arm}: step 열이 격자 간 다르다 — 이 분해의 전제가 깨진다\n"
            f"  mb  {dict(sorted(h_mb.items()))}\n  mb6 {dict(sorted(h_mb6.items()))}")
    hist = h_mb
    map_mb = {a: bucket_for(a, GRIDS["mb"]) for a in hist}
    map_mb6 = {a: bucket_for(a, GRIDS["mb6"]) for a in hist}

    # Same computation path as TASK52, used as the cross-check on p.
    checks = {}
    for g in GRIDS:
        parts = [(run / g, f"n{n}.b{rep}") for rep in REPS]
        checks[g] = arm_totals(parts, arm, GRIDS[g])["padding_ratio"]
    p_mb, p_mb6 = p_of(hist, map_mb), p_of(hist, map_mb6)
    for g, got in (("mb", p_mb), ("mb6", p_mb6)):
        if abs(got - checks[g]) > TOL:
            raise SystemExit(f"N={n} {arm} {g}: p {got:.6f} != arm_totals {checks[g]:.6f}")

    changed = sorted(a for a in hist if map_mb[a] != map_mb6[a])
    rows = []
    for a in sorted(hist):
        c = hist[a]
        rows.append({
            "n": a, "steps": c, "share_steps": c / sum(hist.values()),
            "bucket_mb": map_mb[a], "bucket_mb6": map_mb6[a],
            "pad_slots_mb": c * (map_mb[a] - a),
            "pad_slots_mb6": c * (map_mb6[a] - a),
            "pad_slots_removed": c * (map_mb[a] - a) - c * (map_mb6[a] - a),
            "changed": a in changed,
        })
    removed = sum(r["pad_slots_removed"] for r in rows)
    for r in rows:
        r["share_of_removed"] = (r["pad_slots_removed"] / removed) if removed else 0.0

    sh = shapley(hist, map_mb, map_mb6, changed)
    drop = p_mb - p_mb6

    # Numerator / denominator split of the same drop, for the interaction.
    P_mb = sum(r["pad_slots_mb"] for r in rows)
    P_mb6 = sum(r["pad_slots_mb6"] for r in rows)
    B_mb = sum(r["steps"] * r["bucket_mb"] for r in rows)
    B_mb6 = sum(r["steps"] * r["bucket_mb6"] for r in rows)
    num_effect = (P_mb - P_mb6) / B_mb
    den_effect = P_mb6 / B_mb - P_mb6 / B_mb6

    return {
        "N": n, "arm": arm, "steps": sum(hist.values()),
        "p_mb": p_mb, "p_mb6": p_mb6, "drop": drop,
        "pad_slots_mb": P_mb, "pad_slots_mb6": P_mb6, "pad_slots_removed": removed,
        "bucket_sum_mb": B_mb, "bucket_sum_mb6": B_mb6,
        "rows": rows, "changed": changed,
        "shapley": {str(k): v for k, v in sh.items()},
        "shapley_share": {str(k): v / drop for k, v in sh.items()},
        "numerator_effect": num_effect, "denominator_effect": den_effect,
    }


def report(a: dict) -> None:
    print("=" * 92)
    print(f"N = {a['N']}, arm = {a['arm']}, 3반복 합산 {a['steps']:,} step "
          f"(격자 간 step 열 동일 — 게이트 통과)")
    print("=" * 92)
    print(f"  p  {a['p_mb']:.4f} → {a['p_mb6']:.4f}   하락분 {a['drop']:.4f}")
    print(f"  padding slot  {a['pad_slots_mb']:,} → {a['pad_slots_mb6']:,}  "
          f"(소멸 {a['pad_slots_removed']:,})")
    print(f"  Σbucket       {a['bucket_sum_mb']:,} → {a['bucket_sum_mb6']:,}")
    print()
    print(f"{'n':>3}{'step':>7}{'step 비중':>11}{'bucket mb':>11}{'mb6':>6}"
          f"{'pad mb':>9}{'pad mb6':>9}{'소멸':>8}{'소멸 몫':>10}")
    for r in a["rows"]:
        mark = " *" if r["changed"] else ""
        print(f"{r['n']:>3}{r['steps']:>7}{100 * r['share_steps']:>10.1f}%"
              f"{r['bucket_mb']:>11}{r['bucket_mb6']:>6}"
              f"{r['pad_slots_mb']:>9}{r['pad_slots_mb6']:>9}"
              f"{r['pad_slots_removed']:>8}"
              f"{100 * r['share_of_removed']:>9.1f}%{mark}")
    print("  * = 격자 변경으로 사상이 바뀐 n")
    print()
    print("  (A) 분자 분해 — 소멸한 padding slot의 몫 (상호작용 없음, 정확)")
    for r in a["rows"]:
        if r["pad_slots_removed"]:
            print(f"      n={r['n']}: {r['pad_slots_removed']:>5} slot  "
                  f"{100 * r['share_of_removed']:>5.1f} %")
    print()
    print("  (B) p 하락분의 정확 분해 — Shapley (분모 축소 상호작용 포함, 잔차 0)")
    tot = 0.0
    for k, v in sorted(a["shapley"].items(), key=lambda kv: -kv[1]):
        tot += v
        print(f"      n={k}: {v:+.4f}   하락분의 {100 * a['shapley_share'][k]:>5.1f} %")
    print(f"      합계 {tot:+.4f}  대  하락분 {a['drop']:+.4f}  "
          f"(잔차 {tot - a['drop']:+.2e})")
    print()
    print("  (C) 같은 하락분의 분자/분모 분해 — 상호작용의 크기를 드러낸다")
    print(f"      분자(padding 소멸)  {a['numerator_effect']:+.4f}   "
          f"{100 * a['numerator_effect'] / a['drop']:>6.1f} %")
    print(f"      분모(Σbucket 축소)  {a['denominator_effect']:+.4f}   "
          f"{100 * a['denominator_effect'] / a['drop']:>6.1f} %")
    print(f"      합계 {a['numerator_effect'] + a['denominator_effect']:+.4f}")
    print("      분모 항은 padding이 그대로인 n의 몫이 커지는 효과다 — 하락을 상쇄한다.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path,
                    default=Path("results/npu/stage2/20260908-133635-grid-paired"))
    ap.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    ap.add_argument("--sessions", default="6,8")
    ap.add_argument("--arm", default="CONVENTIONAL")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    import os
    os.chdir(args.repo)
    out = [analyse(args.run, int(x), args.arm) for x in args.sessions.split(",")]
    for a in out:
        report(a)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"  → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
