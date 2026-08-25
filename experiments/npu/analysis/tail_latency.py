#!/usr/bin/env python3
"""Request completion-time percentiles per arm, from runs already on disk.

Device time is what this project optimised and confirmed, but a serving change
that lowers device time can still hurt the tail a user feels. This re-reads the
per-request JSONL of measurements already taken -- no new run -- and reports
p50/p99 of ``done_s - sent_s`` per arm so the tail can be stated rather than
assumed.

A cell is reported only if every arm in the comparison has it; anything else is
listed as not reported rather than filled in.

    env -u PYTHONPATH python3 experiments/npu/analysis/tail_latency.py \
        --run <RUN> --arms BASE,TUNED --sessions 6,8,10
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    o = sorted(values)
    k = min(len(o) - 1, max(0, int(round(q * len(o) + 0.5)) - 1))
    return o[k]


def latencies(run: Path, label: str) -> list[float] | None:
    f = run / "probe" / f"requests.{label}.jsonl"
    if not f.exists():
        return None
    out = []
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("sent_s") is not None and r.get("done_s") is not None:
            out.append(r["done_s"] - r["sent_s"])
    return out or None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--arms", required=True)
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--baseline", default="BASE")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    arms = args.arms.split(",")
    ns = [int(x) for x in args.sessions.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]

    rows, missing = [], []
    for n in ns:
        per_arm = {}
        for a in arms:
            vals: list[float] = []
            ok = True
            for b in blocks:
                v = latencies(args.run, f"{a}.n{n}.b{b}")
                if v is None:
                    ok = False
                    missing.append(f"{a}.n{n}.b{b}")
                else:
                    vals += v
            per_arm[a] = vals if ok else None
        if any(v is None for v in per_arm.values()):
            continue
        row = {"N": n, "arms": {}}
        base = per_arm[args.baseline]
        for a in arms:
            v = per_arm[a]
            row["arms"][a] = {
                "n_requests": len(v),
                "p50_s": pct(v, 0.50), "p99_s": pct(v, 0.99),
                "mean_s": statistics.fmean(v),
                "p50_ratio": pct(v, 0.50) / pct(base, 0.50),
                "p99_ratio": pct(v, 0.99) / pct(base, 0.99),
            }
        rows.append(row)

    print(f"{'N':>3} {'arm':>10} {'reqs':>5} {'p50 (s)':>9} {'p99 (s)':>9} "
          f"{'p50 ratio':>10} {'p99 ratio':>10}")
    for row in rows:
        for a, v in row["arms"].items():
            print(f"{row['N']:>3} {a:>10} {v['n_requests']:>5} {v['p50_s']:>9.3f} "
                  f"{v['p99_s']:>9.3f} {v['p50_ratio']:>10.4f} {v['p99_ratio']:>10.4f}")
    if missing:
        print(f"\n미보고(artifact 없음) {len(missing)}건: {missing[:6]}")
    if args.output:
        args.output.write_text(json.dumps({"rows": rows, "missing": missing},
                                          indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
