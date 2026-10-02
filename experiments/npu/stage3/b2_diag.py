#!/usr/bin/env python3
"""B2 diagnosis: why the analytic occupancy over-predicts BASE running
(directive 07 work C.1, TASK90). Development set: N = 12, 14, 16 (TASK82, 87).

A ladder from the B2 prediction to the observation, one assumption at a time,
with the step simulator as the laboratory (it reproduces the observed h best,
TASK87). Every rung reports the step-weighted mean running in the evaluation
window -- the quantity ``[BUCKET]`` counts and the observation is measured in.

  A  B2 as predicted (v1 analytic fixed point, step share)
  B  B2 with no prefill (E[P] = 0, phi = 1)
  C  sim, exponential decode lengths, exponential gaps, prefill not exclusive
  C' sim, exponential decode lengths, the plan's gaps, prefill not exclusive
  D  sim, exponential decode lengths, exponential gaps, exclusive prefill
  E  sim, exponential decode lengths, the plan's gaps, exclusive prefill
  F  sim, the plan (= the sim predictor)
  O  observed

Attribution (each a difference of rungs):
  base PS/step model         C - B   (both exponential, no prefill)
  (i) prefill mean field     (D - C) - (A - B)   (exclusive prefill in the sim
                             minus B2's uniform slowdown phi)
  gap shape                  E - D   (with exclusive prefill); C' - C is the
                             same change without it (reported, not in the sum)
  (iii) service distribution F - E   (U(32, 256) instead of exponential; with a
                             queue this is also where FCFS leaves product
                             form -- (ii) alone is exact for an exponential
                             FCFS load-dependent station, so it has no
                             separate rung)
  simulator error            O - F

Exponential variants keep the per-request means of the plan (decode steps
``G``, gaps of non-final turns scaled so the per-request mean equals ``Z``;
the renewal at a session's end stays immediate as in the plan), drawn with
seeds ``20261700 + 10 * N + r`` (decode lengths) and that + 1 (gaps), so rungs
that change only the gaps keep the same decode lengths.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import dataclasses
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
import mt_predict_v11 as Q  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
RUNS = {12: HERE.parents[2] / "results/npu/stage3/20260930-main/main_verdict.json",
        14: HERE.parents[2] / "results/npu/stage3/20261001-hiload/hiload_verdict.json",
        16: HERE.parents[2] / "results/npu/stage3/20261001-hiload/hiload_verdict.json"}


def plans_of(n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / ("INDEX.json" if n == 12 else "INDEX_HI.json")).read_text())
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])]


def step_mean(h: dict) -> float:
    return sum(int(k) * v for k, v in h.items()) / sum(h.values())


def transform(sessions, *, exp_gen: bool, exp_gap: bool, seed: int, g_mean: float, z_mean: float):
    rng_gen = random.Random(seed)          # separate streams: a rung that changes only the
    rng_gap = random.Random(seed + 1)      # gaps keeps exactly the same decode lengths
    nonfinal = sum(len(s.turns) - 1 for s in sessions)
    total = sum(len(s.turns) for s in sessions)
    gap_mean = z_mean * total / nonfinal
    out = []
    for s in sessions:
        turns = []
        for i, t in enumerate(s.turns):
            gen = t.generation_tokens
            gap = t.gap_after_s
            if exp_gen:
                gen = 1 + max(1, round(rng_gen.expovariate(1.0 / g_mean)))
            if exp_gap and i < len(s.turns) - 1:
                gap = rng_gap.expovariate(1.0 / gap_mean)
            turns.append(dataclasses.replace(t, generation_tokens=gen, gap_after_s=gap))
        out.append(dataclasses.replace(s, turns=tuple(turns)))
    return out


def sim_rung(args) -> float:
    n, cfg, r, exp_gen, exp_gap, exclusive = args
    grid, batch = P.CONFIGS[cfg]
    plan = plans_of(n)[r]
    st = P.plan_stats([plan])
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    if exp_gen or exp_gap:
        sessions = transform(sessions, exp_gen=exp_gen, exp_gap=exp_gap,
                             seed=20261700 + 10 * n + r, g_mean=st["gen_mean"] - 1,
                             z_mean=st["think_mean_s"])
    res = simulate(Q.descriptor_v2(grid, batch), sessions, SimConfig(
        max_running_requests=batch, session_start_s=start, successor=succ,
        semantics="descriptor", prefill_exclusive=exclusive))
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=120.0)
    w0 = rule.warmup_end([(slot_of[q.session_index], q.finish_s) for q in res.requests], plan.n_slots)
    h: dict[int, int] = defaultdict(int)
    for s in res.decode_steps:
        if w0 <= s.start_s < w0 + 120.0:
            h[s.running] += 1
    return step_mean(h)


def b2_rungs(n: int, cfg: str) -> tuple[float, float]:
    grid, batch = P.CONFIGS[cfg]
    plans = plans_of(n)
    st = P.plan_stats(plans)
    a = P.analytic(n, grid, batch, st)
    desc = P.descriptor(grid, batch)
    w0 = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                          think_mean_s=st["think_mean_s"], prefill_mean_s=0.0, max_running=batch)
    occ0 = O.solve_occupancy(w0, desc.step_time_s)
    return step_mean(a["h"]), step_mean(occ0.step_share)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--configs", default="BASE,BATCHONLY,TUNED")
    a = ap.parse_args()
    cfgs = a.configs.split(",")
    rungs = {"C": (True, True, False), "Cp": (True, False, False), "D": (True, True, True),
             "E": (True, False, True), "F": (False, False, True)}
    jobs = [(n, c, r, *rungs[k]) for n in RUNS for c in cfgs for r in range(5) for k in rungs]
    with ProcessPoolExecutor(max_workers=60) as ex:
        res = dict(zip(jobs, ex.map(sim_rung, jobs)))
        b2 = {(n, c): ex.submit(b2_rungs, n, c) for n in RUNS for c in cfgs}
        b2 = {k: v.result() for k, v in b2.items()}
    out = {}
    for n in RUNS:
        ver = json.loads(RUNS[n].read_text())["cells"]
        for c in cfgs:
            row = {"A": b2[(n, c)][0], "B": b2[(n, c)][1]}
            for k, flags in rungs.items():
                row[k] = statistics.mean(res[(n, c, r, *flags)] for r in range(5))
            row["O"] = step_mean(ver[f"{c}.n{n}"]["h_obs"])
            row["attribution"] = {
                "base_ps_step": row["C"] - row["B"],
                "i_prefill_mean_field": (row["D"] - row["C"]) - (row["A"] - row["B"]),
                "gap_shape": row["E"] - row["D"],
                "iii_service_distribution": row["F"] - row["E"],
                "simulator_error": row["O"] - row["F"],
                "gap_shape_without_exclusive_prefill": row["Cp"] - row["C"],
                "total_O_minus_A": row["O"] - row["A"]}
            out[f"{c}.n{n}"] = row
            print(c, n, {k: round(v, 3) for k, v in row.items() if k != "attribution"},
                  {k: round(v, 3) for k, v in row["attribution"].items()}, flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
