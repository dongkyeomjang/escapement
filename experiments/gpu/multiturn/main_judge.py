#!/usr/bin/env python3
"""GTASK11 verdicts for the GPU multi-turn main experiment.

Criteria: docs/research/gpu/GPU_MULTITURN_PREREG.md section 5 as amended by
amendment 1 (directive G-04). Predictions: plans/PREDICTIONS.json (``2bef619``),
unchanged. Runs once, after every lifecycle has finished.

usage: main_judge.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "obs"))
import gpu_mt_measure as M  # noqa: E402
from parse_obs import parse  # noqa: E402

PRED = HERE / "plans" / "PREDICTIONS.json"
CONF_N = (20, 22, 24)
EXPL_N = (26,)
CONFIGS = ("BASE", "POOL", "POOL+GRID")
REPS = 5
BOUNDS = ("lo", "hi")
NPU_NULL_REUSE = 5771 / 6812        # TASK82 confirmatory cells, turn >= 1 pooled
NPU_HSIM = {"negative": 6, "cells": 7, "median_abs_e": 0.0055}
BOOT, BOOT_SEED = 10_000, 20262420
UNIFORM_H = {n: 1 / 8 for n in range(1, 9)}


def boot_ci(xs: list[float]) -> tuple[float, float]:
    rng = random.Random(BOOT_SEED)
    bs = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(BOOT))
    return bs[int(0.025 * BOOT)], bs[int(0.975 * BOOT) - 1]


def tvd(a: dict, b: dict) -> float:
    ta, tb = sum(a.values()), sum(b.values())
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in keys)


def decode_h(run: Path, rows_window_lines: tuple[int, int]) -> dict[int, int]:
    """Amendment 1: step-weighted distribution of *decoders* per step.

    Decoders in a step = ``reqs`` if ``maxq == 1`` else ``reqs - k`` with k =
    ``[GPFX] ALLOC`` lines since the previous ``[GSTEP]`` (at least 1). Steps
    with no decoder are left out (B2's h is over decode steps). Same rule as
    the price channel in ``gpu_mt_measure``.
    """
    lo, hi = rows_window_lines
    h = Counter()
    allocs = 0
    for e in parse(run / "server.log"):
        if e["kind"] == "ALLOC":
            allocs += 1
        elif e["kind"] == "STEP":
            if lo <= e["line"] <= hi:
                d = e["reqs"] if e["maxq"] == 1 else max(0, e["reqs"] - max(1, allocs))
                if d >= 1:
                    h[d] += 1
            allocs = 0
    return dict(h)


def window_lines(run: Path) -> tuple[int, int]:
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    ids = {r["request_id"] for r in rows if w0 <= r["sent_s"] < w1}
    lines = []
    for e in parse(run / "server.log"):
        if e["kind"] == "ALLOC":
            parts = e["req"].split("-")
            if any("-".join(parts[:k]) in ids for k in range(2, len(parts))):
                lines.append(e["line"])
    return (min(lines), max(lines)) if lines else (0, -1)


def orphan_evictions(run: Path) -> dict:
    """Exploratory: share of BlockRemoved events whose block still has a
    cached child at the moment of eviction (LRU by release, tail first ->
    about 0; allocation-order FIFO -> high)."""
    parent: dict[int, int | None] = {}
    children: dict[int, set] = defaultdict(set)
    cached: set = set()
    removed = orphan = 0
    for line in (run / "kv_events.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        for e in json.loads(line)["events"]:
            if e["type"] == "BlockStored":
                p = e.get("parent_block_hash")
                for h in e["block_hashes"]:
                    parent[h] = p
                    if p is not None:
                        children[p].add(h)
                    cached.add(h)
                    p = h
            elif e["type"] == "BlockRemoved":
                for h in e["block_hashes"]:
                    if h not in cached:
                        continue
                    removed += 1
                    if any(c in cached for c in children.get(h, ())):
                        orphan += 1
                    cached.discard(h)
            elif e["type"] == "AllBlocksCleared":
                cached.clear()
    return {"removed": removed, "orphan": orphan, "share": orphan / removed if removed else None}


def pick_runs(run_dir: Path) -> tuple[dict, dict]:
    chosen, log = {}, {}
    for n in CONF_N + EXPL_N:
        for c in CONFIGS:
            for r in range(REPS):
                tag = f"n{n}.{c}.r{r}"
                cands = [run_dir / tag] + [run_dir / f"{tag}.retry1"]
                got = None
                hist = []
                for d in cands:
                    if not (d / "windows.json").exists():
                        continue
                    m = M.lifecycle_metrics(d)
                    hist.append({"dir": d.name, "valid": m["valid"],
                                 "reasons": m["invalid_reasons"] + m["checks"]["invalid_reasons_runner"]})
                    if m["valid"] and got is None:
                        got = (d, m)
                if hist:
                    log[tag] = hist
                if got:
                    chosen[tag] = got
    return chosen, log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    P = json.loads(PRED.read_text())["cells"]
    runs, validity = pick_runs(a.run_dir)
    out: dict = {"validity": validity, "used": {k: v[0].name for k, v in runs.items()}}

    # ---- per-cell observations
    obs: dict = {}
    for n in CONF_N + EXPL_N:
        for c in CONFIGS:
            ms = [(r, runs[f"n{n}.{c}.r{r}"]) for r in range(REPS) if f"n{n}.{c}.r{r}" in runs]
            if not ms:
                continue
            ls = [m for _, (_, m) in ms]
            hits = sum(m["reuse"][0] for m in ls)
            tot = sum(m["reuse"][1] for m in ls)
            shape = Counter()
            for m in ls:
                shape.update(m["hit_shape"])
            h_reqs, h_dec = Counter(), Counter()
            orph = {"removed": 0, "orphan": 0}
            for _, (d, m) in ms:
                h_reqs.update({int(k): v for k, v in m["h_counts"].items()})
                h_dec.update(decode_h(d, window_lines(d)))
                o = orphan_evictions(d)
                orph["removed"] += o["removed"]
                orph["orphan"] += o["orphan"]
            obs[(n, c)] = {
                "reps": [r for r, _ in ms], "reuse": [hits, tot], "reuse_rate": hits / tot,
                "token_reuse_ratio": sum(m["hit_tokens"] for m in ls) / sum(m["reusable_tokens"] for m in ls),
                "hit_shape_share": {k: v / tot for k, v in shape.items()},
                "h_reqs": dict(h_reqs), "h_decode": dict(h_dec),
                "orphan_evictions": orph | {"share": orph["orphan"] / orph["removed"] if orph["removed"] else None},
                "device": {b: {r: m["device_per_turn_s"][b] for r, (_, m) in ms} for b in BOUNDS},
                "interference": {b: statistics.mean(m["interference_per_turn_s"][b] for m in ls) for b in BOUNDS},
                "direct_over_price_lo": [m["direct_per_turn_s"] / m["device_per_turn_s"]["lo"] for m in ls],
                "padding": statistics.mean(m["padding"] for m in ls),
                "ttft_turn_ge1_median_s": (statistics.median(t) if (t := [m["ttft_turn_ge1_median_s"] for m in ls
                                           if m["ttft_turn_ge1_median_s"] is not None]) else None),
            }
    out["observed"] = {f"{n}/{c}": v for (n, c), v in obs.items()}

    def pred(n, c, key, b):
        return P[str(n)][c][f"{key}/{b}"]

    def label(base_pass: bool, skill: str) -> str:
        if not base_pass:
            return "FAIL"
        return {"PASS": "PASS", "NOT_INFORMATIVE": "PASS (skill NOT_INFORMATIVE)"}.get(
            skill, "NOT_CONFIRMED (base PASS, skill FAIL)")

    conf_cells = [(n, c) for n in CONF_N for c in CONFIGS if (n, c) in obs]

    # ---- 5.1 reuse
    s51 = {}
    null_mae = statistics.mean(abs(NPU_NULL_REUSE - obs[k]["reuse_rate"]) for k in conf_cells)
    for p in ("analytic", "sim_lru", "sim_fifo"):
        for b in BOUNDS:
            errs = [pred(n, c, p, b)["reuse_rate"] - obs[(n, c)]["reuse_rate"] for n, c in conf_cells]
            a_ok = all(abs(e) <= 0.10 for e in errs)
            b_ok = abs(statistics.mean(errs)) <= 0.05
            mae = statistics.mean(abs(e) for e in errs)
            if null_mae < 0.05:
                skill = "NOT_INFORMATIVE"
            else:
                skill = "PASS" if mae <= 0.5 * null_mae else "FAIL"
            old_null = sum(abs(pred(n, "BASE", p, b)["reuse_rate"] - obs[(n, c)]["reuse_rate"])
                           for n, c in conf_cells)
            s51[f"{p}/{b}"] = {"errors": {f"{n}/{c}": e for (n, c), e in zip(conf_cells, errs)},
                               "a_all_within_0.10": a_ok, "b_mean_signed": statistics.mean(errs),
                               "b_ok": b_ok, "mae": mae, "null_mae": null_mae,
                               "skill_ratio": mae / null_mae, "skill": skill,
                               "verdict": label(a_ok and b_ok, skill),
                               "old_skill_sum_pred": sum(abs(e) for e in errs), "old_skill_sum_basenull": old_null}
    diff = {}
    for n in CONF_N:
        if (n, "BASE") in obs and (n, "POOL") in obs:
            diff[n] = {"observed": obs[(n, "POOL")]["reuse_rate"] - obs[(n, "BASE")]["reuse_rate"],
                       **{p: pred(n, "POOL", p, "lo")["reuse_rate"] - pred(n, "BASE", p, "lo")["reuse_rate"]
                          for p in ("analytic", "sim_lru", "sim_fifo")}}
    out["5.1"] = {"npu_null": NPU_NULL_REUSE, "by_predictor": s51, "pool_minus_base": diff,
                  "observed_range": max(obs[k]["reuse_rate"] for k in conf_cells)
                  - min(obs[k]["reuse_rate"] for k in conf_cells)}

    # ---- paired ratios
    def paired(n, num, den, b):
        dn, dd = obs[(n, num)]["device"][b], obs[(n, den)]["device"][b]
        rs = [dn[r] / dd[r] for r in sorted(set(dn) & set(dd))]
        lo, hi = boot_ci(rs)
        return {"ratios": rs, "m": statistics.median(rs), "ci": [lo, hi], "reps": len(rs)}

    ratio_cells = [(n, c) for n in CONF_N for c in ("POOL", "POOL+GRID")]
    s52 = {}
    for b in BOUNDS:
        ms = {f"{n}/{c}": paired(n, c, "BASE", b) for n, c in ratio_cells}
        sum1 = sum(abs(1 - v["m"]) for v in ms.values())
        ni = sum1 / len(ms) < 0.01
        old_ni = all(v["ci"][0] <= 1 <= v["ci"][1] for v in ms.values())
        per = {}
        for p in ("analytic", "sim_lru", "sim_fifo"):
            basic = enh = 0
            cells = {}
            sp = 0.0
            for (n, c) in ratio_cells:
                v = ms[f"{n}/{c}"]
                pr = pred(n, c, p, b)["ratio_to_base"]
                l, u = v["ci"]
                if l <= 1 <= u:
                    bok = abs(pr - v["m"]) <= 0.03 and abs(pr - 1) <= 0.03
                else:
                    bok = abs(pr - v["m"]) <= 0.03 and (1 - pr) * (1 - v["m"]) > 0
                eok = l - 0.01 <= pr <= u + 0.01
                basic += bok
                enh += eok
                sp += abs(pr - v["m"])
                cells[f"{n}/{c}"] = {"pred": pr, "basic": bok, "enhanced": eok}
            base_pass = basic == len(ratio_cells) and enh >= 5
            skill = "NOT_INFORMATIVE" if ni else ("PASS" if sp <= 0.5 * sum1 else "FAIL")
            per[p] = {"cells": cells, "basic": basic, "enhanced": enh, "sum_abs_err": sp,
                      "skill_ratio": sp / sum1 if sum1 else None, "skill": skill,
                      "verdict": label(base_pass, skill)}
        s52[b] = {"observed": ms, "sum_abs_1_minus_m": sum1, "not_informative_new": ni,
                  "not_informative_old_all_ci_include_1": old_ni, "by_predictor": per,
                  "hsim": {"e": {k: v["m"] - pred(int(k.split("/")[0]), k.split("/")[1], "sim_lru", b)["ratio_to_base"]
                                 for k, v in ms.items()}}}
        es = list(s52[b]["hsim"]["e"].values())
        s52[b]["hsim"].update({"negative": sum(e < 0 for e in es), "positive": sum(e > 0 for e in es),
                               "median_abs_e": statistics.median(abs(e) for e in es), "npu": NPU_HSIM})
    out["5.2"] = s52

    # ---- 5.3 rank and 5.4 POOL+GRID vs POOL
    s53, s54 = {}, {}
    for b in BOUNDS:
        s53[b] = {}
        s54[b] = {}
        for n in CONF_N:
            pairs = {}
            ok = True
            resolved = 0
            for x, y in (("BASE", "POOL"), ("BASE", "POOL+GRID"), ("POOL", "POOL+GRID")):
                v = paired(n, x, y, b)
                res = not (v["ci"][0] <= 1 <= v["ci"][1])
                obs_cheaper = y if v["m"] > 1 else x
                pa, py = pred(n, x, "analytic", b)["device_per_turn_s"], pred(n, y, "analytic", b)["device_per_turn_s"]
                pred_cheaper = y if pa > py else x
                if res:
                    resolved += 1
                    ok &= obs_cheaper == pred_cheaper
                pairs[f"{x}/{y}"] = v | {"resolved": res, "observed_cheaper": obs_cheaper,
                                         "predicted_cheaper": pred_cheaper}
            s53[b][n] = {"pairs": pairs, "verdict": "UNRESOLVED" if resolved == 0 else ("PASS" if ok else "FAIL")}
            v = paired(n, "POOL+GRID", "POOL", b)
            s54[b][n] = v | {"verdict": "PASS" if v["ci"][1] < 1 else ("FAIL" if v["ci"][0] > 1 else "INCONCLUSIVE")}
    out["5.3"], out["5.4"] = s53, s54

    # ---- 5.5 LRU vs FIFO
    sep, dl, df, closer = [], 0.0, 0.0, 0
    cells55 = {}
    for n, c in conf_cells:
        gl = [pred(n, c, "sim_lru", b)["reuse_rate"] - pred(n, c, "sim_fifo", b)["reuse_rate"] for b in BOUNDS]
        lru = statistics.mean(pred(n, c, "sim_lru", b)["reuse_rate"] for b in BOUNDS)
        fifo = statistics.mean(pred(n, c, "sim_fifo", b)["reuse_rate"] for b in BOUNDS)
        o = obs[(n, c)]["reuse_rate"]
        is_sep = all(abs(g) >= 0.07 for g in gl)
        cells55[f"{n}/{c}"] = {"obs": o, "sim_lru": lru, "sim_fifo": fifo, "separating": is_sep,
                               "d_L": abs(o - lru), "d_F": abs(o - fifo),
                               "partial_obs": obs[(n, c)]["hit_shape_share"].get("partial", 0.0),
                               "partial_lru": statistics.mean(pred(n, c, "sim_lru", b)["hit_shape_share"].get("partial", 0) for b in BOUNDS),
                               "partial_fifo": statistics.mean(pred(n, c, "sim_fifo", b)["hit_shape_share"].get("partial", 0) for b in BOUNDS),
                               "token_obs": obs[(n, c)]["token_reuse_ratio"],
                               "token_lru": pred(n, c, "sim_lru", "lo")["token_reuse_ratio"],
                               "token_fifo": pred(n, c, "sim_fifo", "lo")["token_reuse_ratio"],
                               "orphan_evictions": obs[(n, c)]["orphan_evictions"]}
        if is_sep:
            sep.append(f"{n}/{c}")
            dl += abs(o - lru)
            df += abs(o - fifo)
            closer += abs(o - lru) < abs(o - fifo)
    k = len(sep)
    need = -(-7 * k // 9)
    if k == 0:
        v55 = "NOT_TESTABLE"
    elif closer >= need and dl < df:
        v55 = "LRU_SUPPORTED"
    elif (k - closer) >= need and df < dl:
        v55 = "FIFO_SUPPORTED"
    else:
        v55 = "INCONCLUSIVE"
    out["5.5"] = {"cells": cells55, "separating": sep, "closer_to_lru": closer, "needed": need,
                  "sum_d_L": dl, "sum_d_F": df, "verdict": v55}

    # ---- 5.6 h(n)
    s56 = {}
    for b in BOUNDS:
        per = {}
        for defn in ("h_decode", "h_reqs"):
            tv = {f"{n}/{c}": tvd({int(k): v for k, v in pred(n, c, "analytic", b)["h"].items()}, obs[(n, c)][defn])
                  for n, c in conf_cells}
            tu = {f"{n}/{c}": tvd(UNIFORM_H, obs[(n, c)][defn]) for n, c in conf_cells}
            ts = {f"{n}/{c}": tvd({int(k): v for k, v in pred(n, c, "sim_lru", b)["h"].items()}, obs[(n, c)][defn])
                  for n, c in conf_cells}
            med, mx = statistics.median(tv.values()), max(tv.values())
            medu = statistics.median(tu.values())
            base_pass = med <= 0.10 and mx <= 0.20
            skill = "PASS" if med <= 0.5 * medu else "FAIL"
            per[defn] = {"tvd_analytic": tv, "tvd_uniform": tu, "tvd_sim_lru": ts, "median": med, "max": mx,
                         "median_uniform": medu, "skill": skill, "verdict": label(base_pass, skill),
                         "median_sim_lru": statistics.median(ts.values())}
        s56[b] = per
    pad = {f"{n}/{c}": {"obs": obs[(n, c)]["padding"], "analytic": pred(n, c, "analytic", "lo")["padding"],
                        "sim_lru": pred(n, c, "sim_lru", "lo")["padding"]} for n, c in conf_cells}
    out["5.6"] = {"primary_definition": "h_decode", "by_bound": s56, "padding": pad}

    # ---- 5.7 interference (exploratory)
    s57 = {}
    for b in BOUNDS:
        rows = []
        for n, c in conf_cells:
            ob = obs[(n, c)]["interference"][b]
            rows.append({"cell": f"{n}/{c}", "obs": ob,
                         **{p: pred(n, c, p, b)["interference_per_turn_s"] for p in ("analytic", "sim_lru")}})
        def spearman(xs, ys):
            rx = {v: i for i, v in enumerate(sorted(xs))}
            ry = {v: i for i, v in enumerate(sorted(ys))}
            a_ = [rx[x] for x in xs]
            b_ = [ry[y] for y in ys]
            ma, mb = statistics.mean(a_), statistics.mean(b_)
            num = sum((x - ma) * (y - mb) for x, y in zip(a_, b_))
            den = (sum((x - ma) ** 2 for x in a_) * sum((y - mb) ** 2 for y in b_)) ** 0.5
            return num / den if den else None
        s57[b] = {"rows": rows, **{f"{p}_ratio_median": statistics.median(r[p] / r["obs"] for r in rows)
                                   for p in ("analytic", "sim_lru")},
                  **{f"{p}_spearman": spearman([r[p] for r in rows], [r["obs"] for r in rows])
                     for p in ("analytic", "sim_lru")}}
    out["5.7"] = s57

    # ---- N = 26 exploratory
    e26 = {}
    for c in ("BASE", "POOL"):
        if (26, c) in obs:
            o = obs[(26, c)]
            e26[c] = {"reuse_obs": o["reuse_rate"], "per_rep_reuse": None,
                      **{p: pred(26, c, p, "lo")["reuse_rate"] for p in ("analytic", "sim_lru", "sim_fifo")},
                      "hit_shape": o["hit_shape_share"], "orphan_evictions": o["orphan_evictions"]}
    if (26, "BASE") in obs and (26, "POOL") in obs:
        e26["POOL/BASE"] = {b: paired(26, "POOL", "BASE", b) | {
            p: pred(26, "POOL", p, b)["ratio_to_base"] for p in ("analytic", "sim_lru", "sim_fifo")} for b in BOUNDS}
    if (24, "BASE") in obs and (26, "BASE") in obs:
        e26["base_reuse_drop_24_to_26"] = obs[(24, "BASE")]["reuse_rate"] - obs[(26, "BASE")]["reuse_rate"]
    out["N26"] = e26

    # ---- channels
    allr = [x for k in obs for x in obs[k]["direct_over_price_lo"]]
    out["direct_vs_price"] = {"median": statistics.median(allr), "min": min(allr), "max": max(allr),
                              "n": len(allr)}
    out["summary"] = {
        "5.1": {k: v["verdict"] for k, v in s51.items()},
        "5.2": {b: {p: v["verdict"] for p, v in s52[b]["by_predictor"].items()} for b in BOUNDS},
        "5.3": {b: {n: v["verdict"] for n, v in s53[b].items()} for b in BOUNDS},
        "5.4": {b: {n: v["verdict"] for n, v in s54[b].items()} for b in BOUNDS},
        "5.5": v55,
        "5.6": {b: {d: v["verdict"] for d, v in s56[b].items()} for b in BOUNDS},
    }
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
