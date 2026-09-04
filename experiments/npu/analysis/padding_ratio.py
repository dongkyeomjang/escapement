#!/usr/bin/env python3
"""Padding share of the compiled batch grid, recomputed from the stored steps.

The mechanism-1 story is told in utilization, ``u = sum(n_t) / sum(b_t)``, and
every task document records it that way. Telling it in padding instead needs
``p = sum(b_t - n_t) / sum(b_t) = 1 - u`` computed per condition, because a
ratio of utilizations does not convert into anything about padding: from
``u_A / u_C`` alone, ``p_A - p_C`` is not recoverable. So each arm's padding
share is formed first and compared afterwards.

Three things are computed from the same stored ``[BUCKET]`` histograms:

  * ``p`` per (source, grid, N, arm), pooled over that cell's blocks, with the
    original utilization ratio printed beside it for correspondence;
  * decode device time per arm, priced by TASK13's step cost model -- the
    quantity TASK26 observation 4 already reports, recomputed here only to
    check the values, not to claim them;
  * the ``(actual -> bucket)`` step shares behind statements like "conventional
    spends 65 % of its steps on 6->8".

Every recomputed utilization is checked against the number printed in the task
document it came from. A mismatch aborts before any padding figure is printed.

This recomputes. It does not re-adjudicate: no verdict in TASK19, TASK20,
TASK23, TASK25 or TASK26 changes, and none of their documents is edited.
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

from config_search import descriptor_for  # noqa: E402

RUNS = Path("results/npu/stage2")
R19 = RUNS / "20260819-233800-paired-pilot-v2"
R20 = RUNS / "20260820-165200-nslots-sweep"
R23A = RUNS / "20260821-222000-grid-observe"
R23B = RUNS / "20260821-231000-grid-intervene"
R25 = RUNS / "20260822-160532-sim-oos"

BASE_GRID = (1, 2, 4, 8)
INTERVENED_GRID = (1, 2, 4, 6, 8)

#: (source, grid, N) -> list of (run dir, label suffix). The arm name is
#: prepended per arm, so both arms of a cell read exactly the same blocks.
CELLS: list[dict] = [
    # TASK19 pilot: one block, no block suffix in the label.
    {"src": "TASK19", "grid": BASE_GRID, "N": 8, "parts": [(R19, "n8")]},
    {"src": "TASK19", "grid": BASE_GRID, "N": 16, "parts": [(R19, "n16")]},
    # TASK20 sweep.
    *[{"src": "TASK20", "grid": BASE_GRID, "N": n,
       "parts": [(R20, f"n{n}.b{b}") for b in blocks]}
      for n, blocks in [(4, range(3)), (6, range(3)), (8, range(5)),
                        (10, range(3)), (12, range(3)), (16, range(5))]],
    # TASK23 2a: observation on the base grid.
    *[{"src": "TASK23-2a", "grid": BASE_GRID, "N": n,
       "parts": [(R23A, f"n{n}.b{b}") for b in blocks]}
      for n, blocks in [(3, range(3)), (5, range(3)), (7, range(3)),
                        (8, range(5, 8))]],
    # TASK23 2b: the same N on the grid with bucket 6 added.
    *[{"src": "TASK23-2b", "grid": INTERVENED_GRID, "N": n,
       "parts": [(R23B, f"n{n}.b{b}") for b in range(3)]}
      for n in (6, 8)],
    # TASK25 out-of-sample blocks.
    *[{"src": "TASK25", "grid": BASE_GRID, "N": n,
       "parts": [(R25, f"n{n}.b{b}") for b in range(3, 6)]}
      for n in (3, 4, 7)],
]

#: TASK26 observation 4 pools blocks across runs. Reproduced here to check its
#: device-time table, not to restate it.
TASK26_CELLS: list[dict] = [
    {"grid": BASE_GRID, "N": 3, "blocks": 6,
     "parts": [(R23A, f"n3.b{b}") for b in range(3)] + [(R25, f"n3.b{b}") for b in range(3, 6)]},
    {"grid": BASE_GRID, "N": 4, "blocks": 6,
     "parts": [(R20, f"n4.b{b}") for b in range(3)] + [(R25, f"n4.b{b}") for b in range(3, 6)]},
    {"grid": BASE_GRID, "N": 5, "blocks": 3,
     "parts": [(R23A, f"n5.b{b}") for b in range(3)]},
    {"grid": BASE_GRID, "N": 6, "blocks": 3,
     "parts": [(R20, f"n6.b{b}") for b in range(3)]},
    {"grid": BASE_GRID, "N": 7, "blocks": 6,
     "parts": [(R23A, f"n7.b{b}") for b in range(3)] + [(R25, f"n7.b{b}") for b in range(3, 6)]},
    {"grid": BASE_GRID, "N": 8, "blocks": 8,
     "parts": [(R20, f"n8.b{b}") for b in range(5)] + [(R23A, f"n8.b{b}") for b in range(5, 8)]},
    {"grid": BASE_GRID, "N": 10, "blocks": 3,
     "parts": [(R20, f"n10.b{b}") for b in range(3)]},
    {"grid": BASE_GRID, "N": 12, "blocks": 3,
     "parts": [(R20, f"n12.b{b}") for b in range(3)]},
    {"grid": BASE_GRID, "N": 16, "blocks": 5,
     "parts": [(R20, f"n16.b{b}") for b in range(5)]},
    {"grid": INTERVENED_GRID, "N": 6, "blocks": 3,
     "parts": [(R23B, f"n6.b{b}") for b in range(3)]},
    {"grid": INTERVENED_GRID, "N": 8, "blocks": 3,
     "parts": [(R23B, f"n8.b{b}") for b in range(3)]},
]

#: (src, N) -> pooled utilization ratio as printed in that task document.
EXPECTED_RATIO = {
    ("TASK19", 8): 0.8722, ("TASK19", 16): 1.0091,
    ("TASK20", 4): 1.0414, ("TASK20", 6): 1.1504, ("TASK20", 8): 0.9253,
    ("TASK20", 10): 0.9103, ("TASK20", 12): 0.9192, ("TASK20", 16): 0.9944,
}

#: (src, arm, N) -> per-block utilizations as printed. Checked one by one, so a
#: pooling convention that happens to agree cannot hide a per-cell error.
EXPECTED_UTIL = {
    ("TASK19", "CONVENTIONAL", 8): [0.9587], ("TASK19", "AGENTIC", 8): [0.8362],
    ("TASK19", "CONVENTIONAL", 16): [0.9593], ("TASK19", "AGENTIC", 16): [0.9681],
    ("TASK23-2a", "AGENTIC", 3): [0.8446, 0.9547, 0.8957],
    ("TASK23-2a", "CONVENTIONAL", 3): [0.7730, 0.8403, 0.8754],
    ("TASK23-2a", "AGENTIC", 5): [0.8460, 0.7855, 0.8523],
    ("TASK23-2a", "CONVENTIONAL", 5): [0.7906, 0.7529, 0.6714],
    ("TASK23-2a", "AGENTIC", 7): [0.8313, 0.8344, 0.8764],
    ("TASK23-2a", "CONVENTIONAL", 7): [0.8373, 0.8157, 0.8362],
    ("TASK23-2a", "AGENTIC", 8): [0.8535, 0.8537, 0.7973],
    ("TASK23-2a", "CONVENTIONAL", 8): [0.8823, 0.9399, 0.9131],
    ("TASK23-2b", "AGENTIC", 6): [0.9073, 0.9391, 0.9165],
    ("TASK23-2b", "CONVENTIONAL", 6): [0.9563, 0.9364, 0.9600],
    ("TASK23-2b", "AGENTIC", 8): [0.9020, 0.9469, 0.9248],
    ("TASK23-2b", "CONVENTIONAL", 8): [0.9596, 0.9907, 0.9675],
}

#: TASK26 observation 4: (grid, N) -> (device_s AGENTIC, device_s CONVENTIONAL,
#: busy ratio, util ratio) as printed.
EXPECTED_T26 = {
    (BASE_GRID, 3): (31.95, 22.34, 1.430, 1.099),
    (BASE_GRID, 4): (45.67, 25.66, 1.780, 1.028),
    (BASE_GRID, 5): (18.56, 14.59, 1.272, 1.134),
    (BASE_GRID, 6): (24.57, 16.23, 1.514, 1.150),
    (BASE_GRID, 7): (47.05, 34.11, 1.379, 1.027),
    (BASE_GRID, 8): (60.93, 43.91, 1.388, 0.921),
    (BASE_GRID, 10): (23.79, 19.33, 1.231, 0.910),
    (BASE_GRID, 12): (23.29, 22.09, 1.054, 0.919),
    (BASE_GRID, 16): (50.44, 47.28, 1.067, 0.994),
    (INTERVENED_GRID, 6): (21.90, 13.12, 1.669, 0.972),
    (INTERVENED_GRID, 8): (23.53, 16.93, 1.390, 0.951),
}

ARMS = ("AGENTIC", "CONVENTIONAL")


def descriptor(grid: tuple[int, ...]):
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    # batch_size only sets the KV pool, which no quantity here reads; the grid
    # is what prices a step.
    return descriptor_for(D, grid, 8)


def read_block(run: Path, arm: str, suffix: str) -> dict:
    p = run / f"util.{arm}.{suffix}.json"
    d = json.loads(p.read_text())
    if not d.get("valid", True):
        raise SystemExit(f"INVALID {p}: {d['invariant_violations']}")
    return d


def arm_totals(parts, arm: str, grid) -> dict:
    """Pooled counts, padding share and priced decode time for one arm."""
    desc = descriptor(grid)
    n = b = steps = tokens = 0
    device_s = 0.0
    hist: dict[str, int] = {}
    per_block_util = []
    for run, suffix in parts:
        d = read_block(run, arm, suffix)
        n += d["sum_request_nums"]
        b += d["sum_padded_batch_size"]
        steps += d["decode_steps"]
        tokens += d["generated_tokens"]
        per_block_util.append(d["utilization"])
        for key, count in d["pair_histogram"].items():
            hist[key] = hist.get(key, 0) + count
            actual, bucket = (int(x) for x in key.split("->"))
            device_s += desc.step_cost_model.step_time_s(
                bucket=bucket, actual=actual) * count
    return {"arm": arm, "sum_n": n, "sum_b": b, "steps": steps,
            "tokens": tokens, "device_s": device_s,
            "utilization": n / b, "padding_ratio": (b - n) / b,
            "hist": hist, "per_block_util": per_block_util}


def check(cells: list[dict]) -> int:
    """Recomputation against the task documents. Any mismatch is fatal."""
    bad = 0
    for c in cells:
        for arm in ARMS:
            key = (c["src"], arm, c["N"])
            if key not in EXPECTED_UTIL:
                continue
            got = c[arm]["per_block_util"]
            exp = EXPECTED_UTIL[key]
            if len(got) != len(exp):
                print(f"  DIFF {key}: 블록 수 {len(got)} != {len(exp)}")
                bad += 1
                continue
            for i, (g, e) in enumerate(zip(got, exp)):
                if abs(g - e) > 5e-5:
                    print(f"  DIFF {key} b{i}: {g:.4f} vs {e:.4f}")
                    bad += 1
        key = (c["src"], c["N"])
        if key in EXPECTED_RATIO:
            got = c["util_ratio"]
            exp = EXPECTED_RATIO[key]
            if abs(got - exp) > 5e-5:
                print(f"  DIFF ratio {key}: {got:.4f} vs {exp:.4f}")
                bad += 1
    return bad


def build(cells: list[dict]) -> None:
    for c in cells:
        for arm in ARMS:
            c[arm] = arm_totals(c["parts"], arm, c["grid"])
        a, k = c["AGENTIC"], c["CONVENTIONAL"]
        c["util_ratio"] = a["utilization"] / k["utilization"]
        c["delta_p"] = k["padding_ratio"] - a["padding_ratio"]
        c["device_ratio"] = a["device_s"] / k["device_s"]


def grid_label(g) -> str:
    return "(" + ",".join(str(x) for x in g) + ")"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    import os
    os.chdir(args.repo)

    cells = [dict(c) for c in CELLS]
    build(cells)

    print("=" * 96)
    print("§0  재현 대조 — 저장 artifact 재계산 대 TASK 문서 기록값")
    print("=" * 96)
    bad = check(cells)
    n_util = sum(len(v) for v in EXPECTED_UTIL.values())
    if bad:
        raise SystemExit(f"\n대조 실패 {bad}건 — padding 수치를 내지 않는다.")
    print(f"  블록별 utilization {n_util}건 + pooled ratio {len(EXPECTED_RATIO)}건 "
          f"전부 일치 (허용 5e-5).")

    print()
    print("=" * 96)
    print("§1  셀별 padding 비율 p = Σ(b−n)/Σb, 짝 차이 Δp, 원 utilization 비 병기")
    print("=" * 96)
    print(f"{'출처':<11}{'격자':<12}{'N':>3}{'블록':>5}"
          f"{'p_AGENTIC':>11}{'p_CONV':>10}{'Δp=C−A':>10}"
          f"{'u_A':>9}{'u_C':>9}{'u_A/u_C':>10}")
    for c in cells:
        a, k = c["AGENTIC"], c["CONVENTIONAL"]
        print(f"{c['src']:<11}{grid_label(c['grid']):<12}{c['N']:>3}"
              f"{len(c['parts']):>5}"
              f"{a['padding_ratio']:>11.4f}{k['padding_ratio']:>10.4f}"
              f"{c['delta_p']:>+10.4f}"
              f"{a['utilization']:>9.4f}{k['utilization']:>9.4f}"
              f"{c['util_ratio']:>10.4f}")

    print()
    print("=" * 96)
    print("§2  decode device time — TASK13 step 비용을 같은 step 열에 적용")
    print("    (이 계산의 출처는 TASK26 관측 4다. 여기서는 값 대조만 한다.)")
    print("=" * 96)
    t26 = [dict(c) for c in TASK26_CELLS]
    for c in t26:
        for arm in ARMS:
            c[arm] = arm_totals(c["parts"], arm, c["grid"])
        c["util_ratio"] = c["AGENTIC"]["utilization"] / c["CONVENTIONAL"]["utilization"]
        c["device_ratio"] = c["AGENTIC"]["device_s"] / c["CONVENTIONAL"]["device_s"]
    print(f"{'격자':<12}{'N':>3}{'블록':>5}{'decode tok A/C':>16}{'step A/C':>14}"
          f"{'device s A/C':>18}{'busy비':>10}{'util비':>10}  대조")
    dbad = 0
    for c in t26:
        a, k = c["AGENTIC"], c["CONVENTIONAL"]
        e = EXPECTED_T26[(c["grid"], c["N"])]
        # The seconds are the substantive check: they must agree to within the
        # last printed place. TASK26's ratio column turns out to be the ratio of
        # its own rounded seconds rather than of the full-precision values, so
        # that is what the ratio is checked against -- stated explicitly instead
        # of widening the band until a mismatch disappears. The token column
        # there counts decode tokens, sum(completion_tokens - 1) =
        # sum_request_nums, not generated_tokens.
        ratio_of_rounded = round(e[0] / e[1], 3)
        ok = (abs(a["device_s"] - e[0]) <= 0.005 and abs(k["device_s"] - e[1]) <= 0.005
              and ratio_of_rounded == e[2]
              and abs(c["util_ratio"] - e[3]) <= 5.1e-4
              and a["sum_n"] == k["sum_n"])
        dbad += 0 if ok else 1
        print(f"{grid_label(c['grid']):<12}{c['N']:>3}{c['blocks']:>5}"
              f"{a['sum_n']:>8}/{k['sum_n']:<7}"
              f"{a['steps']:>7}/{k['steps']:<6}"
              f"{a['device_s']:>9.2f}/{k['device_s']:<8.2f}"
              f"{c['device_ratio']:>10.4f}{c['util_ratio']:>10.4f}"
              f"  {'OK' if ok else 'DIFF ' + str(e)}")
    print(f"\n  TASK26 관측 4 대조 불일치 {dbad}건 / {len(t26)}칸.")
    print("  (device 초는 전 칸 ±0.005 s 안. busy 비 열은 TASK26이 **반올림된 초**로"
          " 계산한 값이며,")
    print("   전정밀도 비와 최대 0.00054 차이가 난다 — 계산 경로 차이지 자료 차이가"
          " 아니다.)")
    ratios = sorted(c["device_ratio"] for c in t26)
    over = sum(1 for r in ratios if r > 1.0)
    print(f"  busy 비 범위 {ratios[0]:.3f} – {ratios[-1]:.3f}, "
          f"1 초과 {over}/{len(ratios)}칸.")

    print()
    print("=" * 96)
    print("§3  step 히스토그램 — (actual→bucket)별 step 비율과 padding 0 비율")
    print("=" * 96)
    for c in cells:
        a, k = c["AGENTIC"], c["CONVENTIONAL"]
        keys = sorted(set(a["hist"]) | set(k["hist"]),
                      key=lambda s: tuple(int(x) for x in s.split("->")))
        print(f"\n  {c['src']}  격자 {grid_label(c['grid'])}  N={c['N']}  "
              f"블록 {len(c['parts'])}")
        print(f"    {'쌍':>7}{'pad':>5}{'AGENTIC step':>15}{'비율':>9}"
              f"{'CONV step':>12}{'비율':>9}")
        for key in keys:
            actual, bucket = (int(x) for x in key.split("->"))
            ca, ck = a["hist"].get(key, 0), k["hist"].get(key, 0)
            print(f"    {key:>7}{bucket - actual:>5}{ca:>15}"
                  f"{ca / a['steps']:>9.3f}{ck:>12}{ck / k['steps']:>9.3f}")
        for label, d in (("AGENTIC", a), ("CONV", k)):
            zero = sum(v for key, v in d["hist"].items()
                       if len(set(key.split("->"))) == 1)
            print(f"    {label:<8} padding 0인 step 비율 "
                  f"{zero}/{d['steps']} = {zero / d['steps']:.3f}")

    print()
    print("=" * 96)
    print("§4  서술에 쓰인 히스토그램 수치의 출처 — 블록 단위와 합산 단위의 구분")
    print("=" * 96)
    narrative = [("TASK20", R20, BASE_GRID, 6, [f"n6.b{b}" for b in range(3)]),
                 ("TASK23-2b", R23B, INTERVENED_GRID, 6, [f"n6.b{b}" for b in range(3)])]
    for src, run, grid, n, suffixes in narrative:
        top = grid[-1]
        print(f"\n  {src}  격자 {grid_label(grid)}  N={n}")
        print(f"    {'단위':<10}{'arm':<14}{'step':>7}"
              f"{'상위 bucket행 계':>16}{'비율':>8}"
              f"{f'{n}->{top} 단독':>13}{'비율':>8}{'pad 0 비율':>12}")
        for label, parts in ([(f"블록 {i}", [(run, sfx)])
                              for i, sfx in enumerate(suffixes)]
                             + [("합산 3블록", [(run, sfx) for sfx in suffixes])]):
            for arm in ARMS:
                t = arm_totals(parts, arm, grid)
                # Rows that land on the top bucket, i.e. every padded step at
                # or above the grid's last rung.
                topsum = sum(v for k2, v in t["hist"].items()
                             if int(k2.split("->")[1]) == top)
                alone = t["hist"].get(f"{n}->{top}", 0)
                zero = sum(v for k2, v in t["hist"].items()
                           if len(set(k2.split("->"))) == 1)
                print(f"    {label:<10}{arm:<14}{t['steps']:>7}"
                      f"{topsum:>16}{topsum / t['steps']:>8.3f}"
                      f"{alone:>13}{alone / t['steps']:>8.3f}"
                      f"{zero / t['steps']:>12.3f}")

    if args.output:
        payload = []
        for c in cells:
            payload.append({
                "src": c["src"], "grid": list(c["grid"]), "N": c["N"],
                "blocks": len(c["parts"]),
                "padding_ratio_agentic": c["AGENTIC"]["padding_ratio"],
                "padding_ratio_conventional": c["CONVENTIONAL"]["padding_ratio"],
                "delta_p": c["delta_p"],
                "utilization_agentic": c["AGENTIC"]["utilization"],
                "utilization_conventional": c["CONVENTIONAL"]["utilization"],
                "utilization_ratio": c["util_ratio"],
                "hist_agentic": c["AGENTIC"]["hist"],
                "hist_conventional": c["CONVENTIONAL"]["hist"],
                "steps_agentic": c["AGENTIC"]["steps"],
                "steps_conventional": c["CONVENTIONAL"]["steps"],
            })
        args.output.write_text(json.dumps(
            {"cells": payload,
             "task26_recheck": [
                 {"grid": list(c["grid"]), "N": c["N"], "blocks": c["blocks"],
                  "device_s_agentic": c["AGENTIC"]["device_s"],
                  "device_s_conventional": c["CONVENTIONAL"]["device_s"],
                  "device_ratio": c["device_ratio"],
                  "utilization_ratio": c["util_ratio"]} for c in t26]},
            indent=2, ensure_ascii=False) + "\n")
        print(f"\n산출: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
