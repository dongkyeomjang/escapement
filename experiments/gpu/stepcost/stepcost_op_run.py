#!/usr/bin/env python3
"""GTASK17 (directive G-06 A): FULL decode step cost under serving conditions.

Prereg: docs/research/gpu/GPU_STEPCOST_OP_PREREG.md. One lifecycle = one
condition (stream on/off x KV events on/off x admission log on/off) with the
GTASK11 server arguments (BASE pool 1,900, max_num_seqs 8, grid
[1,2,4,8,16], budget 2,048, async scheduling default). The step log
(``[GSTEP]``) is always on; the admission log (``[GPFX]``) is turned off by a
vLLM logging config that raises ``vllm.v1.core.sched.scheduler`` to WARNING
(no patch change).

Load: REPEATS x (n = 1..8 concurrent decoders, prompt 64 random ids,
max_tokens GEN, ignore_eos), one batch at a time.

usage: stepcost_op_run.py --stream 0|1 --kv 0|1 --admlog 0|1 --rep N --out-dir <abs>
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "launch"))
from client import completion, rand_ids, scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402

CARD_UUID = "GPU-4485e769-430a-430d-3383-b9c4ce92a175"
NUM_GPU_BLOCKS, MAX_NUM_SEQS, BUDGET, GRID = 1900, 8, 2048, [1, 2, 4, 8, 16]
NS = list(range(1, 9))
PROMPT, GEN, REPEATS = 64, 256, 3


def logging_config(path: Path) -> None:
    """vLLM's default config plus the scheduler logger at WARNING."""
    from vllm.logger import DEFAULT_LOGGING_CONFIG
    cfg = copy.deepcopy(DEFAULT_LOGGING_CONFIG)
    cfg["handlers"]["vllm"]["formatter"] = "vllm"
    cfg["handlers"]["vllm"]["level"] = "INFO"
    cfg["handlers"]["vllm"]["stream"] = "ext://sys.stdout"
    cfg["loggers"]["vllm"]["level"] = "INFO"
    cfg["loggers"]["vllm.v1.core.sched.scheduler"] = {"level": "WARNING", "propagate": True}
    path.write_text(json.dumps(cfg, indent=1))


def stream_completion(base: str, prompt: list, max_tokens: int) -> dict:
    body = {"model": "Qwen/Qwen3-4B", "prompt": prompt, "max_tokens": max_tokens,
            "temperature": 0.0, "top_p": 1.0, "seed": 20260929, "ignore_eos": True,
            "return_token_ids": True, "stream": True, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(base + "/v1/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    n = 0
    usage = None
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
                n += len(ch.get("token_ids") or [])
            if obj.get("usage"):
                usage = obj["usage"]
    return {"tokens": n, "completion_tokens": (usage or {}).get("completion_tokens")}


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("stream", "kv", "admlog"):
        ap.add_argument(f"--{k}", type=int, choices=(0, 1), required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if "state: patched" not in patch_state():
        raise SystemExit("observation patch must be applied")
    extra = kv_events_args() if a.kv else []
    args = base_args(num_gpu_blocks=NUM_GPU_BLOCKS, max_num_seqs=MAX_NUM_SEQS,
                     max_num_batched_tokens=BUDGET, capture_sizes=GRID, extra=extra)
    env = {}
    if not a.admlog:
        lc_path = out / "logging_config.json"
        logging_config(lc_path)
        env["VLLM_LOGGING_CONFIG_PATH"] = str(lc_path)
    cond = f"s{a.stream}k{a.kv}a{a.admlog}"
    seed = 20262700 + 10000 * a.rep + 1000 * (4 * a.stream + 2 * a.kv + a.admlog)
    events: list = []
    bad: list = []
    with Lifecycle(out, args, obs=True, kv_events=bool(a.kv), extra_env=env) as lc:
        if lc.meta.get("gpu0_uuid") != CARD_UUID:
            bad.append(f"card {lc.meta.get('gpu0_uuid')} != {CARD_UUID}")
        base = lc.base
        m0 = scrape(base)
        for rep in range(REPEATS):
            for n in NS:
                events.append({"tag": f"FULL n={n} k={rep} start", "wall": time.time()})
                res: list = [None] * n

                def w(j, n=n, res=res, rep=rep):
                    p = rand_ids(seed + 100 * rep + 10 * n + j, PROMPT)
                    if a.stream:
                        r = stream_completion(base, p, GEN)
                        res[j] = r["tokens"]
                    else:
                        res[j] = completion(base, p, GEN)["completion_tokens"]

                ts = [threading.Thread(target=w, args=(j,)) for j in range(n)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                events.append({"tag": f"FULL n={n} k={rep} end", "wall": time.time()})
                if any(x != GEN for x in res):
                    bad.append(f"n={n} k={rep} generated {res}")
                time.sleep(0.3)
        m1 = scrape(base)
        ok, why = lc.valid()
    delta = {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}
    if delta.get("vllm:num_preemptions_total", 0):
        bad.append("preemption")
    log = (out / "server.log").read_text(errors="replace")
    n_gpfx = log.count("[GPFX]")
    if a.admlog and n_gpfx == 0:
        bad.append("admission log expected but absent")
    if not a.admlog and n_gpfx:
        bad.append(f"admission log present ({n_gpfx}) though disabled")
    if log.count("[GSTEP]") == 0:
        bad.append("no step log")
    summary = {"condition": cond, "stream": a.stream, "kv": a.kv, "admlog": a.admlog, "rep": a.rep,
               "valid": ok and not bad, "invalid_reasons": why + bad, "gpfx_lines": n_gpfx,
               "metric_delta": delta}
    (out / "events.json").write_text(json.dumps(events, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
