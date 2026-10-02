#!/usr/bin/env python3
"""How much of TASK90 finding 4 (the simulator's +0.03-0.06 cost-ratio bias in
the batch-16 configurations) the operational step times explain (TASK91,
directive 08 work A.2). Development set; the ratios come from the same runs,
so this is an explanation, never an input to a blind prediction.

The simulator advances time with step durations scaled by the audit's
observed/predicted ratios (decode: per configuration and running count;
prefill: per computed-token bin), and every step is then *priced* with the
original cost model -- the observed channel A' prices steps with the original
model too, so only the dynamics change. Cost ratios are compared with the
observed m of TASK82/87 for N = 12, 14, 16.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import b2_diag as B  # noqa: E402
import mt_predict as P  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import WindowRule, to_sim_inputs  # noqa: E402

AUDIT = HERE.parents[2] / "results/npu/stage3/step_audit/audit.json"
CFGS = ("BASE", "BATCHONLY", "TUNED")


class _ScaledPrefill:
    def __init__(self, base, bins):
        self.base, self.bins = base, bins

    def prefill_s(self, n: int) -> float:
        s = self.base.prefill_s(n)
        for (lo, hi), r in self.bins:
            if lo <= n <= hi:
                return s * r
        return s


class _TimeScaled:
    """A v1 descriptor whose step and prefill *durations* are scaled."""

    def __init__(self, base, step_ratio: dict, prefill_bins):
        self._base, self._r = base, step_ratio
        self.prefill_cost_model = _ScaledPrefill(base.prefill_cost_model, prefill_bins)

    def __getattr__(self, name):
        return getattr(self._base, name)

    def step_time_s(self, actual: int) -> float:
        return self._base.step_time_s(actual) * self._r.get(actual, 1.0)


def run(args):
    n, cfg, r, scaled = args
    grid, batch = P.CONFIGS[cfg]
    base = P.descriptor(grid, batch)
    audit = json.loads(AUDIT.read_text())
    desc = base
    if scaled:
        ratio = {s["n"]: s["ratio"] for s in audit["steps"] if s["cfg"] == cfg}
        bins = [(tuple(p["computed_bin"]), p["median_ratio"]) for p in audit["prefill"] if p["cfg"] == cfg]
        desc = _TimeScaled(base, ratio, bins)
    plan = B.plans_of(n)[r]
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(desc, sessions, SimConfig(max_running_requests=batch, session_start_s=start,
                                             successor=succ, semantics="descriptor"))
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=120.0)
    w0 = rule.warmup_end([(slot_of[q.session_index], q.finish_s) for q in res.requests], plan.n_slots)
    reqs = [q for q in res.requests if w0 <= q.arrival_s < w0 + 120.0]
    later = [q for q in reqs if q.turn > 0]
    price = sum(base.step_cost_model.step_time_s(bucket=s.bucket, actual=s.running)
                for s in res.decode_steps if w0 <= s.start_s < w0 + 120.0)
    price += sum(base.prefill_cost_model.prefill_s(s.computed_tokens)
                 for s in res.prefill_steps if w0 <= s.start_s < w0 + 120.0)
    return {"price": price, "requests": len(reqs),
            "hits": sum(1 for q in later if q.cached_tokens > 0), "later": len(later)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    jobs = [(n, c, r, s) for n in (12, 14, 16) for c in CFGS for r in range(5) for s in (False, True)]
    with ProcessPoolExecutor(max_workers=60) as ex:
        res = dict(zip(jobs, ex.map(run, jobs)))
    out = {}
    for n in (12, 14, 16):
        ver = json.loads(B.RUNS[n].read_text())["cells"]
        cell = defaultdict(dict)
        for scaled in (False, True):
            for c in CFGS:
                xs = [res[(n, c, r, scaled)] for r in range(5)]
                cell[c][scaled] = {"device": sum(x["price"] for x in xs) / sum(x["requests"] for x in xs),
                                   "reuse": sum(x["hits"] for x in xs) / sum(x["later"] for x in xs)}
        for c in CFGS:
            row = {"obs_reuse": ver[f"{c}.n{n}"]["reuse_obs"]}
            for scaled, key in ((False, "orig"), (True, "scaled")):
                row[f"{key}_reuse_bias"] = cell[c][scaled]["reuse"] - row["obs_reuse"]
                if c != "BASE":
                    ratio = cell[c][scaled]["device"] / cell["BASE"][scaled]["device"]
                    row[f"{key}_ratio_bias"] = ratio - ver[f"{c}.n{n}"]["ratio"]["m"]
            if c != "BASE":
                o, s = abs(row["orig_ratio_bias"]), abs(row["scaled_ratio_bias"])
                row["ratio_bias_explained"] = (o - s) / o if o else None
            out[f"{c}.n{n}"] = row
            print(c, n, {k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()}, flush=True)
    tot_o = sum(abs(v["orig_ratio_bias"]) for v in out.values() if "orig_ratio_bias" in v)
    tot_s = sum(abs(v["scaled_ratio_bias"]) for v in out.values() if "scaled_ratio_bias" in v)
    summary = {"ratio_bias_sum_orig": tot_o, "ratio_bias_sum_scaled": tot_s,
               "explained_share": (tot_o - tot_s) / tot_o}
    print(json.dumps(summary))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"cells": out, "summary": summary}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
