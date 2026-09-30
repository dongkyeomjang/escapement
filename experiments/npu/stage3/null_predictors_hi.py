#!/usr/bin/env python3
"""Null predictors for the high-load blind cells N = 14, 16 (TASK86).

Same definitions as revision 2 (MULTITURN_MAIN_PREREG.md §7.2):

* reuse: the model-v1 development set pooled survival rate (TASK73 A4),
  0.67635 -- unchanged;
* cost ratio: 1.0;
* h(n): the observed running distribution of the manuscript's Table I
  condition at the same N. This time it is taken from Table I's own row
  definition (``padding_ratio.TASK26_CELLS``, the parts ``make_table_3_1``
  prints), not re-pooled from ``padding_ratio.json`` cells.

Operational rule registered here: Table I has no N = 14 row, so the N = 14
null is the step-count pool of its two neighbouring rows N = 12 and N = 16.

Also written for the record: the Table I rows N = 6, 8, 10. Revision 2 pooled
N = 8 from TASK19 + TASK20 + TASK23-2a; Table I's N = 8 row is TASK20 +
TASK23-2a only (TASK86 correction).
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

import padding_ratio as PR  # noqa: E402

T01_PADDING = {6: 0.120, 8: 0.163, 10: 0.152, 12: 0.098, 16: 0.039}   # results/tables/T01.md


def table_row(n: int) -> Counter:
    cell = next(c for c in PR.TASK26_CELLS if c["grid"] == PR.BASE_GRID and c["N"] == n)
    tot = PR.arm_totals(cell["parts"], "AGENTIC", cell["grid"])
    assert abs(tot["padding_ratio"] - T01_PADDING[n]) < 0.0005, (n, tot["padding_ratio"])
    out = Counter()
    for key, cnt in tot["hist"].items():
        out[int(key.split("->")[0])] += cnt
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    rows = {n: table_row(n) for n in (6, 8, 10, 12, 16)}
    hn = {}
    for n, parts in ((14, (12, 16)), (16, (16,)), (6, (6,)), (8, (8,)), (10, (10,)), (12, (12,))):
        pooled = Counter()
        for p in parts:
            pooled.update(rows[p])
        steps = sum(pooled.values())
        hn[str(n)] = {"table_rows": list(parts), "steps": steps,
                      "h": {str(k): pooled[k] / steps for k in sorted(pooled)}}
    dev = json.loads((REPO / "results/npu/stage3/model_v1_dev/dev.json").read_text())
    scored = [r for r in dev["requests"] if r.get("v1_ss") is not None]
    out = {"reuse_null": {"value": sum(r["obs"] for r in scored) / len(scored),
                          "hits": sum(r["obs"] for r in scored), "n": len(scored)},
           "cost_ratio_null": 1.0,
           "h_null": {k: hn[k] for k in ("14", "16")},
           "table_i_rows_for_record": {k: hn[k] for k in ("6", "8", "10", "12")},
           "rule_n14": "pool of Table I rows N = 12 and N = 16 (no N = 14 row)"}
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print({k: (v["table_rows"], v["steps"]) for k, v in hn.items()}, out["reuse_null"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
