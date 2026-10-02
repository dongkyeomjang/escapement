#!/usr/bin/env python3
"""Paper figures F_a, F_b, F_d (directive 14) from the committed figure CSVs.

Input: ``results/tables/figures/{F_a_survival,F_b_reuse_ratio_vs_N,F_d_applicability}.csv``
only -- nothing is recomputed from other artifacts. Output: vector PDF in
``results/tables/figures/pdf/`` (17.5 cm = 496 pt wide), drawn with the
repository's dependency-free plotter ``paper/figures/svgplot.py`` (matplotlib
is not installed on this host): DejaVuSans is embedded, the PDF carries no
creation date, so a rerun gives byte-identical files.

Okabe-Ito colours; predictors differ by line style, observations by markers,
configurations by colour AND marker, so nothing is told by colour alone.

CSV column -> visual element
============================

F_a_survival.csv (two panels, shared y axis 0-2,100 tokens)
  (a) NPU: substrate = NPU.
      * prediction step line: condition = descriptor_v2_prediction, bg_tokens = 2000,
        x = m_background, y = pred_hit_tokens (the four bg_tokens series are identical,
        the cliff is at the same m; one line is drawn).
      * observation markers: condition = outer_fifo_8, x = m_background,
        y = obs_survive_frac x 1,920 -- the CSV gives the NPU observation as a survival
        fraction (0 or 1 for every row); 1,920 is the full-hit token count of the
        prediction rows at m = 0 in the same file. Filled circles.
  (b) GPU: substrate = GPU, conditions (i) and (ii).
      * prediction step lines: x = m_background, y = pred_hit_tokens, line style by
        bg_tokens (500 / 1,000 / 2,000 / 4,000); (i) and (ii) drawn alike (they differ
        only in the generated-token cache, 2,000 vs 2,016 tokens at full hit).
      * observation markers: y = obs_hit_tokens, hollow circles (they sit on the
        predictions: all 60 rows have obs = pred).
      * bg_tokens = 0 rows (m = 0, no background) start every line.

F_b_reuse_ratio_vs_N.csv (2 x 2: rows reuse / cost ratio, columns NPU / GPU)
  reuse panels (metric = reuse, config = BASE):
      * observed: predictor = observed, marker; filled when population starts with
        "blind_confirm" or is "blind_no_information_cell" (cell measured under a
        preregistration), hollow otherwise (exploratory cell). Legend: one
        "preregistered cell" entry. The CSV carries no replicate range for reuse
        (ci_lo/ci_hi empty), so no vertical bars are drawn.
      * Analytical model: predictor = analytic_v1, dashed; drawn lighter where outside
        scope (NPU N >= 12; GPU: every cell, N > max_num_seqs = 8).
      * Simulator: NPU predictor = sim_observed (TASK82) and sim_descriptor (TASK87,
        TASK95, TASK102) -- the original-cost, descriptor-semantics simulator; GPU
        predictor = sim_lru (GTASK11) and sim_lru_price (GTASK20), labelled
        "Simulator (short-context cost)". Solid.
      * Simulator (context-aware cost): predictor = sim_ctxcost (NPU TASK102, GPU
        GTASK20), dash-dot, only at those N. On the GPU it is the main predictor for
        N >= 25 (GTASK20); the short-context simulator line is drawn lighter after N = 24
        in panels (b) and (d), and panel (d) also draws sim_ctxcost per configuration.
      * hollow observed marker = exploratory cell (own legend entry).
      * Null predictor: predictor = null, dotted horizontal line.
      * not drawn: v1.1 (development model), sim_default (legacy semantics), sim_opcost
        and sim_ctxcost_origprefill (TASK95/102 secondary), sim_fifo, dev-set or
        calibrated GPU rows (GTASK13 cell_set, sim_lru_x1.210, sim_lru_mode_dist,
        sim_lru_orig, sim_lru_x1.131).
  cost-ratio panels (metric = ratio_to_BASE):
      * observed median (value) with 95 % CI (ci_lo, ci_hi) per configuration:
        Larger KV = BATCHONLY / POOL (circle), Larger KV + grid = TUNED / POOL+GRID
        (square); DP (one NPU cell, N = 8) is not drawn.
      * Simulator per configuration: same predictor rule as the reuse panels.
      * dashed horizontal line at 1.0.
  shaded band: NPU between N = 10 and 12 ("queue forms"); GPU between N = 24 and 25
  ("saturation").

F_d_applicability.csv (one panel)
  rows config = BASE; x = queue_mean_obs (log axis 0.01-10), y = |reuse_error|.
      * Analytical model (circle): predictor = analytic_v1.
      * Simulator (triangle): predictor = sim_observed (TASK82), sim_descriptor
        (TASK87, TASK95, TASK102), sim_lru (GTASK11).
      * Simulator (context-aware cost) (square): predictor = sim_ctxcost (TASK102).
      * NPU filled, GPU hollow; N written next to each point.
      * GTASK20 cells (N = 25, 28) are excluded: queue_mean_obs is empty there (no
        queue depth was recorded on the GPU for those cells).
      * a dashed vertical line at x = 0.1, no text.

usage: make_paper_figures.py [--out-dir results/tables/figures/pdf]
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIG = REPO / "results/tables/figures"
sys.path.insert(0, str(REPO / "paper/figures"))

import svgplot as SP  # noqa: E402

SP.set_language("en")

W = 496.0                       # 17.5 cm in pt
TICK = 8.0                      # tick label size, pt
LABEL = 9.0                     # axis label size, pt
LEG = 8.0                       # legend text size, pt
INK = "#000000"
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
      "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
      "grey": "#7f7f7f", "light": "#d9d9d9"}
DASH = {"solid": None, "dash": "5 2.5", "dot": "1.2 2", "dashdot": "6 2 1.2 2", "longdash": "9 3"}


def read(name: str) -> list[dict]:
    with open(FIG / name, newline="") as fh:
        return list(csv.DictReader(fh))


# -- drawing helpers on top of svgplot ---------------------------------------------

class Canvas:
    def __init__(self, height: float):
        self.ax = SP.Axes(width=W, height=height, left=0, right=0, top=0, bottom=0)

    def panel(self, x0: float, y0: float, x1: float, y1: float, xlim, ylim) -> SP.Axes:
        """Plot area from (x0, y0) top-left to (x1, y1) bottom-right, in pt."""
        p = SP.Axes(width=W, height=self.ax.height, left=x0, right=W - x1, top=y0,
                    bottom=self.ax.height - y1, xlim=xlim, ylim=ylim)
        p.prims = self.ax.prims          # shared list: everything lands on one page
        return p

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.ax.save_pdf(path)


def frame(p: SP.Axes, *, xticks, yticks, xlab="", ylab="", xfmt=lambda v: f"{v:g}",
          yfmt=lambda v: f"{v:g}", grid=True, ylabel_x=None) -> None:
    if grid:
        for v in yticks:
            p.raw_path([(p.x0, p.py(v)), (p.x1, p.py(v))], color="#ebebeb", width=0.5)
    p.raw_path([(p.x0, p.y1), (p.x0, p.y0), (p.x1, p.y0)], color=INK, width=0.7)
    for v in xticks:
        p.raw_path([(p.px(v), p.y0), (p.px(v), p.y0 + 3)], color=INK, width=0.6)
        p.text(p.px(v), p.y0 + 3 + TICK + 1, xfmt(v), size=TICK, data=False)
    for v in yticks:
        p.raw_path([(p.x0 - 3, p.py(v)), (p.x0, p.py(v))], color=INK, width=0.6)
        p.text(p.x0 - 5, p.py(v) + TICK * 0.35, yfmt(v), size=TICK, anchor="end", data=False)
    if xlab:
        p.text((p.x0 + p.x1) / 2, p.y0 + 3 + TICK + 2 + LABEL + 2, xlab, size=LABEL, data=False)
    if ylab:
        x = ylabel_x if ylabel_x is not None else p.x0 - 30
        p.text(x, (p.y0 + p.y1) / 2, ylab, size=LABEL, data=False, rotate=-90)


def tag(p: SP.Axes, s: str) -> None:
    p.text(p.x0, p.y1 - 5, s, size=LABEL, anchor="start", weight="bold", data=False)


def circle_path(cx: float, cy: float, r: float, n: int = 24) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n + 1)]


def mark(p: SP.Axes, x: float, y: float, *, color: str, shape: str = "o", hollow: bool = False,
         r: float = 2.6, data: bool = True) -> None:
    cx, cy = (p.px(x), p.py(y)) if data else (x, y)
    if shape == "o":
        if hollow:
            p.raw_path(circle_path(cx, cy, r), color=color, width=0.8, closed=True, fill=None)
        else:
            p.add({"k": "circle", "cx": cx, "cy": cy, "r": r, "fill": color, "stroke": color, "sw": 0.8})
    elif shape == "s":
        pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r), (cx - r, cy - r)]
        p.raw_path(pts, color=color, width=0.8, closed=True, fill=None if hollow else color)
    elif shape == "^":
        pts = [(cx, cy - r * 1.15), (cx + r * 1.1, cy + r * 0.8), (cx - r * 1.1, cy + r * 0.8), (cx, cy - r * 1.15)]
        p.raw_path(pts, color=color, width=0.8, closed=True, fill=None if hollow else color)


def poly(p: SP.Axes, pts, *, color: str, style: str = "solid", width: float = 1.1,
         opacity: float = 1.0) -> None:
    if len(pts) >= 2:
        p.line(pts, color=color, width=width, dash=DASH[style], opacity=opacity)


def poly_split(p: SP.Axes, pts, split: float | None, *, color: str, style: str = "solid",
               width: float = 1.1, faded: float = 0.35) -> None:
    """Full opacity up to x = split, lighter from the last point at or before split on."""
    if split is None:
        poly(p, pts, color=color, style=style, width=width)
        return
    head = [pt for pt in pts if pt[0] <= split]
    tail = ([head[-1]] if head else []) + [pt for pt in pts if pt[0] > split]
    poly(p, head, color=color, style=style, width=width)
    poly(p, tail, color=color, style=style, width=width, opacity=faded)


def step(pts: list[tuple[float, float]], x_end: float) -> list[tuple[float, float]]:
    """Post-step path through sampled (x, y): y holds until the next sample."""
    out = []
    for i, (x, y) in enumerate(pts):
        if i:
            out.append((x, pts[i - 1][1]))
        out.append((x, y))
    out.append((x_end, pts[-1][1]))
    return out


def vband(p: SP.Axes, xa: float, xb: float, label: str, *, bottom: bool = False) -> None:
    p.rect_px(p.px(xa), p.y1, p.px(xb) - p.px(xa), p.y0 - p.y1, fill=OI["light"], opacity=0.55)
    y = p.y0 - 4 if bottom else p.y1 + TICK + 1
    p.text((p.px(xa) + p.px(xb)) / 2, y, label, size=TICK, data=False, fill="#555555")


def legend(p: SP.Axes, entries: list[dict], *, x: float, y: float, dy: float = 10.5) -> None:
    """entries: {label, color, style?(line), shape?, hollow?} drawn at absolute (x, y)."""
    for i, e in enumerate(entries):
        yy = y + i * dy
        if e.get("style"):
            p.raw_path([(x, yy), (x + 16, yy)], color=e["color"], width=1.1, dash=DASH[e["style"]])
        if e.get("shape"):
            mark(p, x + 8, yy, color=e["color"], shape=e["shape"], hollow=e.get("hollow", False),
                 data=False)
        p.text(x + 20, yy + LEG * 0.35, e["label"], size=LEG, anchor="start", data=False)


# -- F_a -------------------------------------------------------------------------------

def fig_a(out: Path) -> None:
    rows = read("F_a_survival.csv")
    H = 272.0
    c = Canvas(H)
    ylim, yt = (0, 2100), [0, 500, 1000, 1500, 2000]
    # (a) NPU
    pa = c.panel(52, 22, 236, 168, (0, 50), ylim)
    frame(pa, xticks=[0, 10, 20, 30, 40, 50], yticks=yt, xlab="Background requests m",
          ylab="Reused tokens", ylabel_x=16)
    tag(pa, "(a) NPU")
    pred = sorted((int(r["m_background"]), float(r["pred_hit_tokens"])) for r in rows
                  if r["substrate"] == "NPU" and r["condition"] == "descriptor_v2_prediction"
                  and r["bg_tokens"] == "2000")
    full = dict(pred)[0]
    poly(pa, step(pred, 50), color=OI["blue"], style="solid")
    obs = sorted({(int(r["m_background"]), float(r["obs_survive_frac"]) * full) for r in rows
                  if r["substrate"] == "NPU" and r["condition"] == "outer_fifo_8"})
    for m, y in obs:
        mark(pa, m, y, color=INK, shape="o")
    legend(pa, [{"label": "Model prediction", "color": OI["blue"], "style": "solid"},
                {"label": "Observed", "color": INK, "shape": "o"}], x=pa.x0, y=pa.y0 + 40)
    # (b) GPU
    pb = c.panel(304, 22, 488, 168, (0, 40), ylim)
    frame(pb, xticks=[0, 10, 20, 30, 40], yticks=yt, xlab="Background requests m",
          ylab="Reused tokens", ylabel_x=268)
    tag(pb, "(b) GPU")
    styles = {"500": ("solid", OI["vermillion"]), "1000": ("dash", OI["blue"]),
              "2000": ("dashdot", OI["green"]), "4000": ("dot", OI["purple"])}
    for cond in ("(i)", "(ii)"):
        start = [(0, float(r["pred_hit_tokens"])) for r in rows
                 if r["substrate"] == "GPU" and r["condition"] == cond and r["bg_tokens"] == "0"]
        for bg, (st, col) in styles.items():
            pts = sorted({(int(r["m_background"]), float(r["pred_hit_tokens"])) for r in rows
                          if r["substrate"] == "GPU" and r["condition"] == cond and r["bg_tokens"] == bg})
            poly(pb, step(start + pts, 40), color=col, style=st)
    for r in rows:
        if r["substrate"] == "GPU":
            col = styles.get(r["bg_tokens"], (None, INK))[1]
            mark(pb, int(r["m_background"]), float(r["obs_hit_tokens"]), color=col, shape="o", hollow=True, r=2.8)
    ents = [{"label": f"Prediction, {int(bg):,}-token background", "color": col, "style": st}
            for bg, (st, col) in styles.items()]
    legend(pb, ents + [{"label": "Observed (= prediction, 60/60)", "color": INK, "shape": "o", "hollow": True}],
           x=pb.x0, y=pb.y0 + 40)
    c.save(out / "F_a_survival.pdf")


# -- F_b -------------------------------------------------------------------------------

NPU_SIM = {"TASK82": "sim_observed", "TASK87": "sim_descriptor", "TASK95": "sim_descriptor",
           "TASK102": "sim_descriptor"}
GPU_SIM = {"GTASK11": "sim_lru", "GTASK20": "sim_lru_price"}
CONF = {"NPU": {"BATCHONLY": ("Larger KV", OI["blue"], "o", "solid"),
                "TUNED": ("Larger KV + grid", OI["vermillion"], "s", "dash")},
        "GPU": {"POOL": ("Larger KV", OI["blue"], "o", "solid"),
                "POOL+GRID": ("Larger KV + grid", OI["vermillion"], "s", "dash")}}


def series(rows, sub, metric, config, pred_rule) -> list[tuple[float, float]]:
    out = []
    for r in rows:
        if r["substrate"] != sub or r["metric"] != metric or r["config"] != config:
            continue
        if callable(pred_rule):
            ok = pred_rule(r)
        else:
            ok = r["predictor"] == pred_rule
        if ok and r["value"] != "":
            out.append((float(r["N"]), float(r["value"])))
    return sorted(out)


def fig_b(out: Path) -> None:
    rows = [r for r in read("F_b_reuse_ratio_vs_N.csv") if r["cell_set"] != "GTASK13"]
    H = 422.0
    c = Canvas(H)
    cols = {"NPU": (52, 248, (5.5, 20.5), [6, 8, 10, 12, 14, 16, 18, 20], (10, 12), "queue forms", 12),
            "GPU": (300, 488, (19.5, 28.5), [20, 22, 24, 26, 28], (24, 25), "saturation", None)}
    leg_reuse, leg_ratio = None, None
    for sub, (x0, x1, xlim, xt, band, band_lab, scope_n) in cols.items():
        sim_rule = (lambda r, m=NPU_SIM: r["predictor"] == m.get(r["cell_set"])) if sub == "NPU" else \
                   (lambda r, m=GPU_SIM: r["predictor"] == m.get(r["cell_set"]))
        sim_lab = "Simulator" if sub == "NPU" else "Simulator (short-context cost)"
        # reuse panel
        p = c.panel(x0, 22, x1, 142, xlim, (0, 1.0))
        vband(p, *band, band_lab)
        frame(p, xticks=xt, yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], xlab="Concurrent sessions N",
              ylab="Baseline reuse rate", yfmt=lambda v: f"{v:.1f}", ylabel_x=x0 - 32)
        tag(p, f"({'a' if sub == 'NPU' else 'b'}) {sub}")
        null = series(rows, sub, "reuse", "BASE", "null")
        if null:
            p.raw_path([(p.x0, p.py(null[0][1])), (p.x1, p.py(null[0][1]))], color=OI["grey"],
                       width=1.0, dash=DASH["dot"])
        an = series(rows, sub, "reuse", "BASE", "analytic_v1")
        if sub == "NPU":
            inside = [pt for pt in an if pt[0] <= 12]
            outside = [pt for pt in an if pt[0] >= 12]
            poly(p, inside, color=OI["blue"], style="dash")
            poly(p, outside, color=OI["blue"], style="dash", opacity=0.35)
        else:
            poly(p, an, color=OI["blue"], style="dash", opacity=0.35)
        # GPU: for N >= 25 the context-aware simulator is the main predictor (GTASK20); the
        # short-context simulator is drawn lighter after N = 24
        sim_split = 24 if sub == "GPU" else None
        poly_split(p, series(rows, sub, "reuse", "BASE", sim_rule), sim_split, color=OI["vermillion"], style="solid")
        ctx = series(rows, sub, "reuse", "BASE", "sim_ctxcost")
        poly(p, ctx, color=OI["green"], style="dashdot", width=1.4)
        for r in rows:
            if r["substrate"] == sub and r["metric"] == "reuse" and r["config"] == "BASE" \
                    and r["predictor"] == "observed":
                pre = r["population"].startswith("blind_confirm") or r["population"] == "blind_no_information_cell"
                mark(p, float(r["N"]), float(r["value"]), color=INK, shape="o", hollow=not pre, r=2.8)
        leg_reuse = p
        # ratio panel
        rr = [r for r in rows if r["substrate"] == sub and r["metric"] == "ratio_to_BASE"
              and r["config"] in CONF[sub]]
        vals = [float(r[k]) for r in rr for k in ("value", "ci_lo", "ci_hi") if r[k] != ""
                and (r["predictor"] in ("observed",) or sim_rule(r))]
        lo = math.floor((min(vals) - 0.02) * 20) / 20
        hi = max(1.05, math.ceil((max(vals) + 0.02) * 20) / 20)
        q = c.panel(x0, 186, x1, 296, xlim, (lo, hi))
        vband(q, *band, band_lab, bottom=True)
        yt = [round(lo + 0.05 * k, 2) for k in range(int(round((hi - lo) / 0.05)) + 1)]
        yt = yt[::2] if len(yt) > 7 else yt
        frame(q, xticks=xt, yticks=yt, xlab="Concurrent sessions N", ylab="Cost ratio to baseline",
              yfmt=lambda v: f"{v:.2f}", ylabel_x=x0 - 36)
        tag(q, f"({'c' if sub == 'NPU' else 'd'}) {sub}")
        q.raw_path([(q.x0, q.py(1.0)), (q.x1, q.py(1.0))], color=OI["grey"], width=0.9, dash=DASH["dash"])
        ents = []
        for i, (cfg, (lab, col, shp, st)) in enumerate(CONF[sub].items()):
            off = -0.18 if i == 0 else 0.18
            poly_split(q, series(rows, sub, "ratio_to_BASE", cfg, sim_rule), sim_split, color=col, style=st)
            if sub == "GPU":
                poly(q, series(rows, sub, "ratio_to_BASE", cfg, "sim_ctxcost"), color=col, style="dashdot", width=1.4)
            for r in rr:
                if r["config"] == cfg and r["predictor"] == "observed":
                    x, v = float(r["N"]) + off, float(r["value"])
                    if r["ci_lo"] != "":
                        q.line([(x, float(r["ci_lo"])), (x, float(r["ci_hi"]))], color=col, width=0.8)
                    mark(q, x, v, color=col, shape=shp, r=2.5)
            ents += [{"label": f"{lab}: observed median, 95% CI", "color": col, "shape": shp},
                     {"label": f"{lab}: simulator", "color": col, "style": st}]
        if sub == "GPU":
            ents += [{"label": f"{lab}: context-aware sim. (GPU)", "color": col,
                      "style": "dashdot"} for _, (lab, col, _, _) in CONF[sub].items()]
        leg_ratio = (q, ents)
    p = leg_reuse
    legend(p, [{"label": "Observed, preregistered cell", "color": INK, "shape": "o"},
               {"label": "Observed, exploratory cell", "color": INK, "shape": "o", "hollow": True},
               {"label": "Analytical model (lighter: outside scope)", "color": OI["blue"], "style": "dash"},
               {"label": "Simulator (GPU: short-context; faded N >= 25)", "color": OI["vermillion"],
                "style": "solid"},
               {"label": "Simulator (context-aware cost)", "color": OI["green"], "style": "dashdot"},
               {"label": "Null predictor", "color": OI["grey"], "style": "dot"}],
           x=40, y=342)
    q, ents = leg_ratio
    legend(q, ents + [{"label": "Cost ratio 1.0", "color": OI["grey"], "style": "dash"}], x=262, y=342)
    c.save(out / "F_b_reuse_ratio_vs_N.pdf")


# -- F_d -------------------------------------------------------------------------------

def fig_d(out: Path) -> None:
    rows = [r for r in read("F_d_applicability.csv") if r["config"] == "BASE"]
    sim_of = {**NPU_SIM, "GTASK11": "sim_lru"}
    H = 236.0
    c = Canvas(H)
    pts = []
    for r in rows:
        if r["queue_mean_obs"] == "":            # GTASK20: no queue depth recorded
            continue
        kind = None
        if r["predictor"] == "analytic_v1":
            kind = "analytic"
        elif r["predictor"] == sim_of.get(r["cell_set"]):
            kind = "sim"
        elif r["predictor"] == "sim_ctxcost":
            kind = "ctx"
        if kind:
            pts.append((float(r["queue_mean_obs"]), abs(float(r["reuse_error"])), kind, r["substrate"], r["N"]))
    ymax = math.ceil(max(p[1] for p in pts) * 20 + 0.5) / 20
    p = c.panel(56, 14, 488, 200, (-2.0, 1.0), (-0.02, ymax))
    yt = [round(0.05 * k, 2) for k in range(int(round(ymax / 0.05)) + 1)]
    frame(p, xticks=[-2, -1, 0, 1], yticks=yt, xfmt=lambda v: f"{10 ** v:g}",
          xlab="Observed queue length (requests)",
          ylab="Baseline reuse absolute error", yfmt=lambda v: f"{v:.2f}", ylabel_x=18)
    p.vline(-1.0, color=OI["grey"], dash=DASH["dash"], width=0.9)
    shape = {"analytic": ("o", OI["blue"]), "sim": ("^", OI["vermillion"]), "ctx": ("s", OI["green"])}
    placed = []                                    # occupied boxes: markers first, then labels
    items = []
    for x, y, kind, sub, n in sorted(pts):
        lx = math.log10(max(x, 0.0101))
        cx, cy = p.px(lx), p.py(y)
        placed.append((cx - 3, cy - 3, cx + 3, cy + 3))
        items.append((cx, cy, lx, y, kind, sub, n))
    fs = 7.0
    for cx, cy, lx, y, kind, sub, n in items:
        shp, col = shape[kind]
        mark(p, lx, y, color=col, shape=shp, hollow=(sub == "GPU"), r=2.8)
        w = SP.text_width(n, fs)
        best = None
        for dx, dy in ((4, -3.5), (4, 8.5), (-4 - w, -3.5), (-4 - w, 8.5), (4, -10), (-4 - w, -10),
                       (4, 15), (-4 - w, 15), (10, 2.5), (-10 - w, 2.5)):
            box = (cx + dx, cy + dy - fs * 0.8, cx + dx + w, cy + dy + 0.5)
            hit = any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in placed)
            if not hit:
                best = (dx, dy, box)
                break
        dx, dy, box = best if best else (4, -3.5, (cx + 4, cy - 9, cx + 4 + w, cy - 3))
        placed.append(box)
        p.text(cx + dx, cy + dy, n, size=fs, anchor="start", data=False, fill=col)
    legend(p, [{"label": "Analytical model", "color": OI["blue"], "shape": "o"},
               {"label": "Simulator", "color": OI["vermillion"], "shape": "^"},
               {"label": "Simulator (context-aware cost)", "color": OI["green"], "shape": "s"},
               {"label": "NPU (filled) / GPU (hollow)", "color": INK, "shape": "o", "hollow": True}],
           x=p.px(-0.85), y=p.y1 + 8)
    c.save(out / "F_d_applicability.pdf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=FIG / "pdf")
    a = ap.parse_args()
    fig_a(a.out_dir)
    fig_b(a.out_dir)
    fig_d(a.out_dir)
    for f in ("F_a_survival.pdf", "F_b_reuse_ratio_vs_N.pdf", "F_d_applicability.pdf"):
        print(a.out_dir / f, (a.out_dir / f).stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
