#!/usr/bin/env python3
"""Boundary effects of the A'-GPU cost aggregation (directive G-09 task A; post_hoc).

The GPU counterpart of ``experiments/npu/analysis/boundary_sensitivity.py``
(NPU TASK111). Read-only over the GTASK11 / GTASK20 run logs and the committed
plans; nothing is measured and no input, model or simulator is changed.

A'-GPU of a lifecycle (``gpu_mt_measure.lifecycle_metrics``): the requests
sent in [w0, w1); every ``[GSTEP]`` between the ``[GPFX] ALLOC`` line of the
first and of the last of them, priced with ``gpu_cost.step_ms(decodes=d,
prefill_tokens=p)`` at bound lo / hi, where d = ``reqs`` if ``maxq == 1`` else
``reqs - max(1, k)`` (k = ALLOC lines since the previous step) and p =
``toks - d``; summed and divided by the request count.

Work A -- window length. The same w0, w1 = w0 + L for L in {60, 90, 120} s
(the runner stops sending at w0 + 120 s). Observed: A'-GPU per lifecycle and
the paired ratio (configuration / BASE, same replicate) median over the
verdict's lifecycles. At L = 120 the per-replicate ratios must equal the
verdict's ``5.2`` (GTASK11 N26: ``N26.POOL/BASE``) ratios exactly.
Predicted: each set's main predictor rerun with the committed code path and
inputs -- GTASK11 ``sim_lru`` (``predict_mt.sim_cell``: duration of the
simulated steps whose start is in [w0, w1)), GTASK20 ``ctx``
(``predict_blind.run_one``: price of those steps) -- pooled over the 5 plans
per window; at L = 120 the pooled ratio must equal the prediction file's
``ratio_to_base`` exactly.

Work B -- boundary residuals (observed). Step membership is rebuilt from the
log by the GTASK12 step progression (``replay.py``, without the block pool):
an ALLOC adds the request with its scheduled chunk; at each later schedule
every running request whose last token is not yet scheduled takes
``min(prompt - computed, budget)`` tokens if still prefilling, else 1. The
rebuilt (members, tokens) is checked against the step's (``reqs``, ``toks``).
A step's A'-GPU price is split into a decode share ``decode_ms(d)`` (d >= 1,
equally over the rebuilt decoders) and a prefill share ``price - decode
share`` (over the rebuilt prefill members in proportion to their tokens;
the whole price when d = 0). Per lifecycle:
  S (start) = share, inside the A'-GPU step range, of members sent before w0;
  E (end)   = share, in steps after the last window ALLOC line, of window members;
  corrected A'-GPU = (A'-GPU total - S + E) / requests.

usage: boundary_sensitivity.py --output <json> [--workers 24]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402
from parse_obs import parse  # noqa: E402
import gpu_cost as C  # noqa: E402
import gpu_mt_sim as SIM  # noqa: E402
import predict_blind as PB  # noqa: E402
import predict_mt as PM  # noqa: E402

RES = REPO / "results/gpu/multiturn"
# set -> run dir, Ns, plan dir, prediction file, main predictor
SETS = {
    "GTASK11": (RES / "main/20260930T1411Z", (20, 22, 24, 26), HERE / "plans/main",
                HERE / "plans/PREDICTIONS.json", "sim_lru"),
    "GTASK20": (RES / "blind/20261002T0655Z", (25, 28), HERE / "plans/blind",
                HERE / "plans/blind/PREDICTIONS_BLIND.json", "ctx"),
}
CONFIGS = ("BASE", "POOL", "POOL+GRID")
BOUNDS = ("lo", "hi")
WINDOWS = (60.0, 90.0, 120.0)
BUDGET = 2048


# -- observed ----------------------------------------------------------------------

def sid_map(ev, rows) -> dict[str, dict]:
    """server id -> client row (client id is a strict prefix of the server id)."""
    by_cid = {r["request_id"]: r for r in rows}
    out = {}
    for e in ev:
        if e["kind"] == "ALLOC" and e["req"] not in out:
            parts = e["req"].split("-")
            for k in range(2, len(parts)):
                r = by_cid.get("-".join(parts[:k]))
                if r is not None:
                    out[e["req"]] = r
                    break
    return out


def membership(ev, smap) -> dict[int, list]:
    """step line -> [(server id, tokens, is_decode)], GTASK12 step progression."""
    running: list[dict] = []
    sched: list[tuple[dict, int]] = []
    open_ = False
    budget = 0
    out = {}

    def start():
        nonlocal sched, open_, budget
        running[:] = [r for r in running if r["q"] < r["G"]]
        budget = BUDGET
        sched = []
        for r in running:
            if budget <= 0:
                break
            n = min(r["P"] - r["c"], budget) if r["c"] < r["P"] else 1
            budget -= n
            sched.append((r, n))
        open_ = True

    for e in ev:
        if e["kind"] in ("LOOKUP", "ALLOC", "ALLOC_FAIL"):
            if not open_:
                start()
            if e["kind"] == "ALLOC":
                row = smap.get(e["req"])
                if row is None:
                    continue
                r = {"sid": e["req"], "P": row["prompt_tokens"], "G": row["requested_generation_tokens"],
                     "c": e["computed"], "q": 0}
                n = e["scheduled"]
                budget -= n
                running.append(r)
                sched.append((r, n))
        elif e["kind"] == "STEP":
            if not open_:
                start()
            mem = []
            for r, n in sched:
                was_prefill = r["c"] < r["P"]
                mem.append((r["sid"], n, not was_prefill))
                r["c"] += n
                if (not was_prefill) or r["c"] >= r["P"]:
                    r["q"] += 1
            out[e["line"]] = mem
            open_ = False
    return out


def split_rule(e) -> tuple[int, int]:
    """(d, p) of a [GSTEP] by the A'-GPU rule (needs ``_k`` = ALLOCs since previous step)."""
    if e["maxq"] == 1:
        return e["reqs"], 0
    d = max(0, e["reqs"] - max(1, e["_k"]))
    return d, e["toks"] - d


