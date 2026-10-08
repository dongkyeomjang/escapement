#!/usr/bin/env python3
"""Per-lifecycle channels of the 2026-10-08 directive (DX_PREREG.md §2).

RECON       = ``mt_measure.lifecycle_metrics`` A' (unchanged frozen cost model:
              TASK13 decode step model x every ``[BUCKET]`` step between the
              first and last ALLOC of the evaluation requests, TASK22 prefill
              model x computed tokens of every evaluation request).
DIRECT_EXEC = the same population with each step's own measured duration from
              the ``[STEPTIME]`` line (patches/vllm_rbln-0.11.1/STEPTIME.md):
              ``t_end - t_exec`` (execute_model entry -> sample_tokens return;
              model forward incl. input build and prefix-KV copy, logits,
              sampler, bookkeeping). Host perf_counter of the one EngineCore
              process; the runtime call is synchronous, so this is completion
              based. One instance over 4 devices -> one elapsed time per step,
              never summed per device. Scheduler work and IPC between steps
              (``t_exec[k+1] - t_end[k]``) are outside and reported separately.
              decode: the ``[STEPTIME]`` (prefill=0) line that follows each
              counted ``[BUCKET]`` line (the bucket is logged inside the same
              step's forward); prefill: every ``[STEPTIME]`` prefill=1 line whose
              single request id is an evaluation request.
Components: model = t_model1 - t_model0, sampler = t_samp1 - t_samp0,
pre = t_model0 - t_exec, post = remainder.

Boundary-corrected variants (auxiliary, identical for both channels): TASK111
membership (request R is a member of every ``[BUCKET]`` step between its ALLOC
and FREE); a step's cost is split equally over its ``request_nums`` members;
S = share of members sent before w0 inside the counted range, E = share of
window members after the last window ALLOC; corrected = (total - S + E) / n.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mt_measure as M  # noqa: E402

_FREE = re.compile(r"\[PFX\] \[FREE-REQUEST\] REQUEST=(\S+)")
_STEP = re.compile(
    r"\[STEPTIME\] prefill=(\d) t_exec=([\d.]+) t_model0=([\d.]+) t_model1=([\d.]+) "
    r"t_samp0=([\d.]+) t_samp1=([\d.]+) t_end=([\d.]+) n_reqs=(\d+) n_tokens=(\d+) "
    r"cached=(.*?) req_ids=(\S+)")

CONFIGS = {  # role -> (artifact dir, grid, batch)
    "BASE": ("Qwen3-4B-rbln-b8-s8192-d4-mb", (1, 2, 4, 8), 8),
    "BATCHONLY": ("Qwen3-4B-rbln-b16-s8192-d4-batchonly", (1, 2, 4, 8, 16), 16),
    "TUNED": ("Qwen3-4B-rbln-b16-s8192-d4-mb16", (1, 4, 6, 8, 10, 16), 16),
    "DP_N8": ("Qwen3-4B-rbln-b16-s8192-d4-dp8", (1, 2, 3, 4, 6, 16), 16),
}


def parse(path: Path) -> list[tuple]:
    ev = []
    prev_ids: tuple = ()
    with path.open(errors="replace") as fh:
        for line in fh:
            if "[STEPTIME2]" in line:   # v2: one line holds many step records
                body = line.split("[STEPTIME2] ", 1)[1].strip()
                for rec in body.split(";"):
                    f = rec.split(",", 9)
                    try:
                        t = [float(x) for x in f[1:7]]
                        ext = f[9]
                        ids, cached = (), ""
                        if ext:
                            a, cached = ext.rsplit("|", 1)
                            ids = tuple(a.split(","))
                        ev.append(("step2", {"prefill": f[0] == "1", "t_exec": t[0], "t_model0": t[1],
                                             "t_model1": t[2], "t_samp0": t[3], "t_samp1": t[4], "t_end": t[5],
                                             "n_reqs": int(f[7]), "n_tokens": int(f[8]), "cached": cached,
                                             "ids": ids}))
                    except (IndexError, ValueError):
                        ev.append(("badstep",))
                continue
            if "[STEPTIME]" in line:
                m = _STEP.search(line)
                if not m:
                    ev.append(("badstep",))
                    continue
                g = m.groups()
                ids = prev_ids if g[10] == "=" else tuple(g[10].split(","))
                prev_ids = ids
                t = [float(x) for x in g[1:7]]
                ev.append(("step", {"prefill": g[0] == "1", "t_exec": t[0], "t_model0": t[1],
                                    "t_model1": t[2], "t_samp0": t[3], "t_samp1": t[4], "t_end": t[5],
                                    "n_reqs": int(g[7]), "n_tokens": int(g[8]), "cached": g[9],
                                    "ids": ids}))
                continue
            m = M._ALLOC.search(line)
            if m:
                ev.append(("alloc", m.group(1)))
                continue
            m = M._HIT.search(line)
            if m:
                ev.append(("hit", m.group(1), int(m.group(2)) * M.D.inner_block_tokens))
                continue
            m = M._PART.search(line)
            if m:
                ev.append(("partial", m.group(1), int(m.group(2))))
                continue
            m = M._BUCKET.search(line)
            if m:
                ev.append(("bucket", int(m.group(1)), int(m.group(2))))
                continue
            m = _FREE.search(line)
            if m:
                ev.append(("free", m.group(1)))
    return ev


def _dur(s: dict) -> dict:
    tot = s["t_end"] - s["t_exec"]
    model = s["t_model1"] - s["t_model0"]
    samp = s["t_samp1"] - s["t_samp0"]
    pre = s["t_model0"] - s["t_exec"]
    return {"total": tot, "model": model, "sampler": samp, "pre": pre, "post": tot - model - samp - pre}


def lifecycle(run: Path, tag: str, cfg: str, obs: bool = True) -> dict:
    _, grid, batch = CONFIGS[cfg]
    recon = M.lifecycle_metrics(run, tag, grid, batch)
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    ev = parse(run / f"server-{tag}.log")
    desc = M.descriptor_for(M.D, tuple(grid), batch)
    sc, pm = desc.step_cost_model, desc.prefill_cost_model

    pos_a, pos_f, lookup = {}, {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            pos_a.setdefault(e[1], i)
        elif e[0] == "free":
            pos_f.setdefault(e[1], i)
        elif e[0] in ("hit", "partial"):
            lookup[e[1]] = e[2]
    sid_of = {}
    for s in pos_a:
        sid_of.setdefault(s.rsplit("-", 2)[0], s)
    ev_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
    eval_sids = {sid_of[r["request_id"]] for r in ev_rows if r["request_id"] in sid_of}
    pos = [pos_a[s] for s in eval_sids]
    lo, hi = min(pos), max(pos)

    # pair bucket -> following decode step line
    pair: dict[int, int] = {}
    pending = None
    n_steps = n_bad = unpaired_dec = orphan_bucket = 0
    for i, e in enumerate(ev):
        if e[0] == "bucket":
            if pending is not None:
                orphan_bucket += 1
            pending = i
        elif e[0] == "badstep":
            n_bad += 1
        elif e[0] == "step":
            n_steps += 1
            if not e[1]["prefill"]:
                if pending is None:
                    unpaired_dec += 1
                else:
                    pair[pending] = i
                    pending = None
            elif pending is not None:   # a bucket line belongs to a decode step only
                orphan_bucket += 1
                pending = None

    # v2 records are buffered: the k-th decode record is the k-th [BUCKET] step
    v2 = any(e[0] == "step2" for e in ev)
    count_mismatch = 0
    if v2:
        pair, unpaired_dec, orphan_bucket = {}, 0, 0
        all_b = [i for i, e in enumerate(ev) if e[0] == "bucket"]
        dec2 = [i for i, e in enumerate(ev) if e[0] == "step2" and not e[1]["prefill"]]
        n_steps = sum(1 for e in ev if e[0] == "step2")
        count_mismatch = len(dec2) - len(all_b)
        for b, j in zip(all_b, dec2):
            pair[b] = j
        ev = [("step", e[1]) if e[0] == "step2" else e for e in ev]

    buckets = [i for i in range(lo, hi + 1) if ev[i][0] == "bucket"]
    out = {"tag": tag, "config": cfg, "recon": recon, "w0": w0, "w1": w1,
           "eval_requests": len(ev_rows), "decode_steps_counted": len(buckets),
           "recon_per_turn_s": recon["a_prime_per_turn_s"]}
    if not obs:
        return out

    missing_dec = [i for i in buckets if i not in pair]
    pre_by_sid: dict[str, list[dict]] = defaultdict(list)
    for e in ev:
        if e[0] == "step" and e[1]["prefill"] and len(e[1]["ids"]) == 1:
            pre_by_sid[e[1]["ids"][0]].append(e[1])
    missing_pre = sorted(s for s in eval_sids if s not in pre_by_sid)
    multi_pre = sum(1 for s in eval_sids if len(pre_by_sid.get(s, [])) > 1)
    size_mismatch = sum(1 for i in buckets if i in pair and ev[pair[i]][1]["n_reqs"] != ev[i][1])

    comp = {k: 0.0 for k in ("total", "model", "sampler", "pre", "post")}
    dec_by_bucket = defaultdict(lambda: [0, 0.0])
    step_cost_direct = {}
    for i in buckets:
        if i not in pair:
            continue
        d = _dur(ev[pair[i]][1])
        step_cost_direct[i] = d["total"]
        for k in comp:
            comp[k] += d[k]
        dec_by_bucket[(ev[i][2], ev[i][1])][0] += 1
        dec_by_bucket[(ev[i][2], ev[i][1])][1] += d["total"]
    pcomp = {k: 0.0 for k in comp}
    pre_recon_by_tokens = []
    for r in ev_rows:
        sid = sid_of.get(r["request_id"])
        for s in pre_by_sid.get(sid, []):
            d = _dur(s)
            for k in pcomp:
                pcomp[k] += d[k]
        cached = r["cached_tokens"] if r["cached_tokens"] is not None else lookup.get(sid, 0)
        comp_tok = max(r["prompt_tokens"] - cached, 0)
        pre_recon_by_tokens.append((comp_tok, pm.prefill_s(comp_tok),
                                    sum(_dur(s)["total"] for s in pre_by_sid.get(sid, []))))
    n = len(ev_rows)

    # inter-step host time inside the counted range (diagnostic)
    # (by time, so it holds for v1 interleaved and v2 buffered records alike)
    cnt = [ev[pair[i]][1] for i in buckets if i in pair]
    gaps = []
    if cnt:
        t_lo, t_hi = min(s["t_exec"] for s in cnt), max(s["t_exec"] for s in cnt)
        steps_t = sorted((e[1] for e in ev if e[0] == "step" and t_lo <= e[1]["t_exec"] <= t_hi),
                         key=lambda s: s["t_exec"])
        gaps = [b["t_exec"] - a["t_end"] for a, b in zip(steps_t, steps_t[1:])]

    # boundary correction, same rule for both channels
    members = defaultdict(list)
    for r in rows:
        s = sid_of.get(r["request_id"])
        if s is None or s not in pos_f:
            continue
        for i in range(pos_a[s], pos_f[s]):
            if ev[i][0] == "bucket":
                members[i].append(r["sent_s"])

    def boundary(cost_of) -> dict:
        st = en = 0.0
        mism = 0
        for i in buckets:
            ms = members.get(i, [])
            if len(ms) != ev[i][1]:
                mism += 1
            st += cost_of(i) * sum(1 for t in ms if t < w0) / ev[i][1]
        for i in range(hi + 1, len(ev)):
            if ev[i][0] == "bucket":
                ms = members.get(i, [])
                c = cost_of(i)
                if c is None:
                    continue
                en += c * sum(1 for t in ms if w0 <= t < w1) / ev[i][1]
        return {"S_s": st, "E_s": en, "membership_mismatch_steps": mism}

    recon_cost = lambda i: sc.step_time_s(bucket=ev[i][2], actual=ev[i][1])  # noqa: E731

    def direct_cost(i):
        j = pair.get(i)
        return None if j is None else _dur(ev[j][1])["total"]

    br = boundary(recon_cost)
    bd = boundary(lambda i: direct_cost(i) or 0.0)
    rt = recon["decode_s"] + recon["prefill_s"]
    dt = comp["total"] + pcomp["total"]
    out.update({
        "attribution": {"steptime_lines": n_steps, "bad_lines": n_bad,
                        "decode_steps_missing": len(missing_dec),
                        "eval_requests_without_prefill_step": len(missing_pre),
                        "eval_requests_with_multiple_prefill_steps": multi_pre,
                        "decode_size_mismatch": size_mismatch,
                        "unpaired_decode_steptime_total": unpaired_dec,
                        "orphan_bucket_total": orphan_bucket,
                        "format": "v2" if v2 else "v1",
                        "v2_decode_record_minus_bucket_count": count_mismatch,
                        "missing_share": (len(missing_dec) + len(missing_pre)) / (len(buckets) + n)},
        "complete": (not missing_dec and not missing_pre and n_bad == 0 and size_mismatch == 0
                     and count_mismatch <= 0),
        "direct": {"decode_s": comp["total"], "prefill_s": pcomp["total"],
                   "per_turn_s": dt / n, "decode_components_s": comp, "prefill_components_s": pcomp,
                   "model_plus_sampler_per_turn_s": (comp["model"] + comp["sampler"] + pcomp["model"]
                                                    + pcomp["sampler"]) / n},
        "recon_per_turn_s": rt / n,
        "boundary": {"recon": br | {"corrected_per_turn_s": (rt - br["S_s"] + br["E_s"]) / n},
                     "direct": bd | {"corrected_per_turn_s": (dt - bd["S_s"] + bd["E_s"]) / n}},
        "inter_step_s": {"sum": sum(gaps), "count": len(gaps),
                         "median": sorted(gaps)[len(gaps) // 2] if gaps else None},
        "decode_by_bucket_actual": {f"{b}:{a}": v for (b, a), v in sorted(dec_by_bucket.items())},
        "prefill_tokens_recon_direct": pre_recon_by_tokens,
    })
    return out
