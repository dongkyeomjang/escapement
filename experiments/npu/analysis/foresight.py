#!/usr/bin/env python3
"""How much of the offline headroom survives when foresight gets noisy.

Three information levels are priced against the same plans:

  (a) omniscient   the offline bound: knows the whole resulting schedule
  (b) ready times  knows exactly when peers come back, nothing else
  (c) noisy        the same, seen through multiplicative prediction error

Reading the three as a curve turns "there is headroom" into "here is how
accurate a predictor has to be before the headroom is reachable", which is the
only form of the answer that says whether to build one.

The policy family used for (b) and (c) has one parameter. It is tuned on
exploration seeds and scored on held-out evaluation seeds, because TASK27
showed that tuning and scoring on the same plans manufactures a gain that does
not survive a new seed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from continuum.policy.lookahead import (  # noqa: E402
    Lookahead,
    NoisyClock,
    sigma_log_for_relative_error,
)
from continuum.policy.oracle import search  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.agentic import (  # noqa: E402
    Distribution,
    generate_sessions,
)
from continuum.workload.tools import load_mix  # noqa: E402

FIRST = Distribution("uniform", low=800, high=1600)
LATER = Distribution("fixed", value=8)
GEN = Distribution("uniform", low=32, high=256)
GAP = Distribution("uniform", low=1, high=5)

#: Set by --gap to swap the synthetic gap law for a measured tool population.
_SAMPLER = None


def set_gap(spec: str) -> str:
    """Install the gap law. ``uniform:1:5`` keeps every earlier task's plans."""
    global _SAMPLER
    if spec.startswith("toolmix:"):
        _, path, cap = spec.split(":", 2)
        mix = load_mix(path, cap_s=float(cap))
        _SAMPLER = lambda rng: mix.draw(rng)[1]  # noqa: E731
        return f"toolmix({len(mix.tools)} tools, cap {cap}s)"
    _SAMPLER = None
    return spec


def plan(n: int, block: int, seed: int):
    return generate_sessions(session_count=n, turns_per_session=2,
                             first_segment=FIRST, later_segment=LATER,
                             generation=GEN,
                             gap_seconds=(Distribution("fixed", value=0)
                                          if _SAMPLER else GAP),
                             gap_sampler=_SAMPLER,
                             base_seed=seed, block_id=f"n{n}b{block}")


