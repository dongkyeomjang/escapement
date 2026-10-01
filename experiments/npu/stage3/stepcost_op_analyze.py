#!/usr/bin/env python3
"""Operational step costs from the controlled-load lifecycles (TASK92,
STEPCOST_OP_DESIGN.md). Parameter measurement: no verdict; reproducibility is
reported.

Attribution is TASK91's (``step_audit.lifecycle``) unchanged. Fits, per
artifact, the cost forms the descriptor already uses:

* decode: ``t(n) = F[b(n)] + beta * n`` (least squares on per-``n`` medians of
  clean decode steps with at least 50 samples; the intercept is folded into
  ``F``);
* exclusive prefill: ``ceil(c / 128) * (a + d * c)`` (least squares on every
  one-prefill interval minus the artifact's median clean step at that
  ``(b, n)`` from its decode lifecycles).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_predict as P  # noqa: E402
import step_audit as SA  # noqa: E402
from mt_check import CONFIGS  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402


def validity(run: Path, tag: str) -> list[str]:
    bad = []
    lc = (run / "probe" / tag / "lifecycle.txt").read_text()
    if "runner_exit=0" not in lc:
        bad.append("runner exit")
    win = json.loads((run / "probe" / tag / f"windows.{tag}.json").read_text())
    if win["stopped_by"] != "window":
        bad.append(f"stopped_by={win['stopped_by']}")
    if win["exhausted_slots"]:
        bad.append("exhausted slots")
    rows = [json.loads(l) for l in (run / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    if any(r["status"] != 200 for r in rows):
        bad.append("http errors")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    tags = sorted(d.name for d in (a.run / "probe").iterdir())
    use, invalid = {}, {}
    for tag in tags:
        base = tag.replace(".retry1", "")
        bad = validity(a.run, tag)
        if bad:
            invalid[tag] = bad
        elif base not in use:
            use[base] = tag
    acc = defaultdict(list)
    pre_all: list = []
    stats = {"requests": 0, "skipped": 0, "lifecycles": 0}
    rep = {}
    for base, tag in sorted(use.items()):
        cfg = tag.split(".")[0]
        local = defaultdict(list)
        pre = []
        SA.lifecycle(a.run, tag, cfg, local, pre, stats)
        stats["lifecycles"] += 1
        if base.endswith(".rep2") or (base.startswith("TUNED.op-decode-n4") or base.startswith("TUNED.op-decode-n8")):
            rep[base] = {f"{k[1]}/{k[2]}": statistics.median(v) for k, v in local.items() if len(v) >= 50}
        if ".rep2" in base:
            continue                        # repeats are for reproducibility only
        for k, v in local.items():
            acc[k].extend(v)
        if "op-prefill" in base:
            pre_all.extend(pre)
    out = {"stats": stats, "invalid": invalid, "artifacts": {}}
    for cfg in ("BASE", "BATCHONLY", "TUNED", "DP"):
        grid, batch = CONFIGS[cfg][1], CONFIGS[cfg][2]
        ctrl = P.descriptor(grid, batch)
        pts = sorted(((k[2], k[1], statistics.median(v), len(v)) for k, v in acc.items()
                      if k[0] == cfg and len(v) >= 50))
        buckets = sorted({b for _, b, _, _ in pts})
        A = np.zeros((len(pts), len(buckets) + 1))
        y = np.zeros(len(pts))
        for i, (n, b, t, _) in enumerate(pts):
            A[i, buckets.index(b)] = 1.0
            A[i, -1] = n
            y[i] = t
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        fixed = {int(b): float(sol[i]) for i, b in enumerate(buckets)}
        beta = float(sol[-1])
        rows = [{"n": n, "b": b, "obs_ms": t * 1e3, "fit_ms": (fixed[b] + beta * n) * 1e3,
                 "controlled_ms": ctrl.step_time_s(n) * 1e3, "obs_over_controlled": t / ctrl.step_time_s(n),
                 "samples": c} for n, b, t, c in pts]
        clean_med = {(k[1], k[2]): statistics.median(v) for k, v in acc.items() if k[0] == cfg}
        samples = []
        for p in pre_all:
            if p["cfg"] != cfg:
                continue
            base_t = clean_med.get((p["b"], p["n"]))
            if base_t is None or p["computed"] <= 0:
                continue
            samples.append((p["computed"], p["interval"] - base_t))
        pf = None
        if samples:
            k = np.array([math.ceil(c / 128) for c, _ in samples], dtype=float)
            c = np.array([c for c, _ in samples], dtype=float)
            yy = np.array([s for _, s in samples])
            M = np.vstack([k, k * c]).T
            (pa, pd), *_ = np.linalg.lstsq(M, yy, rcond=None)
            bins = [(1, 128), (129, 512), (513, 1024), (1025, 2048), (2049, 4096)]
            resid = []
            for lo, hi in bins:
                sel = [(cc, ss) for cc, ss in samples if lo <= cc <= hi]
                if len(sel) < 10:
                    continue
                fit = statistics.median(math.ceil(cc / 128) * (pa + pd * cc) for cc, _ in sel)
                obs = statistics.median(ss for _, ss in sel)
                ctl = statistics.median(D.prefill_cost_model.prefill_s(cc) for cc, _ in sel)
                resid.append({"bin": [lo, hi], "samples": len(sel), "obs_ms": obs * 1e3,
                              "fit_ms": fit * 1e3, "controlled_ms": ctl * 1e3})
            pf = {"per_chunk_s": float(pa), "drift_s_per_token": float(pd), "samples": len(samples),
                  "bins": resid}
        out["artifacts"][cfg] = {"grid": list(grid), "batch": batch,
                                 "decode": {"fixed_s_by_bucket": fixed, "marginal_s_per_request": beta,
                                            "points": rows},
                                 "prefill": pf}
    reprod = {}
    for n in ("n4", "n8"):
        x = rep.get(f"TUNED.op-decode-{n}")
        y2 = rep.get(f"TUNED.op-decode-{n}.rep2")
        if x and y2:
            reprod[n] = {k: y2[k] / x[k] - 1 for k in x if k in y2}
    out["reproducibility"] = reprod
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"stats": stats, "invalid": invalid}, indent=1))
    for cfg, e in out["artifacts"].items():
        d = e["decode"]
        print(cfg, "F", {b: round(v * 1e3, 3) for b, v in d["fixed_s_by_bucket"].items()},
              "beta ms", round(d["marginal_s_per_request"] * 1e3, 4))
        for r in d["points"]:
            print("   n", r["n"], "b", r["b"], round(r["obs_ms"], 3), "fit", round(r["fit_ms"], 3),
                  "ctrl", round(r["controlled_ms"], 3), "x", round(r["obs_over_controlled"], 3), r["samples"])
        if e["prefill"]:
            print("  prefill a", round(e["prefill"]["per_chunk_s"] * 1e3, 3), "ms d", e["prefill"]["drift_s_per_token"],
                  "n", e["prefill"]["samples"])
            for b in e["prefill"]["bins"]:
                print("    ", b)
    print("reproducibility", json.dumps(reprod))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
