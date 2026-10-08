#!/usr/bin/env python3
"""Directive work D: simple survival approximations against the full rule on
existing validation sets (post hoc, no new device measurement, no tuning).

Status: ``post_hoc``. Part 1 feeds *observed* server events into every rule,
so it is a mechanism analysis, not a prediction. Part 2 compares existing
probabilistic implementations on the analytic model's in-scope cells; it reuses
per-request inputs that read the predecessor's observed tokens (as
``stage3/v11_dev.py`` does), so it is post hoc too. Nothing here was
preregistered and nothing here is a blind result.

Rules (all imported, none re-fitted; coefficients are the ones in the code):

* ``full``  -- ``continuum.model.reference.FifoReplay`` built from the v2
  descriptor (immediate release, ``pre_evict`` dummy, allocate-before-lookup),
  the TASK72/73 reference semantics. Reads ALLOC / FREE-REQUEST / BUCKET only.
* ``A1_gap`` -- ``SubstrateDescriptor.survives_gap`` (TASK15 law candidate,
  TASK16 code): ``outer_slots(T) + B + outer_slots(R) <= outer_slot_count``,
  with ``B`` = server ALLOC lines strictly between T's FREE-REQUEST and R's
  ALLOC, i.e. allocations during the tool wait only.
* ``A2_cf`` -- TASK72's registered auxiliary (B1-1) closed form at the lookup:
  ``survival.survives(C, Window(1, (1,)*A, K_pin))`` with ``A`` = allocations
  in (T alloc, R alloc] and ``K_pin`` = replay's pinned-older-at-lookup.
  Development-set agreement 0.8328 on the 1,298 TASK72 re-arrivals.
* ``A2w_cnt`` -- the same window count without ``K_pin`` (TASK72's
  "window count exceeded" cause test).

Part 2 probabilistic implementations (per request, same inputs for all):
``v0_poi`` / ``v0_bin`` (``survival.survival_probability``, TASK71/72/73) and
``v1_ss`` (``survival_v1.steady_state_survival`` with the request's own gap,
as in ``model_v1_dev.py`` / ``v11_dev.py``); ``v1_prereg`` is the
preregistered cell value (``mt_predict.analytic``) and has no per-request
probability, so it gets no Brier score.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

import model_v0_retro as R  # noqa: E402
import mt_measure as M  # noqa: E402
import mt_predict as P  # noqa: E402
from config_search import descriptor_for  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival as S  # noqa: E402
from continuum.model import survival_v1 as V1  # noqa: E402
from continuum.model.reference import FifoReplay  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_V2, RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

ST3 = REPO / "results/npu/stage3"
PLAN_DIR = REPO / "experiments/npu/stage3/plans/main"

# role: "validation" = not used for any development (primary);
#       "dev_reference" = development set of the simulator / v1.1 (SIMBLIND_PREREG
#       declares N <= 16 the development set) -- reported separately, never pooled.
SETS = [
    {"task": "TASK95", "run": ST3 / "20261002-simblind", "index": "INDEX_SIM.json",
     "pred": "PREDICTIONS_SIM.json", "ns": (13, 17, 20), "role": "validation"},
    {"task": "TASK102", "run": ST3 / "20261002-ctxblind", "index": "INDEX_CTX.json",
     "pred": "PREDICTIONS_CTX.json", "ns": (15, 18), "role": "validation"},
    {"task": "TASK82", "run": ST3 / "20260930-main", "index": "INDEX.json",
     "pred": "PREDICTIONS.json", "ns": (6, 8, 10, 12), "role": "dev_reference"},
    {"task": "TASK87", "run": ST3 / "20261001-hiload", "index": "INDEX_HI.json",
     "pred": "PREDICTIONS_HI.json", "ns": (14, 16), "role": "dev_reference"},
]
CFGS = ("BASE", "BATCHONLY", "TUNED")
APPROX = ("A1_gap", "A2_cf", "A2w_cnt")
PROB = ("v1_ss", "v0_poi", "v0_bin")
BLOCK = D.inner_block_tokens


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_plans(index: str, n: int) -> list[MultiTurnPlan]:
    idx = json.loads((PLAN_DIR / index).read_text())
    ents = sorted((e for e in idx if e["n"] == n), key=lambda e: e["rep"])
    return [MultiTurnPlan.from_json(json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text()))
            for e in ents]


def cell_params(n: int, grid, batch, st):
    """mt_predict.analytic's internals at its fixed point (copied from
    stage3/v11_dev.py.cell_params with N as an argument; no change)."""
    desc = P.descriptor(grid, batch)
    p_s = 0.9
    for _ in range(30):
        ep = st["share_first"] * st["p_first_s"] + (1 - st["share_first"]) * (
            p_s * st["p_hit_s"] + (1 - p_s) * st["p_miss_s"])
        w = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                             think_mean_s=st["think_mean_s"], prefill_mean_s=ep, max_running=batch)
        occ = O.solve_occupancy(w, desc.step_time_s)
        arr = O.arrival_running_distribution(w, desc.step_time_s)
        t_run = desc.step_time_s(max(1, round(occ.mean_running)))
        service = ep + (st["gen_mean"] - 1) * t_run / occ.phi
        lam = occ.throughput_per_s * (n - 1) / n
        new = V1.steady_state_survival(capacity=batch, running_others_pmf=arr, lam=lam,
                                       mu=1.0 / service, s_active=service,
                                       idle_samples=P._compress(st["idle_samples"]))
        if abs(new - p_s) < 1e-7:
            p_s = new
            break
        p_s = 0.5 * (p_s + new)
    return {"occ": occ, "arr": arr, "t_run": t_run, "service": service,
            "lam": lam, "mu": 1.0 / service, "p_s": p_s,
            "cycle_s": st["think_mean_s"] + occ.mean_response_s}


def hit_tokens(t_prompt: int, r_prompt: int) -> int:
    """Hit formula used by mt_predict.plan_stats (prefill-computed prefix, inner
    block granularity, capped at prompt - 1)."""
    return (min(t_prompt, r_prompt - 1) // BLOCK) * BLOCK


def classify(rec: dict, pred: bool) -> str | None:
    """Failure type of an approximation relative to the full rule (None = agree)."""
    if pred == rec["full"]:
        return None
    if pred and not rec["full"]:     # approximation says survive, full rule says lost
        if rec["prior_other_turn"]:
            return "over:other"
        if rec["A"] + 1 > rec["C"]:
            return "over:alloc_window_overflow"        # T's own residence counted by FIFO
        if rec["t_evict_path"] == "dummy":
            return "over:dummy_pre_evict"
        if rec["t_evict_path"] == "admission":
            return "over:pinned_older_at_eviction"     # K_pin at the eviction instant
        return "over:other"
    # approximation says lost, full rule says survive
    if rec["prior_other_turn"]:
        return "under:hit_on_other_turn_entry"
    if rec["newer_victim_while_t_active"] > 0:
        return "under:t_active_protection"
    if rec["evictions_in_window"] == 0:
        return "under:no_eviction_free_slots"
    return "under:other"


def lifecycle(st_set: dict, cfg: str, n: int, rep: int, manifest: dict) -> list[dict]:
    run = st_set["run"]
    tag = f"{cfg}.n{n}.r{rep}"
    probe = run / "probe" / tag
    req_p = probe / f"requests.{tag}.jsonl"
    win_p = probe / f"windows.{tag}.json"
    srv_p = run / f"server-{tag}.log"
    for p in (req_p, win_p, srv_p):
        manifest[str(p.relative_to(REPO))] = sha256(p)
    rows = [json.loads(x) for x in req_p.read_text().splitlines() if x.strip()]
    win = json.loads(win_p.read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    grid, batch = P.CONFIGS[cfg]
    desc1 = descriptor_for(D, tuple(grid), batch)
    ev = R.parse_log(srv_p)
    lk = {}
    for e in M.parse_server(srv_p):
        if e[0] in ("hit", "partial"):
            lk[e[1]] = e[2]
    alloc_pos, obc, free_pos = {}, {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            alloc_pos.setdefault(e[1], i)
            obc[e[1]] = e[2]
        elif e[0] == "free":
            free_pos.setdefault(e[1], i)
    sid_of = {}
    for sid in alloc_pos:
        sid_of.setdefault(sid.rsplit("-", 2)[0], sid)
    sess, joined, row_of = {}, {}, {}
    for x in rows:
        sid = sid_of.get(x["request_id"])
        if sid:
            sess[sid] = x["session"]
            joined[(x["session"], x["turn"])] = sid
            row_of[(x["session"], x["turn"])] = x
    ref = [("alloc", e[1]) if e[0] == "alloc" else ("free", e[1]) if e[0] == "free"
           else ("decode", e[1]) if e[0] == "bucket" else ("skip",) for e in ev]
    rp = FifoReplay.for_descriptor(RBLN_CA25_V2.with_config(grid=grid, max_running=batch,
                                                            reuse_capacity=batch)).run(
        ref, session_of=lambda k: sess.get(k, k))
    assert rp.capacity == batch and rp.release == "immediate" and rp.dummy == "pre_evict" \
        and rp.allocate_before_lookup
    ev_by_key = defaultdict(list)
    for x in rp.evictions:
        ev_by_key[x.key].append(x)
    ev_pos = sorted((x.pos, x.key) for x in rp.evictions)
    out = []
    for x in rows:
        if x["turn"] < 1:
            continue
        key = (x["session"], x["turn"])
        rid, t_key = joined.get(key), joined.get((x["session"], x["turn"] - 1))
        rec = {"set": st_set["task"], "role": st_set["role"], "cfg": cfg, "N": n, "rep": rep,
               "C": batch, "session": x["session"], "turn": x["turn"],
               "in_window": w0 is not None and w0 <= x["sent_s"] < w1}
        if rid is None or t_key is None or obc.get(rid) != 1 or obc.get(t_key) != 1:
            rec["status"] = "UNDECIDABLE"
            out.append(rec)
            continue
        prev = row_of[(x["session"], x["turn"] - 1)]
        srv_tok = lk.get(rid, 0)
        if x["cached_tokens"] is not None:
            obs_tok, src = x["cached_tokens"], "client"
            if (obs_tok > 0) != (srv_tok > 0):
                rec["status"] = "UNKNOWN"
                out.append(rec)
                continue
        else:
            obs_tok, src = srv_tok, "server"
        lu = rp.lookups[rid]
        t_pos, r_pos = alloc_pos[t_key], alloc_pos[rid]
        f_pos = free_pos.get(t_key)
        if f_pos is None or f_pos > r_pos:
            rec["status"] = "UNDECIDABLE"
            out.append(rec)
            continue
        A = sum(1 for e in ref[t_pos + 1:r_pos + 1] if e[0] == "alloc")
        B = sum(1 for e in ref[f_pos + 1:r_pos] if e[0] == "alloc")
        k_pin = lu.pinned_older_at_lookup or 0
        t_ev = [z for z in ev_by_key.get(t_key, []) if t_pos < z.pos <= r_pos]
        in_win = [(p, k) for p, k in ev_pos if t_pos < p <= r_pos]
        newer_active = sum(1 for p, k in in_win if p < f_pos and alloc_pos.get(k, -1) > t_pos)
        rec.update({
            "status": "DECIDED", "obs": obs_tok > 0, "obs_tokens": obs_tok, "obs_source": src,
            "full": lu.predicted_hit,
            "prior_other_turn": bool(lu.predicted_hit and lu.prior_key != t_key),
            "A": A, "B_gap": B, "K_pin": k_pin,
            "t_evict_path": t_ev[0].path if t_ev else None,
            "evictions_in_window": len(in_win), "newer_victim_while_t_active": newer_active,
            "t_prompt": prev["prompt_tokens"], "r_prompt": x["prompt_tokens"],
            "A1_gap": desc1.survives_gap(background_requests=B, target_tokens=prev["prompt_tokens"],
                                         resume_tokens=x["prompt_tokens"]),
            "A2_cf": S.survives(batch, S.Window(target_units=1, window_units=(1,) * A,
                                                pinned_units=k_pin)),
            "A2w_cnt": S.survives(batch, S.Window(target_units=1, window_units=(1,) * A)),
            "formula_tokens": hit_tokens(prev["prompt_tokens"], x["prompt_tokens"]),
            # part-2 inputs (v11_dev definitions)
            "gap": prev["gap_after_s"], "prev_cached": prev["cached_tokens"],
            "prev_completion": prev["completion_tokens"],
        })
        if prev["cached_tokens"] is None:
            rec["prev_cached"] = lk.get(t_key, 0)
        out.append(rec)
    return out


def agreement_table(recs: list[dict]) -> dict:
    d = [r for r in recs if r["status"] == "DECIDED"]
    n = len(d)
    t = {"requests_total": len(recs), "decided": n,
         "undecidable": sum(r["status"] == "UNDECIDABLE" for r in recs),
         "unknown": sum(r["status"] == "UNKNOWN" for r in recs),
         "obs_hit": sum(r["obs"] for r in d)}
    if not n:
        return t
    t["full_vs_obs"] = sum(r["full"] == r["obs"] for r in d)
    for a in APPROX:
        t[f"{a}_vs_full"] = sum(r[a] == r["full"] for r in d)
        t[f"{a}_vs_obs"] = sum(r[a] == r["obs"] for r in d)
        t[f"{a}_hit"] = sum(r[a] for r in d)
        conf = Counter((r[a], r["full"]) for r in d)
        t[f"{a}_confusion"] = {"approx_hit_full_hit": conf[(True, True)],
                               "approx_hit_full_miss": conf[(True, False)],
                               "approx_miss_full_hit": conf[(False, True)],
                               "approx_miss_full_miss": conf[(False, False)]}
        t[f"{a}_failure_types"] = dict(Counter(c for r in d if (c := classify(r, r[a]))))
    t["full_hit"] = sum(r["full"] for r in d)
    # reused tokens: predicted = formula on predicted hit, else 0; observed = obs_tokens
    obs_hits = [r for r in d if r["obs"]]
    t["formula_eq_obs_on_obs_hits"] = sum(r["formula_tokens"] == r["obs_tokens"] for r in obs_hits)
    t["obs_hits"] = len(obs_hits)
    t["obs_tokens_sum"] = sum(r["obs_tokens"] for r in d)
    for a in ("full",) + APPROX:
        pred = [r["formula_tokens"] if r[a] else 0 for r in d]
        diff = [p - r["obs_tokens"] for p, r in zip(pred, d)]
        t[f"{a}_tokens_sum"] = sum(pred)
        t[f"{a}_tokens_signed_diff_sum"] = sum(diff)
        t[f"{a}_tokens_abs_diff_sum"] = sum(abs(z) for z in diff)
        t[f"{a}_tokens_abs_diff_per_req"] = sum(abs(z) for z in diff) / n
    return t


# -- development-set reference (TASK72 1,298 re-arrivals, two-turn runs) -------

def dev_reference() -> dict:
    """A1/A2 on TASK72's development set, same code path as r5prime. Reported
    only as the anchor the approximations were already compared on."""
    stats = Counter()
    for task, run in R.R5_RUNS:
        for tag, rows, server, meta_p in R._cells(run):
            meta = json.load(open(meta_p))
            C = R._capacity(meta)
            grid = tuple(meta.get("buckets") or (1, 2, 4, 8))
            desc1 = descriptor_for(D, grid if grid[-1] == C else tuple(sorted(set(grid) | {C})), C)
            ev = R.parse_log(server)
            allocs = [e for e in ev if e[0] == "alloc"]
            sid_of = {}
            for a_ in allocs:
                sid_of.setdefault(a_[1].rsplit("-", 2)[0], a_[1])
            sess, joined, row_of = {}, {}, {}
            for r in rows:
                sid = sid_of.get(r["request_id"])
                if sid is not None:
                    sess[sid] = r["session"]
                    joined[(r["session"], r["turn"])] = sid
                    row_of[(r["session"], r["turn"])] = r
            obc = {a_[1]: a_[2] for a_ in allocs}
            rp = R.Replay(C, C, "pre_evict", "immediate", session_of=lambda q: sess.get(q, q)).run(ev)
            srv_hit = {e[1] for e in ev if e[0] == "hit"} | \
                {e[1] for e in ev if e[0] == "partial" and e[2] > 0}
            pos_of = {}
            free_of = {}
            for i, e in enumerate(ev):
                if e[0] == "alloc":
                    pos_of.setdefault(e[1], i)
                elif e[0] == "free":
                    free_of.setdefault(e[1], i)
            for r in rows:
                if r["turn"] < 1:
                    continue
                sid, t0 = joined.get((r["session"], r["turn"])), joined.get((r["session"], r["turn"] - 1))
                if sid is None or t0 is None or obc.get(sid) != 1 or obc.get(t0) != 1:
                    stats["undecidable"] += 1
                    continue
                obs = (r["cached_tokens"] or 0) > 0
                if obs != (sid in srv_hit):
                    stats["unknown"] += 1
                    continue
                pr, pt = pos_of[sid], pos_of[t0]
                ft = free_of.get(t0)
                if ft is None or ft > pr:
                    stats["undecidable_no_free"] += 1
                    continue
                full = rp.lookups[sid]["predicted_hit"]
                A = sum(1 for e in ev[pt + 1:pr + 1] if e[0] == "alloc")
                B = sum(1 for e in ev[ft + 1:pr] if e[0] == "alloc")
                k_pin = rp.lookups[sid]["pinned_older_at_lookup"] or 0
                prev = row_of[(r["session"], r["turn"] - 1)]
                a1 = desc1.survives_gap(background_requests=B, target_tokens=prev["prompt_tokens"],
                                        resume_tokens=r["prompt_tokens"])
                a2 = S.survives(C, S.Window(target_units=1, window_units=(1,) * A, pinned_units=k_pin))
                a2w = S.survives(C, S.Window(target_units=1, window_units=(1,) * A))
                stats["decided"] += 1
                stats["full_vs_obs"] += int(full == obs)
                for k, v in (("A1_gap", a1), ("A2_cf", a2), ("A2w_cnt", a2w)):
                    stats[f"{k}_vs_obs"] += int(v == obs)
                    stats[f"{k}_vs_full"] += int(v == full)
    return dict(stats)


# -- part 2 -------------------------------------------------------------------------

def _cell2(job):
    """One in-scope cell: fixed point once, then every evaluation-window request."""
    task, cfg, n, recs, pre = job
    grid, batch = P.CONFIGS[cfg]
    st_set = next(s for s in SETS if s["task"] == task)
    if True:
        plans = load_plans(st_set["index"], n)
        st = P.plan_stats(plans)
        cp = cell_params(n, grid, batch, st)
        pm = D.prefill_cost_model
        scored = []
        for r in recs:
            if r["status"] != "DECIDED" or not r["in_window"]:
                continue
            s_act = pm.prefill_s(max(r["t_prompt"] - (r["prev_cached"] or 0), 0)) + \
                (r["prev_completion"] - 1) * cp["t_run"] / cp["occ"].phi
            win = S.fifo_window_samples(residence_s=s_act, gap_samples=[(r["gap"], 1.0)])
            q = {"obs": r["obs"], "rep": r["rep"]}
            q["v1_ss"] = V1.steady_state_survival(capacity=batch, running_others_pmf=cp["arr"],
                                                  lam=cp["lam"], mu=cp["mu"], s_active=s_act,
                                                  idle_samples=[(r["gap"], 1.0)])
            for law, k in (("poisson", "v0_poi"), ("binomial", "v0_bin")):
                q[k] = S.survival_probability(capacity=batch, target_units=1, resume_units=1,
                                              other_unit=1, other_sessions=n - 1,
                                              window_samples=win, cycle_s=cp["cycle_s"], law=law)
            scored.append(q)
        obs_rate = statistics.mean(q["obs"] for q in scored)
        cell = {"set": task, "role": st_set["role"], "cfg": cfg, "N": n, "n_requests": len(scored),
                "obs_reuse": obs_rate, "obs_hits": sum(q["obs"] for q in scored),
                "v1_prereg_reuse": pre["reuse_rate"],
                "v1_prereg_reproduced_p_s": cp["p_s"],
                "params": {k: cp[k] for k in ("t_run", "service", "lam", "mu", "cycle_s", "p_s")},
                "models": {}}
        for k in PROB:
            cell["models"][k] = {"pred_reuse": statistics.mean(q[k] for q in scored),
                                 "brier": statistics.mean((q[k] - q["obs"]) ** 2 for q in scored),
                                 "brier_sum": sum((q[k] - q["obs"]) ** 2 for q in scored)}
        cell["brier_climatology_in_cell"] = statistics.mean((obs_rate - q["obs"]) ** 2 for q in scored)
        reps = defaultdict(list)
        for q in scored:
            reps[q["rep"]].append(q)
        cell["per_rep"] = {str(rr): {"n": len(v), "obs": statistics.mean(q["obs"] for q in v),
                                     **{k: statistics.mean(q[k] for q in v) for k in PROB}}
                           for rr, v in sorted(reps.items())}
    return f"{task}.{cfg}.n{n}", cell


def part2(set_recs: dict, preds: dict, workers: int = 8) -> dict:
    """In-scope (N <= batch) cells only. Same per-request inputs for all models."""
    from concurrent.futures import ProcessPoolExecutor
    jobs = []
    for (task, cfg, n), recs in sorted(set_recs.items()):
        grid, batch = P.CONFIGS[cfg]
        if n > batch:
            continue
        pe = preds[task]["cells"][str(n)][cfg]
        pre = pe["v1"] if "v1" in pe else pe["analytic"]   # TASK80 file names it "analytic"
        keep = [r for r in recs if r["status"] == "DECIDED" and r["in_window"]]
        jobs.append((task, cfg, n, keep, pre))
    with ProcessPoolExecutor(max_workers=min(8, workers)) as ex:   # resource rule: <= 8
        res = list(ex.map(_cell2, jobs))
    return dict(sorted(res))


def summarize_part2(cells: dict, role: str) -> dict:
    cs = [c for c in cells.values() if c["role"] == role]
    if not cs:
        return {}
    s = {"cells": [f"{c['set']}.{c['cfg']}.n{c['N']}" for c in cs],
         "n_requests": sum(c["n_requests"] for c in cs)}
    s["reuse_MAE_cell"] = {"v1_prereg": statistics.mean(abs(c["v1_prereg_reuse"] - c["obs_reuse"]) for c in cs)}
    for k in PROB:
        s["reuse_MAE_cell"][k] = statistics.mean(abs(c["models"][k]["pred_reuse"] - c["obs_reuse"]) for c in cs)
    reps = [(c, rr) for c in cs for rr in c["per_rep"].values()]
    s["reuse_MAE_lifecycle"] = {k: statistics.mean(abs(rr[k] - rr["obs"]) for _, rr in reps) for k in PROB}
    s["reuse_MAE_lifecycle"]["v1_prereg"] = statistics.mean(abs(c["v1_prereg_reuse"] - rr["obs"]) for c, rr in reps)
    s["n_lifecycles"] = len(reps)
    n = s["n_requests"]
    s["brier_pooled"] = {k: sum(c["models"][k]["brier_sum"] for c in cs) / n for k in PROB}
    s["brier_climatology_in_cell_pooled"] = sum(c["brier_climatology_in_cell"] * c["n_requests"] for c in cs) / n
    s["brier_v1_prereg"] = "NOT_ASSIGNED (cell-level value, no per-request probability)"
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ST3 / "dx_simple_approx" / "dx_simple_approx.json")
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--skip-dev-reference", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    t0 = time.time()
    manifest: dict[str, str] = {}
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    status = subprocess.run(["git", "-C", str(REPO), "status", "--short"], capture_output=True,
                            text=True).stdout
    for f in ("model/reference.py", "model/survival.py", "model/survival_v1.py",
              "model/occupancy.py", "substrate/descriptor.py"):
        p = REPO / "src/continuum" / f
        manifest[str(p.relative_to(REPO))] = sha256(p)
    for p in (HERE / "dx_simple_approx.py", HERE / "model_v0_retro.py", REPO / "experiments/npu/stage3/mt_predict.py",
              REPO / "experiments/npu/stage3/mt_measure.py", REPO / "experiments/npu/stage3/v11_dev.py",
              REPO / "experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py", HERE / "config_search.py"):
        manifest[str(p.relative_to(REPO))] = sha256(p)
    preds = {}
    all_recs = []
    by_cell = defaultdict(list)
    for st_set in SETS:
        pp = PLAN_DIR / st_set["pred"]
        manifest[str(pp.relative_to(REPO))] = sha256(pp)
        ip = PLAN_DIR / st_set["index"]
        manifest[str(ip.relative_to(REPO))] = sha256(ip)
        preds[st_set["task"]] = json.loads(pp.read_text())
        for n in st_set["ns"]:
            for cfg in CFGS:
                for rep in range(10):   # TASK81 added N=8 r5-r9 plans
                    if not (st_set["run"] / "probe" / f"{cfg}.n{n}.r{rep}").exists():
                        continue
                    recs = lifecycle(st_set, cfg, n, rep, manifest)
                    all_recs.extend(recs)
                    by_cell[(st_set["task"], cfg, n)].extend(recs)
        print(st_set["task"], "parsed", round(time.time() - t0, 1), "s", flush=True)

    part1 = {"by_cell": {}, "by_set": {}, "by_role": {}}
    for (task, cfg, n), recs in sorted(by_cell.items()):
        part1["by_cell"][f"{task}.{cfg}.n{n}"] = {"all": agreement_table(recs),
                                                  "eval_window": agreement_table([r for r in recs if r["in_window"]])}
    for st_set in SETS:
        rs = [r for r in all_recs if r["set"] == st_set["task"]]
        part1["by_set"][st_set["task"]] = {"role": st_set["role"], "all": agreement_table(rs),
                                           "eval_window": agreement_table([r for r in rs if r["in_window"]])}
    for role in ("validation", "dev_reference"):
        rs = [r for r in all_recs if r["role"] == role]
        part1["by_role"][role] = {"all": agreement_table(rs),
                                  "eval_window": agreement_table([r for r in rs if r["in_window"]])}
    # in-scope / out-of-scope split for validation
    for scope in ("in_scope", "out_of_scope"):
        rs = [r for r in all_recs if r["role"] == "validation" and r.get("C") and
              ((r["N"] <= r["C"]) == (scope == "in_scope"))]
        part1["by_role"][f"validation_{scope}"] = {"all": agreement_table(rs)}
    print("part1 done", round(time.time() - t0, 1), "s", flush=True)

    p2 = part2(by_cell, preds, a.workers)
    part2_out = {"cells": p2, "summary": {"validation": summarize_part2(p2, "validation"),
                                          "dev_reference": summarize_part2(p2, "dev_reference")}}
    print("part2 done", round(time.time() - t0, 1), "s", flush=True)
    dev = None if a.skip_dev_reference else dev_reference()

    out = {"status": "post_hoc",
           "note": "Mechanism analysis on observed events; not preregistered; not a blind result.",
           "git_head": head, "git_status_short": status, "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "python": sys.version, "seconds": round(time.time() - t0, 1),
           "sets": [{k: (str(v.relative_to(REPO)) if isinstance(v, Path) else v) for k, v in s.items()}
                    for s in SETS],
           "part1": part1, "part2": part2_out, "dev_reference_task72": dev,
           "manifest_sha256": manifest,
           "requests": [{k: v for k, v in r.items()} for r in all_recs]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float) + "\n")

    if a.csv:
        cols = ["scope", "role", "decided", "obs_hit", "full_vs_obs"] + \
            [f"{x}_{y}" for x in APPROX for y in ("vs_full", "vs_obs")] + \
            ["full_tokens_abs_diff_sum"] + [f"{x}_tokens_abs_diff_sum" for x in APPROX] + ["obs_tokens_sum"]
        lines = [",".join(cols)]
        keys = [("by_set", k) for k in part1["by_set"]] + [("by_role", k) for k in part1["by_role"]] + \
            [("by_cell", k) for k in part1["by_cell"]]
        for grp, k in keys:
            e = part1[grp][k]
            t = e["all"]
            role = e.get("role", k if grp == "by_role" else None)
            if grp == "by_cell":
                role = next(s["role"] for s in SETS if s["task"] == k.split(".")[0])
            lines.append(",".join(str(x) for x in [f"{grp}:{k}", role] + [t.get(c) for c in cols[2:]]))
        a.csv.parent.mkdir(parents=True, exist_ok=True)
        a.csv.write_text("\n".join(lines) + "\n")

    # console summary
    for role, e in part1["by_role"].items():
        t = e["all"]
        print(role, {k: t.get(k) for k in ("decided", "undecidable", "unknown", "obs_hit", "full_vs_obs",
                                            "A1_gap_vs_full", "A2_cf_vs_full", "A2w_cnt_vs_full")})
        for x in APPROX:
            if f"{x}_failure_types" in t:
                print("   ", x, t[f"{x}_failure_types"])
    print("part2", json.dumps(part2_out["summary"], indent=1, default=float))
    print("dev_reference", dev)
    print("total", round(time.time() - t0, 1), "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