def busy(descriptor, sessions, *, policy=None, budget=0.0, clock=None) -> float:
    cfg = SimConfig(max_running_requests=8, return_policy=policy,
                    return_budget_s=budget, peer_clock=clock)
    return simulate(descriptor, sessions, cfg).busy_s


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--explore-seeds", default="20260830,20260841,20260850")
    p.add_argument("--eval-seeds", default="20260860,20260871,20260882")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--sessions", default="6,8,10,12")
    p.add_argument("--budget", type=float, default=1.0)
    p.add_argument("--ratios", default="0,0.1,0.25,0.5,1,2",
                   help="noise std as a multiple of the gap distribution's std")
    p.add_argument("--min-gains", default="1,2,3")
    p.add_argument("--noise-seed", type=int, default=20260901)
    p.add_argument("--gap", default="uniform:1:5",
                   help="uniform:1:5 (default) or toolmix:<summary.json>:<cap_s>")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    print(f"gap 법칙: {set_gap(args.gap)}")
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D

    explore = [int(x) for x in args.explore_seeds.split(",")]
    evals = [int(x) for x in args.eval_seeds.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    ns = [int(x) for x in args.sessions.split(",")]
    ratios = [float(x) for x in args.ratios.split(",")]
    gains = [int(x) for x in args.min_gains.split(",")]
    eps = args.budget

    def cells(seeds):
        return [(n, b, s) for s in seeds for n in ns for b in blocks]

    # Noise scale is fixed from the gap law once, not per cell, so the same
    # grid point means the same thing everywhere.
    sample_gaps = [t.gap_after_s for (n, b, s) in cells(explore)
                   for sess in plan(n, b, s) for t in sess.turns if t.gap_after_s > 0]
    sigmas = {r: sigma_log_for_relative_error(sample_gaps, r, seed=args.noise_seed)
              for r in ratios}
    gmean = statistics.mean(sample_gaps)
    gstd = statistics.stdev(sample_gaps)
    print(f"gap 분포: 평균 {gmean:.3f} s, 표준편차 {gstd:.3f} s (n={len(sample_gaps)})")
    print("노이즈 격자: " + "  ".join(
        f"ρ={r:g}→σ_log {sigmas[r]:.4f}" for r in ratios))

    print("\n=== 탐색 seed에서 min_gain 선택 (ε=%.1f s, 무노이즈) ===" % eps)
    best_gain, best_sav = None, -9.0
    for g in gains:
        base = pol = 0.0
        for (n, b, s) in cells(explore):
            ss = plan(n, b, s)
            base += busy(D, ss)
            pol += busy(D, ss, policy=Lookahead(min_gain=g), budget=eps,
                        clock=NoisyClock(sigma_log=0.0, seed=args.noise_seed))
        sav = 1 - pol / base
        print(f"  min_gain={g}: 절감 {100*sav:+.2f}%")
        if sav > best_sav:
            best_gain, best_sav = g, sav
    print(f"  → 선택 min_gain={best_gain}")

    print("\n=== 평가 seed에서 정보 수준별 이득 (ε=%.1f s) ===" % eps)
    report = {"epsilon_s": eps, "min_gain": best_gain, "sigmas": sigmas,
              "gap_mean_s": gmean, "gap_std_s": gstd, "rows": []}
    print(f"{'N':>3} {'(a) 전지':>10} {'(b) 반환시각':>12} "
          + "".join(f"ρ={r:g}".rjust(9) for r in ratios if r > 0))
    for n in ns:
        cs = [(n, b, s) for s in evals for b in blocks]
        base = sum(busy(D, plan(*c)) for c in cs)
        omni = sum(search(D, plan(*c), SimConfig(max_running_requests=8),
                          budget_s=eps, seed=args.noise_seed + i).best.busy_s
                   for i, c in enumerate(cs))
        row = {"N": n, "busy_base_s": base, "busy_omniscient_s": omni,
               "saving_omniscient": 1 - omni / base, "noisy": {}}
        cells_out = []
        for r in ratios:
            tot = 0.0
            for i, c in enumerate(cs):
                clock = NoisyClock(sigma_log=sigmas[r], seed=args.noise_seed + 1000 * i)
                tot += busy(D, plan(*c), policy=Lookahead(min_gain=best_gain),
                            budget=eps, clock=clock)
            sav = 1 - tot / base
            row["noisy"][str(r)] = {"busy_s": tot, "saving": sav}
            if r == 0:
                row["saving_ready_times"] = sav
            else:
                cells_out.append(f"{100*sav:+8.2f}%")
        report["rows"].append(row)
        print(f"{n:>3} {100*row['saving_omniscient']:>9.2f}% "
              f"{100*row['saving_ready_times']:>11.2f}% " + " ".join(cells_out))

    # sigma* : where half of the zero-noise foresight gain is left.
    print("\n=== 정확도 문턱 σ* (무노이즈 이득의 절반이 남는 ρ) ===")
    report["sigma_star"] = {}
    for row in report["rows"]:
        g0 = row["saving_ready_times"]
        if g0 <= 0:
            report["sigma_star"][str(row["N"])] = None
            print(f"  N={row['N']:>2}: 무노이즈 이득이 {100*g0:+.2f}%라 정의되지 않음")
            continue
        half = g0 / 2
        prev_r, prev_v = 0.0, g0
        star = None
        for r in sorted((x for x in ratios if x > 0)):
            v = row["noisy"][str(r)]["saving"]
            if v < half:
                star = prev_r + (prev_v - half) / (prev_v - v) * (r - prev_r)
                break
            prev_r, prev_v = r, v
        report["sigma_star"][str(row["N"])] = star
        if star is None:
            print(f"  N={row['N']:>2}: ρ={max(ratios):g}까지 절반 이상 유지 (σ* > {max(ratios):g})")
        else:
            print(f"  N={row['N']:>2}: σ* = {star:.3f} × gap std = {star*gstd:.3f} s")
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
