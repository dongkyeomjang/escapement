#!/usr/bin/env python3
"""G-10 B: plans and frozen predictions for the saturated cost-ratio check.

Prereg: docs/research/gpu/G10_B_PREREG.md. Run once, before any B lifecycle.

1. plans ``g10b-n{N}-r{r}`` (N = 28 required, 25 extension; r = 0..9), seeds
   20264100 + 10 * k + r (k = 0 for N = 28, 1 for N = 25), the GTASK09/20 law
   (``make_plan.build``: opening U(800, 1600), later segment 8, generation
   U(32, 256), 8 turns, toolmix gap cap 60 s), ``cycle_s`` = analytic POOL
   prediction (the GTASK20 rule);
2. sim LRU (``gpu_mt_sim``) with the current context-aware step time
   (GTASK20 predictor (1) ``ctx``: ``predict_blind.StepCost("ctx")``, GTASK18
   c = 2.120e-4 ms/token) for GPU_BASE (1,900 blocks) and GPU_KV (2,300),
   grid (1, 2, 4, 8, 16), ``max_num_seqs`` 8, both prefill-cost bounds.

Per replicate: reuse (requests, tokens), PRED cost per call = the price
channel (``gpu_cost.step_ms`` at the same bound) over the simulated window
steps / window requests (the GTASK20 definition), the simulated step-time sum
per call (report only), decode-only h, queue waits.

usage: predict_b.py --out <abs json> [--jobs 24]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
MT = HERE.parent / "multiturn"
REPO = HERE.parents[2]
sys.path.insert(0, str(MT))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

import make_plan as MP  # noqa: E402
from gpu_mt_model import analytic, plan_samples  # noqa: E402
import gpu_mt_sim as S  # noqa: E402
from gpu_mt_sim import GpuConfig  # noqa: E402
import gpu_cost as C  # noqa: E402
from predict_blind import GAP, StepCost  # noqa: E402

NS = {28: 0, 25: 1}          # N -> seed block k
REPS = 10
SEED0 = 20264100
BOUNDS = ("lo", "hi")
GRID = (1, 2, 4, 8, 16)
CFGS = {"GPU_BASE": GpuConfig("GPU_BASE", 1900, 8, GRID),
        "GPU_KV": GpuConfig("GPU_KV", 2300, 8, GRID)}
PLAN_DIR = HERE / "plans_b"


def seed_of(n: int, r: int) -> int:
    return SEED0 + 10 * NS[n] + r


def run_one(job) -> dict:
    n, r, cname, bound = job
    from continuum.workload.multiturn import MultiTurnPlan
    cfg = CFGS[cname]
    plan = MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"g10b-n{n}-r{r}.json").read_text()))
    cost = StepCost("ctx", None, seed=0)
    res = S.simulate(plan, cfg, eviction="lru", bound=bound, step_cost=cost)
    m = S.window_metrics(res, cfg, bound)
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    ws = [s for s in res["steps"] if w0 <= s.start_s < w1]
    price = sum(C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=GRID, bound=bound)
                for s in ws) / 1e3
    wall = sum(s.duration_s for s in ws)
    reqs = [q for q in res["requests"] if w0 <= q.arrival_s < w1]
    waits = sorted(q.admit_s - q.arrival_s for q in reqs)
    nw = m["requests_in_window"]
    return {"n": n, "rep": r, "config": cname, "bound": bound,
            "reuse": m["reuse"], "reuse_rate": m["reuse_rate"],
            "hit_tokens": m["hit_tokens"], "reusable_tokens": m["reusable_tokens"],
            "token_reuse_ratio": m["token_reuse_ratio"], "hit_shape": m["hit_shape"],
            "requests_in_window": nw, "price_s": price, "price_per_turn_s": price / nw,
            "simwall_s": wall, "simwall_per_turn_s": wall / nw,
            "steps_in_window": len(ws),
            "steps_by_type": dict(Counter("decode" if s.prefill_tokens == 0 else
                                          ("prefill" if s.decodes == 0 else "mixed") for s in ws)),
            "h_decode": dict(Counter(s.decodes for s in ws if s.decodes >= 1)),
            "queue_wait_mean_s": statistics.fmean(waits) if waits else None,
            "queue_wait_median_s": waits[len(waits) // 2] if waits else None,
            "max_running": m["max_running"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    from continuum.workload.multiturn import MultiTurnPlan
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    for n in NS:
        for r in range(REPS):
            pid = f"g10b-n{n}-r{r}"
            prov = MP.build(n=n, seed=seed_of(n, r), plan_id=pid, cycle_s=6.0, gap=GAP)
            cyc = analytic(n, CFGS["GPU_KV"], plan_samples([prov]), bound="lo")["cycle_s"]
            plan = MP.build(n=n, seed=seed_of(n, r), plan_id=pid, cycle_s=round(cyc, 3), gap=GAP)
            path = PLAN_DIR / f"{pid}.json"
            sha = MP.write(plan, path)
            mx = MP.max_context_tokens(plan)
            need = 1 + 8 * -(-mx // 16)
            if need > 1900:
                raise SystemExit(f"{pid}: preemption-free bound {need} > 1900")
            index.append({"plan_id": pid, "n": n, "rep": r, "seed": seed_of(n, r),
                          "cycle_s": plan.spec["cycle_s"], "content_sha256": sha,
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "max_context": mx, "preemption_blocks_needed": need})
            print(pid, seed_of(n, r), plan.spec["cycle_s"], sha[:12], mx, need, flush=True)
            MultiTurnPlan.from_json(json.loads(path.read_text()))
    (PLAN_DIR / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    jobs = [(n, r, c, b) for n in NS for r in range(REPS) for c in CFGS for b in BOUNDS]
    with ProcessPoolExecutor(a.jobs) as ex:
        runs = list(ex.map(run_one, jobs))
    cells: dict = {}
    for b in BOUNDS:
        for n in NS:
            per = {c: sorted((x for x in runs if (x["bound"], x["n"], x["config"]) == (b, n, c)),
                             key=lambda x: x["rep"]) for c in CFGS}
            cell = {}
            for c, rs in per.items():
                h = Counter()
                for x in rs:
                    h.update({int(d): v for d, v in x["h_decode"].items()})
                ht = sum(h.values())
                cell[c] = {"reuse": [sum(x["reuse"][0] for x in rs), sum(x["reuse"][1] for x in rs)],
                           "hit_tokens": sum(x["hit_tokens"] for x in rs),
                           "reusable_tokens": sum(x["reusable_tokens"] for x in rs),
                           "price_per_turn_s_pooled": sum(x["price_s"] for x in rs)
                           / sum(x["requests_in_window"] for x in rs),
                           "h_decode": {d: v / ht for d, v in sorted(h.items())},
                           "per_rep": rs}
                cell[c]["reuse_rate"] = cell[c]["reuse"][0] / cell[c]["reuse"][1]
                cell[c]["token_reuse_ratio"] = cell[c]["hit_tokens"] / cell[c]["reusable_tokens"]
            ratios = [k["price_per_turn_s"] / bb["price_per_turn_s"]
                      for k, bb in zip(per["GPU_KV"], per["GPU_BASE"])]
            wratios = [k["simwall_per_turn_s"] / bb["simwall_per_turn_s"]
                       for k, bb in zip(per["GPU_KV"], per["GPU_BASE"])]
            cell["R_PRED"] = {"per_rep": ratios, "median": statistics.median(ratios)}
            cell["R_PRED_simwall_report_only"] = {"per_rep": wratios, "median": statistics.median(wratios)}
            cells.setdefault(b, {})[str(n)] = cell
    out = {"inputs": {"predictor": "gpu_mt_sim LRU + predict_blind.StepCost('ctx')",
                      "C_CTX_ms_per_token": 2.120e-4, "L_PRICE": 128,
                      "gpu_cost_sha256": hashlib.sha256((MT / "gpu_cost.py").read_bytes()).hexdigest(),
                      "gpu_mt_sim_sha256": hashlib.sha256((MT / "gpu_mt_sim.py").read_bytes()).hexdigest(),
                      "predict_blind_sha256": hashlib.sha256((MT / "predict_blind.py").read_bytes()).hexdigest(),
                      "python": sys.version},
           "plans": index, "cells": cells}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("sha256", hashlib.sha256(a.out.read_bytes()).hexdigest())
    for b in BOUNDS:
        for n in NS:
            c = cells[b][str(n)]
            print(b, n, {k: (round(c[k]["reuse_rate"], 3), round(c[k]["token_reuse_ratio"], 3),
                             round(c[k]["price_per_turn_s_pooled"], 4)) for k in CFGS},
                  "R_PRED", round(c["R_PRED"]["median"], 4), "simwall", round(c["R_PRED_simwall_report_only"]["median"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
