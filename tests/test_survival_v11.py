#!/usr/bin/env python3
"""Model v1.1 self-check (TASK85): the load chain against a Monte Carlo of the
same assumptions, entry by entry. Runs without pytest:

    env -u PYTHONPATH python3 tests/test_survival_v11.py

Cases cover a queue (N > M), no queue (N < M), short and long idle times and
both completion orders. Tolerance 0.02 (MC standard error about 0.008 at
4,000 cycles). Also: the gap-law fit preserves the sample mean, and v1.1
refuses a release-ordered LRU substrate.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

import mc_survival_v11 as MC  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival_v11 as V  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        FAILS.append(label)


def main() -> int:
    law = V.GapLaw(0.128, (0.585, 0.415), (0.066, 9.87))
    g_steps, t_step = 144.8, 0.0125
    c = lambda r: 0.6 / (g_steps * t_step)  # noqa: E731
    for order in ("random", "admission"):
        for n, m_run, cap, sa, si in ((12, 8, 8, 3.0, 1.0), (12, 8, 8, 3.0, 5.0),
                                      (6, 8, 8, 2.0, 3.0), (12, 16, 16, 3.0, 3.0)):
            w = O.ClosedWorkload(sessions=n, decode_steps_per_request=g_steps,
                                 think_mean_s=law.mean, prefill_mean_s=0.0, max_running=m_run)
            others = O.others_in_engine_at_arrival(w, lambda r: t_step / 0.6)
            inp = V.LoadChainInputs(sessions=n, max_running=m_run, capacity=cap, gap=law,
                                    completion_rate=c, others_at_arrival=others, s_active=sa,
                                    completion_order=order)
            chain = V.survival_probability_v11(inp, [(si, 1.0)])
            mc = MC.simulate(n=n, m_run=m_run, cap=cap, gap=law, c=c, s_active=sa, s_idle=si,
                             cycles=4000, seed=7, order=order)
            check(abs(chain - mc) <= 0.02,
                  f"{order:9s} N={n} M={m_run} C={cap} s_act={sa} s_idle={si}: "
                  f"chain {chain:.3f} vs MC {mc:.3f}")
    gaps = [0.0] * 13 + [0.01 * k for k in range(1, 60)] + [5.0 * k for k in range(1, 12)]
    fit = V.fit_gap_law(gaps, 3)
    check(abs(fit.mean - sum(gaps) / len(gaps)) < 1e-6, f"gap-law fit keeps the mean ({fit.mean:.4f})")
    sys.path.insert(0, str(REPO / "tests"))
    from test_descriptor_v2 import gpu_test_descriptor
    try:
        V.check_substrate(gpu_test_descriptor())
        check(False, "v1.1 refuses release-ordered LRU")
    except NotImplementedError:
        check(True, "v1.1 refuses release-ordered LRU")
    print("FAIL" if FAILS else "PASS", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
