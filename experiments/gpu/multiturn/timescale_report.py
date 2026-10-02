#!/usr/bin/env python3
"""G-05 task B report (development set): reuse, cost ratio and collapse curve
of the sim LRU time-scale variants against the GTASK11 observation.

usage: timescale_report.py --sim <abs sim.json> --verdict <abs verdict.json>
                           --pred <abs PREDICTIONS.json> --out <abs json>
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

CONF = [(n, c) for n in (20, 22, 24) for c in ("BASE", "POOL", "POOL+GRID")]
RATIO = [(n, c) for n in (20, 22, 24) for c in ("POOL", "POOL+GRID")]


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("sim", "verdict", "pred", "out"):
        ap.add_argument(f"--{k}", required=True, type=Path)
    a = ap.parse_args()
    sim = json.loads(a.sim.read_text())
    ver = json.loads(a.verdict.read_text())
    pred = json.loads(a.pred.read_text())
    runs = defaultdict(list)
    for r in sim["runs"]:
        runs[(r["variant"], r["n"], r["config"])].append(r)
    obs_reuse = {}
    for key, o in ver["observed"].items():
        n, c = key.split("/")
        obs_reuse[(int(n), c)] = o["reuse_rate"]
    obs_m = {}
    for key, o in ver["5.2"]["lo"]["observed"].items():
        n, c = key.split("/")
        obs_m[(int(n), c)] = o["m"]
    # N26 POOL/BASE observed m
    out = {"variants": {}}
    for v in sim["meta"]["variants"]:
        cell = {}
        for (vv, n, c), rs in runs.items():
            if vv != v:
                continue
            rs.sort(key=lambda r: r["rep"])
            hits = sum(r["reuse"][0] for r in rs)
            later = sum(r["reuse"][1] for r in rs)
            cell[(n, c)] = {"reuse": hits / later,
                            "price_per_turn": [r["price_per_turn_s"] for r in rs],
                            "pooled": sum(r["price_per_turn_s"] * r["requests_in_window"] for r in rs)
                            / sum(r["requests_in_window"] for r in rs)}
        for (n, c), e in cell.items():
            base = cell[(n, "BASE")]["price_per_turn"]
            e["ratios"] = [x / y for x, y in zip(e["price_per_turn"], base)]
            # same definition as PREDICTIONS.json ratio_to_base (pooled over reps)
            e["m"] = e["pooled"] / cell[(n, "BASE")]["pooled"]
        err = {f"{n}/{c}": cell[(n, c)]["reuse"] - obs_reuse[(n, c)] for n, c in cell}
        mae = statistics.mean(abs(err[f"{n}/{c}"]) for n, c in CONF)
        cost_err = {f"{n}/{c}": cell[(n, c)]["m"] - obs_m[(n, c)] for n, c in RATIO}
        out["variants"][v] = {
            "reuse": {f"{n}/{c}": e["reuse"] for (n, c), e in sorted(cell.items())},
            "reuse_minus_obs": err, "conf_mae": mae,
            "mean_signed_conf": statistics.mean(err[f"{n}/{c}"] for n, c in CONF),
            "cost_m": {f"{n}/{c}": cell[(n, c)]["m"] for n, c in cell if c != "BASE"},
            "cost_minus_obs": cost_err,
            "cost_sum_abs_err": sum(abs(x) for x in cost_err.values()),
        }
    # regression: orig vs PREDICTIONS sim_lru/lo
    reg = {}
    for (n, c) in CONF + [(26, "BASE"), (26, "POOL")]:
        reg[f"{n}/{c}"] = out["variants"]["orig"]["reuse"][f"{n}/{c}"] - \
            pred["cells"][str(n)][c]["sim_lru/lo"]["reuse_rate"]
    out["regression_orig_minus_predictions"] = reg
    out["regression_ratio"] = {f"{n}/{c}": out["variants"]["orig"]["cost_m"][f"{n}/{c}"]
                               - pred["cells"][str(n)][c]["sim_lru/lo"]["ratio_to_base"]
                               for n, c in RATIO}
    # share of finding-4 gap explained
    share = {}
    for key in ("22/BASE", "24/BASE", "26/BASE"):
        gap = out["variants"]["orig"]["reuse_minus_obs"][key]
        share[key] = {v: (gap - d["reuse_minus_obs"][key]) / gap for v, d in out["variants"].items()}
    out["gap_explained_share"] = share
    out["observed_reuse"] = {f"{n}/{c}": x for (n, c), x in obs_reuse.items()}
    out["meta"] = sim["meta"]
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    v0 = out["variants"]
    print("regression max |d|", max(abs(x) for x in reg.values()),
          max(abs(x) for x in out["regression_ratio"].values()))
    print("cell", "obs", *v0)
    for key in out["variants"]["orig"]["reuse"]:
        print(key, round(obs_reuse[tuple([int(key.split('/')[0]), key.split('/')[1]])], 3),
              *[round(d["reuse"][key], 3) for d in v0.values()])
    for v, d in v0.items():
        print(v, "MAE", round(d["conf_mae"], 4), "signed", round(d["mean_signed_conf"], 4),
              "costΣ", round(d["cost_sum_abs_err"], 4),
              "N24B", round(d["reuse_minus_obs"]["24/BASE"], 3), "N26B", round(d["reuse_minus_obs"]["26/BASE"], 3))
    print("share", json.dumps(share, indent=0))
    print("meta", json.dumps(sim["meta"]["class_median_ratio"]), sim["meta"]["variants"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
