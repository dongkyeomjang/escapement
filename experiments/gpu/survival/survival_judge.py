#!/usr/bin/env python3
"""GTASK04 verdict (criteria: docs/research/gpu/GPU_SURVIVAL_PREREG.md).

Per trial, four channels for the resume request:
  ch1  response usage.prompt_tokens_details.cached_tokens (absent -> 0 only if
       the server log shows enable_prompt_tokens_details True)
  ch2  [GPFX] LOOKUP hit of the resume (last LOOKUP in the log)
  ch3  resume-window deltas of vllm:prompt_tokens_cached_total and
       vllm:prefix_cache_hits_total
  ch4  KV events: target blocks stored before the first background LOOKUP,
       and how many of them were removed before the resume LOOKUP

usage: survival_judge.py --run-dir <abs> --pred <abs predictions.json> --out <abs>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "obs"))
from parse_obs import parse  # noqa: E402


def judge_trial(d: Path, pred: dict) -> dict:
    rec = json.loads((d / "trial.json").read_text())
    log = d / "server.log"
    flag = "'enable_prompt_tokens_details': True" in log.read_text(errors="replace")
    reqs = rec["requests"]
    resume = reqs[-1]
    ch1 = resume["cached_tokens"] if resume["cached_tokens"] is not None else (0 if flag else None)
    obs = parse(log)
    looks = [x for x in obs if x["kind"] == "LOOKUP"]
    fails = [x for x in obs if x["kind"] == "ALLOC_FAIL"]
    ch2 = looks[-1]["hit"] if looks else None
    md = resume.get("metric_delta", {})
    ch3 = (md.get("vllm:prompt_tokens_cached_total"), md.get("vllm:prefix_cache_hits_total"))
    # ch4
    batches = [json.loads(x) for x in (d / "kv_events.jsonl").read_text().splitlines()]
    t_hashes: set = set()
    evicted = 0
    first_bg_wall = looks[1]["wall"] if len(looks) > 2 else looks[-1]["wall"]
    resume_wall = looks[-1]["wall"]
    for b in batches:
        for e in b["events"]:
            if e["type"] == "BlockStored" and b["ts"] < first_bg_wall:
                t_hashes.update(e["block_hashes"])
            elif e["type"] == "BlockRemoved" and b["ts"] < resume_wall:
                evicted += sum(1 for h in e["block_hashes"] if h in t_hashes)
    ch4 = {"target_blocks_stored": len(t_hashes), "target_blocks_evicted": evicted}
    preempt = rec["metric_delta_total"].get("vllm:num_preemptions_total")
    agree = (ch1 is not None and ch1 == ch2 == ch3[0] == ch3[1]
             and ch4["target_blocks_evicted"] == pred["pred_target_blocks_evicted"])
    valid = rec["valid"] and preempt == 0 and not fails and len(looks) == len(reqs) and flag
    return {"trial": rec["trial"], "pred": pred["pred_hit"], "ch1": ch1, "ch2": ch2, "ch3": ch3,
            "ch4": ch4, "pred_target_blocks_evicted": pred["pred_target_blocks_evicted"],
            "valid": valid, "invalid_reasons": rec["invalid_reasons"], "preemptions": preempt,
            "channels_agree": agree, "exact": valid and agree and ch1 == pred["pred_hit"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    preds = json.loads(Path(a.pred).read_text())["trials"]
    key = {(p["cond"], p["bg"], p["m"], p["rep"]): p for p in preds}
    rows = []
    for d in sorted(Path(a.run_dir).iterdir()):
        if not (d / "trial.json").exists():
            continue
        t = json.loads((d / "trial.json").read_text())["trial"]
        rows.append(judge_trial(d, key[(t["cond"], t["bg"], t["m"], t["rep"])]))
    n_exact = sum(r["exact"] for r in rows)
    verdict = {
        "trials_expected": len(preds), "trials_judged": len(rows),
        "exact": n_exact, "invalid": sum(not r["valid"] for r in rows),
        "channel_disagreements": sum(r["valid"] and not r["channels_agree"] for r in rows),
        "CONFIRMED": n_exact == len(preds) == len(rows),
        "mismatches": [r for r in rows if not r["exact"]],
    }
    Path(a.out).write_text(json.dumps({"verdict": verdict, "rows": rows}, indent=1))
    print(json.dumps({k: v for k, v in verdict.items() if k != "mismatches"}, indent=2))
    for r in verdict["mismatches"]:
        print("MISMATCH", r["trial"], "pred", r["pred"], "ch1-3", r["ch1"], r["ch2"], r["ch3"], r["ch4"], r["valid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
