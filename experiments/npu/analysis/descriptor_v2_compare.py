#!/usr/bin/env python3
"""Compare two descriptor_v2_regression.sh output directories byte for byte.

Exemptions, all run metadata rather than results: ``tables/manifest.json``
records when and at which HEAD the tables were generated (its other keys must
match); JSON keys ``computed_at``, ``started``, ``seconds`` and any key ending
in ``_seconds`` (wall-clock timings of the self-check and the retro run).
Everything else must be identical. Also checks that the simulator's
``semantics='descriptor'`` on the RBLN v2 instance equals the explicit
observed-semantics switches (immediate release + pre-evict) on every main plan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))

META = {"generated_at", "git_head", "git_dirty"}


def strip(path: Path, rel: str) -> bytes | dict:
    if rel == "tables/manifest.json":
        d = json.loads(path.read_text())
        return {k: v for k, v in d.items() if k not in META}
    if rel.endswith(".json"):
        return _drop_timing(json.loads(path.read_text()))
    return path.read_bytes()


def _drop_timing(x):
    if isinstance(x, dict):
        return {k: _drop_timing(v) for k, v in x.items()
                if k not in ("computed_at", "started", "seconds") and not k.endswith("_seconds")}
    if isinstance(x, list):
        return [_drop_timing(v) for v in x]
    return x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--semantics-check", action="store_true")
    a = ap.parse_args()
    files = sorted(p.relative_to(a.base).as_posix() for p in a.base.rglob("*")
                   if p.is_file() and not p.name.endswith(".log"))
    bad = []
    for rel in files:
        q = a.after / rel
        if not q.exists() or strip(a.base / rel, rel) != strip(q, rel):
            bad.append(rel)
    extra = sorted(p.relative_to(a.after).as_posix() for p in a.after.rglob("*")
                   if p.is_file() and not p.name.endswith(".log")
                   and not (a.base / p.relative_to(a.after)).exists())
    print(f"compared {len(files)} files: {len(bad)} differ, {len(extra)} new")
    for rel in bad + extra:
        print("  DIFF", rel)
    ok = not bad and not extra
    if a.semantics_check:
        import mt_predict as P
        from continuum.sim import SimConfig, simulate
        from continuum.workload.multiturn import MultiTurnPlan, to_sim_inputs
        from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_V2
        plans = sorted((REPO / "experiments/npu/stage3/plans/main").glob("main-n*-r*.json"))
        grids = dict(P.CONFIGS)
        n_same = n_all = 0
        for pf in plans:
            plan = MultiTurnPlan.from_json(json.loads(pf.read_text()))
            sessions, start, succ, _ = to_sim_inputs(plan)
            for name, (grid, batch) in grids.items():
                obs = simulate(P.descriptor(grid, batch), sessions, SimConfig(
                    max_running_requests=batch, session_start_s=start, successor=succ,
                    release_rule="immediate", dummy_mode="pre_evict"))
                d2 = RBLN_CA25_V2.with_config(grid=grid, max_running=batch, reuse_capacity=batch)
                via = simulate(d2, sessions, SimConfig(
                    max_running_requests=batch, session_start_s=start, successor=succ,
                    semantics="descriptor"))
                n_all += 1
                n_same += (obs.steps == via.steps and obs.requests == via.requests
                           and obs.evictions == via.evictions)
        print(f"semantics='descriptor' == explicit observed switches: {n_same}/{n_all} runs")
        ok &= n_same == n_all
    print("REGRESSION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
