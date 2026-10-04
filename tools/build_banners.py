"""Builds the profile banners: assets/header-{dark,light}.svg and assets/studio.svg.

Text is converted to outlines (shaped with HarfBuzz, so kerning is kept), which
means the banners render the same everywhere without loading any font.

    pip install fonttools brotli uharfbuzz
    python tools/build_banners.py

Edit TEXT below when something changes (role, city, availability).
"""

import io
import math
import re
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
BRAND = ROOT / "tools" / "brand"
OUT = ROOT / "assets"

TEXT = {
    "eyebrow": "SENIOR GAME DEVELOPER  ·  VALENCIA, SPAIN",
    "name": "Andrés Llorens",
    "headline": ["Gameplay, tools and systems", "for games, VR and mobile."],
    "chips": ["Unity", "Godot", "C#", "GDScript", "XR", "Android"],
    "status": "Open to new roles  ·  Founder of Pal Lobby Games",
    "studio_slogan": ("Games with ", "personality."),
    "studio_traits": "Creativity. Play. Character.",
}

WIDTH, HEIGHT, RADIUS, PAD = 1280, 420, 26, 72

THEMES = {
    "dark": {
        "bg": "#0b0b10",
        "glow": "#c858f8",
        "glow_opacity": 0.30,
        "border": "rgba(255,255,255,0.08)",
        "text": "#f2f1f6",
        "headline": "#d9d7e3",
        "muted": "#a9a7b8",
        "accent": "#c858f8",
        "chip_fill": "rgba(255,255,255,0.035)",
        "chip_stroke": "rgba(255,255,255,0.14)",
        "chip_text": "#d9d7e3",
        "hex_fill": "rgba(255,255,255,0.018)",
        "hex_stroke": "rgba(255,255,255,0.075)",
        "hex_on_fill": "rgba(255,255,255,0.045)",
        "hex_on_stroke": "rgba(255,255,255,0.16)",
        "red": "#ff4f5e",
        "blue": "#4a90ff",
        "purple": "#c858f8",
        "core": "#ffffff",
        "check": "#14091a",
        "green": "#3ddc97",
        "dim": 0.30,
    },
    "light": {
        "bg": "#faf8fd",
        "glow": "#c858f8",
        "glow_opacity": 0.20,
        "border": "rgba(40,20,70,0.10)",
        "text": "#15131c",
        "headline": "#2c2938",
        "muted": "#5b5870",
        "accent": "#9a2fd0",
        "chip_fill": "rgba(255,255,255,0.75)",
        "chip_stroke": "rgba(40,20,70,0.16)",
        "chip_text": "#34313f",
        "hex_fill": "rgba(40,20,70,0.02)",
        "hex_stroke": "rgba(40,20,70,0.09)",
        "hex_on_fill": "rgba(40,20,70,0.04)",
        "hex_on_stroke": "rgba(40,20,70,0.18)",
        "red": "#e2334a",
        "blue": "#2d6fe0",
        "purple": "#a23ad8",
        "core": "#ffffff",
        "check": "#ffffff",
        "green": "#12a86a",
        "dim": 0.28,
    },
}


def num(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


class Font:
    def __init__(self, filename, weight):
        tt = TTFont(FONTS / filename)
        if "fvar" in tt:
            tt = instancer.instantiateVariableFont(tt, {"wght": weight})
        tt.flavor = None
        buf = io.BytesIO()
        tt.save(buf)
        data = buf.getvalue()
        self.tt = TTFont(io.BytesIO(data))
        self.hb = hb.Font(hb.Face(data))
        self.upem = self.tt["head"].unitsPerEm
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()

    def _shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        return buf

    def measure(self, text, size, tracking=0.0):
        buf = self._shape(text)
        scale = size / self.upem
        return sum(p.x_advance for p in buf.glyph_positions) * scale + tracking * (len(buf.glyph_positions) - 1)

    def path(self, text, x, y, size, tracking=0.0):
        buf = self._shape(text)
        scale = size / self.upem
        pen = SVGPathPen(self.glyphs, ntos=num)
        cursor = x
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = self.order[info.codepoint]
            ox = cursor + pos.x_offset * scale
            oy = y - pos.y_offset * scale
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, ox, oy)))
            cursor += pos.x_advance * scale + tracking
        return pen.getCommands()


