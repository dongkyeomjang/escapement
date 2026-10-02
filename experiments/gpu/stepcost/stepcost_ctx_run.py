#!/usr/bin/env python3
"""GTASK18 (directive G-07 B): FULL decode step cost vs per-request context length.

Prereg: docs/research/gpu/GPU_STEPCOST_CTX_PREREG.md. One lifecycle = the
GTASK11 condition s1k1a1 (streaming client, KV events, admission log, step log)
with the GTASK11 BASE server arguments. Inside it, ROUNDS rounds; each round
visits every cell of ctx_order.json once (order shuffled per lifecycle and
round). A cell sends n concurrent decoders whose prompts are random ids of the
cell's context lengths, max_tokens GEN, ignore_eos, and waits for all of them.

usage: stepcost_ctx_run.py --rep N --out-dir <abs>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "launch"))
sys.path.insert(0, str(HERE))
from client import rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402
from stepcost_op_run import CARD_UUID, NUM_GPU_BLOCKS, MAX_NUM_SEQS, BUDGET, GRID, stream_completion  # noqa: E402

GEN, ROUNDS = 128, 3
ORDER = HERE / "ctx_order.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if "state: patched" not in patch_state():
        raise SystemExit("observation patch must be applied")
    order = json.loads(ORDER.read_text())
    rounds = order["lifecycles"][str(a.rep)]
    cells = {c["cell"]: c for c in order["cells"]}
    args = base_args(num_gpu_blocks=NUM_GPU_BLOCKS, max_num_seqs=MAX_NUM_SEQS,
                     max_num_batched_tokens=BUDGET, capture_sizes=GRID, extra=kv_events_args())
    seed0 = 20262800 + 100000 * a.rep
    events: list = []
    bad: list = []
    with Lifecycle(out, args, obs=True, kv_events=True) as lc:
        if lc.meta.get("gpu0_uuid") != CARD_UUID:
            bad.append(f"card {lc.meta.get('gpu0_uuid')} != {CARD_UUID}")
        base = lc.base
        m0 = scrape(base)
        for k, names in enumerate(rounds[:ROUNDS]):
            for ci, name in enumerate(names):
                lens = cells[name]["lens"]
                n = len(lens)
                tag = f"CTX {name} n={n} k={k}"
                events.append({"tag": tag + " start", "wall": time.time()})
                res: list = [None] * n

                def w(j, lens=lens, res=res, k=k, ci=ci):
                    p = rand_ids(seed0 + 1000 * k + 20 * ci + j, lens[j])
                    res[j] = stream_completion(base, p, GEN)["tokens"]

                ts = [threading.Thread(target=w, args=(j,)) for j in range(n)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                events.append({"tag": tag + " end", "wall": time.time()})
                if any(x != GEN for x in res):
                    bad.append(f"{tag} generated {res}")
                time.sleep(0.3)
        m1 = scrape(base)
        ok, why = lc.valid()
    delta = {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}
    if delta.get("vllm:num_preemptions_total", 0):
        bad.append("preemption")
    log = (out / "server.log").read_text(errors="replace")
    if log.count("[GSTEP]") == 0:
        bad.append("no step log")
    if log.count("[GPFX]") == 0:
        bad.append("admission log expected but absent")
    summary = {"condition": "s1k1a1", "rep": a.rep, "valid": ok and not bad,
               "invalid_reasons": why + bad, "metric_delta": delta}
    (out / "events.json").write_text(json.dumps(events, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
