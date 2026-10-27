"""Preview sheet of the final direction: python brand/klinvexa/board_final.py"""
import os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "final")
def img(n, extra=""): return f'<img {extra} src="file:///{os.path.join(F, n).replace(chr(92), "/")}">'
def sheet(p, title):
    return f'''<h2>{title}</h2><div class="g">
<div class="big">{img(f"klinvexa-{p}-horizontal.svg")}</div>
<div class="ic"><div>{img(f"klinvexa-{p}-app-icon-light.svg")}<span>App icon (light)</span></div><div>{img(f"klinvexa-{p}-app-icon-dark.svg")}<span>App icon (dark)</span></div></div>
<div class="row3"><div class="w">{img(f"klinvexa-{p}-wordmark.svg")}<span>Without tagline</span></div><div class="w d">{img(f"klinvexa-{p}-dark-bg.svg")}<span>On dark</span></div>
<div class="w">{img("klinvexa-black.svg")}<span>Black and white</span></div><div class="w d">{img("klinvexa-white.svg")}<span>White on black</span></div></div></div>'''
html = '''<style>body{margin:0;padding:26px;background:#eef2f6;font-family:Segoe UI,Arial;width:1340px}h2{font-size:16px;color:#334155;margin:22px 0 10px}
.g{display:grid;grid-template-columns:2fr 1fr;gap:14px}.big{background:#fff;border-radius:14px;border:1px solid #e2e8f0;padding:16px}.big img{width:100%;display:block}
.ic{display:flex;gap:14px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;padding:16px;align-items:center;justify-content:center}.ic div{text-align:center;font-size:12px;color:#64748b}.ic img{width:130px;display:block;margin-bottom:8px}
.row3{grid-column:1/-1;display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.w{background:#fff;border-radius:14px;border:1px solid #e2e8f0;padding:12px;text-align:center;font-size:12px;color:#64748b}.w.d{background:#0f172a}.w img{width:100%;display:block;margin-bottom:6px}</style>'''
html += sheet("brief", "A. Brief colours (navy, blue, teal)") + sheet("ours", "B. Our software colours (charcoal, orange, teal)")
page = os.path.join(HERE, "_final.html"); open(page, "w", encoding="utf-8").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(channel="chromium"); pg = b.new_page(viewport={"width": 1400, "height": 800}, device_scale_factor=1.2)
    pg.goto("file:///" + page.replace(chr(92), "/")); pg.wait_for_timeout(600); pg.screenshot(path=os.path.join(HERE, "final_preview.png"), full_page=True); b.close()
os.remove(page)
