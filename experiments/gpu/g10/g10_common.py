"""G-10 shared analysis helpers (statistics, boundary residuals, queue proxy).

Boundary residuals (Appendix G / GTASK22 rule, auxiliary only): a step's value
is split into a decode share ``decode_ms(d)`` (equally over the decoders) and
a prefill share ``value - decode share`` (over the prefill members by their
tokens; all of it when d = 0), scaled for a channel whose step value is not
the price by ``channel value / price`` of that step (same proportions). The
start residual S = shares, inside the aggregation step range, of members sent
before w0; the end residual E = shares, in steps after the range, of members
sent in [w0, w1). corrected = (total - S + E) / requests. The observed side
reuses ``boundary_sensitivity`` (membership, sid map, split rule) unchanged;
the simulated side records the scheduler's members per step through a
``gpu_mt_sim.Step`` factory that reads the scheduling list of the caller (the
simulation itself is unchanged; durations are asserted equal to a plain run).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
MT = HERE.parent / "multiturn"
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(MT))

import gpu_cost as C  # noqa: E402
from parse_obs import parse  # noqa: E402
from exec_measure import gexec, _tkey  # noqa: E402

BOOT = 10_000


def boot_ci(xs: list[float], seed: int) -> tuple[float, float]:
    """Percentile bootstrap of the median, resampling replicates."""
    rng = random.Random(seed)
    bs = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(BOOT))
    return bs[int(0.025 * BOOT)], bs[int(0.975 * BOOT) - 1]


def sign_test(xs: list[float]) -> dict:
    """Exact two-sided sign test of ratio < 1 against 1 (ties dropped)."""
    below = sum(1 for x in xs if x < 1)
    above = sum(1 for x in xs if x > 1)
    n = below + above
    k = min(below, above)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else None
    return {"below_1": below, "above_1": above, "n": n, "p_two_sided": p}


def _shares(price: float, d: int, members: list, grid) -> dict:
    """members: [(id, tokens, is_decode)] -> {id: share of price}."""
    decs = [m for m, _, dec in members if dec]
    pres = [(m, t) for m, t, dec in members if not dec]
    dshare = C.decode_ms(d, grid) / 1e3 if d >= 1 and decs else 0.0
    dshare = min(dshare, price)
    pshare = price - dshare
    ptok = sum(t for _, t in pres)
    out: dict = {}
    for m in decs:
        out[m] = out.get(m, 0.0) + dshare / len(decs)
    for m, t in pres:
        out[m] = out.get(m, 0.0) + (pshare * t / ptok if ptok else pshare / len(pres))
    if not pres and decs:
        for m in decs:
            out[m] += pshare / len(decs)
    return out


def boundary_observed(run: Path, with_direct: bool) -> dict:
    """S, E and corrected per-call value for RECON lo / hi (and DIRECT_EXEC)."""
    import boundary_sensitivity as BS
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    prov = json.loads((run / "provenance.json").read_text())
    grid = tuple(sorted(prov["config"]["capture_sizes"]))
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    ev = parse(run / "server.log")
    smap = BS.sid_map(ev, rows)
    sent_of = {sid: r["sent_s"] for sid, r in smap.items()}
    alloc_line, stepl, k = {}, [], 0
    for e in ev:
        if e["kind"] == "ALLOC":
            alloc_line.setdefault(e["req"], e["line"])
            k += 1
        elif e["kind"] == "STEP":
            e["_k"] = k
            k = 0
            stepl.append(e)
    sid_of = {}
    for sid in alloc_line:
        parts = sid.split("-")
        for j in range(2, len(parts)):
            sid_of.setdefault("-".join(parts[:j]), sid)
    mem = BS.membership(ev, smap)
    ev_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
    lines = [alloc_line[sid_of[r["request_id"]]] for r in ev_rows]
    lo, hi = min(lines), max(lines)
    gx = gexec(run / "server.log") if with_direct else {}
    chans = ("lo", "hi", "direct") if with_direct else ("lo", "hi")
    acc = {c: {"total": 0.0, "S": 0.0, "E": 0.0} for c in chans}
    missing_after = 0
    for e in stepl:
        if e["line"] < lo:
            continue
        inside = e["line"] <= hi
        d, p = BS.split_rule(e)
        m = mem.get(e["line"], [])
        prices = {b: C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound=b) / 1e3 for b in ("lo", "hi")}
        for c in chans:
            if c == "direct":
                x = gx.get(_tkey(e["t"]))
                if x is None:
                    if not inside:
                        missing_after += 1
                    continue
                val = (x["prep"] + x["run"]) / 1e3
                sh = {sid: v * val / prices["lo"] for sid, v in _shares(prices["lo"], d, m, grid).items()}
            else:
                val = prices[c]
                sh = _shares(val, d, m, grid)
            if inside:
                acc[c]["total"] += val
            for sid, v in sh.items():
                t0 = sent_of.get(sid)
                if t0 is None:
                    continue
                if inside and t0 < w0:
                    acc[c]["S"] += v
                elif not inside and w0 <= t0 < w1:
                    acc[c]["E"] += v
    n = len(ev_rows)
    out = {c: {"per_call_s": a["total"] / n, "S_s": a["S"], "E_s": a["E"],
               "corrected_per_call_s": (a["total"] - a["S"] + a["E"]) / n} for c, a in acc.items()}
    out["direct_missing_after_window"] = missing_after if with_direct else None
    return out


def sim_with_members(plan, cfg, *, bound: str, step_cost):
    """gpu_mt_sim.simulate with per-step members recorded (behaviour unchanged)."""
    import gpu_mt_sim as S
    orig = S.Step
    members: list = []

    def factory(**kw):
        f = sys._getframe(1).f_locals
        members.append([(r.idx, n, (r.computed - n) >= r.prompt) for r, n in f["sched"]])
        return orig(**kw)

    S.Step = factory
    try:
        res = S.simulate(plan, cfg, eviction="lru", bound=bound, step_cost=step_cost)
    finally:
        S.Step = orig
    return res, members


def boundary_sim(res, members, grid, bound: str) -> dict:
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    arr = {r.idx: r.arrival_s for r in res["requests"]}
    n = sum(1 for r in res["requests"] if w0 <= r.arrival_s < w1)
    total = st = en = 0.0
    for s, m in zip(res["steps"], members):
        if s.start_s < w0:
            continue
        inside = s.start_s < w1
        price = C.step_ms(decodes=s.decodes, prefill_tokens=s.prefill_tokens, grid=grid, bound=bound) / 1e3
        if inside:
            total += price
        for rid, v in _shares(price, s.decodes, m, grid).items():
            t0 = arr.get(rid)
            if t0 is None:
                continue
            if inside and t0 < w0:
                st += v
            elif not inside and w0 <= t0 < w1:
                en += v
    return {"per_call_s": total / n, "S_s": st, "E_s": en, "corrected_per_call_s": (total - st + en) / n}


def admission_delay(run: Path) -> dict:
    """Observed queue proxy: first [GPFX] ALLOC wall time - client send wall time
    (window requests; includes HTTP/tokeniser latency, report only)."""
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    w0, w1, o = win["warmup_end_s"], win["eval_end_s"], win["origin_wall"]
    first: dict = {}
    for e in parse(run / "server.log"):
        if e["kind"] == "ALLOC":
            first.setdefault(e["req"], e["wall"])
    sid_of = {}
    for sid in first:
        parts = sid.split("-")
        for j in range(2, len(parts)):
            sid_of.setdefault("-".join(parts[:j]), sid)
    ds = sorted(first[sid_of[r["request_id"]]] - (o + r["sent_s"]) for r in rows
                if w0 <= r["sent_s"] < w1 and r["request_id"] in sid_of)
    return {"mean_s": statistics.fmean(ds) if ds else None, "median_s": ds[len(ds) // 2] if ds else None,
            "n": len(ds)}
