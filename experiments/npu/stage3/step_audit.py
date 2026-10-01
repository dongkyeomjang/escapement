#!/usr/bin/env python3
"""NPU operational step-time audit (directive 08 work A, TASK91). Development
set: TASK82 (75 lifecycles) and TASK87 (30). No verdict.

Attribution (decided before computing)
--------------------------------------
For a request R (client id joined to its server id by prefix, TASK18), the
``[BUCKET]`` lines between R's ``[PFX] [ALLOC]`` and ``[FREE-REQUEST]`` are R's
decode steps, in order; their count equals ``completion_tokens - 1`` (checked
per request; a request where it does not is skipped and counted). R's streamed
chunk ``k`` (0-based) arrives after decode step ``k - 1`` (chunk 0 after R's own
prefill). The interval chunk ``k`` -> ``k + 1`` (``k >= 1``) therefore spans
decode step ``k`` plus anything the engine ran between steps ``k - 1`` and
``k``:

* **clean decode step**: no ``[ALLOC]`` between the two ``[BUCKET]`` lines --
  the interval is one decode step at that line's ``(n, b)``;
* **one prefill**: exactly one other request's ``[ALLOC]`` between them (the
  exclusive prefill runs there) -- interval minus the configuration's median
  clean step at that ``(n, b)`` is that prefill's observed duration, priced
  against ``prefill_s(prompt - cached)`` of the admitted request;
* anything else is not used.

Every running request sees the same step, so a step contributes one sample per
running request; per ``(configuration, b, n)`` the median is reported. The
client channel is the same one TASK13's step-cost fit used (end-to-end ITL).
Only evaluation-window requests are used.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

import model_v0_retro as R  # noqa: E402
import mt_predict as P  # noqa: E402
from mt_check import CONFIGS  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

RUNS = [REPO / "results/npu/stage3/20260930-main", REPO / "results/npu/stage3/20261001-hiload"]


def lifecycle(run: Path, tag: str, cfg: str, acc: dict, pre: list, stats: dict,
              eval_s: float = 120.0) -> None:
    grid, batch = CONFIGS[cfg][1], CONFIGS[cfg][2]
    desc = P.descriptor(grid, batch)
    ev = R.parse_log(run / f"server-{tag}.log")
    rows = [json.loads(l) for l in (run / "probe" / tag / f"requests.{tag}.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "probe" / tag / f"windows.{tag}.json").read_text())
    w0, w1 = win["warmup_end_s"], win["warmup_end_s"] + eval_s
    tok = {}
    with gzip.open(run / "probe" / tag / f"tokens.{tag}.jsonl.gz", "rt") as fh:
        for l in fh:
            x = json.loads(l)
            tok[x["request_id"]] = x["t"]
    pos_a, pos_f = {}, {}
    for i, e in enumerate(ev):
        if e[0] == "alloc":
            pos_a.setdefault(e[1], i)
        elif e[0] == "free":
            pos_f.setdefault(e[1], i)
    sid = {}
    for s in pos_a:
        sid.setdefault(s.rsplit("-", 2)[0], s)
    row_of_sid = {sid[r["request_id"]]: r for r in rows if r["request_id"] in sid}
    lookup = {e[1]: e[2] for e in ev if e[0] == "partial"}
    hits = {e[1] for e in ev if e[0] == "hit"}

    def computed(s: str) -> int | None:
        r = row_of_sid.get(s)
        if r is None:
            return None
        c = r["cached_tokens"]
        if c is None:
            c = lookup.get(s, 0) if s not in hits else None
            if c is None:
                return None
        return max(r["prompt_tokens"] - c, 0)

    clean_local = defaultdict(list)
    one_prefill = []
    for r in rows:
        if not (w0 <= r["sent_s"] < w1):
            continue
        s = sid.get(r["request_id"])
        if s is None or s not in pos_f:
            continue
        t = tok.get(r["request_id"], [])
        bpos = [i for i in range(pos_a[s], pos_f[s]) if ev[i][0] == "bucket"]
        if len(bpos) != r["completion_tokens"] - 1 or len(t) != r["completion_tokens"]:
            stats["skipped"] += 1
            continue
        stats["requests"] += 1
        for k in range(1, len(bpos)):
            between = [e for e in ev[bpos[k - 1] + 1:bpos[k]] if e[0] == "alloc"]
            n = ev[bpos[k]][1]
            b = desc.bucket_for(n)
            iv = t[k + 1] - t[k]
            if not between:
                clean_local[(b, n)].append(iv)
            elif len(between) == 1:
                one_prefill.append((b, n, iv, between[0][1]))
    for key, xs in clean_local.items():
        acc[(cfg,) + key].extend(xs)
    for b, n, iv, other in one_prefill:
        c = computed(other)
        if c is None:
            continue
        pre.append({"cfg": cfg, "b": b, "n": n, "interval": iv, "computed": c,
                    "pred_prefill": D.prefill_cost_model.prefill_s(c)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    acc = defaultdict(list)
    pre: list = []
    stats = {"requests": 0, "skipped": 0, "lifecycles": 0}
    for run in RUNS:
        for d in sorted((run / "probe").iterdir()):
            tag = d.name
            if ".retry1" in tag:
                continue
            cfg = tag.split(".")[0]
            lifecycle(run, tag, cfg, acc, pre, stats)
            stats["lifecycles"] += 1
    steps = []
    for (cfg, b, n), xs in sorted(acc.items()):
        grid, batch = CONFIGS[cfg][1], CONFIGS[cfg][2]
        desc = P.descriptor(grid, batch)
        pred = desc.step_time_s(n)
        med = statistics.median(xs)
        steps.append({"cfg": cfg, "b": b, "n": n, "samples": len(xs), "obs_median_ms": med * 1e3,
                      "pred_ms": pred * 1e3, "ratio": med / pred,
                      "measured_bucket": b in D.step_cost_model.fixed_s_by_bucket})
    # prefill: subtract the configuration's median clean step at (b, n)
    clean_med = {(s["cfg"], s["b"], s["n"]): s["obs_median_ms"] / 1e3 for s in steps}
    pre_rows = []
    for p in pre:
        base = clean_med.get((p["cfg"], p["b"], p["n"]))
        if base is None or p["pred_prefill"] <= 0:
            continue
        pre_rows.append({**p, "obs_prefill": p["interval"] - base})
    bins = [(0, 128), (129, 512), (513, 1024), (1025, 2048), (2049, 10**6)]
    pre_tab = []
    for cfg in sorted({p["cfg"] for p in pre_rows}):
        for lo, hi in bins:
            sel = [p for p in pre_rows if p["cfg"] == cfg and lo <= p["computed"] <= hi]
            if len(sel) < 10:
                continue
            pre_tab.append({"cfg": cfg, "computed_bin": [lo, hi], "samples": len(sel),
                            "obs_median_ms": statistics.median(p["obs_prefill"] for p in sel) * 1e3,
                            "pred_median_ms": statistics.median(p["pred_prefill"] for p in sel) * 1e3,
                            "ratio_of_medians": statistics.median(p["obs_prefill"] for p in sel)
                            / statistics.median(p["pred_prefill"] for p in sel),
                            "median_ratio": statistics.median(p["obs_prefill"] / p["pred_prefill"] for p in sel)})
    # per-configuration time scale: decode-step-weighted mean of obs/pred
    scale = {}
    for cfg in sorted({s["cfg"] for s in steps}):
        sel = [s for s in steps if s["cfg"] == cfg]
        w = sum(s["samples"] for s in sel)
        scale[cfg] = {"step_weighted_ratio": sum(s["ratio"] * s["samples"] for s in sel) / w,
                      "samples": w}
    out = {"stats": stats, "steps": steps, "prefill": pre_tab, "decode_time_scale": scale}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(stats))
    for s in steps:
        if s["samples"] >= 200:
            print(f"{s['cfg']:9s} b={s['b']:2d} n={s['n']:2d} {s['samples']:6d} obs {s['obs_median_ms']:7.3f} "
                  f"pred {s['pred_ms']:7.3f} ratio {s['ratio']:.3f}{'' if s['measured_bucket'] else '  (interp/extrap)'}")
    for p in pre_tab:
        print(p["cfg"], p["computed_bin"], p["samples"], round(p["obs_median_ms"], 1), round(p["pred_median_ms"], 1),
              round(p["ratio_of_medians"], 3), round(p["median_ratio"], 3))
    print(json.dumps(scale, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
