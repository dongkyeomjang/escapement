#!/usr/bin/env python3
"""G-10 A: ON/OFF comparison of the exec-timing development check.

Prereg: docs/research/gpu/G10_A_PREREG.md section 3. Per condition (load x
configuration), per pair k: relative change ON/OFF - 1 of (1) throughput
(generated tokens arriving in the 60 s window) and (2) the median dispatch gap
of consecutive FULL decode-only steps at the representative width w* (low 2,
sat 8). Condition verdict: |median over pairs| <= 1 % for both -> OK, else
EXCEEDS. Independent checks of the ON runs are summarised.

usage: exec_check_analyze.py --run-dir <abs> --out <abs json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

WSTAR = {"low": "2", "sat": "8"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    order = json.loads((Path(__file__).with_name("exec_check_order.json")).read_text())
    got: dict = {}
    hist: dict = {}
    for e in order:
        for d in (a.run_dir / e["tag"], a.run_dir / f"{e['tag']}.retry1"):
            f = d / "summary.json"
            if not f.exists():
                continue
            s = json.loads(f.read_text())
            hist.setdefault(e["tag"], []).append({"dir": d.name, "valid": s["valid"], "reasons": s["invalid_reasons"]})
            if s["valid"] and e["tag"] not in got:
                got[e["tag"]] = s
    conds = {}
    for load in ("low", "sat"):
        for cfg in ("GPU_BASE", "GPU_KV"):
            rows = []
            for k in range(5):
                on, off = got.get(f"{load}.{cfg}.p{k}.exec1"), got.get(f"{load}.{cfg}.p{k}.exec0")
                if not (on and off):
                    rows.append({"pair": k, "complete": False})
                    continue
                w = WSTAR[load]
                g1, g0 = on["full_decode_gap_median_ms"].get(w), off["full_decode_gap_median_ms"].get(w)
                rows.append({"pair": k, "complete": True,
                             "thr_on": on["throughput_tok_s"], "thr_off": off["throughput_tok_s"],
                             "thr_change": on["throughput_tok_s"] / off["throughput_tok_s"] - 1,
                             "gap_on_ms": g1, "gap_off_ms": g0,
                             "gap_change": (g1 / g0 - 1) if (g1 and g0) else None,
                             "gap_n_on": on["full_decode_gap_count"].get(w), "gap_n_off": off["full_decode_gap_count"].get(w),
                             "exec_missing_window": on["exec_missing_window"],
                             "exec_overlaps_window": on["exec_overlaps_window"],
                             "exec_sum_over_span": (on["exec_sum_window_s"] / on["exec_device_span_window_s"]
                                                    if on.get("exec_device_span_window_s") else None),
                             "exec_sum_over_host_span": (on["exec_sum_window_s"] / on["window_step_span_s"]
                                                         if on["window_step_span_s"] else None),
                             "full_exec_median_ms": on["full_decode_exec_median_ms"].get(w),
                             "exec_over_gap": (on["full_decode_exec_median_ms"].get(w) / g1)
                             if (g1 and on["full_decode_exec_median_ms"].get(w)) else None,
                             "steps_on": on["window_steps"], "steps_off": off["window_steps"],
                             "gexec_lines_off": off["gexec_lines"]})
            C = [r for r in rows if r["complete"]]
            tc = [r["thr_change"] for r in C]
            gc = [r["gap_change"] for r in C if r["gap_change"] is not None]
            med_t = statistics.median(tc) if tc else None
            med_g = statistics.median(gc) if gc else None
            ok = (med_t is not None and med_g is not None and abs(med_t) <= 0.01 and abs(med_g) <= 0.01)
            conds[f"{load}/{cfg}"] = {"pairs": rows, "complete_pairs": len(C),
                                      "median_thr_change": med_t, "range_thr_change": [min(tc), max(tc)] if tc else None,
                                      "median_gap_change": med_g, "range_gap_change": [min(gc), max(gc)] if gc else None,
                                      "verdict": "OK" if ok else ("EXCEEDS" if C else "NO_DATA")}
    checks = {"missing_total": sum(r.get("exec_missing_window") or 0 for c in conds.values() for r in c["pairs"]),
              "overlaps_total": sum(r.get("exec_overlaps_window") or 0 for c in conds.values() for r in c["pairs"]),
              "exec_over_span_max": max((r["exec_sum_over_span"] for c in conds.values() for r in c["pairs"]
                                         if r.get("exec_sum_over_span") is not None), default=None),
              "gexec_lines_in_off_runs": sum(r.get("gexec_lines_off") or 0 for c in conds.values() for r in c["pairs"])}
    overall = "OK" if all(c["verdict"] == "OK" for c in conds.values()) else "EXCEEDS_OR_INCOMPLETE"
    out = {"validity": hist, "conditions": conds, "checks": checks, "overall": overall}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(overall, json.dumps(checks))
    for k, c in conds.items():
        print(k, c["verdict"], c["median_thr_change"], c["median_gap_change"], c["range_thr_change"], c["range_gap_change"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
