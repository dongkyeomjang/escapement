#!/usr/bin/env python3
"""G-10 B verdicts: saturated cost ratio GPU_KV / GPU_BASE, three channels.

Prereg: docs/research/gpu/G10_B_PREREG.md (criteria section 5). Predictions:
plans_b/PREDICTIONS_B.json, committed before the measurement. Runs once.

Per replicate r (both configurations usable): R_ch,r = cost per call of
GPU_KV / that of GPU_BASE for ch in PRED_lo, PRED_hi (simulator, frozen),
RECON_lo, RECON_hi (gpu_cost price of the observed window steps) and
DIRECT_EXEC (sum of [GEXEC] prep + run over the same steps). Medians over
the judged replicate set (both lifecycles valid, no preemption, DIRECT
complete).

usage: judge_b.py --run-dir <abs> --out <abs json>
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
MT = HERE.parent / "multiturn"
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MT))

import gpu_mt_measure as M  # noqa: E402
from main_judge import decode_h, tvd, window_lines  # noqa: E402
from exec_measure import exec_metrics  # noqa: E402
import g10_common as G  # noqa: E402

PRED = HERE / "plans_b" / "PREDICTIONS_B.json"
NS = (28, 25)                 # 28 required, 25 extension
REQUIRED = (28,)
REPS = 10
CFGS = ("GPU_BASE", "GPU_KV")
BOUNDS = ("lo", "hi")
TOL = 0.03
BOOT_SEED = 20264150


def load(d: Path) -> dict:
    m = M.lifecycle_metrics(d)
    x = exec_metrics(d, m)
    pre = m["metric_delta"].get("vllm:num_preemptions_total", 0.0)
    return {"dir": d.name, "valid": m["valid"], "preemptions": pre,
            "reasons": m["invalid_reasons"] + m["checks"]["invalid_reasons_runner"],
            "m": m, "x": x,
            "direct_ok": x["direct_complete"] and x["overlaps"] == 0 and x["nonpositive"] == 0}


def sim_boundary(job):
    n, r, cname, bound = job
    from continuum.workload.multiturn import MultiTurnPlan
    import predict_b as PB
    plan = MultiTurnPlan.from_json(json.loads((PB.PLAN_DIR / f"g10b-n{n}-r{r}.json").read_text()))
    cfg = PB.CFGS[cname]
    res, mem = G.sim_with_members(plan, cfg, bound=bound, step_cost=PB.StepCost("ctx", None, seed=0))
    return (n, r, cname, bound), G.boundary_sim(res, mem, PB.GRID, bound)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    P = json.loads(PRED.read_text())["cells"]
    runs, hist = {}, {}
    for n in NS:
        for c in CFGS:
            for r in range(REPS):
                tag = f"n{n}.{c}.r{r}"
                for d in (a.run_dir / tag, a.run_dir / f"{tag}.retry1"):
                    if not (d / "windows.json").exists():
                        continue
                    try:
                        L = load(d)
                    except Exception as ex:  # broken lifecycle = INVALID
                        hist.setdefault(tag, []).append({"dir": d.name, "valid": False, "reasons": [repr(ex)]})
                        continue
                    hist.setdefault(tag, []).append({k: L[k] for k in ("dir", "valid", "preemptions", "reasons",
                                                                        "direct_ok")}
                                                    | {"missing_window": L["x"]["missing_window"],
                                                       "missing_rate_window": L["x"]["missing_rate_window"]})
                    # first lifecycle with preemption is kept (scope violation, never
                    # replaced); otherwise the first valid one with complete DIRECT, else
                    # the first valid one (a retry exists only after an INVALID primary
                    # or an incomplete DIRECT channel)
                    cur = runs.get(tag)
                    if L["preemptions"] > 0 and cur is None:
                        runs[tag] = L
                    elif L["valid"] and (cur is None or (cur["preemptions"] == 0 and not cur["direct_ok"]
                                                          and L["direct_ok"])):
                        runs[tag] = L
    out: dict = {"validity": hist, "used": {k: v["dir"] for k, v in runs.items()}}
    scope = sorted(k for k, v in runs.items() if v["preemptions"] > 0)
    out["preemption_scope_violation"] = scope
    pres_ns = sorted({int(k.split(".")[0][1:]) for k in scope})

    res: dict = {}
    for n in NS:
        if not any(f"n{n}.GPU_BASE.r{r}" in runs for r in range(REPS)):
            continue
        pr = {b: P[b][str(n)] for b in BOUNDS}
        reps, rows = [], []
        for r in range(REPS):
            kb, kk = runs.get(f"n{n}.GPU_BASE.r{r}"), runs.get(f"n{n}.GPU_KV.r{r}")
            row = {"rep": r, "usable": bool(kb and kk and kb["valid"] and kk["valid"]
                                            and kb["preemptions"] == 0 and kk["preemptions"] == 0)}
            for b in BOUNDS:
                row[f"R_PRED_{b}"] = pr[b]["R_PRED"]["per_rep"][r]
            if row["usable"]:
                for b in BOUNDS:
                    row[f"R_RECON_{b}"] = kk["x"]["recon_per_turn_s"][b] / kb["x"]["recon_per_turn_s"][b]
                row["direct_ok"] = kb["direct_ok"] and kk["direct_ok"]
                if row["direct_ok"]:
                    row["R_DIRECT"] = kk["x"]["direct_per_turn_s"] / kb["x"]["direct_per_turn_s"]
                    row["R_DIRECT_prep"] = kk["x"]["direct_prep_per_turn_s"] / kb["x"]["direct_prep_per_turn_s"]
                    row["R_DIRECT_run"] = kk["x"]["direct_run_per_turn_s"] / kb["x"]["direct_run_per_turn_s"]
                    reps.append(r)
                for c, L in (("GPU_BASE", kb), ("GPU_KV", kk)):
                    row[c] = {"recon_lo_s": L["x"]["recon_per_turn_s"]["lo"], "recon_hi_s": L["x"]["recon_per_turn_s"]["hi"],
                              "direct_s": L["x"]["direct_per_turn_s"], "direct_prep_s": L["x"]["direct_prep_per_turn_s"],
                              "direct_run_s": L["x"]["direct_run_per_turn_s"],
                              "pred_lo_s": pr["lo"][c]["per_rep"][r]["price_per_turn_s"],
                              "pred_hi_s": pr["hi"][c]["per_rep"][r]["price_per_turn_s"],
                              "reuse": L["m"]["reuse"], "hit_tokens": L["m"]["hit_tokens"],
                              "reusable_tokens": L["m"]["reusable_tokens"], "hit_shape": L["m"]["hit_shape"],
                              "eval_requests": L["m"]["eval_requests"], "window_steps": L["x"]["window_steps"],
                              "by_type": L["x"]["by_type"], "missing_window": L["x"]["missing_window"]}
            rows.append(row)
        J = [x for x in rows if x.get("R_DIRECT") is not None]
        cell: dict = {"replicates_judged": reps, "rows": rows,
                      "replicates_usable": [x["rep"] for x in rows if x["usable"]]}
        med = lambda k, xs=J: statistics.median(x[k] for x in xs) if xs else None  # noqa: E731
        md = med("R_DIRECT")
        cell["median"] = {k: med(k) for k in ("R_DIRECT", "R_DIRECT_prep", "R_DIRECT_run",
                                               "R_RECON_lo", "R_RECON_hi", "R_PRED_lo", "R_PRED_hi")}
        U = [x for x in rows if x["usable"]]
        cell["median_all_usable"] = {k: (statistics.median(x[k] for x in U) if U else None)
                                     for k in ("R_RECON_lo", "R_RECON_hi", "R_PRED_lo", "R_PRED_hi")}
        cell["median_pred_all10"] = {b: statistics.median(pr[b]["R_PRED"]["per_rep"]) for b in BOUNDS}
        if md is not None:
            cell["recon_check"] = {b: {"diff": cell["median"][f"R_RECON_{b}"] - md,
                                       "pass": abs(cell["median"][f"R_RECON_{b}"] - md) <= TOL} for b in BOUNDS}
            cell["pred_check"] = {b: {"diff": cell["median"][f"R_PRED_{b}"] - md,
                                      "pass": abs(cell["median"][f"R_PRED_{b}"] - md) <= TOL} for b in BOUNDS}
            rd = [x["R_DIRECT"] for x in J]
            lo, hi = G.boot_ci(rd, BOOT_SEED)
            cell["reduction"] = {"ci95": [lo, hi], "verdict": "CONFIRMED" if hi < 1 else (
                "INCREASE" if lo > 1 else "INCONCLUSIVE"), "sign_test": G.sign_test(rd)}
            cell["per_rep_diff"] = [{"rep": x["rep"], "PRED_lo-DIRECT": x["R_PRED_lo"] - x["R_DIRECT"],
                                     "PRED_hi-DIRECT": x["R_PRED_hi"] - x["R_DIRECT"],
                                     "RECON_lo-DIRECT": x["R_RECON_lo"] - x["R_DIRECT"],
                                     "RECON_hi-DIRECT": x["R_RECON_hi"] - x["R_DIRECT"]} for x in J]
        # absolute per-call times (median over usable replicates)
        cell["absolute_per_call_s"] = {c: {k: (statistics.median(x[c][k] for x in U if x[c][k] is not None)
                                               if any(x[c][k] is not None for x in U) else None)
                                           for k in ("recon_lo_s", "recon_hi_s", "direct_s", "direct_prep_s",
                                                     "direct_run_s", "pred_lo_s", "pred_hi_s")} for c in CFGS}
        # reuse / token reuse / h / queue vs predictions (report)
        rep_ = {}
        for c in CFGS:
            Ls = [runs[f"n{n}.{c}.r{r}"] for r in range(REPS) if f"n{n}.{c}.r{r}" in runs
                  and runs[f"n{n}.{c}.r{r}"]["valid"]]
            if not Ls:
                continue
            hits, tot = sum(L["m"]["reuse"][0] for L in Ls), sum(L["m"]["reuse"][1] for L in Ls)
            ht, rt = sum(L["m"]["hit_tokens"] for L in Ls), sum(L["m"]["reusable_tokens"] for L in Ls)
            h = Counter()
            for L in Ls:
                d = a.run_dir / L["dir"]
                h.update(decode_h(d, window_lines(d)))
            hp = {b: {int(k): v for k, v in pr[b][c]["h_decode"].items()} for b in BOUNDS}
            qd = [G.admission_delay(a.run_dir / L["dir"]) for L in Ls]
            rep_[c] = {"reuse_obs": hits / tot, "reuse_pred": {b: pr[b][c]["reuse_rate"] for b in BOUNDS},
                       "token_reuse_obs": ht / rt, "token_reuse_pred": {b: pr[b][c]["token_reuse_ratio"] for b in BOUNDS},
                       "h_decode_tvd": {b: tvd(h, hp[b]) for b in BOUNDS},
                       "admission_delay_obs_mean_s": statistics.fmean(q["mean_s"] for q in qd),
                       "queue_wait_pred_mean_s": {b: statistics.fmean(x["queue_wait_mean_s"]
                                                                      for x in pr[b][c]["per_rep"]) for b in BOUNDS}}
        cell["reuse_queue_report"] = rep_
        res[str(n)] = cell
    out["cells"] = res

    # verdicts
    ver: dict = {}
    judged = [n for n in NS if str(n) in res and res[str(n)]["median"]["R_DIRECT"] is not None]
    for scope_name, ns in (("required", [n for n in judged if n in REQUIRED]), ("all_B", judged)):
        if not ns:
            ver[scope_name] = "NA (no judged cell)"
            continue
        v = {}
        for b in BOUNDS:
            v[f"recon_{b}"] = all(res[str(n)]["recon_check"][b]["pass"] for n in ns)
            v[f"pred_{b}"] = all(res[str(n)]["pred_check"][b]["pass"] for n in ns)
            e = sum(abs(res[str(n)]["median"][f"R_PRED_{b}"] - res[str(n)]["median"]["R_DIRECT"]) for n in ns)
            e0 = sum(abs(1 - res[str(n)]["median"]["R_DIRECT"]) for n in ns)
            v[f"skill_{b}"] = {"err_sum": e, "baseline_err_sum": e0,
                               "verdict": "NA" if e0 <= 1e-12 else ("PASS" if e <= 0.5 * e0 else "FAIL")}
        v["pred_overall"] = "PASS" if v["pred_lo"] and v["pred_hi"] else "FAIL"
        v["recon_overall"] = "PASS" if v["recon_lo"] and v["recon_hi"] else "FAIL"
        v["cells"] = ns
        ver[scope_name] = v
    for n in NS:
        if n in pres_ns:
            ver[f"N{n}_scope"] = "SCOPE_VIOLATION (preemption observed; confirmation halted for this N)"
    out["verdict"] = ver

    # auxiliary: boundary-corrected ratios (all channels, same rule)
    jobs = [(n, r, c, b) for n in NS if str(n) in res for r in res[str(n)]["replicates_judged"]
            for c in CFGS for b in BOUNDS]
    with ProcessPoolExecutor(a.jobs) as ex:
        simb = dict(ex.map(sim_boundary, jobs))
    aux = {}
    for n in NS:
        if str(n) not in res:
            continue
        rows = []
        for r in res[str(n)]["replicates_judged"]:
            ob = {c: G.boundary_observed(a.run_dir / runs[f"n{n}.{c}.r{r}"]["dir"], with_direct=True) for c in CFGS}
            row = {"rep": r}
            for ch in ("lo", "hi", "direct"):
                row[f"R_{ch}_raw"] = ob["GPU_KV"][ch]["per_call_s"] / ob["GPU_BASE"][ch]["per_call_s"]
                row[f"R_{ch}_corrected"] = (ob["GPU_KV"][ch]["corrected_per_call_s"]
                                            / ob["GPU_BASE"][ch]["corrected_per_call_s"])
            for b in BOUNDS:
                sk, sb = simb[(n, r, "GPU_KV", b)], simb[(n, r, "GPU_BASE", b)]
                row[f"R_PRED_{b}_raw"] = sk["per_call_s"] / sb["per_call_s"]
                row[f"R_PRED_{b}_corrected"] = sk["corrected_per_call_s"] / sb["corrected_per_call_s"]
            row["residuals"] = {c: {ch: {"S_s": ob[c][ch]["S_s"], "E_s": ob[c][ch]["E_s"]} for ch in ("lo", "hi", "direct")}
                                for c in CFGS}
            row["direct_missing_after_window"] = {c: ob[c]["direct_missing_after_window"] for c in CFGS}
            rows.append(row)
        keys = [k for k in rows[0] if k.startswith("R_")] if rows else []
        aux[str(n)] = {"rows": rows, "median": {k: statistics.median(x[k] for x in rows) for k in keys}}
    out["aux_boundary"] = aux
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(ver, indent=1))
    for n in NS:
        if str(n) in res:
            print(n, {k: (round(v, 4) if v is not None else None) for k, v in res[str(n)]["median"].items()},
                  res[str(n)].get("reduction", {}).get("verdict"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