MANROPE_XBOLD = Font("Manrope-latin-variable.woff2", 800)
MANROPE_SEMI = Font("Manrope-latin-variable.woff2", 600)
MANROPE_BOLD = Font("Manrope-latin-variable.woff2", 700)
INTER_BLACK = Font("InterDisplay-Black.woff2", 900)

# Hex board, a nod to Kromivolt: red and blue signals merge into purple and power two targets.
HEX = 44.0
HEX_W = math.sqrt(3) * HEX
HEX_X0, HEX_YC = 700.0, HEIGHT / 2


def cell(r, c):
    return (HEX_X0 + c * HEX_W + (HEX_W / 2 if r % 2 else 0), HEX_YC + (r - 3) * 1.5 * HEX)


def hexagon(cx, cy, s):
    pts = []
    for k in range(6):
        a = math.radians(60 * k - 90)
        pts.append(f"{num(cx + s * math.cos(a))},{num(cy + s * math.sin(a))}")
    return " ".join(pts)


SRC_RED, SRC_BLUE = (1, 3), (5, 3)
ROUTE_RED = [SRC_RED, (2, 4), (3, 4)]
ROUTE_BLUE = [SRC_BLUE, (4, 4), (3, 4)]
ROUTE_UP = [(3, 4), (3, 5), (2, 6)]
ROUTE_DOWN = [(3, 4), (3, 5), (4, 6)]
TARGETS = [(2, 6), (4, 6)]
ON_CELLS = set(ROUTE_RED + ROUTE_BLUE + ROUTE_UP + ROUTE_DOWN)

CYCLE = "4.6s"


def route_d(route):
    pts = [cell(*rc) for rc in route]
    return "M" + " L".join(f"{num(x)} {num(y)}" for x, y in pts)


def route_len(route):
    pts = [cell(*rc) for rc in route]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def anim(attr, values, times):
    return (
        f'<animate attributeName="{attr}" dur="{CYCLE}" repeatCount="indefinite" '
        f'values="{values}" keyTimes="{times}"/>'
    )


