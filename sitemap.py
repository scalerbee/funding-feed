"""Build sitemap.xml for every opportunity page + the hub pages.
Usage: python3 sitemap.py data.json sitemap.xml
Upload/serve it as https://scalerbee.com/TheFundGuy/sitemap.xml (or have a PHP page proxy the raw GitHub file),
then submit that URL in Google Search Console."""
import json, sys
from xml.sax.saxutils import escape
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
base = "https://scalerbee.com/TheFundGuy/"
urls = [(base + "resources.html", d["updated"], "daily", "1.0"), (base + "grants.php", d["updated"], "daily", "0.9")]
for it in d["items"]:
    urls.append((base + "grant.php?g=" + it["id"], d["updated"], "weekly", "0.8"))
with open(out, "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for loc, lm, cf, pr in urls:
        f.write(f"  <url><loc>{escape(loc)}</loc><lastmod>{lm}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>\n")
    f.write("</urlset>\n")
print(len(urls), "urls ->", out)
