#!/usr/bin/env python3
"""G-10 A: one short development lifecycle for the exec-timing ON/OFF check.

Prereg: docs/research/gpu/G10_A_PREREG.md. A controlled closed-loop load (not
a multi-turn plan; no validation seed is used): ``clients`` threads, each
sending its own fixed sequence of requests back to back -- random-id prompts
of U(1000, 3000) tokens (seeded per pair and client, so ON and OFF of one pair
send identical prompts), 128 generated tokens, ignore_eos, streaming. No
prefix is shared. Load ``low`` = 2 clients, ``sat`` = 16 clients (> max_num_seqs
8: the engine is saturated and a queue forms).

Timeline after the server is ready: warm-up WARM_S, window WIN_S (wall clock),
then no new request; in-flight requests finish. Server arguments = GPU_BASE /
GPU_KV of G-10 (1,900 / 2,300 blocks, grid (1,2,4,8,16), max_num_seqs 8,
budget 2,048), observation patch logs and KV events on in both arms; the arm
differs only in ``ESCAPEMENT_EXEC`` (1 = exec-timing layer active).

usage: exec_check_run.py --config GPU_BASE|GPU_KV --load low|sat --exec 0|1
                         --pair K --out-dir <abs>
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
import json
from pathlib import Path
import random
import statistics
import sys
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "launch"))
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(HERE))
from client import rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402
from parse_obs import parse  # noqa: E402
from exec_measure import gexec, _tkey  # noqa: E402

CARD_UUID = "GPU-4485e769-430a-430d-3383-b9c4ce92a175"
POOLS = {"GPU_BASE": 1900, "GPU_KV": 2300}
GRID = [1, 2, 4, 8, 16]
CLIENTS = {"low": 2, "sat": 16}
GEN, WARM_S, WIN_S = 128, 15.0, 60.0
SEED0 = 20264900


def stream(base: str, prompt: list, times: list, origin: float) -> int:
    body = {"model": "Qwen/Qwen3-4B", "prompt": prompt, "max_tokens": GEN, "temperature": 0.0,
            "top_p": 1.0, "seed": 20260929, "ignore_eos": True, "return_token_ids": True,
            "stream": True, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(base + "/v1/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    n = 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            obj = json.loads(data)
            for ch in obj.get("choices") or []:
                k = len(ch.get("token_ids") or [])
                if k:
                    times.extend([time.perf_counter() - origin] * k)
                    n += k
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=sorted(POOLS))
    ap.add_argument("--load", required=True, choices=sorted(CLIENTS))
    ap.add_argument("--exec", type=int, required=True, choices=(0, 1))
    ap.add_argument("--pair", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    if not out.is_absolute():
        raise SystemExit("out-dir must be absolute (KNOWN_PITFALLS 1)")
    out.mkdir(parents=True, exist_ok=True)
    ps = patch_state()
    if "state: patched" not in ps or "exec_layer: present" not in ps:
        raise SystemExit("observation patch with the exec-timing layer must be applied")
    args = base_args(num_gpu_blocks=POOLS[a.config], max_num_seqs=8, max_num_batched_tokens=2048,
                     capture_sizes=GRID, extra=kv_events_args())
    env = {"ESCAPEMENT_EXEC": "1" if a.exec else "0"}
    nc = CLIENTS[a.load]
    bad: list = []
    with Lifecycle(out, args, obs=True, kv_events=True, extra_env=env) as lc:
        if lc.meta.get("gpu0_uuid") != CARD_UUID:
            bad.append(f"card {lc.meta.get('gpu0_uuid')} != {CARD_UUID}")
        base = lc.base
        m0 = scrape(base)
        origin = time.perf_counter()
        wall0 = time.time()
        stop = threading.Event()
        times: list[list[float]] = [[] for _ in range(nc)]
        counts = [0] * nc

        def client(c: int) -> None:
            rng = random.Random(SEED0 + 1000 * a.pair + c)
            j = 0
            while not stop.is_set() and time.perf_counter() - origin < WARM_S + WIN_S:
                L = rng.randint(1000, 3000)
                p = rand_ids(SEED0 + 100000 * (1 + a.pair) + 1000 * c + j, L)
                got = stream(base, p, times[c], origin)
                if got != GEN:
                    bad.append(f"client {c} request {j} generated {got}")
                counts[c] += 1
                j += 1

        ts = [threading.Thread(target=client, args=(c,)) for c in range(nc)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        m1 = scrape(base)
        ok, why = lc.valid()
    delta = {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}
    if delta.get("vllm:num_preemptions_total", 0):
        bad.append("preemption")
    allt = sorted(x for ts_ in times for x in ts_)
    tok_win = bisect_left(allt, WARM_S + WIN_S) - bisect_left(allt, WARM_S)
    # server steps in the wall window
    ev = [e for e in parse(out / "server.log") if e["kind"] == "STEP"]
    w_lo, w_hi = wall0 + WARM_S, wall0 + WARM_S + WIN_S
    idx = [i for i, e in enumerate(ev) if w_lo <= e["wall"] < w_hi]
    gaps: dict[int, list] = {}
    for i in idx:
        if i + 1 < len(ev):
            e, f = ev[i], ev[i + 1]
            if e["maxq"] == 1 and e["mode"] == "FULL" and f["maxq"] == 1 and f["mode"] == "FULL":
                gaps.setdefault(e["reqs"], []).append((f["t"] - e["t"]) * 1e3)
    span = (ev[idx[-1]]["t"] - ev[idx[0]]["t"]) if len(idx) > 1 else None
    gx = gexec(out / "server.log")
    exec_win = [gx.get(_tkey(ev[i]["t"])) for i in idx]
    missing = sum(1 for x in exec_win if x is None)
    have = [x for x in exec_win if x is not None]
    # overlap tolerance 0.01 ms: s, prep, run are each printed with %.4f and the
    # event timer resolves about 0.5 us, so stream-ordered steps can show < 10 us
    overl = sum(1 for x, y in zip(have, have[1:]) if y["s"] < x["s"] + x["prep"] + x["run"] - 0.01)
    dev_span = ((have[-1]["s"] + have[-1]["prep"] + have[-1]["run"] - have[0]["s"]) / 1e3) if have else None
    full_exec: dict[int, list] = {}
    for i in idx:
        x = gx.get(_tkey(ev[i]["t"]))
        if x is not None and ev[i]["maxq"] == 1 and ev[i]["mode"] == "FULL":
            full_exec.setdefault(ev[i]["reqs"], []).append(x["prep"] + x["run"])
    summary = {
        "config": a.config, "load": a.load, "exec": a.exec, "pair": a.pair, "clients": nc,
        "valid": ok and not bad, "invalid_reasons": why + bad, "metric_delta": delta,
        "requests": sum(counts), "tokens_in_window": tok_win, "throughput_tok_s": tok_win / WIN_S,
        "window_steps": len(idx), "window_step_span_s": span,
        "full_decode_gap_median_ms": {str(k): statistics.median(v) for k, v in sorted(gaps.items())},
        "full_decode_gap_count": {str(k): len(v) for k, v in sorted(gaps.items())},
        "gexec_lines": len(gx), "gstep_lines": len(ev),
        "exec_missing_window": missing if a.exec else None,
        "exec_overlaps_window": overl if a.exec else None,
        "exec_sum_window_s": sum(x["prep"] + x["run"] for x in have) / 1e3 if a.exec else None,
        "exec_device_span_window_s": dev_span if a.exec else None,
        "full_decode_exec_median_ms": ({str(k): statistics.median(v) for k, v in sorted(full_exec.items())}
                                       if a.exec else None),
    }
    if a.exec == 1 and missing:
        summary["valid"] = False
        summary["invalid_reasons"].append(f"GEXEC missing for {missing} window steps")
    if a.exec == 0 and len(gx):
        summary["valid"] = False
        summary["invalid_reasons"].append("GEXEC lines with ESCAPEMENT_EXEC=0")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("config", "load", "exec", "pair", "valid", "throughput_tok_s",
                                              "window_steps", "exec_missing_window")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
