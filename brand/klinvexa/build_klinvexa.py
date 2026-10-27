"""
Builds the Klinvexa wordmark concepts as pure vector paths (no font needed to open the SVG).
Letters come from the Satoshi Bold font (free licence, see backend/assets/fonts), the custom letters are drawn here.

    python brand/klinvexa/build_klinvexa.py          # writes SVG files into brand/klinvexa/out/

SAFE TO EDIT: the colours in PALETTES and the numbers at the top of each concept.
"""
import os
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "..", "backend", "assets", "fonts", "Satoshi-Bold.otf")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

font = TTFont(FONT)
glyphs = font.getGlyphSet()
cmap = font.getBestCmap()
XH = 494       # x-height of Satoshi Bold
CAP = 731      # cap height
STEM = 121     # width of the straight stem of the letter "l"

PALETTES = {
    # the colours from the Klinvexa brief
    "brief": {"dark": "#0F172A", "main": "#2563EB", "accent": "#14B8A6"},
    # the software's own colours (charcoal, ember orange, teal)
    "ours": {"dark": "#1F2430", "main": "#E0560F", "accent": "#0F8F84"},
    "brief-dark": {"dark": "#FFFFFF", "main": "#3B82F6", "accent": "#2DD4BF"},
    "ours-dark": {"dark": "#FFFFFF", "main": "#FF7A33", "accent": "#2DD4BF"},
    "black": {"dark": "#000000", "main": "#000000", "accent": "#000000"},
    "white": {"dark": "#FFFFFF", "main": "#FFFFFF", "accent": "#FFFFFF"},
}


def glyph(ch, x):
    """SVG path of one letter, with its left edge at x (font units, y up -> SVG y down). Returns (d, advance)."""
    name = cmap[ord(ch)]
    pen = SVGPathPen(glyphs)
    glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
    return pen.getCommands(), font["hmtx"][name][0]


def bar(x0, y0, x1, y1, w):
    """A slanted bar from (x0,y0) to (x1,y1), w wide (measured sideways). Returns an SVG path."""
    return f"M{x0:.1f} {-y0:.1f}L{x0 + w:.1f} {-y0:.1f}L{x1 + w:.1f} {-y1:.1f}L{x1:.1f} {-y1:.1f}Z"


def shift(path, dx):
    """Moves a bar path sideways by dx (it is a simple M/L/Z path)."""
    import re
    return re.sub(r"([ML])(-?[\d.]+) (-?[\d.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) + dx:.1f} {m.group(3)}", path)


def x_crossing(x, gap=60, w=150, width=500, nudge=14):
    """The custom x: one bar is whole, the other is cut where they cross. Returns (main_parts, accent_part)."""
    x0, x1 = x + 8, x + width - w - 8
    whole = bar(x0, XH, x1, 0, w)            # top-left -> bottom-right, unbroken
    mid = 0.5
    span = gap / XH
    def piece(t0, t1):
        return bar(x0 + (x1 - x0) * t0, XH * t0, x0 + (x1 - x0) * t1, XH * t1, w)
    lower = piece(0, mid - span)             # bottom-left half
    upper = piece(mid + span, 1)             # top-right half (gets the accent colour)
    upper = shift(upper, nudge)
    return [whole, lower], upper


def k_detached(x, gap=64):
    """The custom K: the upper arm is detached from the stem (a small cut). Returns (path, advance)."""
    stem = f"M{x + 81} 0V{-CAP}H{x + 81 + STEM}V0Z"
    w = 160
    sx = x + 81 + STEM
    leg = bar(sx - 60, CAP * 0.36, x + 650 - w, 0, w)
    arm = bar(sx + gap, CAP * 0.50, x + 655 - w, CAP, w)
    return stem + leg + arm, 674


def build_word(spec, tracking=-6):
    """spec: list of letters, or ("custom", name). Returns (list of (path, role)), width."""
    parts, x = [], 0
    for item in spec:
        if item == "x*":
            main, accent = x_crossing(x)
            parts += [(p, "main") for p in main]
            parts.append((accent, "accent"))
            x += 513 + tracking
        elif item == "K*":
            d, adv = k_detached(x)
            parts.append((d, "dark"))
            x += adv + tracking
        else:
            d, adv = glyph(item[0], x)
            role = item[1] if len(item) > 1 else "dark"
            parts.append((d, role))
            x += adv + tracking
    return parts, x


def colour_of(role, pal, scheme):
    if scheme == "split":                      # "Klin" dark, "vexa" main, accent piece in accent colour
        return {"dark": pal["dark"], "main": pal["main"], "accent": pal["accent"]}[role]
    return pal["dark"]                         # one solid colour


