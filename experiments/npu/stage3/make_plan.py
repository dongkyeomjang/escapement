#!/usr/bin/env python3
"""Generate one multi-turn plan file (``continuum.workload.multiturn``).

The workload spec defaults to the decisions of TASK76 (D1 8-token later
segments, D2 K = 8, D6 60 s gap cap) and the manuscript's opening prompt and
generation ranges. ``--cycle-s`` sets the stagger (``cycle / N``) and the
window rule's cycle; the caller supplies it from a model prediction so it is
fixed before anything is measured.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from continuum.workload.agentic import Distribution  # noqa: E402
from continuum.workload.multiturn import generate_plan, max_context_tokens  # noqa: E402
from continuum.workload.tools import load_mix  # noqa: E402

GAP_FILE = "/home/rebel/vllm-continuum/results/tracelab/summary.json"


def parse(spec: str) -> Distribution:
    p = spec.split(":")
    if p[0] == "fixed":
        return Distribution("fixed", value=int(p[1]))
    if p[0] == "uniform":
        return Distribution("uniform", low=int(p[1]), high=int(p[2]))
    raise SystemExit(f"unknown distribution {spec!r}")


def build(*, n: int, seed: int, plan_id: str, cycle_s: float, turns: int = 8,
          sessions_per_slot: int = 16, first: str = "uniform:800:1600",
          later: str = "fixed:8", generation: str = "uniform:32:256",
          gap: str = f"toolmix:{GAP_FILE}:60", max_seq_len: int = 8192):
    if gap.startswith("toolmix:"):
        _, path, cap = gap.split(":", 2)
        mix = load_mix(path, cap_s=float(cap))
        sampler = lambda rng: mix.draw(rng)[1]  # noqa: E731
    elif gap.startswith("uniform:"):
        _, lo, hi = gap.split(":")
        sampler = lambda rng: rng.uniform(float(lo), float(hi))  # noqa: E731
    else:
        raise SystemExit(f"unknown gap {gap!r}")
    spec = {"first_segment": first, "later_segment": later, "generation": generation,
            "gap": gap, "cycle_s": cycle_s, "turns": turns,
            "sessions_per_slot": sessions_per_slot, "max_seq_len": max_seq_len}
    plan = generate_plan(n_slots=n, turns=turns, sessions_per_slot=sessions_per_slot,
                         first_segment=parse(first), later_segment=parse(later),
                         generation=parse(generation), gap_sampler=sampler,
                         stagger_s=cycle_s / n, base_seed=seed, plan_id=plan_id, spec=spec)
    worst = max_context_tokens(plan)
    if worst > max_seq_len:
        raise SystemExit(f"plan {plan_id} reaches {worst} tokens > max_seq_len {max_seq_len}")
    return plan


def write(plan, path: Path) -> str:
    d = plan.to_json()
    d["_sha256"] = plan.sha256()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, sort_keys=True, separators=(",", ":")) + "\n")
    return d["_sha256"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--plan-id", required=True)
    ap.add_argument("--cycle-s", type=float, required=True)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--sessions-per-slot", type=int, default=16)
    ap.add_argument("--gap", default=f"toolmix:{GAP_FILE}:60")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    plan = build(n=a.n, seed=a.seed, plan_id=a.plan_id, cycle_s=a.cycle_s, turns=a.turns,
                 sessions_per_slot=a.sessions_per_slot, gap=a.gap)
    print(write(plan, a.output), max_context_tokens(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
