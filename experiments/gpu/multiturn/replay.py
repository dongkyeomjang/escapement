#!/usr/bin/env python3
"""GTASK12 (directive G-05 task A): event replay of the GPU multi-turn lifecycles.

Specification: docs/research/gpu/GPU_REPLAY_PREREG.md (commit 0973228, before
this file was written). The replay walks the server log in log order --
``[GPFX] LOOKUP``/``ALLOC`` lines and ``[GSTEP]`` lines -- and emulates the
vLLM 0.22.0 block pool and step progression on that observed admission
sequence. Inputs: log order, the client rows' (session, turn, prompt tokens,
generation length), the pool size. Everything else in the log (``free=``,
``hit=``, ``scheduled=``, ``computed=``, ``reqs``, ``toks``) and the KV events
are only compared against (section 6).

Rule switches (section 7 counterfactuals): ``lag`` (release before the
schedule of step e + 1 + lag), ``lookup_first``, ``eviction`` (lru/fifo),
``tail_first``, ``cache_gen``.

usage: replay.py --run-dir <abs> --out <abs json>
"""

from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import heapq
import json
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE.parent / "obs"))
from parse_obs import parse  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402

BLOCK = 16
BUDGET = 2048
MAIN = dict(lag=1, lookup_first=True, eviction="lru", tail_first=True, cache_gen=True,
            ambiguous_late=False)
VARIANTS = {
    "i_lag0": dict(MAIN, lag=0),
    "i_lag2": dict(MAIN, lag=2),
    "ii_alloc_first": dict(MAIN, lookup_first=False),
    "iii_fifo": dict(MAIN, eviction="fifo"),
    "iv_head_first": dict(MAIN, tail_first=False),
    "v_prompt_only": dict(MAIN, cache_gen=False),
}
ALT_AMBIGUOUS = dict(MAIN, ambiguous_late=True)


def segment_ids(seed: int, n: int) -> list[int]:   # gpu_mt_runner.segment_ids
    rng = random.Random(seed)
    return [rng.randrange(1000, 150000) for _ in range(n)]


class Pool:
    def __init__(self, n: int, eviction: str):
        self.eviction = eviction
        self.key: dict[int, tuple | None] = {b: None for b in range(1, n)}
        self.cache: dict[tuple, list[int]] = defaultdict(list)   # key -> blocks (registration order)
        self.ref = {b: 0 for b in range(1, n)}
        self.evicted: list[tuple] = []
        if eviction == "lru":
            self.free = OrderedDict((b, None) for b in range(1, n))
        else:
            self.order = {b: (-1, b) for b in range(1, n)}
            self.heap = [(self.order[b], b) for b in range(1, n)]
            heapq.heapify(self.heap)
            self.in_free = set(range(1, n))

    def nfree(self) -> int:
        return len(self.free) if self.eviction == "lru" else len(self.in_free)

    def pop(self, stamp: int, pos: int) -> int:
        if self.eviction == "lru":
            if not self.free:
                raise RuntimeError("no free block")
            b, _ = self.free.popitem(last=False)
        else:
            while True:
                if not self.heap:
                    raise RuntimeError("no free block")
                o, b = heapq.heappop(self.heap)
                if b in self.in_free and self.order[b] == o:
                    self.in_free.discard(b)
                    break
            self.order[b] = (stamp, -pos)
        k = self.key[b]
        if k is not None:
            lst = self.cache[k]
            lst.remove(b)
            if not lst:
                del self.cache[k]
            self.evicted.append(k)
            self.key[b] = None
        self.ref[b] = 1
        return b

    def push_front(self, b: int) -> None:
        """Give back a block popped by mistake (alloc-first counterfactual)."""
        self.ref[b] = 0
        if self.eviction == "lru":
            self.free[b] = None
            self.free.move_to_end(b, last=False)
        else:
            self.order[b] = (-2, b)
            self.in_free.add(b)
            heapq.heappush(self.heap, (self.order[b], b))

    def lookup(self, key: tuple) -> int | None:
        lst = self.cache.get(key)
        return lst[0] if lst else None

    def touch(self, b: int) -> None:
        if self.ref[b] == 0:
            if self.eviction == "lru":
                del self.free[b]
            else:
                self.in_free.discard(b)
        self.ref[b] += 1

    def release(self, blocks: list[int], tail_first: bool) -> None:
        for b in (reversed(blocks) if tail_first else blocks):
            self.ref[b] -= 1
            if self.ref[b] == 0:
                if self.eviction == "lru":
                    self.free[b] = None
                else:
                    self.in_free.add(b)
                    heapq.heappush(self.heap, (self.order[b], b))

    def register(self, b: int, key: tuple) -> None:
        if self.key[b] is None:
            self.key[b] = key
            self.cache[key].append(b)


