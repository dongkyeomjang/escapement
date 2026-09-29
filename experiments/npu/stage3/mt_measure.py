#!/usr/bin/env python3
"""Measured metrics of one multi-turn lifecycle (pilot and main experiment).

Channel A' per turn over the evaluation window, defined without any clock
alignment between client and server:

* the server window runs from the ``[PFX] [ALLOC]`` line of the first request
  *sent* in the evaluation window to that of the last one (client id is a
  strict prefix of the server id, TASK18);
* decode = every ``[BUCKET]`` step in the server window priced by the TASK13
  step-cost model (interpolated widths via ``config_search.descriptor_for``);
* prefill = for every evaluation request, ``prefill_s(prompt - cached)``.
  ``cached`` is the client's ``cached_tokens``; when that is ``null`` it comes
  from the server's own lookup line (``[CACHE-HIT]`` ``IB_COUNT x block``,
  ``[CACHE-PARTIAL]`` ``REUSED``, no lookup line -> 0). A request with no
  ``prompt_tokens`` makes the cell ``INVALID``.

Also: the runner checks registered for the pilot, reuse, the step-weighted
histogram and throughput.
"""

from __future__ import annotations

from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

from continuum.workload.multiturn import WindowRule  # noqa: E402
from config_search import descriptor_for  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

_ALLOC = re.compile(r"\[PFX\] \[ALLOC\] REQUEST=(\S+)")
_HIT = re.compile(r"\[PFX\] \[CACHE-HIT\] REQUEST=(\S+) .*IB_COUNT=(\d+)")
_PART = re.compile(r"\[PFX\] \[CACHE-PARTIAL\] REQUEST=(\S+) \| REUSED=(\d+)/")
_BUCKET = re.compile(r"\[BUCKET\] request_nums=(\d+) padded_batch_size=(\d+)")


def parse_server(path: Path) -> list[tuple]:
    ev = []
    with path.open(errors="replace") as fh:
        for line in fh:
            m = _ALLOC.search(line)
            if m:
                ev.append(("alloc", m.group(1)))
                continue
            m = _HIT.search(line)
            if m:
                ev.append(("hit", m.group(1), int(m.group(2)) * D.inner_block_tokens))
                continue
            m = _PART.search(line)
            if m:
                ev.append(("partial", m.group(1), int(m.group(2))))
                continue
            m = _BUCKET.search(line)
            if m:
                ev.append(("bucket", int(m.group(1)), int(m.group(2))))
    return ev


