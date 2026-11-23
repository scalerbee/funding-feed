"""Build a LinkedIn PDF carousel (1080x1350 slides) of investors from a JSON spec.

Usage: python linkedin/carousel.py spec.json out.pdf [--png-dir DIR]

Spec:
{
  "kicker": "INVESTOR LIST #1",                      # small label on the cover
  "title": "10 Singapore VCs that back Indian founders",
  "subtitle": "Stage, cheque size and how to reach each one",
  "investors": [
    {"name": "...", "hq": "Singapore", "type": "VC fund", "stage": "Seed to Series A",
     "cheque": "US$0.5M–3M", "sectors": ["SaaS", "Fintech"],
     "india_portfolio": ["Company A", "Company B"],
     "reach": "website.com/apply", "note": "One practical line (optional)"}
  ],
  "cta_url": "scalerbee.com/TheFundGuy/contact.html"
}
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
NAVY, NAVY2, GOLD, CREAM = "#0b1f3a", "#13305a", "#d4a83a", "#f6f1e4"


def e(s):
    return html.escape(str(s or ""))


def css():
    faces = "".join(
        f"@font-face{{font-family:P;font-weight:{w};src:url('file://{FONTS}/Poppins-{n}.ttf')}}"
        for n, w in [("Light", 300), ("Regular", 400), ("Medium", 500), ("Bold", 700)])
    return faces + f"""
