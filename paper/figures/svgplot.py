#!/usr/bin/env python3
"""A dependency-free plotter that renders to SVG and to PDF.

matplotlib is not installed on this host, cairo is absent so ``cairosvg``
cannot be installed without an apt package, and no CJK font exists anywhere on
the filesystem. So the figures are built from primitives and written out twice:

  * **SVG** for review in a browser,
  * **PDF** for LaTeX, which cannot ``\\includegraphics`` an SVG.

The PDF writer embeds DejaVuSans (already on this host, at
``/usr/share/fonts/truetype/dejavu/``) as a simple TrueType font with
WinAnsiEncoding, and takes its glyph advances from Pillow, which is already
installed. Nothing new is installed. Because the same width table drives both
the ``/Widths`` array and this module's own text anchoring, positioning is
consistent with what a viewer computes rather than merely close to it.

WinAnsiEncoding covers Latin-1 and no more, so **PDF output requires ASCII
text**. ``set_language`` swaps every non-ASCII label through a translation
table and raises on any string the table does not cover, which is what keeps a
Korean label from silently vanishing from an English figure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html
from pathlib import Path
import re
import zlib

PALETTE = {
    "base": "#37474f", "arm2": "#1565c0", "arm3": "#c62828",
    "accent": "#ef6c00", "muted": "#90a4ae", "grid": "#e0e0e0",
    "ok": "#2e7d32", "bad": "#b71c1c", "ink": "#212121",
}

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONTS = {"normal": FONT_DIR / "DejaVuSans.ttf", "bold": FONT_DIR / "DejaVuSans-Bold.ttf"}

# -- language ---------------------------------------------------------------
_LANG = "ko"
_TABLE: dict[str, str] = {}
_PATTERNS: list[tuple[object, str]] = []
_USED: set[str] = set()


def set_language(lang: str, table: dict[str, str] | None = None,
                 patterns: list[tuple[str, str]] | None = None) -> None:
    """``ko`` passes labels through; any other language translates them.

    ``patterns`` covers labels built with an f-string, where the literal text
    is fixed but a number is not. Each entry is a regex and a replacement
    template evaluated with ``Match.expand``.
    """
    global _LANG, _TABLE, _PATTERNS
    _LANG = lang
    _TABLE = table or {}
    _PATTERNS = [(re.compile(pat), rep) for pat, rep in (patterns or [])]
    _USED.clear()


def used_translations() -> set[str]:
    return set(_USED)


def _tr(s: str) -> str:
    if _LANG == "ko" or all(ord(c) < 127 for c in s):
        return s
    if s in _TABLE:
        _USED.add(s)
        out = _TABLE[s]
    else:
        out = None
        for rx, rep in _PATTERNS:
            m = rx.fullmatch(s)
            if m:
                _USED.add(rx.pattern)
                out = m.expand(rep)
                break
        if out is None:
            raise KeyError(f"no {_LANG} translation for figure label: {s!r}")
    bad = [c for c in out if ord(c) > 255]
    if bad:
        raise ValueError(f"translation is not Latin-1, so it cannot go in a PDF: {out!r}")
    return out


# -- text metrics -----------------------------------------------------------
_WIDTH_CACHE: dict[str, list[int]] = {}


def _widths(weight: str) -> list[int]:
    """Advance widths for codes 32-255, in 1/1000 em, from the actual font."""
    if weight not in _WIDTH_CACHE:
        from PIL import ImageFont
        f = ImageFont.truetype(str(FONTS[weight]), 1000)
        _WIDTH_CACHE[weight] = [round(f.getlength(bytes([c]).decode("latin-1")))
                                for c in range(32, 256)]
    return _WIDTH_CACHE[weight]


def text_width(s: str, size: float, weight: str = "normal") -> float:
    w = _widths(weight)
    total = 0
    for ch in s:
        o = ord(ch)
        total += w[o - 32] if 32 <= o < 256 else 600
    return total / 1000.0 * size


# -- primitives -------------------------------------------------------------
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
    prims: list[dict] = field(default_factory=list)

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

    # -- drawing --------------------------------------------------------
    def add(self, prim: dict) -> None:
        self.prims.append(prim)

    def text(self, x: float, y: float, s: str, *, size: float = 12, anchor: str = "middle",
             fill: str = PALETTE["ink"], weight: str = "normal", data: bool = True,
             rotate: float | None = None) -> None:
        px, py = (self.px(x), self.py(y)) if data else (x, y)
        self.add({"k": "text", "x": px, "y": py, "s": _tr(s), "size": size,
                  "anchor": anchor, "fill": fill, "weight": weight, "rotate": rotate})

    def line(self, pts: list[tuple[float, float]], *, color: str, width: float = 2.0,
             dash: str | None = None, opacity: float = 1.0) -> None:
        self.add({"k": "path", "pts": [(self.px(x), self.py(y)) for x, y in pts],
                  "stroke": color, "w": width, "dash": dash, "op": opacity})

    def raw_path(self, pts: list[tuple[float, float]], *, color: str, width: float = 2.0,
                 dash: str | None = None, opacity: float = 1.0, closed: bool = False,
                 fill: str | None = None) -> None:
        self.add({"k": "path", "pts": pts, "stroke": color, "w": width, "dash": dash,
                  "op": opacity, "closed": closed, "fill": fill})

    def marker(self, x: float, y: float, *, color: str, r: float = 4.0,
               shape: str = "o", fill: str | None = None) -> None:
        cx, cy = self.px(x), self.py(y)
        f = color if fill is None else fill
        if shape == "o":
            self.add({"k": "circle", "cx": cx, "cy": cy, "r": r, "fill": f,
                      "stroke": color, "sw": 1.4})
        elif shape == "s":
            self.add({"k": "rect", "x": cx - r, "y": cy - r, "w": 2 * r, "h": 2 * r,
                      "fill": f, "stroke": color, "sw": 1.4, "op": 1.0})
        elif shape == "^":
            self.add({"k": "poly", "pts": [(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)],
                      "fill": f, "stroke": color, "sw": 1.4})
        elif shape == "x":
            self.raw_path([(cx - r, cy - r), (cx + r, cy + r)], color=color, width=2)
            self.raw_path([(cx - r, cy + r), (cx + r, cy - r)], color=color, width=2)

    def bar(self, x: float, y: float, *, w: float, color: str, y_base: float = 0.0,
            opacity: float = 1.0, stroke: str | None = None) -> None:
        left, right = self.px(x - w / 2), self.px(x + w / 2)
        top, bot = self.py(y), self.py(y_base)
        if top > bot:
            top, bot = bot, top
        self.add({"k": "rect", "x": left, "y": top, "w": right - left, "h": bot - top,
                  "fill": color, "op": opacity, "stroke": stroke, "sw": 1.2})

    def rect_px(self, x: float, y: float, w: float, h: float, *, fill: str,
                opacity: float = 1.0) -> None:
        self.add({"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                  "op": opacity, "stroke": None, "sw": 0})

    def hspan(self, ylo: float, yhi: float, *, color: str, opacity: float = 0.12) -> None:
        top, bot = self.py(yhi), self.py(ylo)
        self.rect_px(self.x0, top, self.x1 - self.x0, bot - top, fill=color, opacity=opacity)

    def vline(self, x: float, *, color: str, dash: str | None = "4 3", width: float = 1.4) -> None:
        self.raw_path([(self.px(x), self.y0), (self.px(x), self.y1)], color=color,
                      width=width, dash=dash)

    def hline(self, y: float, *, color: str, dash: str | None = "4 3", width: float = 1.4) -> None:
        self.raw_path([(self.x0, self.py(y)), (self.x1, self.py(y))], color=color,
                      width=width, dash=dash)

    # -- frame ----------------------------------------------------------
    def frame(self, *, xticks: list[float], yticks: list[float],
              xfmt=lambda v: f"{v:g}", yfmt=lambda v: f"{v:g}",
              xlabel: str = "", ylabel: str = "", title: str = "", subtitle: str = "",
              xtick_labels: list[str] | None = None, grid: bool = True,
              xtick_rotate: float = 0.0) -> None:
        pre: list[dict] = []
        if grid:
            for v in yticks:
                pre.append({"k": "path", "pts": [(self.x0, self.py(v)), (self.x1, self.py(v))],
                            "stroke": PALETTE["grid"], "w": 1, "dash": None, "op": 1.0})
        self.prims = pre + self.prims
        self.raw_path([(self.x0, self.y1), (self.x0, self.y0), (self.x1, self.y0)],
                      color=PALETTE["ink"], width=1.3)
        for i, v in enumerate(xticks):
            lab = xtick_labels[i] if xtick_labels else xfmt(v)
            self.raw_path([(self.px(v), self.y0), (self.px(v), self.y0 + 5)],
                          color=PALETTE["ink"], width=1.2)
            for j, part in enumerate(str(lab).split("\n")):
                if xtick_rotate:
                    self.text(self.px(v) - 4, self.y0 + 12 + j * 13, part, size=11,
                              anchor="end", data=False, rotate=xtick_rotate)
                else:
                    self.text(self.px(v), self.y0 + 19 + j * 13, part, size=12, data=False)
        for v in yticks:
            self.raw_path([(self.x0 - 5, self.py(v)), (self.x0, self.py(v))],
                          color=PALETTE["ink"], width=1.2)
            self.text(self.x0 - 9, self.py(v) + 4, yfmt(v), size=12, anchor="end", data=False)
        if xlabel:
            self.text((self.x0 + self.x1) / 2, self.height - 14, xlabel, size=13, data=False)
        if ylabel:
            self.text(18, (self.y0 + self.y1) / 2, ylabel, size=13, data=False, rotate=-90)
        if title:
            self.text(self.x0, 20, title, size=15, anchor="start", weight="bold", data=False)
        if subtitle:
            self.text(self.x0, 36, subtitle, size=11.5, anchor="start",
                      fill=PALETTE["muted"], data=False)

    def legend(self, entries: list[tuple[str, str, str]], *, x: float, y: float,
               dy: float = 17) -> None:
        for i, (label, color, shape) in enumerate(entries):
            yy = y + i * dy
            if shape == "line":
                self.raw_path([(x, yy), (x + 22, yy)], color=color, width=2.4)
            elif shape == "box":
                self.add({"k": "rect", "x": x, "y": yy - 6, "w": 22, "h": 12,
                          "fill": color, "op": 1.0, "stroke": None, "sw": 0})
            else:
                cx = x + 11
                if shape == "o":
                    self.add({"k": "circle", "cx": cx, "cy": yy, "r": 4.5, "fill": color,
                              "stroke": color, "sw": 0})
                elif shape == "s":
                    self.add({"k": "rect", "x": cx - 4.5, "y": yy - 4.5, "w": 9, "h": 9,
                              "fill": color, "op": 1.0, "stroke": None, "sw": 0})
                elif shape == "^":
                    self.add({"k": "poly", "pts": [(cx, yy - 5), (cx + 5, yy + 4), (cx - 5, yy + 4)],
                              "fill": color, "stroke": color, "sw": 0})
            self.text(x + 29, yy + 4, label, size=12, anchor="start", data=False)

    # -- layout check ---------------------------------------------------
    def text_boxes(self) -> list[tuple[float, float, float, float, str]]:
        """Bounding box of every unrotated text primitive, in canvas pixels.

        Every glyph position in these figures is computed here rather than by a
        layout engine, so collisions are decidable analytically: the same width
        table that places the text can also ask whether two pieces overlap.
        """
        out = []
        for p in self.prims:
            if p["k"] != "text" or p.get("rotate"):
                continue
            w = text_width(p["s"], p["size"], p["weight"])
            x = p["x"]
            if p["anchor"] == "middle":
                x -= w / 2
            elif p["anchor"] == "end":
                x -= w
            # baseline-relative: ascent above, a little descent below
            out.append((x, p["y"] - p["size"] * 0.80, x + w, p["y"] + p["size"] * 0.22, p["s"]))
        return out

    def text_collisions(self, pad: float = 0.5) -> list[tuple[str, str, float]]:
        """Pairs of text primitives whose boxes overlap, with the overlap area."""
        boxes = self.text_boxes()
        hits = []
        for i in range(len(boxes)):
            ax0, ay0, ax1, ay1, at = boxes[i]
            for j in range(i + 1, len(boxes)):
                bx0, by0, bx1, by1, bt = boxes[j]
                ox = min(ax1, bx1) - max(ax0, bx0) - pad
                oy = min(ay1, by1) - max(ay0, by0) - pad
                if ox > 0 and oy > 0:
                    hits.append((at, bt, ox * oy))
        return sorted(hits, key=lambda h: -h[2])

    # -- SVG ------------------------------------------------------------
    def render(self) -> str:
        out = []
        for p in self.prims:
            k = p["k"]
            if k == "text":
                tf = ""
                if p["rotate"]:
                    tf = f' transform="rotate({p["rotate"]} {p["x"]:.1f} {p["y"]:.1f})"'
                out.append(f'<text x="{p["x"]:.1f}" y="{p["y"]:.1f}" font-size="{p["size"]}" '
                           f'text-anchor="{p["anchor"]}" fill="{p["fill"]}" '
                           f'font-weight="{p["weight"]}" '
                           f'font-family="Helvetica,Arial,sans-serif"{tf}>'
                           f'{html.escape(p["s"])}</text>')
            elif k == "path":
                d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
                             for i, (x, y) in enumerate(p["pts"]))
                if p.get("closed"):
                    d += " Z"
                da = f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
                fill = p.get("fill") or "none"
                out.append(f'<path d="{d}" fill="{fill}" stroke="{p["stroke"]}" '
                           f'stroke-width="{p["w"]}" stroke-opacity="{p.get("op", 1.0)}" '
                           f'stroke-linejoin="round"{da}/>')
            elif k == "rect":
                st = (f' stroke="{p["stroke"]}" stroke-width="{p["sw"]}"'
                      if p.get("stroke") else "")
                out.append(f'<rect x="{p["x"]:.1f}" y="{p["y"]:.1f}" width="{p["w"]:.1f}" '
                           f'height="{p["h"]:.1f}" fill="{p["fill"]}" '
                           f'fill-opacity="{p.get("op", 1.0)}"{st}/>')
            elif k == "circle":
                out.append(f'<circle cx="{p["cx"]:.1f}" cy="{p["cy"]:.1f}" r="{p["r"]}" '
                           f'fill="{p["fill"]}" stroke="{p["stroke"]}" '
                           f'stroke-width="{p["sw"]}"/>')
            elif k == "poly":
                pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p["pts"])
                out.append(f'<polygon points="{pts}" fill="{p["fill"]}" '
                           f'fill-opacity="{p.get("op", 1.0)}" stroke="{p["stroke"]}" '
                           f'stroke-width="{p["sw"]}"/>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
                f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">'
                f'<rect width="{self.width}" height="{self.height}" fill="#ffffff"/>'
                + "".join(out) + "</svg>\n")

    def save(self, path) -> None:
        Path(path).write_text(self.render())

    # -- PDF ------------------------------------------------------------
    def save_pdf(self, path) -> None:
        Path(path).write_bytes(_pdf(self))


def _rgb(hexcolor: str) -> tuple[float, float, float]:
    h = hexcolor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _dash(spec: str) -> str:
    return "[" + " ".join(f"{float(v):g}" for v in spec.replace(",", " ").split()) + "] 0 d"


def _esc(s: str) -> bytes:
    out = s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return out.encode("latin-1", "replace")


def _content(ax: Axes) -> bytes:
    """Draw in SVG coordinates: the CTM flip makes y grow downward."""
    b: list[str] = [f"1 0 0 -1 0 {ax.height} cm",
                    "1 1 1 rg", f"0 0 {ax.width} {ax.height} re f"]
    ops: dict[float, str] = {}

    def gs(op: float) -> str:
        if op >= 0.999:
            return "/GS1 gs"
        ops.setdefault(op, f"/GS{len(ops) + 2}")
        return f"{ops[op]} gs"

    for p in ax.prims:
        k = p["k"]
        if k == "path":
            r, g, bl = _rgb(p["stroke"])
            b.append("q")
            b.append(gs(p.get("op", 1.0)))
            b.append(f"{r:.3f} {g:.3f} {bl:.3f} RG {p['w']} w 1 j")
            if p.get("dash"):
                b.append(_dash(p["dash"]))
            pts = p["pts"]
            b.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} m")
            for x, y in pts[1:]:
                b.append(f"{x:.2f} {y:.2f} l")
            if p.get("closed"):
                b.append("h")
            if p.get("fill"):
                fr, fg, fb = _rgb(p["fill"])
                b.append(f"{fr:.3f} {fg:.3f} {fb:.3f} rg B")
            else:
                b.append("S")
            b.append("Q")
        elif k == "rect":
            r, g, bl = _rgb(p["fill"])
            b.append("q")
            b.append(gs(p.get("op", 1.0)))
            b.append(f"{r:.3f} {g:.3f} {bl:.3f} rg")
            b.append(f"{p['x']:.2f} {p['y']:.2f} {p['w']:.2f} {p['h']:.2f} re")
            if p.get("stroke"):
                sr, sg, sb = _rgb(p["stroke"])
                b.append(f"{sr:.3f} {sg:.3f} {sb:.3f} RG {p['sw']} w B")
            else:
                b.append("f")
            b.append("Q")
        elif k == "circle":
            cx, cy, rr = p["cx"], p["cy"], p["r"]
            kk = 0.5523 * rr
            fr, fg, fb = _rgb(p["fill"])
            sr, sg, sb = _rgb(p["stroke"])
            b.append("q")
            b.append(f"{fr:.3f} {fg:.3f} {fb:.3f} rg {sr:.3f} {sg:.3f} {sb:.3f} RG "
                     f"{p['sw'] or 0} w")
            b.append(f"{cx + rr:.2f} {cy:.2f} m")
            b.append(f"{cx + rr:.2f} {cy + kk:.2f} {cx + kk:.2f} {cy + rr:.2f} "
                     f"{cx:.2f} {cy + rr:.2f} c")
            b.append(f"{cx - kk:.2f} {cy + rr:.2f} {cx - rr:.2f} {cy + kk:.2f} "
                     f"{cx - rr:.2f} {cy:.2f} c")
            b.append(f"{cx - rr:.2f} {cy - kk:.2f} {cx - kk:.2f} {cy - rr:.2f} "
                     f"{cx:.2f} {cy - rr:.2f} c")
            b.append(f"{cx + kk:.2f} {cy - rr:.2f} {cx + rr:.2f} {cy - kk:.2f} "
                     f"{cx + rr:.2f} {cy:.2f} c")
            b.append("h B" if p["sw"] else "h f")
            b.append("Q")
        elif k == "poly":
            fr, fg, fb = _rgb(p["fill"])
            sr, sg, sb = _rgb(p["stroke"])
            pts = p["pts"]
            b.append("q")
            b.append(gs(p.get("op", 1.0)))
            b.append(f"{fr:.3f} {fg:.3f} {fb:.3f} rg {sr:.3f} {sg:.3f} {sb:.3f} RG "
                     f"{p['sw'] or 0} w")
            b.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} m")
            for x, y in pts[1:]:
                b.append(f"{x:.2f} {y:.2f} l")
            b.append("h B" if p["sw"] else "h f")
            b.append("Q")
        elif k == "text":
            w = text_width(p["s"], p["size"], p["weight"])
            x, y = p["x"], p["y"]
            if p["anchor"] == "middle":
                dx = -w / 2
            elif p["anchor"] == "end":
                dx = -w
            else:
                dx = 0.0
            r, g, bl = _rgb(p["fill"])
            fnt = "/F2" if p["weight"] == "bold" else "/F1"
            b.append("q")
            b.append(f"{r:.3f} {g:.3f} {bl:.3f} rg BT {fnt} {p['size']} Tf")
            if p["rotate"] == -90:
                # advance points up the page; glyph tops face left
                b.append(f"0 -1 -1 0 {x:.2f} {y - dx:.2f} Tm")
            else:
                b.append(f"1 0 0 -1 {x + dx:.2f} {y:.2f} Tm")
            b.append(f"({_esc(p['s']).decode('latin-1')}) Tj ET")
            b.append("Q")
    head = " ".join(b).encode("latin-1", "replace")
    return head, ops


def _pdf(ax: Axes) -> bytes:
    content, ops = _content(ax)
    objs: list[bytes] = []

    def obj(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    fonts = {}
    for tag, weight, name in (("F1", "normal", "DejaVuSans"), ("F2", "bold", "DejaVuSans-Bold")):
        ttf = FONTS[weight].read_bytes()
        # Flate the font programme: it is over 90 % of the file otherwise.
        packed_ttf = zlib.compress(ttf, 9)
        ff = obj(b"<< /Length " + str(len(packed_ttf)).encode() + b" /Length1 "
                 + str(len(ttf)).encode() + b" /Filter /FlateDecode >>\nstream\n"
                 + packed_ttf + b"\nendstream")
        fd = obj(f"<< /Type /FontDescriptor /FontName /{name} /Flags 32 "
                 f"/FontBBox [-1021 -463 1793 1232] /ItalicAngle 0 /Ascent 928 "
                 f"/Descent -236 /CapHeight 700 /StemV {80 if weight == 'normal' else 140} "
                 f"/FontFile2 {ff} 0 R >>".encode())
        widths = " ".join(str(w) for w in _widths(weight))
        fonts[tag] = obj(f"<< /Type /Font /Subtype /TrueType /BaseFont /{name} "
                         f"/FirstChar 32 /LastChar 255 /Widths [{widths}] "
                         f"/Encoding /WinAnsiEncoding /FontDescriptor {fd} 0 R >>".encode())

    gs_items = ["/GS1 << /Type /ExtGState /ca 1 /CA 1 >>"]
    for op, tag in ops.items():
        gs_items.append(f"{tag} << /Type /ExtGState /ca {op:.3f} /CA {op:.3f} >>")
    packed = zlib.compress(content)
    cont = obj(b"<< /Length " + str(len(packed)).encode() + b" /Filter /FlateDecode >>\n"
               b"stream\n" + packed + b"\nendstream")
    res = ("<< /Font << " + " ".join(f"/{t} {n} 0 R" for t, n in fonts.items())
           + " >> /ExtGState << " + " ".join(gs_items) + " >> >>")
    page = obj(f"<< /Type /Page /Parent PAGES 0 R /MediaBox [0 0 {ax.width} {ax.height}] "
               f"/Resources {res} /Contents {cont} 0 R >>".encode())
    pages = obj(f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>".encode())
    root = obj(f"<< /Type /Catalog /Pages {pages} 0 R >>".encode())
    objs[page - 1] = objs[page - 1].replace(b"PAGES", str(pages).encode())

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root {root} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    return bytes(out)
