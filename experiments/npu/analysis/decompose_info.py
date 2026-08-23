#!/usr/bin/env python3
"""Which information the remaining headroom is carried by.

The offline bound knows everything and finds a saving. Blind policies find
none. Between those sits a set of restricted knowledge levels, and pricing
each one says what a runtime policy would have to observe -- or proves that no
per-session policy can get there at all, because the value is in agreeing
rather than in knowing.

  (a) omniscient          the bound: joint search over hold vectors
  (b) return times        when peers come back, nothing else
  (c) generation lengths  when running requests stop decoding, nothing else
  (d) both
  (e) omniscient, uncoordinated   full knowledge, decided one session at a time

(a) minus (e) is the price of coordination: knowledge cannot buy it.

Policy parameters are tuned on exploration seeds and scored on evaluation
seeds, per TASK27.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from continuum.policy.lookahead import Informed  # noqa: E402
from continuum.policy.oracle import search, search_independent  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
import foresight as F  # noqa: E402


def busy(descriptor, sessions, *, policy=None, budget=0.0,
         peers=False, generation=False) -> float:
    cfg = SimConfig(max_running_requests=8, return_policy=policy,
                    return_budget_s=budget, reveal_peers=peers,
                    reveal_generation=generation)
    return simulate(descriptor, sessions, cfg).busy_s


def make(descriptor, *, peers: bool, generation: bool, min_saving_s: float):
    return Informed(bucket_sizes=descriptor.bucket_sizes,
                    fixed_s_by_bucket=dict(descriptor.step_cost_model.fixed_s_by_bucket),
                    use_peers=peers, use_generation=generation,
                    min_saving_s=min_saving_s)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gap", default="toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60")
    p.add_argument("--explore-seeds", default="20260910,20260921,20260932")
    p.add_argument("--eval-seeds", default="20260943,20260954,20260965")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--budgets", default="1,2,5")
    p.add_argument("--min-savings", default="0,0.001,0.005,0.02",
                   help="candidate guards, in seconds of predicted saving")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    print(f"gap 법칙: {F.set_gap(args.gap)}")
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D

    explore = [int(x) for x in args.explore_seeds.split(",")]
    evals = [int(x) for x in args.eval_seeds.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    ns = [int(x) for x in args.sessions.split(",")]
    budgets = [float(x) for x in args.budgets.split(",")]
    guards = [float(x) for x in args.min_savings.split(",")]

    CHANNELS = (("b", True, False), ("c", False, True), ("d", True, True))
    report = {"gap": args.gap, "rows": [], "guards": {}}

    for eps in budgets:
        print(f"\n{'='*74}\n=== ε = {eps:g} s ===")
        # Tune the guard per channel set on exploration seeds only.
        chosen = {}
        for tag, pe, ge in CHANNELS:
            best = None
            for g in guards:
                base = pol = 0.0
                for s in explore:
                    for n in ns:
                        for b in blocks:
                            ss = F.plan(n, b, s)
                            base += busy(D, ss)
                            pol += busy(D, ss, policy=make(D, peers=pe, generation=ge,
                                                           min_saving_s=g),
                                        budget=eps, peers=pe, generation=ge)
                sav = 1 - pol / base
                if best is None or sav > best[1]:
                    best = (g, sav)
            chosen[tag] = best[0]
        report["guards"][str(eps)] = chosen
        print("탐색 seed에서 고른 guard(s): " + "  ".join(
            f"({t}) {chosen[t]:g}" for t, _, _ in CHANNELS))

        print(f"\n{'N':>3} {'(a) 전지':>9} {'(b) 반환시각':>12} {'(c) 생성길이':>12} "
              f"{'(d) 둘 다':>10} {'(e) 전지·독립':>13} {'(a)−(e)':>9}")
        for n in ns:
            cells = [(n, b, s) for s in evals for b in blocks]
            base = sum(busy(D, F.plan(*c)) for c in cells)
            omni = sum(search(D, F.plan(*c), SimConfig(max_running_requests=8),
                              budget_s=eps, seed=90000 + i).best.busy_s
                       for i, c in enumerate(cells))
            indep = sum(search_independent(D, F.plan(*c),
                                           SimConfig(max_running_requests=8),
                                           budget_s=eps).best.busy_s
                        for c in cells)
            vals = {}
            for tag, pe, ge in CHANNELS:
                tot = sum(busy(D, F.plan(*c),
                               policy=make(D, peers=pe, generation=ge,
                                           min_saving_s=chosen[tag]),
                               budget=eps, peers=pe, generation=ge) for c in cells)
                vals[tag] = 1 - tot / base
            sa = 1 - omni / base
            se = 1 - indep / base
            row = {"epsilon_s": eps, "N": n, "busy_base_s": base,
                   "a_omniscient": sa, "b_return_times": vals["b"],
                   "c_generation": vals["c"], "d_both": vals["d"],
                   "e_uncoordinated": se, "coordination_price": sa - se}
            report["rows"].append(row)
            print(f"{n:>3} {100*sa:>8.2f}% {100*vals['b']:>11.2f}% {100*vals['c']:>11.2f}% "
                  f"{100*vals['d']:>9.2f}% {100*se:>12.2f}% {100*(sa-se):>8.2f}%")

    print(f"\n{'='*74}\n=== 판정 분기 (사전 명시) ===")
    print("(c) 또는 (d)가 headroom(a)의 절반 이상 → 생성 길이 예측 기반 runtime 정책 부활")
    print("어느 한계 정보도 절반을 못 넘음 → headroom은 결합 조율의 산물, compile-time이 유일 경로")
    verdicts = {}
    for eps in budgets:
        rows = [r for r in report["rows"] if r["epsilon_s"] == eps]
        half = []
        for r in rows:
            if r["a_omniscient"] <= 0:
                half.append(None)
                continue
            half.append(max(r["c_generation"], r["d_both"]) / r["a_omniscient"])
        ok = [h for h in half if h is not None and h >= 0.5]
        verdicts[str(eps)] = {"ratios": half, "n_over_half": len(ok), "n": len(rows)}
        print(f"  ε={eps:g} s: max((c),(d))/(a) = " +
              " ".join("정의불가" if h is None else f"{h:.2f}" for h in half) +
              f"  → 절반 이상인 N: {len(ok)}/{len(rows)}")
    report["verdicts"] = verdicts
    total_over = sum(v["n_over_half"] for v in verdicts.values())
    total_n = sum(v["n"] for v in verdicts.values())
    branch = "runtime 후보 부활" if total_over > total_n / 2 else "compile-time이 유일 경로"
    report["branch"] = branch
    print(f"\n분기 결과: **{branch}** (절반 이상인 칸 {total_over}/{total_n})")
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
