#!/usr/bin/env python3
"""Verdicts of the multi-turn main experiment (MULTITURN_MAIN_PREREG.md §5,
revision 2). Run once, after every lifecycle has finished (directive 05 §2.4).

Population rules (revision 2):

* A lifecycle is used when its check record (``check.<tag>.json``) is VALID;
  otherwise its ``.retry1`` if VALID; otherwise the replicate is missing and
  every cell / pair that needs it is computed on the remaining replicates,
  with the count reported.
* §5.1, §5.2, §5.3, §5.5, §5.6 and the N = 12 exploration use replicates
  r0..r4 only (the plans the preregistered predictions were computed on).
  The extra N = 8 plans r5..r9 enter §5.4 only (DP vs TUNED, r0..r9).
* Every bootstrap: percentile, 10,000 resamples of replicates with
  replacement, a fresh ``random.Random(20261420)`` per cell or pair.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
import math
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_measure as M  # noqa: E402
from mt_check import CONFIGS  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
PREDS = ("analytic", "sim_default", "sim_observed")
CONFIRM_N = (6, 8, 10)
ALL_N = (6, 8, 10, 12)
BOOT = 10_000
BOOT_SEED = 20261420
MAIN_REPS = range(5)
EXT_REPS = range(10)

# preregistered thresholds (§5, revision 2)
REUSE_TOL, REUSE_BIAS, REUSE_SHARE = 0.10, 0.05, 0.90
REUSE_RANGE_MIN = 0.10
RATIO_TOL, RATIO_WIDEN = 0.03, 0.01
RATIO_STRONG_NEEDED = {6: 5, 7: 6}
RATIO_EFFECT_MIN = 0.01
SKILL_FACTOR = 0.5
HSIM_MEDIAN = 0.0130
H_MEDIAN, H_MAX = 0.10, 0.20


def configs_of(n: int) -> tuple[str, ...]:
    return ("BASE", "BATCHONLY", "TUNED", "DP") if n == 8 else ("BASE", "BATCHONLY", "TUNED")


# -- lifecycle selection ------------------------------------------------------------

def chosen_tag(run: Path, cfg: str, n: int, r: int) -> tuple[str | None, list[str]]:
    base = f"{cfg}.n{n}.r{r}"
    tried = []
    for tag in (base, base + ".retry1"):
        p = run / f"check.{tag}.json"
        if p.exists():
            rec = json.loads(p.read_text())
            tried.append(f"{tag}:{'VALID' if rec['valid'] else 'INVALID'}")
            if rec["valid"]:
                return tag, tried
    return None, tried


# -- per-lifecycle measurement ------------------------------------------------------

def per_request(run: Path, tag: str, grid, batch, w0: float, w1: float) -> list[dict]:
    """Evaluation-window requests with prefill time P and the running decoders
    K at their allocation (last [BUCKET] request_nums before the ALLOC line)."""
    rows = [json.loads(l) for l in (run / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines()
            if l.strip()]
    ev = M.parse_server(run / f"server-{tag}.log")
    pm = M.descriptor_for(M.D, tuple(grid), batch).prefill_cost_model
    k_at, lookup = {}, {}
    last_n = 0
    for e in ev:
        if e[0] == "bucket":
            last_n = e[1]
        elif e[0] == "alloc":
            k_at.setdefault(e[1], last_n)
        else:
            lookup[e[1]] = e[2]
    sid_of = {}
    for sid in k_at:
        sid_of.setdefault(sid.rsplit("-", 2)[0], sid)
    out = []
    for r in rows:
        if not (w0 <= r["sent_s"] < w1):
            continue
        sid = sid_of[r["request_id"]]
        cached = r["cached_tokens"] if r["cached_tokens"] is not None else lookup.get(sid, 0)
        out.append({"request_id": r["request_id"], "sent_s": r["sent_s"], "turn": r["turn"],
                    "reused": cached > 0,
                    "P": pm.prefill_s(max(r["prompt_tokens"] - cached, 0)), "K": k_at[sid]})
    return out


def w_measured(run: Path, tag: str, ids: set[str], n_req: int) -> float | None:
    chunks = M.chunk_times(run, tag)
    if not chunks:
        return None
    total = 0.0
    for rid in ids:
        t = chunks.get(rid, [])
        iv = [b - a for a, b in zip(t, t[1:])]
        if len(iv) < 2:
            continue
        med = statistics.median(iv)
        total += sum(x - med for x in iv if x > 3 * med)
    return total / n_req


def halves(run: Path, tag: str, w0: float, w1: float) -> dict:
    """Stationarity: first vs second half of the evaluation window."""
    rows = [json.loads(l) for l in (run / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines()
            if l.strip()]
    ev = M.parse_server(run / f"server-{tag}.log")
    mid = (w0 + w1) / 2
    alloc_pos = {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            alloc_pos.setdefault(e[1], i)
    sid_of = {}
    for sid in alloc_pos:
        sid_of.setdefault(sid.rsplit("-", 2)[0], sid)
    win = [r for r in rows if w0 <= r["sent_s"] < w1]
    pos = {r["request_id"]: alloc_pos[sid_of[r["request_id"]]] for r in win}
    first = [r for r in win if r["sent_s"] < mid]
    second = [r for r in win if r["sent_s"] >= mid]
    lo = min(pos.values())
    cut = min((pos[r["request_id"]] for r in second), default=None)
    hi = max(pos.values())
    h1, h2 = Counter(), Counter()
    for i in range(lo, hi + 1):
        e = ev[i]
        if e[0] == "bucket":
            (h1 if cut is None or i < cut else h2)[e[1]] += 1
    return {"first_requests": len(first), "second_requests": len(second),
            "h_tvd": M.tvd(h1, h2) if h1 and h2 else None,
            "h1_steps": sum(h1.values()), "h2_steps": sum(h2.values())}


def lifecycle(run: Path, tag: str, cfg: str) -> dict:
    _, grid, batch = CONFIGS[cfg]
    m = M.lifecycle_metrics(run, tag, grid, batch)
    w0 = m["warmup_end_s"]
    w1 = w0 + 120.0
    reqs = per_request(run, tag, grid, batch, w0, w1)
    assert len(reqs) == m["eval_requests"]
    m["W_measured_per_turn_s"] = w_measured(run, tag, {q["request_id"] for q in reqs}, len(reqs))
    ps = [q["P"] for q in reqs]
    ks = [q["K"] for q in reqs]
    m["B4"] = {"E_P": statistics.mean(ps), "E_K": statistics.mean(ks),
               "E_PK": statistics.mean(p * k for p, k in zip(ps, ks)),
               "cov_PK": statistics.mean(p * k for p, k in zip(ps, ks)) - statistics.mean(ps) * statistics.mean(ks)}
    mid = w0 + 60.0
    later = [q for q in reqs if q["turn"] > 0]
    r1 = [q for q in later if q["sent_s"] < mid]
    r2 = [q for q in later if q["sent_s"] >= mid]
    m["stationarity"] = halves(run, tag, w0, w1)
    m["stationarity"]["reuse_first"] = sum(q["reused"] for q in r1) / len(r1) if r1 else None
    m["stationarity"]["reuse_second"] = sum(q["reused"] for q in r2) / len(r2) if r2 else None
    return m


# -- statistics ---------------------------------------------------------------------

def boot_median_ci(xs: list[float]) -> tuple[float, float, float]:
    med = statistics.median(xs)
    rng = random.Random(BOOT_SEED)
    boots = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(BOOT))
    return med, boots[int(0.025 * BOOT)], boots[int(0.975 * BOOT) - 1]


def binom_two_sided(k: int, n: int) -> float:
    pmf = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, 2 * min(sum(pmf[:k + 1]), sum(pmf[k:])))


def h_of(pred_h: dict) -> dict[int, float]:
    return {int(k): v for k, v in pred_h.items()}


def spearman(xs, ys) -> float | None:
    if len(xs) < 3:
        return None
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                r[order[t]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


# -- main -----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    run = a.run
    pred = json.loads((PLAN_DIR / "PREDICTIONS.json").read_text())["cells"]
    pext = json.loads((PLAN_DIR / "PREDICTIONS_EXT.json").read_text())["populations"]
    null = json.loads((PLAN_DIR / "NULL_PREDICTORS.json").read_text())

    # ---- collect lifecycles
    lc: dict[tuple, dict] = {}
    selection = {}
    for n in ALL_N:
        for cfg in configs_of(n):
            reps = EXT_REPS if (n == 8 and cfg in ("DP", "TUNED")) else MAIN_REPS
            for r in reps:
                tag, tried = chosen_tag(run, cfg, n, r)
                selection[f"{cfg}.n{n}.r{r}"] = {"used": tag, "tried": tried}
                if tag is not None:
                    lc[(cfg, n, r)] = lifecycle(run, tag, cfg)
    out: dict = {"selection": selection}

    def a_prime(cfg, n, r):
        x = lc.get((cfg, n, r))
        return x["a_prime_per_turn_s"] if x else None

    def paired(cfg_a, cfg_b, n, reps):
        xs = []
        for r in reps:
            u, v = a_prime(cfg_a, n, r), a_prime(cfg_b, n, r)
            if u is not None and v is not None:
                xs.append(u / v)
        return xs

    # ---- per-cell observations
    cells = {}
    for n in ALL_N:
        for cfg in configs_of(n):
            used = [lc[(cfg, n, r)] for r in MAIN_REPS if (cfg, n, r) in lc]
            hits = sum(x["reuse"][0] for x in used)
            tot = sum(x["reuse"][1] for x in used)
            h = Counter()
            for x in used:
                for k, v in x["h_counts"].items():
                    h[int(k)] += v
            nreq = sum(x["eval_requests"] for x in used)
            c = {"replicates": len(used), "reuse_obs": hits / tot if tot else None, "reuse": [hits, tot],
                 "h_obs": {k: v / sum(h.values()) for k, v in sorted(h.items())} if h else {},
                 "padding_obs": statistics.mean(x["padding"] for x in used) if used else None,
                 "a_prime_mean_s": statistics.mean(x["a_prime_per_turn_s"] for x in used) if used else None,
                 "W_measured_per_turn_s": (sum(x["W_measured_per_turn_s"] * x["eval_requests"] for x in used) / nreq)
                 if used and all(x["W_measured_per_turn_s"] is not None for x in used) else None,
                 "B4_cov_PK_mean": statistics.mean(x["B4"]["cov_PK"] for x in used) if used else None,
                 "B4_E_PK_over_EP_EK": statistics.mean(x["B4"]["E_PK"] / (x["B4"]["E_P"] * x["B4"]["E_K"])
                                                        for x in used if x["B4"]["E_K"] > 0) if used else None,
                 "ttft_turn_ge1_median_s": statistics.median(x["ttft_turn_ge1_median_s"] for x in used) if used else None,
                 "stationarity": {
                     "h_tvd_median": statistics.median(x["stationarity"]["h_tvd"] for x in used
                                                       if x["stationarity"]["h_tvd"] is not None) if used else None,
                     "reuse_diff_mean": statistics.mean(x["stationarity"]["reuse_second"] - x["stationarity"]["reuse_first"]
                                                        for x in used if x["stationarity"]["reuse_first"] is not None
                                                        and x["stationarity"]["reuse_second"] is not None) if used else None}}
            if cfg != "BASE":
                xs = paired(cfg, "BASE", n, MAIN_REPS)
                if xs:
                    m, lo, hi = boot_median_ci(xs)
                    c["ratio"] = {"per_rep": xs, "m": m, "ci": [lo, hi], "k": len(xs)}
            p = pred[str(n)][cfg]
            c["pred"] = {pr: {"reuse": p[pr]["reuse_rate"], "ratio": p[pr]["ratio_to_base"],
                              "h": h_of(p[pr]["h"]), "padding": p[pr]["padding"],
                              "W": p[pr]["W_per_turn_s"], "rank": p[pr]["rank"]} for pr in PREDS}
            cells[f"{cfg}.n{n}"] = c
    out["cells"] = cells

    conf_reuse = [(n, cfg) for n in CONFIRM_N for cfg in configs_of(n)]
    conf_ratio = [(n, cfg) for n in CONFIRM_N for cfg in configs_of(n) if cfg != "BASE"]

    # ---- §5.1 reuse
    s51 = {"cells": {}}
    reuse_null = null["reuse_null"]["value"]
    errs = {pr: [] for pr in PREDS}
    null_err = []
    obs_list = []
    for n, cfg in conf_reuse:
        c = cells[f"{cfg}.n{n}"]
        o = c["reuse_obs"]
        obs_list.append(o)
        row = {"obs": o, "null": reuse_null}
        for pr in PREDS:
            e = c["pred"][pr]["reuse"] - o
            errs[pr].append(e)
            row[pr] = c["pred"][pr]["reuse"]
        null_err.append(reuse_null - o)
        s51["cells"][f"{cfg}.n{n}"] = row
    k = len(conf_reuse)
    need = math.ceil(REUSE_SHARE * k - 1e-9)
    for pr in PREDS:
        within = sum(abs(e) <= REUSE_TOL for e in errs[pr])
        bias = statistics.mean(errs[pr])
        mae = statistics.mean(abs(e) for e in errs[pr])
        base_pass = within >= need and abs(bias) <= REUSE_BIAS
        s51[pr] = {"within_tol": within, "needed": need, "cells": k, "mean_signed_error": bias,
                   "base": "PASS" if base_pass else "FAIL", "MAE": mae}
    mae_null = statistics.mean(abs(e) for e in null_err)
    obs_range = max(obs_list) - min(obs_list)
    s51["MAE_null"] = mae_null
    s51["obs_range"] = obs_range
    for pr in PREDS:
        if obs_range < REUSE_RANGE_MIN:
            skill = "NOT_INFORMATIVE"
        else:
            skill = "PASS" if s51[pr]["MAE"] <= SKILL_FACTOR * mae_null else "FAIL"
        s51[pr]["skill"] = skill
        s51[pr]["MAE_over_null"] = s51[pr]["MAE"] / mae_null if mae_null else None
    s51["verdict"] = final(s51["analytic"]["base"], s51["analytic"]["skill"])
    out["5.1"] = s51

    # ---- §5.2 cost ratio
    s52 = {"cells": {}}
    for n, cfg in conf_ratio:
        c = cells[f"{cfg}.n{n}"]
        m, (lo, hi) = c["ratio"]["m"], c["ratio"]["ci"]
        row = {"m": m, "ci": [lo, hi], "k": c["ratio"]["k"]}
        for pr in PREDS:
            p = c["pred"][pr]["ratio"]
            if lo <= 1.0 <= hi:
                basic = abs(p - m) <= RATIO_TOL and abs(p - 1.0) <= RATIO_TOL
            else:
                basic = abs(p - m) <= RATIO_TOL and (math.copysign(1, 1 - p) == math.copysign(1, 1 - m))
            strong = (lo - RATIO_WIDEN) <= p <= (hi + RATIO_WIDEN)
            row[pr] = {"pred": p, "basic": basic, "strong": strong}
        s52["cells"][f"{cfg}.n{n}"] = row
    kk = len(conf_ratio)
    need_s = RATIO_STRONG_NEEDED.get(kk, math.ceil(0.83 * kk))
    sum_null = sum(abs(1 - r["m"]) for r in s52["cells"].values())
    effect = sum_null / kk
    s52["sum_abs_1_minus_m"] = sum_null
    s52["mean_abs_1_minus_m"] = effect
    for pr in PREDS:
        rows = list(s52["cells"].values())
        nb = sum(r[pr]["basic"] for r in rows)
        ns = sum(r[pr]["strong"] for r in rows)
        base_pass = nb == kk and ns >= need_s
        sp = sum(abs(r[pr]["pred"] - r["m"]) for r in rows)
        if effect < RATIO_EFFECT_MIN:
            skill = "NOT_INFORMATIVE"
        else:
            skill = "PASS" if sp <= SKILL_FACTOR * sum_null else "FAIL"
        s52[pr] = {"basic_pass": nb, "strong_pass": ns, "strong_needed": need_s, "cells": kk,
                   "base": "PASS" if base_pass else "FAIL", "sum_abs_err": sp,
                   "skill_ratio": sp / sum_null if sum_null else None, "skill": skill,
                   "verdict": final("PASS" if base_pass else "FAIL", skill)}
    out["5.2"] = s52

    # ---- §5.3 ranking
    s53 = {"per_n": {}}
    agree_all, any_resolved = True, False
    for n in CONFIRM_N:
        pairs = []
        for x, y in combinations(configs_of(n), 2):
            xs = paired(x, y, n, MAIN_REPS)
            m, lo, hi = boot_median_ci(xs)
            resolved = not (lo <= 1.0 <= hi)
            obs_cheaper = (x if hi < 1 else y) if resolved else None
            prow = {"pair": f"{x}/{y}", "m": m, "ci": [lo, hi], "k": len(xs), "resolved": resolved,
                    "obs_cheaper": obs_cheaper}
            for pr in PREDS:
                rx, ry = cells[f"{x}.n{n}"]["pred"][pr]["rank"], cells[f"{y}.n{n}"]["pred"][pr]["rank"]
                pc = x if rx < ry else y
                prow[f"{pr}_cheaper"] = pc
                prow[f"{pr}_agrees"] = (pc == obs_cheaper) if resolved else None
            pairs.append(prow)
        res = [p for p in pairs if p["resolved"]]
        if res:
            any_resolved = True
            ok = all(p["analytic_agrees"] for p in res)
            agree_all &= ok
            v = "PASS" if ok else "FAIL"
        else:
            v = "UNRESOLVED"
        s53["per_n"][str(n)] = {"verdict": v, "resolved": len(res), "pairs": pairs,
                                "agree": {pr: sum(bool(p[f"{pr}_agrees"]) for p in res) for pr in PREDS}}
    s53["verdict"] = ("PASS" if agree_all else "FAIL") if any_resolved else "UNRESOLVED"
    out["5.3"] = s53

    # ---- §5.4 DP vs TUNED (N = 8, r0..r9)
    xs = paired("DP", "TUNED", 8, EXT_REPS)
    m, lo, hi = boot_median_ci(xs)
    v = "PASS" if hi < 1 else ("FAIL" if lo > 1 else "INCONCLUSIVE")
    xs5 = paired("DP", "TUNED", 8, MAIN_REPS)
    m5, lo5, hi5 = boot_median_ci(xs5)
    out["5.4"] = {"k": len(xs), "per_rep": xs, "m": m, "ci": [lo, hi], "verdict": v,
                  "prior_prediction": "INCONCLUSIVE",
                  "pred_r0_r9": {pr: pext["r0_r9"]["DP_over_TUNED"][pr] for pr in PREDS},
                  "report_r0_r4_only": {"k": len(xs5), "m": m5, "ci": [lo5, hi5]}}

    # ---- §5.5 H-sim
    es = []
    for n, cfg in conf_ratio:
        c = s52["cells"][f"{cfg}.n{n}"]
        es.append(c["m"] - c["sim_default"]["pred"])
    kpos = sum(e > 0 for e in es)
    p = binom_two_sided(kpos, len(es))
    med = statistics.median(abs(e) for e in es)
    ca, cb = p >= 0.05, med < HSIM_MEDIAN
    out["5.5"] = {"e": es, "positive": kpos, "cells": len(es), "binom_p": p, "median_abs_e": med,
                  "a": ca, "b": cb,
                  "verdict": "SUPPORTED" if ca and cb else ("PARTIAL" if cb else "NOT_SUPPORTED"),
                  "manuscript_median_abs_e": HSIM_MEDIAN}

    # ---- §5.6 h(n)
    s56 = {"cells": {}}
    tv = {pr: [] for pr in PREDS}
    tv_null = []
    for n, cfg in conf_reuse:
        c = cells[f"{cfg}.n{n}"]
        ho = c["h_obs"]
        row = {"null": M.tvd(ho, h_of(null["h_null"][str(n)]["h"]))}
        tv_null.append(row["null"])
        for pr in PREDS:
            t = M.tvd(ho, c["pred"][pr]["h"])
            tv[pr].append(t)
            row[pr] = t
            row[f"{pr}_padding_abs_err"] = abs(c["pred"][pr]["padding"] - c["padding_obs"])
        s56["cells"][f"{cfg}.n{n}"] = row
    s56["null_median"] = statistics.median(tv_null)
    for pr in PREDS:
        med, mx = statistics.median(tv[pr]), max(tv[pr])
        base_pass = med <= H_MEDIAN and mx <= H_MAX
        skill = "PASS" if med < s56["null_median"] else "FAIL"
        s56[pr] = {"median": med, "max": mx, "base": "PASS" if base_pass else "FAIL", "skill": skill,
                   "verdict": final("PASS" if base_pass else "FAIL", skill)}
    s56["verdict"] = s56["analytic"]["verdict"]
    out["5.6"] = s56

    # ---- §5.7 W (exploratory)
    rows = []
    for n in ALL_N:
        for cfg in configs_of(n):
            c = cells[f"{cfg}.n{n}"]
            if c["W_measured_per_turn_s"] is None:
                continue
            rows.append({"cell": f"{cfg}.n{n}", "W_obs": c["W_measured_per_turn_s"],
                         **{f"W_{pr}": c["pred"][pr]["W"] for pr in PREDS},
                         "cov_PK": c["B4_cov_PK_mean"], "E_PK_over_EP_EK": c["B4_E_PK_over_EP_EK"]})
    out["5.7"] = {"rows": rows,
                  "ratio_pred_over_obs_median": {pr: statistics.median(r[f"W_{pr}"] / r["W_obs"] for r in rows
                                                                       if r["W_obs"] > 0) for pr in PREDS}
                  if rows else None,
                  "spearman": {pr: spearman([r[f"W_{pr}"] for r in rows], [r["W_obs"] for r in rows])
                               for pr in PREDS} if rows else None,
                  "cov_PK_positive_cells": sum(r["cov_PK"] > 0 for r in rows), "cells": len(rows)}

    # ---- N = 12 (exploratory)
    ex = {}
    for cfg in configs_of(12):
        c = cells[f"{cfg}.n12"]
        ex[cfg] = {"reuse_obs": c["reuse_obs"], "reuse_pred": {pr: c["pred"][pr]["reuse"] for pr in PREDS},
                   "h_tvd": {pr: M.tvd(c["h_obs"], c["pred"][pr]["h"]) for pr in PREDS},
                   "h_tvd_null": M.tvd(c["h_obs"], h_of(null["h_null"]["12"]["h"])),
                   "mean_running_obs": sum(k * v for k, v in c["h_obs"].items()),
                   "mean_running_pred": {pr: sum(k * v for k, v in c["pred"][pr]["h"].items()) for pr in PREDS}}
        if cfg != "BASE":
            ex[cfg]["ratio"] = {"m": c["ratio"]["m"], "ci": c["ratio"]["ci"],
                                "pred": {pr: c["pred"][pr]["ratio"] for pr in PREDS}}
    out["n12"] = ex

    # ---- §5.8 validity summary
    checks = [json.loads(l) for l in (run / "checks.jsonl").read_text().splitlines() if l.strip()]
    out["5.8"] = {"lifecycles_run": len(checks), "invalid": [c["tag"] for c in checks if not c["valid"]],
                  "retries": [c["tag"] for c in checks if c["tag"].endswith(".retry1")],
                  "missing_replicates": [k for k, v in selection.items() if v["used"] is None]}
    out["lifecycles"] = {f"{c}.n{n}.r{r}": v for (c, n, r), v in lc.items()}

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, default=str) + "\n")
    summary = {"5.1": s51["verdict"], "5.2": {pr: s52[pr]["verdict"] for pr in PREDS},
               "5.3": s53["verdict"], "5.4": out["5.4"]["verdict"], "5.5": out["5.5"]["verdict"],
               "5.6": s56["verdict"], "5.8": out["5.8"]}
    print(json.dumps(summary, indent=1))
    return 0


def final(base: str, skill: str) -> str:
    """Revision 2: the skill condition is ANDed to the confirmatory verdict."""
    if base != "PASS":
        return "FAIL"
    if skill == "PASS":
        return "PASS"
    if skill == "NOT_INFORMATIVE":
        return "PASS (skill NOT_INFORMATIVE)"
    return "NOT_CONFIRMED (base PASS, skill FAIL)"


if __name__ == "__main__":
    raise SystemExit(main())
