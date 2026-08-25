#!/usr/bin/env python3
"""Convert the markdown draft into LaTeX section files.

The draft in ``paper/draft/`` is the editable source; this produces a
mechanical first pass of ``paper/latex/sections/*.tex`` from it. The output is
meant to be polished by hand -- it is a transport, not a typesetter -- and
regenerating overwrites that polish, so once hand-editing starts, stop running
this.

Handled: headings, bold/italic/code spans, ``<!-- CLAIMS -->`` comments (kept
as LaTeX comments so the evidence trail survives into the manuscript), pipe
tables, and the ``**Figure X.**`` markers, which become float environments
pointing at the PDFs in ``paper/figures/pdf/``.

    env -u PYTHONPATH python3 paper/latex/md2tex.py
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE.parent / "draft"
OUT = HERE / "sections"

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
FIGFILE = {
    "①": "fig1_survival_cliff", "②": "fig2_grid_alignment", "③": "fig3_prefill_tax",
    "④": "fig4_simulator_validation", "⑤": "fig5_headroom_decomposition",
    "⑥": "fig6_predictor_error", "⑦": "fig7_compile_cost", "⑧": "fig8_final_result",
    "⑨": "fig9_batch_saturation",
}
FIGCAP = {
    "①": "Reuse cliff: the threshold counts requests, not tokens.",
    "②": "Grid alignment sets the sign of the gap effect, established by intervention.",
    "③": "Prefill is a system cost; adding its term removes the concurrency-dependent bias.",
    "④": "Predictive power of the uncalibrated simulator.",
    "⑤": "Most of the headroom is coordination, and knowledge cannot buy it.",
    "⑥": "The predictor misses the accuracy threshold, and more samples do not help.",
    "⑦": "A recompile costs seven minutes; a two-point cost model holds at the fifth point.",
    "⑧": "Compile configuration recovers device time, and the source is conditional.",
    "⑨": "The batch\\_size gain ends where the survival rate saturates.",
}


def esc(t: str) -> str:
    """Escape TeX specials in running text. Order matters: backslash first."""
    t = t.replace("\\", "\\textbackslash{}")
    for a, b in (("&", "\\&"), ("%", "\\%"), ("$", "\\$"), ("#", "\\#"),
                 ("_", "\\_"), ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"),
                 ("^", "\\textasciicircum{}")):
        t = t.replace(a, b)
    for a, b in (("—", "---"), ("–", "--"), ("‘", "`"), ("’", "'"),
                 ("“", "``"), ("”", "''"), ("×", "$\\times$"), ("≤", "$\\leq$"),
                 ("≥", "$\\geq$"), ("→", "$\\rightarrow$"), ("−", "$-$"), ("·", "$\\cdot$"),
                 ("±", "$\\pm$"), ("∈", "$\\in$"), ("′", "$'$"), ("≈", "$\\approx$"),
                 ("∼", "$\\sim$"), ("½", "$1/2$"), ("°", "$^\\circ$")):
        t = t.replace(a, b)
    return t


SECREF = {c: f"{i + 1:02d}" for i, c in enumerate(CIRCLED)}


def crossrefs(t: str) -> str:
    """Circled numerals and section marks become \\ref, not glyphs.

    T1-encoded fonts have no circled numerals, and a section mark followed by a
    hand-written number would go stale the moment a section moves.
    """
    t = re.sub(rf"(?:Section\s*|\u00a7)?([{CIRCLED}])",
               lambda m: "Section~\\ref{sec:" + SECREF[m.group(1)] + "}", t)
    t = re.sub(r"\u00a7(\d+)(?:\.\d+)*", lambda m: "Section~\\ref{sec:0" + m.group(1) + "}", t)
    return t


def inline(t: str) -> str:
    """Escape, then restore the markup spans that were written as markdown."""
    t = crossrefs(t)
    t = re.sub(r"Section~\\ref\{sec:(\d\d)\}", lambda m: "\x00REF\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"`([^`]+)`", lambda m: "\x00CODE\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"\*\*([^*]+)\*\*", lambda m: "\x00BF\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: "\x00IT\x01" + m.group(1) + "\x02", t)
    t = esc(t)
    t = t.replace("\x00CODE\x01", "\\texttt{").replace("\x00BF\x01", "\\textbf{")
    t = t.replace("\x00IT\x01", "\\emph{").replace("\x02", "}")
    t = re.sub(r"\x00REF\x01(\d\d)\}", lambda m: "Section~\\ref{sec:" + m.group(1) + "}", t)
    return t


def figure_block(sym: str) -> list[str]:
    return ["", "\\begin{figure}[t]", "  \\centering",
            f"  \\includegraphics[width=\\columnwidth]{{{FIGFILE[sym]}}}",
            f"  \\caption{{{FIGCAP[sym]}}}",
            f"  \\label{{fig:{FIGFILE[sym].split('_')[0]}}}",
            "\\end{figure}", ""]


def convert(path: Path) -> str:
    out: list[str] = [f"%% Generated from {path.relative_to(HERE.parents[1])} by md2tex.py.",
                      "%% Mechanical first pass -- polish by hand, then stop regenerating.", ""]
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if s.startswith("<!--") and s.endswith("-->"):
            out.append("% " + s[4:-3].strip())
            i += 1
            continue
        m = re.match(r"^(#+)\s*(.*)$", s)
        if m:
            level, title = len(m.group(1)), m.group(2)
            title = re.sub(rf"^[{CIRCLED}]\s*", "", title)
            title = re.sub(r"^\d+(\.\d+)*\s+", "", title)
            cmd = {1: "section", 2: "subsection"}.get(level, "subsubsection")
            out += ["", f"\\{cmd}{{{inline(title)}}}"]
            if level == 1:
                out.append("\\label{sec:%s}" % path.stem[:2])
            i += 1
            continue
        mf = re.match(rf"^\*\*Figure ([{CIRCLED}])\.\*\*$", s)
        if mf:
            out += figure_block(mf.group(1))
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [re.sub(r"\s*<!--.*?-->", "", c).strip()
                         for c in lines[i].strip()[1:-1].split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                n = len(rows[0])
                out += ["", "\\begin{table}[t]", "  \\centering",
                        "  \\caption{TODO caption}",
                        f"  \\begin{{tabular}}{{{'l' * n}}}", "    \\toprule"]
                out.append("    " + " & ".join(inline(c) for c in rows[0]) + " \\\\")
                out.append("    \\midrule")
                for r in rows[1:]:
                    r = (r + [""] * n)[:n]
                    out.append("    " + " & ".join(inline(c) for c in r) + " \\\\")
                out += ["    \\bottomrule", "  \\end{tabular}", "\\end{table}", ""]
            continue
        if not s:
            out.append("")
            i += 1
            continue
        mnum = re.match(r"^(\d+)\.\s+(.*)$", s)
        mbul = re.match(r"^[-*]\s+(.*)$", s)
        if mnum or mbul:
            env = "enumerate" if mnum else "itemize"
            out += ["", f"\\begin{{{env}}}"]
            while i < len(lines):
                t = lines[i].strip()
                mm = re.match(r"^(\d+)\.\s+(.*)$", t) if mnum else re.match(r"^[-*]\s+(.*)$", t)
                if not mm:
                    break
                raw = mm.group(2)
                notes = [x.strip() for x in re.findall(r"<!--(.*?)-->", raw)]
                out.append("  \\item " + inline(re.sub(r"\s*<!--.*?-->", "", raw).strip()))
                for note in notes:
                    out.append("  % " + " ".join(note.split()))
                i += 1
            out += [f"\\end{{{env}}}", ""]
            continue
        # Inline evidence comments are pulled out of the sentence and re-emitted
        # after it: a LaTeX comment runs to end of line, so leaving one mid-text
        # would swallow the rest of the paragraph.
        notes = [m.strip() for m in re.findall(r"<!--(.*?)-->", s)]
        body = re.sub(r"<!--.*?-->", "", s).strip()
        body = re.sub(r"\s+([.,;:])", r"\1", body)
        body = re.sub(r"\s{2,}", " ", body)
        if body:
            out.append(inline(body))
        for note in notes:
            out.append("% " + " ".join(note.split()))
        i += 1
    return "\n".join(out).replace("\n\n\n", "\n\n").rstrip("\n") + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    abstract = (HERE.parent / "abstract_arxiv.txt").read_text().strip()
    (OUT / "00_abstract.tex").write_text(
        "%% From paper/abstract_arxiv.txt (1,876 chars, within the arXiv 1,920 cap).\n"
        + "\n\n".join(inline(p) for p in abstract.split("\n\n")) + "\n")
    n = 1
    for f in sorted(DRAFT.glob("[0-9]*.md")):
        (OUT / (f.stem + ".tex")).write_text(convert(f))
        n += 1
    print(f"wrote {n} files to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
