#!/usr/bin/env python3
"""Observed waiting-queue depth of the NPU multi-turn lifecycles (directive 09
§2.5, figure (d)). Read-only over existing logs; nothing is simulated.

Definition, per decode step inside the 120 s evaluation window:

    Q = (requests in flight at the client) - (requests in the step)

* the step's request count is its ``[BUCKET] request_nums`` (server log);
* its time is placed on the client clock through any request R that the step
  belongs to (TASK91 attribution: R's ``[BUCKET]`` lines between its ALLOC and
  FREE are its decode steps; step j of R lies between R's streaming chunks j
  and j + 1, so the step is stamped at their midpoint);
* in flight = ``sent_s <= t < done_s`` from the client request records.

Prefill is exclusive on this substrate, so no request is mid-prefill during a
decode step; a request counted in flight but not in the step is waiting for
admission (or, for a few ms, in transit / finishing its response). Reported
per lifecycle and pooled per cell (step-weighted): mean Q, P(Q > 0), and the
share of steps with Q < 0 (clock-placement error check).
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import gzip
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
S3 = REPO / "experiments/npu/stage3"
sys.path.insert(0, str(S3))

import main_analyze as A  # noqa: E402
import model_v0_retro as R  # noqa: E402

RUNS = {  # run directory, N values, configurations, source TASK
    "TASK82": (REPO / "results/npu/stage3/20260930-main", (6, 8, 10, 12), ("BASE", "BATCHONLY", "TUNED")),
    "TASK87": (REPO / "results/npu/stage3/20261001-hiload", (14, 16), ("BASE", "BATCHONLY", "TUNED")),
    "TASK95": (REPO / "results/npu/stage3/20261002-simblind", (13, 17, 20), ("BASE", "BATCHONLY", "TUNED")),
    "TASK102": (REPO / "results/npu/stage3/20261002-ctxblind", (15, 18), ("BASE", "BATCHONLY", "TUNED")),
}
REPS = range(5)
EXTRA = [("TASK82", 8, "DP", range(10))]   # TASK82 §5.4: DP grid at N = 8, 10 replicates


def lifecycle(run: Path, tag: str) -> dict:
    ev = R.parse_log(run / f"server-{tag}.log")
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0 = win["warmup_end_s"]
    w1 = w0 + win["eval_s"]
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
    stamp: dict[int, float] = {}
    for r in rows:
        s = sid.get(r["request_id"])
        t = tok.get(r["request_id"], [])
        if s is None or s not in pos_f:
            continue
        bpos = [i for i in range(pos_a[s], pos_f[s]) if ev[i][0] == "bucket"]
        if len(bpos) != r["completion_tokens"] - 1 or len(t) != r["completion_tokens"]:
            continue
        for j, i in enumerate(bpos):
            stamp.setdefault(i, 0.5 * (t[j] + t[j + 1]))
    sent = sorted(r["sent_s"] for r in rows if r["status"] == 200)
    done = sorted(r["done_s"] for r in rows if r["status"] == 200)
    qs = []
    for i, t in stamp.items():
        if not (w0 <= t < w1):
            continue
        inflight = bisect_right(sent, t) - bisect_right(done, t)
        qs.append(inflight - ev[i][1])
    return {"steps": len(qs), "mean_q": statistics.mean(qs), "p_q_gt0": sum(q > 0 for q in qs) / len(qs),
            "share_q_lt0": sum(q < 0 for q in qs) / len(qs), "sum_q": sum(qs),
            "n_q_gt0": sum(q > 0 for q in qs), "n_q_lt0": sum(q < 0 for q in qs)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    out = {"definition": "Q = client in-flight requests - [BUCKET] request_nums, per decode step "
                         "in the evaluation window; step-weighted", "cells": {}}
    cells = [(task, run, n, cfg, REPS) for task, (run, ns, cfgs) in RUNS.items() for n in ns for cfg in cfgs]
    cells += [(task, RUNS[task][0], n, cfg, reps) for task, n, cfg, reps in EXTRA]
    for task, run, n, cfg, reps in cells:
        per = {}
        for r in reps:
            tag, _ = A.chosen_tag(run, cfg, n, r)
            if tag is not None:
                per[tag] = lifecycle(run, tag)
        steps = sum(p["steps"] for p in per.values())
        out["cells"][f"{cfg}.n{n}"] = {
            "source": task, "run": str(run.relative_to(REPO)), "lifecycles": len(per), "steps": steps,
            "mean_q": sum(p["sum_q"] for p in per.values()) / steps,
            "p_q_gt0": sum(p["n_q_gt0"] for p in per.values()) / steps,
            "share_q_lt0": sum(p["n_q_lt0"] for p in per.values()) / steps,
            "per_lifecycle": per}
        c = out["cells"][f"{cfg}.n{n}"]
        print(task, f"{cfg}.n{n}", c["lifecycles"], steps, round(c["mean_q"], 3),
              round(c["p_q_gt0"], 3), round(c["share_q_lt0"], 4), flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
