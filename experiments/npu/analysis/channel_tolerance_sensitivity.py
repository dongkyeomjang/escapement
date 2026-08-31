#!/usr/bin/env python3
"""Post-hoc sensitivity of every two-channel verdict to the tolerance floor.

The channel-agreement requirement gates every device-time judgement in this
programme. Its current form is

    tau(N) = max(FLOOR, r_BASE / B_BASE),    FLOOR = 0.02

and the second term is derived: TASK36 shows that a residual lying anywhere in
``[0, r_BASE]`` cannot push the channel gap past ``r_BASE / B_BASE``. The
0.02 floor is not derived. It is a convention fixed before any of these
measurements, and nothing in the substrate picks that number.

This script recomputes -- from the stored run artefacts, not from the task
tables -- what every gated cell's verdict would have been had the floor been
0.005, 0.01, 0.02, 0.03 or 0.05 instead. The derived term is taken from the
data as it stands and is never varied.

Two verdict forms are reported per cell, because the four measurements did not
all use the same one:

  * ``fixed``  -- ``gap <= FLOOR``, no residual term. This is literally what
    TASK34 and TASK35 preregistered; the tau form postdates them.
  * ``tau``    -- ``gap <= max(FLOOR, r_BASE / B_BASE)``. This is what TASK36
    and TASK40 preregistered, and what applying today's criterion to the older
    runs would give.

This is a sensitivity check, not a re-adjudication. The verdicts recorded in
TASK34, TASK35, TASK36 and TASK40 stand exactly as they are; nothing computed
here changes any of them, and the script draws no conclusion from what it
computes.
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

import batch_curve  # noqa: E402
import config_device  # noqa: E402
from config_device import channel_a_prime, channel_b  # noqa: E402
from config_search import descriptor_for  # noqa: E402

#: The floors to sweep. 0.02 is the original; it is kept in the list so that
#: the sweep reproduces the original verdict rather than assuming it.
FLOORS = (0.005, 0.01, 0.02, 0.03, 0.05)
ORIGINAL_FLOOR = 0.02

#: arm label -> (compiled bucket set, compile batch_size), per measurement.
#: Copied from config_device.ARMS and batch_curve.ARMS; asserted equal to them
#: at import time below so this file cannot drift from the judged code.
CONFIG_ARMS = {
    "BASE": ((1, 2, 4, 8), 8),
    "BATCHONLY": ((1, 2, 4, 8, 16), 16),
    "TUNED": ((1, 4, 6, 8, 10, 16), 16),
}
BATCH_ARMS = {
    "B8": ((1, 2, 4, 8), 8),
    "B16": ((1, 4, 6, 8, 10, 16), 16),
    "B24": ((1, 4, 6, 8, 10, 24), 24),
    "B32": ((1, 4, 6, 8, 10, 32), 32),
}

assert CONFIG_ARMS == config_device.ARMS, "arm 정의가 config_device.py와 어긋난다"
assert BATCH_ARMS == batch_curve.ARMS, "arm 정의가 batch_curve.py와 어긋난다"
assert config_device.CHANNEL_FLOOR == ORIGINAL_FLOOR, "원본 기본값이 코드와 어긋난다"

RUNS = Path("results/npu/stage2")

#: The four gated measurements. ``channel`` names which channel A definition
#: that measurement preregistered: TASK34 registered a decode-only channel A
#: (its documented defect), the other three registered A' = decode + prefill.
#: ``criterion`` names the form the measurement actually applied.
MEASUREMENTS = [
    {
        "task": "TASK34", "run": RUNS / "20260823-170201-compile-config",
        "arms": CONFIG_ARMS, "baseline": "BASE", "compare": ["TUNED"],
        "sessions": [6, 8, 10], "blocks": [0, 1, 2],
        "channel": "decode", "criterion": "fixed",
        "confirm": [6, 8],
    },
    {
        "task": "TASK35", "run": RUNS / "20260823-183505-final-confirm",
        "arms": CONFIG_ARMS, "baseline": "BASE", "compare": ["BATCHONLY", "TUNED"],
        "sessions": [6, 8, 10], "blocks": [0, 1, 2],
        "channel": "a_prime", "criterion": "fixed",
        "confirm": [6, 8],
    },
    {
        "task": "TASK36", "run": RUNS / "20260824-160028-n6-reconfirm",
        "arms": CONFIG_ARMS, "baseline": "BASE", "compare": ["BATCHONLY", "TUNED"],
        "sessions": [6], "blocks": [0, 1, 2],
        "channel": "a_prime", "criterion": "tau",
        "confirm": [6],
    },
    {
        "task": "TASK40", "run": RUNS / "20260824-222453-batch-saturation",
        "arms": BATCH_ARMS, "baseline": "B8", "compare": ["B16", "B24", "B32"],
        "sessions": [6, 8, 10], "blocks": [0, 1, 2],
        "channel": "a_prime", "criterion": "tau",
        "confirm": [6, 8],
    },
]

#: (task, N, arm) -> (A ratio, B ratio) as printed in the task documents.
#: Recomputation is checked against these so a silent path or parsing error
#: cannot masquerade as a result. Tolerance is one unit in the last recorded
#: digit.
EXPECTED = {
    ("TASK34", 6, "TUNED"): (0.9644, 0.9423),
    ("TASK34", 8, "TUNED"): (1.0042, 0.9134),
    ("TASK34", 10, "TUNED"): (0.9439, 0.8739),
    ("TASK35", 6, "BATCHONLY"): (0.9793, 0.9588),
    ("TASK35", 6, "TUNED"): (0.9660, 0.9424),
    ("TASK35", 8, "BATCHONLY"): (0.9175, 0.9183),
    ("TASK35", 8, "TUNED"): (0.9028, 0.8993),
    ("TASK35", 10, "BATCHONLY"): (0.9552, 0.9551),
    ("TASK35", 10, "TUNED"): (0.9264, 0.9287),
    ("TASK36", 6, "BATCHONLY"): (0.9941, 0.9940),
    ("TASK36", 6, "TUNED"): (0.9789, 0.9726),
    ("TASK40", 6, "B16"): (0.9659, 0.9625),
    ("TASK40", 6, "B24"): (0.9660, 0.9693),
    ("TASK40", 6, "B32"): (0.9663, 0.9595),
    ("TASK40", 8, "B16"): (0.9151, 0.9146),
    ("TASK40", 8, "B24"): (0.9151, 0.9146),
    ("TASK40", 8, "B32"): (0.9161, 0.9158),
    ("TASK40", 10, "B16"): (0.8601, 0.8599),
    ("TASK40", 10, "B24"): (0.8480, 0.8464),
    ("TASK40", 10, "B32"): (0.8482, 0.8460),
}

#: (task, N) -> r_BASE/B_BASE as printed, where the document prints it.
EXPECTED_SHARE = {
    ("TASK36", 6): 0.038,
    ("TASK40", 6): 0.036,
    ("TASK40", 8): 0.040,
    ("TASK40", 10): 0.046,
}


def descriptor(arms: dict, arm: str):
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    buckets, batch = arms[arm]
    return descriptor_for(D, buckets, batch)


def arm_totals(run: Path, arms: dict, arm: str, n: int, blocks: list[int],
               channel: str) -> tuple[float, float]:
    """(channel A total, channel B total) summed over the blocks of one cell."""
    d = descriptor(arms, arm)
    a_tot = b_tot = 0.0
    for blk in blocks:
        label = f"{arm}.n{n}.b{blk}"
        util = json.loads((run / f"util.{label}.json").read_text())
        if not util.get("valid", True):
            raise SystemExit(f"INVALID {label}: {util['invariant_violations']}")
        rows = [json.loads(l) for l in
                (run / "probe" / f"requests.{label}.jsonl").read_text().splitlines()
                if l.strip()]
        total, decode, _prefill = channel_a_prime(util, rows, d)
        a_tot += decode if channel == "decode" else total
        b_tot += channel_b(rows)
    return a_tot, b_tot


def collect() -> list[dict]:
    cells = []
    for m in MEASUREMENTS:
        run = m["run"]
        if not run.exists():
            raise SystemExit(f"run not found: {run}")
        for n in m["sessions"]:
            a_base, b_base = arm_totals(run, m["arms"], m["baseline"], n,
                                        m["blocks"], m["channel"])
            share = (b_base - a_base) / b_base
            for arm in m["compare"]:
                a, b = arm_totals(run, m["arms"], arm, n, m["blocks"], m["channel"])
                ra, rb = a / a_base, b / b_base
                cells.append({
                    "task": m["task"], "N": n, "arm": arm,
                    "channel": m["channel"], "criterion": m["criterion"],
                    "segment": "확증" if n in m["confirm"] else "탐색",
                    "a_ratio": ra, "b_ratio": rb, "gap": abs(ra - rb),
                    "residual_s": b_base - a_base, "b_base_s": b_base,
                    "residual_share": share,
                })
    return cells


def check(cells: list[dict]) -> int:
    """Cross-check the recomputation against the numbers in the task documents."""
    bad = 0
    for c in cells:
        key = (c["task"], c["N"], c["arm"])
        if key not in EXPECTED:
            print(f"  경고: {key} 대조값 없음")
            bad += 1
            continue
        ea, eb = EXPECTED[key]
        da, db = abs(c["a_ratio"] - ea), abs(c["b_ratio"] - eb)
        ok = da <= 5e-4 and db <= 5e-4
        bad += 0 if ok else 1
        print(f"  {'OK  ' if ok else 'DIFF'} {c['task']} N={c['N']:<3}{c['arm']:<10}"
              f" A {c['a_ratio']:.4f} vs {ea:.4f} (Δ{da:.4f})"
              f"   B {c['b_ratio']:.4f} vs {eb:.4f} (Δ{db:.4f})")
    seen = set()
    for c in cells:
        key = (c["task"], c["N"])
        if key in EXPECTED_SHARE and key not in seen:
            seen.add(key)
            e = EXPECTED_SHARE[key]
            d = abs(c["residual_share"] - e)
            ok = d <= 1e-3
            bad += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'DIFF'} {c['task']} N={c['N']} "
                  f"r_BASE/B_BASE {c['residual_share']:.4f} vs {e:.3f} (Δ{d:.4f})")
    return bad


def verdicts(cells: list[dict]) -> None:
    for c in cells:
        c["verdict"] = {}
        for f in FLOORS:
            c["verdict"][f] = {
                "fixed": c["gap"] <= f,
                "tau": c["gap"] <= max(f, c["residual_share"]),
                "tau_value": max(f, c["residual_share"]),
            }
        # The verdict the measurement actually recorded: its own criterion at
        # the original floor.
        c["original"] = c["verdict"][ORIGINAL_FLOOR][c["criterion"]]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    import os
    os.chdir(args.repo)

    print("=" * 78)
    print("§0  재현 대조 — 저장 artifact에서 다시 계산한 값 대 TASK 문서 기록값")
    print("=" * 78)
    cells = collect()
    bad = check(cells)
    if bad:
        raise SystemExit(f"\n대조 실패 {bad}건 — 계산을 신뢰할 수 없다.")
    print(f"\n  대조 {len(cells)}칸 + 잔차비 {len(EXPECTED_SHARE)}건 전부 일치.")

    verdicts(cells)

    print()
    print("=" * 78)
    print("§1  셀별 채널 값과 당시 적용된 허용차")
    print("=" * 78)
    print(f"{'TASK':<7}{'N':>3} {'arm':<10}{'구간':<5}{'채널A':<10}"
          f"{'A비':>8}{'B비':>8}{'차':>8}{'r/B':>8}{'적용허용차':>10}  {'기준':<9}{'원판정':>6}")
    for c in cells:
        applied = (ORIGINAL_FLOOR if c["criterion"] == "fixed"
                   else c["verdict"][ORIGINAL_FLOOR]["tau_value"])
        print(f"{c['task']:<7}{c['N']:>3} {c['arm']:<10}{c['segment']:<5}"
              f"{c['channel']:<10}{c['a_ratio']:>8.4f}{c['b_ratio']:>8.4f}"
              f"{c['gap']:>8.4f}{c['residual_share']:>8.4f}{applied:>10.4f}"
              f"  {c['criterion']:<9}{'통과' if c['original'] else '보류':>6}")

    print()
    print("  참고(사실): TASK34의 r/B가 0.26-0.34로 다른 셋(0.037-0.061)과 자릿수가"
          " 다른 것은")
    print("  그 채널 A가 decode step만 세어 prefill 시간 전부가 잔차에 들어가기"
          " 때문이다.")

    print()
    print("=" * 78)
    print("§2  기본값 민감도 — 전수 (통과 / 보류)")
    print("=" * 78)
    for form, title in (("fixed", "고정 밴드 `차 ≤ 기본값` (TASK34·35가 실제 등록한 형태)"),
                        ("tau", "τ 형태 `차 ≤ max(기본값, r_BASE/B_BASE)` (TASK36·40이 등록한 형태)")):
        print(f"\n  [{form}] {title}")
        print(f"    {'기본값':>8}{'통과':>7}{'보류':>7}   보류 셀")
        for f in FLOORS:
            held = [c for c in cells if not c["verdict"][f][form]]
            passed = len(cells) - len(held)
            names = ", ".join(f"{c['task']}·N{c['N']}·{c['arm']}" for c in held) or "없음"
            mark = "  ← 원본" if f == ORIGINAL_FLOOR else ""
            print(f"    {f:>8.3f}{passed:>7}{len(held):>7}   {names}{mark}")

    print()
    print("  [τ 형태에서 기본값이 실제로 구속하는 셀 수] "
          "기본값 > r_BASE/B_BASE 인 셀만 기본값이 허용차를 정한다")
    print(f"    {'기본값':>8}{'구속':>7}{'미구속':>8}")
    for f in FLOORS:
        binding = sum(1 for c in cells if f > c["residual_share"])
        print(f"    {f:>8.3f}{binding:>7}{len(cells) - binding:>8}")

    print()
    print("=" * 78)
    print("§3  판정이 뒤집히는 셀 — 기본값 0.02 대비")
    print("=" * 78)
    for form in ("fixed", "tau"):
        print(f"\n  [{form}]")
        any_flip = False
        for f in FLOORS:
            if f == ORIGINAL_FLOOR:
                continue
            for c in cells:
                base = c["verdict"][ORIGINAL_FLOOR][form]
                now = c["verdict"][f][form]
                if base != now:
                    any_flip = True
                    tol = f if form == "fixed" else c["verdict"][f]["tau_value"]
                    print(f"    기본값 {f:.3f}: {c['task']}·N{c['N']}·{c['arm']} "
                          f"{'통과→보류' if base else '보류→통과'} "
                          f"(차 {c['gap']:.4f}, 허용차 {tol:.4f})")
        if not any_flip:
            print("    없음 — 0.005~0.05 전 범위에서 20칸 모두 판정이 같다.")

    print()
    print("=" * 78)
    print("§4  원본 기준으로 보류였던 셀이 통과로 바뀌는 기본값")
    print("=" * 78)
    held = [c for c in cells if not c["original"]]
    if not held:
        print("  원본 보류 셀 없음.")
    for c in held:
        row = []
        for f in FLOORS:
            v = c["verdict"][f][c["criterion"]]
            row.append(f"{f:.3f}:{'통과' if v else '보류'}")
        first = next((f for f in FLOORS
                      if c["verdict"][f][c["criterion"]]), None)
        print(f"  {c['task']}·N{c['N']}·{c['arm']}  차 {c['gap']:.4f}  "
              f"기준 {c['criterion']}  " + "  ".join(row))
        print(f"      → 통과로 바뀌는 최소 기본값: "
              f"{f'{first:.3f}' if first is not None else '이 범위에 없음'}")

    print()
    print("=" * 78)
    print("§5  여유 = 허용차 − 차 (원본 기본값 0.02, 각 셀의 자기 기준)")
    print("=" * 78)
    marg = sorted(cells, key=lambda c: (c["verdict"][ORIGINAL_FLOOR]["tau_value"]
                                        if c["criterion"] == "tau" else ORIGINAL_FLOOR)
                  - c["gap"])
    for c in marg:
        tol = (c["verdict"][ORIGINAL_FLOOR]["tau_value"]
               if c["criterion"] == "tau" else ORIGINAL_FLOOR)
        print(f"  {c['task']}·N{c['N']}·{c['arm']:<10} 허용차 {tol:.4f} − 차 "
              f"{c['gap']:.4f} = {tol - c['gap']:+.4f}")

    if args.output:
        payload = {
            "floors": list(FLOORS), "original_floor": ORIGINAL_FLOOR,
            "cells": [{k: v for k, v in c.items() if k != "verdict"} |
                      {"verdict": {str(f): c["verdict"][f] for f in FLOORS}}
                      for c in cells],
        }
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"\n산출: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
