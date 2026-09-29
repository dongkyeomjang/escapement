#!/usr/bin/env python3
"""GTASK03 gate workload: one lifecycle per arm.

  arm A — pristine vLLM, ESCAPEMENT_OBS unset, no KV events
  arm B — patched vLLM, ESCAPEMENT_OBS=1, KV events + collector

Same requests in both arms (docs/research/gpu/GPU_OBS_GATE_PREREG.md):
15 sequential requests (text x3, hit cases H1-H4b seed/probe, H5 seed/probe)
then a 3-way and a 5-way concurrent batch. Sequential requests get a metrics
scrape before and after (counter deltas are attributable only there).

usage: gate_run.py --arm A|B --out-dir <abs>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launch"))
from client import PROMPT_TEXT, completion, rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402

CAPTURE = [1, 2, 4, 6, 8]


def sequential_plan() -> list[tuple[str, object, int]]:
    plan: list[tuple[str, object, int]] = [(f"text_r{i}", PROMPT_TEXT, 64) for i in (1, 2, 3)]
    cases = [("H1", 1000, 1000, 1000), ("H2", 1024, 1024, 1024), ("H3", 800, 500, 800),
             ("H4a", 16, 16, 16), ("H4b", 17, 17, 17)]
    for idx, (name, seed_len, shared, query) in enumerate(cases):
        seed_ids = rand_ids(20260929 + 100 * idx, seed_len)
        probe = seed_ids[:shared] + rand_ids(20260929 + 100 * idx + 1, query - shared)
        plan.append((f"{name}_seed", seed_ids, 1))
        plan.append((f"{name}_probe", probe, 1))
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("A", "B"), required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    patched = a.arm == "B"
    st = patch_state()
    want = "state: patched" if patched else "state: pristine"
    if want not in st:
        raise SystemExit(f"arm {a.arm} requires '{want}', got:\n{st}")

    extra = kv_events_args() if patched else []
    args = base_args(num_gpu_blocks=2048, max_num_seqs=8, max_num_batched_tokens=2048,
                     capture_sizes=CAPTURE, extra=extra)
    rows: list[dict] = []
    with Lifecycle(out, args, obs=patched, kv_events=patched) as lc:
        base = lc.base
        cpu0, col0 = lc.server_cpu_s(), lc.collector_cpu_s()
        m_start = scrape(base)
        for tag, prompt, mt in sequential_plan():
            m0 = scrape(base)
            r = completion(base, prompt, mt)
            m1 = scrape(base)
            r.update(tag=tag, phase="seq", max_tokens=mt,
                     metric_delta={k: m1.get(k, 0) - m0.get(k, 0) for k in m1})
            rows.append(r)
        # H5: generated tokens appended to the probe
        seed = rand_ids(20261929, 1000)
        m0 = scrape(base)
        r = completion(base, seed, 40)
        m1 = scrape(base)
        r.update(tag="H5_seed", phase="seq", max_tokens=40,
                 metric_delta={k: m1.get(k, 0) - m0.get(k, 0) for k in m1})
        rows.append(r)
        probe = seed + (r["token_ids"] or []) + rand_ids(20261930, 5)
        m0 = scrape(base)
        r = completion(base, probe, 1)
        m1 = scrape(base)
        r.update(tag="H5_probe", phase="seq", max_tokens=1,
                 metric_delta={k: m1.get(k, 0) - m0.get(k, 0) for k in m1})
        rows.append(r)
        # concurrency blocks
        for k in (3, 5):
            res: list = [None] * k

            def worker(j: int, k=k, res=res) -> None:
                res[j] = completion(base, f"{PROMPT_TEXT} ({k}-{j})", 64)

            ts = [threading.Thread(target=worker, args=(j,)) for j in range(k)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            for j, r in enumerate(res):
                r.update(tag=f"conc{k}_{j}", phase="conc", max_tokens=64)
                rows.append(r)
        time.sleep(3)
        m_end = scrape(base)
        cpu1, col1 = lc.server_cpu_s(), lc.collector_cpu_s()
        ok, why = lc.valid()
        summary = {
            "arm": a.arm, "valid": ok, "invalid_reasons": why,
            "server_cpu_s_workload": None if cpu0 is None else cpu1 - cpu0,
            "collector_cpu_s_workload": None if col0 is None else col1 - col0,
            "metric_delta_total": {k: m_end.get(k, 0) - m_start.get(k, 0) for k in m_end},
        }
    (out / "requests.json").write_text(json.dumps(rows, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
