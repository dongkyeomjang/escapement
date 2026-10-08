#!/usr/bin/env python3
"""Plans of the 2026-10-08 directive (direct timing, tool-wait cap, same-resource
grid selection; DX_PREREG.md).

Generation rule = ``make_ctxblind_plans.py`` (``make_plan.build`` with the
manuscript workload; cycle from the v1 analytic TUNED prediction of the plan),
with new seeds ``20268000 + 10*N + r`` that no earlier NPU or GPU plan, order or
selection uses (``git grep`` of 20268xxx finds only GPU survival seed 20268001,
which this rule never produces).

Roles:

* ``B``     N = 18 and N = 8, r = 0..9 (cap 60 s, as every earlier plan)
* ``C``     N = 14, r = 0..4, two caps from one raw draw: ``capNN`` = 60 and 120.
            The tool-wait draw is ``min(g_raw, cap)`` (``ToolMix.draw`` clips
            after drawing, so both caps consume the random stream identically
            and every prompt, output, turn count and session renewal is equal).
            Both caps use the cycle the rule gives for the 60 s plan, so the cap
            is the only difference. Both files carry the same internal plan_id
            ``dx-c-n14-rK`` (it seeds every session); the file stem / index key
            carries the cap.
* ``E``     N = 19, r = 0..9 (cap 60 s)
* ``DEV``   instrumentation perturbation check (work A): N = 6 and N = 18,
            r = 0..4, seeds ``20268900 + 10*N + r`` -> 20268960..64, 20269080..84.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_plan as MP  # noqa: E402
import mt_predict as P  # noqa: E402

SEED_BASE = 20268000
DEV_SEED_BASE = 20268900
SPECS = (
    [("B", 18, r, 60) for r in range(10)]
    + [("B", 8, r, 60) for r in range(10)]
    + [("C", 14, r, cap) for r in range(5) for cap in (60, 120)]
    + [("E", 19, r, 60) for r in range(10)]
    + [("DEV", n, r, 60) for n in (6, 18) for r in range(5)]
)


def internal_id(role: str, n: int, r: int) -> str:
    """plan_id inside the plan; it seeds every session (derive_block_seed of
    ``plan_id/slot/g``), so the two caps of a C replicate share it."""
    return f"dx-{role.lower()}-n{n}-r{r}"


def pid_of(role: str, n: int, r: int, cap: int) -> str:
    """File stem and index key (unique)."""
    if role == "C":
        return f"dx-c-n{n}-cap{cap}-r{r}"
    return internal_id(role, n, r)


def cycle_of(args) -> float:
    """The cycle rule always reads the 60 s plan of (n, seed)."""
    n, seed, pid = args
    prov = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=6.0)
    return round(P.analytic(n, P.CONFIGS["TUNED"][0], 16, P.plan_stats([prov]))["cycle_s"], 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "dx")
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    specs = [(role, n, r, cap, (DEV_SEED_BASE if role == "DEV" else SEED_BASE) + 10 * n + r)
             for role, n, r, cap in SPECS]
    keys = sorted({(n, seed): internal_id(role, n, r) for role, n, r, cap, seed in specs}.items())
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        vals = list(ex.map(cycle_of, [(k[0], k[1], pid) for k, pid in keys]))
    cycles = dict(zip([k for k, _ in keys], vals))
    index = []
    for role, n, r, cap, seed in specs:
        pid = pid_of(role, n, r, cap)
        gap = f"toolmix:{MP.GAP_FILE}:{cap}"
        plan = MP.build(n=n, seed=seed, plan_id=internal_id(role, n, r), cycle_s=cycles[(n, seed)], gap=gap)
        path = a.out_dir / f"{pid}.json"
        if path.exists():
            chk = a.out_dir / f".{pid}.check"
            content = MP.write(plan, chk)
            same = chk.read_bytes() == path.read_bytes()
            chk.unlink()
            if not same:
                raise SystemExit(f"{path} differs from its rule")
        else:
            content = MP.write(plan, path)
        index.append({"plan_id": pid, "internal_plan_id": internal_id(role, n, r), "role": role, "n": n, "rep": r, "seed": seed,
                      "cap_s": cap, "cycle_s": plan.spec["cycle_s"], "content_sha256": content,
                      "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "max_context": MP.max_context_tokens(plan)})
        print(pid, seed, plan.spec["cycle_s"], content[:12], index[-1]["max_context"], flush=True)
    (a.out_dir / "INDEX_DX.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