def svg(parts, width, pal, scheme="split", tagline=None, pad=60, bg=None):
    top, bottom = CAP + pad, 0 + pad
    h = top + bottom + (170 if tagline else 0)
    w = width + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="Klinvexa">',
           "<title>Klinvexa</title>"]
    if bg:
        out.append(f'<rect width="{w:.0f}" height="{h:.0f}" fill="{bg}"/>')
    out.append(f'<g transform="translate({pad} {top})">')
    for d, role in parts:
        out.append(f'<path d="{d}" fill="{colour_of(role, pal, scheme)}"/>')
    out.append("</g>")
    if tagline:
        # the tagline is plain text; for final delivery it is turned into paths too
        tag_parts, tag_w = build_text(tagline, size=0.19)
        out.append(f'<g transform="translate({pad} {top + 150}) scale({0.19})" fill="{pal["dark"]}" fill-opacity="0.7">')
        for d in tag_parts:
            out.append(f'<path d="{d}"/>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def build_text(text, size, tracking=60):
    parts, x = [], 0
    for ch in text:
        if ch == " ":
            x += 260
            continue
        d, adv = glyph(ch, x)
        parts.append(d)
        x += adv + tracking
    return parts, x


# ---- the three concepts -------------------------------------------------------------------------
CONCEPTS = {
    # 1: crossing x - one stroke is cut where the strokes cross
    "1-crossing-x": ["K", "l", "i", "n", ("v", "main"), ("e", "main"), "x*", ("a", "main")],
    # 2: detached K - the upper arm of the K is cut away from the stem (a quiet "open / connected" detail)
    "2-open-k": ["K*", "l", "i", "n", ("v", "main"), ("e", "main"), ("x", "main"), ("a", "main")],
    # 3: capitals with wide spacing (calm, architectural)
    "3-capitals": ["K", "L", "I", "N", ("V", "main"), ("E", "main"), ("X", "main"), ("A", "main")],
}

def mark_svg(kind, pal, tile, size=100):
    """The compact app-icon mark: the custom letter from the wordmark on a rounded tile. kind: "x" or "k"."""
    if kind == "x":
        main, accent = x_crossing(0, width=500)
        w, h, body = 500, XH, "".join(f'<path d="{d}" fill="{pal["dark"]}"/>' for d in main) + f'<path d="{accent}" fill="{pal["accent"]}"/>'
    else:
        d, adv = k_detached(-81)
        w, h, body = 600, CAP, f'<path d="{d}" fill="{pal["dark"]}"/>'
    scale = 54 / max(w, h)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">'
            f'<rect width="100" height="100" rx="24" fill="{tile}"/>'
            f'<g transform="translate({(100 - w * scale) / 2:.1f} {(100 + h * scale) / 2:.1f}) scale({scale:.4f})">{body}</g></svg>')


if __name__ == "__main__":
    for name, spec in CONCEPTS.items():
        tr = 70 if name.startswith("3") else -6
        parts, width = build_word(spec, tracking=tr)
        for pal_name, bg in (("black", "#FFFFFF"), ("white", "#000000")):
            with open(os.path.join(OUT, f"klinvexa-{name}-{pal_name}.svg"), "w", encoding="utf-8") as f:
                f.write(svg(parts, width, PALETTES[pal_name], scheme="solid", bg=bg))
        for pal_name in ("brief", "ours"):
            with open(os.path.join(OUT, f"klinvexa-{name}-{pal_name}.svg"), "w", encoding="utf-8") as f:
                f.write(svg(parts, width, PALETTES[pal_name], scheme="split", bg="#FFFFFF"))
    for name in ("1-crossing-x", "2-open-k"):
        parts, width = build_word(CONCEPTS[name], tracking=-6)
        for pal_name in ("brief-dark", "ours-dark"):
            with open(os.path.join(OUT, f"klinvexa-{name}-{pal_name}.svg"), "w", encoding="utf-8") as f:
                f.write(svg(parts, width, PALETTES[pal_name], scheme="split", bg=PALETTES[pal_name.replace("-dark", "")]["dark"]))
    for pal_name in ("brief", "ours"):
        pal = dict(PALETTES[pal_name], dark="#FFFFFF")
        for kind in ("x", "k"):
            with open(os.path.join(OUT, f"klinvexa-mark-{kind}-{pal_name}.svg"), "w", encoding="utf-8") as f:
                f.write(mark_svg(kind, pal, PALETTES[pal_name]["main"] if kind == "k" else PALETTES[pal_name]["dark"]))
    print("done:", sorted(os.listdir(OUT)))
