#!/usr/bin/env python3
"""Admission-path eviction under back-to-back admissions (exploratory).

TASK63 labelled every eviction in a sequential load and found all of them on
the padding-dummy path: the dummy keeps one slot free during decode, so an
admission never met a full pool. This script checks what happens when two
admissions follow each other with no decode step in between.

Per repetition it reuses the TASK63 parser (file order = execution order,
dummy brackets, eviction caller labels), finds the two treatment allocations
by response id, and classifies the repetition by the registered rule in
docs/research/ADMISSION_EVICTION_PLAN.md:

  SATURATION_FAIL   the first treatment admission did not see FREE=1
  ESTABLISHED       no [BUCKET] and no DUMMY-BEGIN between the first treatment
                    ALLOC and the second request's admission entry
  NOT_ESTABLISHED   one of them occurs in between
  UNCLASSIFIABLE    the treatment ALLOC or an admission entry is missing

Subcommands:
  classify  one repetition; prints the class as the last stdout line
            (the runner's stop / switch rule reads it)
  analyze   all repetitions of a run: Q1-Q3 patterns, eviction targets,
            arithmetic consistency
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dummy_lifecycle import _ints, annotate, excerpt, free_ledger, parse  # noqa: E402

POOL = 8
N_BACKGROUND = 8


def mark_brackets(events: list[dict]) -> None:
    inside = False
    for e in events:
        if e["kind"] == "DUMMY-BEGIN":
            inside = True
            e["in_dummy"] = True
        elif e["kind"] == "DUMMY-END":
            e["in_dummy"] = True
            inside = False
        else:
            e["in_dummy"] = inside


def is_admission_entry(e: dict) -> bool:
    """A new request's slot check: CAN-ALLOCATE outside a dummy bracket with COMPUTED=0, NUM_NEW>0."""
    return (e["kind"] == "CAN-ALLOCATE" and not e["in_dummy"]
            and int(e["kv"]["COMPUTED"]) == 0 and int(e["kv"]["NUM_NEW"]) > 0)


def _matches(alloc: dict, rid: str | None) -> bool:
    req = alloc["kv"].get("REQUEST", "")
    return bool(rid) and (req == rid or req.startswith(rid + "-"))


def treatment_allocs(events: list[dict], probe: dict) -> tuple[str, list[tuple[str, dict]]]:
    """(method, [(label, ALLOC event), ...]) in log order."""
    allocs = [e for e in events if e["kind"] == "ALLOC"]
    rids = {r["label"]: r.get("response_id") for r in probe.get("records", []) if r["label"] in ("X", "Y")}
    if len(rids) == 2 and all(rids.values()):
        found = []
        for lab, rid in rids.items():
            a = next((x for x in allocs if _matches(x, rid)), None)
            if a is not None:
                found.append((a["line"], lab, a))
        return "response_id", [(lab, a) for _, lab, a in sorted(found, key=lambda t: t[0])]
    rest = allocs[N_BACKGROUND:]
    return "order", [(f"T{i + 1}", a) for i, a in enumerate(rest[:2])]


def fifo_targets(events: list[dict]) -> list[dict]:
    """For each EVICT: the inactive set at that moment and its earliest-allocated member."""
    state: dict[int, str] = {}
    alloc_line: dict[int, int] = {}
    out = []
    for e in events:
        k = e["kind"]
        if k == "ALLOC":
            for ob in e["ob"]:
                state[ob] = "active"
                alloc_line[ob] = e["line"]
        elif k == "FREE" and e["kv"].get("PREEMPTION") == "False":
            for ob in _ints(e["kv"]["OB"]):
                state[ob] = "inactive"
        elif k == "EVICT":
            inactive = sorted((alloc_line.get(o, -1), o) for o, s in state.items() if s == "inactive")
            expected = inactive[0][1] if inactive else None
            out.append({"line": e["line"], "ob": e["ob"], "gen": e["gen"], "caller": e["caller"],
                        "inactive_before_in_alloc_order": [o for _, o in inactive],
                        "earliest_inactive": expected, "is_earliest": e["ob"] == expected})
            state[e["ob"]] = "free"
    return out


