#!/usr/bin/env python3
"""Correctness self-check for the analytic model v0 -- synthetic inputs only.

This is not a comparison with data. No measured histogram, run or descriptor
constant is read: every histogram, step cost and descriptor below is
generated here from a fixed seed. What is checked is that the code computes
what its specification says (docs/research/MODEL_V0.md):

1. grid DP == exhaustive enumeration, on many synthetic histograms and cost
   curves (optimal cost equal; the DP grid is one of the tied optima).
2. the interpolation rule restated in ``continuum.model.grid`` gives the same
   numbers as ``config_search.descriptor_for`` on synthetic base descriptors.
3. occupancy with a constant step cost and no prefill reduces to the
   closed-form binomial law.
4. survival: the probabilistic form with a degenerate window reproduces the
   deterministic inequality, and the two count laws have the stated mean.

Exit status is non-zero on any failure.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuum.model import grid as G  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival as S  # noqa: E402
from continuum.substrate import (  # noqa: E402
    HitFormula, PrefillCostModel, Provenance, StepCostModel, SubstrateDescriptor,
)


def synthetic_h(rng: random.Random, top: int, shape: str) -> dict[int, float]:
    ns = range(1, top + 1)
    if shape == "uniform":
        h = {n: rng.random() for n in ns}
    elif shape == "geometric":
        q = rng.uniform(0.5, 0.95)
        h = {n: q ** n for n in ns}
    elif shape == "peak":
        c = rng.randint(1, top)
        s = rng.uniform(0.5, 3.0)
        h = {n: math.exp(-((n - c) / s) ** 2) for n in ns}
    elif shape == "bimodal":
        a, b = rng.randint(1, top), rng.randint(1, top)
        h = {n: math.exp(-(n - a) ** 2) + 0.5 * math.exp(-(n - b) ** 2) for n in ns}
    elif shape == "sparse":
        h = {n: (rng.random() if rng.random() < 0.3 else 0.0) for n in ns}
        h[rng.randint(1, top)] = 1.0
    elif shape == "integer":
        h = {n: float(rng.randint(0, 50)) for n in ns}
    else:
        raise ValueError(shape)
    return h


def synthetic_fixed(rng: random.Random, top: int, shape: str) -> dict[int, float]:
    base = rng.uniform(5.0, 15.0)
    out = {}
    acc = base
    for b in range(1, top + 1):
        if shape == "linear":
            step = 0.3
        elif shape == "concave":
            step = 1.0 / b
        elif shape == "stairs":
            step = 2.0 if b in (3, 5, 9, 13) else 0.05
        else:  # random increasing
            step = rng.uniform(0.0, 1.0)
        acc += step if b > 1 else 0.0
        out[b] = acc
    return out


def check_dp(seed: int) -> dict:
    rng = random.Random(seed)
    cases = matches = unique = 0
    failures = []
    t_dp = t_bf = 0.0
    for top in (4, 8, 10, 12, 16):
        for k in range(2, 7):
            for hs in ("uniform", "geometric", "peak", "bimodal", "sparse", "integer"):
                for fs in ("linear", "concave", "stairs", "random"):
                    for _ in range(2):
                        h = synthetic_h(rng, top, hs)
                        fixed = synthetic_fixed(rng, top, fs)
                        t0 = time.perf_counter()
                        dp = G.optimal_grid(h, top=top, max_buckets=k, fixed=fixed)
                        t1 = time.perf_counter()
                        bf, ties = G.brute_force_grid(h, top=top, max_buckets=k, fixed=fixed)
                        t2 = time.perf_counter()
                        t_dp += t1 - t0
                        t_bf += t2 - t1
                        cases += 1
                        tol = 1e-9 * max(1.0, abs(bf.fixed_cost))
                        recomputed = G.grid_fixed_cost(dp.grid, h, fixed)
                        ok = (abs(dp.fixed_cost - bf.fixed_cost) <= tol
                              and abs(recomputed - bf.fixed_cost) <= tol
                              and dp.grid in [t.grid for t in ties]
                              and len(dp.grid) <= k and dp.grid[0] == 1
                              and dp.grid[-1] == top)
                        if len(ties) == 1:
                            unique += 1
                        if ok:
                            matches += 1
                        else:
                            failures.append({"top": top, "k": k, "h": hs, "f": fs,
                                             "dp": dp.grid, "bf": bf.grid})
    return {"cases": cases, "matches": matches, "unique_optimum_cases": unique,
            "dp_seconds": round(t_dp, 4), "brute_force_seconds": round(t_bf, 4),
            "failures": failures[:5]}


def synthetic_descriptor(rng: random.Random) -> SubstrateDescriptor:
    widths = sorted(rng.sample(range(1, 13), 4))
    if widths[0] != 1:
        widths[0] = 1
        widths = sorted(set(widths))
    cost = {}
    acc = rng.uniform(0.005, 0.015)
    for w in widths:
        acc += rng.uniform(0.0, 0.003)
        cost[w] = acc
    p = Provenance("universal", "TASK71", "derived", "synthetic self-check")
    return SubstrateDescriptor(
        name="synthetic", bucket_sizes=tuple(widths),
        step_cost_model=StepCostModel(fixed_s_by_bucket=cost,
                                      marginal_s_per_request=0.0, intercept_s=0.0),
        outer_slot_count=widths[-1], outer_slot_tokens=1024, inner_block_tokens=64,
        inner_block_count=64, outer_eviction_policy="fifo", inner_eviction_policy="lru",
        hit_formula=HitFormula(block_tokens=64), kv_pool_tokens=1024 * widths[-1],
        prefill_cost_model=PrefillCostModel(chunk_tokens=64, per_chunk_s=0.01),
        provenance={f: p for f in ("bucket_sizes", "step_cost_model", "outer_slot_count",
                                   "outer_slot_tokens", "inner_block_tokens",
                                   "inner_block_count", "outer_eviction_policy",
                                   "inner_eviction_policy", "hit_formula",
                                   "kv_pool_tokens", "prefill_cost_model")})


def check_interpolation(seed: int) -> dict:
    import config_search as CS  # noqa: E402  (experiments harness; generic function)
    rng = random.Random(seed)
    cases = matches = 0
    worst = 0.0
    for _ in range(200):
        d = synthetic_descriptor(rng)
        top = rng.choice([8, 10, 12, 16, 20])
        mids = sorted(rng.sample(range(2, top), rng.randint(0, min(4, top - 2))))
        buckets = tuple(sorted({1, *mids, top}))
        ref = CS.descriptor_for(d, buckets, top).step_cost_model.fixed_s_by_bucket
        mine = G.interpolated_fixed_costs(d.step_cost_model.fixed_s_by_bucket, buckets)
        cases += 1
        diff = max(abs(ref[b] - mine[b]) for b in buckets)
        worst = max(worst, diff)
        if diff == 0.0:
            matches += 1
    return {"cases": cases, "bit_identical": matches, "max_abs_diff": worst}


def check_occupancy() -> dict:
    """Constant step, zero prefill, N <= max_running: binomial with
    p/(1-p) = decode_steps * t / Z."""
    worst = 0.0
    cases = 0
    for n_sess in (1, 3, 6, 8):
        for z in (0.5, 2.0, 7.0):
            t, g = 0.012, 100.0
            w = O.ClosedWorkload(sessions=n_sess, decode_steps_per_request=g,
                                 think_mean_s=z, prefill_mean_s=0.0, max_running=8)
            occ = O.solve_occupancy(w, lambda r: t)
            rho = g * t / z
            p = rho / (1 + rho)
            exact = [math.comb(n_sess, k) * p ** k * (1 - p) ** (n_sess - k)
                     for k in range(n_sess + 1)]
            worst = max(worst, max(abs(a - b) for a, b in zip(occ.in_service, exact)))
            cases += 1
    # Prefill share fixed point must satisfy phi = 1 - X E[P].
    w = O.ClosedWorkload(sessions=6, decode_steps_per_request=120.0, think_mean_s=3.0,
                         prefill_mean_s=0.2, max_running=8)
    occ = O.solve_occupancy(w, lambda r: 0.010 + 0.001 * r)
    fp_resid = abs(occ.phi - (1 - occ.throughput_per_s * 0.2))
    return {"binomial_cases": cases, "binomial_max_abs_diff": worst,
            "fixed_point_residual": fp_resid, "fixed_point_converged": occ.converged}


def check_survival() -> dict:
    out = {}
    # Degenerate window: probabilistic form == deterministic inequality.
    ok = 0
    total = 0
    for cap in (4, 8, 16):
        for others in range(0, 20):
            # window = exactly `others` cycles of one session => binomial count = others
            prob = S.survival_probability(capacity=cap, target_units=1, resume_units=1,
                                          other_unit=1, other_sessions=1,
                                          window_samples=[(float(others), 1.0)],
                                          cycle_s=1.0, law="binomial")
            det = S.survives(cap, S.Window(target_units=1,
                                           window_units=(1,) * others + (1,)))
            total += 1
            ok += int((prob == 1.0) == det and prob in (0.0, 1.0))
    out["degenerate_window_agree"] = f"{ok}/{total}"
    # Mean of both count laws == (N-1) * w / c.
    worst = 0.0
    for law in ("binomial", "poisson"):
        for w in (0.3, 1.0, 2.7):
            pmf = S.admissions_in_window_pmf(other_sessions=5, window_s=w, cycle_s=1.3,
                                             law=law, upto=400)
            mean = sum(k * p for k, p in enumerate(pmf))
            worst = max(worst, abs(mean - 5 * w / 1.3))
    out["count_law_mean_max_abs_diff"] = worst
    # Sequential threshold on a synthetic pool: survive iff 1 + B + 1 <= cap.
    agree = all(
        S.survives(c, S.sequential_window(target_units=1, background_units=[1] * b,
                                          resume_units=1)) == (b <= c - 2)
        for c in (3, 5, 9) for b in range(0, 12))
    out["sequential_threshold_agrees"] = agree
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    res = {"seed": args.seed,
           "dp_vs_brute_force": check_dp(args.seed),
           "interpolation_rule": check_interpolation(args.seed + 1),
           "occupancy": check_occupancy(),
           "survival": check_survival()}
    print(json.dumps(res, indent=2, ensure_ascii=False))
    d = res["dp_vs_brute_force"]
    i = res["interpolation_rule"]
    o = res["occupancy"]
    s = res["survival"]
    ok = (d["matches"] == d["cases"] and i["bit_identical"] == i["cases"]
          and o["binomial_max_abs_diff"] < 1e-12 and o["fixed_point_residual"] < 1e-9
          and s["count_law_mean_max_abs_diff"] < 1e-9
          and s["sequential_threshold_agrees"]
          and s["degenerate_window_agree"].split("/")[0] == s["degenerate_window_agree"].split("/")[1])
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    if args.output:
        args.output.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
