#!/usr/bin/env python3
"""Context-length decode step cost (TASK97, CTXCOST_DESIGN.md). Parameter
measurement: no verdict; reproducibility is reported.

Attribution is TASK91's: request R's ``[BUCKET]`` lines between its ALLOC and
FREE are its decode steps; the step at R's k-th bucket line lasts
``t[k+1] - t[k]`` of R's streaming chunks and is clean when no ALLOC lies
between R's (k-1)-th and k-th bucket lines. A step's ``sum_ctx`` is the sum,
over every request running in it, of (prompt tokens + tokens generated so far
+ 1); a step is used only when every running request is attributed.

Fits per artifact, on 64-token mean-context bins (median step time per
(n, bin) with at least 30 samples):

* F1 ``t = f(b) + beta n + c sum_ctx``
* F2 ``t = f(b) + beta n + c_b sum_ctx``
* F3 ``t = f(b) + beta n + c b mean_ctx``

TASK92's short-context ``op-decode`` lifecycles (prompt 128) are included.
Then the operational-ratio check: the fitted cost applied to the decode-step
structure (b, n, sum_ctx) of the TASK82/87/95 multi-turn runs and of TASK92's
``op-prefill-mt`` -- step times of those runs are not read.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import statistics
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import main_analyze as A  # noqa: E402
import model_v0_retro as R  # noqa: E402
import mt_predict as P  # noqa: E402
from mt_check import CONFIGS  # noqa: E402

REPO = HERE.parents[2]
S3 = REPO / "results/npu/stage3"
STEPCOST_RUN = S3 / "20261001-stepcost-op"
MT_RUNS = {"TASK82": (S3 / "20260930-main", (6, 8, 10, 12)), "TASK87": (S3 / "20261001-hiload", (14, 16)),
           "TASK95": (S3 / "20261002-simblind", (13, 17, 20))}
ARTS = ("BASE", "TUNED")
BIN = 64
MIN_SAMPLES = 30


def steps_of(run: Path, tag: str, eval_s: float | None = None) -> list[dict]:
    """Every attributable decode step in the evaluation window:
    {b, n, sum_ctx, interval (s, from one running request), clean}."""
    cfg = tag.split(".")[0]
    desc = P.descriptor(CONFIGS[cfg][1], CONFIGS[cfg][2])
    ev = R.parse_log(run / f"server-{tag}.log")
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0 = win["warmup_end_s"]
    w1 = w0 + (eval_s if eval_s is not None else float(win["eval_s"]))
    tok = {}
    with gzip.open(probe / f"tokens.{tag}.jsonl.gz", "rt") as fh:
        for l in fh:
            x = json.loads(l)
            tok[x["request_id"]] = x["t"]
    pos_a, pos_f = {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            pos_a.setdefault(e[1], i)
        elif e[0] == "free":
            pos_f.setdefault(e[1], i)
    sid = {}
    for s in pos_a:
        sid.setdefault(s.rsplit("-", 2)[0], s)
    ctx = defaultdict(int)
    cnt = defaultdict(int)
    iv = {}
    for r in rows:
        s = sid.get(r["request_id"])
        t = tok.get(r["request_id"], [])
        if s is None or s not in pos_f:
            continue
        bpos = [i for i in range(pos_a[s], pos_f[s]) if ev[i][0] == "bucket"]
        if len(bpos) != r["completion_tokens"] - 1 or len(t) != r["completion_tokens"]:
            continue
        for k, i in enumerate(bpos):
            ctx[i] += r["prompt_tokens"] + k + 1
            cnt[i] += 1
            if k >= 1 and i not in iv and w0 <= r["sent_s"] < w1:
                clean = not any(e[0] == "alloc" for e in ev[bpos[k - 1] + 1:i])
                iv[i] = (t[k + 1] - t[k], clean, 0.5 * (t[k] + t[k + 1]))
    out = []
    for i, (dt, clean, at) in iv.items():
        n = ev[i][1]
        if cnt[i] != n or not (w0 <= at < w1):
            continue
        out.append({"b": desc.bucket_for(n), "n": n, "sum_ctx": ctx[i], "interval": dt, "clean": clean})
    return out


def fit(points, form: str):
    """points: (b, n, sum_ctx, t). Returns params, design function and residuals."""
    buckets = sorted({p[0] for p in points})

    def row(b, n, s):
        x = [1.0 if b == bb else 0.0 for bb in buckets] + [n]
        if form == "F1":
            x.append(s)
        elif form == "F2":
            x += [s if b == bb else 0.0 for bb in buckets]
        elif form == "F3":
            x.append(b * s / n)
        return x

    X = np.array([row(b, n, s) for b, n, s, _ in points])
    y = np.array([t for *_, t in points])
    sol, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ sol
    return sol, (lambda b, n, s: float(np.dot(row(b, n, s), sol))), res, buckets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    use, invalid = {}, []
    for d in sorted((a.run / "probe").iterdir()):
        tag = d.name
        lc = (d / "lifecycle.txt").read_text()
        win = json.loads((d / f"windows.{tag}.json").read_text())
        if "runner_exit=0" not in lc or win["stopped_by"] != "window" or win["exhausted_slots"]:
            invalid.append(tag)
            continue
        use.setdefault(tag.replace(".retry1", ""), tag)
    per_cell = defaultdict(list)          # (cfg, n, L, rep) -> clean steps
    stats = {"lifecycles": 0, "steps": 0}
    for base, tag in sorted(use.items()):
        cfg, pid = tag.split(".")[0], tag.split(".")[1]
        L = int(pid.split("-L")[1])
        n = int(pid.split("-n")[1].split("-")[0])
        st = [s for s in steps_of(a.run, tag) if s["clean"]]
        stats["lifecycles"] += 1
        stats["steps"] += len(st)
        per_cell[(cfg, n, L, ".rep2" in base)].extend(st)
    short = defaultdict(list)             # TASK92 op-decode, prompt 128
    for d in sorted((STEPCOST_RUN / "probe").iterdir()):
        tag = d.name
        cfg = tag.split(".")[0]
        if cfg not in ARTS or "op-decode" not in tag:
            continue
        win = json.loads((d / f"windows.{tag}.json").read_text())
        if "runner_exit=0" not in (d / "lifecycle.txt").read_text() or win["exhausted_slots"]:
            continue
        short[cfg].extend(s for s in steps_of(STEPCOST_RUN, tag) if s["clean"])
    out = {"stats": stats, "invalid": invalid, "artifacts": {}}
    for cfg in ARTS:
        ctrl = P.descriptor(CONFIGS[cfg][1], CONFIGS[cfg][2])
        table = []
        for (c, n, L, rep), st in sorted(per_cell.items()):
            if c != cfg or rep:
                continue
            ts = [s["interval"] for s in st if s["n"] == n]
            if not ts:
                continue
            q = [[] for _ in range(4)]
            for s in st:
                if s["n"] == n:
                    k = s["sum_ctx"] / n - L
                    q[min(3, max(0, int(k // BIN)))].append(s["interval"])
            table.append({"n": n, "L": L, "b": ctrl.bucket_for(n), "samples": len(ts),
                          "median_ms": statistics.median(ts) * 1e3,
                          "controlled_ms": ctrl.step_time_s(n) * 1e3,
                          "ratio_to_controlled": statistics.median(ts) / ctrl.step_time_s(n),
                          "k_quarter_median_ms": [statistics.median(x) * 1e3 if x else None for x in q]})
        groups = defaultdict(list)
        for (c, n, L, rep), st in per_cell.items():
            if c != cfg or rep:
                continue
            for s in st:
                groups[(s["b"], s["n"], round(s["sum_ctx"] / s["n"] / BIN))].append(s)
        for s in short[cfg]:
            groups[(s["b"], s["n"], round(s["sum_ctx"] / s["n"] / BIN))].append(s)
        points = [(b, n, statistics.median(x["sum_ctx"] for x in g), statistics.median(x["interval"] for x in g))
                  for (b, n, _), g in groups.items() if len(g) >= MIN_SAMPLES]
        fits = {}
        for form in ("F1", "F2", "F3"):
            sol, fn, res, buckets = fit(points, form)
            nb = len(buckets)
            fits[form] = {"f_by_bucket_ms": {int(bb): float(sol[i]) * 1e3 for i, bb in enumerate(buckets)},
                          "beta_ms": float(sol[nb]) * 1e3,
                          "c_ms_per_token": [float(x) * 1e3 for x in sol[nb + 1:]],
                          "rms_ms": float(np.sqrt(np.mean(res ** 2))) * 1e3,
                          "max_abs_ms": float(np.max(np.abs(res))) * 1e3, "points": len(points)}
            fits[form]["_fn"] = fn
        reprod = {}
        for (c, n, L, rep), st in per_cell.items():
            if c == cfg and rep:
                x0 = statistics.median(s["interval"] for s in per_cell[(c, n, L, False)] if s["n"] == n)
                x1 = statistics.median(s["interval"] for s in st if s["n"] == n)
                reprod[f"n{n}-L{L}"] = x1 / x0 - 1
        out["artifacts"][cfg] = {"table": table, "fits": fits, "reproducibility": reprod,
                                 "short_ctx_points": len(short[cfg])}
    # operational-ratio check: fitted cost / controlled cost on the runs' step structure
    check = {}
    for cfg in ARTS:
        ctrl = P.descriptor(CONFIGS[cfg][1], CONFIGS[cfg][2])
        fns = {f: out["artifacts"][cfg]["fits"][f]["_fn"] for f in ("F1", "F2", "F3")}
        for task, (run, ns) in list(MT_RUNS.items()) + [("TASK92_prefill_mt", (STEPCOST_RUN, None))]:
            if ns is None:
                tags = [f"{cfg}.op-prefill-mt"]
            else:
                tags = [A.chosen_tag(run, cfg, n, r)[0] for n in ns for r in range(5)]
            cells = defaultdict(lambda: defaultdict(list))
            for tag in tags:
                if tag is None:
                    continue
                for s in steps_of(run, tag):
                    if s["clean"]:
                        for f, fn in fns.items():
                            cells[f][(s["b"], s["n"])] += [fn(s["b"], s["n"], s["sum_ctx"])] * s["n"]
            res = {}
            for f, by in cells.items():
                w = sum(len(v) for v in by.values())
                res[f] = sum(statistics.median(v) / ctrl.step_time_s(n) * len(v) for (b, n), v in by.items()) / w
            res["samples"] = sum(len(v) for v in cells["F1"].values())
            check.setdefault(cfg, {})[task] = res
    out["operational_ratio_check"] = check
    for cfg in ARTS:
        for f in out["artifacts"][cfg]["fits"].values():
            f.pop("_fn")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"stats": stats, "invalid": invalid}))
    for cfg in ARTS:
        e = out["artifacts"][cfg]
        print(cfg, "short-ctx steps", e["short_ctx_points"])
        for r in e["table"]:
            print(f"  n{r['n']:>2} L{r['L']:>5} b{r['b']:>2} {r['median_ms']:7.3f} ms ctrl {r['controlled_ms']:7.3f} "
                  f"x{r['ratio_to_controlled']:.3f}  quarters {[round(x, 2) if x else None for x in r['k_quarter_median_ms']]}"
                  f"  ({r['samples']})")
        for f, v in e["fits"].items():
            print(f"  {f}: f {({k: round(x, 3) for k, x in v['f_by_bucket_ms'].items()})} beta {v['beta_ms']:.4f} "
                  f"c {[round(x * 1e3, 4) for x in v['c_ms_per_token']]} us/token rms {v['rms_ms']:.3f} max {v['max_abs_ms']:.3f}")
        print("  reproducibility", {k: round(v, 4) for k, v in e["reproducibility"].items()})
        print("  ratio check", {t: {k: round(x, 4) if isinstance(x, float) else x for k, x in v.items()}
                                for t, v in check[cfg].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
