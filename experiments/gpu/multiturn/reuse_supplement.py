#!/usr/bin/env python3
"""GPU-host-only reuse values (directive G-09 task B; post_hoc, read-only).

For every lifecycle the GTASK11 / GTASK20 verdicts used (``verdict.json``
``used``), the evaluation-window turn >= 1 requests are read with
``gpu_mt_measure.lifecycle_metrics`` (the verdicts' code path) and, from the
same client rows, the directive's reusable-token definition:

* ``cap`` (verdicts, simulator): ``min(floor((prev prompt + prev generated
  - 1)/16), floor((prompt - 1)/16)) * 16`` -- the largest hit vLLM can give
  (generated tokens cached except the last sampled one; hit <= query - 1);
* ``prefix`` (directive G-09 B1): ``floor(shared/16) * 16`` with ``shared`` =
  the token prefix the prompt shares with the previous turn = previous prompt
  + previous generated tokens (``gpu_mt_runner``: prompt = previous prompt ids
  + previous generated ids + new segment ids; checked per request as
  ``prompt_tokens == prev prompt + prev generated + requested_segment_tokens``).

Per lifecycle and pooled per cell: request-level reuse (hit > 0) with its
denominator, token ratio sum(cached) / sum(reusable) under both definitions,
partial share (0 < cached < reusable) under both. Cell sums are checked
against the verdict (``reuse``, GTASK11 ``token_reuse_ratio`` and partial
share).

usage: reuse_supplement.py --output <json>
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import gpu_mt_measure as M  # noqa: E402

RES = REPO / "results/gpu/multiturn"
SETS = {"GTASK11": (RES / "main/20260930T1411Z", (20, 22, 24, 26)),
        "GTASK20": (RES / "blind/20261002T0655Z", (25, 28))}
CONFIGS = ("BASE", "POOL", "POOL+GRID")
BLOCK = 16


def lifecycle(run: Path) -> dict:
    m = M.lifecycle_metrics(run)
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    details = m["checks"]["details_flag_in_log"]
    prev = {(r["session"], r["turn"]): r for r in rows}
    c = Counter()
    for r in rows:
        if not (w0 <= r["sent_s"] < w1) or r["turn"] == 0:
            continue
        p = prev[(r["session"], r["turn"] - 1)]
        cached = r["cached_tokens"] if r["cached_tokens"] is not None else (0 if details else None)
        if cached is None:
            raise RuntimeError(f"cached unknown {r['request_id']}")
        shared = p["prompt_tokens"] + p["requested_generation_tokens"]
        c["prompt_eq_construction"] += int(r["prompt_tokens"] == shared + r["requested_segment_tokens"])
        cap = min((shared - 1) // BLOCK, (r["prompt_tokens"] - 1) // BLOCK) * BLOCK
        pre = shared // BLOCK * BLOCK
        c["n"] += 1
        c["hit"] += int(cached > 0)
        c["cached"] += cached
        c["reusable_cap"] += cap
        c["reusable_prefix"] += pre
        c["partial_cap"] += int(0 < cached < cap)
        c["partial_prefix"] += int(0 < cached < pre)
        c["cached_gt_cap"] += int(cached > cap)
    assert [c["hit"], c["n"]] == m["reuse"] and c["cached"] == m["hit_tokens"] \
        and c["reusable_cap"] == m["reusable_tokens"] and c["partial_cap"] == m["hit_shape"].get("partial", 0), run
    return {"run": run.name, **c}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    jobs, verdicts = {}, {}
    for task, (run, ns) in SETS.items():
        v = json.loads((run / "verdict.json").read_text())
        verdicts[task] = v
        for n in ns:
            for cfg in CONFIGS:
                for r in range(5):
                    tag = f"n{n}.{cfg}.r{r}"
                    if tag in v["used"]:
                        jobs[(task, n, cfg, r)] = run / v["used"][tag]
    with ProcessPoolExecutor(24) as ex:
        res = dict(zip(jobs, ex.map(lifecycle, jobs.values())))
    cells = []
    for task, (run, ns) in SETS.items():
        v = verdicts[task]
        for n in ns:
            for cfg in CONFIGS:
                reps = [res[(task, n, cfg, r)] for r in range(5) if (task, n, cfg, r) in res]
                if not reps:
                    continue
                t = Counter()
                for x in reps:
                    t.update({k: x[k] for k in x if k != "run"})
                o = v["observed"][f"{n}/{cfg}"]
                cell = {"set": task, "N": n, "config": cfg, "runs": [x["run"] for x in reps],
                        "per_rep": [{k: x[k] for k in ("n", "hit", "cached", "reusable_cap", "reusable_prefix",
                                                       "partial_cap", "partial_prefix")} for x in reps],
                        "pooled": dict(t),
                        "reuse_rate": t["hit"] / t["n"],
                        "token_ratio_cap": t["cached"] / t["reusable_cap"],
                        "token_ratio_prefix": t["cached"] / t["reusable_prefix"],
                        "partial_share_cap": t["partial_cap"] / t["n"],
                        "partial_share_prefix": t["partial_prefix"] / t["n"]}
                cell["check_reuse_eq_verdict"] = [t["hit"], t["n"]] == o["reuse"]
                if task == "GTASK11":
                    cell["check_token_eq_verdict"] = cell["token_ratio_cap"] == o["token_reuse_ratio"]
                    cell["check_partial_eq_verdict"] = (cell["partial_share_cap"]
                                                        == o["hit_shape_share"].get("partial", 0.0))
                else:
                    cell["check_per_rep_eq_verdict"] = [x["hit"] / x["n"] for x in reps] == o["per_rep_reuse"]
                cells.append(cell)
                print(task, n, cfg, round(cell["reuse_rate"], 4), round(cell["token_ratio_cap"], 4),
                      round(cell["token_ratio_prefix"], 4), round(cell["partial_share_cap"], 4),
                      {k: v_ for k, v_ in cell.items() if k.startswith("check")}, flush=True)
    tot = Counter()
    for x in res.values():
        tot.update({k: x[k] for k in ("n", "prompt_eq_construction", "cached_gt_cap")})
    print("construction", dict(tot))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"construction_check": dict(tot), "cells": cells}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
