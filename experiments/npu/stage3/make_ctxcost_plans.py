#!/usr/bin/env python3
"""Controlled decode-only load at a fixed context length (TASK97, directive 10
work A, CTXCOST_DESIGN.md). Not a workload of interest.

``ctx-n{n}-L{L}``: ``n`` slots, every session one turn of an ``L``-token prompt
and exactly 256 generated tokens, renewed at once. All slots start together
(``cycle_s`` 0.01 -> stagger 0.01/n s) and every request generates the same
number of tokens, so the slots run in lock step on purpose: the ``n`` prefills
of a renewal run back to back and then ``n`` requests decode together for 255
steps with contexts ``L + k`` (k = 1..255). Decode steps are what is measured;
the lock step keeps the running count at exactly ``n`` (TASK92's lock-step
defect concerned prefill sampling, which this load does not measure).

Sessions per slot: 40. The shortest session (n = 1, L = 512) lasts about
0.13 s + 255 x 10 ms = 2.7 s, so 40 sessions cover 108 s > warm-up (two
completions per slot) + 40 s window; ``check_exhaustion`` asserts the margin
for every plan from TASK13/TASK22 costs (TASK92's plan-exhaustion defect).
Seeds ``20262000 + 10 n + i_L``.
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
import mt_predict  # noqa: E402,F401  (puts src/ and substrate/ on sys.path)
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

NS = (1, 2, 4, 8, 16)
LS = (512, 1500, 3000)
GEN = 256
SESSIONS = 40
EVAL_S = 40.0


def check_exhaustion(n: int, L: int) -> float:
    """Seconds of load the plan holds at the fastest plausible pace, over
    the seconds it must cover (warm-up of two sessions + window), x 1.5."""
    step = 0.0095                                   # below every measured decode step
    session = n * D.prefill_cost_model.prefill_s(L) * 0.9 + (GEN - 1) * step
    need = 1.5 * (2 * session + EVAL_S)
    have = SESSIONS * session
    assert have >= need, (n, L, have, need)
    return have / need


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "plans" / "ctxcost")
    a = ap.parse_args()
    index = []
    for n in NS:
        for i, L in enumerate(LS):
            pid = f"ctx-n{n}-L{L}"
            seed = 20262000 + 10 * n + i
            margin = check_exhaustion(n, L)
            plan = MP.build(n=n, seed=seed, plan_id=pid, cycle_s=0.01, turns=1, sessions_per_slot=SESSIONS,
                            first=f"fixed:{L}", later="fixed:8", generation=f"fixed:{GEN}", gap="uniform:0:0")
            path = a.out_dir / f"{pid}.json"
            content = MP.write(plan, path)
            index.append({"plan_id": pid, "n": n, "L": L, "seed": seed, "sessions_per_slot": SESSIONS,
                          "generation": GEN, "exhaustion_margin": round(margin, 2),
                          "content_sha256": content, "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "max_context": MP.max_context_tokens(plan)})
            print(pid, seed, round(margin, 2), content[:12], index[-1]["max_context"])
    (a.out_dir / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
