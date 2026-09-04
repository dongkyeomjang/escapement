#!/usr/bin/env python3
"""Build section 3.1's table: padding share beside decode device time.

The point of the table is a reversal. In the low-concurrency cells the gap
condition pads *less* than the no-gap condition, and in every cell it spends
*more* decode device time. Both numbers therefore have to be formed on the same
pooled set of blocks, or "the same combination" is not the same combination.

That constraint decides the row set. The device-time column exists for exactly
eleven pooled cells, so those eleven are the rows, and the padding column is
formed on the identical block lists by the identical code path -- this file
imports the cell definitions and the totals function from the analysis module
rather than restating either.

Seven of the eleven rows coincide with a cell whose padding share is already
printed in the padding-ratio record; those seven are checked against it here,
and the check is fatal. The other four pool two runs together, a pooling that
record splits by source run; ``UNALIGNED`` names them, and the provenance
document lists what they are made of.

Outputs the Korean markdown table and a booktabs LaTeX version of the same
numbers. It computes nothing that the committed analysis module does not.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/npu/analysis"))

import padding_ratio as pr  # noqa: E402

#: (grid, N) -> (p AGENTIC, p CONVENTIONAL) as printed in the padding record for
#: the cell that covers exactly the same blocks. Fatal if recomputation differs.
ALIGNED = {
    (pr.BASE_GRID, 5): (0.1707, 0.2684),
    (pr.BASE_GRID, 6): (0.1199, 0.2350),
    (pr.BASE_GRID, 10): (0.1522, 0.0686),
    (pr.BASE_GRID, 12): (0.0983, 0.0191),
    (pr.BASE_GRID, 16): (0.0388, 0.0334),
    (pr.INTERVENED_GRID, 6): (0.0776, 0.0508),
    (pr.INTERVENED_GRID, 8): (0.0752, 0.0273),
}

#: Rows whose pooling spans two runs, which the padding record reports
#: separately. (grid, N) -> the constituent cells, for the provenance document.
UNALIGNED = {
    (pr.BASE_GRID, 3): "관측 격자 b0-b2 (0.0976 / 0.1660) + 표본외 b3-b5 (0.1328 / 0.2203)",
    (pr.BASE_GRID, 4): "sweep b0-b2 (0.0275 / 0.0662) + 표본외 b3-b5 (0.0410 / 0.0567)",
    (pr.BASE_GRID, 7): "관측 격자 b0-b2 (0.1528 / 0.1710) + 표본외 b3-b5 (0.1626 / 0.1887)",
    (pr.BASE_GRID, 8): "sweep b0-b4 (0.1593 / 0.0914) + 관측 격자 b5-b7 (0.1675 / 0.0884)",
}

#: Device-time ratios as printed in the device-time record, to three decimals.
#: That column is a ratio of its own rounded seconds, so the check is against
#: the same construction rather than against the full-precision quotient.
DEVICE_RATIO = {
    (pr.BASE_GRID, 3): 1.430, (pr.BASE_GRID, 4): 1.780,
    (pr.BASE_GRID, 5): 1.272, (pr.BASE_GRID, 6): 1.514,
    (pr.BASE_GRID, 7): 1.379, (pr.BASE_GRID, 8): 1.388,
    (pr.BASE_GRID, 10): 1.231, (pr.BASE_GRID, 12): 1.054,
    (pr.BASE_GRID, 16): 1.067,
    (pr.INTERVENED_GRID, 6): 1.669, (pr.INTERVENED_GRID, 8): 1.390,
}

DAGGER_GRID = pr.INTERVENED_GRID

CAPTION_KO = ("표 3.1 — gap 유무에 따른 padding 비율과 decode device time. "
              "Δp > 0은 gap 조건의 padding이 낮음을 뜻함")
NOTE_KO = "† bucket 6의 step 비용은 4와 8의 보간값임"


def grid_label(g) -> str:
    return "{" + ", ".join(str(x) for x in g) + "}"


def rows() -> list[dict]:
    out = []
    for c in pr.TASK26_CELLS:
        key = (c["grid"], c["N"])
        a = pr.arm_totals(c["parts"], "AGENTIC", c["grid"])
        k = pr.arm_totals(c["parts"], "CONVENTIONAL", c["grid"])
        out.append({
            "grid": c["grid"], "N": c["N"], "blocks": c["blocks"],
            "p_gap": a["padding_ratio"], "p_nogap": k["padding_ratio"],
            "delta_p": k["padding_ratio"] - a["padding_ratio"],
            "device_ratio": a["device_s"] / k["device_s"],
            "device_ratio_printed": DEVICE_RATIO[key],
            "aligned": key in ALIGNED,
            "dagger": c["grid"] == DAGGER_GRID,
        })
    # Grouped by grid, N ascending. TASK26_CELLS is already in that order; sort
    # anyway so the file does not depend on that.
    out.sort(key=lambda r: (len(r["grid"]), r["grid"], r["N"]))
    return out


def verify(rs: list[dict]) -> list[str]:
    """Fatal cross-checks. Returns the report lines; raises on any mismatch."""
    lines = []
    bad = 0
    for r in rs:
        key = (r["grid"], r["N"])
        if r["aligned"]:
            ea, ek = ALIGNED[key]
            da, dk = abs(r["p_gap"] - ea), abs(r["p_nogap"] - ek)
            ok = da <= 5e-5 and dk <= 5e-5
            bad += 0 if ok else 1
            lines.append(
                f"  {'OK  ' if ok else 'DIFF'} p  {grid_label(r['grid']):<14}N={r['N']:<3}"
                f" gap {r['p_gap']:.4f} vs {ea:.4f} (Δ{da:.4f})"
                f"   무gap {r['p_nogap']:.4f} vs {ek:.4f} (Δ{dk:.4f})")
        else:
            lines.append(
                f"  --   p  {grid_label(r['grid']):<14}N={r['N']:<3}"
                f" gap {r['p_gap']:.4f}  무gap {r['p_nogap']:.4f}"
                f"   (합산 단위가 달라 직접 대조 대상 아님)")
    for r in rs:
        # The device record's ratio column is the quotient of its rounded
        # seconds; the recomputed full-precision quotient must round to it.
        got = round(r["device_ratio"], 3)
        exp = r["device_ratio_printed"]
        ok = abs(got - exp) <= 1.001e-3
        bad += 0 if ok else 1
        lines.append(
            f"  {'OK  ' if ok else 'DIFF'} 비 {grid_label(r['grid']):<14}N={r['N']:<3}"
            f" {r['device_ratio']:.4f} → {got:.3f} vs 기록 {exp:.3f}")
    if bad:
        raise SystemExit("\n".join(lines) + f"\n\n대조 실패 {bad}건 — 표를 내지 않는다.")
    return lines


def markdown(rs: list[dict]) -> str:
    head = ("| 격자 | N | p_gap | p_무gap | Δp | decode device time 비 (gap/무gap) |\n"
            "|---|---|---|---|---|---|\n")
    body = ""
    for r in rs:
        g = grid_label(r["grid"]) + ("†" if r["dagger"] else "")
        rev = r["delta_p"] > 0 and r["device_ratio_printed"] > 1.0
        cells = [g, str(r["N"]), f"{r['p_gap']:.3f}", f"{r['p_nogap']:.3f}",
                 f"{r['delta_p']:+.3f}", f"{r['device_ratio_printed']:.2f}"]
        if rev:
            cells = [f"**{c}**" for c in cells]
        body += "| " + " | ".join(cells) + " |\n"
    return (f"<!-- TABLECOLS: p{{2.0cm}}p{{0.6cm}}p{{1.2cm}}p{{1.3cm}}p{{1.1cm}}p{{2.5cm}} -->\n"
            f"<!-- TABLELABEL: padvsdevice -->\n"
            f"<!-- TABLENOTE: {NOTE_KO} -->\n"
            f"<!-- TABLE: {CAPTION_KO} -->\n\n" + head + body)


def latex(rs: list[dict]) -> str:
    """booktabs version of the same numbers.

    Deliberately plain: the grid is set in text mode so ``\\textbf`` actually
    bolds it (it would not inside math), the note is a ``\\footnotesize`` line
    rather than ``tablenotes`` so it needs no ``threeparttable``, and signed
    numbers are in math mode so the minus is a minus and not a hyphen.
    """
    out = ["% 한국어 캡션·머리글이 들어 있어 CJK 지원 없는 현재 main.tex preamble로는",
           "% 컴파일되지 않는다. 영문화 시 캡션과 머리글만 교체하면 된다.",
           "\\begin{table}[!t]", "\\centering",
           f"\\caption{{{CAPTION_KO}}}", "\\label{tab:padvsdevice}",
           "\\begin{tabular}{lrrrrr}", "\\toprule",
           "격자 & $N$ & $p_{\\mathrm{gap}}$ & $p_{\\mathrm{no\\,gap}}$ "
           "& $\\Delta p$ & device time 비 \\\\",
           "\\midrule"]
    prev = None
    for r in rs:
        if prev is not None and r["grid"] != prev:
            out.append("\\midrule")
        prev = r["grid"]
        g = "\\{" + ", ".join(str(x) for x in r["grid"]) + "\\}"
        if r["dagger"]:
            g += "$^{\\dagger}$"
        nums = [str(r["N"]), f"{r['p_gap']:.3f}", f"{r['p_nogap']:.3f}",
                f"{r['delta_p']:+.3f}", f"{r['device_ratio_printed']:.2f}"]
        if r["delta_p"] > 0 and r["device_ratio_printed"] > 1.0:
            # \textbf has no effect inside math mode, so the numerals are bolded
            # with \mathbf and only the text cell with \textbf.
            vals = [f"\\textbf{{{g}}}"] + [f"$\\mathbf{{{n}}}$" for n in nums]
        else:
            vals = [g] + [f"${n}$" for n in nums]
        out.append(" & ".join(vals) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "",
            "\\vspace{2pt}",
            "{\\footnotesize $^{\\dagger}$" + NOTE_KO[2:] + "}",
            "\\end{table}"]
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    import os
    os.chdir(REPO)

    rs = rows()
    print("=" * 78)
    print("대조 — 재계산 대 기존 기록 (padding 7행 + device time 비 11행)")
    print("=" * 78)
    for line in verify(rs):
        print(line)
    aligned = sum(1 for r in rs if r["aligned"])
    print(f"\n  padding 정렬 {aligned}/{len(rs)}행 일치, "
          f"미정렬 {len(rs) - aligned}행은 합산 단위가 달라 직접 대조 대상이 아니다.")
    print(f"  device time 비 {len(rs)}/{len(rs)}행 일치.")

    rev = [r for r in rs if r["delta_p"] > 0 and r["device_ratio_printed"] > 1.0]
    print(f"\n  반전 행(Δp > 0 이면서 비 > 1): {len(rev)}/{len(rs)} — "
          + ", ".join(f"{grid_label(r['grid'])} N={r['N']}" for r in rev))
    print(f"  비 > 1인 행: {sum(1 for r in rs if r['device_ratio_printed'] > 1.0)}/{len(rs)}")

    md, tex = markdown(rs), latex(rs)
    print("\n" + md)
    if args.write:
        (HERE / "table_3_1.md").write_text(md)
        (HERE / "table_3_1.tex").write_text(tex)
        print(f"기록: {HERE / 'table_3_1.md'}\n기록: {HERE / 'table_3_1.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