@page {{ size: 1080px 1350px; margin: 0 }}
* {{ box-sizing: border-box; margin: 0; padding: 0 }}
body {{ font-family: P, sans-serif; }}
.slide {{ width:1080px; height:1350px; position:relative; overflow:hidden; page-break-after:always;
  background: radial-gradient(1200px 900px at 85% -10%, {NAVY2} 0%, {NAVY} 60%); color:#fff; padding:80px 72px; }}
.ring {{ position:absolute; border:2px solid rgba(212,168,58,.22); border-radius:50%; }}
.r1 {{ width:520px; height:520px; right:-170px; top:-170px }}
.r2 {{ width:360px; height:360px; right:-90px; top:-90px }}
.kicker {{ color:{GOLD}; font-weight:600; letter-spacing:5px; font-size:32px; text-transform:uppercase }}
.cover h1 {{ font-size:112px; line-height:1.08; font-weight:700; margin-top:60px }}
.cover h1 b {{ color:{GOLD} }}
.cover .sub {{ font-size:46px; font-weight:400; color:#dfe6f2; margin-top:44px; line-height:1.4; max-width:860px }}
.swipe {{ position:absolute; bottom:190px; left:72px; font-size:40px; color:{GOLD}; font-weight:500 }}
.foot {{ position:absolute; left:72px; right:72px; bottom:60px; display:flex; justify-content:space-between;
  font-size:28px; letter-spacing:3px; color:#9fb0cc; border-top:1px solid rgba(255,255,255,.15); padding-top:26px }}
.foot b {{ color:{GOLD}; font-weight:600 }}
.num {{ font-size:34px; color:{GOLD}; font-weight:600; letter-spacing:4px }}
.inv h2 {{ font-size:84px; line-height:1.05; font-weight:700; margin-top:18px }}
.tags {{ margin-top:22px; display:flex; gap:14px; flex-wrap:wrap }}
.tag {{ border:1.5px solid {GOLD}; color:{GOLD}; border-radius:40px; padding:8px 26px; font-size:32px; font-weight:500 }}
.grid {{ margin-top:40px; display:grid; grid-template-columns:1fr 1fr; gap:20px }}
.cell {{ background:rgba(255,255,255,.06); border-radius:22px; padding:22px 28px }}
.cell.full {{ grid-column:1 / span 2 }}
.lab {{ font-size:26px; letter-spacing:3px; color:#9fb0cc; text-transform:uppercase; font-weight:500 }}
.val {{ font-size:44px; margin-top:6px; line-height:1.2; font-weight:600 }}
.val.small {{ font-size:38px; font-weight:500 }}
.reach {{ color:{GOLD}; word-break:break-all }}
.note {{ margin-top:26px; font-size:34px; color:#dfe6f2; font-weight:400; line-height:1.45;
  border-left:5px solid {GOLD}; padding-left:24px }}
.cta {{ background:{CREAM}; color:{NAVY} }}
.cta .kicker {{ color:#a07c1f }}
.cta h1 {{ font-size:96px; line-height:1.12; font-weight:700; margin-top:70px }}
.cta h1 b {{ color:#a07c1f }}
.cta p {{ font-size:44px; margin-top:44px; line-height:1.45; color:#2b3b55; max-width:880px }}
.btn {{ display:inline-block; margin-top:60px; background:{NAVY}; color:#fff; font-size:40px; font-weight:600;
  border-radius:60px; padding:28px 52px }}
.url {{ margin-top:30px; font-size:38px; color:#a07c1f; font-weight:600 }}
.cta .foot {{ color:#6b7a93; border-top-color:rgba(11,31,58,.15) }}
"""


def foot(i, n):
    return f'<div class="foot"><span><b>THE FUND GUY</b> · SCALER BEE</span><span>{i} / {n}</span></div>'


def build_html(spec):
    inv = spec["investors"]
    n = len(inv) + 2
    title = e(spec["title"])
    # highlight the leading number / first words in gold
    parts = title.split(" ", 1)
    title_html = f"<b>{parts[0]}</b> {parts[1]}" if len(parts) == 2 else title
    out = [f"""<section class="slide cover"><div class="ring r1"></div><div class="ring r2"></div>
<div class="kicker">{e(spec.get('kicker', 'INVESTOR LIST'))}</div><h1>{title_html}</h1>
<div class="sub">{e(spec.get('subtitle', ''))}</div><div class="swipe">Swipe →</div>{foot(1, n)}</section>"""]
    for k, v in enumerate(inv, 1):
        tags = "".join(f'<span class="tag">{e(t)}</span>' for t in [v.get("hq"), v.get("type")] if t)
        port = ", ".join(v.get("india_portfolio") or []) or "—"
        sectors = ", ".join(v.get("sectors") or []) or "Sector-agnostic"
        note = f'<div class="note">{e(v["note"])}</div>' if v.get("note") else ""
        out.append(f"""<section class="slide inv"><div class="ring r2"></div>
<div class="fit"><div class="num">{k:02d} / {len(inv):02d}</div><h2>{e(v['name'])}</h2><div class="tags">{tags}</div>
<div class="grid">
 <div class="cell"><div class="lab">Stage</div><div class="val">{e(v.get('stage'))}</div></div>
 <div class="cell"><div class="lab">Cheque size</div><div class="val">{e(v.get('cheque') or 'Not disclosed')}</div></div>
 <div class="cell full"><div class="lab">Sectors</div><div class="val small">{e(sectors)}</div></div>
 <div class="cell full"><div class="lab">Backed in India</div><div class="val small">{e(port)}</div></div>
 <div class="cell full"><div class="lab">How to reach</div><div class="val small reach">{e(v.get('reach'))}</div></div>
</div>{note}</div>{foot(k + 1, n)}</section>""")
    url = e(spec.get("cta_url", "scalerbee.com/TheFundGuy/contact.html"))
    out.append(f"""<section class="slide cta"><div class="kicker">THE FUND GUY · SCALER BEE</div>
<h1>Raising funds?<br><b>Get an expert</b> in your corner.</h1>
<p>Pitch deck, financial model, valuation and investor outreach — we help pre-seed to Series A founders get investor-ready.</p>
<div class="btn">Reach out to us</div><div class="url">{url}</div>{foot(n, n)}</section>""")
    return f"<html><head><meta charset='utf-8'><style>{css()}</style></head><body>{''.join(out)}</body></html>"


def render(spec, pdf_path, png_dir=None):
    from playwright.sync_api import sync_playwright
    doc = build_html(spec)
    tmp = os.path.join(os.path.dirname(os.path.abspath(pdf_path)) or ".", "_carousel.html")
    open(tmp, "w", encoding="utf-8").write(doc)
    exe = os.environ.get("CHROME_PATH")
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto("file://" + tmp)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(500)
        # shrink a slide's content slightly if it would run into the footer
        pg.evaluate("""() => document.querySelectorAll('section.slide').forEach(sl => {
            const fit = sl.querySelector('.fit'), foot = sl.querySelector('.foot');
            if (!fit || !foot) return;
            let k = 1;
            while (k > 0.7 && fit.getBoundingClientRect().bottom > foot.getBoundingClientRect().top - 24) {
                k -= 0.02; fit.style.zoom = k;
            }
        })""")
        pg.pdf(path=pdf_path, width="1080px", height="1350px", print_background=True)
        if png_dir:
            os.makedirs(png_dir, exist_ok=True)
            for i, el in enumerate(pg.query_selector_all("section.slide"), 1):
                el.screenshot(path=os.path.join(png_dir, f"slide{i:02d}.png"))
        b.close()
    os.remove(tmp)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    png = sys.argv[sys.argv.index("--png-dir") + 1] if "--png-dir" in sys.argv else None
    render(spec, sys.argv[2], png)
    print("Wrote", sys.argv[2])