@dataclass
class Req:
    sid: str
    session: str
    turn: int
    P: int
    G: int
    stamp: int
    hit: int = 0
    c: int = 0            # scheduled-computed tokens
    q: int = 0            # sampled tokens scheduled
    blocks: list = field(default_factory=list)
    nreg: int = 0
    release_at: int | None = None
    released: bool = False


def load(run: Path) -> dict:
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    prov = json.loads((run / "provenance.json").read_text())
    win = json.loads((run / "windows.json").read_text())
    log_text = (run / "server.log").read_text(errors="replace")
    details = ("enable_prompt_tokens_details=True" in log_text
               or "'enable_prompt_tokens_details': True" in log_text
               or "enable_prompt_tokens_details: True" in log_text)
    ev = parse(run / "server.log")
    return {"rows": rows, "prov": prov, "win": win, "ev": ev, "details": details}


def sid_map(ev, rows) -> dict:
    """server id -> client row (client id is a strict prefix of the server id)."""
    by_cid = {r["request_id"]: r for r in rows}
    out = {}
    for e in ev:
        if e["kind"] == "LOOKUP":
            parts = e["req"].split("-")
            for k in range(2, len(parts)):
                r = by_cid.get("-".join(parts[:k]))
                if r is not None:
                    out[e["req"]] = r
                    break
    return out


