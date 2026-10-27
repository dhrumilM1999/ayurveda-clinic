"""
Klinvexa final-direction logo (built from the reference picture the owner shared): a wide, bold wordmark where
  - the K has its upper arm cut away in the accent colour,
  - the dot of the i is a teal circle,
  - the x has its top-right stroke cut in teal,
and a wide-spaced tagline "CLINIC OPERATIONS, CONNECTED." under it.
Everything is vector paths (no font needed to open the SVG). Fonts used: Satoshi Bold (wordmark), Satoshi Regular (tagline).

    python brand/klinvexa/build_reference.py       # writes SVG + PNG into brand/klinvexa/final/

SAFE TO EDIT: PALETTES (colours), WIDEN (how wide the letters are), GAP (the cuts).
"""
import os
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "backend", "assets", "fonts")
OUT = os.path.join(HERE, "final")
os.makedirs(OUT, exist_ok=True)

XH, CAP, STEM = 494, 731, 121
WIDEN = 1.07          # letters are 7% wider than Satoshi Bold, for a more modern, wide look
TAGLINE = "CLINIC OPERATIONS, CONNECTED."

PALETTES = {
    "brief":  {"dark": "#0F172A", "main": "#2563EB", "accent": "#14B8A6", "arm": ("#2563EB", "#1AA6C8"), "ink": "#475569"},
    "ours":   {"dark": "#1F2430", "main": "#E0560F", "accent": "#0F8F84", "arm": ("#E0560F", "#E0560F"), "ink": "#5B6370"},
    "brief-dark": {"dark": "#FFFFFF", "main": "#3B82F6", "accent": "#2DD4BF", "arm": ("#3B82F6", "#2DD4BF"), "ink": "#CBD5E1"},
    "ours-dark":  {"dark": "#FFFFFF", "main": "#FF7A33", "accent": "#2DD4BF", "arm": ("#FF7A33", "#FF7A33"), "ink": "#D5D8DE"},
    "black": {"dark": "#000000", "main": "#000000", "accent": "#000000", "arm": ("#000000", "#000000"), "ink": "#000000"},
    "white": {"dark": "#FFFFFF", "main": "#FFFFFF", "accent": "#FFFFFF", "arm": ("#FFFFFF", "#FFFFFF"), "ink": "#FFFFFF"},
}


class Face:
    def __init__(self, file):
        self.font = TTFont(os.path.join(FONTS, file))
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()

    def letter(self, ch, x):
        name = self.cmap[ord(ch)]
        pen = SVGPathPen(self.glyphs)
        self.glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
        return pen.getCommands(), self.font["hmtx"][name][0]


BOLD, REGULAR = Face("Satoshi-Bold.otf"), Face("Satoshi-Regular.otf")


def bar(x0, y0, x1, y1, w):
    return f"M{x0:.1f} {-y0:.1f}L{x0 + w:.1f} {-y0:.1f}L{x1 + w:.1f} {-y1:.1f}L{x1:.1f} {-y1:.1f}Z"


def shift(path, dx):
    import re
    return re.sub(r"([ML])(-?[0-9.]+) (-?[0-9.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) + dx:.1f} {m.group(3)}", path)


def k_parts(x):
    """K: stem + leg (dark) and the upper arm cut away from the stem (arm colour). Returns (dark, arm)."""
    w, sx = 160, x + 81 + STEM
    stem = f"M{x + 81} 0V{-CAP}H{sx}V0Z"
    leg = bar(sx - 60, CAP * 0.36, x + 650 - w, 0, w)
    arm = bar(sx + 56, CAP * 0.50, x + 662 - w, CAP, w)
    return stem + leg, arm


def i_parts(x):
    """i: a plain stem and a round teal dot. Returns (stem, dot)."""
    stem = f"M{x + 65} 0V{-XH}H{x + 186}V0Z"
    cx, cy, r = x + 125.5, -(XH + 150), 76
    dot = f"M{cx - r} {cy}a{r} {r} 0 1 0 {2 * r} 0a{r} {r} 0 1 0 {-2 * r} 0Z"
    return stem, dot


def x_parts(x, gap=62, w=150, width=500, nudge=14):
    """x: one stroke whole, the other cut where they cross; the top-right half is the accent. Returns (main, accent)."""
    x0, x1 = x + 8, x + width - w - 8
    whole = bar(x0, XH, x1, 0, w)
    span = gap / XH

    def piece(t0, t1):
        return bar(x0 + (x1 - x0) * t0, XH * t0, x0 + (x1 - x0) * t1, XH * t1, w)
    return whole + piece(0, 0.5 - span), shift(piece(0.5 + span, 1), nudge)


