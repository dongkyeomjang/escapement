#!/usr/bin/env python3
"""GPU Stage 0 client probe (GTASK02). Talks to a running vLLM OpenAI server.

Sequential requests only (no per-request attribution from counters under
concurrency -- KNOWN_PITFALLS 3). The concurrency block at the end exists only
to put 3 and 5 requests in one decode batch for the cudagraph padding table;
nothing is attributed per request there.

Everything the prereg (docs/research/gpu/GPU_STAGE0_PREREG.md) judges is
written raw to --out-dir; the script computes the machine-checkable items but
the verdict is recorded in the GTASK, not here.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import threading
import time
import urllib.request
from pathlib import Path

PROMPT_TEXT = "Explain in two sentences what a neural processing unit is."
BLOCK = 16  # prereg: --block-size 16 on L2/L3; L1 resolves the default (predicted 16)

COUNTERS = (
    "vllm:prompt_tokens_cached_total",
    "vllm:prefix_cache_hits_total",
    "vllm:prefix_cache_queries_total",
    "vllm:num_preemptions_total",
    "vllm:prompt_tokens_total",
)


def post(base: str, path: str, body: dict, timeout: float = 600.0) -> tuple[dict, float]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return out, time.time() - t0


def get_text(base: str, path: str) -> str:
    with urllib.request.urlopen(base + path, timeout=60) as r:
        return r.read().decode()


def scrape(base: str) -> dict[str, float]:
    """Sum every sample of each counter of interest (all label sets)."""
    text = get_text(base, "/metrics")
    totals: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)$", line)
        if not m:
            continue
        name, value = m.group(1), m.group(3)
        if name in COUNTERS:
            totals[name] = totals.get(name, 0.0) + float(value)
    return totals


def completion(base: str, model: str, prompt, max_tokens: int, *, ignore_eos: bool = False) -> tuple[dict, float]:
    body = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 20260929,
        "return_token_ids": True,
    }
    if ignore_eos:
        body["ignore_eos"] = True
    return post(base, "/v1/completions", body)


def cached_tokens(resp: dict):
    """Observed cached_tokens. Absent details are recorded as None, not 0."""
    details = (resp.get("usage") or {}).get("prompt_tokens_details")
    if details is None:
        return None
    return details.get("cached_tokens")


def rand_ids(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(1000, 150000) for _ in range(n)]


def hit_formula(shared: int, query: int, block: int = BLOCK) -> int:
    return (min(shared, query - 1) // block) * block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8100")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--concurrency-block", action="store_true",
                    help="also send 3- and 5-way concurrent batches (padding table)")
    ap.add_argument("--stats-wait-s", type=float, default=15.0)
    args = ap.parse_args()

    out = Path(args.out_dir)
    if not out.is_absolute():
        raise SystemExit("--out-dir must be absolute (KNOWN_PITFALLS 1)")
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "requests.jsonl").open("w")

    def record(tag: str, req: dict, resp: dict, dt: float, m0: dict, m1: dict) -> dict:
        delta = {k: m1.get(k, 0.0) - m0.get(k, 0.0) for k in COUNTERS}
        row = {"tag": tag, "request": req, "response": resp, "elapsed_s": dt,
               "metric_delta": delta, "t_end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        log.write(json.dumps(row) + "\n")
        log.flush()
        return row

    base, model = args.base, args.model
    (out / "models.json").write_text(get_text(base, "/v1/models"))
    (out / "metrics_pre.txt").write_text(get_text(base, "/metrics"))
    summary: dict = {"hit_cases": [], "text_runs": []}

    # -- P1/P2: fixed text prompt, three sequential greedy runs ---------------
    for i in range(3):
        m0 = scrape(base)
        resp, dt = completion(base, model, PROMPT_TEXT, 64)
        m1 = scrape(base)
        row = record(f"text_r{i + 1}", {"prompt": PROMPT_TEXT, "max_tokens": 64}, resp, dt, m0, m1)
        ch = resp["choices"][0]
        summary["text_runs"].append({
            "run": i + 1,
            "prompt_tokens": resp["usage"]["prompt_tokens"],
            "completion_tokens": resp["usage"]["completion_tokens"],
            "finish_reason": ch.get("finish_reason"),
            "token_ids": ch.get("token_ids"),
            "text": ch.get("text"),
            "cached_tokens_observed": cached_tokens(resp),
            "metric_delta": row["metric_delta"],
            "elapsed_s": dt,
        })

    # -- P4: hit formula cases (token-id prompts, fresh ids per case) ---------
    cases = [
        # name, seed_len, probe = seed[:shared] + fresh (query - shared)
        ("H1_identical_1000", 1000, 1000, 1000),
        ("H2_identical_1024", 1024, 1024, 1024),
        ("H3_shared500_query800", 800, 500, 800),
        ("H4a_identical_16", 16, 16, 16),
        ("H4b_identical_17", 17, 17, 17),
    ]
    for idx, (name, seed_len, shared, query) in enumerate(cases):
        seed_ids = rand_ids(20260929 + 100 * idx, seed_len)
        probe_ids = seed_ids[:shared] + rand_ids(20260929 + 100 * idx + 1, query - shared)
        m0 = scrape(base)
        r_seed, dt_s = completion(base, model, seed_ids, 1)
        m1 = scrape(base)
        record(f"{name}_seed", {"prompt_len": seed_len, "max_tokens": 1}, r_seed, dt_s, m0, m1)
        r_probe, dt_p = completion(base, model, probe_ids, 1)
        m2 = scrape(base)
        row = record(f"{name}_probe", {"prompt_len": query, "shared": shared, "max_tokens": 1},
                     r_probe, dt_p, m1, m2)
        summary["hit_cases"].append({
            "case": name, "seed_len": seed_len, "shared": shared, "query": query,
            "predicted": hit_formula(shared, query),
            "seed_cached_observed": cached_tokens(r_seed),
            "probe_cached_observed": cached_tokens(r_probe),
            "probe_prompt_tokens": r_probe["usage"]["prompt_tokens"],
            "probe_metric_delta": row["metric_delta"],
        })

    # -- H5 (prediction only): are decode-generated tokens cached? -----------
    seed_ids = rand_ids(20261929, 1000)
    m0 = scrape(base)
    r_seed, dt_s = completion(base, model, seed_ids, 40, ignore_eos=True)
    m1 = scrape(base)
    record("H5_seed", {"prompt_len": 1000, "max_tokens": 40, "ignore_eos": True}, r_seed, dt_s, m0, m1)
    gen = r_seed["choices"][0].get("token_ids") or []
    probe_ids = seed_ids + gen + rand_ids(20261930, 5)
    r_probe, dt_p = completion(base, model, probe_ids, 1)
    m2 = scrape(base)
    row = record("H5_probe", {"prompt_len": len(probe_ids), "max_tokens": 1}, r_probe, dt_p, m1, m2)
    summary["h5"] = {
        "generated": len(gen),
        "query": len(probe_ids),
        "predicted_generated_cached": hit_formula(1000 + len(gen) - 1, len(probe_ids)),
        "alternative_prompt_only": hit_formula(1000, len(probe_ids)),
        "probe_cached_observed": cached_tokens(r_probe),
        "probe_metric_delta": row["metric_delta"],
    }

    # -- concurrency block: 3- and 5-way decode batches (padding table) ------
    if args.concurrency_block:
        summary["concurrency"] = []
        for k in (3, 5):
            results: list = [None] * k

            def worker(j: int) -> None:
                results[j] = completion(base, model, f"{PROMPT_TEXT} ({k}-{j})", 64, ignore_eos=True)

            threads = [threading.Thread(target=worker, args=(j,)) for j in range(k)]
            t0 = time.time()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            summary["concurrency"].append({
                "k": k, "wall_s": time.time() - t0,
                "completion_tokens": [r[0]["usage"]["completion_tokens"] for r in results],
            })
            for j, (resp, dt) in enumerate(results):
                log.write(json.dumps({"tag": f"conc{k}_{j}", "response": resp, "elapsed_s": dt}) + "\n")
        time.sleep(args.stats_wait_s)  # let at least one stats-log interval elapse

    (out / "metrics_post.txt").write_text(get_text(base, "/metrics"))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    log.close()
    print(json.dumps({k: v for k, v in summary.items() if k != "text_runs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
