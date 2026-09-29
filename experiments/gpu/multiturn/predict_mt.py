#!/usr/bin/env python3
"""GTASK09: main/pilot plans and blind predictions for the GPU multi-turn experiment.

Inputs: ``selection/selection.json`` (GTASK08), GTASK01-05 constants through
``gpu_cost`` / ``gpu_mt_sim`` / ``gpu_mt_model``, and the plans generated here.
Nothing measured in a multi-turn run (pilot or main) is read.

Plans
* main: N in the confirmatory set plus the exploratory collapse cell N = 26,
  r = 0..4, seed ``20262300 + i`` (i = running index), plan_id
  ``gmain-n{N}-r{r}``;
* pilot: N = middle confirmatory N, r = 0..2, seed ``20262500 + i``,
  plan_id ``gpilot-n{N}-r{r}``.
``cycle_s`` (stagger and window rule) = the analytic model's POOL cycle at the
lo bound for that plan, fixed before anything is measured (as the NPU used
its analytic TUNED cycle).

Predictors (directive G-03 5.1): ``analytic`` (v1 GPU instance), ``sim_lru``
(GPU semantics), ``sim_fifo`` (counterfactual: allocation-order eviction),
each at the ``lo`` and ``hi`` cost bound.

usage: predict_mt.py --selection <abs json> --plan-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

import make_plan as MP  # noqa: E402
from gpu_mt_model import analytic, plan_samples  # noqa: E402
from gpu_mt_sim import GpuConfig, simulate, window_metrics  # noqa: E402
import gpu_cost as C  # noqa: E402

GAP_FILE = "/home/csdc/kyeom/Project/vllm-continuum/results/tracelab/summary.json"
GAP = f"toolmix:{GAP_FILE}:60"
MAIN_SEED0, PILOT_SEED0 = 20262300, 20262500
REPS_MAIN, REPS_PILOT = 5, 3
EXPLORATORY_N = (26,)
BOUNDS = ("lo", "hi")


def configs(sel: dict, n: int) -> dict[str, GpuConfig]:
    base = tuple(sel["base_grid"])
    g = sel["per_n_grid"].get(str(n))
    out = {"BASE": GpuConfig("BASE", sel["base_pool"], sel["max_num_seqs"], base),
           "POOL": GpuConfig("POOL", sel["pool_pool"], sel["max_num_seqs"], base)}
    if g is not None:
        out["POOL+GRID"] = GpuConfig("POOL+GRID", sel["pool_pool"], sel["max_num_seqs"], tuple(g["grid"]))
    return out


def make_plans(sel: dict, plan_dir: Path, kind: str, ns, reps, seed0) -> list[dict]:
    index, i = [], 0
    for n in ns:
        pool_cfg = configs(sel, n)["POOL"]
        for r in range(reps):
            pid = f"g{kind}-n{n}-r{r}"
            prov = MP.build(n=n, seed=seed0 + i, plan_id=pid, cycle_s=6.0, gap=GAP)
            cyc = analytic(n, pool_cfg, plan_samples([prov]), bound="lo")["cycle_s"]
            plan = MP.build(n=n, seed=seed0 + i, plan_id=pid, cycle_s=round(cyc, 3), gap=GAP)
            path = plan_dir / f"{pid}.json"
            sha = MP.write(plan, path)
            mx = MP.max_context_tokens(plan)
            if mx > sel["worst_request_tokens"]:
                raise SystemExit(f"{pid} exceeds the worst-case bound")
            index.append({"plan_id": pid, "kind": kind, "n": n, "rep": r, "seed": seed0 + i,
                          "cycle_s": plan.spec["cycle_s"], "content_sha256": sha,
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "max_context": mx,
                          "preemption_blocks_needed": 1 + sel["max_num_seqs"] * -(-mx // 16)})
            print(pid, seed0 + i, plan.spec["cycle_s"], sha[:12], mx, flush=True)
            i += 1
    return index


def mode_counts(res: dict, cfg: GpuConfig) -> dict:
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    steps = [s for s in res["steps"] if w0 <= s.start_s < w1]
    c = defaultdict(int)
    for s in steps:
        c[("MIXED_" if s.prefill_tokens else "DECODE_") + s.mode] += 1
    return dict(c)


def sim_cell(plans, cfg, eviction, bound) -> dict:
    per = []
    for p in plans:
        res = simulate(p, cfg, eviction=eviction, bound=bound)
        m = window_metrics(res, cfg, bound)
        m["mode_counts"] = mode_counts(res, cfg)
        per.append(m)
    nreq = sum(m["requests_in_window"] for m in per)
    later = sum(m["turn_ge1"] for m in per)
    h = defaultdict(int)
    shape = defaultdict(int)
    modes = defaultdict(int)
    for m in per:
        for k, v in m["h_counts"].items():
            h[int(k)] += v
        for k, v in m["hit_shape"].items():
            shape[k] += v
        for k, v in m["mode_counts"].items():
            modes[k] += v
    ht = sum(h.values())
    return {
        "reuse": [sum(m["reuse"][0] for m in per), later],
        "reuse_rate": sum(m["reuse"][0] for m in per) / later,
        "token_reuse_ratio": sum(m["hit_tokens"] for m in per) / sum(m["reusable_tokens"] for m in per),
        "hit_shape_share": {k: v / later for k, v in shape.items()},
        "h": {k: v / ht for k, v in sorted(h.items())},
        "padding": statistics.mean(m["padding"] for m in per),
        "device_per_turn_s": sum(m["device_s"] for m in per) / nreq,
        "interference_per_turn_s": sum(m["interference_per_turn_s"] * m["requests_in_window"]
                                       for m in per) / nreq,
        "piecewise_mixed_steps_per_turn": modes.get("MIXED_PIECEWISE", 0) / nreq,
        "eager_mixed_steps_per_turn": modes.get("MIXED_NONE", 0) / nreq,
        "mode_counts": dict(modes),
        "per_rep": [{"reuse_rate": m["reuse_rate"], "token_reuse_ratio": m["token_reuse_ratio"],
                     "device_per_turn_s": m["device_per_turn_s"],
                     "requests_in_window": m["requests_in_window"],
                     "warmup_end_s": m["warmup_end_s"], "max_running": m["max_running"]}
                    for m in per],
        "requests_in_window": nreq,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True, type=Path)
    ap.add_argument("--plan-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    sel = json.loads(a.selection.read_text())
    ns_conf = sel["confirmatory_n"]
    ns = list(ns_conf) + [n for n in EXPLORATORY_N if n not in ns_conf]
    mid = ns_conf[len(ns_conf) // 2]
    a.plan_dir.mkdir(parents=True, exist_ok=True)
    main_index = make_plans(sel, a.plan_dir / "main", "main", ns, REPS_MAIN, MAIN_SEED0)
    pilot_index = make_plans(sel, a.plan_dir / "pilot", "pilot", [mid], REPS_PILOT, PILOT_SEED0)
    (a.plan_dir / "main" / "INDEX.json").write_text(json.dumps(main_index, indent=2) + "\n")
    (a.plan_dir / "pilot" / "INDEX.json").write_text(json.dumps(pilot_index, indent=2) + "\n")
    from continuum.workload.multiturn import MultiTurnPlan
    out = {"selection_sha256": hashlib.sha256(a.selection.read_bytes()).hexdigest(),
           "confirmatory_n": ns_conf, "exploratory_n": [n for n in ns if n not in ns_conf],
           "cells": {}}
    for n in ns:
        plans = [MultiTurnPlan.from_json(json.loads((a.plan_dir / "main" / f"{e['plan_id']}.json").read_text()))
                 for e in main_index if e["n"] == n]
        st = plan_samples(plans)
        cell = {}
        for name, cfg in configs(sel, n).items():
            entry = {"config": {"num_gpu_blocks": cfg.num_gpu_blocks, "max_num_seqs": cfg.max_num_seqs,
                                "capture_sizes": list(cfg.capture_sizes), "budget": cfg.budget}}
            for b in BOUNDS:
                entry[f"analytic/{b}"] = analytic(n, cfg, st, bound=b)
                entry[f"sim_lru/{b}"] = sim_cell(plans, cfg, "lru", b)
                entry[f"sim_fifo/{b}"] = sim_cell(plans, cfg, "fifo", b)
            cell[name] = entry
            print(n, name, {k: round(v["reuse_rate"], 3) for k, v in entry.items() if "/" in k},
                  {k: round(1e3 * v["device_per_turn_s"], 1) for k, v in entry.items() if "/" in k},
                  flush=True)
        for pk in [k for k in cell["BASE"] if "/" in k]:
            base = cell["BASE"][pk]["device_per_turn_s"]
            for name in cell:
                cell[name][pk]["ratio_to_base"] = cell[name][pk]["device_per_turn_s"] / base
                if "per_rep" in cell[name][pk]:
                    cell[name][pk]["per_rep_ratio_to_base"] = [
                        x["device_per_turn_s"] / y["device_per_turn_s"]
                        for x, y in zip(cell[name][pk]["per_rep"], cell["BASE"][pk]["per_rep"])]
            order = sorted(cell, key=lambda k: cell[k][pk]["device_per_turn_s"])
            for name in cell:
                cell[name][pk]["rank"] = order.index(name) + 1
        out["cells"][str(n)] = cell
    # directive 2.1: largest effect of the PIECEWISE interval on per-turn cost
    impact = {}
    for n, cell in out["cells"].items():
        for name, e in cell.items():
            s = e["sim_lru/lo"]
            impact[f"{n}/{name}"] = {
                "piecewise_mixed_steps_per_turn": s["piecewise_mixed_steps_per_turn"],
                "max_piecewise_ms_per_turn": s["piecewise_mixed_steps_per_turn"] * C.PIECEWISE_INC_MS[1],
                "share_of_device_per_turn": s["piecewise_mixed_steps_per_turn"] * C.PIECEWISE_INC_MS[1]
                / (1e3 * s["device_per_turn_s"]),
                "hi_minus_lo_device_ms": 1e3 * (e["sim_lru/hi"]["device_per_turn_s"] - s["device_per_turn_s"])}
    out["piecewise_interval_impact"] = impact
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("sha256", hashlib.sha256(a.out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
