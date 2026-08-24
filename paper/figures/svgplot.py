#!/usr/bin/env python3
"""A dependency-free SVG plotter.

matplotlib is not installed on this host and installing it needs approval
(CLAUDE.md rule 11), so the figures are emitted as SVG by hand. SVG is also
what a camera-ready wants: vector, no resampling, editable text.

Only what these eight figures need: linear axes, lines, markers, bars, step
functions, spans, and text. Everything is in user units with an explicit
data-to-pixel transform, so a figure's numbers are visible in its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html

PALETTE = {
    "base": "#37474f", "arm2": "#1565c0", "arm3": "#c62828",
    "accent": "#ef6c00", "muted": "#90a4ae", "grid": "#e0e0e0",
    "ok": "#2e7d32", "bad": "#b71c1c", "ink": "#212121",
}


@dataclass
class Axes:
    width: int = 660
    height: int = 400
    left: int = 74
    right: int = 22
    top: int = 44
    bottom: int = 58
    xlim: tuple[float, float] = (0.0, 1.0)
    ylim: tuple[float, float] = (0.0, 1.0)
    parts: list[str] = field(default_factory=list)

    # -- transform ----------------------------------------------------------
    @property
    def x0(self) -> int:
        return self.left

    @property
    def x1(self) -> int:
        return self.width - self.right

    @property
    def y0(self) -> int:
        return self.height - self.bottom

    @property
    def y1(self) -> int:
        return self.top

    def px(self, x: float) -> float:
        lo, hi = self.xlim
        return self.x0 + (x - lo) / (hi - lo) * (self.x1 - self.x0)

    def py(self, y: float) -> float:
        lo, hi = self.ylim
        return self.y0 + (y - lo) / (hi - lo) * (self.y1 - self.y0)

    # -- primitives ---------------------------------------------------------
    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x: float, y: float, s: str, *, size: int = 12, anchor: str = "middle",
             fill: str = PALETTE["ink"], weight: str = "normal", data: bool = True,
             rotate: float | None = None) -> None:
        px, py = (self.px(x), self.py(y)) if data else (x, y)
        tf = f' transform="rotate({rotate} {px:.1f} {py:.1f})"' if rotate else ""
        self.add(f'<text x="{px:.1f}" y="{py:.1f}" font-size="{size}" text-anchor="{anchor}" '
                 f'fill="{fill}" font-weight="{weight}" font-family="Helvetica,Arial,sans-serif"'
                 f'{tf}>{html.escape(s)}</text>')

    def line(self, pts: list[tuple[float, float]], *, color: str, width: float = 2.0,
             dash: str | None = None, opacity: float = 1.0) -> None:
        d = " ".join(f"{'M' if i == 0 else 'L'}{self.px(x):.1f},{self.py(y):.1f}"
                     for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-opacity="{opacity}" stroke-linejoin="round"{da}/>')

    def marker(self, x: float, y: float, *, color: str, r: float = 4.0,
               shape: str = "o", fill: str | None = None) -> None:
        cx, cy = self.px(x), self.py(y)
        f = color if fill is None else fill
        if shape == "o":
            self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{f}" '
                     f'stroke="{color}" stroke-width="1.4"/>')
        elif shape == "s":
            self.add(f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" '
                     f'fill="{f}" stroke="{color}" stroke-width="1.4"/>')
        elif shape == "^":
            self.add(f'<polygon points="{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy + r:.1f} '
                     f'{cx - r:.1f},{cy + r:.1f}" fill="{f}" stroke="{color}" stroke-width="1.4"/>')
        elif shape == "x":
            self.add(f'<path d="M{cx - r:.1f},{cy - r:.1f}L{cx + r:.1f},{cy + r:.1f}'
                     f'M{cx - r:.1f},{cy + r:.1f}L{cx + r:.1f},{cy - r:.1f}" '
                     f'stroke="{color}" stroke-width="2"/>')

    def bar(self, x: float, y: float, *, w: float, color: str, y_base: float = 0.0,
            opacity: float = 1.0, stroke: str | None = None) -> None:
        left, right = self.px(x - w / 2), self.px(x + w / 2)
        top, bot = self.py(y), self.py(y_base)
        if top > bot:
            top, bot = bot, top
        st = f' stroke="{stroke}" stroke-width="1.2"' if stroke else ""
        self.add(f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" '
                 f'height="{bot - top:.1f}" fill="{color}" fill-opacity="{opacity}"{st}/>')

    def hspan(self, ylo: float, yhi: float, *, color: str, opacity: float = 0.12) -> None:
        top, bot = self.py(yhi), self.py(ylo)
        self.add(f'<rect x="{self.x0}" y="{top:.1f}" width="{self.x1 - self.x0}" '
                 f'height="{bot - top:.1f}" fill="{color}" fill-opacity="{opacity}"/>')

    def vline(self, x: float, *, color: str, dash: str | None = "4 3", width: float = 1.4) -> None:
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M{self.px(x):.1f},{self.y0}L{self.px(x):.1f},{self.y1}" '
                 f'stroke="{color}" stroke-width="{width}"{da}/>')

    def hline(self, y: float, *, color: str, dash: str | None = "4 3", width: float = 1.4) -> None:
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M{self.x0},{self.py(y):.1f}L{self.x1},{self.py(y):.1f}" '
                 f'stroke="{color}" stroke-width="{width}"{da}/>')

    # -- frame --------------------------------------------------------------
    def frame(self, *, xticks: list[float], yticks: list[float],
              xfmt=lambda v: f"{v:g}", yfmt=lambda v: f"{v:g}",
              xlabel: str = "", ylabel: str = "", title: str = "", subtitle: str = "",
              xtick_labels: list[str] | None = None, grid: bool = True,
              xtick_rotate: float = 0.0) -> None:
        pre = []
        if grid:
            for v in yticks:
                pre.append(f'<path d="M{self.x0},{self.py(v):.1f}L{self.x1},{self.py(v):.1f}" '
                           f'stroke="{PALETTE["grid"]}" stroke-width="1"/>')
        self.parts = pre + self.parts
        self.add(f'<path d="M{self.x0},{self.y1}L{self.x0},{self.y0}L{self.x1},{self.y0}" '
                 f'fill="none" stroke="{PALETTE["ink"]}" stroke-width="1.3"/>')
        for i, v in enumerate(xticks):
            lab = xtick_labels[i] if xtick_labels else xfmt(v)
            self.add(f'<path d="M{self.px(v):.1f},{self.y0}L{self.px(v):.1f},{self.y0 + 5}" '
                     f'stroke="{PALETTE["ink"]}" stroke-width="1.2"/>')
            # SVG <text> has no line breaks: each line is its own element.
            for j, part in enumerate(str(lab).split("\n")):
                if xtick_rotate:
                    self.text(self.px(v) - 4, self.y0 + 12 + j * 13, part, size=11,
                              anchor="end", data=False, rotate=xtick_rotate)
                else:
                    self.text(self.px(v), self.y0 + 19 + j * 13, part, size=12, data=False)
        for v in yticks:
            self.add(f'<path d="M{self.x0 - 5},{self.py(v):.1f}L{self.x0},{self.py(v):.1f}" '
                     f'stroke="{PALETTE["ink"]}" stroke-width="1.2"/>')
            self.text(self.x0 - 9, self.py(v) + 4, yfmt(v), size=12, anchor="end", data=False)
        if xlabel:
            self.text((self.x0 + self.x1) / 2, self.height - 14, xlabel, size=13, data=False)
        if ylabel:
            self.text(18, (self.y0 + self.y1) / 2, ylabel, size=13, data=False,
                      rotate=-90)
        if title:
            self.text(self.x0, 20, title, size=15, anchor="start", weight="bold", data=False)
        if subtitle:
            self.text(self.x0, 36, subtitle, size=11.5, anchor="start",
                      fill=PALETTE["muted"], data=False)

    def legend(self, entries: list[tuple[str, str, str]], *, x: float, y: float,
               dy: float = 17) -> None:
        """entries: (label, color, shape) with shape in {line, o, s, ^, box}."""
        for i, (label, color, shape) in enumerate(entries):
            yy = y + i * dy
            if shape == "line":
                self.add(f'<path d="M{x},{yy} L{x + 22},{yy}" stroke="{color}" stroke-width="2.4"/>')
            elif shape == "box":
                self.add(f'<rect x="{x}" y="{yy - 6}" width="22" height="12" fill="{color}"/>')
            else:
                cx = x + 11
                if shape == "o":
                    self.add(f'<circle cx="{cx}" cy="{yy}" r="4.5" fill="{color}"/>')
                elif shape == "s":
                    self.add(f'<rect x="{cx - 4.5}" y="{yy - 4.5}" width="9" height="9" fill="{color}"/>')
                elif shape == "^":
                    self.add(f'<polygon points="{cx},{yy - 5} {cx + 5},{yy + 4} {cx - 5},{yy + 4}" '
                             f'fill="{color}"/>')
            self.text(x + 29, yy + 4, label, size=12, anchor="start", data=False)

    def render(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
                f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">'
                f'<rect width="{self.width}" height="{self.height}" fill="#ffffff"/>'
                + "".join(self.parts) + "</svg>\n")

    def save(self, path) -> None:
        from pathlib import Path
        Path(path).write_text(self.render())
