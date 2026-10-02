#!/usr/bin/env python3
"""GTASK07 function check: token-id prompts with streaming (directive G-03 3.2).

Two sessions x three turns on a fresh server. Each turn is sent as a list of
token ids with ``return_token_ids`` and ``ignore_eos``, streamed with
``include_usage``; the generated ids are collected from the chunk deltas and
the next prompt is ``previous prompt ids + generated ids + 8 new ids``.
Checks per turn: delta ids = completion_tokens = max_tokens; turn >= 1
cached_tokens = floor((prev_prompt + prev_gen - 1) / 16) * 16 (GTASK02 hit
formula with generated tokens cached). A non-streaming turn is sent too.
Not a measurement: nothing here is timed or used for a prediction.

usage: tokid_check.py --out-dir <abs>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "launch"))
from lifecycle import Lifecycle, base_args  # noqa: E402


def stream(base: str, ids: list[int], max_tokens: int) -> dict:
    body = {"model": "Qwen/Qwen3-4B", "prompt": ids, "max_tokens": max_tokens,
            "temperature": 0.0, "top_p": 1.0, "seed": 20260929, "ignore_eos": True,
            "return_token_ids": True, "stream": True,
            "stream_options": {"include_usage": True}}
    req = urllib.request.Request(base + "/v1/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    gen, usage, chunks, prompt_ids = [], None, 0, None
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            obj = json.loads(line[5:])
            for ch in obj.get("choices") or []:
                if ch.get("prompt_token_ids") is not None:
                    prompt_ids = ch["prompt_token_ids"]
                if ch.get("token_ids"):
                    gen += ch["token_ids"]
                    chunks += 1
            if obj.get("usage"):
                usage = obj["usage"]
    d = (usage or {}).get("prompt_tokens_details")
    return {"gen": gen, "chunks": chunks, "usage": usage,
            "cached": d.get("cached_tokens") if isinstance(d, dict) else None,
            "prompt_echo_equal": prompt_ids == ids if prompt_ids is not None else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    rng = random.Random(20261007)
    args = base_args(num_gpu_blocks=2048, max_num_seqs=8, max_num_batched_tokens=2048,
                     capture_sizes=[1, 2, 4, 8, 16])
    rows = []
    with Lifecycle(a.out_dir, args, obs=False, kv_events=False) as lc:
        for s in range(2):
            ids = [rng.randrange(1000, 150000) for _ in range(1000 + 137 * s)]
            prev = None
            for t in range(3):
                mt = (33, 150, 64)[t]
                r = stream(lc.base, ids, mt)
                exp = None if prev is None else (prev[0] + prev[1] - 1) // 16 * 16
                cached = r["cached"] if r["cached"] is not None else 0   # flag on: absent = 0
                rows.append({"session": s, "turn": t, "prompt_len": len(ids), "max_tokens": mt,
                             "gen_ids": len(r["gen"]), "chunks": r["chunks"],
                             "completion_tokens": r["usage"]["completion_tokens"],
                             "prompt_tokens": r["usage"]["prompt_tokens"],
                             "cached_raw": r["cached"], "expected_cached": exp,
                             "prompt_echo_equal": r["prompt_echo_equal"],
                             "ok": (len(r["gen"]) == mt == r["usage"]["completion_tokens"]
                                    and r["usage"]["prompt_tokens"] == len(ids)
                                    and (exp is None or cached == exp))})
                prev = (len(ids), len(r["gen"]))
                ids = ids + r["gen"] + [rng.randrange(1000, 150000) for _ in range(8)]
        valid, reasons = lc.valid() if hasattr(lc, "valid") else (None, [])
    out = {"rows": rows, "all_ok": all(r["ok"] for r in rows)}
    (a.out_dir / "tokid_check.json").write_text(json.dumps(out, indent=1))
    for r in rows:
        print(r)
    print("ALL_OK", out["all_ok"])
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
