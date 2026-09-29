#!/usr/bin/env python3
"""Null predictors of the preregistration's revision 2 (directive 05 §2.2).

Every value is fixed by data that existed before the main measurement:

* reuse (§5.1): the pooled survival rate of the model-v1 development set
  (TASK73 A4) -- the scored re-arrivals of ``model_v1_dev/dev.json``, the
  same population and base rate as its climatology Brier. One constant for
  every cell.
* cost ratio (§5.2): 1.0 for every cell (no configuration effect).
* h(n) (§5.6): the observed step-weighted running distribution of the
  manuscript's Table I condition (T01, grid (1,2,4,8), AGENTIC arm) at the
  same N -- ``padding_ratio.json`` cells of that grid and N pooled by step
  count, the way T01 pools them. Checked here against T01's padding column.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEV = REPO / "results/npu/stage3/model_v1_dev/dev.json"
PAD = REPO / "results/npu/stage2/padding_ratio.json"
T01_PADDING = {6: 0.120, 8: 0.163, 10: 0.152, 12: 0.098}   # results/tables/T01.md, p_gap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    dev = json.loads(DEV.read_text())
    scored = [r for r in dev["requests"] if r.get("v1_ss") is not None]
    assert len(scored) == dev["summary"]["n_scored"] == 998
    reuse0 = sum(r["obs"] for r in scored) / len(scored)

    cells = json.loads(PAD.read_text())["cells"]
    h0 = {}
    for n in (6, 8, 10, 12):
        pooled = Counter()
        srcs = []
        for c in cells:
            if c["N"] == n and c["grid"] == [1, 2, 4, 8]:
                srcs.append(c["src"])
                for k, v in c["hist_agentic"].items():
                    actual, bucket = (int(x) for x in k.split("->"))
                    pooled[(actual, bucket)] += v
        steps = sum(pooled.values())
        pad = 1 - sum(a_ * v for (a_, _), v in pooled.items()) / sum(b * v for (_, b), v in pooled.items())
        assert abs(pad - T01_PADDING[n]) < 0.0005, (n, pad)
        run = Counter()
        for (a_, _), v in pooled.items():
            run[a_] += v
        h0[str(n)] = {"sources": srcs, "steps": steps, "padding_check_vs_T01": round(pad, 4),
                      "h": {str(k): run[k] / steps for k in sorted(run)}}

    out = {"reuse_null": {"value": reuse0, "hits": sum(r["obs"] for r in scored),
                          "n": len(scored), "source": str(DEV.relative_to(REPO))},
           "cost_ratio_null": 1.0,
           "h_null": h0, "h_null_source": str(PAD.relative_to(REPO))}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"reuse_null": out["reuse_null"],
                      "h_null": {k: {"sources": v["sources"], "steps": v["steps"],
                                     "pad": v["padding_check_vs_T01"]} for k, v in h0.items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
