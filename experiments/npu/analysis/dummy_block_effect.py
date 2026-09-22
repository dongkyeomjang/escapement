#!/usr/bin/env python3
"""What changes when the padding block is charged to the KV pool.

TASK63 watched this stack ask for a padding block on every decode step whose
request count lies strictly between zero and the execution ceiling, and stop
asking at the ceiling. TASK58 had already traced a one-block difference in
reclaim counts to the same request. The simulator never modelled it: its pool
holds requests and nothing else, and every recorded number was produced that
way.

``SimConfig.dummy_block`` charges the pool one extra slot while the batch is
partial. This file runs the validation cells and the reuse counts in both
settings and puts them side by side. It judges nothing -- the switch is off by
default and stays off until something other than this table says otherwise.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from config_device import ARMS, aggregate, descriptor_for_arm  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from sim_compare import sessions_from_plan  # noqa: E402


def sim_cell(run: Path, arm: str, n: int, blk: int, dummy: bool):
    label = f"{arm}.n{n}.b{blk}"
    meta = json.loads((run / "probe" / f"meta.{label}.json").read_text())
    sessions = sessions_from_plan(meta["plan"], meta["block_id"])
    cfg = SimConfig(max_running_requests=ARMS[arm][1], dummy_block=dummy)
    return simulate(descriptor_for_arm(arm), sessions, cfg)


def measured_reuse(run: Path, arm: str, n: int, blocks: list[int]) -> tuple[int, int]:
    hits = total = 0
    for blk in blocks:
        rows = [json.loads(l) for l in
                (run / "probe" / f"requests.{arm}.n{n}.b{blk}.jsonl").read_text().splitlines()
                if l.strip()]
        turn2 = [r for r in rows if r["turn"] > 0]
        hits += sum(1 for r in turn2 if (r.get("cached_tokens") or 0) > 0)
        total += len(turn2)
    return hits, total


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--baseline-arm", default="BASE")
    p.add_argument("--arms", default="BATCHONLY,TUNED")
    p.add_argument("--sessions", default="6,8,10")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    blocks = [int(x) for x in args.blocks.split(",")]
    arms = args.arms.split(",")
    base_arm = args.baseline_arm
    out = []

    for n in (int(x) for x in args.sessions.split(",")):
        base_meas = aggregate(args.run, base_arm, n, blocks)
        base_sim = {}
        for dummy in (False, True):
            res = [sim_cell(args.run, base_arm, n, b, dummy) for b in blocks]
            base_sim[dummy] = {
                "busy_s": sum(r.busy_s for r in res),
                "reuse_hits": sum(r.reuse_hits for r in res),
                "resume": sum(r.resume_requests for r in res),
                "evictions": sum(len(r.evictions) for r in res),
            }
        mh, mt = measured_reuse(args.run, base_arm, n, blocks)
        row = {"N": n, "blocks": blocks, "baseline_arm": base_arm,
               "baseline_sim": {str(k): v for k, v in base_sim.items()},
               "baseline_measured_reuse": [mh, mt], "arms": []}
        print(f"\nN={n}  {base_arm} sim busy off {base_sim[False]['busy_s']:.3f} s / "
              f"on {base_sim[True]['busy_s']:.3f} s   재사용 sim "
              f"{base_sim[False]['reuse_hits']}→{base_sim[True]['reuse_hits']} "
              f"(실측 {mh}/{mt})")
        for arm in arms:
            meas = aggregate(args.run, arm, n, blocks)
            meas_ratio = meas["a_prime_s"] / base_meas["a_prime_s"]
            cell = {"arm": arm, "measured_a_prime_ratio": meas_ratio,
                    "measured_reuse": list(measured_reuse(args.run, arm, n, blocks)),
                    "modes": {}}
            for dummy in (False, True):
                res = [sim_cell(args.run, arm, n, b, dummy) for b in blocks]
                tot = sum(r.busy_s for r in res)
                ratio = tot / base_sim[dummy]["busy_s"]
                cell["modes"]["on" if dummy else "off"] = {
                    "sim_busy_s": tot, "sim_ratio": ratio,
                    "e_c": ratio - meas_ratio, "abs_e_c": abs(ratio - meas_ratio),
                    "reuse_hits": sum(r.reuse_hits for r in res),
                    "resume": sum(r.resume_requests for r in res),
                    "evictions": sum(len(r.evictions) for r in res),
                }
            off, on = cell["modes"]["off"], cell["modes"]["on"]
            cell["ratio_on_minus_off"] = on["sim_ratio"] - off["sim_ratio"]
            cell["abs_e_c_on_minus_off"] = on["abs_e_c"] - off["abs_e_c"]
            row["arms"].append(cell)
            print(f"      {arm:<10} 실측 {meas_ratio:.4f}  "
                  f"off {off['sim_ratio']:.4f} (|e_c| {off['abs_e_c']:.4f})  "
                  f"on {on['sim_ratio']:.4f} (|e_c| {on['abs_e_c']:.4f})  "
                  f"Δ비 {cell['ratio_on_minus_off']:+.4f}  "
                  f"재사용 {off['reuse_hits']}→{on['reuse_hits']} of {on['resume']}  "
                  f"회수 {off['evictions']}→{on['evictions']}")
        out.append(row)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
