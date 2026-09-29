#!/usr/bin/env python3
"""GTASK05 step-cost summaries (prereg: docs/research/gpu/GPU_STEPCOST_PREREG.md).

Timing source: consecutive [GSTEP] dispatch timestamps (perf_counter, same
process). Delta_k = t_{k+1} - t_k.

Attribution. With async scheduling the engine keeps two batches in flight
(v1/engine/core.py:469-533): step k+2 is dispatched only after step k's output
arrives. In a GPU-bound steady state Delta_{k+1} therefore spans GPU step k.
The lag L used to attribute an isolated step is fixed by rule, not by eye:
L = argmax over {0, 1, 2} of the median (Delta_{k+L} - decode baseline) on the
largest isolated steps (EAGER, d=4, p=2048), and the same L is used for every
isolated step in every lifecycle. Inside a homogeneous decode segment the lag
does not matter.

Summaries (TASK13/TASK55 style): median per cell, IQR, n, and the spread of
per-lifecycle medians (between-restart variation). FULL is also fitted as
t(n) = F[bucket(n)] + g * n over grids G1/G3 (least squares, shared g).

usage: stepcost_analyze.py --run-dir <abs> --out <abs json> --md <abs md>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "obs"))
from parse_obs import parse  # noqa: E402

GRIDS = {"G1": [1, 2, 4, 8, 16], "G2": [1, 2, 4, 6, 8], "G3": list(range(1, 17))}
TRIM = 3  # steps dropped at each end of a homogeneous segment


def q(xs, p):
    return float(np.percentile(xs, p)) if xs else None


def windows(events: list) -> dict:
    w = {}
    for e in events:
        m = re.match(r"(\w+) (.*) (start|end)$", e["tag"])
        key = (m.group(1), m.group(2))
        w.setdefault(key, {})[m.group(3)] = e["wall"]
    return w


def lifecycle_cells(d: Path, lag: int | None, budget: int | None = None) -> tuple[dict, dict]:
    steps = [s for s in parse(d / "server.log") if s["kind"] == "STEP"]
    t = [s["t"] for s in steps]
    delta = [t[i + 1] - t[i] for i in range(len(t) - 1)] + [None]
    win = windows(json.loads((d / "events.json").read_text()))
    full, iso = {}, {}
    for (phase, spec), w in win.items():
        idx = [i for i, s in enumerate(steps) if w["start"] <= s["wall"] <= w["end"]]
        if phase == "FULL":
            n = int(spec.split("=")[1])
            seg = [i for i in idx if steps[i]["reqs"] == n and steps[i]["maxq"] == 1]
            runs, cur = [], []
            for i in seg:
                if cur and i != cur[-1] + 1:
                    runs.append(cur)
                    cur = []
                cur.append(i)
            if cur:
                runs.append(cur)
            vals = []
            for r in runs:
                core = r[TRIM:len(r) - TRIM]
                vals += [delta[i] for i in core if delta[i] is not None and (i + 1) in r]
            full[n] = {"deltas": vals, "mode": steps[seg[len(seg) // 2]]["mode"] if seg else None,
                       "padded": steps[seg[len(seg) // 2]]["padded"] if seg else None}
        else:
            dd, pp = (int(x.split("=")[1]) for x in spec.split())
            # Amendment 2: with a token budget, a probe with dd + pp > budget is chunked and its
            # first chunk carries budget - dd prefill tokens (the rest runs in the next step).
            first = min(pp, budget - dd) if budget else pp
            probes = [i for i in idx if steps[i]["maxq"] == first and steps[i]["reqs"] == dd + 1]
            base = [delta[i] for i in idx
                    if steps[i]["reqs"] == dd and steps[i]["maxq"] == 1
                    and i > 0 and steps[i - 1]["reqs"] == dd and steps[i - 1]["maxq"] == 1
                    and i + 1 < len(steps) and steps[i + 1]["reqs"] == dd and steps[i + 1]["maxq"] == 1
                    and delta[i] is not None]
            lagged = {L: [delta[i + L] for i in probes if i + L < len(delta) and delta[i + L] is not None]
                      for L in (0, 1, 2)}
            iso[(phase, dd, pp)] = {"probe_steps": len(probes), "baseline": base, "lagged": lagged,
                                    "toks": dd + first, "chunked": first != pp,
                                    "mode": steps[probes[0]]["mode"] if probes else None,
                                    "padded": steps[probes[0]]["padded"] if probes else None}
    return full, iso


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--chunk-budget", type=int, default=None,
                    help="amendment 2: match the first chunk of probes split by --max-num-batched-tokens")
    a = ap.parse_args()
    lcs, excluded = [], {}
    for p in sorted(Path(a.run_dir).iterdir()):
        if not (p / "events.json").exists():
            continue
        sm = json.loads((p / "summary.json").read_text())
        pre = sm["metric_delta"].get("vllm:num_preemptions_total")
        if not sm["valid"] or pre != 0:
            excluded[p.name] = {"valid": sm["valid"], "reasons": sm["invalid_reasons"], "preemptions": pre}
            continue
        lcs.append(p)
    data = {p.name: lifecycle_cells(p, None, a.chunk_budget) for p in lcs}

    # lag rule on EAGER d=4 p=2048
    elev = {L: [] for L in (0, 1, 2)}
    for _, (_, iso) in data.items():
        c = iso.get(("EAGER", 4, 2048))
        if not c or not c["baseline"]:
            continue
        b = statistics.median(c["baseline"])
        for L in (0, 1, 2):
            if c["lagged"][L]:
                elev[L].append(statistics.median(c["lagged"][L]) - b)
    lag_med = {L: (statistics.median(v) if v else None) for L, v in elev.items()}
    LAG = max((L for L in lag_med if lag_med[L] is not None), key=lambda L: lag_med[L])

    out = {"lifecycles": [p.name for p in lcs], "excluded": excluded,
           "lag_rule": {"median_elevation_s": lag_med, "chosen_lag": LAG}, "full": {}, "iso": {}}
    # FULL
    for grid in GRIDS:
        names = [n for n in data if n.startswith(grid)]
        for n in range(1, 17):
            per = [statistics.median(data[x][0][n]["deltas"]) for x in names
                   if n in data[x][0] and data[x][0][n]["deltas"]]
            pooled = [v for x in names if n in data[x][0] for v in data[x][0][n]["deltas"]]
            modes = {data[x][0][n]["mode"] for x in names if n in data[x][0]}
            padded = {data[x][0][n]["padded"] for x in names if n in data[x][0]}
            out["full"][f"{grid}/{n}"] = {
                "grid": grid, "n": n, "mode": sorted(m for m in modes if m), "padded": sorted(p for p in padded if p),
                "median_ms": 1e3 * statistics.median(pooled) if pooled else None,
                "iqr_ms": [1e3 * q(pooled, 25), 1e3 * q(pooled, 75)] if pooled else None,
                "count": len(pooled),
                "per_lifecycle_median_ms": [1e3 * v for v in per],
                "between_lifecycle_range_ms": 1e3 * (max(per) - min(per)) if len(per) > 1 else None}
    # isolated MIXED / EAGER
    keys = sorted({k for _, (_, iso) in data.items() for k in iso})
    for k in keys:
        for grid in GRIDS:
            names = [n for n in data if n.startswith(grid) and k in data[n][1]]
            if not names:
                continue
            probe = [v for x in names for v in data[x][1][k]["lagged"][LAG]]
            base = [v for x in names for v in data[x][1][k]["baseline"]]
            per = [statistics.median(data[x][1][k]["lagged"][LAG]) for x in names if data[x][1][k]["lagged"][LAG]]
            out["iso"][f"{grid}/{k[0]}/d{k[1]}/p{k[2]}"] = {
                "grid": grid, "phase": k[0], "d": k[1], "p": k[2], "toks": data[names[0]][1][k]["toks"],
                "chunked": data[names[0]][1][k]["chunked"],
                "mode": sorted({data[x][1][k]["mode"] for x in names} - {None}),
                "padded": sorted({data[x][1][k]["padded"] for x in names} - {None}),
                "probe_steps": sum(data[x][1][k]["probe_steps"] for x in names),
                "step_median_ms": 1e3 * statistics.median(probe) if probe else None,
                "step_iqr_ms": [1e3 * q(probe, 25), 1e3 * q(probe, 75)] if probe else None,
                "decode_baseline_median_ms": 1e3 * statistics.median(base) if base else None,
                "increment_ms": (1e3 * (statistics.median(probe) - statistics.median(base))
                                 if probe and base else None),
                "per_lifecycle_median_ms": [1e3 * v for v in per],
                "between_lifecycle_range_ms": 1e3 * (max(per) - min(per)) if len(per) > 1 else None}
    # FULL fit t = F[b] + g*n on G1 and G3 FULL-mode cells (per-lifecycle medians as points)
    rows, ys = [], []
    buckets = sorted({1, 2, 4, 8, 16} | set(range(1, 17)))
    for grid in ("G1", "G3"):
        for n in range(1, 17):
            c = out["full"][f"{grid}/{n}"]
            if c["mode"] != ["FULL"] or not c["padded"]:
                continue
            b = c["padded"][0]
            for v in c["per_lifecycle_median_ms"]:
                x = [0.0] * (len(buckets) + 1)
                x[buckets.index(b)] = 1.0
                x[-1] = float(n)
                rows.append(x)
                ys.append(v)
    if rows:
        X, Y = np.array(rows), np.array(ys)
        used = X.any(axis=0)
        coef, *_ = np.linalg.lstsq(X[:, used], Y, rcond=None)
        names = [f"F[{b}]" for b in buckets] + ["g_per_request"]
        fit = dict(zip([n for n, u in zip(names, used) if u], coef.tolist()))
        resid = Y - X[:, used] @ coef
        out["full_fit_ms"] = {"coef": fit, "max_abs_resid_ms": float(np.max(np.abs(resid))), "points": len(ys)}
    Path(a.out).write_text(json.dumps(out, indent=1))

    L = ["## FULL (decode-only) — step 시간 중앙값 ms [IQR], 수명주기별 중앙값 범위", "",
         "| n | G1 mode/pad | G1 | G2 mode/pad | G2 | G3 mode/pad | G3 |", "|---|---|---|---|---|---|---|"]
    for n in range(1, 17):
        cells = []
        for g in GRIDS:
            c = out["full"][f"{g}/{n}"]
            if c["median_ms"] is None:
                cells += ["—", "—"]
                continue
            rng = c["between_lifecycle_range_ms"]
            cells += [f"{'/'.join(c['mode'])} {c['padded']}",
                      f"{c['median_ms']:.3f} [{c['iqr_ms'][0]:.3f}, {c['iqr_ms'][1]:.3f}] Δlc {rng:.3f}" if rng is not None
                      else f"{c['median_ms']:.3f}"]
        L.append(f"| {n} | " + " | ".join(cells) + " |")
    L += ["", f"lag rule: median elevation (ms) by lag {{L: v*1e3}} = "
          f"{ {k: (None if v is None else round(v * 1e3, 3)) for k, v in lag_med.items()} } → L = {LAG}", "",
          "## MIXED / EAGER — 고립 step 시간(lag L) 중앙값 ms, decode 기준선, 증분", "",
          "| grid | phase | d | p | toks | mode/pad | steps | step | baseline | increment | Δlc |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in out["iso"].items():
        if c["step_median_ms"] is None:
            continue
        rng = c["between_lifecycle_range_ms"]
        L.append(f"| {c['grid']} | {c['phase']} | {c['d']} | {c['p']} | {c['toks']} | {'/'.join(c['mode'])} {c['padded']} | "
                 f"{c['probe_steps']} | {c['step_median_ms']:.3f} | {c['decode_baseline_median_ms']:.3f} | "
                 f"{c['increment_ms']:.3f} | {'' if rng is None else f'{rng:.3f}'} |")
    if "full_fit_ms" in out:
        L += ["", f"FULL fit t = F[b] + g·n (ms): {json.dumps({k: round(v, 4) for k, v in out['full_fit_ms']['coef'].items()})}, "
              f"max |resid| {out['full_fit_ms']['max_abs_resid_ms']:.4f}, points {out['full_fit_ms']['points']}"]
    Path(a.md).write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