def replay(data: dict, rules: dict) -> dict:
    ev, rows = data["ev"], data["rows"]
    smap = sid_map(ev, rows)
    pool = Pool(data["prov"]["config"]["num_gpu_blocks"], rules["eviction"])
    running: list[Req] = []
    pending_release: list[Req] = []
    pred: dict[str, dict] = {}
    k = 0                 # index of the [GSTEP] the current schedule call will produce
    open_ = False
    sched: list[tuple[Req, int]] = []
    budget = 0
    stamp = 0
    integ = Counter()
    first_free_div = None
    ambiguous_steps = []
    error = None

    def register_full(r: Req) -> None:
        lim = r.P + r.G - 1 if rules["cache_gen"] else r.P
        n = min(r.c, lim) // BLOCK
        while r.nreg < n:
            pool.register(r.blocks[r.nreg], (r.session, r.nreg))
            r.nreg += 1

    def alloc_to(r: Req, tokens: int) -> None:
        need = -(-tokens // BLOCK)
        while len(r.blocks) < need:
            r.blocks.append(pool.pop(r.stamp, len(r.blocks)))

    def start_schedule() -> None:
        nonlocal budget, sched, open_
        live = [r for r in running if not r.released]
        # ambiguous release (prereg 3.5 exception): every running request is
        # skip-state at this schedule while releases are still pending
        due = [r for r in pending_release if r.release_at is not None and r.release_at <= k]
        later = [r for r in pending_release if r not in due]
        if later and rules["lag"] == 1:
            nonskip = [r for r in live if r.q < r.G]
            if not nonskip and all(r.release_at == k + 1 for r in later):
                ambiguous_steps.append(k)
                if not rules["ambiguous_late"]:
                    due = due + later
        for r in sorted(due, key=lambda r: r.stamp):
            pool.release(r.blocks, rules["tail_first"])
            r.released = True
            pending_release.remove(r)
        running[:] = [r for r in running if not r.released]
        budget = BUDGET
        sched = []
        for r in running:
            if budget <= 0:
                break
            if r.q >= r.G:          # async skip: last token scheduled, output not processed
                continue
            n = min(r.P - r.c, budget) if r.c < r.P else 1
            alloc_to(r, r.c + n)
            budget -= n
            sched.append((r, n))
        open_ = True

    try:
        for e in ev:
            if e["kind"] in ("LOOKUP", "ALLOC", "ALLOC_FAIL"):
                if not open_:
                    start_schedule()
                if e["kind"] == "LOOKUP":
                    row = smap.get(e["req"])
                    integ["lookup"] += 1
                    if pool.nfree() == e["free"]:
                        integ["lookup_free_eq"] += 1
                    elif first_free_div is None:
                        first_free_div = e["line"]
                    if row is None:
                        continue
                    r = Req(sid=e["req"], session=row["session"], turn=row["turn"],
                            P=row["prompt_tokens"], G=row["requested_generation_tokens"], stamp=stamp)
                    stamp += 1
                    limit = (r.P - 1) // BLOCK
                    pre = []
                    if not rules["lookup_first"]:
                        # NPU order: allocate as if nothing hit, then look up
                        m = -(-min(r.P, budget) // BLOCK)
                        pre = [pool.pop(r.stamp, i) for i in range(m)]
                    hits = []
                    for j in range(limit):
                        b = pool.lookup((r.session, j))
                        if b is None:
                            break
                        hits.append(b)
                    for b in hits:
                        pool.touch(b)
                    r.blocks = list(hits)
                    r.nreg = len(hits)
                    r.hit = len(hits) * BLOCK
                    r.c = r.hit
                    n = min(r.P - r.c, budget)
                    need = -(-(r.c + n) // BLOCK) - len(r.blocks)
                    use, back = pre[:need], pre[need:]
                    for b in reversed(back):
                        pool.push_front(b)
                    r.blocks += use
                    alloc_to(r, r.c + n)
                    budget -= n
                    running.append(r)
                    sched.append((r, n))
                    pred[r.sid] = {"hit": r.hit, "lookup_line": e["line"],
                                   "free_pred": None, "free_obs": e["free"]}
                    r._alloc_check = (n, r.hit)
                elif e["kind"] == "ALLOC":
                    integ["alloc"] += 1
                    r = next((x for x, _ in reversed(sched) if x.sid == e["req"]), None)
                    if r is not None:
                        n_pred, c_pred = r._alloc_check
                        if (pool.nfree(), n_pred, c_pred) == (e["free"], e["scheduled"], e["computed"]):
                            integ["alloc_eq"] += 1
            elif e["kind"] == "STEP":
                if not open_:
                    start_schedule()
                integ["step"] += 1
                if (len(sched), sum(n for _, n in sched)) == (e["reqs"], e["toks"]):
                    integ["step_eq"] += 1
                for r, n in sched:
                    was_prefill = r.c < r.P
                    r.c += n
                    if (not was_prefill) or r.c >= r.P:
                        r.q += 1
                    register_full(r)
                    if r.q >= r.G and r.release_at is None:
                        r.release_at = k + 1 + rules["lag"]
                        pending_release.append(r)
                k += 1
                open_ = False
    except RuntimeError as exc:
        error = f"{exc} at step {k}"
    return {"pred": pred, "integrity": dict(integ), "first_free_divergence_line": first_free_div,
            "ambiguous_steps": ambiguous_steps, "evicted": pool.evicted, "error": error,
            "error_line": None}


def observed(data: dict) -> dict:
    """server id -> (row, observed cached or None)."""
    out = {}
    for sid, r in sid_map(data["ev"], data["rows"]).items():
        if r["cached_tokens"] is not None:
            c = r["cached_tokens"]
        elif data["details"]:
            c = 0
        else:
            c = None
        out[sid] = (r, c)
    return out


def kv_removed(run: Path, data: dict) -> list[tuple] | None:
    """Observed eviction sequence as (session, block index), cached blocks only."""
    plan_path = Path(data["prov"]["argv"][data["prov"]["argv"].index("--plan") + 1])
    plan = MultiTurnPlan.from_json(json.loads(plan_path.read_text()))
    root = {}
    for sp in plan.slots:
        for s in sp.sessions:
            t0 = s.turns[0]
            root[tuple(segment_ids(t0.text_seed, t0.new_segment_tokens)[:BLOCK])] = s.session_id
    where: dict[int, tuple] = {}
    cached: set = set()
    out = []
    for line in (run / "kv_events.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        for e in json.loads(line)["events"]:
            if e["type"] == "BlockStored":
                p = e.get("parent_block_hash")
                toks = e.get("token_ids") or []
                for i, h in enumerate(e["block_hashes"]):
                    if p is None:
                        sess = root.get(tuple(toks[i * BLOCK:(i + 1) * BLOCK]))
                        where[h] = (sess, 0)
                    else:
                        ps = where.get(p)
                        where[h] = (ps[0], ps[1] + 1) if ps else (None, None)
                    cached.add(h)
                    p = h
            elif e["type"] == "BlockRemoved":
                for h in e["block_hashes"]:
                    if h in cached:
                        cached.discard(h)
                        out.append(where.get(h, (None, None)))
            elif e["type"] == "AllBlocksCleared":
                cached.clear()
    return out


def analyse(run: Path) -> dict:
    data = load(run)
    obs = observed(data)
    win = data["win"]
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    main = replay(data, MAIN)
    alt = replay(data, ALT_AMBIGUOUS)
    var = {name: replay(data, rules) for name, rules in VARIANTS.items()}
    # population: every LOOKUP'd turn >= 1 request; judged = sent inside the window
    by_sess_prev = {}
    for r in data["rows"]:
        by_sess_prev[(r["session"], r["turn"])] = r
    recs = []
    for sid, (row, cached) in obs.items():
        if row["turn"] < 1:
            continue
        rec = {"sid": sid, "session": row["session"], "turn": row["turn"],
               "in_window": w0 <= row["sent_s"] < w1, "obs": cached}
        p = main["pred"].get(sid)
        if cached is None:
            rec["status"] = "UNKNOWN"; rec["why"] = "cached unknown"
        elif (row["session"], row["turn"] - 1) not in by_sess_prev:
            rec["status"] = "UNKNOWN"; rec["why"] = "no previous turn"
        elif p is None:
            rec["status"] = "UNKNOWN"; rec["why"] = "replay stopped" if main["error"] else "not replayed"
        else:
            rec["pred"] = p["hit"]
            a = alt["pred"].get(sid)
            if a is None or a["hit"] != p["hit"]:
                rec["status"] = "UNDECIDABLE"
            else:
                rec["status"] = "MATCH" if p["hit"] == cached else "MISMATCH"
            if rec["status"] == "MISMATCH":
                cat = None
                for name in ("i_lag0", "i_lag2", "ii_alloc_first", "iii_fifo", "iv_head_first",
                             "v_prompt_only"):
                    vp = var[name]["pred"].get(sid)
                    if vp is not None and vp["hit"] == cached:
                        cat = name.split("_")[0]
                        break
                if cat is None:
                    cat = "vi" if p["free_obs"] is not None and main_free_pred(main, sid) else "vii"
                rec["category"] = cat
                rec["variant_preds"] = {n: (v["pred"].get(sid) or {}).get("hit") for n, v in var.items()}
            rec["lookup_free_obs"] = p["free_obs"]
        recs.append(rec)
    removed = kv_removed(run, data)
    ev_pred = main["evicted"]
    same_pos = sum(1 for a, b in zip(removed, ev_pred) if a == b)
    return {
        "run": run.name, "main_integrity": main["integrity"], "main_error": main["error"],
        "first_free_divergence_line": main["first_free_divergence_line"],
        "ambiguous_steps": len(main["ambiguous_steps"]),
        "variant_integrity": {n: v["integrity"] for n, v in var.items()},
        "variant_errors": {n: v["error"] for n, v in var.items() if v["error"]},
        "kv": {"observed_removed": len(removed), "replay_evicted": len(ev_pred),
               "same_position": same_pos,
               "unmapped_observed": sum(1 for x in removed if x[0] is None)},
        "requests": recs,
    }


def main_free_pred(main: dict, sid: str) -> bool:
    """True when the replay's free count differed from the observed one at or
    before this request's LOOKUP (state divergence, category vi)."""
    d = main["first_free_divergence_line"]
    p = main["pred"].get(sid)
    return d is not None and p is not None and d <= p["lookup_line"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only", default=None, help="comma-separated lifecycle names (debug)")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    runs = sorted(d for d in a.run_dir.iterdir()
                  if d.is_dir() and (d / "done").exists() and not d.name.endswith(".retry1"))
    if a.only:
        keep = set(a.only.split(","))
        runs = [d for d in runs if d.name in keep]
    t0 = time.time()
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(analyse, runs))
    a.out.write_text(json.dumps({"lifecycles": res, "elapsed_s": time.time() - t0}) + "\n")
    print("wrote", a.out, len(res), "lifecycles", round(time.time() - t0, 1), "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
