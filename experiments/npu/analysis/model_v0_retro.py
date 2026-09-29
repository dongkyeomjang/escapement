#!/usr/bin/env python3
"""Retro comparison of the analytic model v0 with existing data (R1-R5').

Registered in docs/research/MODEL_V0_RETRO_PREREG.md (initial 8c107a0,
amendment 1 1728f0d). This script only *imports* ``continuum.model``; it never
edits it, and it does not change simulator defaults.

Each item writes one JSON under ``--out-dir`` (default
``results/npu/stage3/model_v0_retro/``). Tables M01.. are built from those files
by ``make_tables.py``.

Inputs to model predictions are restricted as registered:
* R1 / R5' replay reads only ``[PFX] [ALLOC]``, ``[PFX] [FREE-REQUEST]`` and
  ``[BUCKET]`` lines. Outcome lines (``[EVICTION]``, ``[MAPPING-*]``,
  ``[CACHE-*]``) are read only as observations.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuum.model import grid as G  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival as S  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

ST2 = REPO / "results/npu/stage2"

# -- log parsing -------------------------------------------------------------

_ALLOC = re.compile(r"\[PFX\] \[ALLOC\] REQUEST=(\S+) \| OB_COUNT=(\d+) OB=\[([^\]]*)\]")
_FREE = re.compile(r"\[PFX\] \[FREE-REQUEST\] REQUEST=(\S+)")
_EVICT = re.compile(r"\[PFX\] \[EVICTION\] OB=(\d+)")
_HIT = re.compile(r"\[PFX\] \[CACHE-HIT\] REQUEST=(\S+)")
_PARTIAL = re.compile(r"\[PFX\] \[CACHE-PARTIAL\] REQUEST=(\S+) \| REUSED=(\d+)/")
_BUCKET = re.compile(r"\[BUCKET\] request_nums=(\d+)")
_DBEGIN = re.compile(r"\[OBS\] \[DUMMY-BEGIN\]")
_DEND = re.compile(r"\[OBS\] \[DUMMY-END\]")


def parse_log(path: Path) -> list[tuple]:
    ev = []
    with path.open(errors="replace") as fh:
        for line in fh:
            if "[PFX]" not in line and "[BUCKET]" not in line and "[OBS]" not in line:
                continue
            m = _ALLOC.search(line)
            if m:
                obs = [int(x) for x in m.group(3).split(",") if x.strip()]
                ev.append(("alloc", m.group(1), int(m.group(2)), obs))
                continue
            m = _FREE.search(line)
            if m:
                ev.append(("free", m.group(1)))
                continue
            m = _EVICT.search(line)
            if m:
                ev.append(("evict", int(m.group(1))))
                continue
            m = _HIT.search(line)
            if m:
                ev.append(("hit", m.group(1)))
                continue
            m = _PARTIAL.search(line)
            if m:
                ev.append(("partial", m.group(1), int(m.group(2))))
                continue
            m = _BUCKET.search(line)
            if m:
                ev.append(("bucket", int(m.group(1))))
                continue
            if _DBEGIN.search(line):
                ev.append(("dbegin",))
            elif _DEND.search(line):
                ev.append(("dend",))
    return ev


# -- replay of (B1-1) ----------------------------------------------------------

class Replay:
    """FIFO-by-allocation pool driven by ALLOC / FREE-REQUEST / [BUCKET] only.

    ``mode``: ``pre_evict`` (observed dummy reading), ``reserved`` (TASK69
    switch reading) or ``none``. ``release``: ``immediate`` or ``deferred``
    (inactive only after the next admission's victim choice).
    """

    def __init__(self, capacity: int, ceiling: int, mode: str = "pre_evict",
                 release: str = "immediate", session_of=None):
        self.C = capacity
        self.ceiling = ceiling
        self.mode = mode
        self.release = release
        self.session_of = session_of or (lambda req: req)
        self.entries: list[dict] = []     # resident entries, allocation order
        self.pending: list[str] = []
        self.evictions: list[dict] = []   # predicted: {"req", "pos", "path"}
        self.lookups: dict[str, dict] = {}
        self.undefined: list[int] = []

    def _active_count(self) -> int:
        return sum(1 for e in self.entries if e["active"])

    def _evict_one(self, pos: int, path: str) -> bool:
        for i, e in enumerate(self.entries):
            if not e["active"]:
                self.evictions.append({"req": e["req"], "pos": pos, "path": path})
                del self.entries[i]
                return True
        self.undefined.append(pos)
        return False

    def run(self, events: list[tuple]) -> "Replay":
        for pos, e in enumerate(events):
            kind = e[0]
            if kind == "alloc":
                req = e[1]
                need = 1
                if self.mode == "reserved":
                    active = self._active_count()
                    need += int(0 < active < self.ceiling)
                while self.C - len(self.entries) < need:
                    if not self._evict_one(pos, "admission"):
                        break
                if self.release == "deferred":
                    for r in self.pending:
                        for x in self.entries:
                            if x["req"] == r:
                                x["active"] = False
                    self.pending.clear()
                sess = self.session_of(req)
                prior = [x for x in self.entries if x["session"] == sess]
                pinned = None
                if prior:
                    first = self.entries.index(prior[0])
                    pinned = sum(1 for x in self.entries[:first] if x["active"])
                self.entries.append({"req": req, "session": sess, "active": True})
                self.lookups[req] = {"pos": pos, "predicted_hit": bool(prior),
                                     "prior_req": prior[-1]["req"] if prior else None,
                                     "pinned_older_at_lookup": pinned}
            elif kind == "free":
                if self.release == "immediate":
                    for x in self.entries:
                        if x["req"] == e[1]:
                            x["active"] = False
                else:
                    self.pending.append(e[1])
            elif kind == "bucket" and self.mode == "pre_evict":
                n = e[1]
                if 0 < n < self.ceiling and len(self.entries) >= self.C:
                    if any(not x["active"] for x in self.entries):
                        self._evict_one(pos, "dummy")
        return self


def observed_evictions(events: list[tuple]) -> list[dict]:
    """Observed evictions mapped to the request whose entry held the OB."""
    holder: dict[int, str] = {}
    out = []
    for pos, e in enumerate(events):
        if e[0] == "alloc":
            for ob in e[3]:
                holder[ob] = e[1]
        elif e[0] == "evict":
            out.append({"req": holder.get(e[1]), "pos": pos, "ob": e[1]})
            holder.pop(e[1], None)
    return out


# -- R1 --------------------------------------------------------------------------

R1_RUNS = [
    ("TASK14", ST2 / "20260819-200800-gap-turnover", "server-B*.log", "sequential"),
    ("TASK15", ST2 / "20260819-204900-cliff-repro", "server-B*.log", "sequential"),
    ("TASK63", ST2 / "20260912-134732-dummy-lifecycle", "server-A.B*.log", "sequential"),
    ("TASK63", ST2 / "20260912-134732-dummy-lifecycle", "server-B.b*.log", "concurrent"),
    ("TASK64", ST2 / "20260912-144017-admission-eviction", "server-R0*.log", "back_to_back"),
]


def _trial_m(name: str) -> int | None:
    m = re.match(r"server-(?:A\.)?B(\d+)", name)
    return int(m.group(1)) if m else None


def r1() -> dict:
    C = D.outer_slot_count
    trials = []
    for task, run, pat, kind in R1_RUNS:
        for path in sorted(run.glob(pat)):
            ev = parse_log(path)
            allocs = [e for e in ev if e[0] == "alloc"]
            obs_ev = observed_evictions(ev)
            rp = Replay(C, C, "pre_evict").run(ev)
            t = {"task": task, "file": str(path.relative_to(REPO)), "kind": kind,
                 "allocs": len(allocs), "ob_count_all_1": all(a[2] == 1 for a in allocs)}
            # P2
            pred_n = S.sequential_eviction_count(allocations=len(allocs), capacity_units=C,
                                                 trailing_dummy=True)
            t["P2"] = {"pred": pred_n, "obs": len(obs_ev), "ok": pred_n == len(obs_ev)}
            t["P2_replay_count"] = len(rp.evictions)
            # P3: victim identity, in order
            pv = [x["req"] for x in rp.evictions]
            ov = [x["req"] for x in obs_ev]
            t["P3"] = {"n": len(ov), "ok_each": [a == b for a, b in zip(pv, ov)],
                       "ok": pv == ov}
            # P4: timing. k-th eviction must lie after alloc #(C+k-1) and before
            # alloc #(C+k); the next event is the first [BUCKET] with 0<n<C
            # after alloc #(C+k-1), unless no such bucket precedes alloc #(C+k)
            # (back-to-back admissions): then it is alloc #(C+k) itself.
            alloc_pos = [i for i, e in enumerate(ev) if e[0] == "alloc"]
            p4 = []
            for k, o in enumerate(obs_ev, start=1):
                lo = alloc_pos[C + k - 2] if C + k - 2 < len(alloc_pos) else None
                hi = alloc_pos[C + k - 1] if C + k - 1 < len(alloc_pos) else len(ev)
                if lo is None:
                    p4.append({"k": k, "ok": False, "why": "fewer allocations than predicted"})
                    continue
                buckets = [i for i in range(lo, hi) if ev[i][0] == "bucket" and 0 < ev[i][1] < C]
                if buckets:
                    path_pred = "dummy"
                    anchor = buckets[0]
                    # eviction must be after lo and before that bucket, with no
                    # partial bucket in between
                    ok = lo < o["pos"] < anchor
                else:
                    path_pred = "admission"
                    anchor = hi
                    nxt = next((ev[i] for i in range(o["pos"] + 1, len(ev))
                                if ev[i][0] in ("alloc", "bucket")), None)
                    ok = lo < o["pos"] < hi and nxt is not None and nxt[0] == "alloc"
                item = {"k": k, "path_pred": path_pred, "ok": bool(ok)}
                if any(e[0] == "dbegin" for e in ev):
                    # inside a DUMMY bracket?
                    b = max((i for i in range(0, o["pos"]) if ev[i][0] == "dbegin"), default=-1)
                    en = max((i for i in range(0, o["pos"]) if ev[i][0] == "dend"), default=-1)
                    inside = b > en
                    item["in_dummy_bracket"] = inside
                    item["ok"] = item["ok"] and (inside == (path_pred == "dummy"))
                p4.append(item)
            t["P4"] = {"items": p4, "ok": all(x["ok"] for x in p4)}
            # P1: sequential only
            if kind == "sequential":
                m = _trial_m(path.name)
                w = S.sequential_window(target_units=S.sequence_slot_units(D, 2000),
                                        background_units=[1] * m,
                                        resume_units=S.sequence_slot_units(D, 2008))
                pred = S.survives(C, w)
                target, resume = allocs[0][1], allocs[-1][1]
                hit = any(e[0] == "hit" and e[1] == resume for e in ev)
                partial = [e for e in ev if e[0] == "partial" and e[1] == resume]
                rpos = alloc_pos[-1]
                t_ob = allocs[0][3][0]
                evicted_before = any(o["req"] == target and o["pos"] < rpos for o in obs_ev)
                if hit:
                    obs = True
                elif partial:
                    obs = partial[0][2] > 0
                else:
                    obs = False if evicted_before else None
                t["P1"] = {"m": m, "pred_survive": pred, "obs_survive": obs,
                           "obs_channel": "CACHE-HIT" if hit else ("CACHE-PARTIAL" if partial
                                                                  else "target evicted before resume ALLOC"),
                           "replay_pred": rp.lookups[resume]["predicted_hit"] if resume in rp.lookups else None,
                           "ok": (obs is not None and obs == pred)}
            trials.append(t)
    seq = [t for t in trials if "P1" in t]
    summary = {
        "trials": len(trials),
        "P1": f"{sum(t['P1']['ok'] for t in seq)}/{len(seq)}",
        "P1_unknown": sum(1 for t in seq if t["P1"]["obs_survive"] is None),
        "P2": f"{sum(t['P2']['ok'] for t in trials)}/{len(trials)}",
        "P3_evictions": f"{sum(sum(t['P3']['ok_each']) for t in trials)}/"
                        f"{sum(t['P3']['n'] for t in trials)}",
        "P3_trials": f"{sum(t['P3']['ok'] for t in trials)}/{len(trials)}",
        "P4_evictions": f"{sum(sum(x['ok'] for x in t['P4']['items']) for t in trials)}/"
                        f"{sum(len(t['P4']['items']) for t in trials)}",
        "P4_admission_path_pred": sum(1 for t in trials for x in t["P4"]["items"]
                                      if x["path_pred"] == "admission"),
    }
    ok = all(t["P2"]["ok"] and t["P3"]["ok"] and t["P4"]["ok"] for t in trials) and \
        all(t["P1"]["ok"] for t in seq)
    summary["verdict"] = "PASS" if ok else "FAIL"
    return {"summary": summary, "trials": trials}


# -- R2 --------------------------------------------------------------------------

def r2() -> dict:
    from continuum.sim.cache import GranularPool
    C, blk = D.inner_block_count, D.inner_block_tokens
    tgt, res = 2000, 2008
    full_hit_units = D.hit_formula.hit_tokens(shared_prefix_tokens=tgt, query_tokens=res) // blk
    rows = []
    mism = 0
    cells = 0
    for bg in (500, 1000, 2000, 4000):
        sim_curve, mod_curve = [], []
        for b in range(0, 131):
            pool = GranularPool(capacity=C, block_tokens=blk, policy="lru")
            pool.admit(session_key="target", blocks_needed=pool.blocks_for(tgt), prompt_tokens=tgt)
            pool.release("target")
            for i in range(b):
                pool.settle()
                pool.admit(session_key=f"bg{i}", blocks_needed=pool.blocks_for(bg), prompt_tokens=bg)
                pool.release(f"bg{i}")
            pool.settle()
            hit, _ = pool.admit(session_key="target", blocks_needed=pool.blocks_for(res),
                                prompt_tokens=res)
            sim_curve.append(D.hit_formula.hit_tokens(shared_prefix_tokens=hit, query_tokens=res))
            w = S.sequential_window(target_units=S.block_units(D, tgt),
                                    background_units=[S.block_units(D, bg)] * b,
                                    resume_units=S.block_units(D, res))
            mod_curve.append(S.reusable_tokens(hit_formula=D.hit_formula, granularity="block",
                                               capacity=C, window=w, unit_tokens=blk,
                                               cached_prefix_tokens=tgt, query_tokens=res))
        diffs = [b for b in range(len(sim_curve)) if sim_curve[b] != mod_curve[b]]
        cells += len(sim_curve)
        mism += len(diffs)
        full = sim_curve[0]
        th = S.block_pool_thresholds(capacity=C, target_units=S.block_units(D, tgt),
                                     background_unit=S.block_units(D, bg),
                                     resume_units=S.block_units(D, res),
                                     full_hit_units=full_hit_units)
        rows.append({"background_tokens": bg,
                     "sim_first_loss": next((i for i, v in enumerate(sim_curve) if v < full), None),
                     "sim_zero": next((i for i, v in enumerate(sim_curve) if v == 0), None),
                     "model_first_loss": th[0], "model_zero": th[1],
                     "mismatch_B": diffs,
                     "levels_sim": sorted(set(sim_curve), reverse=True)})
    return {"summary": {"cells": cells, "mismatches": mism,
                        "verdict": "CONSISTENT" if mism == 0 else "INCONSISTENT"},
            "rows": rows}


# -- R3 --------------------------------------------------------------------------

G_STAR = (1, 4, 6, 8, 10, 16)
G_REF = (1, 2, 4, 8, 16)
TOP, KMAX = 16, 6


def _fixed_for(grid_cand: tuple[int, ...]) -> dict[int, float]:
    return G.interpolated_fixed_costs(D.step_cost_model.fixed_s_by_bucket, range(1, TOP + 1))


def _hist_from_pairs(pairs: dict[str, int]) -> dict[int, float]:
    h: dict[int, float] = defaultdict(float)
    for k, v in pairs.items():
        n = int(k.split("->")[0])
        h[n] += v
    return dict(h)


def _grid_eval(h: dict[int, float]) -> dict:
    fixed = _fixed_for(G_STAR)
    dp = G.optimal_grid(h, top=TOP, max_buckets=KMAX, fixed=fixed)
    cs = G.grid_fixed_cost(G_STAR, h, fixed)
    cd = G.grid_fixed_cost(dp.grid, h, fixed)
    cr = G.grid_fixed_cost(G_REF, h, fixed)
    regret = (cs - cd) / cs
    E = (cr - cs) / cs
    sc = D.step_cost_model
    tot_s = G.grid_total_cost(G_STAR, h, fixed, intercept=sc.intercept_s,
                              marginal=sc.marginal_s_per_request)
    tot_d = G.grid_total_cost(dp.grid, h, fixed, intercept=sc.intercept_s,
                              marginal=sc.marginal_s_per_request)
    regret_old = (tot_s - tot_d) / tot_s
    if E <= 0:
        verdict = "NOT_INFORMATIVE"
    elif dp.grid == G_STAR:
        verdict = "PASS (EXACT)"
    else:
        verdict = "PASS" if regret <= 0.25 * E else "FAIL"
    return {"h": {str(k): v for k, v in sorted(h.items())}, "dp_grid": list(dp.grid),
            "cost_grid_star_s": cs, "cost_grid_dp_s": cd, "cost_grid_ref_s": cr,
            "regret_rel": regret, "E": E, "threshold": 0.25 * E, "verdict": verdict,
            "old_regret_rel": regret_old,
            "old_verdict": "PASS" if regret_old <= 0.01 else "FAIL"}


def _sim_hist(grid_cand, cells):
    import config_search as CS
    import foresight as F
    from continuum.sim import SimConfig, simulate
    desc = CS.descriptor_for(D, grid_cand, TOP)
    h: dict[int, float] = defaultdict(float)
    for (n, b, s) in cells:
        res = simulate(desc, F.plan(n, b, s), SimConfig(max_running_requests=TOP))
        for k, v in _hist_from_pairs(res.pair_histogram()).items():
            h[k] += v
    return dict(h)


def r3() -> dict:
    import foresight as F
    gap = "toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60"
    gap_desc = F.set_gap(gap)
    cells = [(n, b, s) for n in (6, 8, 10) for s in (20260910, 20260921, 20260932)
             for b in (0, 1, 2)]
    h_sim = _sim_hist(G_STAR, cells)
    r3a = _grid_eval(h_sim)
    # R3b: measured TUNED [BUCKET]
    files = sorted((ST2 / "20260823-183505-final-confirm").glob("server-TUNED.n*.b*.log")) + \
        sorted((ST2 / "20260824-160028-n6-reconfirm").glob("server-TUNED.n*.b*.log"))
    h_obs: dict[int, float] = defaultdict(float)
    per_n: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for f in files:
        n = re.search(r"\.n(\d+)\.", f.name).group(1)
        for e in parse_log(f):
            if e[0] == "bucket":
                h_obs[e[1]] += 1
                per_n[n][e[1]] += 1
    r3b = _grid_eval(dict(h_obs))
    r3b_per_n = {n: _grid_eval(dict(v)) for n, v in sorted(per_n.items())}
    # R3c: best-response iteration on the simulator histogram
    chain = [list(G_STAR)]
    cur = tuple(r3a["dp_grid"])
    status = "fixed_point_at_start" if cur == G_STAR else None
    seen = {G_STAR}
    it = 0
    while status is None and it < 5:
        it += 1
        chain.append(list(cur))
        if cur in seen:
            status = "cycle"
            break
        seen.add(cur)
        h = _sim_hist(cur, cells)
        nxt = tuple(_grid_eval(h)["dp_grid"])
        if nxt == cur:
            status = "fixed_point"
            break
        cur = nxt
    if status is None:
        status = "no_convergence_in_5"
    # explore ratio of chain members from the TASK61 ledger
    ledger = json.load(open(ST2 / "20260911-153800-config-search-rerun/run-a/ledger.json"))
    rows = ledger["rows"]
    idx = {(tuple(r["buckets"]), r["batch_size"]): r for r in rows}
    chain_info = [{"grid": g, "explore_ratio": idx.get((tuple(g), TOP), {}).get("explore_ratio"),
                   "explore_rank": idx.get((tuple(g), TOP), {}).get("explore_rank")}
                  for g in chain]
    informative = [x for x in (r3a, r3b) if x["verdict"] != "NOT_INFORMATIVE"]
    if not informative:
        verdict = "NOT_INFORMATIVE"
    elif all(x["verdict"].startswith("PASS") for x in informative):
        verdict = "PASS (EXACT)" if all(x["verdict"] == "PASS (EXACT)" for x in informative) else "PASS"
    else:
        verdict = "FAIL"
    return {"summary": {"verdict": verdict, "R3a": r3a["verdict"], "R3b": r3b["verdict"],
                        "R3c": status, "old_R3a": r3a["old_verdict"],
                        "old_R3b": r3b["old_verdict"]},
            "gap": gap_desc, "R3a": r3a, "R3b": r3b, "R3b_per_n": r3b_per_n,
            "R3b_files": [str(f.relative_to(REPO)) for f in files],
            "R3c": {"status": status, "chain": chain_info}}


# -- R4 --------------------------------------------------------------------------

SRC_RUN = {"TASK19": "20260819-233800-paired-pilot-v2", "TASK20": "20260820-165200-nslots-sweep",
           "TASK23-2a": "20260821-222000-grid-observe", "TASK23-2b": "20260821-231000-grid-intervene",
           "TASK25": "20260822-160532-sim-oos"}


def _plan_stats(run: Path, arm: str, n: int) -> dict:
    gens, gaps, prompts = [], [], []
    pat = re.compile(rf"meta\.{arm}\.n{n}(\.b\d+)?\.json$")
    files = [f for f in sorted(run.glob("**/meta.*.json")) if pat.search(f.name)]
    for f in files:
        p = json.load(open(f))["plan"]
        for s in range(p["session_count"]):
            ctx = 0
            for t, g in enumerate(p["generation_tokens"][s]):
                seg = p["new_segment_tokens"][s][t]
                prompts.append(ctx + seg)
                ctx += seg + g
                gens.append(g)
                if t < len(p["generation_tokens"][s]) - 1:
                    gaps.append(p["gap_after_s"][s][t])
    return {"files": len(files),
            "gen_mean": statistics.mean(gens), "gap_mean": statistics.mean(gaps) if gaps else 0.0,
            "prompt_prefill_mean_s": statistics.mean(D.prefill_cost_model.prefill_s(q) for q in prompts),
            "gaps": gaps}


def _occ_for(n: int, grid_cand, st: dict, M: int = 8):
    import config_search as CS
    desc = CS.descriptor_for(D, tuple(grid_cand), M)
    w = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                         think_mean_s=st["gap_mean"], prefill_mean_s=st["prompt_prefill_mean_s"],
                         max_running=M)
    return O.solve_occupancy(w, desc.step_time_s), desc


def r4() -> dict:
    pr = json.load(open(ST2 / "padding_ratio.json"))
    out = []
    for c in pr["cells"]:
        n, grid_cand, src = c["N"], tuple(c["grid"]), c["src"]
        run = ST2 / SRC_RUN[src]
        st = _plan_stats(run, "AGENTIC", n)
        occ, desc = _occ_for(n, grid_cand, st)
        pred = occ.step_share
        hist = _hist_from_pairs(c["hist_agentic"])
        tot = sum(hist.values())
        obs = {k: v / tot for k, v in hist.items()}
        keys = set(pred) | set(obs)
        tvd = 0.5 * sum(abs(pred.get(k, 0) - obs.get(k, 0)) for k in keys)
        mp = sum(k * v for k, v in pred.items())
        mo = sum(k * v for k, v in obs.items())

        def pad(dist):
            num = sum(v * (desc.bucket_for(k) - k) for k, v in dist.items())
            den = sum(v * desc.bucket_for(k) for k, v in dist.items())
            return num / den
        cyc = st["gap_mean"] + occ.mean_response_s
        out.append({"src": src, "N": n, "grid": list(grid_cand), "blocks": c["blocks"],
                    "plan_files": st["files"], "gen_mean": st["gen_mean"],
                    "gap_mean_s": st["gap_mean"], "tvd": tvd,
                    "mean_running_pred": mp, "mean_running_obs": mo,
                    "mean_running_diff": mp - mo, "padding_pred": pad(pred),
                    "padding_obs": pad(obs), "phi": occ.phi,
                    "mean_response_s": occ.mean_response_s, "cycle_s": cyc,
                    "pred": {str(k): v for k, v in sorted(pred.items())},
                    "obs": {str(k): v for k, v in sorted(obs.items())},
                    "conventional": "NOT_APPLICABLE (Z=0)"})
    return {"summary": {"cells": len(out),
                        "tvd_gt_0_3": sum(1 for r in out if r["tvd"] > 0.3),
                        "mean_running_underpredicted": sum(1 for r in out if r["mean_running_diff"] < 0),
                        "tvd_median": statistics.median(r["tvd"] for r in out),
                        "verdict": "EXPLORATORY"},
            "cells": out}


# -- R5 / R5' ------------------------------------------------------------------

R5_RUNS = [
    ("TASK20", ST2 / "20260820-165200-nslots-sweep"),
    ("TASK50", ST2 / "20260901-020342-null-channel"),
    ("TASK35", ST2 / "20260823-183505-final-confirm"),
    ("TASK36", ST2 / "20260824-160028-n6-reconfirm"),
    ("TASK40", ST2 / "20260824-222453-batch-saturation"),
    ("TASK54-mb", ST2 / "20260908-133635-grid-paired/mb"),
    ("TASK54-mb6", ST2 / "20260908-133635-grid-paired/mb6"),
]


def _cells(run: Path):
    for req in sorted(run.glob("**/requests.*.jsonl")):
        tag = req.name[len("requests."):-len(".jsonl")]          # ARM.nN.bK
        server = next(iter(sorted(run.glob(f"**/server-{tag}.log"))), None)
        meta = next(iter(sorted(run.glob(f"**/meta.{tag}.json"))), None)
        rows = [json.loads(x) for x in req.read_text().splitlines() if x.strip()]
        yield tag, rows, server, meta


def _capacity(meta: dict) -> int:
    m = re.search(r"-b(\d+)-", meta["served_model_id"])
    return int(m.group(1))


def r5prime() -> dict:
    runs = []
    all_mis = []
    for task, run in R5_RUNS:
        stats = Counter()
        cells = []
        for tag, rows, server, meta_p in _cells(run):
            meta = json.load(open(meta_p))
            C = _capacity(meta)
            ev = parse_log(server)
            allocs = [e for e in ev if e[0] == "alloc"]
            # client -> server id join (strict prefix)
            sid_of = {}
            for a in allocs:
                sid_of.setdefault(a[1].rsplit("-", 2)[0], a[1])
            sess_of_server = {}
            joined = {}
            for r in rows:
                sid = sid_of.get(r["request_id"])
                if sid is not None:
                    sess_of_server[sid] = r["session"]
                    joined[(r["session"], r["turn"])] = sid
            obc = {a[1]: a[2] for a in allocs}
            reps = {}
            for mode, rel in (("pre_evict", "immediate"), ("reserved", "immediate"),
                              ("pre_evict", "deferred")):
                reps[(mode, rel)] = Replay(C, C, mode, rel,
                                           session_of=lambda q: sess_of_server.get(q, q)).run(ev)
            srv_hit = {e[1] for e in ev if e[0] == "hit"} | \
                {e[1] for e in ev if e[0] == "partial" and e[2] > 0}
            for r in rows:
                if r["turn"] < 1:
                    continue
                key = (r["session"], r["turn"])
                sid = joined.get(key)
                t0 = joined.get((r["session"], r["turn"] - 1))
                rec = {"run": task, "cell": tag, "session": r["session"], "turn": r["turn"],
                       "cached_tokens": r["cached_tokens"]}
                if sid is None or t0 is None or obc.get(sid) != 1 or obc.get(t0) != 1:
                    rec["status"] = "UNDECIDABLE"
                    stats["UNDECIDABLE"] += 1
                    cells.append(rec)
                    continue
                obs = (r["cached_tokens"] or 0) > 0
                srv = sid in srv_hit
                if obs != srv:
                    rec["status"] = "UNKNOWN"
                    stats["UNKNOWN"] += 1
                    cells.append(rec)
                    continue
                main = reps[("pre_evict", "immediate")]
                if main.undefined and any(u <= main.lookups[sid]["pos"] for u in main.undefined):
                    rec["status"] = "UNDECIDABLE"
                    stats["UNDECIDABLE"] += 1
                    cells.append(rec)
                    continue
                pred = main.lookups[sid]["predicted_hit"]
                rec.update({"obs": obs, "pred": pred,
                            "pred_reserved": reps[("reserved", "immediate")].lookups[sid]["predicted_hit"],
                            "pred_deferred": reps[("pre_evict", "deferred")].lookups[sid]["predicted_hit"]})
                # closed-form cross-check: A and K_pin at the lookup
                pos_t0 = next(i for i, e in enumerate(ev) if e[0] == "alloc" and e[1] == t0)
                pos_r = main.lookups[sid]["pos"]
                A = sum(1 for e in ev[pos_t0 + 1:pos_r + 1] if e[0] == "alloc")
                rec["A"] = A
                # Registered auxiliary: (B1-1) closed form at the lookup instant,
                # K_pin = older entries active at the lookup, D = 0 (PRE_EVICT).
                # When the prior entry is gone K_pin is not defined; use 0.
                k_pin = main.lookups[sid]["pinned_older_at_lookup"] or 0
                rec["K_pin_at_lookup"] = k_pin
                rec["closed_form_pred"] = S.survives(C, S.Window(
                    target_units=1, window_units=(1,) * A, pinned_units=k_pin))
                stats["closed_form_match"] += int(rec["closed_form_pred"] == obs)
                if not obs:
                    # Model-side cause of an observed failure (registered 8.3):
                    # window count exceeded / K_pin / dummy pre-evict / other.
                    ev_t0 = next((x for x in main.evictions if x["req"] == t0), None)
                    rec["t0_evicted_path"] = ev_t0["path"] if ev_t0 else None
                    rec["t0_active_at_eviction"] = None
                    if not S.survives(C, S.Window(target_units=1, window_units=(1,) * A)):
                        cause = "window count exceeded"
                    elif not rec["closed_form_pred"]:
                        cause = "K_pin"
                    elif ev_t0 and ev_t0["path"] == "dummy":
                        cause = "dummy pre-evict"
                    else:
                        cause = "other"
                    rec["failure_cause"] = cause
                rec["status"] = "MATCH" if pred == obs else "MISMATCH"
                stats[rec["status"]] += 1
                stats["reserved_match"] += int(rec["pred_reserved"] == obs)
                if pred != obs:
                    if rec["pred_deferred"] == obs:
                        cat = "(i) release timing"
                    else:
                        cat = "(iii) other"
                    rec["category"] = cat
                    # event context: condensed sequence from T0 alloc to R alloc
                    ctx = []
                    for e in ev[pos_t0:pos_r + 1]:
                        if e[0] == "alloc":
                            ctx.append(f"A:{sess_of_server.get(e[1], '?')}")
                        elif e[0] == "free":
                            ctx.append(f"F:{sess_of_server.get(e[1], '?')}")
                        elif e[0] == "evict":
                            ctx.append(f"E:{e[1]}")
                    rec["events_t0_to_r"] = ctx
                    all_mis.append(rec)
                cells.append(rec)
        dec = stats["MATCH"] + stats["MISMATCH"]
        total = dec + stats["UNDECIDABLE"] + stats["UNKNOWN"]
        runs.append({"run": task, "path": str(run.relative_to(REPO)), "total": total,
                     "match": stats["MATCH"], "mismatch": stats["MISMATCH"],
                     "undecidable": stats["UNDECIDABLE"], "unknown": stats["UNKNOWN"],
                     "agreement": stats["MATCH"] / dec if dec else None,
                     "reserved_agreement": stats["reserved_match"] / dec if dec else None,
                     "closed_form_agreement": stats["closed_form_match"] / dec if dec else None,
                     "requests": cells})
    tot = sum(r["total"] for r in runs)
    und = sum(r["undecidable"] + r["unknown"] for r in runs)
    cats = Counter(m["category"] for m in all_mis)
    if tot and und / tot > 0.05:
        verdict = "INCONCLUSIVE"
    elif all(r["agreement"] is not None and r["agreement"] >= 0.95 for r in runs):
        verdict = "PASS" if cats.get("(iii) other", 0) == 0 else \
            f"PASS (미설명 {cats['(iii) other']}건)"
    else:
        verdict = "FAIL"
    dec_all = sum(r["match"] + r["mismatch"] for r in runs)
    return {"summary": {"verdict": verdict, "requests": tot, "decided": dec_all,
                        "agreement": sum(r["match"] for r in runs) / dec_all if dec_all else None,
                        "reserved_agreement": sum(r["reserved_agreement"] * (r["match"] + r["mismatch"])
                                                  for r in runs if r["reserved_agreement"] is not None) / dec_all,
                        "closed_form_agreement": sum(r["closed_form_agreement"] * (r["match"] + r["mismatch"])
                                                     for r in runs if r["closed_form_agreement"] is not None) / dec_all,
                        "undecidable_unknown_share": und / tot if tot else None,
                        "categories": dict(cats)},
            "runs": runs, "mismatches": all_mis}


def r5(r5p: dict) -> dict:
    """Probabilistic extension vs observed reuse, per cell (exploratory)."""
    import config_search as CS
    out = []
    nulls = defaultdict(list)
    for task, run in R5_RUNS:
        for tag, rows, server, meta_p in _cells(run):
            meta = json.load(open(meta_p))
            C = _capacity(meta)
            p = meta["plan"]
            n = p["session_count"]
            grid_cand = tuple(meta.get("buckets") or (1, 2, 4, 8))
            if grid_cand[-1] != C:
                grid_cand = tuple(sorted(set(grid_cand) | {C}))
            desc = CS.descriptor_for(D, grid_cand, C)
            gens = [g for s in p["generation_tokens"] for g in s]
            gaps = [s[0] for s in p["gap_after_s"]]
            prompts0 = [s[0] for s in p["new_segment_tokens"]]
            zmean = statistics.mean(gaps)
            if zmean <= 0:
                continue   # CONVENTIONAL: no gap, no steady state
            w = O.ClosedWorkload(sessions=n, decode_steps_per_request=statistics.mean(gens) - 1,
                                 think_mean_s=zmean,
                                 prefill_mean_s=statistics.mean(D.prefill_cost_model.prefill_s(q)
                                                                for q in prompts0),
                                 max_running=C)
            occ = O.solve_occupancy(w, desc.step_time_s)
            t_run = desc.step_time_s(max(1, round(occ.mean_running)))
            cyc = zmean + occ.mean_response_s
            pred = {"binomial": 0.0, "poisson": 0.0}
            for s in range(n):
                resid = D.prefill_cost_model.prefill_s(prompts0[s]) + \
                    (p["generation_tokens"][s][0] - 1) * t_run / occ.phi
                win = S.fifo_window_samples(residence_s=resid, gap_samples=[(gaps[s], 1.0)])
                for law in pred:
                    pred[law] += S.survival_probability(capacity=C, target_units=1, resume_units=1,
                                                        other_unit=1, other_sessions=n - 1,
                                                        window_samples=win, cycle_s=cyc, law=law)
            obs = sum(1 for r in rows if r["turn"] >= 1 and (r["cached_tokens"] or 0) > 0)
            out.append({"run": task, "cell": tag, "N": n, "C": C, "obs_reuse": obs,
                        "pred_binomial": pred["binomial"], "pred_poisson": pred["poisson"],
                        "turn1": n, "cycle_s": cyc})
            if task == "TASK50":
                nulls[n].append(obs)
    null_var = {str(k): {"counts": v, "mean": statistics.mean(v),
                         "var": statistics.pvariance(v)} for k, v in sorted(nulls.items())}
    # failure totals by natural grouping (for the manuscript's "73 failures")
    fail = defaultdict(int)
    for rr in r5p["runs"]:
        for q in rr["requests"]:
            if q.get("obs") is False:
                arm = q["cell"].split(".")[0]
                nn = q["cell"].split(".")[1]
                fail[(rr["run"], arm)] += 1
                fail[(rr["run"], arm, nn)] += 1
                fail[(rr["run"],)] += 1
    groups = {" / ".join(k): v for k, v in sorted(fail.items())}
    hits73 = [k for k, v in groups.items() if v == 73]
    # Two whole-run groups summing to 73 are also listed; a whole-run pair is
    # the only combination treated as a candidate.
    runs_only = {k: v for k, v in groups.items() if " / " not in k}
    pairs73 = [f"{a} + {b}" for a in runs_only for b in runs_only
               if a < b and runs_only[a] + runs_only[b] == 73]
    causes = defaultdict(Counter)
    for rr in r5p["runs"]:
        for q in rr["requests"]:
            if q.get("obs") is False:
                causes[rr["run"]][q.get("failure_cause")] += 1
                causes[rr["run"]]["path:" + str(q.get("t0_evicted_path"))] += 1
    return {"summary": {"cells": len(out), "verdict": "EXPLORATORY",
                        "binomial_abs_err_mean": statistics.mean(abs(c["pred_binomial"] - c["obs_reuse"]) for c in out),
                        "poisson_abs_err_mean": statistics.mean(abs(c["pred_poisson"] - c["obs_reuse"]) for c in out),
                        "binomial_bias_mean": statistics.mean(c["pred_binomial"] - c["obs_reuse"] for c in out),
                        "poisson_bias_mean": statistics.mean(c["pred_poisson"] - c["obs_reuse"] for c in out)},
            "cells": out, "task50_repeat": null_var, "failure_groups": groups,
            "groups_equal_73": hits73, "run_pairs_equal_73": pairs73,
            "failure_causes_by_run": {k: dict(v) for k, v in causes.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=REPO / "results/npu/stage3/model_v0_retro")
    ap.add_argument("--items", default="r1,r2,r3,r4,r5p,r5")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    items = args.items.split(",")
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    print("started", started)
    done = {}
    r5p = None
    for it in items:
        t0 = time.perf_counter()
        if it == "r1":
            res = r1()
        elif it == "r2":
            res = r2()
        elif it == "r3":
            res = r3()
        elif it == "r4":
            res = r4()
        elif it == "r5p":
            res = r5p = r5prime()
        elif it == "r5":
            if r5p is None:
                r5p = json.load(open(args.out_dir / "r5p.json"))
            res = r5(r5p)
        else:
            raise SystemExit(f"unknown item {it}")
        res["computed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        res["seconds"] = round(time.perf_counter() - t0, 2)
        (args.out_dir / f"{it}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str) + "\n")
        done[it] = res["summary"]
        print(it, json.dumps(res["summary"], ensure_ascii=False, default=str))
    (args.out_dir / "run_meta.json").write_text(json.dumps(
        {"started": started, "items": items, "summaries": done}, indent=2, ensure_ascii=False,
        default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
