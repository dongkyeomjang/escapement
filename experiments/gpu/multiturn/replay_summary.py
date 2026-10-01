#!/usr/bin/env python3
"""GTASK12: verdict and report tables from replay.py output (prereg section 5-7).

Also re-runs the section-7 counterfactual replays to report how many judged
requests each single-rule change would get right (discrimination, not part of
the verdict).

usage: replay_summary.py --run-dir <abs> --replay <abs json> --out <abs json>
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import replay as RP  # noqa: E402


def variant_rates(run: Path) -> dict:
    data = RP.load(run)
    obs = RP.observed(data)
    w0, w1 = data["win"]["warmup_end_s"], data["win"]["eval_end_s"]
    judged = {sid: c for sid, (r, c) in obs.items()
              if r["turn"] >= 1 and w0 <= r["sent_s"] < w1 and c is not None}
    out = {}
    for name, rules in {"main": RP.MAIN, **RP.VARIANTS}.items():
        res = RP.replay(data, rules)
        p = res["pred"]
        ok = sum(1 for s, c in judged.items() if s in p and p[s]["hit"] == c)
        okb = sum(1 for s, c in judged.items() if s in p and (p[s]["hit"] > 0) == (c > 0))
        out[name] = {"exact": ok, "binary": okb, "n": len(judged), "error": res["error"],
                     "lookup_free_eq": res["integrity"].get("lookup_free_eq"),
                     "lookup": res["integrity"].get("lookup")}
    ev = RP.parse(run / "server.log")
    steps = [e for e in ev if e["kind"] == "STEP"]
    first_lookup = next(e["line"] for e in ev if e["kind"] == "LOOKUP")
    out["steps_before_first_lookup"] = sum(1 for e in steps if e["line"] < first_lookup)
    return {"run": run.name, **out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--replay", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    R = json.loads(a.replay.read_text())["lifecycles"]
    per, cell = [], defaultdict(Counter)
    verdict_ok = True
    for L in R:
        rq = [r for r in L["requests"] if r["in_window"]]
        c = Counter(r["status"] for r in rq)
        den = len(rq) - c["UNDECIDABLE"] - c["UNKNOWN"]
        acc = c["MATCH"] / den if den else None
        u = (c["UNDECIDABLE"] + c["UNKNOWN"]) / len(rq) if rq else None
        allrq = L["requests"]
        ca = Counter(r["status"] for r in allrq)
        ok = acc is not None and acc >= 0.95 and u <= 0.05
        verdict_ok &= ok
        n, cfg, _ = L["run"].split(".")
        key = f"{n[1:]}/{cfg}"
        cell[key].update({"n": len(rq), **c, "all_n": len(allrq), "all_match": ca["MATCH"],
                          "binary_match": sum(1 for r in rq if r["status"] == "MATCH"
                                              or (r.get("pred") is not None and r["obs"] is not None
                                                  and (r["pred"] > 0) == (r["obs"] > 0)))})
        per.append({"run": L["run"], "n": len(rq), "status": dict(c), "a": acc, "u": u, "pass": ok,
                    "mismatch_categories": dict(Counter(r.get("category") for r in rq
                                                        if r["status"] == "MISMATCH")),
                    "integrity": L["main_integrity"], "kv": L["kv"],
                    "ambiguous_steps": L["ambiguous_steps"], "error": L["main_error"]})
    runs = [a.run_dir / L["run"] for L in R]
    with ProcessPoolExecutor(16) as ex:
        var = list(ex.map(variant_rates, runs))
    vcell = defaultdict(lambda: defaultdict(Counter))
    for v in var:
        n, cfg, _ = v["run"].split(".")
        for name in ["main", *RP.VARIANTS]:
            vcell[f"{n[1:]}/{cfg}"][name].update({"exact": v[name]["exact"], "binary": v[name]["binary"],
                                                  "n": v[name]["n"]})
    out = {"verdict": "PASS" if verdict_ok else "FAIL", "per_lifecycle": per,
           "cells": {k: dict(v) for k, v in cell.items()},
           "variants_per_lifecycle": var,
           "variants_cells": {k: {n: dict(c) for n, c in v.items()} for k, v in vcell.items()}}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(out["verdict"])
    for k in sorted(vcell, key=lambda s: (int(s.split("/")[0]), s)):
        row = vcell[k]
        print(k, cell[k]["MATCH"], "/", cell[k]["n"], " ".join(
            f"{n}={row[n]['exact'] / row[n]['n']:.3f}" for n in ["main", *RP.VARIANTS]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
