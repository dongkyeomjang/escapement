"""G-10: per-step execution timing (``[GEXEC]``) joined to the window steps.

``[GEXEC] seq t s prep run`` (exec-timing layer, GTASK23): three CUDA events
recorded on the issuing stream of one model step -- e0 at the ``[GSTEP]``
point (start of the step, before input preparation), e1 just before the
forward (graph replay or eager/piecewise call), e2 after sampling,
postprocess and the KV-connector hook (end of ``sample_tokens``).
``s`` = elapsed(ref, e0) ms on the device timeline (ref = first recorded
event of the process), ``prep`` = elapsed(e0, e1), ``run`` = elapsed(e1, e2).
``t`` repeats the ``[GSTEP]`` ``t`` field (same perf_counter value, same
``%.6f`` format), which is the join key.

DIRECT_EXEC of a step = prep + run: the device-stream interval from the
step's start marker to the completion of its sampling. It contains every
kernel of the step on that stream (CUDA-graph replay included) and the
stream's idle time *inside* the step while it waits for host launches; it
excludes the time between one step's end marker and the next step's start
marker. Consecutive steps are stream-ordered, so a step is counted once and
two steps never overlap (checked).

The window steps, their decode / prefill split and RECON (``gpu_cost`` price
at lo / hi) are ``gpu_mt_measure.lifecycle_metrics``'s, restated here so the
three channels use one step list; RECON is asserted equal to that function's
``device_per_turn_s``.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
MT = HERE.parent / "multiturn"
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(MT))

from parse_obs import parse  # noqa: E402
import gpu_cost as C  # noqa: E402
import gpu_mt_measure as M  # noqa: E402

_EX = re.compile(r"\[GEXEC\] seq=(\d+) t=(\S+) s=(\S+) prep=(\S+) run=(\S+)")


def gexec(log: Path) -> dict[str, dict]:
    out = {}
    for raw in Path(log).read_text(errors="replace").splitlines():
        m = _EX.search(raw)
        if m:
            seq, t, s, prep, run = m.groups()
            out[t] = {"seq": int(seq), "s": float(s), "prep": float(prep), "run": float(run)}
    return out


def _tkey(t) -> str:
    return f"{float(t):.6f}"


def window_steps(run: Path) -> tuple[list, int, tuple]:
    """(steps [(event, decoders, prefill tokens)], eval requests, grid) --
    the selection of ``gpu_mt_measure.lifecycle_metrics``."""
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    prov = json.loads((run / "provenance.json").read_text())
    grid = tuple(sorted(prov["config"]["capture_sizes"]))
    ev = parse(run / "server.log")
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    alloc_line: dict[str, int] = {}
    for e in ev:
        if e["kind"] == "ALLOC":
            alloc_line.setdefault(e["req"], e["line"])
    sid_of = {}
    for sid in alloc_line:
        parts = sid.split("-")
        for k in range(2, len(parts)):
            sid_of.setdefault("-".join(parts[:k]), sid)
    ev_rows = [r for r in rows if w0 is not None and w0 <= r["sent_s"] < w1]
    lines = [alloc_line[sid_of[r["request_id"]]] for r in ev_rows if r["request_id"] in sid_of]
    lo, hi = (min(lines), max(lines)) if lines else (0, -1)
    steps = []
    allocs_since = 0
    for e in ev:
        if e["kind"] == "ALLOC":
            allocs_since += 1
        elif e["kind"] == "STEP":
            if lo <= e["line"] <= hi:
                if e["maxq"] == 1:
                    d, p = e["reqs"], 0
                else:
                    k = max(1, allocs_since)
                    d = max(0, e["reqs"] - k)
                    p = e["toks"] - d
                steps.append((e, d, p))
            allocs_since = 0
    return steps, len(ev_rows), grid


def step_type(d: int, p: int) -> str:
    if p == 0:
        return "decode"
    return "prefill" if d == 0 else "mixed"


def exec_metrics(run: Path, base: dict | None = None) -> dict:
    """DIRECT_EXEC and RECON over the same window steps of one lifecycle."""
    base = base or M.lifecycle_metrics(run)
    steps, n, grid = window_steps(run)
    gx = gexec(run / "server.log")
    allsteps = [e for e in parse(run / "server.log") if e["kind"] == "STEP"]
    joined = sum(1 for e in allsteps if _tkey(e["t"]) in gx)
    recon = {"lo": 0.0, "hi": 0.0}
    direct = prep = runt = 0.0
    by_type: dict = {}
    missing = 0
    prev_end = None
    overlaps = 0
    nonpos = 0
    for e, d, p in steps:
        ty = step_type(d, p)
        bt = by_type.setdefault(ty, {"steps": 0, "direct_s": 0.0, "recon_lo_s": 0.0, "recon_hi_s": 0.0,
                                     "missing": 0})
        bt["steps"] += 1
        for b in ("lo", "hi"):
            v = C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound=b) / 1e3
            recon[b] += v
            bt[f"recon_{b}_s"] += v
        x = gx.get(_tkey(e["t"]))
        if x is None:
            missing += 1
            bt["missing"] += 1
            prev_end = None
            continue
        dur = (x["prep"] + x["run"]) / 1e3
        if x["prep"] < 0 or x["run"] <= 0:
            nonpos += 1
        if prev_end is not None and x["s"] < prev_end - 0.01:   # %.4f print + ~0.5 us timer
            overlaps += 1
        prev_end = x["s"] + x["prep"] + x["run"]
        direct += dur
        prep += x["prep"] / 1e3
        runt += x["run"] / 1e3
        bt["direct_s"] += dur
    for b in ("lo", "hi"):
        assert base["device_per_turn_s"] is None or abs(recon[b] / n - base["device_per_turn_s"][b]) < 1e-9, \
            "RECON restatement differs from gpu_mt_measure"
    complete = missing == 0 and len(steps) > 0
    return {
        "eval_requests": n, "window_steps": len(steps),
        "gexec_lines": len(gx), "gstep_lines": len(allsteps), "gexec_joined_all": joined,
        "missing_window": missing, "missing_rate_window": missing / len(steps) if steps else None,
        "direct_complete": complete, "overlaps": overlaps, "nonpositive": nonpos,
        "recon_per_turn_s": {b: recon[b] / n for b in recon} if n else None,
        "direct_per_turn_s": direct / n if (n and complete) else None,
        "direct_prep_per_turn_s": prep / n if (n and complete) else None,
        "direct_run_per_turn_s": runt / n if (n and complete) else None,
        "direct_sum_s": direct, "by_type": by_type,
        "hw_active": "NA (no device profiler signal in this stack run)",
    }
