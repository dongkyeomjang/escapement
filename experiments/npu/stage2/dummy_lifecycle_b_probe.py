#!/usr/bin/env python3
"""Experiment B of the dummy-block lifecycle observation (exploratory).

Eight requests arrive one at a time with a fixed spacing and all ask for the
same number of tokens. Arrivals ramp the number of running decoders up to the
execution ceiling (8 on the b8 artifact) and completions, which come in arrival
order, ramp it back down -- so one run passes through n < 8, n = 8, and n < 8
again. Prompts are short (< 129 tokens) and distinct, so no prefix is reused.

Only request bookkeeping is recorded here; the observations themselves come
from the server's [OBS]/[PFX]/[BUCKET] log lines.

Registered in docs/research/DUMMY_LIFECYCLE_PLAN.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request


def post(base: str, model: str, prompt: str, max_tokens: int, seed: int) -> dict:
    payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens,
               "temperature": 0.0, "top_p": 1.0, "seed": seed, "stream": False,
               "ignore_eos": True}
    req = urllib.request.Request(f"{base}/v1/completions", data=json.dumps(payload).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            body = json.loads(resp.read().decode())
            return {"status": resp.status, "usage": body.get("usage")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "usage": None, "error": e.read().decode("utf-8", "replace")[:500]}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--prompt-file", required=True, type=Path)
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--spacing-s", type=float, default=0.3)
    p.add_argument("--max-tokens", type=int, default=384)
    p.add_argument("--seed", type=int, default=20260819)
    p.add_argument("--tag", required=True)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    with urllib.request.urlopen(f"{base}/v1/models", timeout=30) as r:
        model = json.loads(r.read().decode())["data"][0]["id"]
    text = args.prompt_file.read_text().strip()

    records: list[dict] = [{} for _ in range(args.n)]
    t0 = time.time() + 0.5

    def worker(i: int) -> None:
        delay = t0 + i * args.spacing_s - time.time()
        if delay > 0:
            time.sleep(delay)
        sent = time.time()
        r = post(base, model, f"[{i}] {text}", args.max_tokens, args.seed)
        records[i] = {"index": i, "sent_s": sent, "done_s": time.time(), **r}

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = {"tag": args.tag, "n": args.n, "spacing_s": args.spacing_s,
           "max_tokens": args.max_tokens, "seed": args.seed, "t0": t0, "records": records}
    (args.output_dir / f"dummy_b.{args.tag}.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"tag": args.tag,
                      "statuses": sorted({r.get("status") for r in records}),
                      "completion_tokens": sorted({(r.get("usage") or {}).get("completion_tokens")
                                                   for r in records})}))
    return 0 if all(r.get("status") == 200 for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
