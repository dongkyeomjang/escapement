#!/usr/bin/env python3
"""G-07 C verdicts for the collapse-region blind cells N = 25, 28.

Criteria: docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md section 5 (GPU prereg
amendment 1 sections 5.1, 5.2, 5.3, 5.6 on 6 cells / 4 ratio cells; primary
predictor ``ctx``). Predictions: plans/blind/PREDICTIONS_BLIND.json, committed
before the measurement. Helpers (bootstrap, TVD, decode-only h, window lines,
lifecycle metrics) are main_judge's, unchanged. Runs once.

usage: blind_judge.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_mt_measure as M  # noqa: E402
from main_judge import NPU_NULL_REUSE, UNIFORM_H, boot_ci, decode_h, tvd, window_lines  # noqa: E402

PRED = HERE / "plans" / "blind" / "PREDICTIONS_BLIND.json"
NS = (25, 28)
CONFIGS = ("BASE", "POOL", "POOL+GRID")
RATIO_CELLS = [(n, c) for n in NS for c in ("POOL", "POOL+GRID")]
REPS = 5
BOUNDS = ("lo", "hi")
PREDICTORS = ("ctx", "x1.210", "mode_dist", "price")
PRIMARY = "ctx"


def label(base_pass: bool, skill: str) -> str:
    if not base_pass:
        return "FAIL"
    return {"PASS": "PASS", "NOT_INFORMATIVE": "PASS (skill NOT_INFORMATIVE)"}.get(
        skill, "NOT_CONFIRMED (base PASS, skill FAIL)")


def both(vs: list[str]) -> str:
    """Overall over the two bounds: PASS only if PASS in both."""
    if all(v.startswith("PASS") for v in vs):
        return vs[0] if len(set(vs)) == 1 else "PASS"
    return "FAIL" if any(v == "FAIL" for v in vs) else "NOT_CONFIRMED"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    P = json.loads(PRED.read_text())["cells"]

    def pred(p, b, n, c):
        return P[f"{p}/{b}"][str(n)][c]

    runs, validity = {}, {}
    for n in NS:
        for c in CONFIGS:
            for r in range(REPS):
                tag = f"n{n}.{c}.r{r}"
                hist, got = [], None
                for d in (a.run_dir / tag, a.run_dir / f"{tag}.retry1"):
                    if not (d / "windows.json").exists():
                        continue
                    m = M.lifecycle_metrics(d)
                    hist.append({"dir": d.name, "valid": m["valid"],
                                 "reasons": m["invalid_reasons"] + m["checks"]["invalid_reasons_runner"]})
                    if m["valid"] and got is None:
                        got = (d, m)
                if hist:
                    validity[tag] = hist
                if got:
                    runs[tag] = got
    out: dict = {"validity": validity, "used": {k: v[0].name for k, v in runs.items()}}

    obs = {}
    for n in NS:
        for c in CONFIGS:
            ms = [(r, runs[f"n{n}.{c}.r{r}"]) for r in range(REPS) if f"n{n}.{c}.r{r}" in runs]
            if not ms:
                continue
            ls = [m for _, (_, m) in ms]
            hits, tot = sum(m["reuse"][0] for m in ls), sum(m["reuse"][1] for m in ls)
            h_dec, h_reqs = Counter(), Counter()
            for _, (d, m) in ms:
                h_dec.update(decode_h(d, window_lines(d)))
                h_reqs.update({int(k): v for k, v in m["h_counts"].items()})
            obs[(n, c)] = {"reps": [r for r, _ in ms], "reuse": [hits, tot], "reuse_rate": hits / tot,
                           "per_rep_reuse": [m["reuse"][0] / m["reuse"][1] for m in ls],
                           "h_decode": dict(h_dec), "h_reqs": dict(h_reqs),
                           "device": {b: {r: m["device_per_turn_s"][b] for r, (_, m) in ms} for b in BOUNDS},
                           "direct_over_price_lo": [m["direct_per_turn_s"] / m["device_per_turn_s"]["lo"] for m in ls],
                           "ttft_turn_ge1_median_s": (statistics.median(t) if (t := [
                               m["ttft_turn_ge1_median_s"] for m in ls if m["ttft_turn_ge1_median_s"] is not None])
                               else None)}
    out["observed"] = {f"{n}/{c}": v for (n, c), v in obs.items()}
    cells = [(n, c) for n in NS for c in CONFIGS if (n, c) in obs]

    def paired(n, num, den, b):
        dn, dd = obs[(n, num)]["device"][b], obs[(n, den)]["device"][b]
        rs = [dn[r] / dd[r] for r in sorted(set(dn) & set(dd))]
        lo, hi = boot_ci(rs)
        return {"ratios": rs, "m": statistics.median(rs), "ci": [lo, hi], "reps": len(rs)}

    # 5.1 reuse
    s51 = {}
    null_mae = statistics.mean(abs(NPU_NULL_REUSE - obs[k]["reuse_rate"]) for k in cells)
    for p in PREDICTORS:
        per = {}
        for b in BOUNDS:
            errs = {f"{n}/{c}": pred(p, b, n, c)["reuse_rate"] - obs[(n, c)]["reuse_rate"] for n, c in cells}
            a_ok = all(abs(e) <= 0.10 for e in errs.values())
            msigned = statistics.mean(errs.values())
            mae = statistics.mean(abs(e) for e in errs.values())
            skill = "NOT_INFORMATIVE" if null_mae < 0.05 else ("PASS" if mae <= 0.5 * null_mae else "FAIL")
            per[b] = {"errors": errs, "a_ok": a_ok, "mean_signed": msigned, "b_ok": abs(msigned) <= 0.05,
                      "mae": mae, "null_mae": null_mae, "skill": skill,
                      "verdict": label(a_ok and abs(msigned) <= 0.05, skill)}
        per["overall"] = both([per[b]["verdict"] for b in BOUNDS])
        s51[p] = per
    out["5.1"] = s51

    # 5.2 cost ratio
    s52 = {}
    for b in BOUNDS:
        ms = {f"{n}/{c}": paired(n, c, "BASE", b) for n, c in RATIO_CELLS if (n, c) in obs and (n, "BASE") in obs}
        sum1 = sum(abs(1 - v["m"]) for v in ms.values())
        ni = sum1 / len(ms) < 0.01
        per = {}
        for p in PREDICTORS:
            basic = enh = 0
            sp = 0.0
            cl = {}
            for key, v in ms.items():
                n, c = int(key.split("/")[0]), key.split("/")[1]
                pr = pred(p, b, n, c)["ratio_to_base"]
                l, u = v["ci"]
                if l <= 1 <= u:
                    bok = abs(pr - v["m"]) <= 0.03 and abs(pr - 1) <= 0.03
                else:
                    bok = abs(pr - v["m"]) <= 0.03 and (1 - pr) * (1 - v["m"]) > 0
                eok = l - 0.01 <= pr <= u + 0.01
                basic += bok
                enh += eok
                sp += abs(pr - v["m"])
                cl[key] = {"pred": pr, "err": pr - v["m"], "basic": bok, "enhanced": eok}
            base_pass = basic == len(ms) and enh >= len(ms) - 1
            skill = "NOT_INFORMATIVE" if ni else ("PASS" if sp <= 0.5 * sum1 else "FAIL")
            per[p] = {"cells": cl, "basic": basic, "enhanced": enh, "sum_abs_err": sp, "skill": skill,
                      "verdict": label(base_pass, skill)}
        s52[b] = {"observed": ms, "sum_abs_1_minus_m": sum1, "not_informative": ni, "by_predictor": per}
    out["5.2"] = s52
    out["5.2_overall"] = {p: both([s52[b]["by_predictor"][p]["verdict"] for b in BOUNDS]) for p in PREDICTORS}

    # 5.3 rank (primary predictor's per-turn price)
    s53 = {}
    for b in BOUNDS:
        s53[b] = {}
        for n in NS:
            pairs, ok, resolved = {}, True, 0
            for x, y in (("BASE", "POOL"), ("BASE", "POOL+GRID"), ("POOL", "POOL+GRID")):
                if (n, x) not in obs or (n, y) not in obs:
                    continue
                v = paired(n, x, y, b)
                res = not (v["ci"][0] <= 1 <= v["ci"][1])
                obs_cheaper = y if v["m"] > 1 else x
                pc = {p: (y if pred(p, b, n, x)["price_per_turn_s"] > pred(p, b, n, y)["price_per_turn_s"] else x)
                      for p in PREDICTORS}
                if res:
                    resolved += 1
                    ok &= obs_cheaper == pc[PRIMARY]
                pairs[f"{x}/{y}"] = v | {"resolved": res, "observed_cheaper": obs_cheaper, "predicted_cheaper": pc}
            s53[b][n] = {"pairs": pairs, "verdict": "UNRESOLVED" if resolved == 0 else ("PASS" if ok else "FAIL")}
    out["5.3"] = s53

    # 5.6 h (decode-only primary, reqs reported)
    s56 = {}
    for b in BOUNDS:
        per = {}
        for defn in ("h_decode", "h_reqs"):
            tu = {f"{n}/{c}": tvd(UNIFORM_H, obs[(n, c)][defn]) for n, c in cells}
            byp = {}
            for p in PREDICTORS:
                tv = {f"{n}/{c}": tvd({int(k): v for k, v in pred(p, b, n, c)["h_decode"].items()}, obs[(n, c)][defn])
                      for n, c in cells}
                med, mx = statistics.median(tv.values()), max(tv.values())
                skill = "PASS" if med <= 0.5 * statistics.median(tu.values()) else "FAIL"
                byp[p] = {"tvd": tv, "median": med, "max": mx, "skill": skill,
                          "verdict": label(med <= 0.10 and mx <= 0.20, skill)}
            per[defn] = {"tvd_uniform": tu, "median_uniform": statistics.median(tu.values()), "by_predictor": byp}
        s56[b] = per
    out["5.6"] = s56
    out["5.6_overall"] = {p: both([s56[b]["h_decode"]["by_predictor"][p]["verdict"] for b in BOUNDS])
                          for p in PREDICTORS}

    # additional confirmation: (1) ctx beats (3) price on BASE reuse error and ratio sum error
    def base_err(p, b):
        return sum(abs(pred(p, b, n, "BASE")["reuse_rate"] - obs[(n, "BASE")]["reuse_rate"])
                   for n in NS if (n, "BASE") in obs)
    add = {}
    for b in BOUNDS:
        e = {p: {"base_reuse_abs_err": base_err(p, b), "ratio_sum_abs_err": s52[b]["by_predictor"][p]["sum_abs_err"]}
             for p in PREDICTORS}
        add[b] = {"errors": e,
                  "ctx_beats_price": e["ctx"]["base_reuse_abs_err"] < e["price"]["base_reuse_abs_err"]
                  and e["ctx"]["ratio_sum_abs_err"] < e["price"]["ratio_sum_abs_err"],
                  "report_ctx_vs_x1.210": {k: e["ctx"][k] - e["x1.210"][k] for k in e["ctx"]},
                  "report_ctx_vs_mode_dist": {k: e["ctx"][k] - e["mode_dist"][k] for k in e["ctx"]}}
    out["additional"] = add
    out["additional_overall"] = "CONFIRMED" if all(add[b]["ctx_beats_price"] for b in BOUNDS) else "NOT_CONFIRMED"
    allr = [x for k in obs for x in obs[k]["direct_over_price_lo"]]
    out["direct_vs_price"] = {"median": statistics.median(allr), "min": min(allr), "max": max(allr), "n": len(allr)}
    out["summary"] = {"5.1": {p: s51[p]["overall"] for p in PREDICTORS}, "5.2": out["5.2_overall"],
                      "5.3": {b: {n: v["verdict"] for n, v in s53[b].items()} for b in BOUNDS},
                      "5.6": out["5.6_overall"], "additional": out["additional_overall"]}
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