def wordmark(tracking=-4):
    """Returns ([(path, role)], width) in font units. roles: dark, main, accent, arm."""
    parts, x = [], 0
    for ch in "Klinvexa":
        if ch == "K":
            dark, arm = k_parts(x)
            parts += [(dark, "dark"), (arm, "arm")]
            adv = 674
        elif ch == "i":
            stem, dot = i_parts(x)
            parts += [(stem, "dark"), (dot, "accent")]
            adv = 251
        elif ch == "x":
            main, accent = x_parts(x)
            parts += [(main, "main"), (accent, "accent")]
            adv = 513
        else:
            d, adv = BOLD.letter(ch, x)
            parts.append((d, "main" if ch in "ve" else "dark"))
        x += adv + tracking
    return parts, x - tracking


def tagline_parts(target_width):
    """The tagline as paths, spaced so that it is exactly as wide as the wordmark (before widening).
    Returns (paths, size): the paths are in font units, draw them scaled by size."""
    size = 0.105
    items = [(ch, REGULAR.font["hmtx"][REGULAR.cmap[ord(ch)]][0] if ch != " " else 280) for ch in TAGLINE]
    natural = sum(adv for _, adv in items) * size
    tracking = (target_width / WIDEN - natural) / (len(items) - 1) / size
    out, x = [], 0
    for ch, adv in items:
        if ch != " ":
            out.append(REGULAR.letter(ch, x)[0])
        x += adv + tracking
    return out, size


def paint(role, pal, grad_id, solid):
    if role == "arm":
        return f"url(#{grad_id})" if not solid else pal["main"]
    return pal[role]


def logo_svg(pal_name, tagline=True, bg=None, solid=False, pad=70):
    pal = PALETTES[pal_name]
    parts, width = wordmark()
    gid = f"arm-{pal_name}"
    w = width * WIDEN + 2 * pad
    top = CAP + pad + 40                       # room above for the i dot
    h = top + pad + (230 if tagline else 0)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="Klinvexa">', "<title>Klinvexa</title>"]
    c1, c2 = pal["arm"]
    if c1 != c2 and not solid:
        o.append(f'<defs><linearGradient id="{gid}" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>')
    if bg:
        o.append(f'<rect width="{w:.0f}" height="{h:.0f}" fill="{bg}"/>')
    o.append(f'<g transform="translate({pad} {top}) scale({WIDEN} 1)">')
    for d, role in parts:
        o.append(f'<path d="{d}" fill="{paint(role, pal, gid, solid or c1 == c2)}"/>')
    o.append("</g>")
    if tagline:
        letters, size = tagline_parts(width * WIDEN)
        o.append(f'<g transform="translate({pad} {top + 235}) scale({size})" fill="{pal["ink"]}">')
        o += [f'<path d="{d}"/>' for d in letters]
        o.append("</g>")
    o.append("</svg>")
    return "\n".join(o)


def app_icon(pal_name, tile, size=100):
    """The compact mark: the K (stem + leg dark, arm in the arm colour) on a rounded tile."""
    pal = PALETTES[pal_name]
    dark, arm = k_parts(-81)
    scale = 52 / CAP
    gid = f"icon-{pal_name}-{abs(hash(tile)) % 999}"
    c1, c2 = pal["arm"]
    defs = f'<defs><linearGradient id="{gid}" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>' if c1 != c2 else ""
    fill_arm = f"url(#{gid})" if c1 != c2 else pal["main"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">{defs}'
            f'<rect width="100" height="100" rx="24" fill="{tile}" stroke="#E2E8F0" stroke-width="{1 if tile.upper() == "#FFFFFF" else 0}"/>'
            f'<g transform="translate({(100 - 600 * scale) / 2:.1f} {(100 + CAP * scale) / 2:.1f}) scale({scale:.4f})">'
            f'<path d="{dark}" fill="{pal["dark"]}"/><path d="{arm}" fill="{fill_arm}"/></g></svg>')


def write(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    for p in ("brief", "ours"):
        write(f"klinvexa-{p}-horizontal.svg", logo_svg(p, tagline=True, bg="#FFFFFF"))
        write(f"klinvexa-{p}-wordmark.svg", logo_svg(p, tagline=False, bg="#FFFFFF"))
        write(f"klinvexa-{p}-horizontal-transparent.svg", logo_svg(p, tagline=True))
        write(f"klinvexa-{p}-dark-bg.svg", logo_svg(f"{p}-dark", tagline=True, bg=PALETTES[p]["dark"]))
        write(f"klinvexa-{p}-dark-transparent.svg", logo_svg(f"{p}-dark", tagline=True))
        write(f"klinvexa-{p}-app-icon-light.svg", app_icon(p, "#FFFFFF"))
        write(f"klinvexa-{p}-app-icon-dark.svg", app_icon(f"{p}-dark", PALETTES[p]["dark"]))
    write("klinvexa-black.svg", logo_svg("black", tagline=True, bg="#FFFFFF", solid=True))
    write("klinvexa-white.svg", logo_svg("white", tagline=True, bg="#000000", solid=True))
    write("klinvexa-black-transparent.svg", logo_svg("black", tagline=True, solid=True))
    write("klinvexa-white-transparent.svg", logo_svg("white", tagline=True, solid=True))
    print(sorted(os.listdir(OUT)))
