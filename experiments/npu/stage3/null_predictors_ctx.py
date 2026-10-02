#!/usr/bin/env python3
"""Null predictors for the context-cost simulator blind cells N = 15, 18
(directive 11 work B, TASK101). Same definitions as revision 2 and TASK86:

* reuse: 0.67635 (model-v1 development set pooled survival, TASK73 A4);
* cost ratio: 1.0;
* h(n): the observed running distribution of the manuscript's Table I row at
  the same N, built from Table I's own row definition
  (``null_predictors_hi.table_row``).

Operational rules registered here (input values, not a new kind of
criterion): Table I has rows N = 6, 8, 10, 12, 16 only. N = 13 takes the pool
of its two neighbouring rows 12 and 16 (TASK86's N = 14 rule); N = 17 and
N = 20 lie above the last row and take the nearest row, N = 16. Here: N = 15
lies between rows 12 and 16 (pool, as N = 13, 14); N = 18 lies above the last
row (row 16, as N = 17, 20).
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))

import null_predictors_hi as NH  # noqa: E402

RULES = {15: (12, 16), 18: (16,)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    rows = {n: NH.table_row(n) for n in (12, 16)}
    hn = {}
    for n, parts in RULES.items():
        pooled = Counter()
        for p in parts:
            pooled.update(rows[p])
        steps = sum(pooled.values())
        hn[str(n)] = {"table_rows": list(parts), "steps": steps,
                      "h": {str(k): pooled[k] / steps for k in sorted(pooled)}}
    prev = json.loads((HERE / "plans" / "main" / "NULL_PREDICTORS_HI.json").read_text())
    out = {"reuse_null": prev["reuse_null"], "cost_ratio_null": 1.0, "h_null": hn,
           "rules": {"15": "pool of Table I rows N = 12 and N = 16 (no N = 15 row)",
                     "18": "Table I row N = 16 (nearest; no row above 16)"}}
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print({k: (v["table_rows"], v["steps"]) for k, v in hn.items()}, out["reuse_null"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
