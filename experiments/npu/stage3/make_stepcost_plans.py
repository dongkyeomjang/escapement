#!/usr/bin/env python3
"""Controlled-load plans for the operational step-cost measurement (TASK92,
directive 08 work B; design in STEPCOST_OP_DESIGN.md).

Not a workload of interest: a load chosen so the engine runs a known number of
decoders, through the same runner, server arguments and streaming path as the
multi-turn experiment.

* decode plans ``op-decode-n{n}``: ``n`` slots, every session one turn of a
  128-token prompt and 512 generated tokens, renewed at once -- ``n`` requests
  decode almost all the time; the 128-token prefill of a renewal is rare.
* prefill plan ``op-prefill``: 4 slots, one-turn sessions, prompt U(64, 4096),
  32 generated tokens -- an exclusive prefill of a known size between almost
  every few decode steps.

``cycle_s`` = 1 s (stagger 1/n s); seeds ``20261800 + n`` and ``20261899``.

Supplement (``--supplement``, TASK92 amendment): with 10 sessions per slot the
n = 1 and n = 2 plans ran out before the evaluation window ended (one fast
decoder finishes 10 x 512 tokens in about 55 s). ``op-decode-n{1,2}-s30`` are
the same load with 30 sessions per slot, seeds ``20261820 + n``; listed in
``INDEX_SUPP.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_plan as MP  # noqa: E402

NS = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "stepcost")
    ap.add_argument("--supplement", action="store_true")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    if a.supplement:
        specs = [(f"op-decode-n{n}-s30", n, 20261820 + n, "fixed:128", "fixed:512", 30) for n in (1, 2)]
    else:
        specs = [(f"op-decode-n{n}", n, 20261800 + n, "fixed:128", "fixed:512", 10) for n in NS]
        specs.append(("op-prefill", 4, 20261899, "uniform:64:4096", "fixed:32", 160))
    for pid, n, seed, first, gen, sessions in specs:
        plan = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=1.0, turns=1, sessions_per_slot=sessions,
                        first=first, later="fixed:8", generation=gen, gap="uniform:0:0")
        path = a.out_dir / f"{pid}.json"
        content = MP.write(plan, path)
        index.append({"plan_id": pid, "n": n, "seed": seed, "first": first, "generation": gen,
                      "sessions_per_slot": sessions, "content_sha256": content,
                      "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "max_context": MP.max_context_tokens(plan)})
        print(pid, n, content[:12], index[-1]["max_context"])
    (a.out_dir / ("INDEX_SUPP.json" if a.supplement else "INDEX.json")).write_text(
        json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
