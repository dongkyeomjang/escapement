#!/usr/bin/env python3
"""Generate every plan of the multi-turn main experiment (directive 04 §6.1).

N in 6, 8, 10, 12; replicate r in 0..4; seed ``20261400 + 10*N + r`` (the grid
selection used 20261200-range seeds and the pilot 20261300-20261302, so no plan
is shared). One plan per (N, r), used by every configuration of that cell --
the paired design derives all arms from one plan (TASK19).

``cycle_s`` (stagger and window rule) is the analytic model's TUNED prediction
for that plan, fixed here before anything is measured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_plan as MP  # noqa: E402
import mt_predict as P  # noqa: E402

NS = (6, 8, 10, 12)
REPS = 5
SEED_BASE = 20261400


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "main")
    a = ap.parse_args()
    index = []
    for n in NS:
        for r in range(REPS):
            seed = SEED_BASE + 10 * n + r
            pid = f"main-n{n}-r{r}"
            prov = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=6.0)
            cyc = P.analytic(n, P.CONFIGS["TUNED"][0], 16, P.plan_stats([prov]))["cycle_s"]
            plan = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=round(cyc, 3))
            path = a.out_dir / f"{pid}.json"
            content = MP.write(plan, path)
            index.append({"plan_id": pid, "n": n, "rep": r, "seed": seed,
                          "cycle_s": plan.spec["cycle_s"], "content_sha256": content,
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "max_context": MP.max_context_tokens(plan)})
            print(pid, seed, plan.spec["cycle_s"], content[:12], index[-1]["max_context"])
    (a.out_dir / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
