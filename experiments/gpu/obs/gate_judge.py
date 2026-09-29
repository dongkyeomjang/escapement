#!/usr/bin/env python3
"""GTASK03 gate verdicts G1-G3 (criteria: docs/research/gpu/GPU_OBS_GATE_PREREG.md).

usage: gate_judge.py --a <abs arm A dir> --b <abs arm B dir> --revert-log <abs file>
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_obs import parse  # noqa: E402

BUDGET = 2048
CAPTURE = [1, 2, 4, 6, 8]
BLOCK = 16
PRISTINE = {
    "vllm/v1/core/sched/scheduler.py": "41ff2e524c90d9aa72b72cd77492eb62ee2a729a773bd8233e970f39abbb5983",
    "vllm/v1/worker/gpu/model_runner.py": "c5332aad7701ef66ec75747adb62b34fd542835a834808a29b7dcd6c9f688a16",
}


def flag_on(server_log: Path) -> bool:
    return "'enable_prompt_tokens_details': True" in server_log.read_text(errors="replace")


def expected_step(toks: int, maxq: int) -> tuple[int, str]:
    if toks > max(CAPTURE):
        return toks, "NONE"
    padded = min(c for c in CAPTURE if c >= toks)
    return padded, ("FULL" if maxq == 1 else "PIECEWISE")


def g1(bdir: Path) -> dict:
    reqs = json.loads((bdir / "requests.json").read_text())
    summ = json.loads((bdir / "summary.json").read_text())
    log = bdir / "server.log"
    recs = parse(log)
    flag = flag_on(log)
    checks: dict = {"flag_prompt_tokens_details": flag}
    lookups = [r for r in recs if r["kind"] == "LOOKUP"]
    allocs = [r for r in recs if r["kind"] == "ALLOC"]
    fails = [r for r in recs if r["kind"] == "ALLOC_FAIL"]
    steps = [r for r in recs if r["kind"] == "STEP"]
    n_req = len(reqs)
    succ = summ["metric_delta_total"].get("vllm:request_success_total")
    checks["a_counts"] = {"requests": n_req, "lookup": len(lookups), "alloc": len(allocs),
                          "alloc_fail": len(fails), "request_success_delta": succ}
    checks["a_pass"] = (len(lookups) == len(allocs) == n_req == succ and not fails)

    # b: hit per request, joined by id prefix; absence of cached_tokens reads 0 only if flag on
    mism = []
    for r in reqs:
        cand = [x for x in lookups if str(x["req"]).startswith(r["id"])]
        obs = r["cached_tokens"]
        obs0 = obs if obs is not None else (0 if flag else None)
        row = {"tag": r["tag"], "log_hit": [c["hit"] for c in cand], "resp": obs0}
        if r["phase"] == "seq":
            row["counter_cached"] = r["metric_delta"].get("vllm:prompt_tokens_cached_total")
            row["counter_hits"] = r["metric_delta"].get("vllm:prefix_cache_hits_total")
        ok = (len(cand) == 1 and obs0 is not None and cand[0]["hit"] == obs0
              and (r["phase"] != "seq" or (row["counter_cached"] == obs0 == row["counter_hits"])))
        if not ok:
            mism.append(row)
    checks["b_hit_mismatches"] = mism
    checks["b_pass"] = not mism

    # Revision 1 (GPU_OBS_GATE_PREREG.md section 8): the server's startup warmup
    # executes non-dummy steps before any request; (c) and (d) count from the
    # first LOOKUP, and the warmup steps are reported separately.
    first_line = lookups[0]["line"]
    warm = [s for s in steps if s["line"] < first_line]
    checks["warmup_steps_report_only"] = [
        {k: s[k] for k in ("reqs", "toks", "maxq", "padded", "mode")} for s in warm]
    steps = [s for s in steps if s["line"] > first_line]

    # c: total scheduled tokens
    exp_toks = sum(r["prompt_tokens"] - (r["cached_tokens"] or 0) + r["completion_tokens"] - 1
                   for r in reqs)
    obs_toks = sum(s["toks"] for s in steps)
    checks["c_tokens"] = {"expected": exp_toks, "observed": obs_toks}
    checks["c_pass"] = exp_toks == obs_toks

    # d: sequential step count (between the first LOOKUP and the first concurrent LOOKUP)
    seq = [r for r in reqs if r["phase"] == "seq"]
    first_conc_line = lookups[len(seq)]["line"]
    seq_steps = [s for s in steps if s["line"] < first_conc_line]
    exp_steps = sum(math.ceil((r["prompt_tokens"] - (r["cached_tokens"] or 0)) / BUDGET)
                    + r["completion_tokens"] - 1 for r in seq)
    checks["d_seq_steps"] = {"expected": exp_steps, "observed": len(seq_steps)}
    checks["d_pass"] = exp_steps == len(seq_steps)

    # e: dispatch mapping on every step
    bad = [s for s in steps + warm
           if (s["padded"], s["mode"]) != expected_step(s["toks"], s["maxq"])]
    checks["e_mapping_violations"] = bad[:20]
    checks["e_n_violations"] = len(bad)
    checks["e_pass"] = not bad

    # f: KV events — no removals; every H-case seed prompt block stored with that content
    evs = [json.loads(x) for x in (bdir / "kv_events.jsonl").read_text().splitlines()]
    stored = set()
    removed = 0
    for b in evs:
        for e in b["events"]:
            if e["type"] == "BlockStored":
                toks = e["token_ids"]
                bs = e["block_size"]
                for i in range(0, len(toks), bs):
                    stored.add(tuple(toks[i:i + bs]))
            elif e["type"] == "BlockRemoved":
                removed += len(e["block_hashes"])
    missing = 0
    total = 0
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launch"))
    from gate_run import sequential_plan  # noqa: E402
    for tag, prompt, _ in sequential_plan():
        if tag.endswith("_seed"):
            for i in range(len(prompt) // BLOCK):
                total += 1
                if tuple(prompt[i * BLOCK:(i + 1) * BLOCK]) not in stored:
                    missing += 1
    checks["f_kv"] = {"batches": len(evs), "removed_blocks": removed,
                      "seed_prompt_blocks": total, "missing_in_stored": missing}
    checks["f_pass"] = removed == 0 and missing == 0 and total > 0
    checks["G1"] = all(checks[k] for k in ("a_pass", "b_pass", "c_pass", "d_pass", "e_pass", "f_pass"))
    return checks


def g2(adir: Path, bdir: Path) -> dict:
    A = {r["tag"]: r for r in json.loads((adir / "requests.json").read_text())}
    B = {r["tag"]: r for r in json.loads((bdir / "requests.json").read_text())}
    seq_tags = [t for t, r in A.items() if r["phase"] == "seq"]
    ident = {t: A[t]["token_ids"] == B[t]["token_ids"] for t in seq_tags}
    conc_ident = {t: A[t]["token_ids"] == B[t]["token_ids"] for t in A if A[t]["phase"] == "conc"}
    ratios = [B[t]["elapsed_s"] / A[t]["elapsed_s"] for t in seq_tags]
    med = statistics.median(ratios)
    sa = json.loads((adir / "summary.json").read_text())
    sb = json.loads((bdir / "summary.json").read_text())
    return {
        "seq_identical": sum(ident.values()), "seq_total": len(seq_tags),
        "non_identical": [t for t, v in ident.items() if not v],
        "conc_identical_report_only": conc_ident,
        "elapsed_ratio_B_over_A": {"median": med, "min": min(ratios), "max": max(ratios),
                                   "per_tag": dict(zip(seq_tags, ratios))},
        "server_cpu_s_workload": {"A": sa["server_cpu_s_workload"], "B": sb["server_cpu_s_workload"]},
        "collector_cpu_s_workload_B": sb["collector_cpu_s_workload"],
        "validity": {"A": sa["valid"], "B": sb["valid"]},
        "G2": all(ident.values()) and 0.90 <= med <= 1.10,
    }


def g3(revert_log: Path) -> dict:
    text = revert_log.read_text()
    got = dict(re.findall(r"^(vllm/\S+) ([0-9a-f]{64})$", text, re.M))
    ok = "reverted. state=pristine" in text and all(got.get(k) == v for k, v in PRISTINE.items())
    return {"sha_after_revert": got, "G3": ok}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--revert-log", required=True)
    ap.add_argument("--out", required=True)
    x = ap.parse_args()
    res = {"G1": g1(Path(x.b)), "G2": g2(Path(x.a), Path(x.b)), "G3": g3(Path(x.revert_log))}
    Path(x.out).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v[k] for k, v in res.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
