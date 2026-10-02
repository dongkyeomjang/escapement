#!/usr/bin/env python3
"""Validity of one main-experiment lifecycle (preregistration §5.8).

Prints one JSON line with the checks only -- no device time, reuse or h --
so the measurement can be watched without looking at outcomes (directive 05
§2.4). Exit 0 = VALID, 1 = INVALID.

VALID <=> runner exit 0, stopped by the window, no exhausted slot, online
window = offline recomputation, nothing sent after the evaluation end, no
HTTP error, plan file and content SHA256 equal to the preregistered index,
every evaluation request joined to a server id with ``prompt_tokens``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_measure as M  # noqa: E402

REPO = HERE.parents[2]
MODELS = REPO / "models"
PLAN_DIR = HERE / "plans" / "main"
CONFIGS = {
    "BASE": ("Qwen3-4B-rbln-b8-s8192-d4-mb", (1, 2, 4, 8), 8),
    "BATCHONLY": ("Qwen3-4B-rbln-b16-s8192-d4-batchonly", (1, 2, 4, 8, 16), 16),
    "TUNED": ("Qwen3-4B-rbln-b16-s8192-d4-mb16", (1, 4, 6, 8, 10, 16), 16),
    "DP": ("Qwen3-4B-rbln-b16-s8192-d4-dp8", (1, 2, 3, 4, 6, 16), 16),   # N = 8 only
}


def plan_index() -> dict[str, dict]:
    out = {}
    for f in ("INDEX.json", "INDEX_EXT.json", "INDEX_HI.json", "INDEX_SIM.json", "INDEX_CTX.json"):
        for e in json.loads((PLAN_DIR / f).read_text()):
            out[e["plan_id"]] = e
    return out


def check(run: Path, tag: str, config: str, plan_id: str) -> dict:
    _, grid, batch = CONFIGS[config]
    idx = plan_index()[plan_id]
    lc = {}
    for line in (run / "probe" / tag / "lifecycle.txt").read_text().splitlines():
        for part in line.split():
            if "=" in part and not line.startswith("patch:"):
                k, v = part.split("=", 1)
                lc[k] = v
    res = {"tag": tag, "config": config, "plan_id": plan_id,
           "runner_exit": lc.get("runner_exit"), "started": lc.get("started"),
           "finished": lc.get("finished"),
           "plan_file_sha_ok": lc.get("plan_sha256") == idx["file_sha256"]}
    reasons = []
    if lc.get("runner_exit") != "0":
        reasons.append(f"runner_exit={lc.get('runner_exit')}")
    if not res["plan_file_sha_ok"]:
        reasons.append("plan file sha")
    try:
        m = M.lifecycle_metrics(run, tag, grid, batch)
    except Exception as e:  # missing or unreadable outputs
        reasons.append(f"metrics error: {type(e).__name__}: {e}")
        m = None
    if m is not None:
        c = m["checks"]
        res["checks"] = {k: c[k] for k in ("stopped_by_window", "exhausted_slots",
                                           "window_online_eq_offline", "sent_after_eval_end",
                                           "http_errors", "runner_commit", "renewal_count",
                                           "renewal_max_delay_s")}
        res["eval_requests"] = m["eval_requests"]
        res["cached_source"] = m["cached_source"]
        if not c["stopped_by_window"]:
            reasons.append("not stopped by window")
        if c["exhausted_slots"]:
            reasons.append(f"exhausted slots {c['exhausted_slots']}")
        if not c["window_online_eq_offline"]:
            reasons.append("window online != offline")
        if c["sent_after_eval_end"]:
            reasons.append(f"sent after eval end {c['sent_after_eval_end']}")
        if c["http_errors"]:
            reasons.append(f"http errors {c['http_errors']}")
        if c["plan_content_sha256"] != idx["content_sha256"]:
            reasons.append("plan content sha")
        if not m["valid"]:
            reasons.extend(m["invalid_reasons"])
    res["valid"] = not reasons
    res["invalid_reasons"] = reasons
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--config", required=True, choices=sorted(CONFIGS))
    ap.add_argument("--plan-id", required=True)
    a = ap.parse_args()
    res = check(a.run, a.tag, a.config, a.plan_id)
    print(json.dumps(res))
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