def lifecycle(run: Path) -> dict:
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    prov = json.loads((run / "provenance.json").read_text())
    grid = tuple(sorted(prov["config"]["capture_sizes"]))
    w0 = win["warmup_end_s"]
    ev = parse(run / "server.log")
    smap = sid_map(ev, rows)
    sent_of = {sid: r["sent_s"] for sid, r in smap.items()}
    alloc_line = {}
    k = 0
    stepl = []
    for e in ev:
        if e["kind"] == "ALLOC":
            alloc_line.setdefault(e["req"], e["line"])
            k += 1
        elif e["kind"] == "STEP":
            e["_k"] = k
            k = 0
            stepl.append(e)
    sid_of = {}
    for sid in alloc_line:
        parts = sid.split("-")
        for j in range(2, len(parts)):
            sid_of.setdefault("-".join(parts[:j]), sid)
    mem = membership(ev, smap)
    integ = Counter()
    first_alloc = min(alloc_line.values())
    for e in stepl:
        m = mem.get(e["line"], [])
        if e["line"] < first_alloc:          # server warm-up steps, no request
            integ["steps_before_first_alloc"] += 1
            continue
        integ["steps"] += 1
        integ["members_eq_reqs"] += int(len(m) == e["reqs"])
        integ["tokens_eq_toks"] += int(sum(n for _, n, _ in m) == e["toks"])
        d, _ = split_rule(e)
        integ["decoders_eq_rule"] += int(sum(1 for _, _, dec in m if dec) == d)
    out = {"run": run.name, "integrity": dict(integ), "windows": {}}
    for L in WINDOWS:
        w1 = w0 + L
        ev_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
        lines = [alloc_line[sid_of[r["request_id"]]] for r in ev_rows]
        lo, hi = min(lines), max(lines)
        n = len(ev_rows)
        w = {"requests": n}
        for b in BOUNDS:
            total = st = en = 0.0
            nsteps = 0
            for e in stepl:
                d, p = split_rule(e)
                price = C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound=b) / 1e3
                inside = lo <= e["line"] <= hi
                if inside:
                    total += price
                    nsteps += 1
                elif e["line"] < lo:
                    continue
                m = mem.get(e["line"], [])
                decs = [sid for sid, _, dec in m if dec]
                pres = [(sid, t) for sid, t, dec in m if not dec]
                dshare = C.decode_ms(d, grid) / 1e3 if d >= 1 and decs else 0.0
                pshare = price - dshare
                ptok = sum(t for _, t in pres)
                share = {}
                for sid in decs:
                    share[sid] = share.get(sid, 0.0) + dshare / len(decs)
                for sid, t in pres:
                    share[sid] = share.get(sid, 0.0) + (pshare * t / ptok if ptok else pshare / len(pres))
                if not pres and decs:
                    for sid in decs:
                        share[sid] += pshare / len(decs)
                for sid, s in share.items():
                    t0 = sent_of.get(sid)
                    if t0 is None:
                        continue
                    if inside and t0 < w0:
                        st += s
                    elif not inside and w0 <= t0 < w1:
                        en += s
            w[b] = {"total_s": total, "a_prime_per_turn_s": total / n, "start_resid_s": st,
                    "end_resid_s": en, "corrected_per_turn_s": (total - st + en) / n, "steps": nsteps}
        out["windows"][str(int(L))] = w
    return out


