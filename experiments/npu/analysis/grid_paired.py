#!/usr/bin/env python3
"""TASK54: the grid intervention re-measured on one shared trace.

TASK23 changed the compiled bucket grid and watched Δp move from +0.1150 to
−0.0268, but the two batches drew their session plans from different seeds, so
that move carries a grid effect and a trace difference together. Here every
(N, repetition) plan is replayed under both grids and both arms, so the only
thing that differs between the two grids is the grid.

Three things are checked before any number is printed:

  G1  the plan of a given (N, repetition, arm) is byte-identical across grids
      -- if the grid reached the trace, this whole task is INVALID;
  G2  the CONVENTIONAL plan is the AGENTIC plan with its gaps zeroed;
  G3  the three repetitions really are three different traces.

Padding is formed exactly as TASK52 formed it: ``arm_totals`` is imported from
padding_ratio rather than reimplemented, so "same computation path" is a fact
about the code and not a claim in a document.

Verdicts P1-P3 and the null band X = 0.004 are preregistered in
docs/research/GRID_PAIRED_PREREG.md and are not recomputed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

from padding_ratio import arm_totals  # noqa: E402
from bootstrap_ratio import median_ratio_ci  # noqa: E402

GRIDS = {"mb": (1, 2, 4, 8), "mb6": (1, 2, 4, 6, 8)}
ARMS = ("AGENTIC", "CONVENTIONAL")
NS = (6, 8)
REPS = (0, 1, 2)

#: Preregistered null band on Δp (GRID_PAIRED_PREREG.md, "무효 밴드 X").
X = 0.004
#: Preregistered bootstrap settings for the supplementary equivalence check.
CI_WIDTH_MAX = 0.06
RESAMPLES = 2000
BASE_SEED = 20260954

#: TASK23 / PADDING_RATIO.md §1, for side-by-side only. Not re-adjudicated.
TASK23 = {
    ("mb", 6): {"dp": +0.1150, "u_ratio": 1.1504, "src": "TASK20 (seed 20260830)"},
    ("mb6", 6): {"dp": -0.0268, "u_ratio": 0.9717, "src": "TASK23-2b (seed 20260842)"},
    ("mb", 8): {"dp": -0.0791, "u_ratio": 0.9132, "src": "TASK23-2a b5-b7 (seed 20260841)"},
    ("mb6", 8): {"dp": -0.0479, "u_ratio": 0.9508, "src": "TASK23-2b (seed 20260842)"},
}


def plan_hash(meta: dict) -> str:
    return hashlib.sha256(
        json.dumps(meta["plan"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def zeroed(plan: dict) -> dict:
    out = dict(plan)
    out["gap_after_s"] = [[0.0 for _ in turns] for turns in plan["gap_after_s"]]
    return out


def zeroed_hash(meta: dict) -> str:
    return hashlib.sha256(
        json.dumps(zeroed(meta["plan"]), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sign(dp: float) -> str:
    if dp > X:
        return "양수"
    if dp < -X:
        return "음수"
    return "null"


def bucket8_steps(hist: dict) -> int:
    return sum(c for k, c in hist.items() if k.split("->")[1] == "8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path, help="run dir holding mb/ and mb6/")
    ap.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    import os
    os.chdir(args.repo)
    run = args.run

    out: dict = {"run": str(run), "null_band_X": X, "gates": {}, "cells": [],
                 "reps": [], "verdicts": {}}

    # ---------------------------------------------------------------- gates
    metas: dict[tuple, dict] = {}
    missing = []
    for g in GRIDS:
        for n in NS:
            for rep in REPS:
                for arm in ARMS:
                    tag = f"{arm}.n{n}.b{rep}"
                    mp = run / g / "probe" / f"meta.{tag}.json"
                    dm = run / g / f"done.{tag}"
                    if not mp.exists() or not dm.exists():
                        missing.append(f"{g}/{tag}")
                        continue
                    metas[(g, n, rep, arm)] = json.loads(mp.read_text())
    out["gates"]["G5_missing"] = missing

    g1 = []
    for n in NS:
        for rep in REPS:
            for arm in ARMS:
                hs = {g: plan_hash(metas[(g, n, rep, arm)])
                      for g in GRIDS if (g, n, rep, arm) in metas}
                same = len(set(hs.values())) == 1 and len(hs) == len(GRIDS)
                g1.append({"N": n, "rep": rep, "arm": arm, "hashes": hs, "same": same})
    out["gates"]["G1"] = {"rows": g1, "pass": all(r["same"] for r in g1)}

    g2 = []
    for g in GRIDS:
        for n in NS:
            for rep in REPS:
                a, c = (g, n, rep, "AGENTIC"), (g, n, rep, "CONVENTIONAL")
                if a not in metas or c not in metas:
                    continue
                ok = zeroed_hash(metas[a]) == plan_hash(metas[c])
                g2.append({"grid": g, "N": n, "rep": rep, "paired": ok,
                           "total_gap_s_A": metas[a]["total_gap_s"],
                           "total_gap_s_C": metas[c]["total_gap_s"]})
    out["gates"]["G2"] = {"rows": g2, "pass": all(r["paired"] for r in g2)}

    g3 = []
    for g in GRIDS:
        for n in NS:
            for arm in ARMS:
                hs = [plan_hash(metas[(g, n, r, arm)]) for r in REPS
                      if (g, n, r, arm) in metas]
                g3.append({"grid": g, "N": n, "arm": arm,
                           "distinct": len(set(hs)), "of": len(hs)})
    out["gates"]["G3"] = {"rows": g3,
                          "pass": all(r["distinct"] == r["of"] for r in g3)}

    print("=" * 92)
    print("§0  게이트")
    print("=" * 92)
    print(f"  G1 격자 간 plan 동일       : {'PASS' if out['gates']['G1']['pass'] else 'FAIL'}"
          f"  ({len(g1)}칸)")
    print(f"  G2 arm 짝 동일성 (zero_gaps): {'PASS' if out['gates']['G2']['pass'] else 'FAIL'}"
          f"  ({len(g2)}칸)")
    print(f"  G3 반복이 서로 다른 trace  : {'PASS' if out['gates']['G3']['pass'] else 'FAIL'}")
    print(f"  G5 누락 칸                 : {missing if missing else '없음'}")
    if not out["gates"]["G1"]["pass"]:
        raise SystemExit("G1 실패 — 격자가 trace에 닿았다. TASK 전체 INVALID.")

    # ------------------------------------------------------------- per cell
    print()
    print("=" * 92)
    print("§1  p = Σ(b−n)/Σb, Δp = p_CONV − p_AGENTIC   (계산 경로: padding_ratio.arm_totals)")
    print("=" * 92)
    print(f"{'격자':<6}{'N':>3}{'반복':>6}{'p_A':>9}{'p_C':>9}{'Δp':>10}{'부호':>7}"
          f"{'u_A':>9}{'u_C':>9}{'u_A/u_C':>10}{'step A/C':>14}")

    per_rep: dict[tuple, list[float]] = {}
    ratio_samples: dict[tuple, list[float]] = {}
    for g, grid in GRIDS.items():
        for n in NS:
            for rep in REPS:
                parts = [(run / g, f"n{n}.b{rep}")]
                a = arm_totals(parts, "AGENTIC", grid)
                c = arm_totals(parts, "CONVENTIONAL", grid)
                dp = c["padding_ratio"] - a["padding_ratio"]
                ur = a["utilization"] / c["utilization"]
                per_rep.setdefault((g, n), []).append(dp)
                ratio_samples.setdefault((g, n), []).append(ur)
                out["reps"].append({
                    "grid": g, "N": n, "rep": rep,
                    "p_A": a["padding_ratio"], "p_C": c["padding_ratio"],
                    "delta_p": dp, "u_A": a["utilization"], "u_C": c["utilization"],
                    "u_ratio": ur, "steps_A": a["steps"], "steps_C": c["steps"],
                    "bucket8_A": bucket8_steps(a["hist"]),
                    "bucket8_C": bucket8_steps(c["hist"]),
                    "hist_A": a["hist"], "hist_C": c["hist"],
                })
                print(f"{g:<6}{n:>3}{rep:>6}{a['padding_ratio']:>9.4f}"
                      f"{c['padding_ratio']:>9.4f}{dp:>+10.4f}{sign(dp):>7}"
                      f"{a['utilization']:>9.4f}{c['utilization']:>9.4f}{ur:>10.4f}"
                      f"{a['steps']:>7}/{c['steps']:<6}")

    # --------------------------------------------------------------- pooled
    print()
    print("=" * 92)
    print("§2  3반복 합산 (pooled, step 가중) — 판정 대상")
    print("=" * 92)
    print(f"{'격자':<6}{'N':>3}{'p_A':>9}{'p_C':>9}{'Δp':>10}{'부호':>7}"
          f"{'반복 부호':>11}{'u_A/u_C':>10}{'TASK23 Δp':>12}{'TASK23 비':>11}")
    pooled: dict[tuple, dict] = {}
    for g, grid in GRIDS.items():
        for n in NS:
            parts = [(run / g, f"n{n}.b{rep}") for rep in REPS]
            a = arm_totals(parts, "AGENTIC", grid)
            c = arm_totals(parts, "CONVENTIONAL", grid)
            dp = c["padding_ratio"] - a["padding_ratio"]
            ur = a["utilization"] / c["utilization"]
            signs = [sign(v) for v in per_rep[(g, n)]]
            agree = f"{signs.count(sign(dp))}/3"
            pooled[(g, n)] = {
                "grid": g, "N": n, "p_A": a["padding_ratio"],
                "p_C": c["padding_ratio"], "delta_p": dp, "sign": sign(dp),
                "rep_signs": signs, "rep_agree": agree, "u_ratio": ur,
                "u_A": a["utilization"], "u_C": c["utilization"],
                "steps_A": a["steps"], "steps_C": c["steps"],
                "bucket8_A": bucket8_steps(a["hist"]),
                "bucket8_C": bucket8_steps(c["hist"]),
                "hist_A": a["hist"], "hist_C": c["hist"],
                "task23_delta_p": TASK23[(g, n)]["dp"],
                "task23_u_ratio": TASK23[(g, n)]["u_ratio"],
                "task23_src": TASK23[(g, n)]["src"],
            }
            out["cells"].append(pooled[(g, n)])
            print(f"{g:<6}{n:>3}{a['padding_ratio']:>9.4f}{c['padding_ratio']:>9.4f}"
                  f"{dp:>+10.4f}{sign(dp):>7}{agree:>11}{ur:>10.4f}"
                  f"{TASK23[(g, n)]['dp']:>+12.4f}{TASK23[(g, n)]['u_ratio']:>11.4f}")

    print()
    print("  이동량 shift(N) = Δp(mb) − Δp(mb6)   [부수 산출, 판정 아님]")
    for n in NS:
        s = pooled[("mb", n)]["delta_p"] - pooled[("mb6", n)]["delta_p"]
        t = TASK23[("mb", n)]["dp"] - TASK23[("mb6", n)]["dp"]
        out.setdefault("shift", {})[str(n)] = {"measured": s, "task23": t}
        print(f"    N={n}: 이번 {s:+.4f}   TASK23 {t:+.4f}  (다른 seed·다른 run)")

    # ------------------------------------------------------------- bucket 8
    print()
    print("=" * 92)
    print("§3  bucket 8행 step 수 (`*→8`)")
    print("=" * 92)
    print(f"{'격자':<6}{'N':>3}{'AGENTIC':>10}{'CONVENTIONAL':>15}{'A step':>9}{'C step':>9}")
    for g in GRIDS:
        for n in NS:
            c = pooled[(g, n)]
            print(f"{g:<6}{n:>3}{c['bucket8_A']:>10}{c['bucket8_C']:>15}"
                  f"{c['steps_A']:>9}{c['steps_C']:>9}")

    # ------------------------------------------------------------- verdicts
    p1_base = pooled[("mb", 6)]["sign"] == "양수"
    p1_mb6 = pooled[("mb6", 6)]["sign"] in ("음수", "null")
    p1 = p1_base and p1_mb6
    p2 = pooled[("mb", 8)]["sign"] == "음수" and pooled[("mb6", 8)]["sign"] == "음수"
    p3 = pooled[("mb6", 6)]["bucket8_C"] == 0
    out["verdicts"] = {
        "P1": {"pass": p1, "mb_n6_sign": pooled[("mb", 6)]["sign"],
               "mb6_n6_sign": pooled[("mb6", 6)]["sign"]},
        "P2": {"pass": p2, "mb_n8_sign": pooled[("mb", 8)]["sign"],
               "mb6_n8_sign": pooled[("mb6", 8)]["sign"]},
        "P3": {"pass": p3, "bucket8_conventional_mb6_n6": pooled[("mb6", 6)]["bucket8_C"]},
    }
    print()
    print("=" * 92)
    print(f"§4  선등록 판정 (무효 밴드 X = {X})")
    print("=" * 92)
    print(f"  P1  N=6: mb Δp 양수 & mb6 Δp 음수/null : "
          f"{'PASS' if p1 else 'FAIL'}  (mb={pooled[('mb',6)]['sign']}, "
          f"mb6={pooled[('mb6',6)]['sign']})")
    print(f"  P2  N=8: 두 격자 모두 Δp 음수          : "
          f"{'PASS' if p2 else 'FAIL'}  (mb={pooled[('mb',8)]['sign']}, "
          f"mb6={pooled[('mb6',8)]['sign']})")
    print(f"  P3  mb6 N=6 CONVENTIONAL bucket 8행 = 0: "
          f"{'PASS' if p3 else 'FAIL'}  ({pooled[('mb6',6)]['bucket8_C']} step)")

    # -------------------------------------------------- supplementary CI
    print()
    print("=" * 92)
    print(f"§5  보조 — 중앙 u_A/u_C ratio의 bootstrap CI (표본 3, 폭 상한 {CI_WIDTH_MAX})")
    print("=" * 92)
    print(f"{'격자':<6}{'N':>3}{'중앙비':>9}{'CI':>20}{'폭':>9}{'판정':>15}")
    out["bootstrap"] = []
    for g in GRIDS:
        for n in NS:
            s = ratio_samples[(g, n)]
            r = median_ratio_ci([1.0] * len(s), s, resamples=RESAMPLES,
                                base_seed=BASE_SEED, label=f"{g}.n{n}")
            r["ci_width_within_bound"] = r["ci_width"] <= CI_WIDTH_MAX
            r["verdict"] = ("EQUIVALENT" if (r["contains_one"] and r["ci_width_within_bound"])
                            else ("DIFFERENT" if not r["contains_one"] else "INCONCLUSIVE"))
            r["grid"], r["N"], r["samples"] = g, n, s
            out["bootstrap"].append(r)
            print(f"{g:<6}{n:>3}{r['point_ratio']:>9.4f}"
                  f"   [{r['ci_low']:.4f},{r['ci_high']:.4f}]{r['ci_width']:>9.4f}"
                  f"{r['verdict']:>15}")
    print("  표본이 3이므로 보조 검정이다. P1–P3의 판정을 대체하지 않는다.")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"\n  → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
