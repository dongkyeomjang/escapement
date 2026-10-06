#!/usr/bin/env python3
"""Markdown tables of directive G-09 (GTASK22) from the two ignored JSON outputs.

usage: boundary_tables.py --boundary <json> --reuse <json>  (prints markdown)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

Ls = ("60", "90", "120")
AB = {"BASE": "BASE", "POOL": "P", "POOL+GRID": "PG"}


def f4(x):
    return f"{x:.4f}"


def sg(x):
    return f"{x:+.4f}"


def boundary(d: dict) -> None:
    cells = [c for c in d["cells"] if c["config"] != "BASE"]
    print("### A-1 창 길이별 비용 비 (관측 = replicate 쌍 비 중앙, 예측 = plan 5개 합산 비)\n")
    print("| 묶음 | N | 구성 | bound | 관측 60 | 관측 90 | 관측 120 | 관측 폭 | 예측 60 | 예측 90 | 예측 120 | 예측 폭 "
          "| 관측−예측 60 / 90 / 120 | 120 s 재현 (관측 / 예측) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        w = c["windows"]
        o = [w[L]["obs_ratio_median"] for L in Ls]
        p = [w[L]["pred_ratio"] for L in Ls]
        n = f"{c['N']} (탐색)" if c["N"] == 26 else str(c["N"])
        print(f"| {c['set']} | {n} | {c['config']} | {c['bound']} | " + " | ".join(map(f4, o))
              + f" | {f4(c['obs_span'])} | " + " | ".join(map(f4, p)) + f" | {f4(c['pred_span'])} | "
              + " / ".join(sg(a - b) for a, b in zip(o, p))
              + f" | {'예' if c['reproduced_obs_120'] else '아니오'} / {'예' if c['reproduced_pred_120'] else '아니오'} |")
    os_ = [c["obs_span"] for c in cells]
    ps = [c["pred_span"] for c in cells]
    print(f"\n관측 폭 {min(os_):.4f}–{max(os_):.4f}, 중앙 {sorted(os_)[len(os_)//2 - 1]:.4f}/{sorted(os_)[len(os_)//2]:.4f}; "
          f"예측 폭 {min(ps):.4f}–{max(ps):.4f}, 중앙 {sorted(ps)[len(ps)//2 - 1]:.4f}/{sorted(ps)[len(ps)//2]:.4f} "
          f"(22 행, 짝수 개라 가운데 두 값)\n")
    print("### A-2 구성 순위 (창별; P = POOL, PG = POOL+GRID)\n")
    print("| 묶음 | N | bound | 관측 60 | 관측 90 | 관측 120 | 예측 60 | 예측 90 | 예측 120 | 관측 순위 변화 | 예측 순위 변화 "
          "| P·PG 쌍 예측=관측 (60/90/120) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")

    def ab(s):
        return " < ".join(AB[x] for x in s.split(" < "))
    for g in d["groups"]:
        ob, pr = g["obs_order"], g["pred_order"]
        same = []
        for L in Ls:
            if g["N"] == 26:
                same.append("—")
            else:
                po = [x for x in ob[L].split(" < ") if x != "BASE"]
                pp = [x for x in pr[L].split(" < ") if x != "BASE"]
                same.append("예" if po == pp else "아니오")
        print(f"| {g['set']} | {g['N']} | {g['bound']} | " + " | ".join(ab(ob[L]) for L in Ls) + " | "
              + " | ".join(ab(pr[L]) for L in Ls)
              + f" | {'바뀜' if g['obs_order_changes'] else '같음'} | {'바뀜' if g['pred_order_changes'] else '같음'} | "
              + " / ".join(same) + " |")
    print("\n### B-1 경계 잔여 작업량 (L = 120, A′-GPU 총합 대비, cell 합산 [replicate 최소–최대])\n")
    print("| 묶음 | N | 구성 | S lo | E lo | E − S lo | S hi | E hi | E − S hi |")
    print("|---|---|---|---|---|---|---|---|---|")
    rows = {}
    for c in d["cells"]:
        rows.setdefault((c["set"], c["N"], c["config"]), {})[c["bound"]] = c["windows"]["120"]
    for (s, n, cfg), b in rows.items():
        out = []
        for bd in ("lo", "hi"):
            w = b[bd]
            out += [f"{w['start_resid_share']:.4f} [{w['start_resid_share_range'][0]:.4f}–{w['start_resid_share_range'][1]:.4f}]",
                    f"{w['end_resid_share']:.4f} [{w['end_resid_share_range'][0]:.4f}–{w['end_resid_share_range'][1]:.4f}]",
                    sg(w["end_resid_share"] - w["start_resid_share"])]
        print(f"| {s} | {n} | {cfg} | " + " | ".join(out) + " |")
    S = [b[bd]["start_resid_share"] for b in rows.values() for bd in ("lo", "hi")]
    E = [b[bd]["end_resid_share"] for b in rows.values() for bd in ("lo", "hi")]
    D = [b[bd]["end_resid_share"] - b[bd]["start_resid_share"] for b in rows.values() for bd in ("lo", "hi")]
    print(f"\nS cell 범위 {min(S):.4f}–{max(S):.4f}, E {min(E):.4f}–{max(E):.4f}, E − S {min(D):+.4f}–{max(D):+.4f} "
          "(17 cell × 2 bound)\n")
    print("### B-2 경계 보정 후 비 − 원래 비\n")
    print("| 묶음 | N | 구성 | bound | 원래 비 (120) | 보정 비 (120) | 차 (중앙끼리) 60 / 90 / 120 | 쌍별 차 중앙 60 / 90 / 120 "
          "| \\|차\\| > 0.01 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        w = c["windows"]
        big = [f"{L} s" for L in Ls if abs(w[L]["corrected_minus_original"]) > 0.01]
        print(f"| {c['set']} | {c['N']} | {c['config']} | {c['bound']} | {f4(w['120']['obs_ratio_median'])} | "
              f"{f4(w['120']['corrected_ratio_median'])} | "
              + " / ".join(sg(w[L]["corrected_minus_original"]) for L in Ls) + " | "
              + " / ".join(sg(w[L]["paired_diff_median"]) for L in Ls) + " | "
              + (("**" + ", ".join(big) + "**") if big else "—") + " |")
    pairs = []
    for c in cells:
        w = c["windows"]["120"]
        for r, (x, y) in enumerate(zip(w["obs_ratio_per_rep"], w["corrected_ratio_per_rep"])):
            pairs.append((abs(y - x), y - x, c["set"], c["N"], c["config"], c["bound"], r))
    pairs.sort(reverse=True)
    ad = sorted(p[0] for p in pairs)
    print(f"\nreplicate 쌍 {len(pairs)}개(22 행 × 5)의 |보정 − 원래| (L = 120): 중앙 "
          f"{(ad[len(ad)//2 - 1] + ad[len(ad)//2]) / 2:.4f}, 최대 {ad[-1]:.4f}, > 0.01 {sum(x > 0.01 for x in ad)}쌍: "
          + ", ".join(f"{p[2]} N{p[3]} {p[4]} {p[5]} r{p[6]} {p[1]:+.4f}" for p in pairs if p[0] > 0.01) + "\n")
    print(f"membership 무결성: {d['integrity']}\n")


def reuse(d: dict) -> None:
    cells = d["cells"]
    print("### B-1 token 기준 재사용 비율 Σ cached / Σ 재사용 가능 (관측, replicate 합산)\n")
    print("| 묶음 | N | 구성 | Σ cached | Σ 재사용 가능 (cap) | 비율 (cap) | Σ 재사용 가능 (prefix) | 비율 (prefix) |")
    print("|---|---|---|---|---|---|---|---|")
    for c in cells:
        t = c["pooled"]
        print(f"| {c['set']} | {c['N']} | {c['config']} | {t['cached']:,} | {t['reusable_cap']:,} | "
              f"{c['token_ratio_cap']:.4f} | {t['reusable_prefix']:,} | {c['token_ratio_prefix']:.4f} |")
    print("\n### B-1′ token 기준 재사용 비율 replicate별 (cap / prefix)\n")
    print("| 묶음 | N | 구성 | r0 | r1 | r2 | r3 | r4 |")
    print("|---|---|---|---|---|---|---|---|")
    for c in cells:
        print(f"| {c['set']} | {c['N']} | {c['config']} | " + " | ".join(
            f"{x['cached'] / x['reusable_cap']:.4f} / {x['cached'] / x['reusable_prefix']:.4f}" for x in c["per_rep"]) + " |")
    print("\n### B-2 replicate별 재사용률 (요청 단위, hit > 0 / turn ≥ 1)\n")
    print("| 묶음 | N | 구성 | r0 | r1 | r2 | r3 | r4 | 합산 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        t = c["pooled"]
        print(f"| {c['set']} | {c['N']} | {c['config']} | " + " | ".join(
            f"{x['hit']}/{x['n']} = {x['hit'] / x['n']:.3f}" for x in c["per_rep"])
            + f" | {t['hit']:,}/{t['n']:,} = {c['reuse_rate']:.4f} |")
    print("\n### B-3 부분 재사용 비율 (0 < cached < 재사용 가능인 turn ≥ 1 요청 / turn ≥ 1 요청, %; cap / prefix)\n")
    print("| 묶음 | N | 구성 | r0 | r1 | r2 | r3 | r4 | 합산 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        t = c["pooled"]
        print(f"| {c['set']} | {c['N']} | {c['config']} | " + " | ".join(
            f"{100 * x['partial_cap'] / x['n']:.2f} / {100 * x['partial_prefix'] / x['n']:.2f}" for x in c["per_rep"])
            + f" | {t['partial_cap']}/{t['n']:,} = {100 * c['partial_share_cap']:.2f} / "
              f"{t['partial_prefix']}/{t['n']:,} = {100 * c['partial_share_prefix']:.2f} |")
    print(f"\nprompt 구성 확인: {d['construction_check']}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--reuse", type=Path, required=True)
    a = ap.parse_args()
    boundary(json.loads(a.boundary.read_text()))
    print("=" * 20 + "\n")
    reuse(json.loads(a.reuse.read_text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