# -- predicted ---------------------------------------------------------------------

def sim_windows(job) -> dict:
    task, n, cname, rep, bound = job
    _, _, plan_dir, _, _ = SETS[task]
    sel = json.loads((HERE / "selection/selection.json").read_text())
    if task == "GTASK11":
        idx = json.loads((plan_dir / "INDEX.json").read_text())
        pid = [e["plan_id"] for e in idx if e["n"] == n and e["rep"] == rep][0]
        cfg = PM.configs(sel, n)[cname]
        cost = None
    else:
        pid = f"gblind-n{n}-r{rep}"
        grids = json.loads((HERE / "selection/blind_grids.json").read_text())["per_n_grid"]
        cfg = PB.cfgs(sel, n, grids)[cname]
        cost = PB.StepCost("ctx", None, seed=PB.SEED0 + 1000 * n + 10 * rep + PB.CONFIGS.index(cname))
    plan = MultiTurnPlan.from_json(json.loads((plan_dir / f"{pid}.json").read_text()))
    res = SIM.simulate(plan, cfg, eviction="lru", bound=bound, step_cost=cost)
    grid = tuple(sorted(cfg.capture_sizes))
    w0 = res["warmup_end_s"]
    out = {}
    for L in WINDOWS:
        w1 = w0 + L
        ws = [s for s in res["steps"] if w0 <= s.start_s < w1]
        nreq = sum(1 for r in res["requests"] if w0 <= r.arrival_s < w1)
        if task == "GTASK11":     # window_metrics device_s
            dev = sum(s.duration_s for s in ws)
        else:                     # predict_blind.run_one price_s
            dev = sum(C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=grid, bound=bound)
                      for s in ws) / 1e3
        out[str(int(L))] = (dev, nreq)
    return out


# -- main ----------------------------------------------------------------------------

