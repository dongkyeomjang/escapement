#!/usr/bin/env python3
"""G-10 C: capacity, plans, candidate-N scan and frozen predictions (simulator only).

Prereg: docs/research/gpu/G10_C_PREREG.md. Run once, before any C lifecycle.

Workload (directive G-10 5.1): the GTASK09/20 law; SHORT_TOOL = later segment
8 tokens, LONG_TOOL = later segment 512 tokens (256 if any turn of the law
could exceed 8,192 = max_model_len; decided from lengths only). The two plans
of one (N, r) share plan_id and seed, so every per-session draw (opening
length, generation length, tool wait, text seed) is identical; only the later
segment length differs (``Distribution("fixed").draw`` consumes no random
number). ``cycle_s`` (stagger and window rule) is computed once per (N, r)
from the LONG_TOOL plan (analytic, GPU_LONG_KV, lo) and used by both plans.

Capacity (5.2): GPU_LONG_BASE = 1 + max_num_seqs * ceil(W / 16), W = the law's
largest prompt + generation (GTASK08 rule, vLLM 0.22.0 with async scheduling
and no speculative tokens allocates at most ceil((prompt + gen - 1)/16)
blocks per request); GPU_LONG_KV = ceil(GPU_LONG_BASE * 2300 / 1900).

Timing (5.3): GTASK20 predictor (1) form, ``price + c * (decode context -
decodes * 128)``, with c = ``c_long`` of the long-context microbenchmark
(``ctx_long_result/summary.json``).

Candidate N in (24, 28, 32, 36), 5 plans each: select the smallest N with
LONG_TOOL x GPU_LONG_BASE reuse in [0.2, 0.8] at lo and hi, and
LONG_TOOL x GPU_LONG_KV reuse - that >= 0.05 at lo and hi (pooled: the
simulator's own hits / turn>=1 requests summed over the 5 plans).

usage: predict_c.py --ctx-long <abs summary.json> --out <abs json> [--jobs 24]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
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
from predict_blind import GAP, L_PRICE  # noqa: E402

CAND_N = (24, 28, 32, 36)
REPS = 5
SEED0 = 20264200
BOUNDS = ("lo", "hi")
GRID = (1, 2, 4, 8, 16)
MAX_SEQS, MAX_LEN = 8, 8192
FIRST_MAX, GEN_MAX, TURNS = 1600, 256, 8
TOOLS = {"SHORT_TOOL": 8, "LONG_TOOL": 512}
PLAN_DIR = HERE / "plans_c"


def law_max(seg: int) -> int:
    return FIRST_MAX + (TURNS - 1) * seg + TURNS * GEN_MAX


def long_segment() -> int:
    return 512 if law_max(512) <= MAX_LEN else 256


W_MAX = law_max(long_segment())
BASE_BLOCKS = 1 + MAX_SEQS * math.ceil(W_MAX / 16)
KV_BLOCKS = math.ceil(BASE_BLOCKS * 2300 / 1900)
CFGS = {"GPU_LONG_BASE": GpuConfig("GPU_LONG_BASE", BASE_BLOCKS, MAX_SEQS, GRID),
        "GPU_LONG_KV": GpuConfig("GPU_LONG_KV", KV_BLOCKS, MAX_SEQS, GRID)}


class StepCostLong:
    """GTASK20 ``ctx`` form with the long-context slope."""

    def __init__(self, c: float):
        self.c = c

    def __call__(self, *, decodes, prefill_tokens, grid, bound, decode_ctx):
        base = C.step_ms(decodes=decodes, prefill_tokens=prefill_tokens, grid=grid, bound=bound)
        return base + self.c * (decode_ctx - decodes * L_PRICE) if decodes else base


def seed_of(n: int, r: int) -> int:
    return SEED0 + 10 * CAND_N.index(n) + r


def plan_path(n: int, r: int, tool: str) -> Path:
    return PLAN_DIR / f"g10c-n{n}-r{r}-{tool.split('_')[0].lower()}.json"


def run_one(job) -> dict:
    n, r, tool, cname, bound, c = job
    from continuum.workload.multiturn import MultiTurnPlan
    cfg = CFGS[cname]
    plan = MultiTurnPlan.from_json(json.loads(plan_path(n, r, tool).read_text()))
    res = S.simulate(plan, cfg, eviction="lru", bound=bound, step_cost=StepCostLong(c))
    m = S.window_metrics(res, cfg, bound)
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    ws = [s for s in res["steps"] if w0 <= s.start_s < w1]
    price = sum(C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=GRID, bound=bound)
                for s in ws) / 1e3
    reqs = [q for q in res["requests"] if w0 <= q.arrival_s < w1]
    later = [q for q in reqs if q.turn > 0]
    waits = sorted(q.admit_s - q.arrival_s for q in reqs)
    nw = m["requests_in_window"]
    return {"n": n, "rep": r, "tool": tool, "config": cname, "bound": bound,
            "reuse": m["reuse"], "reuse_rate": m["reuse_rate"],
            "hit_tokens": m["hit_tokens"], "reusable_tokens": m["reusable_tokens"],
            "token_reuse_ratio": m["token_reuse_ratio"], "hit_shape": m["hit_shape"],
            "prefill_tokens_computed_later": sum(q.prompt - q.hit for q in later),
            "prompt_tokens_later": sum(q.prompt for q in later),
            "requests_in_window": nw, "price_s": price, "price_per_turn_s": price / nw,
            "simwall_per_turn_s": sum(s.duration_s for s in ws) / nw,
            "context_mean_later": statistics.fmean(q.prompt for q in later) if later else None,
            "context_max_later": max((q.prompt + q.gen for q in later), default=None),
            "h_decode": dict(Counter(s.decodes for s in ws if s.decodes >= 1)),
            "queue_wait_mean_s": statistics.fmean(waits) if waits else None,
            "queue_wait_median_s": waits[len(waits) // 2] if waits else None,
            "max_running": m["max_running"], "warmup_end_s": w0}


def pool_cell(rs: list) -> dict:
    hits, tot = sum(x["reuse"][0] for x in rs), sum(x["reuse"][1] for x in rs)
    ht, rt = sum(x["hit_tokens"] for x in rs), sum(x["reusable_tokens"] for x in rs)
    shape = Counter()
    for x in rs:
        shape.update(x["hit_shape"])
    return {"reuse": [hits, tot], "reuse_rate": hits / tot, "hit_tokens": ht, "reusable_tokens": rt,
            "token_reuse_ratio": ht / rt, "hit_shape": dict(shape),
            "partial_fraction": shape["partial"] / tot,
            "prefill_tokens_computed_later": sum(x["prefill_tokens_computed_later"] for x in rs),
            "price_per_turn_s_pooled": sum(x["price_s"] for x in rs) / sum(x["requests_in_window"] for x in rs),
            "queue_wait_mean_s": statistics.fmean(x["queue_wait_mean_s"] for x in rs),
            "per_rep": rs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx-long", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    cl = json.loads(a.ctx_long.read_text())
    if not cl.get("complete"):
        raise SystemExit("long-context calibration incomplete")
    c_long = cl["F1"]["c_ms_per_token"]
    from continuum.workload.multiturn import MultiTurnPlan
    seg = long_segment()
    TOOLS["LONG_TOOL"] = seg
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    for n in CAND_N:
        for r in range(REPS):
            pid = f"g10c-n{n}-r{r}"
            prov = MP.build(n=n, seed=seed_of(n, r), plan_id=pid, cycle_s=6.0, gap=GAP, later=f"fixed:{seg}")
            cyc = round(analytic(n, CFGS["GPU_LONG_KV"], plan_samples([prov]), bound="lo")["cycle_s"], 3)
            row = {"plan_id": pid, "n": n, "rep": r, "seed": seed_of(n, r), "cycle_s": cyc}
            plans = {}
            for tool, sg in TOOLS.items():
                plan = MP.build(n=n, seed=seed_of(n, r), plan_id=pid, cycle_s=cyc, gap=GAP, later=f"fixed:{sg}")
                path = plan_path(n, r, tool)
                sha = MP.write(plan, path)
                mx = MP.max_context_tokens(plan)
                need = 1 + MAX_SEQS * -(-mx // 16)
                if mx > MAX_LEN or need > BASE_BLOCKS:
                    raise SystemExit(f"{pid} {tool}: max context {mx}, blocks {need} > {BASE_BLOCKS}")
                plans[tool] = MultiTurnPlan.from_json(json.loads(path.read_text()))
                row[tool] = {"file": path.name, "content_sha256": sha,
                             "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "max_context": mx, "preemption_blocks_needed": need}
            # identical logical plan apart from the later segment length
            for s1, s2 in zip(plans["SHORT_TOOL"].slots, plans["LONG_TOOL"].slots):
                assert s1.start_s == s2.start_s
                for x, y in zip(s1.sessions, s2.sessions):
                    assert x.session_id == y.session_id and len(x.turns) == len(y.turns)
                    for t, u in zip(x.turns, y.turns):
                        assert (t.generation_tokens, t.gap_after_s, t.text_seed) == \
                            (u.generation_tokens, u.gap_after_s, u.text_seed)
                        assert t.index > 0 or t.new_segment_tokens == u.new_segment_tokens
            index.append(row)
            print(pid, row["seed"], cyc, row["SHORT_TOOL"]["max_context"], row["LONG_TOOL"]["max_context"], flush=True)
    (PLAN_DIR / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    (PLAN_DIR / "CONFIGS.json").write_text(json.dumps(
        {k: {"num_gpu_blocks": v.num_gpu_blocks, "max_num_seqs": v.max_num_seqs,
             "capture_sizes": list(v.capture_sizes), "budget": v.budget} for k, v in CFGS.items()},
        indent=1) + "\n")
    jobs = [(n, r, t, cn, b, c_long) for n in CAND_N for r in range(REPS) for t in TOOLS for cn in CFGS
            for b in BOUNDS]
    with ProcessPoolExecutor(a.jobs) as ex:
        runs = list(ex.map(run_one, jobs))
    cells: dict = {}
    for n in CAND_N:
        for t in TOOLS:
            for b in BOUNDS:
                per = {cn: sorted((x for x in runs if (x["n"], x["tool"], x["bound"], x["config"]) == (n, t, b, cn)),
                                  key=lambda x: x["rep"]) for cn in CFGS}
                cell = {cn: pool_cell(rs) for cn, rs in per.items()}
                rat = [k["price_per_turn_s"] / bb["price_per_turn_s"]
                       for k, bb in zip(per["GPU_LONG_KV"], per["GPU_LONG_BASE"])]
                cell["R_PRED"] = {"per_rep": rat, "median": statistics.median(rat)}
                cells.setdefault(str(n), {}).setdefault(t, {})[b] = cell
    scan, chosen = [], None
    for n in CAND_N:
        lt = cells[str(n)]["LONG_TOOL"]
        base = {b: lt[b]["GPU_LONG_BASE"]["reuse_rate"] for b in BOUNDS}
        kv = {b: lt[b]["GPU_LONG_KV"]["reuse_rate"] for b in BOUNDS}
        ok = all(0.2 <= base[b] <= 0.8 for b in BOUNDS) and all(kv[b] - base[b] >= 0.05 for b in BOUNDS)
        scan.append({"n": n, "long_base_reuse": base, "long_kv_reuse": kv,
                     "kv_minus_base": {b: kv[b] - base[b] for b in BOUNDS}, "eligible": ok})
        if ok and chosen is None:
            chosen = n
    out = {"inputs": {"c_long_ms_per_token": c_long,
                      "ctx_long_summary_sha256": hashlib.sha256(a.ctx_long.read_bytes()).hexdigest(),
                      "L_PRICE": L_PRICE, "long_segment": seg, "law_max_context": W_MAX,
                      "gpu_long_base_blocks": BASE_BLOCKS, "gpu_long_kv_blocks": KV_BLOCKS,
                      "gpu_cost_sha256": hashlib.sha256((MT / "gpu_cost.py").read_bytes()).hexdigest(),
                      "gpu_mt_sim_sha256": hashlib.sha256((MT / "gpu_mt_sim.py").read_bytes()).hexdigest(),
                      "python": sys.version},
           "plans": index, "scan": scan, "chosen_n": chosen, "cells": cells}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("sha256", hashlib.sha256(a.out.read_bytes()).hexdigest())
    print("blocks", BASE_BLOCKS, KV_BLOCKS, "segment", seg, "W", W_MAX, "c_long", c_long)
    for s in scan:
        print(s)
    print("chosen N", chosen)
    for n in CAND_N:
        for t in TOOLS:
            for b in BOUNDS:
                c = cells[str(n)][t][b]
                print(n, t, b, {cn: (round(c[cn]["reuse_rate"], 3), round(c[cn]["token_reuse_ratio"], 3))
                                for cn in CFGS}, "R", round(c["R_PRED"]["median"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