def classify(events: list[dict], probe: dict) -> dict:
    method, tr = treatment_allocs(events, probe)
    res: dict = {"label_method": method, "treatment_order": [lab for lab, _ in tr]}
    if not tr:
        return {**res, "class": "UNCLASSIFIABLE", "reason": "no treatment ALLOC"}
    idx = {id(e): i for i, e in enumerate(events)}
    a1 = tr[0][1]
    i1 = idx[id(a1)]
    e1 = next((events[j] for j in range(i1 - 1, -1, -1) if is_admission_entry(events[j])), None)
    j2 = next((j for j in range(i1 + 1, len(events)) if is_admission_entry(events[j])), None)
    res["A1"] = {"label": tr[0][0], "line": a1["line"], "ob": a1["ob"], "gen": a1["gen"]}
    res["E1"] = ({"line": e1["line"], "free": int(e1["kv"]["FREE"]), "required": int(e1["kv"]["REQUIRED_OB"])}
                 if e1 else None)
    if e1 is None or j2 is None:
        return {**res, "class": "UNCLASSIFIABLE",
                "reason": "E1 missing" if e1 is None else "E2 missing"}
    between = events[i1 + 1:j2]
    res["between_A1_E2"] = {"buckets": sum(1 for x in between if x["kind"] == "BUCKET"),
                            "dummy_begins": sum(1 for x in between if x["kind"] == "DUMMY-BEGIN"),
                            "t_A1": a1["t"], "t_E2": events[j2]["t"]}
    if res["E1"]["free"] != 1:
        cls = "SATURATION_FAIL"
    elif res["between_A1_E2"]["buckets"] == 0 and res["between_A1_E2"]["dummy_begins"] == 0:
        cls = "ESTABLISHED"
    else:
        cls = "NOT_ESTABLISHED"
    res["class"] = cls

    # Q1: the E2 segment runs to the first ALLOC / [BUCKET] / DUMMY-BEGIN / admission entry.
    e2 = events[j2]
    free2, req2 = int(e2["kv"]["FREE"]), int(e2["kv"]["REQUIRED_OB"])
    seg_evicts, end = [], None
    for x in events[j2 + 1:]:
        if x["kind"] in ("ALLOC", "BUCKET", "DUMMY-BEGIN") or is_admission_entry(x):
            end = x
            break
        if x["kind"] == "EVICT":
            seg_evicts.append(x)
    a2 = tr[1][1] if len(tr) > 1 else None
    ends_with_a2 = end is not None and a2 is not None and end is a2
    callers = [x["caller"] for x in seg_evicts]
    if free2 < req2 and seg_evicts and ends_with_a2 and all(c == "request_alloc" for c in callers):
        pattern = "P1"
    elif free2 >= req2 and not seg_evicts and ends_with_a2:
        pattern = "P2"
    elif free2 < req2 and not seg_evicts and not ends_with_a2:
        pattern = "P3"
    else:
        pattern = "OTHER"
    res["E2"] = {"line": e2["line"], "free": free2, "required": req2}
    res["q1"] = {"pattern": pattern, "segment_end": (end["kind"] if end else None),
                 "segment_end_line": (end["line"] if end else None),
                 "evictions": [f"OB{x['ob']}#{x['gen']}:{x['caller']}" for x in seg_evicts]}

    # Q3: what happened to the second treatment request.
    second_label = tr[1][0] if len(tr) > 1 else next(
        (lab for lab in ("X", "Y", "T2") if lab != tr[0][0]), None)
    rec2 = next((r for r in probe.get("records", []) if r["label"] == second_label), None)
    q3: dict = {"second_label": second_label, "status": rec2.get("status") if rec2 else None,
                "error": rec2.get("error") if rec2 else None}
    if a2 is not None:
        i2 = idx[id(a2)]
        mid = events[j2:i2]
        q3.update({"A2_line": a2["line"], "A2_ob": a2["ob"], "A2_gen": a2["gen"],
                   "buckets_waited": sum(1 for x in mid if x["kind"] == "BUCKET"),
                   "admission_entries": sum(1 for x in mid if is_admission_entry(x)),
                   "evictions_between": [f"OB{x['ob']}#{x['gen']}:{x['caller']}" for x in mid if x["kind"] == "EVICT"]})
    if pattern == "P1":  # Q3 asks only about repetitions where the admission did not evict
        q3["pattern"] = "NOT_APPLICABLE"
    elif pattern == "P2":
        q3["pattern"] = "IMMEDIATE"
    elif a2 is None or (rec2 is not None and rec2.get("status") != 200):
        q3["pattern"] = "ERROR_OR_UNSERVED"
    elif q3.get("buckets_waited", 0) >= 1:
        q3["pattern"] = "WAIT_THEN_ALLOC"
    else:
        q3["pattern"] = "OTHER"
    res["q3"] = q3
    return res


def consistency(events: list[dict], probe: dict) -> dict:
    evicts = [e for e in events if e["kind"] == "EVICT"]
    allocs = [e for e in events if e["kind"] == "ALLOC"]
    reassigned = [any(a["line"] > e["line"] and e["ob"] in a["ob"] for a in allocs) for e in evicts]
    recs = probe.get("records", [])
    return {
        "C1_obs_evict": len(evicts),
        "C1_pfx_eviction": sum(1 for e in events if e["kind"] == "PFX-EVICTION"),
        "C1_ok": len(evicts) == sum(1 for e in events if e["kind"] == "PFX-EVICTION"),
        "C2_allocs": len(allocs),
        "C2_expected_max0_alloc_plus1_minus8": max(0, len(allocs) + 1 - POOL),
        "C2_ok": len(evicts) == max(0, len(allocs) + 1 - POOL),
        "C3_preemption_free": sum(1 for e in events if e["kind"] == "FREE" and e["kv"].get("PREEMPTION") == "True"),
        "C4_ledger": free_ledger(events),
        "C5_statuses": {r["label"]: r.get("status") for r in recs},
        "C5_treatment_usage": {r["label"]: r.get("usage") for r in recs if r["label"] in ("X", "Y")},
        "C6_never_reassigned_by_caller": {c: sum(1 for e, r in zip(evicts, reassigned) if not r and e["caller"] == c)
                                          for c in ("dummy", "request_alloc", "preemption", "unlabeled")},
        "evictions_by_caller": {c: sum(1 for e in evicts if e["caller"] == c)
                                for c in ("dummy", "request_alloc", "preemption", "unlabeled")},
    }


