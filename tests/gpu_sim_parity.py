#!/usr/bin/env python3
"""Integrated simulator vs the GPU wrapper (TASK89, directive 07 work B.3).

Recomputes GTASK09's ``sim_lru/{lo,hi}`` and ``sim_fifo/{lo,hi}`` predictions
for every cell with ``continuum.sim`` (paged engine) and a TEST-ONLY GPU
descriptor, and compares them field by field with the wrapper's
``PREDICTIONS.json``. Window and aggregation definitions are the wrapper's
(``gpu_mt_sim.window_metrics``, ``predict_mt.sim_cell``), restated here.

The GPU files are read from a read-only copy of ``origin/gpu-a6000``
(``git archive``); the GTASK05 cost constants are taken from that copy's
``gpu_cost.py`` so nothing is retyped.

    env -u PYTHONPATH python3 tests/gpu_sim_parity.py --gpu-root <dir of the archive> --out <json>
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import dataclasses
import json
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.sim import paged as PG  # noqa: E402
from continuum.substrate import (  # noqa: E402
    Admission, EagerStepCost, FullGraphDecodeCost, Grid, PiecewiseMixedCost, Provenance,
)
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402
from test_descriptor_v2 import gpu_test_descriptor  # noqa: E402

GPU_ROOT: Path = Path()


def fsum(xs) -> float:
    """CPython 3.12's float ``sum`` (Neumaier compensated summation).

    The wrapper's predictions were computed under Python 3.12 (the GPU venv),
    whose built-in ``sum`` of floats compensates rounding error; this host runs
    3.10, whose ``sum`` does not. Aggregates are restated with this function so
    the comparison is exact rather than within a tolerance."""
    total, c = 0.0, 0.0
    for x in xs:
        x = float(x)
        t = total + x
        if abs(total) >= abs(x):
            c += (total - t) + x
        else:
            c += (x - t) + total
        total = t
    if c and c == c and abs(c) != float("inf"):
        total += c
    return total


def gpu_cost_module():
    sys.path.insert(0, str(GPU_ROOT / "experiments/gpu/multiturn"))
    import gpu_cost  # noqa: E402  (read-only copy)
    return gpu_cost


def descriptor(num_gpu_blocks: int, max_num_seqs: int, grid: tuple[int, ...], budget: int,
               eviction: str, bound: str):
    """TEST-ONLY GPU descriptor for one server configuration and cost bound."""
    C = gpu_cost_module()
    k = 0 if bound == "lo" else 1
    base = gpu_test_descriptor(num_gpu_blocks=num_gpu_blocks, max_num_seqs=max_num_seqs)
    layer = dataclasses.replace(base.layers[0],
                                eviction_order={"lru": "release_lru", "fifo": "allocation_fifo"}[eviction])
    costs = {
        "decode": FullGraphDecodeCost(fixed_ms_by_width=dict(C.F_MS), marginal_ms_per_request=C.G_MS,
                                      max_measured_requests=C.MAX_MEASURED_DECODE),
        "mixed": PiecewiseMixedCost(increment_ms=C.PIECEWISE_INC_MS[k]),
        "eager": EagerStepCost(decode_ms_by_n=dict(C.EAGER_DECODE_MS),
                               increment_points=tuple(zip(C._EAGER_P,
                                                          C._EAGER_LO if k == 0 else C._EAGER_HI))),
    }
    prov = dict(base.provenance)
    for m in ("decode", "mixed", "eager"):
        prov[f"step_cost.{m}"] = Provenance("silicon", "GTASK05", "measured", f"gpu_cost.py, bound {bound}")
    prov["step_cost_measurement"] = Provenance("stack", "GTASK05", "measured", "dispatch interval")
    return dataclasses.replace(
        base, layers=(layer,),
        admission=dataclasses.replace(base.admission, max_running=max_num_seqs, step_token_budget=budget),
        grid=dataclasses.replace(base.grid, sizes=tuple(sorted(grid))),
        step_cost=costs, step_cost_measurement="dispatch interval (GTASK05)", provenance=prov)


def window_metrics(res, d) -> dict:
    """``gpu_mt_sim.window_metrics`` restated on a ``PagedResult``."""
    w0, w1 = res.warmup_end_s, res.eval_end_s
    if w0 is None:
        raise RuntimeError("simulated run never left warm-up")
    reqs = [r for r in res.requests if w0 <= r.arrival_s < w1]
    later = [r for r in reqs if r.turn > 0]
    steps = [s for s in res.steps if w0 <= s.start_s < w1]
    h: dict[int, int] = {}
    for s in steps:
        h[s.reqs] = h.get(s.reqs, 0) + 1
    pad_num = sum((s.padded or (s.decodes + s.prefill_tokens)) - (s.decodes + s.prefill_tokens)
                  for s in steps)
    pad_den = sum((s.padded or (s.decodes + s.prefill_tokens)) for s in steps)
    device = fsum(s.duration_s for s in steps)
    mixed = [s for s in steps if s.prefill_tokens > 0]
    interference = fsum((s.duration_s - PG._decode_ms(d, max(s.decodes, 1)) / 1e3) * s.decodes
                        for s in mixed)
    hits = sum(1 for r in later if r.hit > 0)
    full = sum(1 for r in later if r.reusable > 0 and r.hit >= r.reusable)
    zero = sum(1 for r in later if r.hit == 0)
    n = len(reqs)
    modes = defaultdict(int)
    for s in steps:
        modes[("MIXED_" if s.prefill_tokens else "DECODE_") + s.mode] += 1
    return {"requests_in_window": n, "turn_ge1": len(later), "reuse": [hits, len(later)],
            "reuse_rate": hits / len(later) if later else None,
            "hit_tokens": sum(r.hit for r in later), "reusable_tokens": sum(r.reusable for r in later),
            "token_reuse_ratio": (sum(r.hit for r in later) / sum(r.reusable for r in later)
                                  if later else None),
            "hit_shape": {"zero": zero, "partial": len(later) - zero - full, "full": full},
            "h_counts": {str(k): v for k, v in sorted(h.items())},
            "padding": pad_num / pad_den if pad_den else None,
            "device_s": device, "device_per_turn_s": device / n if n else None,
            "interference_per_turn_s": interference / n if n else None,
            "max_running": max((s.reqs for s in res.steps), default=0),
            "warmup_end_s": w0, "mode_counts": dict(modes)}


def run_plan(args):
    plan_path, cfg, eviction, bound = args
    plan = MultiTurnPlan.from_json(json.loads(Path(plan_path).read_text()))
    d = descriptor(cfg["num_gpu_blocks"], cfg["max_num_seqs"], tuple(cfg["capture_sizes"]),
                   cfg["budget"], eviction, bound)
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(d, sessions, SimConfig(
        max_running_requests=cfg["max_num_seqs"], session_start_s=start, successor=succ,
        semantics="descriptor", window_rule=WindowRule(cycle_s=float(plan.spec["cycle_s"])),
        slot_of=tuple(slot_of), n_slots=plan.n_slots))
    return window_metrics(res, d)


def sim_cell(per: list[dict]) -> dict:
    """``predict_mt.sim_cell`` restated."""
    nreq = sum(m["requests_in_window"] for m in per)
    later = sum(m["turn_ge1"] for m in per)
    h, shape, modes = defaultdict(int), defaultdict(int), defaultdict(int)
    for m in per:
        for k, v in m["h_counts"].items():
            h[int(k)] += v
        for k, v in m["hit_shape"].items():
            shape[k] += v
        for k, v in m["mode_counts"].items():
            modes[k] += v
    ht = sum(h.values())
    return {"reuse": [sum(m["reuse"][0] for m in per), later],
            "reuse_rate": sum(m["reuse"][0] for m in per) / later,
            "token_reuse_ratio": sum(m["hit_tokens"] for m in per) / sum(m["reusable_tokens"] for m in per),
            "hit_shape_share": {k: v / later for k, v in shape.items()},
            "h": {str(k): v / ht for k, v in sorted(h.items())},
            "padding": statistics.mean(m["padding"] for m in per),
            "device_per_turn_s": fsum(m["device_s"] for m in per) / nreq,
            "interference_per_turn_s": fsum(m["interference_per_turn_s"] * m["requests_in_window"]
                                            for m in per) / nreq,
            "piecewise_mixed_steps_per_turn": modes.get("MIXED_PIECEWISE", 0) / nreq,
            "eager_mixed_steps_per_turn": modes.get("MIXED_NONE", 0) / nreq,
            "mode_counts": dict(modes),
            "per_rep": [{"reuse_rate": m["reuse_rate"], "token_reuse_ratio": m["token_reuse_ratio"],
                         "device_per_turn_s": m["device_per_turn_s"],
                         "requests_in_window": m["requests_in_window"],
                         "warmup_end_s": m["warmup_end_s"], "max_running": m["max_running"]}
                        for m in per],
            "requests_in_window": nreq}


def compare(a, b, path="") -> list[str]:
    """Exact comparison; returns the differing paths."""
    if isinstance(b, dict):
        out = []
        for k in b:
            if k not in a:
                out.append(f"{path}/{k} missing")
            else:
                out += compare(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(b, list):
        if len(a) != len(b):
            return [f"{path} length"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += compare(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def main() -> int:
    global GPU_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()
    GPU_ROOT = a.gpu_root
    mt = GPU_ROOT / "experiments/gpu/multiturn"
    pred = json.loads((mt / "plans/PREDICTIONS.json").read_text())
    idx = json.loads((mt / "plans/main/INDEX.json").read_text())
    jobs, keys = [], []
    for n, cells in pred["cells"].items():
        plans = [str(mt / f"plans/main/{e['plan_id']}.json")
                 for e in sorted((e for e in idx if e["n"] == int(n)), key=lambda e: e["rep"])]
        for cfg_name, entry in cells.items():
            for ev in ("lru", "fifo"):
                for b in ("lo", "hi"):
                    for p in plans:
                        jobs.append((p, entry["config"], ev, b))
                        keys.append((n, cfg_name, f"sim_{ev}/{b}"))
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(str(GPU_ROOT),)) as ex:
        res = list(ex.map(run_plan, jobs, chunksize=1))
    per: dict = defaultdict(list)
    for k, r in zip(keys, res):
        per[k].append(r)
    ours: dict = defaultdict(dict)
    for (n, cfg_name, pk), ms in per.items():
        ours[n].setdefault(cfg_name, {})[pk] = sim_cell(ms)
    for n, cells in ours.items():
        for pk in {k for c in cells.values() for k in c}:
            base = cells["BASE"][pk]["device_per_turn_s"]
            for name in cells:
                c = cells[name][pk]
                c["ratio_to_base"] = c["device_per_turn_s"] / base
                c["per_rep_ratio_to_base"] = [x["device_per_turn_s"] / y["device_per_turn_s"]
                                              for x, y in zip(c["per_rep"], cells["BASE"][pk]["per_rep"])]
            order = sorted(cells, key=lambda k: cells[k][pk]["device_per_turn_s"])
            for name in cells:
                cells[name][pk]["rank"] = order.index(name) + 1
    report = {}
    total_diff = 0
    for n, cells in pred["cells"].items():
        for cfg_name, entry in cells.items():
            for pk in [k for k in entry if k.startswith("sim_")]:
                diffs = compare(ours[n][cfg_name][pk], entry[pk])
                total_diff += len(diffs)
                report[f"{n}/{cfg_name}/{pk}"] = {"differences": len(diffs), "first": diffs[:5]}
    out = {"cells_compared": len(report), "total_differences": total_diff, "report": report,
           "ours": ours}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for k, v in report.items():
        if v["differences"]:
            print(k, v)
    print(f"cells {len(report)}, differing fields {total_diff}")
    print("PARITY", "PASS" if total_diff == 0 else "FAIL")
    return 0 if total_diff == 0 else 1


def _init(root: str) -> None:
    global GPU_ROOT
    GPU_ROOT = Path(root)


if __name__ == "__main__":
    raise SystemExit(main())
