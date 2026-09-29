#!/usr/bin/env python3
"""Do the two semantic switches explain the simulator's systematic error?

Registered in docs/research/SIM_SEMANTICS_PREREG.md before this was run.

Cells: the eight validation comparisons (seed 20261000 N=6,8,10 and seed
20261100 N=6; arms BATCHONLY and TUNED against BASE; blocks 0,1,2) and the
four BASE reuse counts. For each combination of ``release_rule`` and
``dummy_mode`` the simulator is run on the measured plans, exactly as
``dummy_block_effect.py`` does, and compared with the measured A' channel.

Sign convention: ``e = measured ratio - simulated ratio``. Positive means the
simulator predicts more saving than was measured (the manuscript's IV-E
convention; all eight are positive with the default switches).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

from config_device import ARMS, aggregate, descriptor_for_arm  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from dummy_block_effect import measured_reuse  # noqa: E402
from sim_compare import sessions_from_plan  # noqa: E402

ST2 = REPO / "results/npu/stage2"
RUNS = [(20261000, ST2 / "20260823-183505-final-confirm", (6, 8, 10)),
        (20261100, ST2 / "20260824-160028-n6-reconfirm", (6,))]
COMBOS = [("deferred", "off"), ("immediate", "off"), ("deferred", "pre_evict"),
          ("immediate", "pre_evict"), ("deferred", "reserved")]
BLOCKS = [0, 1, 2]


def sim(run: Path, arm: str, n: int, blk: int, release: str, dummy: str):
    meta = json.loads((run / "probe" / f"meta.{arm}.n{n}.b{blk}.json").read_text())
    sessions = sessions_from_plan(meta["plan"], meta["block_id"])
    cfg = SimConfig(max_running_requests=ARMS[arm][1], release_rule=release,
                    dummy_mode=dummy)
    return simulate(descriptor_for_arm(arm), sessions, cfg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path,
                    default=REPO / "results/npu/stage3/sim_semantics/effect.json")
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    base_rows = []
    for seed, run, ns in RUNS:
        for n in ns:
            base_meas = aggregate(run, "BASE", n, BLOCKS)
            mh, mt = measured_reuse(run, "BASE", n, BLOCKS)
            meas = {arm: aggregate(run, arm, n, BLOCKS)["a_prime_s"] / base_meas["a_prime_s"]
                    for arm in ("BATCHONLY", "TUNED")}
            for release, dummy in COMBOS:
                res = {arm: [sim(run, arm, n, b, release, dummy) for b in BLOCKS]
                       for arm in ("BASE", "BATCHONLY", "TUNED")}
                bb = sum(r.busy_s for r in res["BASE"])
                base_rows.append({"seed": seed, "N": n, "release": release, "dummy": dummy,
                                  "sim_reuse": sum(r.reuse_hits for r in res["BASE"]),
                                  "resume": sum(r.resume_requests for r in res["BASE"]),
                                  "measured_reuse": mh, "measured_total": mt,
                                  "sim_evictions": sum(len(r.evictions) for r in res["BASE"])})
                for arm in ("BATCHONLY", "TUNED"):
                    ratio = sum(r.busy_s for r in res[arm]) / bb
                    rows.append({"seed": seed, "N": n, "arm": arm, "release": release,
                                 "dummy": dummy, "sim_ratio": ratio, "measured_ratio": meas[arm],
                                 "e": meas[arm] - ratio,
                                 "sim_reuse": sum(r.reuse_hits for r in res[arm])})
    summary = {}
    for release, dummy in COMBOS:
        sel = [r for r in rows if r["release"] == release and r["dummy"] == dummy]
        bs = [b for b in base_rows if b["release"] == release and b["dummy"] == dummy]
        summary[f"{release}/{dummy}"] = {
            "mean_abs_e": statistics.mean(abs(r["e"]) for r in sel),
            "mean_e": statistics.mean(r["e"] for r in sel),
            "positive_e": sum(1 for r in sel if r["e"] > 0),
            "baseline_gaps": [abs(b["sim_reuse"] - b["measured_reuse"]) for b in bs],
            "baseline_sim_reuse": [f"{b['sim_reuse']}/{b['resume']}" for b in bs]}
    off = summary["deferred/off"]
    both = summary["immediate/pre_evict"]
    c1 = both["mean_abs_e"] < off["mean_abs_e"]
    c2 = sum(1 for a, b in zip(both["baseline_gaps"], off["baseline_gaps"]) if a <= b) >= 3
    c3 = both["mean_abs_e"] <= 0.75 * off["mean_abs_e"]
    verdict = "PASS" if (c1 and c2 and c3) else ("PARTIAL" if (c1 and c2) else "FAIL")
    out = {"verdict": verdict, "criteria": {"C1_mean_abs_e_down": c1,
                                            "C2_baseline_3of4": c2,
                                            "C3_reduction_ge_25pct": c3},
           "summary": summary, "rows": rows, "baseline": base_rows}
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"verdict": verdict, "criteria": out["criteria"]}, ensure_ascii=False))
    for k, v in summary.items():
        print(k, {kk: (round(vv, 5) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