def board(t):
    out = []
    # Cells fade out towards the text column so the board never fights the name.
    for r in range(0, 7):
        for c in range(-6, 9):
            cx, cy = cell(r, c)
            if cx < 470 or cx > WIDTH + HEX:
                continue
            k = max(0.0, min(1.0, (cx - 560) / 420))
            k = k * k * (3 - 2 * k)
            if k <= 0.02:
                continue
            on = (r, c) in ON_CELLS
            fill = t["hex_on_fill"] if on else t["hex_fill"]
            stroke = t["hex_on_stroke"] if on else t["hex_stroke"]
            out.append(
                f'<polygon points="{hexagon(cx, cy, HEX - 3.5)}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="1.5" stroke-linejoin="round" opacity="{k:.2f}"/>'
            )

    routes = [
        (ROUTE_RED, t["red"], "0;0.06;0.40;1"),
        (ROUTE_BLUE, t["blue"], "0;0.06;0.40;1"),
        (ROUTE_UP, t["purple"], "0;0.42;0.70;1"),
        (ROUTE_DOWN, t["purple"], "0;0.42;0.70;1"),
    ]
    # Dim traces.
    for route, color, _ in routes:
        out.append(
            f'<path d="{route_d(route)}" fill="none" stroke="{color}" stroke-opacity="{t["dim"]}" '
            f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    # Lit traces: drawn behind the travelling signal, then faded out at the end of the cycle.
    lit_anim, lit_static = [], []
    for route, color, times in routes:
        d, length = route_d(route), num(route_len(route))
        base = f'd="{d}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
        lit_anim.append(
            f'<path {base} stroke-dasharray="{length} {length}" stroke-dashoffset="{length}">'
            + anim("stroke-dashoffset", f"{length};{length};0;0", times)
            + anim("opacity", "1;1;0;0", "0;0.86;0.97;1")
            + "</path>"
        )
        lit_static.append(f"<path {base}/>")

    # Nodes.
    nodes = []
    for rc in [(2, 4), (4, 4), (3, 5)]:
        x, y = cell(*rc)
        color = t["purple"] if rc == (3, 5) else (t["red"] if rc == (2, 4) else t["blue"])
        nodes.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="6.5" fill="{color}"/>')
    for rc, color in [(SRC_RED, t["red"]), (SRC_BLUE, t["blue"])]:
        x, y = cell(*rc)
        nodes.append(
            f'<circle cx="{num(x)}" cy="{num(y)}" r="21" fill="none" stroke="{color}" stroke-opacity="0.45" stroke-width="2"/>'
            f'<circle cx="{num(x)}" cy="{num(y)}" r="13" fill="{color}"/>'
            f'<circle cx="{num(x)}" cy="{num(y)}" r="4.5" fill="{t["core"]}" opacity="0.9"/>'
        )
    jx, jy = cell(3, 4)
    nodes.append(
        f'<circle cx="{num(jx)}" cy="{num(jy)}" r="11" fill="{t["purple"]}"/>'
        f'<circle cx="{num(jx)}" cy="{num(jy)}" r="4" fill="{t["core"]}" opacity="0.9"/>'
    )

    def target(x, y, lit):
        fill = t["purple"] if lit else t["bg"]
        check = (
            f'<path d="M{num(x - 7)} {num(y + 0.5)} l5 5 l9.5 -10" fill="none" stroke="{t["check"]}" '
            f'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
            if lit
            else ""
        )
        return (
            f'<rect x="{num(x - 15)}" y="{num(y - 15)}" width="30" height="30" rx="6" '
            f'transform="rotate(45 {num(x)} {num(y)})" fill="{fill}" stroke="{t["purple"]}" stroke-width="3"/>' + check
        )

    for rc in TARGETS:
        nodes.append(target(*cell(*rc), lit=False))

    # Animated layer: pulses, junction flash, targets lighting up.
    pulses = []
    for route, color, times in routes:
        pulses.append(
            f'<g opacity="0">'
            f'<circle r="20" fill="url(#glow-{color[1:]})"/>'
            f'<circle r="5.5" fill="{t["core"]}"/>'
            f'<animateMotion dur="{CYCLE}" repeatCount="indefinite" calcMode="linear" '
            f'keyPoints="0;0;1;1" keyTimes="{times}" path="{route_d(route)}"/>'
            + (
                anim("opacity", "0;0;1;1;0;0", "0;0.05;0.08;0.38;0.41;1")
                if color != t["purple"]
                else anim("opacity", "0;0;1;1;0;0", "0;0.41;0.44;0.68;0.71;1")
            )
            + "</g>"
        )
    flashes = [
        f'<circle cx="{num(jx)}" cy="{num(jy)}" r="11" fill="none" stroke="{t["purple"]}" stroke-width="3" opacity="0">'
        + anim("r", "11;11;30;30", "0;0.40;0.56;1")
        + anim("opacity", "0;0;0.9;0;0", "0;0.399;0.40;0.56;1")
        + "</circle>"
    ]
    for rc in TARGETS:
        x, y = cell(*rc)
        flashes.append(
            f'<g opacity="0">{target(x, y, lit=True)}'
            + anim("opacity", "0;0;1;1;0;0", "0;0.70;0.73;0.86;0.96;1")
            + "</g>"
            + f'<circle cx="{num(x)}" cy="{num(y)}" r="20" fill="none" stroke="{t["purple"]}" stroke-width="3" opacity="0">'
            + anim("r", "20;20;40;40", "0;0.70;0.86;1")
            + anim("opacity", "0;0;0.8;0;0", "0;0.699;0.70;0.86;1")
            + "</circle>"
        )
    lit_targets = "".join(target(*cell(*rc), lit=True) for rc in TARGETS)

    return (
        "".join(out)
        + f'<g class="anim">{"".join(lit_anim)}</g>'
        + f'<g class="still">{"".join(lit_static)}</g>'
        + "".join(nodes)
        + f'<g class="anim">{"".join(pulses)}{"".join(flashes)}</g>'
        + f'<g class="still">{lit_targets}</g>'
    )


def text_block(t):
    out = []
    y = 80
    out.append(
        f'<path fill="{t["accent"]}" d="{MANROPE_BOLD.path(TEXT["eyebrow"], PAD, y, 17, tracking=2.2)}"/>'
    )
    out.append(f'<path fill="{t["text"]}" d="{MANROPE_XBOLD.path(TEXT["name"], PAD - 4, 160, 82, tracking=-2.2)}"/>')
    for i, line in enumerate(TEXT["headline"]):
        out.append(
            f'<path fill="{t["headline"]}" d="{MANROPE_SEMI.path(line, PAD, 214 + i * 38, 30, tracking=-0.3)}"/>'
        )

    x, top, h, size = PAD, 284, 38, 17
    for label in TEXT["chips"]:
        w = MANROPE_SEMI.measure(label, size) + 34
        out.append(
            f'<rect x="{num(x)}" y="{top}" width="{num(w)}" height="{h}" rx="{h / 2}" '
            f'fill="{t["chip_fill"]}" stroke="{t["chip_stroke"]}" stroke-width="1.5"/>'
            f'<path fill="{t["chip_text"]}" d="{MANROPE_SEMI.path(label, x + 17, top + 25, size)}"/>'
        )
        x += w + 10

    sy = 360
    out.append(
        f'<circle cx="{PAD + 6}" cy="{sy - 6}" r="6" fill="{t["green"]}"/>'
        f'<circle class="anim" cx="{PAD + 6}" cy="{sy - 6}" r="6" fill="none" stroke="{t["green"]}" stroke-width="2">'
        f'<animate attributeName="r" values="6;15" dur="2.2s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0.8;0" dur="2.2s" repeatCount="indefinite"/></circle>'
        f'<path fill="{t["muted"]}" d="{MANROPE_SEMI.path(TEXT["status"], PAD + 24, sy, 17)}"/>'
    )
    return "".join(out)


def build(theme):
    t = THEMES[theme]
    glows = "".join(
        f'<radialGradient id="glow-{t[k][1:]}"><stop offset="0" stop-color="{t[k]}" stop-opacity="0.75"/>'
        f'<stop offset="1" stop-color="{t[k]}" stop-opacity="0"/></radialGradient>'
        for k in ("red", "blue", "purple")
    )
    label = f'{TEXT["name"]}, {TEXT["eyebrow"].title()}. {" ".join(TEXT["headline"])}'
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{label}">
<title>{label}</title>
<style>.still{{display:none}}@media (prefers-reduced-motion:reduce){{.anim{{display:none}}.still{{display:inline}}}}</style>
<defs>
<clipPath id="card"><rect width="{WIDTH}" height="{HEIGHT}" rx="{RADIUS}"/></clipPath>
<radialGradient id="bg-glow" cx="1080" cy="-60" r="760" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{t["glow"]}" stop-opacity="{t["glow_opacity"]}"/>
<stop offset="1" stop-color="{t["glow"]}" stop-opacity="0"/></radialGradient>
{glows}
</defs>
<g clip-path="url(#card)">
<rect width="{WIDTH}" height="{HEIGHT}" fill="{t["bg"]}"/>
<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg-glow)"/>
{board(t)}
{text_block(t)}
</g>
<rect x="0.75" y="0.75" width="{WIDTH - 1.5}" height="{HEIGHT - 1.5}" rx="{RADIUS - 0.75}" fill="none" stroke="{t["border"]}" stroke-width="1.5"/>
</svg>
"""
    path = OUT / f"header-{theme}.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"{path.relative_to(ROOT)}  {len(svg.encode()) / 1024:.1f} KB")


# Pal Lobby Games card, in the studio's own brand kit (Ink, Paper, Ascua, Inter Display).
PLG = {"ink": "#111114", "paper": "#f2f0ec", "ascua": "#ff5a36", "teal": "#00e5c7", "pink": "#ff2e88"}
STUDIO_W, STUDIO_H = 1280, 320


def embed(filename, x, y, width, opacity=None):
    src = (BRAND / filename).read_text(encoding="utf-8")
    vw, vh = (float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src).groups())
    inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", src, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner)
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return (
        f'<svg x="{num(x)}" y="{num(y)}" width="{num(width)}" height="{num(width * vh / vw)}" '
        f'viewBox="0 0 {num(vw)} {num(vh)}"{op}>{inner}</svg>'
    )


def build_studio():
    c = PLG
    first, accent = TEXT["studio_slogan"]
    tx, base = 318, 212
    slogan = INTER_BLACK.path(first, tx, base, 62, tracking=-1.2)
    accent_x = tx + INTER_BLACK.measure(first, 62, tracking=-1.2) - 1.2
    sparks = [
        ("M24 115 L80 110", c["ascua"], "0s"),
        ("M66 23 L100 65", c["ascua"], "0.5s"),
        ("M209 74 L247 36", c["teal"], "1s"),
        ("M221 129 L267 142", c["pink"], "1.5s"),
    ]
    spark_paths = "".join(
        f'<path d="{d}" stroke="{color}"><animate class="anim" attributeName="opacity" values="1;0.25;1" '
        f'dur="2.6s" begin="{begin}" repeatCount="indefinite"/></path>'
        for d, color, begin in sparks
    )
    label = f"Pal Lobby Games. {first}{accent} {TEXT['studio_traits']}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{STUDIO_W}" height="{STUDIO_H}" viewBox="0 0 {STUDIO_W} {STUDIO_H}" role="img" aria-label="{label}">
<title>{label}</title>
<style>@media (prefers-reduced-motion:reduce){{.anim{{display:none}}}}</style>
<defs>
<clipPath id="card"><rect width="{STUDIO_W}" height="{STUDIO_H}" rx="{RADIUS}"/></clipPath>
<radialGradient id="ember" cx="168" cy="170" r="260" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{c["ascua"]}" stop-opacity="0.22"/><stop offset="1" stop-color="{c["ascua"]}" stop-opacity="0"/></radialGradient>
</defs>
<g clip-path="url(#card)">
<rect width="{STUDIO_W}" height="{STUDIO_H}" fill="{c["ink"]}"/>
<rect width="{STUDIO_W}" height="{STUDIO_H}" fill="url(#ember)"/>
{embed("plg-principal-ascua.svg", 1010, 36, 400, opacity=0.035)}
{embed("plg-principal-ascua.svg", 64, 58, 200)}
{embed("plg-wordmark-dark.svg", tx - 5, 70, 500)}
<path fill="{c["paper"]}" d="{slogan}"/>
<path fill="{c["ascua"]}" d="{INTER_BLACK.path(accent, accent_x, base, 62, tracking=-1.2)}"/>
<path fill="{c["paper"]}" fill-opacity="0.62" d="{MANROPE_SEMI.path(TEXT["studio_traits"], tx + 2, 258, 21)}"/>
<g transform="translate(836 40) scale(0.5)" fill="none" stroke-width="12" stroke-linecap="round">{spark_paths}</g>
</g>
<rect x="0.75" y="0.75" width="{STUDIO_W - 1.5}" height="{STUDIO_H - 1.5}" rx="{RADIUS - 0.75}" fill="none" stroke="rgba(242,240,236,0.08)" stroke-width="1.5"/>
</svg>
"""
    path = OUT / "studio.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"{path.relative_to(ROOT)}  {len(svg.encode()) / 1024:.1f} KB")


if __name__ == "__main__":
    for name in THEMES:
        build(name)
    build_studio()
