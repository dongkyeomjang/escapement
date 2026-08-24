#!/usr/bin/env python3
"""The batch_size saturation curve, and the mechanism behind its shape.

TASK35 showed that batch_size is the lever that recovers device time, and
TASK36 showed the recovery is proportional to how much cache the baseline was
losing. Both invite the obvious rebuttal -- then make it bigger -- so this
prices the curve directly.

Shape is judged from the bootstrap CI of the median per-cell ratio between
adjacent configurations, never from a fixed band (repository rule 17). The
mechanism is read off two quantities that the preregistration predicts will
explain a plateau if one appears: the layer-2 survival rate, and how often the
top compiled bucket is actually selected. A bucket that is never selected can
neither cost nor save anything, which is the whole reason a larger pool can be
free rather than harmful.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from bootstrap_ratio import median_ratio_ci  # noqa: E402
from config_device import CHANNEL_FLOOR, channel_a_prime, channel_b  # noqa: E402
from config_search import descriptor_for  # noqa: E402

#: arm -> (compiled bucket set, batch_size). Only the top rung changes across
#: B16/B24/B32, which is what makes those two steps controlled comparisons.
ARMS: dict[str, tuple[tuple[int, ...], int]] = {
    "B8": ((1, 2, 4, 8), 8),
    "B16": ((1, 4, 6, 8, 10, 16), 16),
    "B24": ((1, 4, 6, 8, 10, 24), 24),
    "B32": ((1, 4, 6, 8, 10, 32), 32),
}
CI_WIDTH_LIMIT = 0.04          # preregistered
RESAMPLES = 4000               # preregistered
BOOTSTRAP_SEED = 20261200      # preregistered


def descriptor(arm: str):
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    buckets, batch = ARMS[arm]
    return descriptor_for(D, buckets, batch)


def cell(run: Path, arm: str, n: int, blk: int) -> dict | None:
    label = f"{arm}.n{n}.b{blk}"
    util_p = run / f"util.{label}.json"
    if not util_p.exists():
        return None
    util = json.loads(util_p.read_text())
    if not util.get("valid", True):
        raise SystemExit(f"INVALID {label}: {util['invariant_violations']}")
    rows = [json.loads(l) for l in
            (run / "probe" / f"requests.{label}.jsonl").read_text().splitlines() if l.strip()]
    a, dec, pre = channel_a_prime(util, rows, descriptor(arm))
    turn2 = [r for r in rows if r["turn"] > 0]
    top = ARMS[arm][0][-1]
    hist = util["pair_histogram"]
    steps = sum(hist.values())
    top_steps = sum(c for k, c in hist.items() if int(k.split("->")[1]) == top)
    return {"label": label, "a_prime_s": a, "decode_s": dec, "prefill_s": pre,
            "b_s": channel_b(rows),
            "reuse": sum(1 for r in turn2 if (r.get("cached_tokens") or 0) > 0),
            "resume": len(turn2),
            "top_bucket": top, "top_share": top_steps / steps if steps else 0.0,
            "steps": steps}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--arms", default="B8,B16,B24,B32")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--baseline", default="B8")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    arms = [a for a in args.arms.split(",")]
    ns = [int(x) for x in args.sessions.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]

    cells: dict[tuple[str, int, int], dict] = {}
    missing: list[str] = []
    for arm in arms:
        for n in ns:
            for b in blocks:
                c = cell(args.run, arm, n, b)
                if c is None:
                    missing.append(f"{arm}.n{n}.b{b}")
                else:
                    cells[(arm, n, b)] = c
    present = [a for a in arms if any(k[0] == a for k in cells)]
    if missing:
        print(f"실행되지 않은 조합 {len(missing)}개: {missing[:4]}{' ...' if len(missing) > 4 else ''}")

    out: dict = {"arms": present, "missing": missing, "per_n": [], "adjacent": [],
                 "mechanism": []}

    # -- the curve, per N, on both channels ------------------------------
    print(f"\n=== B-곡선 ({args.baseline} 대비 device time ratio) ===")
    print(f"{'N':>3}  " + "  ".join(f"{a:>16}" for a in present))
    for n in ns:
        base_a = sum(cells[(args.baseline, n, b)]["a_prime_s"] for b in blocks)
        base_b = sum(cells[(args.baseline, n, b)]["b_s"] for b in blocks)
        r_base = base_b - base_a
        tol = max(CHANNEL_FLOOR, r_base / base_b)
        row = {"N": n, "channel_tolerance": tol, "residual_s": r_base,
               "residual_share": r_base / base_b, "arms": {}}
        cellstr = []
        for a in present:
            if (a, n, blocks[0]) not in cells:
                cellstr.append(f"{'--':>16}")
                continue
            ta = sum(cells[(a, n, b)]["a_prime_s"] for b in blocks)
            tb = sum(cells[(a, n, b)]["b_s"] for b in blocks)
            ra, rb = ta / base_a, tb / base_b
            row["arms"][a] = {"a_prime_ratio": ra, "b_ratio": rb,
                              "channel_gap": abs(ra - rb),
                              "channel_pass": abs(ra - rb) <= tol,
                              "a_prime_s": ta, "b_s": tb}
            mark = "" if abs(ra - rb) <= tol else "!"
            cellstr.append(f"{ra:.4f}/{rb:.4f}{mark:>2}")
        print(f"{n:>3}  " + "  ".join(f"{c:>16}" for c in cellstr))
        print(f"     채널 허용차 tau={tol:.4f} (잔차 {r_base:.3f} s = {100 * r_base / base_b:.1f} %)")
        out["per_n"].append(row)

    # -- shape: bootstrap CI on the adjacent pairs -----------------------
    print(f"\n=== 인접쌍 형태 판정 (per-cell ratio {len(ns) * len(blocks)}칸, "
          f"bootstrap {RESAMPLES}, CI 폭 상한 {CI_WIDTH_LIMIT}) ===")
    for lo, hi in zip(present, present[1:]):
        pop_a = [cells[(lo, n, b)]["a_prime_s"] for n in ns for b in blocks
                 if (lo, n, b) in cells and (hi, n, b) in cells]
        pop_b = [cells[(hi, n, b)]["a_prime_s"] for n in ns for b in blocks
                 if (lo, n, b) in cells and (hi, n, b) in cells]
        ratios = [y / x for x, y in zip(pop_a, pop_b)]
        ci = median_ratio_ci([1.0] * len(ratios), ratios, resamples=RESAMPLES,
                             base_seed=BOOTSTRAP_SEED, label=f"{lo}->{hi}")
        if ci["ci_low"] > 1.0:
            verdict = "반전"
        elif ci["ci_high"] < 1.0:
            verdict = "계속 이득"
        elif ci["ci_width"] <= CI_WIDTH_LIMIT:
            verdict = "포화"
        else:
            verdict = "INCONCLUSIVE"
        controlled = lo != args.baseline
        print(f"  {lo}→{hi}  중앙 ratio {ci['point_ratio']:.4f}  "
              f"CI [{ci['ci_low']:.4f}, {ci['ci_high']:.4f}]  폭 {ci['ci_width']:.4f}  "
              f"→ **{verdict}**{'' if controlled else '  (통제되지 않은 쌍)'}")
        out["adjacent"].append({"from": lo, "to": hi, "controlled": controlled,
                                "verdict": verdict, "per_cell_ratios": ratios, **ci})

    # -- mechanism -------------------------------------------------------
    print("\n=== 기전 분해 ===")
    print(f"{'N':>3} {'arm':>5} {'생존율':>12} {'최상위 bucket':>14} {'최상위 비중':>12}")
    for n in ns:
        for a in present:
            if (a, n, blocks[0]) not in cells:
                continue
            hits = sum(cells[(a, n, b)]["reuse"] for b in blocks)
            res = sum(cells[(a, n, b)]["resume"] for b in blocks)
            steps = sum(cells[(a, n, b)]["steps"] for b in blocks)
            tops = sum(cells[(a, n, b)]["top_share"] * cells[(a, n, b)]["steps"] for b in blocks)
            share = tops / steps if steps else 0.0
            out["mechanism"].append({"N": n, "arm": a, "reuse": hits, "resume": res,
                                     "survival": hits / res if res else 0.0,
                                     "top_bucket": ARMS[a][0][-1], "top_share": share})
            print(f"{n:>3} {a:>5} {f'{hits}/{res}':>12} {ARMS[a][0][-1]:>14} "
                  f"{100 * share:>11.1f} %")

    if args.output:
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
