#!/usr/bin/env python3
"""Validity of one lifecycle of the 2026-10-08 directive (DX_PREREG.md §2.5).

Prints one JSON line with checks only (no cost, reuse or ratio), exit 0 = VALID.

VALID <=> the mt_check conditions (runner exit 0, stopped by the window, no
exhausted slot, online window = offline recomputation, nothing sent after the
evaluation end, no HTTP error, plan file and content SHA256 equal to
``plans/dx/INDEX_DX.json``, every evaluation request joined to a server id with
``prompt_tokens``), the steptime patch (v1 or v2) state ``patched`` recorded in the
lifecycle, and, when the lifecycle ran with OBS=1, a complete DIRECT_EXEC
attribution (every counted ``[BUCKET]`` step has its ``[STEPTIME]`` line with
the same request count, every evaluation request has a prefill step, no
unparsable ``[STEPTIME]`` line).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dx_steps as X  # noqa: E402

PLAN_DIR = HERE / "plans" / "dx"


def check(run: Path, tag: str, config: str, plan_id: str) -> dict:
    idx = {e["plan_id"]: e for e in json.loads((PLAN_DIR / "INDEX_DX.json").read_text())}[plan_id]
    lc, raw = {}, (run / "probe" / tag / "lifecycle.txt").read_text()
    for line in raw.splitlines():
        for part in line.split():
            if "=" in part and not line.startswith("patch"):
                k, v = part.split("=", 1)
                lc[k] = v
    obs = lc.get("obs_steptime") == "1"
    res = {"tag": tag, "config": config, "plan_id": plan_id, "obs": obs,
           "runner_exit": lc.get("runner_exit"), "started": lc.get("started"),
           "finished": lc.get("finished"), "plan_file_sha_ok": lc.get("plan_sha256") == idx["file_sha256"]}
    reasons = []
    if lc.get("runner_exit") != "0":
        reasons.append(f"runner_exit={lc.get('runner_exit')}")
    if not res["plan_file_sha_ok"]:
        reasons.append("plan file sha")
    v1 = "patch-steptime: state:   patched" in raw
    v2 = "patch-steptime-v2: state:   patched" in raw
    res["steptime_patch"] = "v1" if v1 else "v2" if v2 else None
    if not (v1 or v2):
        reasons.append("steptime patch (v1 or v2) not recorded as patched")
    try:
        x = X.lifecycle(run, tag, config, obs=obs)
    except Exception as e:  # missing or unreadable outputs
        reasons.append(f"metrics error: {type(e).__name__}: {e}")
        x = None
    if x is not None:
        m = x["recon"]
        c = m["checks"]
        res["checks"] = {k: c[k] for k in ("stopped_by_window", "exhausted_slots",
                                           "window_online_eq_offline", "sent_after_eval_end",
                                           "http_errors", "runner_commit", "renewal_count",
                                           "renewal_max_delay_s")}
        res["eval_requests"] = m["eval_requests"]
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
        if obs:
            res["attribution"] = x["attribution"]
            if not x["complete"]:
                reasons.append("DIRECT_EXEC attribution incomplete")
    res["valid"] = not reasons
    res["reasons"] = reasons
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--config", required=True, choices=sorted(X.CONFIGS))
    ap.add_argument("--plan-id", required=True)
    a = ap.parse_args()
    res = check(a.run, a.tag, a.config, a.plan_id)
    print(json.dumps(res, default=str))
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
