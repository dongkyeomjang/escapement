"""Minimal OpenAI-completions client for the GPU drivers (stdlib only).

``cached_tokens`` absent from the response is returned as ``None``, never 0
(KNOWN_PITFALLS 6). Whether absence may be read as 0 is decided by the
analysis, and only for a run whose server log shows
``enable_prompt_tokens_details: True`` (vllm 0.22.0 omits the field when the
value is 0: entrypoints/openai/completion/serving.py:586).
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.request

COUNTERS = (
    "vllm:prompt_tokens_cached_total",
    "vllm:prefix_cache_hits_total",
    "vllm:prefix_cache_queries_total",
    "vllm:num_preemptions_total",
    "vllm:prompt_tokens_total",
    "vllm:generation_tokens_total",
    "vllm:request_success_total",
)

PROMPT_TEXT = "Explain in two sentences what a neural processing unit is."


def post(base: str, path: str, body: dict, timeout: float = 600.0) -> tuple[dict, float, float]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    w0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return out, time.perf_counter() - t0, w0


def scrape(base: str) -> dict[str, float]:
    with urllib.request.urlopen(base + "/metrics", timeout=60) as r:
        text = r.read().decode()
    totals: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)$", line)
        if m and m.group(1) in COUNTERS:
            totals[m.group(1)] = totals.get(m.group(1), 0.0) + float(m.group(3))
    return totals


def completion(base: str, prompt, max_tokens: int, *, ignore_eos: bool = True,
               model: str = "Qwen/Qwen3-4B") -> dict:
    body = {"model": model, "prompt": prompt, "max_tokens": max_tokens,
            "temperature": 0.0, "top_p": 1.0, "seed": 20260929,
            "return_token_ids": True, "ignore_eos": ignore_eos}
    resp, dt, w0 = post(base, "/v1/completions", body)
    ch = resp["choices"][0]
    return {
        "id": resp.get("id"),
        "send_wall": w0,
        "elapsed_s": dt,
        "prompt_tokens": resp["usage"]["prompt_tokens"],
        "completion_tokens": resp["usage"]["completion_tokens"],
        "cached_tokens": cached_tokens(resp),
        "finish_reason": ch.get("finish_reason"),
        "token_ids": ch.get("token_ids"),
        "text": ch.get("text"),
    }


def cached_tokens(resp: dict):
    details = (resp.get("usage") or {}).get("prompt_tokens_details")
    if details is None:
        return None
    return details.get("cached_tokens")


def rand_ids(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(1000, 150000) for _ in range(n)]