def lifecycle_metrics(run: Path, tag: str, grid: tuple[int, ...], batch: int) -> dict:
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines()
            if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    prov = json.loads((probe / "provenance.json").read_text())
    ev = parse_server(run / f"server-{tag}.log")
    desc = descriptor_for(D, tuple(grid), batch)
    sc, pm = desc.step_cost_model, desc.prefill_cost_model

    # runner checks
    rule = WindowRule(cycle_s=win["cycle_s"], eval_s=win["eval_s"])
    w0 = win["warmup_end_s"]
    w1 = win["eval_end_s"]
    off = rule.warmup_end([(r["slot"], r["done_s"]) for r in rows], max(r["slot"] for r in rows) + 1)
    delays = []
    by_slot: dict[int, list] = {}
    for r in rows:
        by_slot.setdefault(r["slot"], []).append(r)
    for rs in by_slot.values():
        rs.sort(key=lambda r: r["sent_s"])
        for a, b in zip(rs, rs[1:]):
            if b["generation"] == a["generation"] + 1 and b["turn"] == 0:
                delays.append(b["sent_s"] - a["done_s"])
    checks = {
        "stopped_by_window": win["stopped_by"] == "window",
        "exhausted_slots": win["exhausted_slots"],
        "window_online_eq_offline": off is not None and w0 is not None and abs(off - w0) < 1e-9,
        "sent_after_eval_end": sum(1 for r in rows if w1 is not None and r["sent_s"] >= w1 + 1e-6),
        "http_errors": sum(1 for r in rows if r["status"] != 200),
        "runner_commit": prov["runner_commit"],
        "plan_content_sha256": prov["plan_content_sha256"],
        "renewal_count": len(delays),
        "renewal_max_delay_s": max(delays) if delays else None,
        "details_present_share": sum(1 for r in rows if r["details_present"]) / len(rows),
    }

    # join client -> server ids
    alloc_pos: dict[str, int] = {}
    lookup: dict[str, int] = {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            alloc_pos.setdefault(e[1], i)
        elif e[0] == "hit":
            lookup[e[1]] = e[2]
        elif e[0] == "partial":
            lookup[e[1]] = e[2]
    sid_of = {}
    for sid in alloc_pos:
        sid_of.setdefault(sid.rsplit("-", 2)[0], sid)
    ev_rows = [r for r in rows if w0 is not None and w0 <= r["sent_s"] < w1]
    invalid = []
    cached_src = Counter()
    prefill = 0.0
    reuse_hits = reuse_n = 0
    pos = []
    for r in ev_rows:
        sid = sid_of.get(r["request_id"])
        if sid is None:
            invalid.append(f"no server id for {r['request_id']}")
            continue
        pos.append(alloc_pos[sid])
        if r["prompt_tokens"] is None:
            invalid.append(f"no prompt_tokens for {r['request_id']}")
            continue
        if r["cached_tokens"] is not None:
            cached = r["cached_tokens"]
            cached_src["client"] += 1
            if sid in lookup and lookup[sid] != cached:
                cached_src["client_server_disagree"] += 1
        else:
            cached = lookup.get(sid, 0)
            cached_src["server"] += 1
        prefill += pm.prefill_s(max(r["prompt_tokens"] - cached, 0))
        if r["turn"] > 0:
            reuse_n += 1
            reuse_hits += int(cached > 0)
    lo, hi = (min(pos), max(pos)) if pos else (0, -1)
    decode = 0.0
    h = Counter()
    pad_num = pad_den = 0
    for e in ev[lo:hi + 1]:
        if e[0] == "bucket":
            n, b = e[1], e[2]
            decode += sc.step_time_s(bucket=b, actual=n)
            h[n] += 1
            pad_num += b - n
            pad_den += b
    n_req = len(ev_rows)
    ttft = [r["first_token_s"] - r["sent_s"] for r in ev_rows
            if r["turn"] > 0 and r.get("first_token_s") is not None]
    return {
        "tag": tag, "valid": not invalid, "invalid_reasons": invalid[:10],
        "checks": checks, "eval_requests": n_req,
        "decode_s": decode, "prefill_s": prefill,
        "a_prime_per_turn_s": (decode + prefill) / n_req if n_req else None,
        "decode_per_turn_s": decode / n_req if n_req else None,
        "prefill_per_turn_s": prefill / n_req if n_req else None,
        "reuse": [reuse_hits, reuse_n], "cached_source": dict(cached_src),
        "h_counts": {str(k): v for k, v in sorted(h.items())},
        "padding": pad_num / pad_den if pad_den else None,
        "throughput_per_s": n_req / win["eval_s"],
        "ttft_turn_ge1_median_s": sorted(ttft)[len(ttft) // 2] if ttft else None,
        "warmup_end_s": w0, "wall_s": win["wall_s"],
    }


def tvd(a: dict, b: dict) -> float:
    ta, tb = sum(a.values()), sum(b.values())
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in keys)


def chunk_times(run: Path, tag: str) -> dict[str, list[float]]:
    p = run / "probe" / tag / f"tokens.{tag}.jsonl.gz"
    if not p.exists():
        return {}
    with gzip.open(p, "rt") as fh:
        return {json.loads(l)["request_id"]: json.loads(l)["t"] for l in fh}
