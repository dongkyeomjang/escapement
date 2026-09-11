#!/usr/bin/env python3
"""Separate a recompile effect from run-to-run variation in decode step cost.

TASK55 found a 0.29 ms difference in C_model(2) between two artifacts that
share bucket 2, but it measured each artifact once, so an artifact effect and
the variation between server lifecycles were confounded. Here every
(artifact, bucket) cell is measured in five rounds, each on a fresh server.
The null distribution is built from the rounds of one artifact against each
other -- same artifact, same bucket, different lifecycle -- and differences
between artifacts are judged against it, bucket by bucket.

Subcommands:
  check     gate one lifecycle (called by the driver right after it ends)
  selftest  confirm the parser reproduces TASK55's published C_model values
  analyze   build the raw table, the null distribution, and rules R1 and R2

Preregistered in docs/research/RECOMPILE_VARIANCE_PREREG.md.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import statistics
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_step_cost import BUCKET_RE, metrics_p50  # noqa: E402

ARTIFACTS = ("A1", "A2", "A3")
BUCKETS = (1, 2, 4, 8)
ROUNDS = (0, 1, 2, 3, 4)
#: Comparisons: R1 is the same-configuration recompile, R2 the grid change.
COMPARISONS = {"R1": [("A1", "A3")], "R2": [("A1", "A2"), ("A2", "A3")]}
#: Float guard for "|delta| <= q". Inputs are printed to 0.01 ms.
EPS = 1e-9

#: TASK55 observation 2, C_model p50 in ms, for the parser self-test.
TASK55_MODEL = {("mb", 1): 9.49, ("mb", 2): 10.37, ("mb", 4): 10.28, ("mb", 8): 12.28,
                ("mb6", 1): 9.52, ("mb6", 2): 10.08, ("mb6", 4): 10.37,
                ("mb6", 6): 11.15, ("mb6", 8): 12.36}


def read_cell(log_path: Path, probe_path: Path, level: int) -> dict:
    log = log_path.read_text(errors="replace")
    probe = json.loads(probe_path.read_text())
    pairs = [(int(a), int(b)) for a, b in BUCKET_RE.findall(log)]
    reqs = probe["requests"]
    model, sampler = metrics_p50(log, "MODEL"), metrics_p50(log, "SAMPLER")
    return {
        "level": level,
        "model_p50_ms": model,
        "sampler_p50_ms": sampler,
        "fixed_ms": (model + sampler) if model is not None and sampler is not None else None,
        "median_itl_ms": statistics.median(probe["itl_samples"]) * 1000,
        "client_mean_itl_ms": statistics.fmean(probe["itl_samples"]) * 1000,
        "server_mean_itl_ms": (probe["server_mean_itl_s"] or 0) * 1000,
        "step_lines": len(pairs),
        "actuals": sorted({a for a, _ in pairs}),
        "buckets": sorted({b for _, b in pairs}),
        "statuses": sorted({r["status"] for r in reqs}),
        "chunk_counts": sorted({r["chunk_count"] for r in reqs}),
    }


def gate(cell: dict, expected_bucket: int) -> dict:
    g1 = cell["statuses"] == [200] and cell["chunk_counts"] == [512]
    g2 = (cell["step_lines"] == 511 and cell["actuals"] == [cell["level"]]
          and cell["buckets"] == [expected_bucket])
    metrics = cell["model_p50_ms"] is not None and cell["sampler_p50_ms"] is not None
    return {"G1": g1, "G2": g2, "metrics_parsed": metrics, "ok": g1 and g2 and metrics}


def cmd_check(args) -> int:
    try:
        cell = read_cell(args.log, args.probe, args.level)
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({"ok": False, "error": repr(e)}))
        return 1
    g = gate(cell, args.level)        # levels 1,2,4,8 map to themselves on every artifact
    print(json.dumps({**g, "model_p50_ms": cell["model_p50_ms"],
                      "sampler_p50_ms": cell["sampler_p50_ms"],
                      "step_lines": cell["step_lines"], "actuals": cell["actuals"],
                      "buckets": cell["buckets"], "statuses": cell["statuses"],
                      "chunk_counts": cell["chunk_counts"]}))
    return 0 if g["ok"] else 1


def cmd_selftest(args) -> int:
    bad = 0
    for (grid, level), want in TASK55_MODEL.items():
        cell = read_cell(args.task55_run / f"server-{grid}.L{level}.log",
                         args.task55_run / "probe" / f"decode_cost.{grid}.L{level}.json", level)
        got = cell["model_p50_ms"]
        ok = got == want and gate(cell, level)["ok"]
        bad += not ok
        print(f"{grid}.L{level}: C_model {got} (TASK55 {want}) gates {gate(cell, level)} "
              f"{'ok' if ok else 'MISMATCH'}")
    print(f"selftest: {len(TASK55_MODEL) - bad}/{len(TASK55_MODEL)} match")
    return 1 if bad else 0


def quantiles(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    return {"n": int(arr.size), "median": float(np.percentile(arr, 50, method="linear")),
            "q90": float(np.percentile(arr, 90, method="linear")),
            "q95": float(np.percentile(arr, 95, method="linear")),
            "max": float(arr.max()), "min": float(arr.min())}


def cmd_analyze(args) -> int:
    run = args.run
    raw, table = [], {}
    for a in ARTIFACTS:
        for r in ROUNDS:
            for b in BUCKETS:
                tag = f"{a}.r{r}.L{b}"
                row = {"artifact": a, "round": r, "bucket": b, "tag": tag,
                       "launched_at": _read(run / f"{tag}-launch.txt"),
                       "rerun": tag in _lines(run / "reruns.txt"),
                       "invalid_marker": (run / f"invalid.{tag}").exists()}
                log, probe = run / f"server-{tag}.log", run / "probe" / f"decode_cost.{tag}.json"
                if log.exists() and probe.exists() and not row["invalid_marker"]:
                    cell = read_cell(log, probe, b)
                    row.update(cell)
                    row.update(gate(cell, b))
                else:
                    row["ok"] = False
                raw.append(row)
                if row["ok"]:
                    table[(a, r, b)] = row["model_p50_ms"]

    null, cells = {}, {}
    for b in BUCKETS:
        deltas = []
        for a in ARTIFACTS:
            vals = [table[(a, r, b)] for r in ROUNDS if (a, r, b) in table]
            cells[(a, b)] = {"values": vals, "n": len(vals),
                             "median": statistics.median(vals) if vals else None,
                             "complete": len(vals) == len(ROUNDS)}
            deltas += [abs(x - y) for x, y in itertools.combinations(vals, 2)]
        null[b] = {**quantiles(deltas), "pairs": deltas,
                   "complete": all(cells[(a, b)]["complete"] for a in ARTIFACTS)}

    rules = {}
    for rule, pairs in COMPARISONS.items():
        rules[rule] = []
        for x, y in pairs:
            rows = []
            for b in BUCKETS:
                mx, my = cells[(x, b)]["median"], cells[(y, b)]["median"]
                complete = cells[(x, b)]["complete"] and cells[(y, b)]["complete"] and null[b]["complete"]
                d = abs(mx - my) if mx is not None and my is not None else None
                q95, q90 = null[b]["q95"], null[b]["q90"]
                verdict = ("INCOMPLETE" if not complete or d is None
                           else "WITHIN" if d <= q95 + EPS else "OUTSIDE")
                rows.append({"bucket": b, "median_x": mx, "median_y": my, "abs_delta": d,
                             "q95": q95, "q90": q90, "verdict_q95": verdict,
                             "within_q90": (d <= q90 + EPS) if d is not None else None})
            verdicts = [r["verdict_q95"] for r in rows]
            overall = ("구별되지 않음" if all(v == "WITHIN" for v in verdicts)
                       else "구별됨" if "OUTSIDE" in verdicts else "판정 불가")
            rules[rule].append({"x": x, "y": y, "buckets": rows, "overall": overall,
                                "outside": [r["bucket"] for r in rows if r["verdict_q95"] == "OUTSIDE"]})

    out = {"raw": raw,
           "cells": {f"{a}.b{b}": c for (a, b), c in cells.items()},
           "null": {f"b{b}": v for b, v in null.items()},
           "rules": rules,
           "counts": {"lifecycles_ok": len(table), "expected": len(ARTIFACTS) * len(ROUNDS) * len(BUCKETS),
                      "reruns": _lines(run / "reruns.txt")}}
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    _print_tables(out)
    return 0


def _read(p: Path) -> str | None:
    return p.read_text().strip() if p.exists() else None


def _lines(p: Path) -> list[str]:
    return p.read_text().split() if p.exists() else []


def _print_tables(out: dict) -> None:
    print("## 원자료 C_model p50 (ms) — 회차 × artifact × bucket")
    print("| artifact | 회차 | b1 | b2 | b4 | b8 |")
    print("|---|---|---|---|---|---|")
    by = {(r["artifact"], r["round"], r["bucket"]): r for r in out["raw"]}
    for a in ARTIFACTS:
        for rd in ROUNDS:
            vals = []
            for b in BUCKETS:
                r = by[(a, rd, b)]
                v = r.get("model_p50_ms")
                vals.append(("INVALID" if not r["ok"] else f"{v:.2f}") + (" (재)" if r["rerun"] else ""))
            print(f"| {a} | r{rd} | " + " | ".join(vals) + " |")
    print("\n## 귀무 분포 (같은 artifact·같은 bucket의 회차 쌍 |Δ|, bucket별 30쌍)")
    print("| bucket | n | 중앙값 | q90 | q95 | 최대 |")
    print("|---|---|---|---|---|---|")
    for b in BUCKETS:
        n = out["null"][f"b{b}"]
        print(f"| {b} | {n['n']} | {n['median']:.4f} | {n['q90']:.4f} | {n['q95']:.4f} | {n['max']:.4f} |")
    print("\n## 판정 통계량과 규칙")
    for rule, comps in out["rules"].items():
        for c in comps:
            print(f"\n{rule} |Δ({c['x']},{c['y']})| — 종합: {c['overall']}")
            print("| bucket | 중앙값 x | 중앙값 y | |Δ| | q95 | q95 판정 | q90 이내 |")
            print("|---|---|---|---|---|---|---|")
            for r in c["buckets"]:
                d = "—" if r["abs_delta"] is None else f"{r['abs_delta']:.4f}"
                print(f"| {r['bucket']} | {r['median_x']} | {r['median_y']} | {d} | "
                      f"{r['q95']:.4f} | {r['verdict_q95']} | {r['within_q90']} |")


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--log", type=Path, required=True)
    c.add_argument("--probe", type=Path, required=True)
    c.add_argument("--level", type=int, required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--task55-run", type=Path,
                   default=Path("results/npu/stage2/20260908-151119-step-cost"))
    a = sub.add_parser("analyze")
    a.add_argument("--run", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    return {"check": cmd_check, "selftest": cmd_selftest, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
