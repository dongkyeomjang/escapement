#!/usr/bin/env python3
"""One repetition of the admission-eviction observation (exploratory).

Saturation: the eight background prompts of cliff trial B8r0 are sent strictly
sequentially, so the outer-block pool ends with one free slot (the padding
dummy's reserve) and seven inactive blocks. After a fixed idle, the treatment
sends two new 2,000-token prompts (X = B8r0 target, Y = B8r1 target) so that
the second admission may happen before any decode step:

  consecutive   X's request is written to its socket, then Y's immediately
                (no sleep), on two pre-opened connections; two threads read
                the responses afterwards.
  simultaneous  two threads, each holding a pre-opened connection, are released
                by a barrier and write their requests at the same moment.

Only request bookkeeping is recorded here: wall-clock send/response times
(time.time(), the same clock as the server's [OBS] t= fields), HTTP status,
the response id (a strict prefix of the server-side request id, TASK18), and
usage. The observations come from the server's [OBS]/[PFX]/[BUCKET] lines.

Exit codes: 0 done (treatment errors are data, not failures), 2 saturation
failed, 3 prompt check failed.

Registered in docs/research/ADMISSION_EVICTION_PLAN.md.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import itertools
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlparse
import urllib.request

MAX_SHARED_PREFIX_CHARS = 64


def payload(model: str, prompt: str, max_tokens: int, seed: int) -> bytes:
    return json.dumps({"model": model, "prompt": prompt, "max_tokens": max_tokens,
                       "temperature": 0.0, "top_p": 1.0, "seed": seed,
                       "stream": False}).encode()


def open_conn(base: str) -> http.client.HTTPConnection:
    u = urlparse(base)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=1800)
    conn.connect()
    return conn


def send(conn: http.client.HTTPConnection, body: bytes) -> None:
    conn.request("POST", "/v1/completions", body=body,
                 headers={"Content-Type": "application/json"})


def receive(conn: http.client.HTTPConnection) -> dict:
    try:
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", "replace")
        status = resp.status
    except Exception as e:  # connection-level failure is recorded, not raised
        return {"status": None, "response_s": time.time(), "response_id": None,
                "usage": None, "error": repr(e)[:1000]}
    t = time.time()
    try:
        body = json.loads(raw)
    except ValueError:
        body = None
    ok = isinstance(body, dict)
    return {"status": status, "response_s": t,
            "response_id": body.get("id") if ok else None,
            "usage": body.get("usage") if ok else None,
            "error": None if status == 200 else raw[:1000]}


def one_sequential(base: str, label: str, body: bytes) -> dict:
    conn = open_conn(base)
    t0 = time.time()
    send(conn, body)
    t1 = time.time()
    r = receive(conn)
    conn.close()
    return {"label": label, "send_start_s": t0, "send_end_s": t1, **r}


def treatment(base: str, mode: str, bodies: dict[str, bytes]) -> list[dict]:
    conns = {lab: open_conn(base) for lab in ("X", "Y")}
    rec: dict[str, dict] = {lab: {"label": lab} for lab in ("X", "Y")}

    def reader(lab: str) -> None:
        rec[lab].update(receive(conns[lab]))

    if mode == "consecutive":
        for lab in ("X", "Y"):
            rec[lab]["send_start_s"] = time.time()
            send(conns[lab], bodies[lab])
            rec[lab]["send_end_s"] = time.time()
        threads = [threading.Thread(target=reader, args=(lab,)) for lab in ("X", "Y")]
        for t in threads:
            t.start()
    else:  # simultaneous
        barrier = threading.Barrier(2)

        def fire(lab: str) -> None:
            barrier.wait()
            rec[lab]["send_start_s"] = time.time()
            send(conns[lab], bodies[lab])
            rec[lab]["send_end_s"] = time.time()
            reader(lab)

        threads = [threading.Thread(target=fire, args=(lab,)) for lab in ("X", "Y")]
        for t in threads:
            t.start()
    for t in threads:
        t.join()
    for c in conns.values():
        c.close()
    return [rec["X"], rec["Y"]]


def shared_prefix(a: str, b: str) -> int:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--prompts-file", required=True, type=Path)
    p.add_argument("--mode", required=True, choices=("consecutive", "simultaneous"))
    p.add_argument("--max-tokens", type=int, default=8)
    p.add_argument("--seed", type=int, default=20260819)
    p.add_argument("--idle-s", type=float, default=1.0)
    p.add_argument("--tag", required=True)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()

    spec = json.loads(args.prompts_file.read_text())
    prompts = {f"bg{i}": s for i, s in enumerate(spec["trials"]["B8r0"]["background"][:8])}
    prompts["X"] = spec["trials"]["B8r0"]["target"]
    prompts["Y"] = spec["trials"]["B8r1"]["target"]
    worst = max(shared_prefix(a, b) for a, b in itertools.combinations(prompts.values(), 2))
    meta = {"tag": args.tag, "mode": args.mode, "max_tokens": args.max_tokens, "seed": args.seed,
            "idle_s": args.idle_s, "max_pairwise_shared_prefix_chars": worst,
            "prompts": {k: {"chars": len(v), "sha256": hashlib.sha256(v.encode()).hexdigest()}
                        for k, v in prompts.items()}}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"admission.{args.tag}.json"
    if worst >= MAX_SHARED_PREFIX_CHARS:
        out_path.write_text(json.dumps({**meta, "error": "prompt check failed"}, indent=2) + "\n")
        return 3

    base = args.base_url.rstrip("/")
    with urllib.request.urlopen(f"{base}/v1/models", timeout=30) as r:
        model = json.loads(r.read().decode())["data"][0]["id"]
    bodies = {k: payload(model, v, args.max_tokens, args.seed) for k, v in prompts.items()}

    records = []
    for i in range(8):
        records.append(one_sequential(base, f"bg{i}", bodies[f"bg{i}"]))
    saturation_ok = all(r["status"] == 200 for r in records)
    if saturation_ok:
        time.sleep(args.idle_s)
        treatment_start = time.time()
        records += treatment(base, args.mode, {"X": bodies["X"], "Y": bodies["Y"]})
    else:
        treatment_start = None

    out = {**meta, "served_model_id": model, "saturation_ok": saturation_ok,
           "treatment_start_s": treatment_start, "records": records}
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    tr = [r for r in records if r["label"] in ("X", "Y")]
    print(json.dumps({"tag": args.tag, "mode": args.mode, "saturation_ok": saturation_ok,
                      "statuses": [r.get("status") for r in records],
                      "treatment_send_gap_ms": (round((tr[1]["send_start_s"] - tr[0]["send_start_s"]) * 1e3, 3)
                                                if len(tr) == 2 else None)}))
    return 0 if saturation_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
