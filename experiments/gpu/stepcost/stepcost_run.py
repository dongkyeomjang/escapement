#!/usr/bin/env python3
"""GTASK05 step-cost measurement (prereg: docs/research/gpu/GPU_STEPCOST_PREREG.md).

One lifecycle = one capture grid. Three phases, all timed from the
observation patch's [GSTEP] dispatch lines (the analysis attributes step
costs; this driver only produces the load):

  FULL   n = 1..16 concurrent decoders (prompt 64, max_tokens 128), one batch
         at a time -> long homogeneous decode segments of width n.
  MIXED  d background decoders (streamed, aborted after the phase) + a
         sequence of probes with prompt p and max_tokens 1, one at a time ->
         isolated steps of d decodes + one p-token prefill.
  EAGER  same as MIXED with larger p (> top capture size).

usage: stepcost_run.py --grid G1|G2|G3 --rep N --out-dir <abs>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "launch"))
from client import completion, rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, patch_state  # noqa: E402

GRIDS = {
    "G1": [1, 2, 4, 8, 16],             # default list at max_num_seqs=8
    "G2": [1, 2, 4, 6, 8],              # GTASK02 L2 list
    "G3": list(range(1, 17)),           # continuous 1..16
}
NUM_GPU_BLOCKS = 4096
MAX_NUM_SEQS = 16
BUDGET = 2048
FULL_N = list(range(1, 17))
FULL_PROMPT, FULL_GEN = 64, 128
MIXED_D = [1, 2, 4, 8]   # d >= 1: with no decoder the engine idles and dispatch gaps include idle time
MIXED_P = [2, 4, 8]
EAGER_D = [1, 4]
EAGER_P = [32, 64, 128, 256, 512, 1024, 2048]
REPS_MIXED, REPS_EAGER = 20, 10
BG_PROMPT, BG_GEN = 64, 3000


class Background:
    """d streamed decoders; closing the streams aborts them server-side."""

    def __init__(self, base: str, d: int, seed: int):
        self.resps = []
        self.threads = []
        self.stop = threading.Event()
        for j in range(d):
            body = {"model": "Qwen/Qwen3-4B", "prompt": rand_ids(seed + j, BG_PROMPT),
                    "max_tokens": BG_GEN, "temperature": 0.0, "ignore_eos": True, "stream": True}
            req = urllib.request.Request(base + "/v1/completions", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=600)
            self.resps.append(r)
            t = threading.Thread(target=self._drain, args=(r,), daemon=True)
            t.start()
            self.threads.append(t)

    def _drain(self, r) -> None:
        try:
            while not self.stop.is_set():
                if not r.readline():
                    break
        except Exception:
            pass

    def close(self) -> None:
        self.stop.set()
        for r in self.resps:
            try:
                r.close()
            except Exception:
                pass


def mark(tag: str, events: list) -> None:
    events.append({"tag": tag, "wall": time.time()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", choices=tuple(GRIDS), required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    if "state: patched" not in patch_state():
        raise SystemExit("observation patch must be applied")
    args = base_args(num_gpu_blocks=NUM_GPU_BLOCKS, max_num_seqs=MAX_NUM_SEQS,
                     max_num_batched_tokens=BUDGET, capture_sizes=GRIDS[a.grid])
    seed = 20261100 + 100000 * a.rep + {"G1": 0, "G2": 30000, "G3": 60000}[a.grid]
    events: list = []
    with Lifecycle(out, args, obs=True, kv_events=False) as lc:
        base = lc.base
        m0 = scrape(base)
        # FULL
        for n in FULL_N:
            mark(f"FULL n={n} start", events)
            res: list = [None] * n

            def w(j, n=n, res=res):
                res[j] = completion(base, rand_ids(seed + 1000 * n + j, FULL_PROMPT), FULL_GEN)

            ts = [threading.Thread(target=w, args=(j,)) for j in range(n)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            mark(f"FULL n={n} end", events)
            time.sleep(0.3)
        # MIXED and EAGER
        for phase, ds, ps, reps in (("MIXED", MIXED_D, MIXED_P, REPS_MIXED),
                                     ("EAGER", EAGER_D, EAGER_P, REPS_EAGER)):
            for d in ds:
                bg = Background(base, d, seed + 50000 + 100 * d + (0 if phase == "MIXED" else 7))
                time.sleep(1.5)  # let the decoders reach steady decode
                for p in ps:
                    mark(f"{phase} d={d} p={p} start", events)
                    for r in range(reps):
                        completion(base, rand_ids(seed + 70000 + 1000 * p + 10 * d + r
                                                  + (0 if phase == "MIXED" else 500000), p), 1)
                        time.sleep(0.05)
                    mark(f"{phase} d={d} p={p} end", events)
                bg.close()
                time.sleep(1.5)
        m1 = scrape(base)
        ok, why = lc.valid()
        summary = {"grid": a.grid, "rep": a.rep, "valid": ok, "invalid_reasons": why,
                   "metric_delta": {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}}
    (out / "events.json").write_text(json.dumps(events, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
