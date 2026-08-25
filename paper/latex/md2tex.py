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
    "①": "Reuse of a completed prefix is all-or-nothing, and the threshold counts requests rather "
         "than tokens. Measured on the layer-2 pool of this artifact (eight outer slots of 8{,}192 "
         "tokens, FIFO) with 2{,}000-token requests, where reuse survives six background arrivals "
         "and disappears at the seventh, reproduced identically in 12 of 12 trials. The grey step "
         "is the upper-layer metric, which keeps reporting hits after the tensors are gone; the "
         "dashed steps are an ablation (model, not measurement) replacing FIFO with "
         "block-granular LRU, under which the threshold becomes size-dependent.",
    "②": "Whether a tool gap helps or hurts is decided by where the offered concurrency falls on "
         "the compiled grid, and the effect changes sign. Pooled utilization ratio "
         "(agentic/conventional) at an admission ceiling of eight; the square series is the same "
         "workload, seed, model and slot count after a recompile that added one rung, which is "
         "what makes the attribution causal rather than correlational. The flat line at 1.0000 is "
         "an ablation on a continuous grid (model).",
    "③": "Prefill is charged to every concurrent session, and a cost model that omits it is biased "
         "in a way that grows with concurrency. Predicted over measured inter-token-latency sum "
         "for both arms; hollow markers omit the serialisation term and filled markers include "
         "it, on this hardware and model.",
    "④": "The model predicts rather than merely reproduces. Predicted against measured ratio; "
         "every blue, orange and red point was committed to the repository before the "
         "corresponding measurement ran. The band is the $\\pm$0.03 agreement region. Grey "
         "points are in-sample reproduction and are not evidence of prediction.",
    "⑤": "Most of the reachable headroom is coordination rather than knowledge. Each bar splits "
         "the offline bound into what omniscient but independently deciding sessions recover and "
         "what only joint scheduling recovers; the number above each bar is the latter's share, "
         "median 60\\%. Computed on the measured tool-latency workload at three budgets and three "
         "concurrencies.",
    "⑥": "The published estimator misses the accuracy threshold that would make return-time "
         "information usable, and more data does not close the gap. Converged error standard "
         "deviation per tool and in aggregate, log axis; the green band is the accuracy threshold "
         "derived for the synthetic gap law, which is the only workload for which such a "
         "threshold is definable.",
    "⑦": "A recompile is cheap enough to treat as a configuration choice, and its cost is "
         "predictable. Wall-clock against the number of compiled graphs; the dashed line is a "
         "model fitted to the two square points alone, and the circles are the later observations "
         "that tested it. Qwen3-4B at a sequence length of 8{,}192 on four devices.",
    "⑧": "A configuration chosen without any device measurement recovers device time, and the "
         "source of the gain is conditional rather than fixed. Bars are channel A$'$, hollow "
         "circles channel B, crosses the predictions committed before measurement; the lighter "
         "portion of each right-hand bar is what grid alignment adds on top of pool size. At "
         "N=8 the pool dominates; at N=6 on a fresh seed the baseline already reuses 17 of 18, so "
         "almost nothing is left for the pool to buy.",
    "⑨": "The gain from a larger KV pool ends where the survival rate saturates, at one third of "
         "what the device can physically hold. Upper panel is device time against "
         "batch\\_size with the grid held at $(1,4,6,8,10,B)$ so that only the top rung changes; "
         "lower panel is layer-2 survival on the same axis. The vertical dashed line is the KV "
         "ceiling extrapolated from a three-point fit of device memory, not a measurement. The "
         "circled point is the one cell whose survival had not yet saturated, and the only one "
         "where a larger pool still bought anything. Concurrency of ten and below.",
}


def _ascii(t: str) -> str:
    """Fold a comment to ASCII.

    A published TeX source is read as well as compiled, so a stray en dash in a
    comment is internal text leaking into a reader-facing package.
    """
    for a, b in (("\u2013", "-"), ("\u2014", "-"), ("\u00b7", ","), ("\u2019", "'")):
        t = t.replace(a, b)
    return "".join(c if ord(c) < 128 else "?" for c in t)


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
                 ("∼", "$\\sim$"), ("½", "$1/2$"), ("°", "$^\\circ$"), ("…", "\\ldots{}")):
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


CITEKEY = re.compile(r"\[@([A-Za-z0-9_,;@\s]+)\]")


