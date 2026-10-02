#!/usr/bin/env python3
"""G-05 task B (development set, no verdict): time-scale variants of sim LRU.

``gpu_mt_sim.simulate`` advances time by ``gpu_cost.step_ms`` (the A'-GPU
price channel). The variants replace only that duration; block pool, engine
and plans are untouched (``gpu_mt_sim.py`` is not modified -- its ``C`` module
reference is swapped for a wrapper during a call). Cost metrics are always
priced with the original ``gpu_cost`` over the simulated window steps, so
cost ratios stay on the price channel the observation uses.

Variants (``lo`` bound):
* ``orig``      -- price channel (regression: must equal PREDICTIONS.json)
* ``x1.131``    -- every step x 1.131 (GTASK11 direct/price median, directive)
* ``x1.210``    -- every step x the window wall/price ratio with lag-1
                  attribution (GTASK13 finding; auxiliary)
* ``mode_dist`` -- every step x a ratio drawn from the observed lag-1
                  dispatch/price distribution of its step class
                  (``step_classes``), seeded per (plan, config)

Per lifecycle it also records queue dynamics for task C.

usage: sim_timescale.py --obs <abs obs.json> --out <abs json>
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_cost as C  # noqa: E402
import gpu_mt_sim as S  # noqa: E402
from configs import config_by_name  # noqa: E402
from step_classes import step_class  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402

PLANS = HERE / "plans" / "main"
CELLS = [(n, c) for n in (20, 22, 24) for c in ("BASE", "POOL", "POOL+GRID")] + \
        [(26, "BASE"), (26, "POOL")]
REPS = 5
WALL_RATIO = None   # filled from obs


def ratio_table(obs_path: Path) -> tuple[dict, float]:
    """Lag-1 dispatch/price ratios per step class, pooled over all lifecycles,
    and the pooled window wall/price ratio."""
    obs = json.loads(obs_path.read_text())
    tab = defaultdict(list)
    tot_dt = tot_p = 0.0
    for L in obs:
        st = L["steps"]
        for i, s in enumerate(st):
            if i + 1 >= len(st) or st[i + 1]["dt"] is None:
                continue
            x = st[i + 1]["dt"]
            tab[step_class(s["mode"], s["d"], s["p"])].append(x / s["lo"])
            tot_dt += x
            tot_p += s["lo"]
    return {k: sorted(v) for k, v in tab.items()}, tot_dt / tot_p


class Scaled:
    """Stands in for the ``gpu_cost`` module inside ``gpu_mt_sim``."""

    def __init__(self, kind: str, factor: float = 1.0, table: dict | None = None,
                 seed: int = 0):
        self.kind, self.factor, self.table = kind, factor, table
        self.rng = random.Random(seed)
        self.allr = sorted(x for v in (table or {}).values() for x in v)

    def __getattr__(self, name):
        return getattr(C, name)

    def step_ms(self, *, decodes, prefill_tokens, grid, bound):
        base = C.step_ms(decodes=decodes, prefill_tokens=prefill_tokens, grid=grid, bound=bound)
        if self.kind == "orig":
            return base
        if self.kind == "global":
            return base * self.factor
        mode = C.mode(decodes, prefill_tokens, grid)
        v = self.table.get(step_class(mode, decodes, prefill_tokens)) or self.allr
        return base * v[self.rng.randrange(len(v))]


class TracePool(S.BlockPool):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.npop = 0
        self.rel = defaultdict(list)
        self.lk = defaultdict(list)

    def pop(self, stamp, pos):
        self.npop += 1
        return super().pop(stamp, pos)

    def release(self, blocks):
        k = self.key.get(blocks[0])
        if k is not None:
            self.rel[k[0]].append(self.npop)
        return super().release(blocks)


def run_one(args) -> dict:
    n, cfg_name, r, variant, factor, table = args
    plan = MultiTurnPlan.from_json(json.loads((PLANS / f"gmain-n{n}-r{r}.json").read_text()))
    cfg = config_by_name(cfg_name, n)
    kind = {"orig": "orig", "x1.131": "global", "x1.210": "global", "mode_dist": "dist"}[variant]
    wrap = Scaled(kind, factor, table, seed=hash((n, cfg_name, r)) & 0xFFFF)
    pools = []

    def mkpool(*a, **k):
        p = TracePool(*a, **k)
        pools.append(p)
        return p

    OrigStep = S.Step

    def mkstep(**kw):
        st = OrigStep(**kw)
        st.npop = pools[0].npop      # after this step's allocations
        return st

    oldC, oldPool = S.C, S.BlockPool
    S.C, S.BlockPool, S.Step = wrap, mkpool, mkstep
    try:
        res = S.simulate(plan, cfg, eviction="lru", bound="lo")
    finally:
        S.C, S.BlockPool, S.Step = oldC, oldPool, OrigStep
    m = S.window_metrics(res, cfg, "lo")
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    grid = tuple(sorted(cfg.capture_sizes))
    wsteps = [s for s in res["steps"] if w0 <= s.start_s < w1]
    reqs = [q for q in res["requests"] if w0 <= q.arrival_s < w1]
    price = sum(C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=grid, bound="lo")
                for s in wsteps) / 1e3
    # dynamics (task C)
    arr = sorted(q.arrival_s for q in res["requests"])
    adm = sorted(q.admit_s for q in res["requests"])
    qlen = [bisect_right(arr, s.start_s) - bisect_right(adm, s.start_s) for s in wsteps]
    pool = pools[0]
    step_start = [s.start_s for s in res["steps"]]
    prev = {}
    for q in res["requests"]:
        prev[(q.session, q.turn)] = q
    later = [q for q in reqs if q.turn > 0]
    per_req = []
    for q in later:
        p = prev.get((q.session, q.turn - 1))
        i = bisect_right(step_start, q.admit_s + 1e-12) - 1     # admission step
        before = res["steps"][i - 1].npop if i > 0 else 0
        rels = pool.rel.get(q.session, [])
        oth = before - rels[q.turn - 1] if q.turn - 1 < len(rels) else None
        per_req.append({"wait_s": q.admit_s - q.arrival_s, "ttft_s": q.first_token_s - q.arrival_s,
                        "idle_s": (q.admit_s - p.finish_s) if p else None, "hit": q.hit,
                        "others_alloc": oth})
    modes = defaultdict(list)
    for s in wsteps:
        modes[step_class(s.mode, s.decodes, s.prefill_tokens)].append(s.duration_s * 1e3)
    return {"n": n, "config": cfg_name, "rep": r, "variant": variant,
            "reuse": m["reuse"], "reuse_rate": m["reuse_rate"],
            "requests_in_window": m["requests_in_window"],
            "price_per_turn_s": price / m["requests_in_window"],
            "wall_window_s": sum(s.duration_s for s in wsteps),
            "qlen": qlen, "per_req": per_req,
            "step_ms_by_class": {k: [statistics.median(v), len(v)] for k, v in modes.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    table, wall = ratio_table(a.obs)
    variants = {"orig": 1.0, "x1.131": 1.131, "x1.210": round(wall, 3), "mode_dist": 1.0}
    jobs = [(n, c, r, v, f, table if v == "mode_dist" else None)
            for v, f in variants.items() for n, c in CELLS for r in range(REPS)]
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(run_one, jobs))
    meta = {"wall_over_price_lag1": wall, "variants": variants,
            "class_median_ratio": {k: statistics.median(v) for k, v in table.items()},
            "class_n": {k: len(v) for k, v in table.items()}}
    a.out.write_text(json.dumps({"meta": meta, "runs": res}) + "\n")
    print("wrote", a.out, len(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
