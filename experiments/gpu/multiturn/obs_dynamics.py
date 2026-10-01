#!/usr/bin/env python3
"""G-05 tasks B-D: observed step and queue dynamics of the GTASK11 lifecycles.

Per lifecycle, over the server window of ``gpu_mt_measure`` (first to last
evaluation request's ALLOC line):

* steps: ``[GSTEP]`` mode, ``reqs``, decoders ``d`` / prefill tokens ``p``
  (the price-channel rule of ``gpu_mt_measure``), price at both bounds,
  dispatch gap ``dt`` to the next ``[GSTEP]`` and the direct-channel cap
  ``2 * price_hi + 5 ms``, admissions in the next schedule;
* requests (sent inside the evaluation window): queue wait = server LOOKUP
  wall - client send wall (``origin_wall + sent_s``; same host clock),
  TTFT, client overhead before the request (send - previous turn's done -
  plan gap), idle span (previous turn's done -> this LOOKUP), and the blocks
  other requests took from the free queue in that span (exact, from the
  GTASK12 replay's pool);
* waiting-queue length sampled at every window step's dispatch wall time.

usage: obs_dynamics.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
from bisect import bisect_right

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "obs"))
import gpu_cost as C  # noqa: E402
import replay as RP  # noqa: E402


class TracePool(RP.Pool):
    """Pool that counts pops and records, per session, the pop counter at each
    release of its blocks and at each admission lookup (key index 0)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.npop = 0
        self.rel = {}
        self.lk = {}

    def pop(self, stamp, pos):
        self.npop += 1
        return super().pop(stamp, pos)

    def release(self, blocks, tail_first):
        k = self.key.get(blocks[0])
        if k is not None:
            self.rel.setdefault(k[0], []).append(self.npop)
        return super().release(blocks, tail_first)

    def lookup(self, key):
        if key[1] == 0:
            self.lk.setdefault(key[0], []).append(self.npop)
        return super().lookup(key)


def others_alloc(data: dict) -> dict:
    """(session, turn) -> blocks others took from the free queue between the
    session's previous release and this turn's LOOKUP (main-rule replay)."""
    made = []
    orig = RP.Pool

    def factory(*a, **k):
        p = TracePool(*a, **k)
        made.append(p)
        return p

    RP.Pool = factory
    try:
        RP.replay(data, RP.MAIN)
    finally:
        RP.Pool = orig
    p = made[0]
    out = {}
    for sess, lks in p.lk.items():
        rels = p.rel.get(sess, [])
        for t in range(1, len(lks)):
            if t - 1 < len(rels):
                out[(sess, t)] = lks[t] - rels[t - 1]
    return out


def lifecycle(run: Path) -> dict:
    data = RP.load(run)
    ev, rows, win = data["ev"], data["rows"], data["win"]
    grid = tuple(sorted(data["prov"]["config"]["capture_sizes"]))
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    origin = win["origin_wall"]
    smap = RP.sid_map(ev, rows)
    cid2sid = {r["request_id"]: s for s, r in smap.items()}
    lookup_wall = {e["req"]: e["wall"] for e in ev if e["kind"] == "LOOKUP"}
    lookup_line = {e["req"]: e["line"] for e in ev if e["kind"] == "LOOKUP"}
    in_win = [r for r in rows if w0 <= r["sent_s"] < w1]
    lines = [lookup_line[cid2sid[r["request_id"]]] for r in in_win]
    lo, hi = min(lines), max(lines)
    # steps (price-channel rule)
    stepl = [e for e in ev if e["kind"] == "STEP"]
    allocs_since = 0
    rec = []
    per_step_d = {}
    for e in ev:
        if e["kind"] == "ALLOC":
            allocs_since += 1
        elif e["kind"] == "STEP":
            if e["maxq"] == 1:
                d, p = e["reqs"], 0
            else:
                k = max(1, allocs_since)
                d = max(0, e["reqs"] - k)
                p = e["toks"] - d
            per_step_d[e["line"]] = (d, p, allocs_since)
            allocs_since = 0
    for i, e in enumerate(stepl):
        if not (lo <= e["line"] <= hi):
            continue
        d, p, adm = per_step_d[e["line"]]
        plo = C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound="lo")
        phi = C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound="hi")
        nxt = stepl[i + 1] if i + 1 < len(stepl) else None
        dt = (nxt["t"] - e["t"]) * 1e3 if nxt else None
        nadm = per_step_d[nxt["line"]][2] if nxt else None
        rec.append({"mode": e["mode"], "reqs": e["reqs"], "d": d, "p": p, "toks": e["toks"],
                    "lo": plo, "hi": phi, "dt": dt, "cap": 2 * phi + 5.0,
                    "adm_next": nadm, "wall": e["wall"]})
    # requests
    oth = others_alloc(data)
    by_key = {(r["session"], r["turn"]): r for r in rows}
    reqs = []
    for r in in_win:
        sid = cid2sid[r["request_id"]]
        q = {"turn": r["turn"], "wait_s": lookup_wall[sid] - (origin + r["sent_s"]),
             "ttft_s": (r["first_token_s"] - r["sent_s"]) if r.get("first_token_s") else None,
             "cached": r["cached_tokens"] or 0, "prompt": r["prompt_tokens"]}
        prev = by_key.get((r["session"], r["turn"] - 1))
        if prev is not None:
            q["client_overhead_s"] = r["sent_s"] - prev["done_s"] - prev["gap_after_s"]
            q["idle_s"] = lookup_wall[sid] - (origin + prev["done_s"])
            q["others_alloc"] = oth.get((r["session"], r["turn"]))
        reqs.append(q)
    # waiting-queue length at each window step
    sends = sorted(origin + r["sent_s"] for r in rows)
    admits = sorted(lookup_wall[cid2sid[r["request_id"]]] for r in rows)
    qlen = [bisect_right(sends, s["wall"]) - bisect_right(admits, s["wall"]) for s in rec]
    return {"run": run.name, "steps": rec, "requests": reqs, "queue_len": qlen}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    runs = sorted(d for d in a.run_dir.iterdir() if d.is_dir() and (d / "done").exists())
    with ProcessPoolExecutor(16) as ex:
        res = list(ex.map(lifecycle, runs))
    a.out.write_text(json.dumps(res) + "\n")
    print("wrote", a.out, len(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
