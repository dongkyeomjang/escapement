#!/usr/bin/env python3
"""GTASK04 measurement: sequential survival trials, fresh server per trial.

Plan and content seeds come from ``predict.trial_plan()`` (committed with the
predictions). Each trial: target -> m background requests -> resume, one at a
time. The observation patch must be applied (``apply.sh status`` = patched);
the server runs with ESCAPEMENT_OBS=1 and KV events.

usage: survival_run.py --out-dir <abs> [--only i|ii]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "launch"))
from client import completion, rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402
import predict as P  # noqa: E402


def run_trial(t: dict, out: Path) -> dict:
    args = base_args(num_gpu_blocks=P.NUM_GPU_BLOCKS, max_num_seqs=1,
                     max_num_batched_tokens=P.BUDGET, capture_sizes=[1, 2, 4, 8, 16],
                     extra=kv_events_args())
    seed = t["seed"]
    target = rand_ids(seed, P.TARGET_PROMPT)
    rec: dict = {"trial": t, "requests": []}
    with Lifecycle(out, args, obs=True, kv_events=True) as lc:
        base = lc.base
        m_start = scrape(base)
        r = completion(base, target, P.TARGET_GEN[t["cond"]])
        r["role"] = "target"
        rec["requests"].append(r)
        for k in range(t["m"]):
            b = completion(base, rand_ids(seed + 1 + k, t["bg"]), P.BG_GEN)
            b["role"] = f"bg{k}"
            b.pop("token_ids", None)
            b.pop("text", None)
            rec["requests"].append(b)
        suffix = rand_ids(seed + 999, P.SUFFIX)
        resume = target + (r["token_ids"] if t["cond"] == "ii" else []) + suffix
        m0 = scrape(base)
        rr = completion(base, resume, P.BG_GEN)
        m1 = scrape(base)
        rr["role"] = "resume"
        rr["metric_delta"] = {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}
        rec["requests"].append(rr)
        time.sleep(1.0)
        m_end = scrape(base)
        rec["metric_delta_total"] = {k: m_end.get(k, 0) - m_start.get(k, 0) for k in m_end}
        ok, why = lc.valid()
        rec["valid"], rec["invalid_reasons"] = ok, why
        rec["target_prompt_ids"] = target
    (out / "trial.json").write_text(json.dumps(rec))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", choices=("i", "ii"))
    a = ap.parse_args()
    out = Path(a.out_dir)
    if not out.is_absolute():
        raise SystemExit("--out-dir must be absolute")
    if "state: patched" not in patch_state():
        raise SystemExit("observation patch must be applied (apply.sh status)")
    out.mkdir(parents=True, exist_ok=True)
    plan = [t for t in P.trial_plan() if a.only in (None, t["cond"])]
    log = (out / "progress.log").open("a")
    for n, t in enumerate(plan):
        d = out / f"{n:03d}_{t['cond']}_bg{t['bg']}_m{t['m']}_r{t['rep']}"
        if (d / "trial.json").exists():
            continue
        t0 = time.time()
        try:
            rec = run_trial(t, d)
            rr = rec["requests"][-1]
            msg = f"{n} {t} cached={rr['cached_tokens']} valid={rec['valid']} {time.time() - t0:.0f}s"
        except Exception as exc:  # keep going; the failure is recorded, not retried
            msg = f"{n} {t} ERROR {type(exc).__name__}: {exc}"
        log.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + msg + "\n")
        log.flush()
        print(msg, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
