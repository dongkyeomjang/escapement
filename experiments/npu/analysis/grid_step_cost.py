#!/usr/bin/env python3
"""TASK55: measured decode step cost per bucket on both grids, and what it
does to the intervention batch's device time.

Three things the intervention rested on but never measured:

  * the intervened grid's C(6) was a linear interpolation between C(4) and
    C(8) (config_search.descriptor_for), so every device-time number computed
    on that grid was a model twice over;
  * nobody checked that recompiling left the cost of the buckets that already
    existed alone -- the two artifacts differ in prefill.rbln bytes too;
  * the padding -> device time conversion on the intervention batch was never
    put against a channel that depends on no cost model.

Part 1/2 measure C(b) on both artifacts by TASK13's method and compare the
four shared buckets. Part 3 re-prices TASK54's stored step columns with the
measured C and puts channel A' (model) against channel B (in-flight union),
importing both channel functions from config_device rather than restating
them.

Verdicts P1, P2a-c, P3, the bands (0.03 ms / 0.06 ms / 0.5 %) and tau(N) are
preregistered in docs/research/GRID_STEP_COST_PREREG.md and are not chosen
here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parents[1] / "substrate"))

from dataclasses import replace  # noqa: E402

from config_device import channel_a_prime, channel_b, CHANNEL_FLOOR  # noqa: E402
from config_search import descriptor_for  # noqa: E402
from bootstrap_ratio import median_ratio_ci  # noqa: E402

GRIDS = {"mb": (1, 2, 4, 8), "mb6": (1, 2, 4, 6, 8)}
LEVELS = {"mb": (1, 2, 4, 8), "mb6": (1, 2, 4, 6, 8)}
SHARED = (1, 2, 4, 8)
ARMS = ("AGENTIC", "CONVENTIONAL")
NS = (6, 8)
REPS = (0, 1, 2)

#: Preregistered bands (GRID_STEP_COST_PREREG.md, "변동 기준의 유도").
BAND_MODEL_MS = 0.03
BAND_FIXED_MS = 0.06
BAND_ITL_RATIO = 0.005
CI_WIDTH_MAX = 0.10
RESAMPLES = 2000
BASE_SEED = 20260955

#: TASK13 measured values, in ms. Cited for juxtaposition, never re-adjudicated.
TASK13_MODEL = {1: 9.51, 2: 10.05, 4: 10.355, 8: 12.4025}
TASK13_SAMPLER = {1: 0.36, 2: 0.37, 4: 0.47, 8: 0.5675}

BUCKET_RE = re.compile(r"\[BUCKET\] request_nums=(\d+) padded_batch_size=(\d+)")
P50_RE = re.compile(r"Latency \(ms\):.*?p50 ([0-9.]+)")


def metrics_p50(log: str, section: str) -> float | None:
    """DECODE p50 of one FINAL PERFORMANCE STATISTICS section, in ms."""
    i = log.find(f"FINAL PERFORMANCE STATISTICS [{section}]")
    if i < 0:
        return None
    tail = log[i:]
    j = tail.find("FINAL PERFORMANCE STATISTICS", 1)
    if j > 0:
        tail = tail[:j]
    k = tail.find("DECODE METRICS:")
    if k < 0:
        return None
    m = P50_RE.search(tail[k:])
    return float(m.group(1)) if m else None


def read_level(run: Path, grid: str, level: int) -> dict:
    log = (run / f"server-{grid}.L{level}.log").read_text(errors="replace")
    probe = json.loads((run / "probe" / f"decode_cost.{grid}.L{level}.json").read_text())
    pairs = [(int(a), int(b)) for a, b in BUCKET_RE.findall(log)]
    statuses = sorted({r["status"] for r in probe["requests"]})
    chunks = sorted({r["chunk_count"] for r in probe["requests"]})
    actuals = sorted({a for a, _ in pairs})
    buckets = sorted({b for _, b in pairs})
    return {
        "grid": grid, "level": level,
        "model_p50_ms": metrics_p50(log, "MODEL"),
        "sampler_p50_ms": metrics_p50(log, "SAMPLER"),
        "itl_samples": probe["itl_samples"],
        "median_itl_ms": statistics.median(probe["itl_samples"]) * 1000,
        "server_mean_itl_ms": (probe["server_mean_itl_s"] or 0) * 1000,
        "client_mean_itl_ms": statistics.fmean(probe["itl_samples"]) * 1000,
        "step_lines": len(pairs), "actuals": actuals, "buckets": buckets,
        "statuses": statuses, "chunk_counts": chunks,
        "counters_delta": probe["counters_delta"],
    }


def gates(cells: dict) -> dict:
    g1, g2 = [], []
    for (grid, level), c in sorted(cells.items()):
        g1.append({"grid": grid, "level": level,
                   "statuses": c["statuses"], "chunk_counts": c["chunk_counts"],
                   "ok": c["statuses"] == [200] and c["chunk_counts"] == [512]})
        expected = min(b for b in GRIDS[grid] if b >= level)
        g2.append({"grid": grid, "level": level, "step_lines": c["step_lines"],
                   "actuals": c["actuals"], "buckets": c["buckets"],
                   "expected_bucket": expected,
                   "ok": (c["step_lines"] == 511 and c["actuals"] == [level]
                          and c["buckets"] == [expected])})
    return {"G1": {"rows": g1, "pass": all(r["ok"] for r in g1)},
            "G2": {"rows": g2, "pass": all(r["ok"] for r in g2)}}


def measured_descriptor(base, grid: str, cells: dict):
    """Descriptor whose fixed_s_by_bucket is this run's measurement.

    Only the bucket-determined term is replaced. The residual slope, the
    intercept and the prefill model stay at their TASK13 / TASK22 values:
    this task measures C(bucket), it does not refit the cost model.
    """
    d = descriptor_for(base, GRIDS[grid], 8)
    fixed = {}
    for level in LEVELS[grid]:
        c = cells[(grid, level)]
        b = min(x for x in GRIDS[grid] if x >= level)
        fixed[b] = (c["model_p50_ms"] + c["sampler_p50_ms"]) / 1000.0
    missing = set(GRIDS[grid]) - set(fixed)
    if missing:
        raise SystemExit(f"{grid}: no measurement for buckets {sorted(missing)}")
    return replace(d, step_cost_model=replace(d.step_cost_model,
                                              fixed_s_by_bucket=fixed))


def cell_channels(t54: Path, grid: str, n: int, arm: str, reps, descriptor) -> dict:
    a = b = dec = pre = 0.0
    per_rep = []
    for rep in reps:
        tag = f"{arm}.n{n}.b{rep}"
        util = json.loads((t54 / grid / f"util.{tag}.json").read_text())
        if not util.get("valid", True):
            raise SystemExit(f"INVALID {grid}/{tag}")
        rows = [json.loads(l) for l in
                (t54 / grid / "probe" / f"requests.{tag}.jsonl").read_text().splitlines()
                if l.strip()]
        tot, d_, p_ = channel_a_prime(util, rows, descriptor)
        bb = channel_b(rows)
        a += tot; dec += d_; pre += p_; b += bb
        per_rep.append({"rep": rep, "a_prime_s": tot, "b_s": bb,
                        "decode_s": d_, "prefill_s": p_})
    return {"a_prime_s": a, "b_s": b, "decode_s": dec, "prefill_s": pre,
            "residual_s": b - a, "per_rep": per_rep}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path, help="TASK55 step-cost run dir")
    ap.add_argument("--task54-run", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    import os
    os.chdir(args.repo)
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as BASE

    cells = {(g, l): read_level(args.run, g, l)
             for g in GRIDS for l in LEVELS[g]}
    out: dict = {"run": str(args.run), "task54_run": str(args.task54_run),
                 "bands": {"model_ms": BAND_MODEL_MS, "fixed_ms": BAND_FIXED_MS,
                           "itl_ratio": BAND_ITL_RATIO}}

    # ------------------------------------------------------------- gates
    gt = gates(cells)
    out["gates"] = gt
    print("=" * 96)
    print("§0  게이트")
    print("=" * 96)
    print(f"  G1 status 200 · chunk 512 : {'PASS' if gt['G1']['pass'] else 'FAIL'}"
          f"  ({len(gt['G1']['rows'])} level)")
    print(f"  G2 [BUCKET] 511줄 · 사상   : {'PASS' if gt['G2']['pass'] else 'FAIL'}")
    for r in gt["G2"]["rows"]:
        print(f"     {r['grid']:4} L{r['level']}: {r['step_lines']:>3}줄 "
              f"actual={r['actuals']} bucket={r['buckets']} "
              f"기대 {r['expected_bucket']} {'ok' if r['ok'] else 'FAIL'}")
    if not (gt["G1"]["pass"] and gt["G2"]["pass"]):
        raise SystemExit("게이트 실패 — 비용값을 내지 않는다.")

    print()
    print("=" * 96)
    print("§1  C(bucket) 실측 — 채널 D 대조 포함")
    print("=" * 96)
    print(f"{'격자':<5}{'level':>6}{'bucket':>7}{'C_model':>10}{'C_sampler':>11}"
          f"{'C_fixed':>10}{'ITL 중앙':>10}{'ITL 평균(C)':>12}{'ITL 평균(D)':>12}")
    rows = []
    for g in GRIDS:
        for l in LEVELS[g]:
            c = cells[(g, l)]
            b = min(x for x in GRIDS[g] if x >= l)
            fixed = c["model_p50_ms"] + c["sampler_p50_ms"]
            rows.append({"grid": g, "level": l, "bucket": b,
                         "model_ms": c["model_p50_ms"],
                         "sampler_ms": c["sampler_p50_ms"], "fixed_ms": fixed,
                         "median_itl_ms": c["median_itl_ms"],
                         "client_mean_itl_ms": c["client_mean_itl_ms"],
                         "server_mean_itl_ms": c["server_mean_itl_ms"]})
            print(f"{g:<5}{l:>6}{b:>7}{c['model_p50_ms']:>10.2f}"
                  f"{c['sampler_p50_ms']:>11.2f}{fixed:>10.3f}"
                  f"{c['median_itl_ms']:>10.3f}{c['client_mean_itl_ms']:>12.3f}"
                  f"{c['server_mean_itl_ms']:>12.3f}")
    out["levels"] = rows

    # -------------------------------------------------------------- P1
    mb6 = {r["bucket"]: r for r in rows if r["grid"] == "mb6"}
    seq = [mb6[b]["model_ms"] for b in (1, 2, 4, 6, 8)]
    p1 = all(x < y for x, y in zip(seq, seq[1:]))
    interp = descriptor_for(BASE, GRIDS["mb6"], 8).step_cost_model.fixed_s_by_bucket[6] * 1000
    out["P1"] = {"pass": p1, "model_sequence_ms": seq}
    out["C6"] = {"measured_fixed_ms": mb6[6]["fixed_ms"],
                 "interpolated_fixed_ms": interp,
                 "delta_ms": mb6[6]["fixed_ms"] - interp,
                 "measured_model_ms": mb6[6]["model_ms"]}

    # ------------------------------------------------------------- P2
    print()
    print("=" * 96)
    print(f"§2  통제 비교 — 공유 bucket 4개 (밴드 model {BAND_MODEL_MS} ms / "
          f"fixed {BAND_FIXED_MS} ms / ITL비 ±{BAND_ITL_RATIO})")
    print("=" * 96)
    print(f"{'bucket':>7}{'mb C_model':>12}{'mb6 C_model':>13}{'Δmodel':>9}{'':>4}"
          f"{'mb C_fixed':>12}{'mb6 C_fixed':>13}{'Δfixed':>9}{'':>4}"
          f"{'ITL비':>8}{'':>4}{'TASK13':>9}")
    ctrl = []
    for b in SHARED:
        a = next(r for r in rows if r["grid"] == "mb" and r["bucket"] == b)
        c = next(r for r in rows if r["grid"] == "mb6" and r["bucket"] == b)
        dm = c["model_ms"] - a["model_ms"]
        df = c["fixed_ms"] - a["fixed_ms"]
        ri = c["median_itl_ms"] / a["median_itl_ms"]
        e = {"bucket": b, "mb_model_ms": a["model_ms"], "mb6_model_ms": c["model_ms"],
             "delta_model_ms": dm, "mb_fixed_ms": a["fixed_ms"],
             "mb6_fixed_ms": c["fixed_ms"], "delta_fixed_ms": df,
             "itl_ratio": ri,
             "in_band_model": abs(dm) <= BAND_MODEL_MS,
             "in_band_fixed": abs(df) <= BAND_FIXED_MS,
             "in_band_itl": abs(ri - 1.0) <= BAND_ITL_RATIO,
             "task13_model_ms": TASK13_MODEL[b],
             "mb_minus_task13_ms": a["model_ms"] - TASK13_MODEL[b]}
        ctrl.append(e)
        print(f"{b:>7}{a['model_ms']:>12.2f}{c['model_ms']:>13.2f}{dm:>+9.2f}"
              f"{'ok' if e['in_band_model'] else 'OUT':>4}"
              f"{a['fixed_ms']:>12.3f}{c['fixed_ms']:>13.3f}{df:>+9.3f}"
              f"{'ok' if e['in_band_fixed'] else 'OUT':>4}"
              f"{ri:>8.4f}{'ok' if e['in_band_itl'] else 'OUT':>4}"
              f"{TASK13_MODEL[b]:>9.3f}")
    out["control"] = ctrl
    out["P2a"] = {"pass": all(e["in_band_model"] for e in ctrl)}
    out["P2b"] = {"pass": all(e["in_band_fixed"] for e in ctrl)}
    out["P2c"] = {"pass": all(e["in_band_itl"] for e in ctrl)}

    print()
    print(f"  보조 — 채널 C 중앙 ITL의 mb6/mb bootstrap CI (폭 상한 {CI_WIDTH_MAX})")
    print(f"    {'bucket':>7}{'n_mb':>8}{'n_mb6':>8}{'비':>9}{'CI':>20}{'폭':>9}{'판정':>13}")
    boot = []
    for b in SHARED:
        la = next(l for l in LEVELS["mb"] if min(x for x in GRIDS["mb"] if x >= l) == b)
        lc = next(l for l in LEVELS["mb6"] if min(x for x in GRIDS["mb6"] if x >= l) == b)
        r = median_ratio_ci(cells[("mb", la)]["itl_samples"],
                            cells[("mb6", lc)]["itl_samples"],
                            resamples=RESAMPLES, base_seed=BASE_SEED, label=f"b{b}")
        r["bucket"] = b
        r["ci_width_within_bound"] = r["ci_width"] <= CI_WIDTH_MAX
        r["verdict"] = ("EQUIVALENT" if (r["contains_one"] and r["ci_width_within_bound"])
                        else ("DIFFERENT" if not r["contains_one"] else "INCONCLUSIVE"))
        boot.append(r)
        print(f"    {b:>7}{r['n_a']:>8}{r['n_b']:>8}{r['point_ratio']:>9.4f}"
              f"   [{r['ci_low']:.4f},{r['ci_high']:.4f}]{r['ci_width']:>9.4f}"
              f"{r['verdict']:>13}")
    out["bootstrap"] = boot
    print("  TASK13이 이미 보인 대로 표본이 수천이면 0.1 % 차이도 CI가 1을 배제한다.")
    print("  판정은 크기(P2a–P2c)로 하고 CI는 불확실성 보고용이다 — 선등록대로.")

    # ------------------------------------------------------------- P3
    print()
    print("=" * 96)
    print("§3  device time 검증 — TASK54 배치에 실측 C 적용, 채널 A′ 대 채널 B")
    print("=" * 96)
    desc_m = {g: measured_descriptor(BASE, g, cells) for g in GRIDS}
    desc_i = {g: descriptor_for(BASE, GRIDS[g], 8) for g in GRIDS}

    ch: dict = {}
    for g in GRIDS:
        for n in NS:
            for arm in ARMS:
                ch[(g, n, arm)] = cell_channels(args.task54_run, g, n, arm,
                                                REPS, desc_m[g])
    print(f"{'격자':<5}{'N':>3}{'arm':>14}{'A′(s)':>10}{'decode':>9}{'prefill':>9}"
          f"{'B(s)':>10}{'r=B−A′':>10}{'r/B':>8}")
    for g in GRIDS:
        for n in NS:
            for arm in ARMS:
                c = ch[(g, n, arm)]
                print(f"{g:<5}{n:>3}{arm:>14}{c['a_prime_s']:>10.3f}"
                      f"{c['decode_s']:>9.3f}{c['prefill_s']:>9.3f}"
                      f"{c['b_s']:>10.3f}{c['residual_s']:>10.3f}"
                      f"{c['residual_s'] / c['b_s']:>8.4f}")
    out["channels"] = {f"{g}.n{n}.{a}": v for (g, n, a), v in ch.items()}

    pairs = []
    for g in GRIDS:                       # arm 짝: 분모 CONVENTIONAL
        for n in NS:
            pairs.append(("arm", f"{g}.n{n}", ch[(g, n, "AGENTIC")],
                          ch[(g, n, "CONVENTIONAL")], n))
    for n in NS:                          # 격자 짝: 분모 mb
        for arm in ARMS:
            pairs.append(("grid", f"n{n}.{arm}", ch[("mb6", n, arm)],
                          ch[("mb", n, arm)], n))

    print()
    print(f"{'짝':<6}{'라벨':<18}{'A′비':>9}{'B비':>9}{'차':>9}{'τ(N)':>9}{'판정':>7}{'0.02기준':>10}")
    res = []
    for kind, label, num, den, n in pairs:
        tau = max(CHANNEL_FLOOR, den["residual_s"] / den["b_s"])
        ra = num["a_prime_s"] / den["a_prime_s"]
        rb = num["b_s"] / den["b_s"]
        gap = abs(ra - rb)
        e = {"kind": kind, "label": label, "N": n, "a_prime_ratio": ra,
             "b_ratio": rb, "gap": gap, "tau": tau, "pass": gap <= tau,
             "pass_fixed_002": gap <= CHANNEL_FLOOR}
        res.append(e)
        print(f"{kind:<6}{label:<18}{ra:>9.4f}{rb:>9.4f}{gap:>9.4f}{tau:>9.4f}"
              f"{'통과' if e['pass'] else '초과':>7}"
              f"{'통과' if e['pass_fixed_002'] else '초과':>10}")
    out["P3"] = {"pass": all(e["pass"] for e in res), "pairs": res}

    # ------------------------------------------------------- 파트 4 표
    t54 = json.loads((args.task54_run / "grid_paired.json").read_text())
    dp = {(c["grid"], c["N"]): c["delta_p"] for c in t54["cells"]}

    dev: dict = {}
    for g in GRIDS:
        for n in NS:
            for tag, d in (("measured", desc_m[g]), ("interp", desc_i[g])):
                a = c_ = 0.0
                for arm, acc in (("AGENTIC", "a"), ("CONVENTIONAL", "c")):
                    tot = 0.0
                    for rep in REPS:
                        util = json.loads((args.task54_run / g /
                                           f"util.{arm}.n{n}.b{rep}.json").read_text())
                        for key, count in util["pair_histogram"].items():
                            act, bk = (int(x) for x in key.split("->"))
                            tot += d.step_cost_model.step_time_s(
                                bucket=bk, actual=act) * count
                    if acc == "a":
                        a = tot
                    else:
                        c_ = tot
                dev[(g, n, tag)] = {"agentic_s": a, "conventional_s": c_,
                                    "ratio": a / c_}

    print()
    print("=" * 96)
    print("§4  격자 × {Δpadding, Δdevice time} 요약")
    print("=" * 96)
    for n in NS:
        print(f"  N = {n}")
        print(f"    {'격자':<6}{'Δpadding (Δp)':>16}{'Δdevice (A/C, 실측 C)':>24}"
              f"{'(보간 C)':>12}{'차':>9}")
        for g in GRIDS:
            m, i = dev[(g, n, "measured")], dev[(g, n, "interp")]
            print(f"    {g:<6}{dp[(g, n)]:>+16.4f}{m['ratio']:>24.4f}"
                  f"{i['ratio']:>12.4f}{m['ratio'] - i['ratio']:>+9.4f}")
        print()
    out["summary_2x2"] = {
        f"{g}.n{n}": {"delta_p": dp[(g, n)],
                      "device_ratio_measured": dev[(g, n, "measured")]["ratio"],
                      "device_ratio_interp": dev[(g, n, "interp")]["ratio"],
                      "device_agentic_s": dev[(g, n, "measured")]["agentic_s"],
                      "device_conventional_s": dev[(g, n, "measured")]["conventional_s"]}
        for g in GRIDS for n in NS}

    print("=" * 96)
    print("§5  선등록 판정")
    print("=" * 96)
    print(f"  P1  mb6 C_model 단조 증가                 : "
          f"{'PASS' if out['P1']['pass'] else 'FAIL'}  "
          f"{[round(x, 2) for x in seq]}")
    print(f"  P2a |ΔC_model| ≤ {BAND_MODEL_MS} ms (4 bucket)      : "
          f"{'PASS' if out['P2a']['pass'] else 'FAIL'}")
    print(f"  P2b |ΔC_fixed| ≤ {BAND_FIXED_MS} ms (4 bucket)      : "
          f"{'PASS' if out['P2b']['pass'] else 'FAIL'}")
    print(f"  P2c ITL 중앙비 1 ± {BAND_ITL_RATIO} (4 bucket)     : "
          f"{'PASS' if out['P2c']['pass'] else 'FAIL'}")
    print(f"  P3  8개 짝 전부 채널차 ≤ τ(N)             : "
          f"{'PASS' if out['P3']['pass'] else 'FAIL'}  "
          f"({sum(e['pass'] for e in res)}/8, 고정 0.02 기준 "
          f"{sum(e['pass_fixed_002'] for e in res)}/8)")
    print()
    print(f"  C(6) 실측 {out['C6']['measured_fixed_ms']:.3f} ms  대  "
          f"보간 {interp:.4f} ms   차 {out['C6']['delta_ms']:+.3f} ms "
          f"({100 * out['C6']['delta_ms'] / interp:+.2f} %)  [판정 없음]")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"\n  → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
