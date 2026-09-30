#!/usr/bin/env python3
"""Extra N = 8 plans for the DP-vs-TUNED comparison (directive 05 §2.3).

Replicates r = 5..9 of N = 8 with the main experiment's generation rule
(``make_main_plans.py``) and seed ``20261400 + 10*8 + r`` = 20261485..20261489,
which no earlier plan, grid-selection or pilot seed uses. They are measured
only for the DP and TUNED configurations of N = 8 and are listed in their own
``INDEX_EXT.json``; ``INDEX.json`` (the preregistered 20 plans) is untouched.
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

N = 8
REPS = range(5, 10)
SEED_BASE = 20261400


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "main")
    a = ap.parse_args()
    index = []
    for r in REPS:
        seed = SEED_BASE + 10 * N + r
        pid = f"main-n{N}-r{r}"
        path = a.out_dir / f"{pid}.json"
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
        prov = MP.build(n=N, seed=seed, plan_id=pid, cycle_s=6.0)
        cyc = P.analytic(N, P.CONFIGS["TUNED"][0], 16, P.plan_stats([prov]))["cycle_s"]
        plan = MP.build(n=N, seed=seed, plan_id=pid, cycle_s=round(cyc, 3))
        content = MP.write(plan, path)
        index.append({"plan_id": pid, "n": N, "rep": r, "seed": seed,
                      "cycle_s": plan.spec["cycle_s"], "content_sha256": content,
                      "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "max_context": MP.max_context_tokens(plan)})
        print(pid, seed, plan.spec["cycle_s"], content[:12], index[-1]["max_context"])
    (a.out_dir / "INDEX_EXT.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