def order_of(vals: dict) -> str:
    return " < ".join(sorted(vals, key=vals.get))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    verdicts, obs_jobs, sim_jobs, cfgs_of = {}, {}, [], {}
    for task, (run, ns, _, _, _) in SETS.items():
        v = json.loads((run / "verdict.json").read_text())
        verdicts[task] = v
        for n in ns:
            cfgs_of[(task, n)] = [c for c in CONFIGS if f"n{n}.{c}.r0" in v["used"]]
            for c in cfgs_of[(task, n)]:
                for r in range(5):
                    tag = f"n{n}.{c}.r{r}"
                    if tag in v["used"]:
                        obs_jobs[(task, n, c, r)] = run / v["used"][tag]
                    for b in BOUNDS:
                        sim_jobs.append((task, n, c, r, b))
    with ProcessPoolExecutor(a.workers) as ex:
        of = {k: ex.submit(lifecycle, p) for k, p in obs_jobs.items()}
        sf = {j: ex.submit(sim_windows, j) for j in sim_jobs}
        lc = {k: f.result() for k, f in of.items()}
        sm = {k: f.result() for k, f in sf.items()}
    Ls = [str(int(L)) for L in WINDOWS]
    cells, groups = [], []
    integ = Counter()
    for x in lc.values():
        integ.update(x["integrity"])
    for task, (run, ns, _, pfile, pname) in SETS.items():
        P = json.loads(pfile.read_text())["cells"]
        v = verdicts[task]
        for n in ns:
            cs = cfgs_of[(task, n)]
            for b in BOUNDS:
                pred = {c: {L: sum(sm[(task, n, c, r, b)][L][0] for r in range(5))
                            / sum(sm[(task, n, c, r, b)][L][1] for r in range(5)) for L in Ls} for c in cs}
                g = {"set": task, "N": n, "bound": b, "obs_order": {}, "pred_order": {}}
                rows = []
                for c in cs:
                    xs = [lc[(task, n, c, r)] for r in range(5) if (task, n, c, r) in lc]
                    row = {"set": task, "N": n, "config": c, "bound": b, "replicates": len(xs), "windows": {}}
                    for L in Ls:
                        ws = [x["windows"][L][b] for x in xs]
                        tot = sum(w["total_s"] for w in ws)
                        w = {"requests": sum(x["windows"][L]["requests"] for x in xs),
                             "a_prime_mean_s": statistics.mean(w_["a_prime_per_turn_s"] for w_ in ws),
                             "start_resid_share": sum(w_["start_resid_s"] for w_ in ws) / tot,
                             "end_resid_share": sum(w_["end_resid_s"] for w_ in ws) / tot,
                             "start_resid_share_range": [min(w_["start_resid_s"] / w_["total_s"] for w_ in ws),
                                                         max(w_["start_resid_s"] / w_["total_s"] for w_ in ws)],
                             "end_resid_share_range": [min(w_["end_resid_s"] / w_["total_s"] for w_ in ws),
                                                       max(w_["end_resid_s"] / w_["total_s"] for w_ in ws)],
                             "pred_device_per_turn_s": pred[c][L]}
                        if c != "BASE":
                            o, k = [], []
                            for r in range(5):
                                x, y = lc.get((task, n, c, r)), lc.get((task, n, "BASE", r))
                                if x and y:
                                    o.append(x["windows"][L][b]["a_prime_per_turn_s"]
                                             / y["windows"][L][b]["a_prime_per_turn_s"])
                                    k.append(x["windows"][L][b]["corrected_per_turn_s"]
                                             / y["windows"][L][b]["corrected_per_turn_s"])
                            w.update({"obs_ratio_per_rep": o, "obs_ratio_median": statistics.median(o),
                                      "corrected_ratio_per_rep": k, "corrected_ratio_median": statistics.median(k),
                                      "paired_diff_median": statistics.median(y_ - x_ for x_, y_ in zip(o, k)),
                                      "corrected_minus_original": statistics.median(k) - statistics.median(o),
                                      "pred_ratio": pred[c][L] / pred["BASE"][L]})
                        row["windows"][L] = w
                    if c != "BASE":
                        if task == "GTASK11" and n == 26:
                            vr = v["N26"]["POOL/BASE"][b]["ratios"]
                            pr = P[str(n)][c][f"{pname}/{b}"]["ratio_to_base"]
                        elif task == "GTASK11":
                            vr = v["5.2"][b]["observed"][f"{n}/{c}"]["ratios"]
                            pr = P[str(n)][c][f"{pname}/{b}"]["ratio_to_base"]
                        else:
                            vr = v["5.2"][b]["observed"][f"{n}/{c}"]["ratios"]
                            pr = P[f"{pname}/{b}"][str(n)][c]["ratio_to_base"]
                        row["reproduced_obs_120"] = row["windows"]["120"]["obs_ratio_per_rep"] == vr
                        row["reproduced_pred_120"] = row["windows"]["120"]["pred_ratio"] == pr
                        ob = [row["windows"][L]["obs_ratio_median"] for L in Ls]
                        pd = [row["windows"][L]["pred_ratio"] for L in Ls]
                        row["obs_span"], row["pred_span"] = max(ob) - min(ob), max(pd) - min(pd)
                    rows.append(row)
                for L in Ls:
                    ov = {"BASE": 1.0}
                    pv = {"BASE": 1.0}
                    for row in rows:
                        if row["config"] != "BASE":
                            ov[row["config"]] = row["windows"][L]["obs_ratio_median"]
                            pv[row["config"]] = row["windows"][L]["pred_ratio"]
                    g["obs_order"][L], g["pred_order"][L] = order_of(ov), order_of(pv)
                g["obs_order_changes"] = len(set(g["obs_order"].values())) > 1
                g["pred_order_changes"] = len(set(g["pred_order"].values())) > 1
                cells += rows
                groups.append(g)
                print(task, n, b, g["obs_order"], g["pred_order"], flush=True)
    for row in cells:
        if row["config"] != "BASE":
            print(row["set"], row["N"], row["config"], row["bound"], "repro",
                  row["reproduced_obs_120"], row["reproduced_pred_120"],
                  {L: (round(row["windows"][L]["obs_ratio_median"], 4), round(row["windows"][L]["pred_ratio"], 4))
                   for L in Ls}, "corr-orig@120", round(row["windows"]["120"]["corrected_minus_original"], 4),
                  flush=True)
    print("integrity", dict(integ))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"windows_s": list(WINDOWS), "integrity": dict(integ),
                                    "lifecycles": {"/".join(map(str, k)): v for k, v in lc.items()},
                                    "cells": cells, "groups": groups}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
