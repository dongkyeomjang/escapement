#!/usr/bin/env python3
"""INPUT_MANIFEST of the 2026-10-08 directive (§0.2): role -> path, SHA256 and
last commit touching it. Writes docs/research/dx/INPUT_MANIFEST.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[3]
SITE = Path("/usr/local/lib/python3.10/dist-packages")
ITEMS = [
    ("integrated simulator (engine, exclusive prefill)", "src/continuum/sim/engine.py"),
    ("simulator config / entry", "src/continuum/sim/__init__.py"),
    ("descriptor v2 (ContextCost, SubstrateDescriptorV2)", "src/continuum/substrate/v2.py"),
    ("descriptor step-cost model", "src/continuum/substrate/descriptor.py"),
    ("NPU descriptor instance (TASK13 decode, TASK22 prefill)", "experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py"),
    ("descriptor v2 builder (descriptor_v2)", "experiments/npu/stage3/mt_predict_v11.py"),
    ("interpolated-grid descriptor (descriptor_for)", "experiments/npu/analysis/config_search.py"),
    ("analytic model v1 (cycle rule)", "experiments/npu/stage3/mt_predict.py"),
    ("context-length time input (TASK97/100)", "experiments/npu/stage3/plans/main/CTXCOST_BLIND.json"),
    ("cost reconstruction A' (RECON)", "experiments/npu/stage3/mt_measure.py"),
    ("steady-state workload generator", "src/continuum/workload/multiturn.py"),
    ("tool-wait mix (TraceLab quantiles)", "src/continuum/workload/tools.py"),
    ("plan builder", "experiments/npu/stage3/make_plan.py"),
    ("multi-turn runner", "experiments/npu/stage3/multiturn_runner.py"),
    ("lifecycle script (reference)", "experiments/npu/stage3/run_multiturn.sh"),
    ("valid-run decision (reference)", "experiments/npu/stage3/mt_check.py"),
    ("latest preregistered evaluation script (TASK101/102)", "experiments/npu/stage3/ctxblind_analyze.py"),
    ("latest preregistered predictor (TASK101)", "experiments/npu/stage3/predict_ctxblind.py"),
    ("latest preregistration", "docs/research/CTXBLIND_PREREG.md"),
    ("reuse null of latest independent validation", "experiments/npu/stage3/plans/main/NULL_PREDICTORS_CTX.json"),
    ("Appendix E equivalent: independent activity-time check (TASK110)", "experiments/npu/analysis/activity_time_ratio.py"),
    ("Appendix E equivalent: report", "paper/ACTIVITY_TIME_RATIO.md"),
    ("Appendix G equivalent: boundary correction (TASK111)", "experiments/npu/analysis/boundary_sensitivity.py"),
    ("Appendix G equivalent: report", "paper/BOUNDARY_SENSITIVITY.md"),
    ("bucket observation patch", "patches/vllm_rbln-0.11.1/decoder_bucket_observe.patch"),
    ("steptime observation patch (this directive)", "patches/vllm_rbln-0.11.1/steptime_observe.patch"),
]
ARTIFACTS = {
    "BASE": "models/Qwen3-4B-rbln-b8-s8192-d4-mb",
    "BATCHONLY": "models/Qwen3-4B-rbln-b16-s8192-d4-batchonly",
    "TUNED": "models/Qwen3-4B-rbln-b16-s8192-d4-mb16",
    "DP_N8": "models/Qwen3-4B-rbln-b16-s8192-d4-dp8",
}
SITE_FILES = ["vllm_rbln/v1/worker/optimum_model_runner.py", "vllm_rbln/model_executor/models/optimum/model_base.py",
              "vllm_rbln/v1/worker/metrics.py", "rebel/sync_runtime.py"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()


def main() -> int:
    out = {"head": git("rev-parse", "HEAD"), "items": [], "artifacts": {}, "site_packages": {},
           "remote_refs": {r: git("log", "-1", "--format=%H %cI", r) for r in ("origin/main", "origin/gpu-a6000")},
           "remote_note": "refs as last fetched; not refetched for this manifest"}
    for role, rel in ITEMS:
        p = REPO / rel
        out["items"].append({"role": role, "path": rel, "sha256": sha(p) if p.exists() else None,
                             "last_commit": git("log", "-1", "--format=%h %cI", "--", rel) or "uncommitted"})
    for role, rel in ARTIFACTS.items():
        cfg = json.loads((REPO / rel / "rbln_config.json").read_text())
        out["artifacts"][role] = {"path": rel, "rbln_config_sha256": sha(REPO / rel / "rbln_config.json"),
                                  "batch_size": cfg.get("batch_size"),
                                  "decoder_batch_sizes": sorted(cfg.get("decoder_batch_sizes") or []),
                                  "kvcache_num_blocks": cfg.get("kvcache_num_blocks"),
                                  "max_seq_len": cfg.get("max_seq_len")}
    for rel in SITE_FILES:
        out["site_packages"][rel] = sha(SITE / rel)
    dst = REPO / "docs/research/dx/INPUT_MANIFEST.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["artifacts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
