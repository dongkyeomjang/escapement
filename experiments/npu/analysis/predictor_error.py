#!/usr/bin/env python3
"""Online error of a borrowed tool-duration predictor, against the threshold.

The predictor is fed the workload's own call sequence one call at a time,
predicting each before it is observed. What comes out is an error that can be
placed next to the accuracy threshold the foresight curve produced -- which is
the only way to answer "is a predictor good enough" rather than "is a
predictor accurate".

Error is summarised by its standard deviation, because that is how the
threshold was defined: sigma* is the standard deviation of injected noise at
which half the foresight gain survives. Median and p90 absolute error are
reported alongside, since a heavy-tailed error is not described by one number.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from continuum.policy.predictor import ToolDurationPredictor  # noqa: E402
from continuum.workload.tools import load_mix  # noqa: E402


def err_stats(errs: list[float]) -> dict:
    if not errs:
        return {"n": 0}
    a = sorted(abs(e) for e in errs)
    return {
        "n": len(errs),
        "std": statistics.stdev(errs) if len(errs) > 1 else 0.0,
        "mean_signed": statistics.mean(errs),
        "abs_p50": a[len(a) // 2],
        "abs_p90": a[min(len(a) - 1, int(0.90 * len(a)))],
        "abs_p99": a[min(len(a) - 1, int(0.99 * len(a)))],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--summary", required=True)
    p.add_argument("--cap-s", type=float, default=60.0)
    p.add_argument("--calls", type=int, default=200_000)
    p.add_argument("--seed", type=int, default=20260970)
    p.add_argument("--delta", type=float, default=0.1)
    p.add_argument("--min-observations", type=int, default=5)
    p.add_argument("--thresholds", default="1.056,1.823",
                   help="sigma* values (seconds) to judge against")
    p.add_argument("--measured-run", type=Path,
                   help="a measured run whose gaps check the draw law")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    mix = load_mix(args.summary, cap_s=args.cap_s)
    rng = random.Random(args.seed)
    thresholds = [float(x) for x in args.thresholds.split(",")]

    preds = {e: ToolDurationPredictor(delta=args.delta,
                                      min_observations=args.min_observations)
             for e in ("bound", "mean")}
    errs = {e: [] for e in preds}
    by_count = {e: {} for e in preds}     # per-tool observation count -> errors
    by_tool = {e: {} for e in preds}
    by_band = {e: {} for e in preds}
    band_of = {t.name: t.band for t in mix.tools}
    tiers = {e: {} for e in preds}

    for _ in range(args.calls):
        tool, actual = mix.draw(rng)
        for e, pr in preds.items():
            k = pr.observations(tool)
            got = pr.predict(tool, estimator=e)
            d = got - actual
            errs[e].append(d)
            bucket = 0 if k == 0 else min(10 ** len(str(k - 1)), 100000)
            by_count[e].setdefault(bucket, []).append(d)
            by_tool[e].setdefault(tool, []).append(d)
            by_band[e].setdefault(band_of[tool], []).append(d)
            t = pr.tier(tool)
            tiers[e][t] = tiers[e].get(t, 0) + 1
        for pr in preds.values():
            pr.observe(tool, actual)

    report = {"calls": args.calls, "delta": args.delta,
              "min_observations": args.min_observations,
              "cap_s": args.cap_s, "thresholds_s": thresholds, "estimators": {}}

    print(f"호출 {args.calls:,}회, 도구 {len(mix.tools)}종, δ={args.delta}, N={args.min_observations}")
    print(f"판정 문턱 σ* = {thresholds} s\n")
    for e in ("bound", "mean"):
        overall = err_stats(errs[e])
        last = err_stats(errs[e][-args.calls // 4:])
        report["estimators"][e] = {"overall": overall, "converged": last,
                                   "tiers": tiers[e]}
        label = "B(δ) — 논문 그대로" if e == "bound" else "μ̂ — 신뢰항 없는 점추정"
        print(f"[{label}]")
        print(f"  전체      : 오차 std {overall['std']:.3f} s  |오차| p50 {overall['abs_p50']:.3f} "
              f"p90 {overall['abs_p90']:.3f} p99 {overall['abs_p99']:.3f}  평균부호 {overall['mean_signed']:+.3f}")
        print(f"  수렴 후(마지막 1/4): 오차 std {last['std']:.3f} s  |오차| p50 {last['abs_p50']:.3f} "
              f"p90 {last['abs_p90']:.3f}")
        for th in thresholds:
            ok = last["std"] <= th
            print(f"    σ* = {th:.3f} s 대비: {'이내' if ok else '초과'} "
                  f"({last['std']/th:.1f}배)")
        print(f"  tier 분포 : {tiers[e]}")

    print("\n=== 도구별 관측 수에 따른 수렴 (μ̂ 기준) ===")
    print(f"{'관측 수 구간':>12} {'n':>9} {'오차 std':>10} {'|오차| p50':>11}")
    for b in sorted(by_count["mean"]):
        st = err_stats(by_count["mean"][b])
        lab = "0" if b == 0 else f"< {b}"
        print(f"{lab:>12} {st['n']:>9,} {st['std']:>10.3f} {st['abs_p50']:>11.3f}")
    report["by_count"] = {str(k): err_stats(v) for k, v in by_count["mean"].items()}

    print("\n=== 유형별 분해 — 어느 유형이 문턱을 깨는가 (μ̂, 수렴 후) ===")
    print(f"{'유형':>10} {'호출 비중':>9} {'오차 std':>10} {'|오차| p50':>11} {'|오차| p90':>11} {'σ*=1.82 s':>10}")
    tail = len(errs["mean"]) - args.calls // 4
    band_tail = {b: v[-max(1, len(v) // 4):] for b, v in by_band["mean"].items()}
    for b in ("instant", "fast", "medium", "slow", "very_slow"):
        if b not in band_tail:
            continue
        st = err_stats(band_tail[b])
        share = len(by_band["mean"][b]) / args.calls
        print(f"{b:>10} {100*share:>8.2f}% {st['std']:>10.3f} {st['abs_p50']:>11.3f} "
              f"{st['abs_p90']:>11.3f} {'이내' if st['std']<=max(thresholds) else '초과':>10}")
    report["by_band"] = {b: err_stats(v) for b, v in band_tail.items()}

    print("\n=== 도구별 상위 (호출 수 기준, μ̂ 수렴 후) ===")
    print(f"{'도구':<16} {'호출':>8} {'오차 std':>10} {'|오차| p50':>11}")
    top = sorted(by_tool["mean"].items(), key=lambda kv: -len(kv[1]))[:10]
    report["by_tool"] = {}
    for name, v in top:
        st = err_stats(v[-max(1, len(v) // 4):])
        report["by_tool"][name] = st
        print(f"{name:<16} {len(v):>8,} {st['std']:>10.3f} {st['abs_p50']:>11.3f}")

    if args.measured_run:
        gaps = []
        for f in sorted(args.measured_run.glob("probe/meta.*.json")):
            m = json.loads(f.read_text())
            gaps += [g[0] for g in m["plan"]["gap_after_s"]]
        report["measured_gaps"] = {"n": len(gaps),
                                   "median": statistics.median(gaps),
                                   "mean": statistics.mean(gaps),
                                   "max": max(gaps)}
        print(f"\n실측 run의 gap {len(gaps)}개: 중앙 {statistics.median(gaps):.3f} s "
              f"평균 {statistics.mean(gaps):.3f} s 최대 {max(gaps):.3f} s "
              f"(추출 법칙 중앙 {statistics.median([mix.draw(rng)[1] for _ in range(20000)]):.3f} s)")

    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
