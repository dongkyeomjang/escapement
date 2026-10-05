#!/usr/bin/env python3
"""Observed activity time per turn and its paired ratio, without a cost model
(directive 16 work B; post_hoc). Read-only over existing run logs.

Population = the A' population of each lifecycle (mt_measure.lifecycle_metrics):
the evaluation-window requests (``w0 <= sent_s < w1``) and the ``[BUCKET]``
lines between their first and last ALLOC lines. A' prices these with the
TASK13 decode / TASK22 prefill cost models; here they are replaced by observed
times:

* decode: each ``[BUCKET]`` line's step time from TASK91 attribution -- request
  R's ``[BUCKET]`` lines between its ALLOC and FREE are its decode steps; the
  step at R's k-th line lasts ``t[k+1] - t[k]`` of R's streaming chunks (client
  clock) and is *clean* when no ALLOC lies between R's (k-1)-th and k-th lines.
  Any running request may attribute a step (the first that does is used). A
  step without a clean interval (prefill inside it, or no attributable running
  request) is *unattributable*: its time is filled with the median clean
  interval at the same ``request_nums`` in the same lifecycle (fallback: the
  lifecycle's median clean interval).
* prefill: there is no per-request prefill elapsed time in the server log. The
  only server figure is the shutdown summary ``PREFILL METRICS`` (model
  forward latency, mean over every prefill call of the whole run, warm-up
  included; one call per ALLOC). Two proxies:
    - ``srv``: window requests x the run's mean prefill latency (primary);
    - ``exc``: for a request whose ALLOC is the only ALLOC inside an
      attributed interval, interval - filled decode time at that step
      (exclusive prefill on this substrate); other requests take ``srv``.

activity/turn = (decode sum + prefill sum) / window requests. Ratio =
config / BASE on the same replicate, the replicates the verdict used
(its ``selection``); median and min..max. Reported next to the verdict's
reconstructed A' ratio.

usage: activity_time_ratio.py --output <json>
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import re
import statistics

REPO = Path(__file__).resolve().parents[3]
S3 = REPO / "results/npu/stage3"
SETS = {
    "TASK82": (S3 / "20260930-main", "main_verdict.json", (6, 8, 10)),
    "TASK87": (S3 / "20261001-hiload", "hiload_verdict.json", (14, 16)),
    "TASK95": (S3 / "20261002-simblind", "simblind_verdict.json", (13, 17, 20)),
    "TASK102": (S3 / "20261002-ctxblind", "ctxblind_verdict.json", (15, 18)),
}
CFGS = ("BASE", "BATCHONLY", "TUNED")
_ALLOC = re.compile(r"\[PFX\] \[ALLOC\] REQUEST=(\S+)")
_FREE = re.compile(r"\[PFX\] \[FREE-REQUEST\] REQUEST=(\S+)")
_BUCKET = re.compile(r"\[BUCKET\] request_nums=(\d+)")
_LAT = re.compile(r"Latency \(ms\): mean ([0-9.]+)")
_CNT = re.compile(r"Total call counts: (\d+)")


def parse(path: Path):
    ev, pre = [], None
    state = 0
    with path.open(errors="replace") as fh:
        for line in fh:
            if pre is None:
                if state == 0 and "PREFILL METRICS:" in line:
                    state, cnt = 1, None
                    continue
                if state == 1:
                    m = _CNT.search(line)
                    if m:
                        cnt = int(m.group(1))
                    m = _LAT.search(line)
                    if m:
                        pre = (float(m.group(1)) / 1000.0, cnt)
                    continue
            m = _BUCKET.search(line)
            if m:
                ev.append(("bucket", int(m.group(1))))
                continue
            m = _ALLOC.search(line)
            if m:
                ev.append(("alloc", m.group(1)))
                continue
            m = _FREE.search(line)
            if m:
                ev.append(("free", m.group(1)))
    return ev, pre


def lifecycle(run: Path, tag: str) -> dict:
    probe = run / "probe" / tag
    rows = [json.loads(l) for l in (probe / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((probe / f"windows.{tag}.json").read_text())
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    ev, pre = parse(run / f"server-{tag}.log")
    with gzip.open(probe / f"tokens.{tag}.jsonl.gz", "rt") as fh:
        tok = {x["request_id"]: x["t"] for x in map(json.loads, fh)}
    pos_a, pos_f = {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            pos_a.setdefault(e[1], i)
        elif e[0] == "free":
            pos_f.setdefault(e[1], i)
    sid_of = {}
    for s in pos_a:
        sid_of.setdefault(s.rsplit("-", 2)[0], s)
    # attribution over every request (any sent time)
    iv: dict[int, tuple[float, list[str]]] = {}
    for r in rows:
        s = sid_of.get(r["request_id"])
        t = tok.get(r["request_id"], [])
        if s is None or s not in pos_f or r.get("completion_tokens") is None:
            continue
        bpos = [i for i in range(pos_a[s], pos_f[s]) if ev[i][0] == "bucket"]
        if len(bpos) != r["completion_tokens"] - 1 or len(t) != r["completion_tokens"]:
            continue
        for k in range(1, len(bpos)):
            i = bpos[k]
            allocs = [e[1] for e in ev[bpos[k - 1] + 1:i] if e[0] == "alloc"]
            prev = iv.get(i)
            if prev is None or (prev[1] and not allocs):
                iv[i] = (t[k + 1] - t[k], allocs)
    win_rows = [r for r in rows if w0 <= r["sent_s"] < w1]
    pos = [pos_a[sid_of[r["request_id"]]] for r in win_rows]
    lo, hi = min(pos), max(pos)
    steps = [i for i in range(lo, hi + 1) if ev[i][0] == "bucket"]
    clean_by_n = defaultdict(list)
    for i in steps:
        if i in iv and not iv[i][1]:
            clean_by_n[ev[i][1]].append(iv[i][0])
    all_clean = [x for v in clean_by_n.values() for x in v]
    med_all = statistics.median(all_clean)
    med_n = {n: statistics.median(v) for n, v in clean_by_n.items()}

    def fill(n):
        return med_n.get(n, med_all)

    decode = decode_clean = 0.0
    unattr = no_attr = fallback = 0
    exc: dict[str, float] = {}
    for i in steps:
        n = ev[i][1]
        if i in iv and not iv[i][1]:
            decode += iv[i][0]
            decode_clean += iv[i][0]
            continue
        unattr += 1
        if i not in iv:
            no_attr += 1
        if n not in med_n:
            fallback += 1
        decode += fill(n)
        if i in iv and len(iv[i][1]) == 1:
            exc[iv[i][1][0]] = iv[i][0] - fill(n)
    nreq = len(win_rows)
    p_srv = nreq * pre[0]
    win_sids = [sid_of[r["request_id"]] for r in win_rows]
    covered = [s for s in win_sids if s in exc]
    p_exc = sum(exc[s] for s in covered) + (nreq - len(covered)) * pre[0]
    return {"tag": tag, "window_requests": nreq, "steps": len(steps), "unattributable": unattr,
            "no_running_attribution": no_attr, "fill_fallback": fallback,
            "decode_s": decode, "decode_clean_s": decode_clean,
            "prefill_mean_s": pre[0], "prefill_calls_run": pre[1], "allocs_in_log": len(pos_a),
            "prefill_srv_s": p_srv, "prefill_exc_s": p_exc, "exc_covered": len(covered),
            "exc_mean_s": statistics.mean(exc[s] for s in covered) if covered else None,
            "act_srv_per_turn_s": (decode + p_srv) / nreq, "act_exc_per_turn_s": (decode + p_exc) / nreq,
            "decode_per_turn_s": decode / nreq}


def summ(xs):
    return {"per_rep": xs, "median": statistics.median(xs), "min": min(xs), "max": max(xs)} if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    jobs, verdicts = {}, {}
    for task, (run, vfile, ns) in SETS.items():
        v = json.loads((run / vfile).read_text())
        verdicts[task] = v
        for n in ns:
            for cfg in CFGS:
                for r in range(5):
                    used = v["selection"][f"{cfg}.n{n}.r{r}"]["used"]
                    if used:
                        jobs[(task, n, cfg, r)] = (run, used)
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {k: ex.submit(lifecycle, *j) for k, j in jobs.items()}
        lc = {k: f.result() for k, f in futs.items()}
    cells = []
    for task, (run, vfile, ns) in SETS.items():
        for n in ns:
            for cfg in CFGS:
                reps = [r for r in range(5) if (task, n, cfg, r) in lc]
                xs = [lc[(task, n, cfg, r)] for r in reps]
                st, ua = sum(x["steps"] for x in xs), sum(x["unattributable"] for x in xs)
                nreq = sum(x["window_requests"] for x in xs)
                row = {"set": task, "N": n, "config": cfg, "replicates": len(xs),
                       "unattributable_share": ua / st, "no_running_attribution_share":
                       sum(x["no_running_attribution"] for x in xs) / st,
                       "fill_fallback_steps": sum(x["fill_fallback"] for x in xs),
                       "exc_coverage": sum(x["exc_covered"] for x in xs) / nreq,
                       "prefill_mean_ms": statistics.mean(x["prefill_mean_s"] for x in xs) * 1e3,
                       "exc_mean_ms": statistics.mean(x["exc_mean_s"] for x in xs if x["exc_mean_s"] is not None) * 1e3
                       if any(x["exc_mean_s"] is not None for x in xs) else None,
                       "prefill_calls_eq_allocs": all(x["prefill_calls_run"] == x["allocs_in_log"] for x in xs),
                       "act_srv_per_turn_s": statistics.mean(x["act_srv_per_turn_s"] for x in xs),
                       "lifecycles": xs}
                if cfg != "BASE":
                    rr = [r for r in reps if (task, n, "BASE", r) in lc]
                    for key in ("act_srv_per_turn_s", "act_exc_per_turn_s", "decode_per_turn_s"):
                        row["ratio_" + key.replace("_per_turn_s", "")] = summ(
                            [lc[(task, n, cfg, r)][key] / lc[(task, n, "BASE", r)][key] for r in rr])
                    vr = verdicts[task]["cells"][f"{cfg}.n{n}"].get("ratio")
                    row["verdict_ratio"] = ({"m": vr["m"], "min": min(vr["per_rep"]), "max": max(vr["per_rep"]),
                                             "per_rep": vr["per_rep"]} if vr else None)
                cells.append(row)
                msg = f"{task} N{n} {cfg} unattr={row['unattributable_share']:.3f}"
                if cfg != "BASE":
                    msg += (f" obs={row['ratio_act_srv']['median']:.3f} exc={row['ratio_act_exc']['median']:.3f}"
                            f" A'={row['verdict_ratio']['m']:.3f}" if row["verdict_ratio"] else "")
                print(msg, flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"cells": cells}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
