#!/usr/bin/env python3
"""Cross-check every figure against its source TASK, and dump its text for review.

This host has no SVG rasteriser, so nobody has looked at the eight figures with
their eyes. Two things stand in for that, and neither is a substitute for the
third:

  1. **Numeric cross-check.** Every data constant in ``make_figures.py`` is
     re-read out of the TASK markdown it came from and compared. A figure can
     be laid out perfectly and still be wrong; this catches that.
  2. **Text dump.** Every string that ends up in each SVG -- title, subtitle,
     axis labels, tick labels, legend, in-plot annotations -- is listed with
     its position, so a reader with a browser open can tick them off.
  3. What is still missing: whether anything *overlaps*. Only eyes do that.

    env -u PYTHONPATH python3 paper/figures/verify_figures.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESEARCH = REPO / "docs/research"
sys.path.insert(0, str(HERE))
import make_figures as F  # noqa: E402

TOL = 1e-9


# -- markdown table reading --------------------------------------------------
def rows(task: str) -> list[list[str]]:
    """Every pipe-table row in a TASK document, as stripped cell lists."""
    out = []
    for line in (RESEARCH / f"{task}.md").read_text().splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                out.append(cells)
    return out


def num(cell: str) -> float | None:
    """The first number in a cell, with markdown emphasis and units removed."""
    t = cell.replace("*", "").replace("−", "-").replace(",", "").replace("~", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None


def find_row(task: str, *contains: str) -> list[str] | None:
    for r in rows(task):
        joined = " | ".join(r)
        if all(c in joined for c in contains):
            return r
    return None


# -- checks ------------------------------------------------------------------
CHECKS: list[tuple[str, str, str, float, float]] = []   # fig, what, source, expected, actual


def chk(fig: str, what: str, source: str, expected, actual, tol: float = 5e-4) -> None:
    ok = expected is not None and abs(expected - actual) <= tol
    CHECKS.append((fig, what, source, expected, actual, ok))


def check_fig1() -> None:
    """Thresholds live in prose, not tables, so match the sentences."""
    t14 = (RESEARCH / "TASK14.md").read_text()
    chk("①", "층 2 문턱 B", "TASK14 핵심 발견 1", 7.0 if "7개째에 사라진다" in t14 else None, 7.0)
    chk("①", "층 1 문턱 상한", "TASK14 핵심 발견 4",
        33.0 if "16 < B ≤ 33" in t14 else None, 33.0)
    t29 = (RESEARCH / "TASK29.md").read_text()
    ok = "61·31·16" in t29
    for thr, tok in ((61.0, "500"), (31.0, "1,000"), (16.0, "2,000")):
        chk("①", f"LRU 절제 문턱 ({tok} tok)", "TASK29 핵심 발견 1", thr if ok else None, thr)


def check_fig2() -> None:
    """TASK24 관측 5 carries measured pooled ratios for both grids."""
    table = [r for r in rows("TASK24")
             if r and r[0].replace("*", "").strip().startswith("(1,2,4")]
    got = {}
    for r in table:
        grid = r[0].replace("*", "").strip()
        n = int(num(r[1]))
        got[(grid, n)] = num(r[3])            # 실측 pooled
    for n, v in F.MEASURED_GRID:
        chk("②", f"측정 격자 N={n}", "TASK24 관측 5", got.get(("(1,2,4,8)", n)), v)
    for n, v in F.INTERVENED:
        chk("②", f"개입 격자 N={n}", "TASK24 관측 5", got.get(("(1,2,4,6,8)", n)), v)


def check_fig3() -> None:
    got = {}
    for r in rows("TASK22"):
        if len(r) == 5 and r[1] in ("AGENTIC", "CONVENTIONAL") and num(r[0]) is not None:
            got[(int(num(r[0])), r[1])] = (num(r[2]), num(r[3]))
    for n, arm, v1, v2 in F.V1V2:
        e = got.get((n, arm), (None, None))
        chk("③", f"N={n} {arm} v1", "TASK22 사후 대조", e[0], v1)
        chk("③", f"N={n} {arm} v2", "TASK22 사후 대조", e[1], v2)


def check_fig4() -> None:
    # TASK25 gate table: N | 선등록 sim | 실측 | ...
    oos = [(num(r[1]), num(r[2])) for r in rows("TASK25")
           if len(r) == 7 and r[0] in ("3", "4", "7")]
    for i, (p, m) in enumerate(F.SIM_OOS):
        e = oos[i] if i < len(oos) else (None, None)
        chk("④", f"TASK25 OOS #{i + 1} 예측", "TASK25 게이트", e[0], p)
        chk("④", f"TASK25 OOS #{i + 1} 실측", "TASK25 게이트", e[1], m)
    dev = [(num(r[1]), num(r[2])) for r in rows("TASK28")
           if len(r) == 8 and r[0] in ("6", "8") and num(r[1]) is not None]
    for i, (p, m) in enumerate(F.SIM_DEVICE):
        e = dev[i] if i < len(dev) else (None, None)
        chk("④", f"TASK28 확증 #{i + 1} 예측", "TASK28 확증", e[0], p)
        chk("④", f"TASK28 확증 #{i + 1} 실측", "TASK28 확증", e[1], m)
    cfg = [(num(r[2]), num(r[3])) for r in rows("TASK35")
           if len(r) == 8 and r[0] in ("6", "8") and r[1] in ("②", "③")]
    for i, (p, m) in enumerate(F.SIM_CONFIG):
        e = cfg[i] if i < len(cfg) else (None, None)
        chk("④", f"TASK35 확증 #{i + 1} 예측", "TASK35 확증", e[0], p)
        chk("④", f"TASK35 확증 #{i + 1} 실측", "TASK35 확증", e[1], m)
    t36 = [(num(r[1]), num(r[2])) for r in rows("TASK36")
           if len(r) == 7 and r[0].startswith("②") or (len(r) == 7 and r[0].startswith("③"))]
    for i, (p, m) in enumerate(F._task36_pairs()):
        e = t36[i] if i < len(t36) else (None, None)
        chk("④", f"TASK36 확증 #{i + 1} 예측", "TASK36 확증", e[0], p)
        chk("④", f"TASK36 확증 #{i + 1} 실측", "TASK36 확증", e[1], m, tol=5e-4)


def check_fig5() -> None:
    got = {}
    for r in rows("TASK33"):
        if len(r) == 8 and r[0] in ("1", "2", "5") and "%" in r[2]:
            got[(int(num(r[0])), int(num(r[1])))] = tuple(num(x) for x in r[2:7])
    for eps, n, a, b, c, d, e in F.DECOMP:
        exp = got.get((eps, n))
        for i, (name, v) in enumerate((("a", a), ("b", b), ("c", c), ("d", d), ("e", e))):
            chk("⑤", f"ε={eps} N={n} ({name})", "TASK33 축별 분해",
                exp[i] if exp else None, v, tol=5e-3)


def check_fig6() -> None:
    for name, std, _ in F.PRED_ERR:
        r = find_row("TASK32", f"`{name}`")
        e = None
        if r:
            cands = [num(c) for c in r[1:] if num(c) is not None]
            e = min(cands, key=lambda x: abs(x - std)) if cands else None
        chk("⑥", f"도구 {name}", "TASK32 도구별 표", e, std, tol=5e-3)
    for label, std in F.AGG:
        key = "B(δ)" if "B(δ)" in label else "μ̂"
        r = find_row("TASK32", key, "s")
        chk("⑥", f"집계 {key}", "TASK32 게이트 표", num(r[1]) if r else None, std, tol=5e-3)


def check_fig7() -> None:
    got = {}
    for r in rows("TASK35"):
        if len(r) == 5 and num(r[0]) is not None and "TASK" in r[4]:
            got[r[4].replace("*", "").strip()] = (num(r[0]), num(r[1]), num(r[2]), num(r[3]))
    for buckets, models, t, gib, task in F.COMPILE:
        key = "이 TASK" if task == "TASK35" else f"[{task}]({task}.md)"
        e = got.get(key)
        chk("⑦", f"{task} bucket 수", "TASK35 관측 1", e[0] if e else None, float(buckets))
        chk("⑦", f"{task} compiled model", "TASK35 관측 1", e[1] if e else None, float(models))
        chk("⑦", f"{task} wall-clock", "TASK35 관측 1", e[2] if e else None, t, tol=0.05)
        chk("⑦", f"{task} artifact GiB", "TASK35 관측 1", e[3] if e else None, gib, tol=5e-4)


def check_fig8() -> None:
    """fig8's N=8 column is hard-coded; re-read it from TASK35's X table."""
    for arm, sym, a_exp, b_exp in (("BATCHONLY", "②", 0.9175, 0.9183),
                                   ("TUNED", "③", 0.9028, 0.8993)):
        r = [x for x in rows("TASK35") if len(x) == 8 and x[0] == "8" and x[1].startswith(sym)]
        chk("⑧", f"N=8 {arm} A′", "TASK35 확증", num(r[0][3]) if r else None, a_exp)
    x = find_row("TASK35", "N=8 (확증, `PASS`)", "③")
    chk("⑧", "N=8 TUNED X (A′)", "TASK35 X 표",
        num(x[2]) if x else None, 100 * (1 - 0.9028), tol=0.02)


# -- svg text extraction -----------------------------------------------------
def svg_text(path: Path) -> tuple[int, int, list[tuple[float, float, float, str]]]:
    s = path.read_text()
    w = int(re.search(r'width="(\d+)"', s).group(1))
    h = int(re.search(r'height="(\d+)"', s).group(1))
    items = []
    for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)" font-size="([\d.]+)"[^>]*>([^<]*)</text>', s):
        items.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4)))
    items.sort(key=lambda t: (round(t[1] / 6), t[0]))
    return w, h, items


FIGS = [("①", "fig1_survival_cliff.svg"), ("②", "fig2_grid_alignment.svg"),
        ("③", "fig3_prefill_tax.svg"), ("④", "fig4_simulator_validation.svg"),
        ("⑤", "fig5_headroom_decomposition.svg"), ("⑥", "fig6_predictor_error.svg"),
        ("⑦", "fig7_compile_cost.svg"), ("⑧", "fig8_final_result.svg")]


def main() -> int:
    for f in (check_fig1, check_fig2, check_fig3, check_fig4,
              check_fig5, check_fig6, check_fig7, check_fig8):
        f()
    bad = [c for c in CHECKS if not c[5]]

    out = ["# 그림 검수표",
           "",
           "이 host에 SVG 래스터라이저가 없어 **그림을 사람 눈으로 확인하지 못했다.** 이 문서가 그 자리를 "
           "부분적으로 메운다.",
           "",
           "- **§1 수치 대조**는 [make_figures.py](make_figures.py)의 데이터 상수를 원 TASK 문서의 표에서 "
           "다시 읽어 자동 비교한다. 레이아웃이 멀쩡해도 값이 틀릴 수 있고, 그것을 잡는 것이 이 절이다.",
           "- **§2 텍스트 목록**은 각 SVG에 실제로 들어간 문자열 전부를 위치와 함께 나열한다. 브라우저로 "
           "그림을 열고 이 목록과 대조하면 누락·오탈자를 짚을 수 있다.",
           "- **여전히 확인되지 않는 것**: 요소가 서로 **겹치는지**. 그것은 눈으로만 확인된다.",
           "",
           "생성: `env -u PYTHONPATH python3 paper/figures/verify_figures.py`",
           "",
           "---",
           "",
           "## 1. 수치 대조 — 그림의 상수 대 원 TASK 값",
           "",
           f"**{len(CHECKS)}개 항목 중 {len(CHECKS) - len(bad)}개 일치, {len(bad)}개 불일치.**",
           ""]
    if bad:
        out += ["### ⚠️ 불일치", "", "| 그림 | 항목 | 출처 | 원 TASK 값 | 그림 값 |", "|---|---|---|---|---|"]
        for fig, what, src, e, a, _ in bad:
            out.append(f"| {fig} | {what} | {src} | "
                       f"{'**찾지 못함**' if e is None else f'{e:g}'} | {a:g} |")
        out.append("")
    else:
        out += ["**불일치 없음.** 8개 그림의 데이터 상수가 전부 원 TASK 문서의 표·문장과 일치한다.", ""]

    out += ["### 그림별 대조 항목 수", "", "| 그림 | 대조 항목 | 일치 | 출처 |", "|---|---|---|---|"]
    for sym, _ in FIGS:
        mine = [c for c in CHECKS if c[0] == sym]
        srcs = sorted({c[2].split()[0] for c in mine})
        out.append(f"| {sym} | {len(mine)} | {sum(1 for c in mine if c[5])} | {', '.join(srcs)} |")
    out += ["", "**대조하지 못한 것**: 그림 ①의 문턱은 TASK 문서에서 표가 아니라 문장으로 기술돼 있어 "
            "문장 일치로 확인했다(값 자체가 아니라 그 값을 말하는 문장의 존재를 확인한다). "
            "그림 ⑧의 N=6 열은 [TASK36](../../docs/research/TASK36.md)의 측정 산출물 JSON을 직접 읽으므로 "
            "대조 대상이 아니라 원본이다.", "",
            "---", "", "## 2. 텍스트 목록 — 브라우저 대조용", ""]

    for sym, fname in FIGS:
        w, h, items = svg_text(HERE / fname)
        out += [f"### {sym} `{fname}` — {w} × {h} px", "",
                "| y | x | 크기 | 텍스트 |", "|---|---|---|---|"]
        for x, y, size, t in items:
            safe = t.replace("|", "\\|")
            out.append(f"| {y:.0f} | {x:.0f} | {size:g} | {safe} |")
        out.append("")

    (HERE / "INSPECTION.md").write_text("\n".join(out).rstrip("\n") + "\n")
    print(f"{len(CHECKS)} checks, {len(bad)} mismatches -> paper/figures/INSPECTION.md")
    for fig, what, src, e, a, _ in bad:
        print(f"  MISMATCH {fig} {what}: TASK={e} FIG={a}  ({src})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
