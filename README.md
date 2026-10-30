# Scaler Bee funding feed

Daily-updated list of open startup grants, challenges, accelerators and schemes for Indian founders.
Shown on https://scalerbee.com/TheFundGuy/resources.html

- `data.json` — master list (researched and verified daily)
- `funding-feed.json` — the file the website reads (generated: `python3 convert.py data.json funding-feed.json`)
- `validate.py` — checks `data.json` before every update
