#!/usr/bin/env python3
"""GTASK08: blind selection of the GPU configurations (directive G-03 section 4).

No measurement is read. Inputs: GTASK05 step costs (``gpu_cost``), GTASK01-04
semantics (``gpu_mt_sim``), the analytic v1 GPU instance (``gpu_mt_model``),
and selection plans generated here with their own seeds.

Rule, fixed before it is run (the output is whatever it gives):

1. ``max_num_seqs = 8`` for every configuration (the directive's BASE),
   ``--max-num-batched-tokens 2048``, block 16.
2. Preemption cannot happen when ``pool - 1 >= 8 * ceil(max request / 16)``.
   The bound uses the workload's **worst case** (opening prompt 1,600 +
   8 turns x (segment 8 + generation 256) = 3,712 tokens -> 232 blocks), so it
   holds for every plan drawn from the law, not only the ones generated
   today: ``pool >= 1,857``. Every generated plan is also checked against
   its own maximum.
3. BASE pool = the smallest multiple of 100 that satisfies 2 (1,900);
   capture grid = vLLM's default for ``max_num_seqs = 8``: (1, 2, 4, 8, 16).
4. Candidate N = 16, 18, ..., 32, three selection plans each
   (seed ``20262100 + i``, ``cycle_s`` 6.0 -- the stagger only).
   N is feasible when the BASE reuse rate predicted by the simulator (LRU)
   and by the analytic model, each at both cost bounds, lies in
   [0.40, 0.85], and the simulator's spread across the three plans (lo
   bound) is at most 0.25 (excludes cells where reuse collapses in some
   plans and not others). The confirmatory N are the three smallest
   consecutive feasible N (step 2); fewer if there are not three.
5. POOL pool = the largest multiple of 100 in [2,000, 4,000] whose predicted
   reuse at the middle confirmatory N is <= 0.85 for both predictors and
   both bounds (larger pool, still inside the informative range).
   POOL grid = BASE grid.
   **Amendment 1 (after the first run, before any measurement):** rule 5 has
   no solution -- BASE at the middle N is already at 0.848, so every larger
   pool exceeds 0.85 (first run log kept in results; ``rule5_solutions`` in the output records the empty set).
   Rule 5' relaxes only the ceiling: the largest such pool with reuse
   <= 0.90. Everything else is unchanged.
6. POOL+GRID = POOL pool with a per-N grid: B3 DP (``optimal_grid``,
   GTASK05 ``F[b]``) over the analytic model's step-weighted h(n) for POOL at
   that N (lo bound), widths 1..8, 4 widths (as many as the default grid has
   up to 8), plus 16 for mixed steps as in the default grid.

usage: select_configs.py --out-dir <abs> --plans-dir <abs>
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

import make_plan as MP  # noqa: E402
from gpu_mt_model import analytic, dp_grid, plan_samples  # noqa: E402
from gpu_mt_sim import GpuConfig, simulate, window_metrics  # noqa: E402

GAP_FILE = "/home/csdc/kyeom/Project/vllm-continuum/results/tracelab/summary.json"
GAP = f"toolmix:{GAP_FILE}:60"
MNS = 8
WORST_TOKENS = 1600 + 8 * (8 + 256)
BOUND_BLOCKS = 1 + MNS * math.ceil(WORST_TOKENS / 16)
BASE_POOL = int(math.ceil(BOUND_BLOCKS / 100) * 100)
BASE_GRID = (1, 2, 4, 8, 16)
NS = tuple(range(16, 33, 2))
REPS = 3
SEED0 = 20262100
LO, HI = 0.40, 0.85


def sim_reuse(plans, cfg, bound, eviction="lru"):
    ms = [window_metrics(simulate(p, cfg, eviction=eviction, bound=bound), cfg, bound) for p in plans]
    return ms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--plans-dir", required=True, type=Path,
                    help="selection plan files (regenerable from their seeds; not tracked)")
    a = ap.parse_args()
    out = a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    a.plans_dir.mkdir(parents=True, exist_ok=True)
    plans_by_n, plan_index = {}, []
    i = 0
    for n in NS:
        plans_by_n[n] = []
        for r in range(REPS):
            pid = f"gsel-n{n}-r{r}"
            plan = MP.build(n=n, seed=SEED0 + i, plan_id=pid, cycle_s=6.0, gap=GAP)
            sha = MP.write(plan, a.plans_dir / f"{pid}.json")
            mx = MP.max_context_tokens(plan)
            assert mx <= WORST_TOKENS
            plan_index.append({"plan_id": pid, "n": n, "rep": r, "seed": SEED0 + i,
                               "content_sha256": sha, "max_context": mx})
            plans_by_n[n].append(plan)
            i += 1
    base = GpuConfig("BASE", BASE_POOL, MNS, BASE_GRID)
    table = {}
    for n in NS:
        st = plan_samples(plans_by_n[n])
        row = {}
        for b in ("lo", "hi"):
            ms = sim_reuse(plans_by_n[n], base, b)
            fm = sim_reuse(plans_by_n[n], base, b, "fifo")
            an = analytic(n, base, st, bound=b)
            row[b] = {"sim_reuse": statistics.mean(m["reuse_rate"] for m in ms),
                      "sim_spread": max(m["reuse_rate"] for m in ms) - min(m["reuse_rate"] for m in ms),
                      "sim_device_ms": 1e3 * statistics.mean(m["device_per_turn_s"] for m in ms),
                      "sim_fifo_reuse": statistics.mean(m["reuse_rate"] for m in fm),
                      "an_reuse": an["reuse_rate"], "an_device_ms": 1e3 * an["device_per_turn_s"],
                      "an_mean_running": an["mean_running"]}
        row["feasible"] = all(LO <= row[b][k] <= HI for b in ("lo", "hi")
                              for k in ("sim_reuse", "an_reuse")) and row["lo"]["sim_spread"] <= 0.25
        table[n] = row
        print(n, json.dumps({b: {k: round(v, 3) for k, v in row[b].items()} for b in ("lo", "hi")}),
              row["feasible"], flush=True)
    feas = [n for n in NS if table[n]["feasible"]]
    chosen = None
    for n in feas:
        if n + 2 in feas and n + 4 in feas:
            chosen = [n, n + 2, n + 4]
            break
    if chosen is None:
        chosen = feas[:3]
    if not chosen:
        raise SystemExit("no feasible N")
    mid = chosen[len(chosen) // 2]
    st_mid = plan_samples(plans_by_n[mid])
    pool_scan = {}
    pool_pick = None
    ceiling = 0.90   # rule 5' (amendment 1); rule 5 used 0.85 and had no solution
    for pool in range(4000, 1999, -100):
        cfg = GpuConfig("POOL", pool, MNS, BASE_GRID)
        s_lo = statistics.mean(m["reuse_rate"] for m in sim_reuse(plans_by_n[mid], cfg, "lo"))
        s_hi = statistics.mean(m["reuse_rate"] for m in sim_reuse(plans_by_n[mid], cfg, "hi"))
        pool_scan[pool] = {"sim_lo": s_lo, "sim_hi": s_hi}
        if max(s_lo, s_hi) > ceiling:
            continue
        a_lo = analytic(mid, cfg, st_mid, bound="lo")["reuse_rate"]
        a_hi = analytic(mid, cfg, st_mid, bound="hi")["reuse_rate"]
        pool_scan[pool].update({"an_lo": a_lo, "an_hi": a_hi})
        print("pool", pool, round(s_lo, 3), round(s_hi, 3), round(a_lo, 3), round(a_hi, 3), flush=True)
        if max(a_lo, a_hi) <= ceiling:
            pool_pick = pool
            break
    rule5 = {p: v for p, v in pool_scan.items()}
    rule5_ok = [p for p, v in pool_scan.items() if max(v["sim_lo"], v["sim_hi"]) <= HI
                and max(v.get("an_lo", 1), v.get("an_hi", 1)) <= HI]
    if pool_pick is None:
        raise SystemExit("no POOL size satisfies rule 5'")
    grids = {}
    for n in chosen:
        st = plan_samples(plans_by_n[n])
        an = analytic(n, GpuConfig("POOL", pool_pick, MNS, BASE_GRID), st, bound="lo")
        grids[n] = {"grid": list(dp_grid(an["h"], top=MNS, k=4)), "h": an["h"]}
    sel = {"rule": "select_configs.py docstring", "max_num_seqs": MNS, "budget": 2048,
           "worst_request_tokens": WORST_TOKENS, "preemption_bound_blocks": BOUND_BLOCKS,
           "base_pool": BASE_POOL, "base_grid": list(BASE_GRID), "pool_pool": pool_pick,
           "confirmatory_n": chosen, "feasible_n": feas, "per_n_grid": grids,
           "table": {str(k): v for k, v in table.items()},
           "pool_scan": {str(k): v for k, v in pool_scan.items()},
           "rule5_solutions": rule5_ok, "rule5_ceiling": HI, "rule5p_ceiling": ceiling,
           "selection_plans": plan_index, "gap_file": GAP_FILE}
    (out / "selection.json").write_text(json.dumps(sel, indent=1) + "\n")
    print("chosen", chosen, "BASE", BASE_POOL, "POOL", pool_pick,
          {n: g["grid"] for n, g in grids.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