def inline(t: str) -> str:
    """Escape, then restore the markup spans that were written as markdown."""
    t = crossrefs(t)
    t = CITEKEY.sub(lambda m: "\x00CITE\x01"
                    + ",".join(k.strip().lstrip("@") for k in m.group(1).split(";")) + "\x02", t)
    t = re.sub(r"Section~\\ref\{sec:(\d\d)\}", lambda m: "\x00REF\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"\^([a-z])\^", lambda m: "\x00SUP" + m.group(1) + "\x03", t)
    def _code(m):
        body = m.group(1)
        if len(body) > 24:
            body = re.sub(r"([/_.])", lambda c: c.group(1) + "\x04", body)
        return "\x00CODE\x01" + body + "\x02"

    t = re.sub(r"`([^`]+)`", _code, t)
    t = re.sub(r"\*\*([^*]+)\*\*", lambda m: "\x00BF\x01" + m.group(1) + "\x02", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: "\x00IT\x01" + m.group(1) + "\x02", t)
    t = esc(t)
    t = t.replace("\x00CODE\x01", "\\texttt{").replace("\x00BF\x01", "\\textbf{")
    t = re.sub(r"\x00SUP(.)\x03", lambda m: "$^{\\mathrm{" + m.group(1) + "}}$", t)
    t = t.replace("\x00IT\x01", "\\emph{").replace("\x00CITE\x01", "\\cite{").replace("\x02", "}")
    t = re.sub(r"\x00REF\x01(\d\d)\}", lambda m: "Section~\\ref{sec:" + m.group(1) + "}", t)
    t = t.replace("\x04", "\\allowbreak{}")
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
    tablecap: list[str] = []
    tablecols: list[str] = []
    tablenote: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if s.startswith("<!--") and s.endswith("-->"):
            note = s[4:-3].strip()
            if note.startswith(("편집 주석", "NEEDS-EVIDENCE")):
                i += 1          # working aid: never reaches the manuscript
                continue
            if note.startswith("TABLECOLS:"):
                tablecols.append(note[10:].strip())
            elif note.startswith("TABLENOTE:"):
                tablenote.append(note[10:].strip())
            elif note.startswith("TABLE:"):
                tablecap.append(inline(note[6:].strip()))
            else:
                out.append("% " + note)
            i += 1
            continue
        m = re.match(r"^(#+)\s*(.*)$", s)
        if m:
            level, title = len(m.group(1)), m.group(2)
            title = re.sub(rf"^[{CIRCLED}]\s*", "", title)
            title = re.sub(r"^\d+(\.\d+)*\s+", "", title)
            # Under IEEEtran's \appendices each appendix is a \section, so the
            # appendix file's heading levels shift by one.
            if path.stem.endswith("appendices"):
                if level == 1:
                    i += 1
                    continue
                title = re.sub(r"^Appendix [A-Z]:\s*", "", title)
                cmd = {2: "section", 3: "subsection"}.get(level, "subsubsection")
                out += ["", f"\\{cmd}{{{inline(title)}}}"]
                i += 1
                continue
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
            cap = tablecap.pop() if tablecap else "TODO caption"
            cols = tablecols.pop() if tablecols else None
            note_row = tablenote.pop() if tablenote else None
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [re.sub(r"\s*<!--.*?-->", "", c).strip()
                         for c in lines[i].strip()[1:-1].split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                n = len(rows[0])
                # A fixed column spec plus \footnotesize is how a wide table is
                # made to fit an IEEE column; without it the cells overrun.
                spec = cols or ("l" * n)
                out += ["", "\\begin{table}[t]", "  \\centering",
                        f"  \\caption{{{cap}}}"]
                if cols:
                    out.append("  \\footnotesize")
                out += [f"  \\begin{{tabular}}{{{spec}}}", "    \\toprule"]
                out.append("    " + " & ".join(inline(c) for c in rows[0]) + " \\\\")
                out.append("    \\midrule")
                for r in rows[1:]:
                    r = (r + [""] * n)[:n]
                    out.append("    " + " & ".join(inline(c) for c in r) + " \\\\")
                out.append("    \\bottomrule")
                out.append("  \\end{tabular}")
                if note_row:
                    out.append(f"  \\\\[2pt]{{\\footnotesize {note_row}}}")
                out += ["\\end{table}", ""]
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
                notes = [" ".join(x.split()) for x in re.findall(r"<!--(.*?)-->", raw)]
                out.append("  \\item " + inline(re.sub(r"\s*<!--.*?-->", "", raw).strip()))
                for note in notes:
                    if note.startswith("CLAIMS"):
                        out.append("  % " + _ascii(note))
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
            note = " ".join(note.split())
            if note.startswith("CLAIMS"):
                out.append("% " + _ascii(note))
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
