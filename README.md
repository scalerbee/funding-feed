# Scaler Bee funding feed

Daily-updated list of open startup grants, challenges, accelerators and schemes for Indian founders.
Shown on https://scalerbee.com/TheFundGuy/resources.html

- `data.json` — master list (researched and verified daily)
- `funding-feed.json` — the file the website reads (generated: `python3 convert.py data.json funding-feed.json`)
- `validate.py` — checks `data.json` before every update
- `roundups.json` — collection pages for the site (generated: `python3 roundups.py data.json roundups.json`):
  `roundups` = new this week, closing soon, rolling, no-equity, women founders, students, by type/stage/state/sector;
  `weekly` = archive of what was added each week. Each entry has `slug`, `title`, `intro`, `count` and `ids` (= `grant.php?g=<id>`).
  Read it from https://raw.githubusercontent.com/scalerbee/funding-feed/main/roundups.json
- Each item in `data.json` carries `added` (YYYY-MM-DD, the day it was first listed); the feed exposes it as `addedOn`.

- `sitemap.xml` — every opportunity page (generated: `python3 sitemap.py data.json sitemap.xml`). Serve it at scalerbee.com/TheFundGuy/sitemap.xml and submit it in Google Search Console.
- Each feed item also carries `seoTitle` and `metaDescription` — use them for the page `<title>` and `<meta name="description">` on grant.php.
