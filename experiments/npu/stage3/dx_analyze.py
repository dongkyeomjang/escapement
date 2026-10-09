#!/usr/bin/env python3
"""Verdicts of the 2026-10-08 directive (DX_PREREG.md). Run once per work item
after its lifecycles have finished; nothing here is tuned to outcomes.

  dx_analyze.py a  --run <RUN_A>  --output <json>     work A perturbation check
  dx_analyze.py b  --run <RUN_B>  [--run8 <RUN_B8>] --output <json>
  dx_analyze.py c  --run <RUN_C>  [--direct-ok] --output <json>
  dx_analyze.py e  --run <RUN_E>  --channel {DIRECT_EXEC,RECON} --output <json>

Statistics are replicate-level (never per request): paired ratios per
replicate, their median, nominal 95 % percentile bootstrap of the median
(10,000 resamples, seed 20268007), exact two-sided sign test.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dx_steps as X  # noqa: E402
import mt_measure as M  # noqa: E402

PLAN_DIR = HERE / "plans" / "dx"
BOOT, BOOT_SEED = 10_000, 20268007
TOL_COST = 0.03          # absolute difference of cost ratios (not 3 %)
TOL_REUSE = 0.05         # absolute reuse-rate error per cell (work C)
SKILL = 0.5
REUSE_NULL = 0.6763527054108216   # NULL_PREDICTORS_CTX.json reuse_null (TASK101), fixed
PERTURB_TOL = 0.01
_MODEL_DEC = re.compile(r"DECODE METRICS:")


# -- statistics --------------------------------------------------------------------

def boot_median(xs: list[float]) -> tuple[float, float, float]:
    med = statistics.median(xs)
    rng = random.Random(BOOT_SEED)
    b = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(BOOT))
    return med, b[int(0.025 * BOOT)], b[int(0.975 * BOOT) - 1]


def sign_test(xs: list[float], ref: float = 1.0) -> dict:
    below = sum(1 for x in xs if x < ref)
    above = sum(1 for x in xs if x > ref)
    n = below + above
    k = min(below, above)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else None
    return {"below": below, "above": above, "ties": len(xs) - n, "n": n, "p_two_sided": p}


def chosen(run: Path, tag: str) -> tuple[str | None, list[str]]:
    tried = []
    for t in (tag, tag + ".retry1"):
        p = run / f"check.{t}.json"
        if p.exists():
            rec = json.loads(p.read_text())
            tried.append(f"{t}:{'VALID' if rec['valid'] else 'INVALID'}")
            if rec["valid"]:
                return t, tried
    return None, tried


def preds() -> dict:
    return json.loads((PLAN_DIR / "PREDICTIONS_DX.json").read_text())


# -- client / server signals present with OBS on and off (work A) ------------------

def run_metrics(log: Path) -> dict:
    """Run-end VLLM_RBLN_METRICS MODEL tracker (on in every run since TASK12)."""
    out, sect = {}, None
    txt = log.read_text(errors="replace").splitlines()
    tracker = None
    for line in txt:
        if "FINAL PERFORMANCE STATISTICS [" in line:
            tracker = line.split("[")[-1].split("]")[0]
        for s in ("PREFILL", "DECODE", "PADDED DECODE"):
            if f"] {s} METRICS:" in line or line.rstrip().endswith(f" {s} METRICS:"):
                sect = s
        m = re.search(r"Total call counts: (\d+)", line)
        if m and sect and tracker:
            out.setdefault(f"{tracker}.{sect}", {})["calls"] = int(m.group(1))
        m = re.search(r"Latency \(ms\): mean ([\d.]+) \| p50 ([\d.]+)", line)
        if m and sect and tracker:
            out.setdefault(f"{tracker}.{sect}", {}).update(mean_ms=float(m.group(1)), p50_ms=float(m.group(2)))
    return out


def client_metrics(run: Path, tag: str) -> dict:
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    ev = [r for r in rows if w0 <= r["sent_s"] < w1]
    itl = []
    p = probe / f"tokens.{tag}.jsonl.gz"
    ids = {r["request_id"] for r in ev}
    if p.exists():
        with gzip.open(p, "rt") as fh:
            for l in fh:
                d = json.loads(l)
                if d["request_id"] in ids and len(d["t"]) > 1:
                    itl.extend(b - a for a, b in zip(d["t"], d["t"][1:]))
    lat = [r["done_s"] - r["sent_s"] for r in ev]
    done_in = sum(1 for r in rows if w0 <= r["done_s"] < w1)
    return {"eval_requests": len(ev), "completed_in_window_per_s": done_in / (w1 - w0),
            "latency_median_s": statistics.median(lat), "latency_mean_s": statistics.mean(lat),
            "itl_median_ms": statistics.median(itl) * 1e3 if itl else None,
            "itl_mean_ms": statistics.mean(itl) * 1e3 if itl else None}


def work_a(run: Path) -> dict:
    order = json.loads((PLAN_DIR / "ORDER_DXA.json").read_text())["order"]
    conds = sorted({(e["config"], int(e["tag"].split(".")[2][1:])) for e in order})
    out = {"conditions": {}, "criterion": "paired median relative change (on/off - 1) of throughput "
           "(completed-in-window per s) or of common-scope execution time (run-end MODEL DECODE mean "
           "latency) > 0.01 -> perturbation"}
    flag = False
    for cfg, n in conds:
        pairs = []
        for r in range(5):
            row = {"rep": r}
            for arm in ("on", "off"):
                tag, tried = chosen(run, f"A.{cfg}.n{n}.r{r}.{arm}")
                row[f"{arm}_tag"] = tag
                if tag is None:
                    row["missing"] = tried
                    continue
                _, grid, batch = X.CONFIGS[cfg]
                m = M.lifecycle_metrics(run, tag, grid, batch)
                c = client_metrics(run, tag)
                s = run_metrics(run / f"server-{tag}.log")
                row[arm] = {"client": c, "server_run_metrics": s,
                            "recon_a_prime_per_turn_s": m["a_prime_per_turn_s"],
                            "decode_steps_in_window": sum(m["h_counts"].values()),
                            "h_counts": m["h_counts"], "reuse": m["reuse"]}
            pairs.append(row)
        full = [p for p in pairs if "on" in p and "off" in p]

        def rel(get):
            xs = []
            for p in full:
                a, b = get(p["on"]), get(p["off"])
                if a is not None and b is not None and b:
                    xs.append(a / b - 1)
            return {"per_pair": xs, "median": statistics.median(xs) if xs else None,
                    "min": min(xs) if xs else None, "max": max(xs) if xs else None,
                    "sd": statistics.stdev(xs) if len(xs) > 1 else None}

        sig = {
            "throughput": rel(lambda x: x["client"]["completed_in_window_per_s"]),
            "decode_exec_mean": rel(lambda x: x["server_run_metrics"].get("MODEL.DECODE", {}).get("mean_ms")),
            "decode_exec_p50": rel(lambda x: x["server_run_metrics"].get("MODEL.DECODE", {}).get("p50_ms")),
            "prefill_exec_mean": rel(lambda x: x["server_run_metrics"].get("MODEL.PREFILL", {}).get("mean_ms")),
            "sampler_decode_mean": rel(lambda x: x["server_run_metrics"].get("SAMPLER.DECODE", {}).get("mean_ms")),
            "client_itl_median": rel(lambda x: x["client"]["itl_median_ms"]),
            "client_latency_median": rel(lambda x: x["client"]["latency_median_s"]),
            "recon_a_prime": rel(lambda x: x["recon_a_prime_per_turn_s"]),
            "decode_steps_in_window": rel(lambda x: x["decode_steps_in_window"]),
        }
        main_vals = [sig["throughput"]["median"], sig["decode_exec_mean"]["median"]]
        over = any(v is not None and abs(v) > PERTURB_TOL for v in main_vals)
        flag |= over
        out["conditions"][f"{cfg}.n{n}"] = {"pairs_complete": len(full), "signals": sig,
                                            "exceeds_1pct": over, "pairs": pairs}
    out["verdict"] = "PERTURBATION" if flag else "WITHIN_1PCT"
    return out


# -- work B --------------------------------------------------------------------------

def per_lifecycle(run: Path, prefix: str, cfgs, n: int, reps) -> tuple[dict, dict]:
    lc, sel = {}, {}
    for cfg in cfgs:
        for r in reps:
            tag, tried = chosen(run, f"{prefix}.{cfg}.n{n}.r{r}")
            sel[f"{cfg}.r{r}"] = {"used": tag, "tried": tried}
            if tag:
                lc[(cfg, r)] = X.lifecycle(run, tag, cfg)
    return lc, sel


def channel_rows(lc: dict, ref: str, cfg: str, reps) -> dict:
    def val(x, ch):
        if ch == "RECON":
            return x["recon_per_turn_s"]
        if ch == "DIRECT_EXEC":
            return x["direct"]["per_turn_s"]
        if ch == "RECON_BC":
            return x["boundary"]["recon"]["corrected_per_turn_s"]
        if ch == "DIRECT_EXEC_BC":
            return x["boundary"]["direct"]["corrected_per_turn_s"]
        if ch == "DIRECT_MODEL_SAMPLER":
            return x["direct"]["model_plus_sampler_per_turn_s"]
        raise KeyError(ch)
    out = {}
    for ch in ("RECON", "DIRECT_EXEC", "RECON_BC", "DIRECT_EXEC_BC", "DIRECT_MODEL_SAMPLER"):
        out[ch] = {r: val(lc[(cfg, r)], ch) / val(lc[(ref, r)], ch) for r in reps
                   if (cfg, r) in lc and (ref, r) in lc}
    return out


def work_b_cell(run: Path, n: int, pred: dict) -> dict:
    reps = range(10)
    lc, sel = per_lifecycle(run, "B", ("BASE", "TUNED"), n, reps)
    rows = channel_rows(lc, "BASE", "TUNED", reps)
    pc = pred["cells"][f"B.n{n}"]["configs"]
    rows["PRED"] = dict(enumerate(pc["TUNED"]["per_rep_ratio_to_ref"]))
    common = sorted(set.intersection(*(set(v) for v in rows.values())))
    R = {ch: [rows[ch][r] for r in common] for ch in rows}
    med = {ch: statistics.median(v) for ch, v in R.items()}
    d_rd = [a - b for a, b in zip(R["RECON"], R["DIRECT_EXEC"])]
    d_pd = [a - b for a, b in zip(R["PRED"], R["DIRECT_EXEC"])]
    m, lo, hi = boot_median(R["DIRECT_EXEC"])
    cell = {
        "replicates": common, "selection": sel,
        "per_rep": {ch: dict(zip(common, v)) for ch, v in R.items()}, "median": med,
        "boot_ci": {ch: list(boot_median(v)[1:]) for ch, v in R.items()},
        "diff_recon_minus_direct": {"per_rep": d_rd, "median_ci": list(boot_median(d_rd))},
        "diff_pred_minus_direct": {"per_rep": d_pd, "median_ci": list(boot_median(d_pd))},
        "crit1_recon_vs_direct": {"abs_diff": abs(med["RECON"] - med["DIRECT_EXEC"]),
                                  "verdict": "PASS" if abs(med["RECON"] - med["DIRECT_EXEC"]) <= TOL_COST else "FAIL"},
        "crit2_pred_vs_direct": {"abs_diff": abs(med["PRED"] - med["DIRECT_EXEC"]),
                                 "verdict": "PASS" if abs(med["PRED"] - med["DIRECT_EXEC"]) <= TOL_COST else "FAIL"},
        "crit4_saving": {"median": m, "ci": [lo, hi], "sign_test": sign_test(R["DIRECT_EXEC"]),
                         "verdict": "개선 확인" if hi < 1.0 else "INCONCLUSIVE"},
        "boundary_corrected_direct_ci": list(boot_median(R["DIRECT_EXEC_BC"])),
    }
    # absolute per-turn times (reported, never refitted)
    absr = {}
    for cfg in ("BASE", "TUNED"):
        pr = pc[cfg]["per_rep_device_per_turn_s"]
        absr[cfg] = {"PRED_median_s": statistics.median(pr[r] for r in common),
                     "RECON_median_s": statistics.median(lc[(cfg, r)]["recon_per_turn_s"] for r in common),
                     "DIRECT_EXEC_median_s": statistics.median(lc[(cfg, r)]["direct"]["per_turn_s"] for r in common),
                     "DIRECT_decode_components_s": {k: statistics.median(lc[(cfg, r)]["direct"]["decode_components_s"][k]
                                                                         / lc[(cfg, r)]["eval_requests"] for r in common)
                                                    for k in ("total", "model", "sampler", "pre", "post")},
                     "DIRECT_prefill_per_turn_s": statistics.median(lc[(cfg, r)]["direct"]["prefill_s"]
                                                                   / lc[(cfg, r)]["eval_requests"] for r in common),
                     "RECON_prefill_per_turn_s": statistics.median(lc[(cfg, r)]["recon"]["prefill_per_turn_s"] for r in common),
                     "RECON_decode_per_turn_s": statistics.median(lc[(cfg, r)]["recon"]["decode_per_turn_s"] for r in common),
                     "missing_share_max": max(lc[(cfg, r)]["attribution"]["missing_share"] for r in common),
                     "inter_step_median_s": statistics.median(lc[(cfg, r)]["inter_step_s"]["median"] for r in common)}
    cell["absolute"] = absr
    cell["lifecycles"] = {f"{c}.r{r}": {k: v for k, v in x.items() if k != "prefill_tokens_recon_direct"}
                          for (c, r), x in lc.items()}
    return cell


def work_b_off(run: Path, n: int) -> dict:
    """DX_PREREG §12 'off' branch: B measured with OBS off. DIRECT_EXEC does not
    exist, so criteria 1-4 are not judged; PRED vs RECON is reported only."""
    pred = preds()
    reps = range(10)
    lc, sel = {}, {}
    for cfg in ("BASE", "TUNED"):
        for r in reps:
            tag, tried = chosen(run, f"B.{cfg}.n{n}.r{r}")
            sel[f"{cfg}.r{r}"] = {"used": tag, "tried": tried}
            if tag:
                lc[(cfg, r)] = X.lifecycle(run, tag, cfg, obs=False)
    common = [r for r in reps if ("BASE", r) in lc and ("TUNED", r) in lc]
    pc = pred["cells"][f"B.n{n}"]["configs"]
    rec = [lc[("TUNED", r)]["recon_per_turn_s"] / lc[("BASE", r)]["recon_per_turn_s"] for r in common]
    prd = [pc["TUNED"]["per_rep_ratio_to_ref"][r] for r in common]
    d = [a - b for a, b in zip(prd, rec)]
    reuse = {}
    for cfg in ("BASE", "TUNED"):
        h = sum(lc[(cfg, r)]["recon"]["reuse"][0] for r in common)
        t = sum(lc[(cfg, r)]["recon"]["reuse"][1] for r in common)
        reuse[cfg] = {"obs": h / t, "pred": pc[cfg]["reuse_pooled"], "obs_counts": [h, t]}
    m, lo, hi = boot_median(rec)
    return {"status": "B direct BLOCKED: instrumentation perturbation (DX_PREREG §12); report only",
            "replicates": common, "selection": sel,
            "R_RECON": {"per_rep": dict(zip(common, rec)), "median": m, "ci": [lo, hi], "sign_test": sign_test(rec)},
            "R_PRED": {"per_rep": dict(zip(common, prd)), "median": statistics.median(prd)},
            "pred_minus_recon": {"per_rep": d, "median_ci": list(boot_median(d)),
                                 "abs_diff_of_medians": abs(statistics.median(prd) - m)},
            "reuse": reuse,
            "absolute_median_s": {cfg: {"PRED": statistics.median(pc[cfg]["per_rep_device_per_turn_s"][r] for r in common),
                                        "RECON": statistics.median(lc[(cfg, r)]["recon_per_turn_s"] for r in common)}
                                  for cfg in ("BASE", "TUNED")},
            "lifecycles": {f"{c}.r{r}": x for (c, r), x in lc.items()}}


def work_b(run: Path, run8: Path | None) -> dict:
    pred = preds()
    out = {"cells": {"n18": work_b_cell(run, 18, pred)}}
    if run8 is not None:
        out["cells"]["n8"] = work_b_cell(run8, 8, pred)
    cells = list(out["cells"].values())
    sp = sum(abs(c["median"]["PRED"] - c["median"]["DIRECT_EXEC"]) for c in cells)
    s0 = sum(abs(1.0 - c["median"]["DIRECT_EXEC"]) for c in cells)
    out["crit3_skill"] = {"sum_abs_err_pred": sp, "sum_abs_err_null1": s0,
                          "verdict": "NA" if s0 <= 1e-12 else ("PASS" if sp <= SKILL * s0 else "FAIL"),
                          "ratio": sp / s0 if s0 > 1e-12 else None}
    return out


# -- work C --------------------------------------------------------------------------

def gap_stats() -> dict:
    """Planned tool waits of the C plans: g_raw (uncapped draw of the same random
    stream, regenerated with cap = inf) and min(g_raw, cap) for cap 60 / 120."""
    import make_plan as MP
    idx = json.loads((PLAN_DIR / "INDEX_DX.json").read_text())
    seen, raw = set(), []
    for e in idx:
        if e["role"] != "C" or e["internal_plan_id"] in seen:
            continue
        seen.add(e["internal_plan_id"])
        plan = MP.build(n=e["n"], seed=e["seed"], plan_id=e["internal_plan_id"], cycle_s=e["cycle_s"],
                        gap=f"toolmix:{MP.GAP_FILE}:inf")
        for s in plan.slots:
            for x in s.sessions:
                raw.extend(t.gap_after_s for t in x.turns[:-1])
    res = {}

    def summ(xs):
        ys = sorted(xs)

        def q(p):
            return ys[min(len(ys) - 1, int(p * len(ys)))]
        return {"n": len(ys), "mean": statistics.mean(ys), "p50": q(0.5), "p90": q(0.9), "p99": q(0.99),
                "max": ys[-1], "sum": sum(ys)}
    res["raw"] = summ(raw)
    for cap in (60, 120):
        c = [min(g, cap) for g in raw]
        res[str(cap)] = summ(c) | {"clipped_share_of_gaps": sum(1 for g in raw if g > cap) / len(raw),
                                   "clipped_sum_s": sum(raw) - sum(c),
                                   "clipped_share_of_raw_sum": (sum(raw) - sum(c)) / sum(raw)}
    # the committed plan files must hold exactly min(g_raw, cap)
    for cap in (60, 120):
        got = []
        for e in idx:
            if e["role"] == "C" and e["cap_s"] == cap:
                d = json.loads((PLAN_DIR / f"{e['plan_id']}.json").read_text())
                for s in d["slots"]:
                    for x in s["sessions"]:
                        got.extend(t["gap_after_s"] for t in x["turns"][:-1])
        res[str(cap)]["plan_files_match"] = got == [min(g, cap) for g in raw]
    return res


def work_c(run: Path, direct_ok: bool) -> dict:
    pred = preds()
    reps = range(5)
    lc, sel = {}, {}
    for cfg in ("BASE", "TUNED"):
        for cap in (60, 120):
            for r in reps:
                tag, tried = chosen(run, f"C.{cfg}.n14.cap{cap}.r{r}")
                sel[f"{cfg}.cap{cap}.r{r}"] = {"used": tag, "tried": tried}
                if tag:
                    lc[(cfg, cap, r)] = X.lifecycle(run, tag, cfg, obs=direct_ok)
    cells, reuse_err = {}, {}
    for cfg in ("BASE", "TUNED"):
        for cap in (60, 120):
            used = [lc[(cfg, cap, r)] for r in reps if (cfg, cap, r) in lc]
            hits = sum(x["recon"]["reuse"][0] for x in used)
            tot = sum(x["recon"]["reuse"][1] for x in used)
            p = pred["cells"][f"C.n14.cap{cap}"]["configs"][cfg]
            h = Counter()
            for x in used:
                for k, v in x["recon"]["h_counts"].items():
                    h[int(k)] += v
            hobs = {k: v / sum(h.values()) for k, v in sorted(h.items())}
            e = p["reuse_pooled"] - hits / tot
            reuse_err[f"{cfg}.cap{cap}"] = e
            cells[f"{cfg}.cap{cap}"] = {
                "replicates": len(used), "reuse_obs": hits / tot, "reuse": [hits, tot],
                "reuse_pred": p["reuse_pooled"], "reuse_err": e,
                "h_obs": hobs, "h_tvd_pred": M.tvd(hobs, {int(k): v for k, v in p["h"].items()}),
                "throughput_per_s": statistics.mean(x["recon"]["throughput_per_s"] for x in used),
                "completed_per_hour": 3600 * statistics.mean(x["recon"]["throughput_per_s"] for x in used),
                "mean_running_obs": sum(k * v for k, v in h.items()) / sum(h.values()),
                "pred_mean_wait_s": p["mean_wait_s"],
                "ttft_turn_ge1_median_s": statistics.median(x["recon"]["ttft_turn_ge1_median_s"] for x in used),
                "recon_per_turn_median_s": statistics.median(x["recon_per_turn_s"] for x in used),
                "boundary_resid": {"S_over_total_median": statistics.median(
                    x["boundary"]["recon"]["S_s"] / (x["recon_per_turn_s"] * x["eval_requests"]) for x in used)
                    if direct_ok else None}}
    errs = list(reuse_err.values())
    obs = [cells[k]["reuse_obs"] for k in reuse_err]
    s0 = sum(abs(REUSE_NULL - o) for o in obs)
    out = {"gap_stats": gap_stats(), "selection": sel, "cells": cells,
           "reuse_main": {"errors": reuse_err, "MAE": statistics.mean(abs(x) for x in errs),
                          "max_abs": max(abs(x) for x in errs),
                          "BASE_errors": {k: v for k, v in reuse_err.items() if k.startswith("BASE")},
                          "TUNED_errors": {k: v for k, v in reuse_err.items() if k.startswith("TUNED")},
                          "verdict": "PASS" if all(abs(x) <= TOL_REUSE for x in errs) else "FAIL"},
           "reuse_skill": {"null_value": REUSE_NULL, "sum_abs_err": sum(abs(x) for x in errs),
                           "sum_abs_null": s0,
                           "verdict": "PASS" if sum(abs(x) for x in errs) <= SKILL * s0 else "FAIL"}}
    cost = {}
    for cap in (60, 120):
        rec, dirr = [], []
        pr = pred["cells"][f"C.n14.cap{cap}"]["configs"]["TUNED"]["per_rep_ratio_to_ref"]
        for r in reps:
            if (("TUNED", cap, r) in lc) and (("BASE", cap, r) in lc):
                t, b = lc[("TUNED", cap, r)], lc[("BASE", cap, r)]
                rec.append(t["recon_per_turn_s"] / b["recon_per_turn_s"])
                if direct_ok:
                    dirr.append(t["direct"]["per_turn_s"] / b["direct"]["per_turn_s"])
        mp = statistics.median(pr)
        mr = statistics.median(rec)
        row = {"pred_median": mp, "recon_per_rep": rec, "recon_median_ci": list(boot_median(rec)),
               "abs_err_vs_recon": abs(mp - mr),
               "verdict_common_cost_model": "PASS" if abs(mp - mr) <= TOL_COST else "FAIL",
               "label": "공통 비용 모형 아래 검증 (RECON 참조)"}
        if direct_ok:
            md = statistics.median(dirr)
            row.update(direct_per_rep=dirr, direct_median_ci=list(boot_median(dirr)), abs_err_vs_direct=abs(mp - md))
        cost[str(cap)] = row
    out["cost_ratio"] = cost
    # sensitivity (observed, paired by replicate): cap120 - cap60
    sens = {}
    for cfg in ("BASE", "TUNED"):
        d_cost = [lc[(cfg, 120, r)]["recon_per_turn_s"] / lc[(cfg, 60, r)]["recon_per_turn_s"]
                  for r in reps if (cfg, 120, r) in lc and (cfg, 60, r) in lc]
        sens[cfg] = {"recon_cost_ratio_cap120_over_cap60": {"per_rep": d_cost, "median_ci": list(boot_median(d_cost))},
                     "reuse_obs_diff": cells[f"{cfg}.cap120"]["reuse_obs"] - cells[f"{cfg}.cap60"]["reuse_obs"],
                     "reuse_pred_diff": cells[f"{cfg}.cap120"]["reuse_pred"] - cells[f"{cfg}.cap60"]["reuse_pred"]}
    out["sensitivity"] = sens
    out["lifecycles"] = {f"{c}.cap{cap}.r{r}": {k: v for k, v in x.items() if k != "prefill_tokens_recon_direct"}
                         for (c, cap, r), x in lc.items()}
    return out


# -- work E --------------------------------------------------------------------------

def work_e(run: Path, channel: str) -> dict:
    pred = preds()
    sel_cfg = json.loads((PLAN_DIR / "SELECTION_DXE.json").read_text())["selected"]
    reps = range(10)
    lc, sel = {}, {}
    for cfg in ("BATCHONLY", "TUNED", "DP_N8"):
        for r in reps:
            tag, tried = chosen(run, f"E.{cfg}.n19.r{r}")
            sel[f"{cfg}.r{r}"] = {"used": tag, "tried": tried}
            if tag:
                lc[(cfg, r)] = X.lifecycle(run, tag, cfg, obs=channel == "DIRECT_EXEC")
    common = [r for r in reps if all((c, r) in lc for c in ("BATCHONLY", "TUNED", "DP_N8"))]
    chans = ("DIRECT_EXEC", "RECON") if channel == "DIRECT_EXEC" else ("RECON",)

    def cost(x, ch):
        return x["direct"]["per_turn_s"] if ch == "DIRECT_EXEC" else x["recon_per_turn_s"]

    res = {}
    for ch in chans:
        rows = {c: [cost(lc[(c, r)], ch) / cost(lc[("BATCHONLY", r)], ch) for r in common]
                for c in ("BATCHONLY", "TUNED", "DP_N8")}
        Rc = {c: statistics.median(v) for c, v in rows.items()}
        best = min(Rc, key=Rc.get)
        loss = Rc[sel_cfg] / Rc[best] - 1
        rng = random.Random(BOOT_SEED)
        bl = []
        for _ in range(BOOT):
            idx = [rng.randrange(len(common)) for _ in common]
            rb = {c: statistics.median(rows[c][i] for i in idx) for c in rows}
            bl.append(rb[sel_cfg] / min(rb.values()) - 1)
        bl.sort()
        within = max(Rc.values()) / min(Rc.values()) - 1 <= 0.01
        adv = None
        if sel_cfg != "BATCHONLY":
            m, lo, hi = boot_median(rows[sel_cfg])
            adv = {"median": m, "ci": [lo, hi], "sign_test": sign_test(rows[sel_cfg]),
                   "verdict": "이점 확인" if hi < 1.0 else "동률 또는 INCONCLUSIVE"}
        res[ch] = {"R": Rc, "per_rep": rows, "observed_lowest": best, "loss": loss,
                   "loss_ci": [bl[int(0.025 * BOOT)], bl[int(0.975 * BOOT) - 1]],
                   "verdict": "PASS" if loss <= 0.01 else "FAIL",
                   "low_discriminability": within, "advantage_vs_BATCHONLY": adv}
    return {"selected": sel_cfg, "primary_channel": channel, "replicates": common, "selection": sel,
            "primary": res[channel], "secondary": res.get("RECON") if channel == "DIRECT_EXEC" else None,
            "pred": {c: pred["cells"]["E.n19"]["configs"][c]["ratio_median"] for c in ("BATCHONLY", "TUNED", "DP_N8")}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work", choices=("a", "b", "b_off", "c", "e"))
    ap.add_argument("--n", type=int, default=18)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--run8", type=Path)
    ap.add_argument("--direct-ok", action="store_true")
    ap.add_argument("--channel", choices=("DIRECT_EXEC", "RECON"), default="DIRECT_EXEC")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.work == "a":
        out = work_a(a.run)
    elif a.work == "b":
        out = work_b(a.run, a.run8)
    elif a.work == "b_off":
        out = work_b_off(a.run, a.n)
    elif a.work == "c":
        out = work_c(a.run, a.direct_ok)
    else:
        out = work_e(a.run, a.channel)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