def load(log: Path, probe_path: Path) -> tuple[list[dict], dict]:
    events = parse(log)
    annotate(events)
    mark_brackets(events)
    probe = json.loads(probe_path.read_text()) if probe_path.exists() else {}
    return events, probe


def cmd_classify(args) -> int:
    events, probe = load(args.log, args.probe)
    res = classify(events, probe)
    if args.out:
        args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(res["class"])
    return 0


def cmd_analyze(args) -> int:
    run = args.run
    order = []
    for line in (run / "order.txt").read_text().splitlines():
        m = re.match(r"(R\d+) (\w+) (\w+) ", line)
        if m:
            order.append(m.groups())
    reps = {}
    for tag, mode, cls in order:
        log, probe_path = run / f"server-{tag}.log", run / "probe" / f"admission.{tag}.json"
        if not log.exists():
            reps[tag] = {"mode": mode, "class": cls, "missing_log": True}
            continue
        events, probe = load(log, probe_path)
        res = classify(events, probe)
        rep = {"mode": mode, "class_runner": cls, **res, "fifo": fifo_targets(events),
               "consistency": consistency(events, probe),
               "send_gap_ms": None}
        tr = [r for r in probe.get("records", []) if r["label"] in ("X", "Y")]
        if len(tr) == 2 and all("send_start_s" in r for r in tr):
            rep["send_gap_ms"] = round((tr[1]["send_start_s"] - tr[0]["send_start_s"]) * 1e3, 3)
        if "A1" in res and res.get("E2"):
            rep["excerpt_treatment"] = excerpt(events, res["E1"]["line"] - 2 if res.get("E1") else res["A1"]["line"] - 5,
                                               (res["q3"].get("A2_line") or res["E2"]["line"]) + 12, 60)
        reps[tag] = rep

    summary: dict = {}
    for mode in ("consecutive", "simultaneous"):
        rs = {t: r for t, r in reps.items() if r["mode"] == mode}
        if not rs:
            continue
        est = {t: r for t, r in rs.items() if r.get("class") == "ESTABLISHED"}
        other = {t: r for t, r in rs.items() if r.get("class") != "ESTABLISHED"}
        fifo_est = [f for r in est.values() for f in r["fifo"]]

        def count(d: dict, key) -> dict:
            out: dict = {}
            for r in d.values():
                k = key(r)
                out[k] = out.get(k, 0) + 1
            return out

        summary[mode] = {
            "reps": len(rs),
            "classes": count(rs, lambda r: r.get("class")),
            "runner_class_agrees": all(r.get("class") == r.get("class_runner") for r in rs.values() if "class_runner" in r),
            "q1_patterns_established": count(est, lambda r: r["q1"]["pattern"]),
            "q1_patterns_other": count({t: r for t, r in other.items() if "q1" in r}, lambda r: r["q1"]["pattern"]),
            "q2_established": {c: {"n": sum(1 for f in fifo_est if f["caller"] == c),
                                   "is_earliest": sum(1 for f in fifo_est if f["caller"] == c and f["is_earliest"])}
                               for c in ("request_alloc", "dummy", "preemption", "unlabeled")},
            "q3_patterns_established": count(est, lambda r: r["q3"]["pattern"]),
            "consistency_all_C1": all(r["consistency"]["C1_ok"] for r in rs.values() if "consistency" in r),
            "consistency_all_C2": all(r["consistency"]["C2_ok"] for r in rs.values() if "consistency" in r),
            "ledger_breaks_total": sum(r["consistency"]["C4_ledger"]["breaks"] for r in rs.values() if "consistency" in r),
            "send_gap_ms": [r.get("send_gap_ms") for r in rs.values()],
        }
    out = {"summary": summary, "reps": reps}
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    for tag, r in reps.items():
        if "q1" in r:
            print(f"{tag} {r['mode']} {r['class']} A1={r['A1']['label']} E1free={r['E1']['free']} "
                  f"between={r['between_A1_E2']} E2free={r['E2']['free']} Q1={r['q1']['pattern']} "
                  f"{r['q1']['evictions']} Q3={r['q3']['pattern']} evict={r['consistency']['evictions_by_caller']} "
                  f"gap_ms={r['send_gap_ms']}")
        else:
            print(f"{tag} {r['mode']} {r.get('class')} {r.get('reason', '')}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("classify")
    a.add_argument("--log", type=Path, required=True)
    a.add_argument("--probe", type=Path, required=True)
    a.add_argument("--out", type=Path)
    b = sub.add_parser("analyze")
    b.add_argument("--run", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    return {"classify": cmd_classify, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
