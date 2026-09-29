"""Measured metrics of one GPU multi-turn lifecycle (pilot and main experiment).

Definitions follow ``docs/research/gpu/GPU_MULTITURN_DESIGN.md`` section 5 and
mirror the NPU ``mt_measure`` where the substrate allows:

* evaluation requests = rows sent inside the runner's evaluation window
  (``WindowRule``, recorded online and re-derived here);
* server window = from the ``[GPFX] ALLOC`` line of the first evaluation
  request to that of the last one (client id is a strict prefix of the server
  id), no client/server clock alignment;
* every ``[GSTEP]`` in the server window is priced with ``gpu_cost.step_ms``.
  Decoders in a step: ``reqs`` when ``maxq == 1``; otherwise
  ``reqs - k`` with ``k`` = number of ``[GPFX] ALLOC`` lines since the
  previous step (admissions scheduled in this step), at least 1 (a
  continuing chunk of a long prompt has no ALLOC line). Prefill tokens =
  ``toks - decoders``. Priced at both bounds (``lo``/``hi``);
* ``cached``: client ``cached_tokens``; absent -> 0 only when the server log
  shows ``enable_prompt_tokens_details`` on (TASK79). Server ``LOOKUP hit=``
  is joined for a cross-check;
* reusable tokens of a turn >= 1 request = ``min(floor((prev prompt + prev
  generated - 1)/16), floor((prompt - 1)/16)) * 16`` from the same session's
  previous row;
* direct channel (exploratory): sum over window steps of
  ``min(dt_k, 2 * price_hi(k) + 5 ms)``, ``dt_k`` the dispatch gap to the
  next step (an idle engine produces no step, so a long gap is idle time).
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE.parent / "obs"))
sys.path.insert(0, str(HERE))

from continuum.workload.multiturn import WindowRule  # noqa: E402
from parse_obs import parse  # noqa: E402
import gpu_cost as C  # noqa: E402

BLOCK = 16


def lifecycle_metrics(run: Path) -> dict:
    rows = [json.loads(l) for l in (run / "requests.jsonl").read_text().splitlines() if l.strip()]
    win = json.loads((run / "windows.json").read_text())
    prov = json.loads((run / "provenance.json").read_text())
    grid = tuple(sorted(prov["config"]["capture_sizes"]))
    log_text = (run / "server.log").read_text(errors="replace")
    details_flag = "enable_prompt_tokens_details=True" in log_text or \
        "'enable_prompt_tokens_details': True" in log_text or \
        "enable_prompt_tokens_details: True" in log_text
    ev = parse(run / "server.log")
    rule = WindowRule(cycle_s=win["cycle_s"], eval_s=win["eval_s"])
    n_slots = max(r["slot"] for r in rows) + 1
    w0, w1 = win["warmup_end_s"], win["eval_end_s"]
    off = rule.warmup_end([(r["slot"], r["done_s"]) for r in rows], n_slots)
    checks = {
        "valid_runner": win["valid"], "invalid_reasons_runner": win["invalid_reasons"],
        "window_online_eq_offline": off is not None and w0 is not None and abs(off - w0) < 1e-9,
        "sent_after_eval_end": sum(1 for r in rows if w1 is not None and r["sent_s"] >= w1 + 1e-6),
        "http_errors": sum(1 for r in rows if r["status"] != 200),
        "gen_len_mismatch": sum(1 for r in rows if r["generated_ids"] != r["requested_generation_tokens"]),
        "details_flag_in_log": details_flag,
        "runner_commit": prov["runner_commit"], "plan_content_sha256": prov["plan_content_sha256"],
    }
    # server join
    alloc_line: dict[str, int] = {}
    lookup_hit: dict[str, int] = {}
    for e in ev:
        if e["kind"] == "ALLOC":
            alloc_line.setdefault(e["req"], e["line"])
        elif e["kind"] == "LOOKUP":
            lookup_hit.setdefault(e["req"], e["hit"])
    # client id is a strict prefix of the server id followed by "-"
    # (non-streaming "cmpl-X-0" and streaming "cmpl-X" both map to "cmpl-X-0-Y")
    sid_of = {}
    for sid in alloc_line:
        parts = sid.split("-")
        for k in range(2, len(parts)):
            sid_of.setdefault("-".join(parts[:k]), sid)
    # reusable tokens from the session's previous row
    by_sess: dict[str, list] = {}
    for r in rows:
        by_sess.setdefault(r["session"], []).append(r)
    reusable = {}
    for rs in by_sess.values():
        rs.sort(key=lambda r: r["turn"])
        for p, q in zip(rs, rs[1:]):
            if q["turn"] == p["turn"] + 1 and p["prompt_tokens"] is not None:
                fed = p["prompt_tokens"] + p["requested_generation_tokens"] - 1
                reusable[(q["session"], q["turn"])] = min(fed // BLOCK, (q["prompt_tokens"] - 1) // BLOCK) * BLOCK
    ev_rows = [r for r in rows if w0 is not None and w0 <= r["sent_s"] < w1]
    invalid, lines = [], []
    src = Counter()
    hits = n_later = hit_tok = reuse_tok = 0
    shape = Counter()
    for r in ev_rows:
        sid = sid_of.get(r["request_id"])
        if sid is None:
            invalid.append(f"no server id for {r['request_id']}")
            continue
        lines.append(alloc_line[sid])
        if r["prompt_tokens"] is None:
            invalid.append(f"no prompt_tokens for {r['request_id']}")
            continue
        if r["cached_tokens"] is not None:
            cached = r["cached_tokens"]
            src["client"] += 1
        elif details_flag:
            cached = 0
            src["absent_as_0"] += 1
        else:
            invalid.append(f"cached unknown for {r['request_id']}")
            continue
        if lookup_hit.get(sid) is not None and lookup_hit[sid] != cached:
            src["client_server_disagree"] += 1
        if r["turn"] > 0:
            n_later += 1
            hits += int(cached > 0)
            ru = reusable.get((r["session"], r["turn"]))
            if ru is None:
                invalid.append(f"no previous row for {r['session']} t{r['turn']}")
                continue
            hit_tok += cached
            reuse_tok += ru
            shape["zero" if cached == 0 else ("full" if cached >= ru else "partial")] += 1
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
    price = {b: 0.0 for b in ("lo", "hi")}
    interf = {b: 0.0 for b in ("lo", "hi")}
    h = Counter()
    pad_num = pad_den = 0
    mode_mismatch = 0
    for e, d, p in steps:
        for b in ("lo", "hi"):
            s = C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound=b) / 1e3
            price[b] += s
            if p > 0:
                interf[b] += (s - C.decode_ms(max(d, 1), grid) / 1e3) * d
        h[e["reqs"]] += 1
        padded = e["padded"] if isinstance(e["padded"], int) else e["toks"]
        pad_num += padded - e["toks"]
        pad_den += padded
        mode_mismatch += int(C.mode(d, p, grid) != e["mode"])
    # direct channel
    direct = 0.0
    stepl = [s for s in ev if s["kind"] == "STEP"]
    idx = {id(s): i for i, s in enumerate(stepl)}
    for e, d, p in steps:
        i = idx[id(e)]
        if i + 1 < len(stepl):
            dt = stepl[i + 1]["t"] - e["t"]
            cap = 2 * C.step_ms(decodes=d, prefill_tokens=p, grid=grid, bound="hi") / 1e3 + 0.005
            direct += min(dt, cap)
    n = len(ev_rows)
    ttft = sorted(r["first_token_s"] - r["sent_s"] for r in ev_rows
                  if r["turn"] > 0 and r.get("first_token_s") is not None)
    return {
        "run": str(run), "valid": win["valid"] and not invalid and checks["window_online_eq_offline"]
        and checks["sent_after_eval_end"] == 0 and checks["http_errors"] == 0
        and checks["gen_len_mismatch"] == 0,
        "invalid_reasons": invalid[:10], "checks": checks, "eval_requests": n,
        "reuse": [hits, n_later], "reuse_rate": hits / n_later if n_later else None,
        "hit_tokens": hit_tok, "reusable_tokens": reuse_tok,
        "token_reuse_ratio": hit_tok / reuse_tok if reuse_tok else None,
        "hit_shape": dict(shape), "cached_source": dict(src),
        "h_counts": {str(k): v for k, v in sorted(h.items())},
        "padding": pad_num / pad_den if pad_den else None,
        "steps_in_window": len(steps), "mode_mismatch_steps": mode_mismatch,
        "device_per_turn_s": {b: price[b] / n for b in price} if n else None,
        "interference_per_turn_s": {b: interf[b] / n for b in interf} if n else None,
        "direct_per_turn_s": direct / n if n else None,
        "throughput_per_s": n / win["eval_s"],
        "ttft_turn_ge1_median_s": ttft[len(ttft) // 2] if ttft else None,
        "warmup_end_s": w0, "metric_delta": win["metric_delta"],
    }


def tvd(a: dict, b: dict) -> float:
    ta, tb = sum(a.values()), sum(b.values())
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in set(a) | set(b))
