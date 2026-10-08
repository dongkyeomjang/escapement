#!/usr/bin/env python3
"""G-10 C verdicts: reuse (requests, tokens) and cost ratio under long tool outputs.

Prereg: docs/research/gpu/G10_C_PREREG.md section 6. Predictions:
plans_c/PREDICTIONS_C.json (committed before the measurement). Runs once.

Cells: chosen N x {SHORT_TOOL, LONG_TOOL} x {GPU_LONG_BASE, GPU_LONG_KV}, 5
paired replicates. Reference cost channel ``REF`` fixed at preregistration.

usage: judge_c.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
MT = HERE.parent / "multiturn"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MT))

import gpu_mt_measure as M  # noqa: E402
from exec_measure import exec_metrics, window_steps  # noqa: E402
import g10_common as G  # noqa: E402

PRED = HERE / "plans_c" / "PREDICTIONS_C.json"
TOOLS = ("SHORT_TOOL", "LONG_TOOL")
CFGS = ("GPU_LONG_BASE", "GPU_LONG_KV")
BOUNDS = ("lo", "hi")
REPS = 5
# reference cost channel, fixed by the preregistered rule (G10_C_PREREG section 6):
# DIRECT if the task-A development check ended "OK", else RECON. Task A ends
# before any C lifecycle; the C data never enter this choice.
_A = HERE / "exec_check_result" / "summary.json"
REF = "DIRECT" if (_A.exists() and json.loads(_A.read_text()).get("overall") == "OK") else "RECON"
NULL_REUSE = 0.84718      # GTASK20 / GTASK11 skill baseline (NPU constant predictor)
TOL_REUSE, TOL_COST = 0.05, 0.03
BOOT_SEED = 20264250


def load(d: Path) -> dict:
    m = M.lifecycle_metrics(d)
    x = exec_metrics(d, m)
    rows = [json.loads(l) for l in (d / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((d / "windows.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    later = [r for r in rows if w0 <= r["sent_s"] < w1 and r["turn"] > 0]
    ctx = sorted(r["prompt_tokens"] for r in later if r["prompt_tokens"] is not None)
    prompt_later = sum(ctx)
    return {"dir": d.name, "valid": m["valid"],
            "preemptions": m["metric_delta"].get("vllm:num_preemptions_total", 0.0),
            "reasons": m["invalid_reasons"] + m["checks"]["invalid_reasons_runner"], "m": m, "x": x,
            "direct_ok": x["direct_complete"] and x["overlaps"] == 0 and x["nonpositive"] == 0,
            "prompt_later": prompt_later, "prefill_computed_later": prompt_later - m["hit_tokens"],
            "ctx_quantiles": {q: ctx[int(q * (len(ctx) - 1))] for q in (0.05, 0.5, 0.95)} if ctx else None,
            "ctx_max": max((r["prompt_tokens"] + r["requested_generation_tokens"] for r in rows
                            if r["prompt_tokens"] is not None), default=None),
            "truncated": sum(1 for r in rows if r["prompt_tokens"] is not None
                             and r["prompt_tokens"] != r["sent_prompt_len"]),
            "admission": G.admission_delay(d)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    PJ = json.loads(PRED.read_text())
    n = PJ["chosen_n"]
    P = PJ["cells"][str(n)]
    runs, hist = {}, {}
    for t in TOOLS:
        for c in CFGS:
            for r in range(REPS):
                tag = f"n{n}.{t}.{c}.r{r}"
                for d in (a.run_dir / tag, a.run_dir / f"{tag}.retry1"):
                    if not (d / "windows.json").exists():
                        continue
                    try:
                        L = load(d)
                    except Exception as ex:
                        hist.setdefault(tag, []).append({"dir": d.name, "valid": False, "reasons": [repr(ex)]})
                        continue
                    hist.setdefault(tag, []).append({k: L[k] for k in ("dir", "valid", "preemptions", "reasons",
                                                                        "direct_ok", "truncated")}
                                                    | {"missing_window": L["x"]["missing_window"]})
                    cur = runs.get(tag)
                    if L["preemptions"] > 0 and cur is None:
                        runs[tag] = L
                    elif L["valid"] and (cur is None or (cur["preemptions"] == 0 and not cur["direct_ok"]
                                                          and L["direct_ok"])):
                        runs[tag] = L
    scope = sorted(k for k, v in runs.items() if v["preemptions"] > 0)
    out: dict = {"n": n, "ref_channel": REF, "validity": hist, "used": {k: v["dir"] for k, v in runs.items()},
                 "preemption_scope_violation": scope}
    ok = lambda L: L is not None and L["valid"] and L["preemptions"] == 0  # noqa: E731
    cells, reuse_err = {}, {b: {"req": [], "tok": []} for b in BOUNDS}
    for t in TOOLS:
        for c in CFGS:
            Ls = [runs.get(f"n{n}.{t}.{c}.r{r}") for r in range(REPS)]
            Ls = [L for L in Ls if ok(L)]
            if not Ls:
                continue
            hits, tot = sum(L["m"]["reuse"][0] for L in Ls), sum(L["m"]["reuse"][1] for L in Ls)
            ht, rt = sum(L["m"]["hit_tokens"] for L in Ls), sum(L["m"]["reusable_tokens"] for L in Ls)
            shape = {}
            for L in Ls:
                for k, v in L["m"]["hit_shape"].items():
                    shape[k] = shape.get(k, 0) + v
            cell = {"replicates": len(Ls), "reuse": [hits, tot], "reuse_rate": hits / tot,
                    "hit_tokens": ht, "reusable_tokens": rt, "token_reuse_ratio": ht / rt,
                    "hit_shape": shape, "partial_fraction": shape.get("partial", 0) / tot,
                    "prefill_tokens_computed_later": sum(L["prefill_computed_later"] for L in Ls),
                    "prompt_tokens_later": sum(L["prompt_later"] for L in Ls),
                    "ctx_quantiles_per_rep": [L["ctx_quantiles"] for L in Ls],
                    "ctx_max": max(L["ctx_max"] for L in Ls), "truncated": sum(L["truncated"] for L in Ls),
                    "admission_delay_mean_s": statistics.fmean(L["admission"]["mean_s"] for L in Ls),
                    "pred": {}}
            for b in BOUNDS:
                p = P[t][b][c]
                cell["pred"][b] = {"reuse_rate": p["reuse_rate"], "token_reuse_ratio": p["token_reuse_ratio"],
                                   "partial_fraction": p["partial_fraction"],
                                   "prefill_tokens_computed_later": p["prefill_tokens_computed_later"],
                                   "queue_wait_mean_s": p["queue_wait_mean_s"],
                                   "err_req": p["reuse_rate"] - cell["reuse_rate"],
                                   "err_tok": p["token_reuse_ratio"] - cell["token_reuse_ratio"]}
                reuse_err[b]["req"].append(cell["pred"][b]["err_req"])
                reuse_err[b]["tok"].append(cell["pred"][b]["err_tok"])
            cells[f"{t}/{c}"] = cell
    out["cells"] = cells
    full = len(cells) == 4
    ver: dict = {"reuse_cells": len(cells)}
    null_sum = sum(abs(NULL_REUSE - v["reuse_rate"]) for v in cells.values())
    for b in BOUNDS:
        er, et = reuse_err[b]["req"], reuse_err[b]["tok"]
        ver[f"reuse_req_{b}"] = {"mae": statistics.fmean(abs(e) for e in er) if er else None,
                                 "max": max((abs(e) for e in er), default=None),
                                 "pass": full and all(abs(e) <= TOL_REUSE for e in er)}
        ver[f"reuse_tok_{b}"] = {"mae": statistics.fmean(abs(e) for e in et) if et else None,
                                 "max": max((abs(e) for e in et), default=None),
                                 "pass": full and all(abs(e) <= TOL_REUSE for e in et),
                                 "note": "token criterion added in G-10, not a past gate"}
        s = sum(abs(e) for e in er)
        ver[f"reuse_skill_{b}"] = {"err_sum": s, "baseline_err_sum": null_sum, "baseline": NULL_REUSE,
                                   "verdict": "NA" if null_sum <= 1e-12 else ("PASS" if s <= 0.5 * null_sum else "FAIL")}
        ver[f"reuse_tok_skill_{b}"] = "NA (no preregistered baseline for the token metric)"
    # cost ratios
    cost = {}
    for t in TOOLS:
        rows = []
        for r in range(REPS):
            kb, kk = runs.get(f"n{n}.{t}.GPU_LONG_BASE.r{r}"), runs.get(f"n{n}.{t}.GPU_LONG_KV.r{r}")
            if not (ok(kb) and ok(kk)):
                continue
            row = {"rep": r}
            for b in BOUNDS:
                row[f"R_PRED_{b}"] = P[t][b]["R_PRED"]["per_rep"][r]
                row[f"R_RECON_{b}"] = kk["x"]["recon_per_turn_s"][b] / kb["x"]["recon_per_turn_s"][b]
            if kb["direct_ok"] and kk["direct_ok"]:
                row["R_DIRECT"] = kk["x"]["direct_per_turn_s"] / kb["x"]["direct_per_turn_s"]
            row["abs"] = {c: {"recon_lo_s": L["x"]["recon_per_turn_s"]["lo"], "recon_hi_s": L["x"]["recon_per_turn_s"]["hi"],
                              "direct_s": L["x"]["direct_per_turn_s"], "by_type": L["x"]["by_type"]}
                          for c, L in (("GPU_LONG_BASE", kb), ("GPU_LONG_KV", kk))}
            rows.append(row)
        med = lambda k: (statistics.median(x[k] for x in rows if k in x)  # noqa: E731
                         if any(k in x for x in rows) else None)
        cm = {k: med(k) for k in ("R_DIRECT", "R_RECON_lo", "R_RECON_hi", "R_PRED_lo", "R_PRED_hi")}
        judged = [x for x in rows if (REF != "DIRECT" or "R_DIRECT" in x)]
        ent = {"rows": rows, "median": cm, "replicates_judged": [x["rep"] for x in judged]}
        for b in BOUNDS:
            refk = "R_DIRECT" if REF == "DIRECT" else f"R_RECON_{b}"
            if judged:
                rp = statistics.median(x[f"R_PRED_{b}"] for x in judged)
                rr = statistics.median(x[refk] for x in judged)
                ent[f"check_{b}"] = {"R_PRED": rp, "R_ref": rr, "diff": rp - rr, "pass": abs(rp - rr) <= TOL_COST}
        if REF == "DIRECT" and any("R_DIRECT" in x for x in rows):
            rd = [x["R_DIRECT"] for x in rows if "R_DIRECT" in x]
            ent["direct_ci95"] = list(G.boot_ci(rd, BOOT_SEED))
            ent["sign_test"] = G.sign_test(rd)
        cost[t] = ent
    out["cost"] = cost
    for b in BOUNDS:
        ch = [cost[t].get(f"check_{b}") for t in TOOLS]
        if any(x is None for x in ch):
            ver[f"cost_{b}"] = "NA"
            ver[f"cost_skill_{b}"] = "NA"
            continue
        ver[f"cost_{b}"] = "PASS" if all(x["pass"] for x in ch) else "FAIL"
        e, e0 = sum(abs(x["diff"]) for x in ch), sum(abs(1 - x["R_ref"]) for x in ch)
        ver[f"cost_skill_{b}"] = {"err_sum": e, "baseline_err_sum": e0,
                                  "verdict": "NA" if e0 <= 1e-12 else ("PASS" if e <= 0.5 * e0 else "FAIL")}
    if scope:
        ver["scope"] = "SCOPE_VIOLATION (preemption observed)"
    out["verdict"] = ver
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(ver, indent=1, default=str))
    for k, v in cells.items():
        print(k, round(v["reuse_rate"], 3), round(v["token_reuse_ratio"], 3),
              {b: (round(v["pred"][b]["reuse_rate"], 3), round(v["pred"][b]["token_reuse_ratio"], 3)) for b in BOUNDS})
    for t in TOOLS:
        print(t, {k: (round(x, 4) if x is not None else None) for k, x in cost[t]["median"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
