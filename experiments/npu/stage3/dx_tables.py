#!/usr/bin/env python3
"""CSV tables of the 2026-10-08 directive from the verdict / report JSONs
(TASK117). No new computation beyond reading them.

usage: dx_tables.py  (writes docs/research/dx/DX_*.csv)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "results/npu/stage3"
OUT = REPO / "docs/research/dx"


def w(name, header, rows):
    with (OUT / name).open("w", newline="") as fh:
        c = csv.writer(fh, lineterminator="\n")
        c.writerow(header)
        c.writerows(rows)


def main() -> int:
    rows = []
    for run, lab in (("20261008-dx-a", "A1_v1"), ("20261009-dx-a2", "A2_v2")):
        d = json.loads((RES / run / "dx_verdict_a.json").read_text())
        for cond, c in d["conditions"].items():
            for sig, v in c["signals"].items():
                rows.append([lab, cond, sig, v["median"], v["min"], v["max"], v["sd"],
                             ";".join(f"{x:.5f}" for x in v["per_pair"]), c["exceeds_1pct"], d["verdict"]])
    w("DX_A_PERTURBATION.csv", ["check", "condition", "signal", "median_rel_change", "min", "max", "sd",
                                 "per_pair", "condition_exceeds_1pct", "verdict"], rows)
    rows = []
    for run, n in (("20261008-dx-b", 18), ("20261008-dx-b8", 8)):
        d = json.loads((RES / run / "dx_report_b_off.json").read_text())
        for r in d["replicates"]:
            rows.append([n, r, d["R_RECON"]["per_rep"][str(r)] if str(r) in d["R_RECON"]["per_rep"] else d["R_RECON"]["per_rep"][r],
                         d["R_PRED"]["per_rep"][str(r)] if str(r) in d["R_PRED"]["per_rep"] else d["R_PRED"]["per_rep"][r]])
    w("DX_B_PER_REP.csv", ["N", "rep", "R_RECON_TUNED_over_BASE", "R_PRED"], rows)
    d = json.loads((RES / "20261008-dx-c/dx_verdict_c.json").read_text())
    rows = [[k, c["reuse_obs"], c["reuse_pred"], c["reuse_err"], c["h_tvd_pred"], c["throughput_per_s"],
             c["completed_per_hour"], c["mean_running_obs"], c["ttft_turn_ge1_median_s"], c["recon_per_turn_median_s"]]
            for k, c in d["cells"].items()]
    w("DX_C_CELLS.csv", ["cell", "reuse_obs", "reuse_pred", "reuse_err", "h_tvd", "throughput_per_s",
                         "completed_per_hour", "mean_running", "ttft_turn_ge1_median_s", "recon_per_turn_median_s"], rows)
    rows = []
    for cap, v in d["cost_ratio"].items():
        for i, x in enumerate(v["recon_per_rep"]):
            rows.append([cap, i, x, v["pred_median"]])
    w("DX_C_COST_PER_REP.csv", ["cap_s", "rep", "R_RECON_TUNED_over_BASE", "R_PRED_median"], rows)
    g = d["gap_stats"]
    w("DX_C_GAPS.csv", ["dist", "mean", "p50", "p90", "p99", "max", "sum", "clipped_share_of_gaps",
                        "clipped_share_of_raw_sum"],
      [[k, v["mean"], v["p50"], v["p90"], v["p99"], v["max"], v["sum"], v.get("clipped_share_of_gaps"),
        v.get("clipped_share_of_raw_sum")] for k, v in g.items()])
    e = json.loads((RES / "20261008-dx-e/dx_verdict_e.json").read_text())
    rows = []
    for c, xs in e["primary"]["per_rep"].items():
        for i, x in enumerate(xs):
            rows.append([c, i, x, e["pred"][c]])
    w("DX_E_PER_REP.csv", ["config", "rep", "R_RECON_over_BATCHONLY", "R_PRED_median"], rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
