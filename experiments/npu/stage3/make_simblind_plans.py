#!/usr/bin/env python3
"""Unified-simulator blind cells N = 13, 17, 20 (directive 08 work C, TASK93).

Replicates r = 0..4 with the main experiment's generation rule
(``make_main_plans.py``, cycle from the v1 analytic TUNED prediction). Seeds
``20261400 + 10*N + r`` = 20261530..34 (N = 13) and 20261600..04 (N = 20),
which no earlier plan, grid-selection or pilot seed uses. For N = 17 the rule
gives 20261570..74, and 20261570 is the ORDER_HI shuffle seed, so N = 17 takes
the next free run 20261575..79. Listed in their own ``INDEX_SIM.json``.
Existing plan files are not rewritten; their content hash must match.
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

NS = (13, 17, 20)
REPS = range(5)
SEED_BASE = 20261400


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "main")
    a = ap.parse_args()
    index = []
    for N, r in [(n, r) for n in NS for r in REPS]:
        seed = SEED_BASE + 10 * N + r + (5 if N == 17 else 0)
        pid = f"main-n{N}-r{r}"
        path = a.out_dir / f"{pid}.json"
        prov = MP.build(n=N, seed=seed, plan_id=pid, cycle_s=6.0)
        cyc = P.analytic(N, P.CONFIGS["TUNED"][0], 16, P.plan_stats([prov]))["cycle_s"]
        plan = MP.build(n=N, seed=seed, plan_id=pid, cycle_s=round(cyc, 3))
        if path.exists():
            old = path.read_bytes()
            content = MP.write(plan, a.out_dir / f".{pid}.check")
            new = (a.out_dir / f".{pid}.check").read_bytes()
            (a.out_dir / f".{pid}.check").unlink()
            if new != old:
                raise SystemExit(f"{path} differs from its rule")
        else:
            content = MP.write(plan, path)
        index.append({"plan_id": pid, "n": N, "rep": r, "seed": seed,
                      "cycle_s": plan.spec["cycle_s"], "content_sha256": content,
                      "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "max_context": MP.max_context_tokens(plan)})
        print(pid, seed, plan.spec["cycle_s"], content[:12], index[-1]["max_context"])
    (a.out_dir / "INDEX_SIM.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
