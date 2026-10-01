#!/usr/bin/env python3
"""Verdicts of the unified-simulator blind cells N = 13, 17, 20
(SIMBLIND_PREREG.md, TASK93; directive 08 work C).

MULTITURN_MAIN_PREREG.md §5.1, §5.2, §5.3 and §5.6 with the revision-2 skill
conditions (0.5x), unchanged thresholds, on the nine cells N in {13, 17, 20} x
{BASE, BATCHONLY, TUNED}; main predictor ``sim_op`` (simulator advanced by
TASK92 operational costs, priced with the original model). User decision
(2026-10-02): the N = 20 BASE cell is excluded from §5.1 (base and skill) and
reported as "no information"; it stays the denominator of the cost ratios.
Plus the confirmatory item "sim_op beats sim": reuse MAE (§5.1 cells) and the
sum of |ratio prediction - m| both smaller. v1 is a reference predictor (no
verdict), labelled out of scope where N > the running ceiling.
Measurement, lifecycle selection and bootstrap are ``main_analyze``'s. Run once,
after every lifecycle has finished.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import main_analyze as A  # noqa: E402
import mt_measure as M  # noqa: E402

PLAN_DIR = HERE / "plans" / "main"
NS = (13, 17, 20)
CFGS = ("BASE", "BATCHONLY", "TUNED")
PREDS = ("sim_op", "sim", "v1")
MAIN = "sim_op"
VERDICT_PREDS = ("sim_op", "sim")     # v1: reference only
REPS = range(5)
STRONG_NEEDED = 5     # 83 % of 6 cells -> 5 (5/6 = 0.833)
NO_INFO = {(20, "BASE")}              # user decision: excluded from §5.1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    pred = json.loads((PLAN_DIR / "PREDICTIONS_SIM.json").read_text())["cells"]
    null = json.loads((PLAN_DIR / "NULL_PREDICTORS_SIM.json").read_text())

    lc, selection = {}, {}
    for n in NS:
        for cfg in CFGS:
            for r in REPS:
                tag, tried = A.chosen_tag(a.run, cfg, n, r)
                selection[f"{cfg}.n{n}.r{r}"] = {"used": tag, "tried": tried}
                if tag is not None:
                    lc[(cfg, n, r)] = A.lifecycle(a.run, tag, cfg)

    def ap_(cfg, n, r):
        x = lc.get((cfg, n, r))
        return x["a_prime_per_turn_s"] if x else None

    def paired(x, y, n):
        return [ap_(x, n, r) / ap_(y, n, r) for r in REPS
                if ap_(x, n, r) is not None and ap_(y, n, r) is not None]

    cells = {}
    for n in NS:
        for cfg in CFGS:
            used = [lc[(cfg, n, r)] for r in REPS if (cfg, n, r) in lc]
            hits = sum(x["reuse"][0] for x in used)
            tot = sum(x["reuse"][1] for x in used)
            h = Counter()
            for x in used:
                for k, v in x["h_counts"].items():
                    h[int(k)] += v
            c = {"replicates": len(used), "reuse_obs": hits / tot, "reuse": [hits, tot],
                 "h_obs": {k: v / sum(h.values()) for k, v in sorted(h.items())},
                 "padding_obs": statistics.mean(x["padding"] for x in used),
                 "a_prime_mean_s": statistics.mean(x["a_prime_per_turn_s"] for x in used),
                 "mean_running_obs": sum(k * v for k, v in h.items()) / sum(h.values()),
                 "ttft_turn_ge1_median_s": statistics.median(x["ttft_turn_ge1_median_s"] for x in used),
                 "W_measured_per_turn_s": sum(x["W_measured_per_turn_s"] * x["eval_requests"] for x in used)
                 / sum(x["eval_requests"] for x in used)}
            if cfg != "BASE":
                xs = paired(cfg, "BASE", n)
                m, lo, hi = A.boot_median_ci(xs)
                c["ratio"] = {"per_rep": xs, "m": m, "ci": [lo, hi], "k": len(xs)}
            p = pred[str(n)][cfg]
            c["pred"] = {pr: {"reuse": p[pr]["reuse_rate"], "ratio": p[pr]["ratio_to_base"],
                              "h": A.h_of(p[pr]["h"]), "padding": p[pr]["padding"],
                              "rank": p[pr]["rank"], "device_s": p[pr]["device_per_turn_s"]}
                         for pr in PREDS}
            c["v1_in_scope"] = p["v1"]["in_scope"]
            cells[f"{cfg}.n{n}"] = c
    out = {"selection": selection, "cells": cells}
    conf = [(n, c) for n in NS for c in CFGS]
    conf51 = [x for x in conf if x not in NO_INFO]
    conf_r = [(n, c) for n in NS for c in CFGS if c != "BASE"]

    # §5.1
    s51 = {"cells": {}}
    r0 = null["reuse_null"]["value"]
    obs = [cells[f"{c}.n{n}"]["reuse_obs"] for n, c in conf51]
    mae_null = statistics.mean(abs(r0 - o) for o in obs)
    rng_obs = max(obs) - min(obs)
    for pr in PREDS:
        errs = [cells[f"{c}.n{n}"]["pred"][pr]["reuse"] - cells[f"{c}.n{n}"]["reuse_obs"] for n, c in conf51]
        within = sum(abs(e) <= A.REUSE_TOL for e in errs)
        need = math.ceil(A.REUSE_SHARE * len(conf51) - 1e-9)
        base = within >= need and abs(statistics.mean(errs)) <= A.REUSE_BIAS
        mae = statistics.mean(abs(e) for e in errs)
        skill = ("NOT_INFORMATIVE" if rng_obs < A.REUSE_RANGE_MIN
                 else "PASS" if mae <= A.SKILL_FACTOR * mae_null else "FAIL")
        s51[pr] = {"within_tol": within, "needed": need, "mean_signed_error": statistics.mean(errs),
                   "MAE": mae, "base": "PASS" if base else "FAIL", "skill": skill,
                   "MAE_over_null": mae / mae_null, "verdict": A.final("PASS" if base else "FAIL", skill),
                   "errors": dict(zip((f"{c}.n{n}" for n, c in conf51), errs))}
    s51.update(MAE_null=mae_null, obs_range=rng_obs, verdict=s51[MAIN]["verdict"],
               no_information={f"{c}.n{n}": {pr: cells[f"{c}.n{n}"]["pred"][pr]["reuse"] for pr in PREDS}
                               | {"obs": cells[f"{c}.n{n}"]["reuse_obs"]} for n, c in sorted(NO_INFO)})
    s51["v1"]["note"] = "reference; out of scope in cells with N > running ceiling"
    out["5.1"] = s51

    # §5.2
    s52 = {"cells": {}}
    for n, c in conf_r:
        cc = cells[f"{c}.n{n}"]
        m, (lo, hi) = cc["ratio"]["m"], cc["ratio"]["ci"]
        row = {"m": m, "ci": [lo, hi]}
        for pr in PREDS:
            p = cc["pred"][pr]["ratio"]
            if lo <= 1.0 <= hi:
                basic = abs(p - m) <= A.RATIO_TOL and abs(p - 1.0) <= A.RATIO_TOL
            else:
                basic = abs(p - m) <= A.RATIO_TOL and math.copysign(1, 1 - p) == math.copysign(1, 1 - m)
            row[pr] = {"pred": p, "basic": basic,
                       "strong": (lo - A.RATIO_WIDEN) <= p <= (hi + A.RATIO_WIDEN)}
        s52["cells"][f"{c}.n{n}"] = row
    rows = list(s52["cells"].values())
    sum_null = sum(abs(1 - r["m"]) for r in rows)
    effect = sum_null / len(rows)
    for pr in PREDS:
        nb = sum(r[pr]["basic"] for r in rows)
        ns = sum(r[pr]["strong"] for r in rows)
        base = nb == len(rows) and ns >= STRONG_NEEDED
        sp = sum(abs(r[pr]["pred"] - r["m"]) for r in rows)
        skill = ("NOT_INFORMATIVE" if effect < A.RATIO_EFFECT_MIN
                 else "PASS" if sp <= A.SKILL_FACTOR * sum_null else "FAIL")
        s52[pr] = {"basic_pass": nb, "strong_pass": ns, "strong_needed": STRONG_NEEDED,
                   "base": "PASS" if base else "FAIL", "sum_abs_err": sp,
                   "skill_ratio": sp / sum_null, "skill": skill,
                   "verdict": A.final("PASS" if base else "FAIL", skill)}
    s52.update(sum_abs_1_minus_m=sum_null, mean_abs_1_minus_m=effect, verdict=s52[MAIN]["verdict"])
    out["5.2"] = s52

    # §5.3
    s53 = {"per_n": {}}
    agree_all, any_res = True, False
    for n in NS:
        pairs = []
        for x, y in combinations(CFGS, 2):
            xs = paired(x, y, n)
            m, lo, hi = A.boot_median_ci(xs)
            res = not (lo <= 1.0 <= hi)
            cheaper = (x if hi < 1 else y) if res else None
            row = {"pair": f"{x}/{y}", "m": m, "ci": [lo, hi], "resolved": res, "obs_cheaper": cheaper}
            for pr in PREDS:
                pc = x if cells[f"{x}.n{n}"]["pred"][pr]["rank"] < cells[f"{y}.n{n}"]["pred"][pr]["rank"] else y
                row[f"{pr}_cheaper"] = pc
                row[f"{pr}_agrees"] = (pc == cheaper) if res else None
            pairs.append(row)
        resd = [p for p in pairs if p["resolved"]]
        if resd:
            any_res = True
            ok = all(p[f"{MAIN}_agrees"] for p in resd)
            agree_all &= ok
        s53["per_n"][str(n)] = {"verdict": ("PASS" if ok else "FAIL") if resd else "UNRESOLVED",
                                "resolved": len(resd), "pairs": pairs,
                                "agree": {pr: sum(bool(p[f"{pr}_agrees"]) for p in resd) for pr in PREDS}}
    s53["verdict"] = ("PASS" if agree_all else "FAIL") if any_res else "UNRESOLVED"
    out["5.3"] = s53

    # §5.6
    s56 = {"cells": {}}
    tv = {pr: [] for pr in PREDS}
    tvn = []
    for n, c in conf:
        cc = cells[f"{c}.n{n}"]
        row = {"null": M.tvd(cc["h_obs"], A.h_of(null["h_null"][str(n)]["h"]))}
        tvn.append(row["null"])
        for pr in PREDS:
            row[pr] = M.tvd(cc["h_obs"], cc["pred"][pr]["h"])
            tv[pr].append(row[pr])
        s56["cells"][f"{c}.n{n}"] = row
    s56["null_median"] = statistics.median(tvn)
    for pr in PREDS:
        med, mx = statistics.median(tv[pr]), max(tv[pr])
        base = med <= A.H_MEDIAN and mx <= A.H_MAX
        skill = "PASS" if med < s56["null_median"] else "FAIL"
        s56[pr] = {"median": med, "max": mx, "base": "PASS" if base else "FAIL", "skill": skill,
                   "verdict": A.final("PASS" if base else "FAIL", skill)}
    s56["verdict"] = s56[MAIN]["verdict"]
    out["5.6"] = s56

    # sim_op vs sim
    ra, rb = s51["sim_op"]["MAE"], s51["sim"]["MAE"]
    ca, cb = s52["sim_op"]["sum_abs_err"], s52["sim"]["sum_abs_err"]
    out["simop_vs_sim"] = {"reuse_MAE": [ra, rb], "ratio_sum_abs_err": [ca, cb],
                           "reuse_better": ra < rb, "ratio_better": ca < cb,
                           "verdict": "PASS" if ra < rb and ca < cb else "FAIL"}
    # v1 reference: in-scope cells only (N <= running ceiling)
    ins = [(n, c) for n, c in conf51 if cells[f"{c}.n{n}"]["v1_in_scope"]]
    out["v1_in_scope_reference"] = {
        "cells": [f"{c}.n{n}" for n, c in ins],
        "reuse_abs_err": {f"{c}.n{n}": abs(cells[f"{c}.n{n}"]["pred"]["v1"]["reuse"] - cells[f"{c}.n{n}"]["reuse_obs"])
                          for n, c in ins},
        "ratio_abs_err": {f"{c}.n{n}": abs(cells[f"{c}.n{n}"]["pred"]["v1"]["ratio"] - cells[f"{c}.n{n}"]["ratio"]["m"])
                          for n, c in ins if c != "BASE"}}

    checks = [json.loads(l) for l in (a.run / "checks.jsonl").read_text().splitlines() if l.strip()]
    out["validity"] = {"lifecycles_run": len(checks), "invalid": [c["tag"] for c in checks if not c["valid"]],
                       "retries": [c["tag"] for c in checks if c["tag"].endswith(".retry1")],
                       "missing_replicates": [k for k, v in selection.items() if v["used"] is None]}
    out["lifecycles"] = {f"{c}.n{n}.r{r}": v for (c, n, r), v in lc.items()}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps({"5.1": {pr: s51[pr]["verdict"] for pr in PREDS},
                      "5.2": {pr: s52[pr]["verdict"] for pr in PREDS}, "5.3": s53["verdict"],
                      "5.6": {pr: s56[pr]["verdict"] for pr in PREDS}, "simop_vs_sim": out["simop_vs_sim"],
                      "validity": out["validity"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
