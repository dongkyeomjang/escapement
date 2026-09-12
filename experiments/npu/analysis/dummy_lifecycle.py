#!/usr/bin/env python3
"""Reconstruct the dummy block's lifecycle from server logs (exploratory).

TASK58 established the dummy block's *effect* -- one extra slot of pool demand,
evictions = max(0, ALLOC + 1 - 8), one never-reassigned eviction per run -- by
elimination, because no log line said which caller triggered an eviction. The
[OBS] observation patch brackets the dummy path (DUMMY-BEGIN ... DUMMY-END) and
marks every can_allocate entry, so each eviction can now be labelled directly.

Per trial this script builds the ordered event list (file order is execution
order: one EngineCore process, async scheduling off), gives every outer block
an allocation generation, splits events into decode steps at each [BUCKET]
line, and counts the log patterns that the interpretation rules in
docs/research/DUMMY_LIFECYCLE_PLAN.md map to answers for Q1-Q5.

Subcommands:
  pilot    log volume per decode step (the flood check)
  analyze  Q1-Q5 pattern counts, eviction labels, arithmetic consistency
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_step_cost import metrics_p50  # noqa: E402

BUCKET_RE = re.compile(r"\[BUCKET\] request_nums=(\d+) padded_batch_size=(\d+)")
OBS_RE = re.compile(r"\[OBS\] \[([A-Z-]+)\] t=([0-9.]+)\s*(.*)$")
KV_RE = re.compile(r"(\w+)=(\[[^\]]*\]|\S+)")
PFX_ALLOC_RE = re.compile(r"\[PFX\] \[ALLOC\] REQUEST=(\S+) \| OB_COUNT=(\d+) OB=(\[[^\]]*\])")
PFX_EVICT_RE = re.compile(r"\[PFX\] \[EVICTION\] OB=(\d+)")
PFX_HIT_RE = re.compile(r"\[PFX\] \[(CACHE-HIT|CACHE-PARTIAL)\] REQUEST=(\S+)")
PREFIX_RE = re.compile(r"^.*?\[(?:vllm_rbln|v1|vllm)[^\]]*\]\s*")
MAX_RUNNING = 8
TASK15_RUN = Path("results/npu/stage2/20260819-204900-cliff-repro")


def _ints(v: str) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", v)]


def parse(log_path: Path) -> list[dict]:
    events = []
    for lineno, line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
        short = PREFIX_RE.sub("", line).strip()
        if m := BUCKET_RE.search(line):
            events.append({"kind": "BUCKET", "n": int(m.group(1)), "bucket": int(m.group(2)),
                           "line": lineno, "text": short})
        elif m := OBS_RE.search(line):
            kv = dict(KV_RE.findall(m.group(3)))
            events.append({"kind": m.group(1), "t": float(m.group(2)), "kv": kv,
                           "line": lineno, "text": short})
        elif m := PFX_ALLOC_RE.search(line):
            events.append({"kind": "PFX-ALLOC", "request": m.group(1), "ob": _ints(m.group(3)),
                           "line": lineno, "text": short})
        elif m := PFX_EVICT_RE.search(line):
            events.append({"kind": "PFX-EVICTION", "ob": int(m.group(1)), "line": lineno, "text": short})
        elif m := PFX_HIT_RE.search(line):
            events.append({"kind": "PFX-" + m.group(1), "request": m.group(2), "line": lineno, "text": short})
    return events


def annotate(events: list[dict]) -> None:
    """Allocation generations, decode-step index, and eviction caller labels."""
    gen: dict[int, int] = {}
    step = 0
    inside_dummy = False
    last_marker = None          # most recent [OBS] context marker outside a dummy bracket
    for e in events:
        e["step"] = step        # schedule segment that precedes decode step `step`
        k = e["kind"]
        if k == "BUCKET":
            e["step_index"] = step
            step += 1
        elif k == "ALLOC":
            obs = _ints(e["kv"]["OB"])
            for ob in obs:
                gen[ob] = gen.get(ob, 0) + 1
            e["ob"] = obs
            e["gen"] = [gen[ob] for ob in obs]
        elif k == "DUMMY-BEGIN":
            inside_dummy = True
        elif k == "DUMMY-END":
            inside_dummy = False
            e["ob"] = int(e["kv"]["OB"])
            e["gen_of_ob"] = gen.get(e["ob"], 0)
        elif k == "CAN-ALLOCATE" and not inside_dummy:
            last_marker = "request_alloc"
        elif k == "FREE":
            last_marker = "preemption" if e["kv"].get("PREEMPTION") == "True" else "free"
        elif k == "EVICT":
            ob = int(e["kv"]["OB"])
            e["ob"] = ob
            e["gen"] = gen.get(ob, 0)
            e["caller"] = ("dummy" if inside_dummy else
                           last_marker if last_marker in ("request_alloc", "preemption") else
                           "unlabeled")


def brackets(events: list[dict]) -> list[dict]:
    """Each DUMMY-BEGIN ... DUMMY-END pair and what happened inside it."""
    out, begin = [], None
    for i, e in enumerate(events):
        if e["kind"] == "DUMMY-BEGIN":
            begin = i
        elif e["kind"] == "DUMMY-END" and begin is not None:
            b, inner = events[begin], events[begin + 1:i]
            out.append({"begin_line": b["line"], "step": b["step"],
                        "free_before": int(b["kv"]["FREE_BEFORE"]), "head": int(b["kv"]["HEAD"]),
                        "free_after": int(e["kv"]["FREE_AFTER"]), "ob": e["ob"],
                        "evictions": [f"OB{x['ob']}#{x['gen']}" for x in inner if x["kind"] == "EVICT"],
                        "allocs_inside": sum(1 for x in inner if x["kind"] == "ALLOC")})
            begin = None
    return out


FREE_FIELD = {"CAN-ALLOCATE": "FREE", "DUMMY-BEGIN": "FREE_BEFORE", "DUMMY-END": "FREE_AFTER",
              "ALLOC": "FREE_AFTER", "EVICT": "FREE_AFTER", "FREE": "FREE"}


def free_ledger(events: list[dict]) -> dict:
    """Free-count bookkeeping: ALLOC takes |OB|, EVICT gives back 1, nothing else moves it.

    A dummy acquisition that allocated, or a dummy release, would have to move the
    free count on some line that is neither ALLOC nor EVICT -- a break here.
    """
    prev, breaks, checked = None, [], 0
    for e in events:
        field = FREE_FIELD.get(e["kind"])
        if field is None or field not in e.get("kv", {}):
            continue
        val = int(e["kv"][field])
        if prev is not None:
            want = prev - len(e["ob"]) if e["kind"] == "ALLOC" else prev + 1 if e["kind"] == "EVICT" else prev
            checked += 1
            if val != want:
                breaks.append({"line": e["line"], "kind": e["kind"], "expected": want, "observed": val})
        prev = val
    return {"transitions_checked": checked, "breaks": len(breaks), "first_breaks": breaks[:5]}


def questions(events: list[dict]) -> dict:
    steps = [e for e in events if e["kind"] == "BUCKET"]
    dummy_by_step: dict[int, int] = {}
    for e in events:
        if e["kind"] == "DUMMY-BEGIN":
            dummy_by_step[e["step"]] = dummy_by_step.get(e["step"], 0) + 1
    n_of = {s["step_index"]: s["n"] for s in steps}
    trailing = sum(1 for e in events if e["kind"] == "DUMMY-BEGIN" and e["step"] not in n_of)
    br = brackets(events)

    # Q1 -- first dummy request relative to the first decode step and first allocation.
    idx = {k: next((i for i, e in enumerate(events) if e["kind"] == k), None)
           for k in ("DUMMY-BEGIN", "BUCKET", "ALLOC")}
    first_dummy = events[idx["DUMMY-BEGIN"]] if idx["DUMMY-BEGIN"] is not None else None
    q1 = {"first_dummy_line": first_dummy["line"] if first_dummy else None,
          "decode_steps_before_first_dummy": (sum(1 for e in events[:idx["DUMMY-BEGIN"]] if e["kind"] == "BUCKET")
                                              if first_dummy else None),
          "allocs_before_first_dummy": (sum(1 for e in events[:idx["DUMMY-BEGIN"]] if e["kind"] == "ALLOC")
                                        if first_dummy else None),
          "first_dummy_step_n": n_of.get(first_dummy["step"]) if first_dummy else None}

    # Q2 -- one request per decode step with 0 < n < 8, or held across steps?
    partial = [i for i, n in n_of.items() if 0 < n < MAX_RUNNING]
    calls = [dummy_by_step.get(i, 0) for i in partial]
    same_as_prev = sum(1 for a, b in zip(br, br[1:]) if a["ob"] == b["ob"])
    no_ev = [b for b in br if not b["evictions"]]
    q2 = {"partial_steps": len(partial),
          "calls_per_partial_step": {str(c): calls.count(c) for c in sorted(set(calls))},
          "dummy_calls_total": sum(1 for e in events if e["kind"] == "DUMMY-BEGIN"),
          "dummy_calls_outside_decode_steps": trailing,
          "consecutive_same_ob": same_as_prev, "consecutive_pairs": max(len(br) - 1, 0),
          "release": {"brackets": len(br), "no_evict_brackets": len(no_ev),
                      "no_evict_free_unchanged": sum(1 for b in no_ev if b["free_after"] == b["free_before"]),
                      "no_evict_free_decreased": sum(1 for b in no_ev if b["free_after"] < b["free_before"]),
                      "no_evict_returned_head": sum(1 for b in no_ev if b["ob"] == b["head"]),
                      "evict_brackets": len(br) - len(no_ev),
                      "evict_free_after_eq_before_plus_evictions": sum(
                          1 for b in br if b["evictions"]
                          and b["free_after"] == b["free_before"] + len(b["evictions"])),
                      "alloc_inside_dummy_bracket": sum(b["allocs_inside"] for b in br),
                      "ledger": free_ledger(events)}}

    # Q3/Q4 -- does a request take the dummy's slot, and what happens next?
    # The dummy's OB stays "pending" from its DUMMY-END until a request ALLOC takes
    # it, an EVICT hits it, or a newer DUMMY-END supersedes it ("그 사이" in the plan).
    pending = None
    taken, dummy_evicted, alloc_other = [], [], 0
    for i, e in enumerate(events):
        if e["kind"] == "DUMMY-END":
            pending = e
        elif e["kind"] == "ALLOC" and pending:
            if pending["ob"] in e["ob"]:
                taken.append(i)
                pending = None
            else:
                alloc_other += 1
        elif e["kind"] == "EVICT" and pending and e["ob"] == pending["ob"]:
            dummy_evicted.append(e["line"])
            pending = None
    follow = []
    for i in taken:
        nb = next((j for j in range(i + 1, len(events)) if events[j]["kind"] == "DUMMY-BEGIN"), None)
        if nb is None:
            follow.append({"alloc_line": events[i]["line"], "next_dummy_line": None})
            continue
        b = next(x for x in br if x["begin_line"] == events[nb]["line"])
        follow.append({"alloc_line": events[i]["line"], "alloc_ob": f"OB{events[i]['ob'][0]}#{events[i]['gen'][0]}",
                       "next_dummy_line": b["begin_line"], "free_before": b["free_before"],
                       "evictions_in_bracket": b["evictions"], "next_dummy_ob": b["ob"]})
    q3 = {"alloc_took_pending_dummy_ob": len(taken), "evict_of_pending_dummy_ob": len(dummy_evicted),
          "evict_of_pending_dummy_ob_lines": dummy_evicted, "alloc_with_pending_other_ob": alloc_other}
    q4 = {"after_take": follow,
          "reacquire_with_eviction": sum(1 for f in follow if f["next_dummy_line"] and f["evictions_in_bracket"]),
          "reacquire_without_eviction": sum(1 for f in follow if f["next_dummy_line"] and not f["evictions_in_bracket"]),
          "no_reacquire": sum(1 for f in follow if f["next_dummy_line"] is None)}

    # Q5 -- decode steps at the ceiling.
    full = [i for i, n in n_of.items() if n == MAX_RUNNING]
    exits = []
    for i in full:
        nxt = n_of.get(i + 1)
        if nxt is not None and nxt < MAX_RUNNING:
            seg = [b for b in br if b["step"] == i + 1]
            exits.append({"last_ceiling_step": i, "next_n": nxt, "dummy_calls": len(seg),
                          "free_before": [b["free_before"] for b in seg],
                          "evictions_in_bracket": [x for b in seg for x in b["evictions"]],
                          "dummy_ob": [b["ob"] for b in seg]})
    q5 = {"steps_at_ceiling": len(full),
          "dummy_calls_in_ceiling_steps": sum(dummy_by_step.get(i, 0) for i in full),
          "transitions_into_ceiling": sum(1 for i in full if i > 0 and n_of.get(i - 1, 0) < MAX_RUNNING),
          "transitions_out_of_ceiling": len(exits), "exits": exits}

    evicts = [e for e in events if e["kind"] == "EVICT"]
    allocs = [e for e in events if e["kind"] == "ALLOC"]
    reassigned = []
    for e in evicts:
        later = any(a["line"] > e["line"] and e["ob"] in a["ob"] for a in allocs)
        reassigned.append(later)
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
            "evictions": {"obs": len(evicts),
                          "pfx": sum(1 for e in events if e["kind"] == "PFX-EVICTION"),
                          "by_caller": {c: sum(1 for e in evicts if e["caller"] == c)
                                        for c in ("dummy", "request_alloc", "preemption", "unlabeled")},
                          "never_reassigned": sum(1 for r in reassigned if not r),
                          "never_reassigned_by_caller": {c: sum(1 for e, r in zip(evicts, reassigned)
                                                                if not r and e["caller"] == c)
                                                         for c in ("dummy", "request_alloc")},
                          "labels": [f"OB{e['ob']}#{e['gen']}:{e['caller']}" for e in evicts]},
            "allocs": len(allocs), "pfx_allocs": sum(1 for e in events if e["kind"] == "PFX-ALLOC"),
            "decode_steps": len(steps),
            "n_histogram": {str(n): sum(1 for s in steps if s["n"] == n) for n in sorted({s["n"] for s in steps})}}


def excerpt(events: list[dict], line_from: int, line_to: int, limit: int = 40) -> list[str]:
    rows = [e for e in events if line_from <= e["line"] <= line_to]
    return [f"L{e['line']}: {e['text'][:170]}" for e in rows[:limit]]


def cmd_pilot(args) -> int:
    log = args.run / "server-pilot.log"
    text = log.read_text(errors="replace")
    ev = parse(log)
    obs = sum(1 for e in ev if e["kind"] not in ("BUCKET",) and not e["kind"].startswith("PFX"))
    steps = sum(1 for e in ev if e["kind"] == "BUCKET")
    per_kind = {}
    for e in ev:
        per_kind[e["kind"]] = per_kind.get(e["kind"], 0) + 1
    out = {"obs_lines": obs, "decode_steps": steps,
           "obs_per_step": obs / steps if steps else None, "per_kind": per_kind,
           "log_bytes": log.stat().st_size, "log_lines": text.count("\n"),
           "model_p50_ms": metrics_p50(text, "MODEL"), "sampler_p50_ms": metrics_p50(text, "SAMPLER"),
           "flood": (obs / steps > args.max_per_step) if steps else None,
           "max_per_step": args.max_per_step}
    (args.run / "pilot.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


def cmd_analyze(args) -> int:
    run = args.run
    trials = {}
    for log in sorted(run.glob("server-[AB].*.log")):
        tag = log.name[len("server-"):-len(".log")]
        ev = parse(log)
        annotate(ev)
        q = questions(ev)
        if tag.startswith("A."):
            key = tag[2:]
            m = int(re.match(r"B(\d+)", key).group(1))
            q["expected_evictions_max0_m_minus5"] = max(0, m - 5)
            t15 = TASK15_RUN / f"server-{key}.log"
            q["task15_same_prompts_evictions"] = (len(PFX_EVICT_RE.findall(t15.read_text(errors="replace")))
                                                  if t15.exists() else None)
        ev_ = q["evictions"]
        c = {"C1_obs_eq_pfx": ev_["obs"] == ev_["pfx"]}
        if tag.startswith("A."):
            c["C2_eq_max0_m_minus5"] = ev_["obs"] == q["expected_evictions_max0_m_minus5"]
            t15n = q["task15_same_prompts_evictions"]
            c["C3_eq_task15"] = None if t15n is None else ev_["obs"] == t15n
        c["C4_never_reassigned"] = ev_["never_reassigned"]
        c["C4_eq_task58_rule"] = ev_["never_reassigned"] == (1 if ev_["obs"] > 0 else 0)
        c["C4_never_reassigned_by_caller"] = ev_["never_reassigned_by_caller"]
        q["consistency"] = c
        first = q["q1"]["first_dummy_line"] or 0
        q["excerpt_first_dummy"] = excerpt(ev, max(first - 30, 0), first + 30)
        takes = q["q4"]["after_take"]
        if takes:
            a = takes[0]["alloc_line"]
            q["excerpt_first_take"] = excerpt(ev, a - 25, a + 40)
        ev_lines = [e["line"] for e in ev if e["kind"] == "EVICT"]
        if ev_lines:
            q["excerpt_evictions"] = [excerpt(ev, x - 12, x + 3, 16) for x in ev_lines[:4]]
        full_steps = [e for e in ev if e["kind"] == "BUCKET" and e["n"] == MAX_RUNNING]
        if full_steps:
            s0, s1 = full_steps[0]["line"], full_steps[-1]["line"]
            q["excerpt_into_ceiling"] = excerpt(ev, s0 - 25, s0 + 6)
            q["excerpt_out_of_ceiling"] = excerpt(ev, s1 - 3, s1 + 25)
        trials[tag] = q
    (args.output).write_text(json.dumps(trials, indent=2, ensure_ascii=False) + "\n")
    for tag, q in trials.items():
        ev_ = q["evictions"]
        print(f"{tag}: steps {q['decode_steps']} n {q['n_histogram']} allocs {q['allocs']} "
              f"evict obs/pfx {ev_['obs']}/{ev_['pfx']} by {ev_['by_caller']} "
              f"never-reassigned {ev_['never_reassigned']} {ev_['never_reassigned_by_caller']}"
              + (f" | expected {q['expected_evictions_max0_m_minus5']} TASK15 {q['task15_same_prompts_evictions']}"
                 if tag.startswith("A.") else ""))
        print(f"   Q1 {q['q1']}\n   Q2 {q['q2']}\n   Q3 {q['q3']}  Q4 with/without/none "
              f"{q['q4']['reacquire_with_eviction']}/{q['q4']['reacquire_without_eviction']}/{q['q4']['no_reacquire']}\n"
              f"   Q5 {q['q5']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pilot")
    a.add_argument("--run", type=Path, required=True)
    a.add_argument("--max-per-step", type=float, default=10.0)
    b = sub.add_parser("analyze")
    b.add_argument("--run", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    return {"pilot": cmd_pilot, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
