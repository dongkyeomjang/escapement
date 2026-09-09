#!/usr/bin/env python3
"""Audit of what the 3.3 observations actually measure.

Definitions are fixed in docs/research/OBSERVATION_AUDIT_PLAN.md, committed
before any of this ran. Nothing here re-adjudicates a past verdict.

  §1  The injection experiment's arrival series. What an "arrival" is, how
      baseline / window / spike / simultaneity were defined, the level medians
      reproduced with the order of the two medians stated, and "simultaneous
      within 1 ms" split into three different quantities that the phrase could
      mean: start-time spread, end-time spread, and width of the common
      intersection.

  §2  The prefill cost model refit from its four stored points, and the
      difference between an increment T(L) - T(L-C) and a standalone T(C).

  §3  Inventory only: whether the capacity run stores what a direct
      interference measurement would need.

  §4  The six N=7 blocks with u, p and Delta p built from the stored [BUCKET]
      sums -- never from a rounded ratio -- split by batch.

  §5  The padding decomposition's unrounded totals and residual.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from padding_ratio import arm_totals  # noqa: E402

PTAX = Path("results/npu/stage2/20260821-220100-prefill-tax")
CAP = Path("results/npu/stage2/20260823-183505-final-confirm")
T23A = Path("results/npu/stage2/20260821-222000-grid-observe")
T25 = Path("results/npu/stage2/20260822-160532-sim-oos")
GRID = (1, 2, 4, 8)


# ------------------------------------------------------------------ §1
def intervals(a: list[float]):
    return [(x, y, y - x) for x, y in zip(a, a[1:])]


def run_arrivals(rec: dict) -> dict:
    inj = rec.get("injection")
    per = []
    for s in rec["bystander_streams"]:
        iv = intervals(s["arrivals_s"])
        if not iv:
            continue
        if inj is None:
            base = statistics.median(g for _, _, g in iv)
            big = max(iv, key=lambda x: x[2])
            per.append({"bystander": s["bystander"], "arrivals": s["arrival_count"],
                        "baseline_s": base, "max_gap_s": big[2],
                        "max_gap_start_s": big[0], "max_gap_end_s": big[1]})
            continue
        lo, hi = inj["sent_s"], inj["done_s"]
        inw = [x for x in iv if x[1] > lo and x[0] < hi]
        outw = [x for x in iv if not (x[1] > lo and x[0] < hi)]
        base = statistics.median(g for _, _, g in outw) if outw else None
        sp = max(inw, key=lambda x: x[2]) if inw else None
        per.append({"bystander": s["bystander"], "arrivals": s["arrival_count"],
                    "baseline_s": base,
                    "spike_s": sp[2] if sp else None,
                    "spike_start_s": sp[0] if sp else None,
                    "spike_end_s": sp[1] if sp else None,
                    "last_arrival_s": s["arrivals_s"][-1]})
    out = {"tag": rec["tag"], "level": rec["inject_prompt_tokens"],
           "rep": rec["rep"], "per": per,
           "bystander_max_tokens": rec["bystander_max_tokens"],
           "warmup_s": rec["warmup_s"]}
    if inj:
        out["inj"] = {k: inj[k] for k in
                      ("sent_s", "done_s", "prefill_time_s", "observed_prompt_tokens",
                       "cached_tokens", "counters_delta")}
        sps = [p for p in per if p.get("spike_s") is not None]
        if len(sps) == len(per) and sps:
            starts = [p["spike_start_s"] for p in sps]
            ends = [p["spike_end_s"] for p in sps]
            out["start_spread_s"] = max(starts) - min(starts)
            out["end_spread_s"] = max(ends) - min(ends)
            out["common_width_s"] = min(ends) - max(starts)
            out["median_spike_s"] = statistics.median(p["spike_s"] for p in sps)
            out["median_baseline_s"] = statistics.median(p["baseline_s"] for p in sps)
        # Did any bystander finish before the injection window closed?
        out["bystander_finished_before_window_close"] = sum(
            1 for p in per if p["last_arrival_s"] < inj["done_s"])
    return out


# ------------------------------------------------------------------ §4
def block_cell(run: Path, n: int, blk: int) -> dict:
    parts = [(run, f"n{n}.b{blk}")]
    a = arm_totals(parts, "AGENTIC", GRID)
    c = arm_totals(parts, "CONVENTIONAL", GRID)
    return {"block": blk, "u_A": a["utilization"], "u_C": c["utilization"],
            "R": a["utilization"] / c["utilization"],
            "p_A": a["padding_ratio"], "p_C": c["padding_ratio"],
            "delta_p": c["padding_ratio"] - a["padding_ratio"],
            "sum_n_A": a["sum_n"], "sum_b_A": a["sum_b"],
            "sum_n_C": c["sum_n"], "sum_b_C": c["sum_b"]}


def pooled(parts) -> dict:
    a = arm_totals(parts, "AGENTIC", GRID)
    c = arm_totals(parts, "CONVENTIONAL", GRID)
    return {"u_A": a["utilization"], "u_C": c["utilization"],
            "R": a["utilization"] / c["utilization"],
            "p_A": a["padding_ratio"], "p_C": c["padding_ratio"],
            "delta_p": c["padding_ratio"] - a["padding_ratio"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    import os
    os.chdir(args.repo)
    out: dict = {}

    # =============================================================== §1
    print("=" * 98)
    print("§1  응답 도착 간격 — 정의 확인과 재현")
    print("=" * 98)
    runs = [run_arrivals(json.loads(f.read_text()))
            for f in sorted(PTAX.glob("probe/prefill_tax.*.json"))]
    out["arrivals"] = runs
    inj_runs = [r for r in runs if "inj" in r]
    ctl_runs = [r for r in runs if "inj" not in r]

    print(f"{'tag':<14}{'수준':>6}{'arrival 수':>28}{'주입창 (s)':>20}"
          f"{'prefill(ms)':>12}{'중앙 spike(ms)':>15}")
    for r in inj_runs:
        counts = [p["arrivals"] for p in r["per"]]
        w = f"[{r['inj']['sent_s']:.3f},{r['inj']['done_s']:.3f}]"
        print(f"{r['tag']:<14}{r['level']:>6}{str(counts):>28}{w:>20}"
              f"{r['inj']['prefill_time_s']*1000:>12.2f}{r['median_spike_s']*1000:>15.2f}")

    print()
    print("  수준별 중앙값 — 적용 순서 두 가지를 모두 낸다")
    print(f"    {'수준':>6}{'① bystander→반복':>22}{'② 반복→bystander':>22}"
          f"{'중앙 prefill(ms)':>18}{'spike/prefill':>14}")
    lvl = {}
    for L in (500, 2000, 6000):
        rs = [r for r in inj_runs if r["level"] == L]
        order1 = statistics.median(r["median_spike_s"] for r in rs)          # ①
        by_b = []
        for b in range(4):
            vals = [p["spike_s"] for r in rs for p in r["per"] if p["bystander"] == b]
            by_b.append(statistics.median(vals))
        order2 = statistics.median(by_b)                                      # ②
        pf = statistics.median(r["inj"]["prefill_time_s"] for r in rs)
        lvl[L] = {"order_bystander_then_rep_ms": order1 * 1000,
                  "order_rep_then_bystander_ms": order2 * 1000,
                  "median_prefill_ms": pf * 1000,
                  "spike_over_prefill": order1 / pf}
        print(f"    {L:>6}{order1*1000:>22.2f}{order2*1000:>22.2f}"
              f"{pf*1000:>18.2f}{order1/pf:>14.3f}")
    out["levels"] = lvl

    print()
    print("  '1 ms 이내 동시'의 세 가지 해석 — 전 9 run")
    print(f"    {'tag':<14}{'시작 시각 차(ms)':>18}{'종료 시각 차(ms)':>18}"
          f"{'공통 교집합 폭(ms)':>20}{'교집합 존재':>12}")
    for r in inj_runs:
        print(f"    {r['tag']:<14}{r['start_spread_s']*1000:>18.3f}"
              f"{r['end_spread_s']*1000:>18.3f}{r['common_width_s']*1000:>20.3f}"
              f"{str(r['common_width_s'] > 0):>12}")
    ss = [r["start_spread_s"] * 1000 for r in inj_runs]
    es = [r["end_spread_s"] * 1000 for r in inj_runs]
    print(f"    시작 차 범위 {min(ss):.3f}–{max(ss):.3f} ms, "
          f"종료 차 범위 {min(es):.3f}–{max(es):.3f} ms")

    print()
    print("  주입 창에서 완료되는 요청이 주입뿐인가 (Q2-2)")
    for r in inj_runs:
        d = r["inj"]["counters_delta"]
        print(f"    {r['tag']:<14}prefill_count 증분 "
              f"{d.get('vllm:request_prefill_time_seconds_count'):>4.0f}   "
              f"창 종료 전에 끝난 bystander {r['bystander_finished_before_window_close']}/4   "
              f"bystander max_tokens {r['bystander_max_tokens']}")

    print()
    print("  대조 3 run — 최대 간격의 발생 시각 (원 PARTIAL 판정의 근거)")
    print(f"    {'tag':<14}{'bystander별 최대 간격(ms)':>34}{'그 간격의 종료 시각(s)':>26}")
    for r in ctl_runs:
        g = [round(p["max_gap_s"] * 1000, 1) for p in r["per"]]
        e = [round(p["max_gap_end_s"], 3) for p in r["per"]]
        print(f"    {r['tag']:<14}{str(g):>34}{str(e):>26}")

    # =============================================================== §2
    print()
    print("=" * 98)
    print("§2  prefill 비용 모형 — 적합 4점 재현과 T(L)−T(L−C) 대 T(C)")
    print("=" * 98)
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    pm = D.prefill_cost_model
    fit = [(500, 0.0885), (2000, 0.3596), (2008, 0.3592), (6000, 1.1772)]
    print(f"    {'n':>6}{'관측(s)':>12}{'모형(s)':>12}{'잔차(s)':>12}{'chunk 수':>10}"
          f"{'chunk당(ms)':>13}")
    worst = 0.0
    for n, obs in fit:
        mod = pm.prefill_s(n)
        worst = max(worst, abs(mod - obs))
        import math
        ch = math.ceil(n / pm.chunk_tokens)
        print(f"    {n:>6}{obs:>12.4f}{mod:>12.4f}{mod-obs:>+12.4f}{ch:>10}"
              f"{mod/ch*1000:>13.2f}")
    print(f"    최대 |잔차| = {worst*1000:.1f} ms")
    out["prefill_fit"] = {"chunk_tokens": pm.chunk_tokens,
                          "per_chunk_s": pm.per_chunk_s,
                          "drift_s_per_token": pm.drift_s_per_token,
                          "worst_residual_ms": worst * 1000}

    print()
    print("    T(L) − T(L−C) 대 T(C) — 같은 C에서 두 값이 다르다")
    print(f"    {'L':>6}{'C':>6}{'T(L)−T(L−C) (s)':>18}{'T(C) (s)':>12}{'차(ms)':>10}")
    diffs = []
    for L, C in ((2008, 88), (2008, 1920), (1490, 338), (6000, 500), (600, 100)):
        inc = pm.prefill_s(L) - pm.prefill_s(L - C)
        std = pm.prefill_s(C)
        diffs.append({"L": L, "C": C, "increment_s": inc, "standalone_s": std})
        print(f"    {L:>6}{C:>6}{inc:>18.4f}{std:>12.4f}{(inc-std)*1000:>10.2f}")
    out["increment_vs_standalone"] = diffs
    print(f"    적합 구간은 [500, 6000] token이다. C < 500은 외삽이다")

    # =============================================================== §3
    print()
    print("=" * 98)
    print("§3  용량 개입에서 간섭의 직접 확인 가능성 — 목록화")
    print("=" * 98)
    rows = [json.loads(l) for l in
            (CAP / "probe" / "requests.BASE.n8.b0.jsonl").read_text().splitlines() if l]
    log = (CAP / "server-BASE.n8.b0.log").read_text(errors="replace")
    ts = re.findall(r"(?:DEBUG|INFO) (\d\d-\d\d \d\d:\d\d:\d\d)", log)
    inv = {
        "per_session_streaming_series": False,
        "per_request_prefill_start_end": False,
        "decode_waiters_at_prefill_time": False,
        "client_row_fields": sorted(rows[0].keys()),
        "server_log_timestamp_example": ts[0] if ts else None,
        "server_log_timestamp_resolution_s": 1,
        "pfx_lines": log.count("[PFX]"),
        "bucket_lines": log.count("[BUCKET]"),
    }
    out["capacity_inventory"] = inv
    print(f"    병행 세션별 streaming 시계열      : {'있음' if inv['per_session_streaming_series'] else '**없음** (요청이 non-streaming)'}")
    print(f"    요청별 prefill 시작·종료 시각     : {'있음' if inv['per_request_prefill_start_end'] else '**없음**'}")
    print(f"    prefill 시점의 decode 대기 세션 수: {'있음' if inv['decode_waiters_at_prefill_time'] else '**없음**'}")
    print(f"    client row가 가진 시각            : sent_s, done_s (요청 단위, perf_counter)")
    print(f"    server 로그 시각 해상도           : **1초** (예: {inv['server_log_timestamp_example']})")
    print(f"    [PFX] {inv['pfx_lines']}줄, [BUCKET] {inv['bucket_lines']}줄 — 자체 timestamp 없음")
    print("    → ms 수준 중첩을 복원할 수 없다. **직접 측정 불가**로 마감한다")

    # =============================================================== §4
    print()
    print("=" * 98)
    print("§4  N=7의 6블록 — u, p, Δp를 [BUCKET] 합계에서 직접 산출")
    print("=" * 98)
    blocks = [("기존", T23A, b) for b in range(3)] + [("신규", T25, b) for b in range(3, 6)]
    print(f"    {'배치':<5}{'블록':>5}{'u_A':>9}{'u_C':>9}{'R':>9}{'밴드':>8}"
          f"{'p_A':>9}{'p_C':>9}{'Δp':>10}")
    rows4 = []
    for batch, run, b in blocks:
        c = block_cell(run, 7, b)
        c["batch"] = batch
        band = "안" if 0.97 <= c["R"] <= 1.03 else ("위" if c["R"] > 1.03 else "아래")
        c["band"] = band
        rows4.append(c)
        print(f"    {batch:<5}{('b'+str(b)):>5}{c['u_A']:>9.4f}{c['u_C']:>9.4f}"
              f"{c['R']:>9.4f}{band:>8}{c['p_A']:>9.4f}{c['p_C']:>9.4f}"
              f"{c['delta_p']:>+10.4f}")
    out["n7_blocks"] = rows4
    band_count = {k: sum(1 for r in rows4 if r["band"] == k) for k in ("위", "안", "아래")}
    print(f"    방향 집계: 위 {band_count['위']}, 밴드 안 {band_count['안']}, "
          f"아래 {band_count['아래']}  (6블록 중 5블록 이상 동방향 요건 미충족)")

    print()
    print("    합산 — 전체와 배치별을 구분한다")
    agg = {
        "6블록 전체": [(T23A, f"n7.b{b}") for b in range(3)] + [(T25, f"n7.b{b}") for b in range(3, 6)],
        "기존 3블록": [(T23A, f"n7.b{b}") for b in range(3)],
        "신규 3블록": [(T25, f"n7.b{b}") for b in range(3, 6)],
    }
    print(f"    {'집계':<12}{'u_A':>9}{'u_C':>9}{'R':>9}{'p_A':>9}{'p_C':>9}{'Δp':>10}")
    out["n7_pooled"] = {}
    for name, parts in agg.items():
        p = pooled(parts)
        out["n7_pooled"][name] = p
        print(f"    {name:<12}{p['u_A']:>9.4f}{p['u_C']:>9.4f}{p['R']:>9.4f}"
              f"{p['p_A']:>9.4f}{p['p_C']:>9.4f}{p['delta_p']:>+10.4f}")

    print()
    print("    Δp의 블록 간 산포 (같은 N=7, 6블록)")
    dps = [r["delta_p"] for r in rows4]
    print(f"      최소 {min(dps):+.4f}  최대 {max(dps):+.4f}  "
          f"범위 {max(dps)-min(dps):.4f}  중앙 {statistics.median(dps):+.4f}")
    print("      이 산포는 blocks 간 trace 차이를 포함한다 — 같은 trace 반복의 변동이 아니다")
    out["n7_delta_p_spread"] = {"min": min(dps), "max": max(dps),
                                "range": max(dps) - min(dps),
                                "median": statistics.median(dps)}

    # =============================================================== §5
    print()
    print("=" * 98)
    print("§5  부록 2 — 반올림 전 값과 잔차")
    print("=" * 98)
    from padding_decompose import analyse
    a6 = analyse(Path("results/npu/stage2/20260908-133635-grid-paired"), 6, "CONVENTIONAL")
    out["decompose_n6"] = {k: a6[k] for k in
                           ("p_mb", "p_mb6", "drop", "pad_slots_mb", "pad_slots_mb6",
                            "pad_slots_removed", "bucket_sum_mb", "bucket_sum_mb6",
                            "shapley", "shapley_share", "numerator_effect",
                            "denominator_effect")}
    print(f"    p  {a6['p_mb']!r} → {a6['p_mb6']!r}")
    print(f"    하락분 (반올림 전) = {a6['drop']!r}")
    sh = a6["shapley"]
    tot = sum(sh.values())
    print(f"    Shapley  n=6 {sh['6']!r}   n=5 {sh['5']!r}")
    print(f"    합 {tot!r}   잔차 {tot - a6['drop']!r}")
    print(f"    분자 {a6['numerator_effect']!r}  분모 {a6['denominator_effect']!r}")
    print(f"    소멸 slot {a6['pad_slots_removed']} = "
          f"{a6['pad_slots_mb']} − {a6['pad_slots_mb6']}")
    print(f"    Σbucket {a6['bucket_sum_mb']} → {a6['bucket_sum_mb6']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                          default=str) + "\n")
        print(f"\n  → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
