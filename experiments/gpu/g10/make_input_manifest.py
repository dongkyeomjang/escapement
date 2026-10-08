#!/usr/bin/env python3
"""G-10 0.2: INPUT_MANIFEST -- path, last commit and SHA256 of every frozen input.

usage: make_input_manifest.py --out <abs json>
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[3]
ITEMS = [
    ("context-aware integrated simulator (engine, LRU pool)", "experiments/gpu/multiturn/gpu_mt_sim.py"),
    ("context-aware step time (GTASK20 predictor (1) ctx, StepCost)", "experiments/gpu/multiturn/predict_blind.py"),
    ("GTASK18 context slope c (F1)", "experiments/gpu/stepcost/ctx_result/summary.json"),
    ("two prefill-cost settings lo/hi and price channel", "experiments/gpu/multiturn/gpu_cost.py"),
    ("GPU descriptor draft", "experiments/gpu/substrate/a6000_vllm_0220_draft.py"),
    ("structural zero-preemption bound and BASE/POOL pools, default grid", "experiments/gpu/multiturn/selection/selection.json"),
    ("configuration names -> server arguments", "experiments/gpu/multiturn/configs.py"),
    ("server arguments (lifecycle, fixed flags)", "experiments/gpu/launch/lifecycle.py"),
    ("runner (token-id prompts, streaming, window rule)", "experiments/gpu/multiturn/gpu_mt_runner.py"),
    ("plan law", "experiments/npu/stage3/make_plan.py"),
    ("plan / window rule (WindowRule)", "src/continuum/workload/multiturn.py"),
    ("KV event replay (GTASK12)", "experiments/gpu/multiturn/replay.py"),
    ("observed metrics, A'-GPU (RECON), reusable-token rule", "experiments/gpu/multiturn/gpu_mt_measure.py"),
    ("observation log parser", "experiments/gpu/obs/parse_obs.py"),
    ("observation patch (GSTEP / GPFX)", "experiments/gpu/patches/vllm-0.22.0/escapement_obs.patch"),
    ("observation patch guard", "experiments/gpu/patches/vllm-0.22.0/apply.sh"),
    ("exec-timing layer (G-10 A)", "experiments/gpu/patches/vllm-0.22.0/escapement_exec.patch"),
    ("exec-timing layer guard", "experiments/gpu/patches/vllm-0.22.0/apply_exec.sh"),
    ("previous criteria (GTASK20 prereg)", "docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md"),
    ("previous judge (bootstrap, h, window lines)", "experiments/gpu/multiturn/main_judge.py"),
    ("evaluation window / boundary correction (GTASK22)", "experiments/gpu/multiturn/boundary_sensitivity.py"),
    ("analytic model (cycle_s for plans)", "experiments/gpu/multiturn/gpu_mt_model.py"),
]


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    rows = []
    for role, rel in ITEMS:
        p = REPO / rel
        rows.append({"role": role, "path": rel, "exists": p.exists(),
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
                     "last_commit": git("log", "-1", "--format=%h %cI", "--", rel) or "uncommitted"})
    out = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
           "dirty": git("status", "--porcelain").splitlines(), "items": rows}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(r["last_commit"][:8], (r["sha256"] or "-")[:12], r["path"])


if __name__ == "__main__":
    main()
