#!/usr/bin/env python3
"""G-07 task C: blind predictions for the collapse-region cells N = 25, 28.

Prereg: docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md. Steps (run once,
before any measurement of these cells):

1. plans ``gblind-n{N}-r{r}`` (r = 0..4, seed 20263000 + i), the GTASK09 law
   (``make_plan.build``, ``cycle_s`` = analytic POOL prediction);
2. POOL+GRID grid per N by GTASK08 rule 6 (``dp_grid`` over the analytic POOL
   h at that N, lo bound) on these plans -> ``selection/blind_grids.json``;
3. sim LRU (``gpu_mt_sim``) for every (N, configuration, plan, bound) with four
   step-time inputs; only the step duration differs:
   * ``ctx``  (1, primary)  price + C_CTX * (decode_ctx - decodes * L_PRICE),
     GTASK18 F1 slope, L_PRICE = mean decode context of the GTASK05 price load;
   * ``x1.210`` (2, calibrated on GTASK11 N = 20-26)  price * 1.210;
   * ``mode_dist`` (2', calibrated)  price * ratio drawn from the GTASK11
     lag-1 dispatch/price distribution of the step class (GTASK13 obs.json);
   * ``price`` (3, baseline)  GTASK05 price (= GTASK17 curve).
   Cost metrics are always the price channel over the simulated window steps
   (what the observation measures), at the same bound.

usage: predict_blind.py --obs <abs GTASK13 obs.json> --out <abs json> [--jobs 24]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

import make_plan as MP  # noqa: E402
from gpu_mt_model import analytic, dp_grid, plan_samples  # noqa: E402
import gpu_mt_sim as S  # noqa: E402
from gpu_mt_sim import GpuConfig  # noqa: E402
import gpu_cost as C  # noqa: E402
from sim_timescale import ratio_table  # noqa: E402
from step_classes import step_class  # noqa: E402

GAP_FILE = "/home/csdc/kyeom/Project/vllm-continuum/results/tracelab/summary.json"
GAP = f"toolmix:{GAP_FILE}:60"
NS = (25, 28)
REPS = 5
SEED0 = 20263000
BOUNDS = ("lo", "hi")
CONFIGS = ("BASE", "POOL", "POOL+GRID")
C_CTX = 2.120e-4        # ms per context token, GTASK18 F1 (ctx_result/summary.json)
L_PRICE = 128           # GTASK05 FULL load: prompt 64 + mean generated position 64
X_CAL = 1.210           # GTASK13 x1.210 (GTASK15 lag-1 window wall/price)
PREDICTORS = ("ctx", "x1.210", "mode_dist", "price")
PLAN_DIR = HERE / "plans" / "blind"
SEL = HERE / "selection" / "selection.json"
GRIDS = HERE / "selection" / "blind_grids.json"


def cfgs(sel: dict, n: int, grids: dict) -> dict:
    base = tuple(sel["base_grid"])
    return {"BASE": GpuConfig("BASE", sel["base_pool"], sel["max_num_seqs"], base),
            "POOL": GpuConfig("POOL", sel["pool_pool"], sel["max_num_seqs"], base),
            "POOL+GRID": GpuConfig("POOL+GRID", sel["pool_pool"], sel["max_num_seqs"],
                                   tuple(grids[str(n)]["grid"]))}


class StepCost:
    def __init__(self, kind: str, table: dict | None, seed: int):
        self.kind, self.table = kind, table
        self.rng = random.Random(seed)
        self.allr = sorted(x for v in (table or {}).values() for x in v)

    def __call__(self, *, decodes, prefill_tokens, grid, bound, decode_ctx):
        base = C.step_ms(decodes=decodes, prefill_tokens=prefill_tokens, grid=grid, bound=bound)
        if self.kind == "price":
            return base
        if self.kind == "ctx":
            return base + C_CTX * (decode_ctx - decodes * L_PRICE) if decodes else base
        if self.kind == "x1.210":
            return base * X_CAL
        mode = C.mode(decodes, prefill_tokens, grid)
        v = self.table.get(step_class(mode, decodes, prefill_tokens)) or self.allr
        return base * v[self.rng.randrange(len(v))]


def run_one(job) -> dict:
    n, r, cname, cfg, kind, bound, table = job
    from continuum.workload.multiturn import MultiTurnPlan
    plan = MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"gblind-n{n}-r{r}.json").read_text()))
    cost = StepCost(kind, table, seed=SEED0 + 1000 * n + 10 * r + CONFIGS.index(cname))
    res = S.simulate(plan, cfg, eviction="lru", bound=bound, step_cost=cost)
    m = S.window_metrics(res, cfg, bound)
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    grid = tuple(sorted(cfg.capture_sizes))
    ws = [s for s in res["steps"] if w0 <= s.start_s < w1]
    price = sum(C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=grid, bound=bound)
                for s in ws) / 1e3
    hdec = Counter(s.decodes for s in ws if s.decodes >= 1)
    return {"n": n, "rep": r, "config": cname, "predictor": kind, "bound": bound,
            "reuse": m["reuse"], "reuse_rate": m["reuse_rate"],
            "requests_in_window": m["requests_in_window"], "price_s": price,
            "price_per_turn_s": price / m["requests_in_window"],
            "wall_window_s": sum(s.duration_s for s in ws), "h_decode": dict(hdec),
            "max_running": m["max_running"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    sel = json.loads(SEL.read_text())
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    from continuum.workload.multiturn import MultiTurnPlan
    index, i = [], 0
    grids = {}
    for n in NS:
        pool_cfg = GpuConfig("POOL", sel["pool_pool"], sel["max_num_seqs"], tuple(sel["base_grid"]))
        plans = []
        for r in range(REPS):
            pid = f"gblind-n{n}-r{r}"
            prov = MP.build(n=n, seed=SEED0 + i, plan_id=pid, cycle_s=6.0, gap=GAP)
            cyc = analytic(n, pool_cfg, plan_samples([prov]), bound="lo")["cycle_s"]
            plan = MP.build(n=n, seed=SEED0 + i, plan_id=pid, cycle_s=round(cyc, 3), gap=GAP)
            path = PLAN_DIR / f"{pid}.json"
            sha = MP.write(plan, path)
            mx = MP.max_context_tokens(plan)
            if mx > sel["worst_request_tokens"]:
                raise SystemExit(f"{pid} exceeds the worst-case bound")
            index.append({"plan_id": pid, "n": n, "rep": r, "seed": SEED0 + i,
                          "cycle_s": plan.spec["cycle_s"], "content_sha256": sha,
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "max_context": mx,
                          "preemption_blocks_needed": 1 + sel["max_num_seqs"] * -(-mx // 16)})
            plans.append(MultiTurnPlan.from_json(json.loads(path.read_text())))
            print(pid, SEED0 + i, plan.spec["cycle_s"], sha[:12], mx, flush=True)
            i += 1
        an = analytic(n, pool_cfg, plan_samples(plans), bound="lo")
        grids[str(n)] = {"grid": list(dp_grid(an["h"], top=sel["max_num_seqs"], k=4)), "h": an["h"]}
        print("grid", n, grids[str(n)]["grid"], flush=True)
    (PLAN_DIR / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    GRIDS.write_text(json.dumps({"rule": "GTASK08 rule 6 on gblind plans (predict_blind.py)",
                                 "per_n_grid": grids}, indent=1) + "\n")
    table, wall = ratio_table(a.obs)
    jobs = [(n, r, cn, cfg, k, b, table if k == "mode_dist" else None)
            for n in NS for cn, cfg in cfgs(sel, n, grids).items() for r in range(REPS)
            for k in PREDICTORS for b in BOUNDS]
    with ProcessPoolExecutor(a.jobs) as ex:
        runs = list(ex.map(run_one, jobs))
    cells: dict = {}
    for k in PREDICTORS:
        for b in BOUNDS:
            for n in NS:
                for cn in CONFIGS:
                    rs = sorted((x for x in runs if (x["predictor"], x["bound"], x["n"], x["config"]) == (k, b, n, cn)),
                                key=lambda x: x["rep"])
                    hits = sum(x["reuse"][0] for x in rs)
                    tot = sum(x["reuse"][1] for x in rs)
                    h = Counter()
                    for x in rs:
                        h.update({int(d): v for d, v in x["h_decode"].items()})
                    ht = sum(h.values())
                    cells.setdefault(f"{k}/{b}", {}).setdefault(str(n), {})[cn] = {
                        "reuse": [hits, tot], "reuse_rate": hits / tot,
                        "price_per_turn_s": sum(x["price_s"] for x in rs) / sum(x["requests_in_window"] for x in rs),
                        "per_rep": [{"reuse_rate": x["reuse_rate"], "price_per_turn_s": x["price_per_turn_s"],
                                     "max_running": x["max_running"]} for x in rs],
                        "h_decode": {d: v / ht for d, v in sorted(h.items())},
                        "wall_over_price": sum(x["wall_window_s"] for x in rs) / sum(x["price_s"] for x in rs)}
                cell = cells[f"{k}/{b}"][str(n)]
                for cn in CONFIGS:
                    cell[cn]["ratio_to_base"] = cell[cn]["price_per_turn_s"] / cell["BASE"]["price_per_turn_s"]
                order = sorted(CONFIGS, key=lambda c: cell[c]["price_per_turn_s"])
                for cn in CONFIGS:
                    cell[cn]["rank"] = order.index(cn) + 1
    out = {"inputs": {"C_CTX_ms_per_token": C_CTX, "L_PRICE": L_PRICE, "X_CAL": X_CAL,
                      "obs_sha256": hashlib.sha256(a.obs.read_bytes()).hexdigest(),
                      "obs_wall_over_price_lag1": wall,
                      "selection_sha256": hashlib.sha256(SEL.read_bytes()).hexdigest()},
           "plans": index, "grids": grids, "cells": cells}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("sha256", hashlib.sha256(a.out.read_bytes()).hexdigest())
    for k in PREDICTORS:
        for n in NS:
            c = cells[f"{k}/lo"][str(n)]
            print(k, n, {cn: (round(c[cn]["reuse_rate"], 3), round(c[cn]["ratio_to_base"], 4)) for cn in CONFIGS})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
