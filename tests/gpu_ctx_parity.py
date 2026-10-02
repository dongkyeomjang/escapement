#!/usr/bin/env python3
"""Parity (TASK103): GTASK20's main predictor (``ctx``, N = 25 and 28, bounds
lo and hi) recomputed with the unified simulator (paged engine) and a
TEST-ONLY GPU descriptor whose ``context_cost`` carries GTASK18's slope
(2.120e-4 ms per context token above the price load's 128 tokens per
decoding request) must equal the GPU branch's ``PREDICTIONS_BLIND.json``.

The GPU files are a read-only copy (``git archive origin/gpu-a6000``). Sums
of floats use ``gpu_sim_parity.fsum`` (CPython 3.12's compensated sum, the
GPU venv's), as in the GTASK09 parity.

usage: gpu_ctx_parity.py --gpu-root <archive copy> [--workers 48]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import dataclasses
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gpu_sim_parity as GP  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.sim import paged as PG  # noqa: E402
from continuum.substrate import ContextCost, Provenance  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

C_CTX_MS = 2.120e-4     # GTASK18 F1 (predict_blind.py C_CTX)
L_PRICE = 128           # GTASK05 price load, tokens per decoding request (predict_blind.py L_PRICE)
NS = (25, 28)
CONFIGS = ("BASE", "POOL", "POOL+GRID")
fsum = GP.fsum


def ctx_descriptor(num_gpu_blocks, max_num_seqs, grid, budget, bound):
    d = GP.descriptor(num_gpu_blocks, max_num_seqs, grid, budget, "lru", bound)
    prov = dict(d.provenance)
    prov["context_cost"] = Provenance("class", "GTASK18", "measured",
                                      "c = 2.120e-4 ms/token over 128 tokens/request (form class, value stack)")
    return dataclasses.replace(d, context_cost=ContextCost(per_token=C_CTX_MS, unit="ms",
                                                           reference_tokens_per_decode=L_PRICE),
                               provenance=prov)


def run_one(args):
    root, n, r, cname, cfg, bound = args
    GP.GPU_ROOT = Path(root)
    mt = Path(root) / "experiments/gpu/multiturn"
    plan = MultiTurnPlan.from_json(json.loads((mt / f"plans/blind/gblind-n{n}-r{r}.json").read_text()))
    d = ctx_descriptor(cfg["num_gpu_blocks"], cfg["max_num_seqs"], tuple(cfg["capture_sizes"]), cfg["budget"], bound)
    price_d = GP.descriptor(cfg["num_gpu_blocks"], cfg["max_num_seqs"], tuple(cfg["capture_sizes"]),
                            cfg["budget"], "lru", bound)
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(d, sessions, SimConfig(
        max_running_requests=cfg["max_num_seqs"], session_start_s=start, successor=succ,
        semantics="descriptor", window_rule=WindowRule(cycle_s=float(plan.spec["cycle_s"])),
        slot_of=tuple(slot_of), n_slots=plan.n_slots))
    m = GP.window_metrics(res, d)
    w0, w1 = res.warmup_end_s, res.eval_end_s
    ws = [s for s in res.steps if w0 <= s.start_s < w1]
    price = fsum(PG.step_ms(price_d, decodes=s.decodes, prefill_tokens=s.prefill_tokens) for s in ws) / 1e3
    hdec = Counter(s.decodes for s in ws if s.decodes >= 1)
    return {"n": n, "rep": r, "config": cname, "bound": bound, "reuse": m["reuse"], "reuse_rate": m["reuse_rate"],
            "requests_in_window": m["requests_in_window"], "price_s": price,
            "price_per_turn_s": price / m["requests_in_window"],
            "wall_window_s": fsum(s.duration_s for s in ws), "h_decode": dict(hdec),
            "max_running": m["max_running"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu-root", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    mt = a.gpu_root / "experiments/gpu/multiturn"
    sel = json.loads((mt / "selection/selection.json").read_text())
    grids = json.loads((mt / "selection/blind_grids.json").read_text())["per_n_grid"]
    ref = json.loads((mt / "plans/blind/PREDICTIONS_BLIND.json").read_text())["cells"]

    def cfgs(n):
        base = list(sel["base_grid"])
        common = {"max_num_seqs": sel["max_num_seqs"], "budget": sel["budget"]}
        return {"BASE": {**common, "num_gpu_blocks": sel["base_pool"], "capture_sizes": base},
                "POOL": {**common, "num_gpu_blocks": sel["pool_pool"], "capture_sizes": base},
                "POOL+GRID": {**common, "num_gpu_blocks": sel["pool_pool"], "capture_sizes": grids[str(n)]["grid"]}}

    jobs = [(str(a.gpu_root), n, r, cn, cfg, b) for n in NS for cn, cfg in cfgs(n).items()
            for r in range(5) for b in ("lo", "hi")]
    with ProcessPoolExecutor(a.workers) as ex:
        runs = list(ex.map(run_one, jobs))
    total = 0
    report = {}
    for b in ("lo", "hi"):
        for n in NS:
            cell = {}
            for cn in CONFIGS:
                rs = sorted((x for x in runs if (x["bound"], x["n"], x["config"]) == (b, n, cn)), key=lambda x: x["rep"])
                hits = sum(x["reuse"][0] for x in rs)
                tot = sum(x["reuse"][1] for x in rs)
                h = Counter()
                for x in rs:
                    h.update({int(k): v for k, v in x["h_decode"].items()})
                ht = sum(h.values())
                cell[cn] = {"reuse": [hits, tot], "reuse_rate": hits / tot,
                            "price_per_turn_s": fsum(x["price_s"] for x in rs) / sum(x["requests_in_window"] for x in rs),
                            "per_rep": [{"reuse_rate": x["reuse_rate"], "price_per_turn_s": x["price_per_turn_s"],
                                         "max_running": x["max_running"]} for x in rs],
                            "h_decode": {k: v / ht for k, v in sorted(h.items())},
                            "wall_over_price": fsum(x["wall_window_s"] for x in rs) / fsum(x["price_s"] for x in rs)}
            for cn in CONFIGS:
                cell[cn]["ratio_to_base"] = cell[cn]["price_per_turn_s"] / cell["BASE"]["price_per_turn_s"]
            order = sorted(CONFIGS, key=lambda c: cell[c]["price_per_turn_s"])
            for cn in CONFIGS:
                cell[cn]["rank"] = order.index(cn) + 1
            mine = json.loads(json.dumps(cell))
            for cn in CONFIGS:
                theirs = ref[f"ctx/{b}"][str(n)][cn]
                diffs = GP.compare(mine[cn], theirs)
                total += len(diffs)
                report[f"ctx/{b}/{n}/{cn}"] = {"differences": len(diffs), "first": diffs[:5]}
                print(f"ctx/{b}", n, cn, "identical" if not diffs else diffs[:3])
    if a.out:
        a.out.write_text(json.dumps({"total_differences": total, "report": report}, indent=1) + "\n")
    print("GPU CTX PARITY", "PASS" if total == 0 else "FAIL", total)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
