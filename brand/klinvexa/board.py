"""Makes a preview picture (PNG) of the concepts: python brand/klinvexa/board.py"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
def card(title, files):
    cells = "".join(f'<div class="c"><img src="file:///{os.path.join(OUT, f).replace(chr(92), "/")}"></div>' for f in files)
    return f'<h2>{title}</h2><div class="r">{cells}</div>'
def make(name, sections, width=1200):
    html = '<style>body{margin:0;padding:28px;background:#f1f5f9;font-family:Segoe UI,Arial;width:%dpx}h2{font-size:15px;color:#334155;margin:18px 0 8px}.r{display:flex;gap:14px}.c{flex:1;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0}img{display:block;width:100%%}</style>' % width + "".join(sections)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chromium"); pg = b.new_page(viewport={"width": width + 56, "height": 600}, device_scale_factor=1.3)
        page = os.path.join(HERE, "_board.html"); open(page, "w", encoding="utf-8").write(html); pg.goto("file:///" + page.replace(chr(92), "/")); pg.wait_for_timeout(500); pg.screenshot(path=os.path.join(HERE, name), full_page=True); b.close()
if __name__ == "__main__":
    make("colour_preview.png", [
        card("Concept 1 - crossing x:  brief colours (left)  |  our colours (right)", ["klinvexa-1-crossing-x-brief.svg", "klinvexa-1-crossing-x-ours.svg"]),
        card("Concept 1 on dark", ["klinvexa-1-crossing-x-brief-dark.svg", "klinvexa-1-crossing-x-ours-dark.svg"]),
        card("Concept 2 - open K:  brief colours (left)  |  our colours (right)", ["klinvexa-2-open-k-brief.svg", "klinvexa-2-open-k-ours.svg"]),
        card("Concept 2 on dark", ["klinvexa-2-open-k-brief-dark.svg", "klinvexa-2-open-k-ours-dark.svg"]),
        card("App icon / favicon: x mark, K mark", ["klinvexa-mark-x-brief.svg", "klinvexa-mark-k-brief.svg", "klinvexa-mark-x-ours.svg", "klinvexa-mark-k-ours.svg"]),
    ])
    make("concepts_bw.png", [card(f"Concept {n}", [f"klinvexa-{k}-black.svg", f"klinvexa-{k}-white.svg"]) for n, k in ((1, "1-crossing-x"), (2, "2-open-k"), (3, "3-capitals"))])
