#!/usr/bin/env python3
"""Price the simulator's re-arrival recomputation against pinned arrivals.

The simulator does not take a session's return times as given. A turn finishes
when the configuration under test finishes it, the tool gap starts there, and
the next turn arrives at ``finish + gap`` -- so a configuration that drains a
batch faster also refills it sooner, and the arrival series is an output rather
than an input. That design costs something to carry, and this file measures
what it buys.

``--fix-arrivals <RUN>`` pins every re-arrival to the time it was observed at
in the baseline arm of ``RUN``, which switches the feedback off: each arm is
then scored against one fixed arrival series. Both modes are run and their
prediction errors against the same measured ratios are put side by side.

This is not ``ablation.py``. That file swaps a measured *substrate* semantic
for a different stack's documented one and asks what the substrate is
responsible for. Here the substrate is untouched and the question is about the
simulator's own construction: whether recomputing arrivals earns its keep.
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


def observed_arrivals(run: Path, label: str) -> dict[tuple[int, int], float]:
    """``(session_index, turn) -> arrival`` from a measured run's client log.

    Times are shifted so that the earliest opening turn sits at zero, which is
    where the simulator starts its clock. Only re-arrivals are returned: turn 0
    is not one, and the simulator does not accept it.
    """
    rows = [json.loads(l) for l in
            (run / "probe" / f"requests.{label}.jsonl").read_text().splitlines()
            if l.strip()]
    firsts = [r["sent_s"] for r in rows if r["turn"] == 0 and r.get("sent_s") is not None]
    if not firsts:
        raise SystemExit(f"{label}: no opening turn with a send time")
    t0 = min(firsts)
    return {(r["session_index"], r["turn"]): r["sent_s"] - t0
            for r in rows if r["turn"] > 0 and r.get("sent_s") is not None}


def sim_cell(run: Path, arm: str, n: int, blk: int,
             fixed: dict[tuple[int, int], float] | None) -> float:
    """Device time the simulator predicts for one cell, in one mode."""
    label = f"{arm}.n{n}.b{blk}"
    meta = json.loads((run / "probe" / f"meta.{label}.json").read_text())
    sessions = sessions_from_plan(meta["plan"], meta["block_id"])
    cfg = SimConfig(max_running_requests=ARMS[arm][1], fixed_arrivals=fixed)
    return simulate(descriptor_for_arm(arm), sessions, cfg).busy_s


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--fix-arrivals", type=Path, required=True,
                   help="run whose baseline-arm arrivals pin the fixed model")
    p.add_argument("--baseline-arm", default="BASE")
    p.add_argument("--arms", default="BATCHONLY,TUNED")
    p.add_argument("--sessions", default="6,8")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    blocks = [int(x) for x in args.blocks.split(",")]
    arms = args.arms.split(",")
    base_arm = args.baseline_arm
    out = []

    for n in (int(x) for x in args.sessions.split(",")):
        # One pinned series per block, taken from the baseline arm: every arm
        # is then scored against the arrivals the baseline actually produced.
        pinned = {blk: observed_arrivals(args.fix_arrivals, f"{base_arm}.n{n}.b{blk}")
                  for blk in blocks}
        modes = {"full": {blk: None for blk in blocks}, "fixed": pinned}
        base_meas = aggregate(args.run, base_arm, n, blocks)
        base_sim = {m: sum(sim_cell(args.run, base_arm, n, b, f[b]) for b in blocks)
                    for m, f in modes.items()}
        row = {"N": n, "blocks": blocks, "baseline_arm": base_arm,
               "baseline_measured_a_prime_s": base_meas["a_prime_s"],
               "baseline_sim_busy_s": base_sim, "arms": []}
        print(f"\nN={n}  {base_arm} sim busy: "
              f"전체 {base_sim['full']:.3f} s / 고정 {base_sim['fixed']:.3f} s, "
              f"실측 A′ {base_meas['a_prime_s']:.3f} s")
        for arm in arms:
            meas = aggregate(args.run, arm, n, blocks)
            meas_ratio = meas["a_prime_s"] / base_meas["a_prime_s"]
            cell = {"arm": arm, "measured_a_prime_ratio": meas_ratio, "modes": {}}
            for mode, f in modes.items():
                tot = sum(sim_cell(args.run, arm, n, b, f[b]) for b in blocks)
                ratio = tot / base_sim[mode]
                cell["modes"][mode] = {
                    "sim_busy_s": tot, "sim_ratio": ratio,
                    "e_c": ratio - meas_ratio, "abs_e_c": abs(ratio - meas_ratio),
                }
            fu, fx = cell["modes"]["full"], cell["modes"]["fixed"]
            cell["abs_e_c_fixed_minus_full"] = fx["abs_e_c"] - fu["abs_e_c"]
            row["arms"].append(cell)
            print(f"      {arm:<10} 실측 {meas_ratio:.4f}  "
                  f"전체 {fu['sim_ratio']:.4f} (|e_c| {fu['abs_e_c']:.4f})  "
                  f"고정 {fx['sim_ratio']:.4f} (|e_c| {fx['abs_e_c']:.4f})  "
                  f"차 {cell['abs_e_c_fixed_minus_full']:+.4f}")
        out.append(row)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
