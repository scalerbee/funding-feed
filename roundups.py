"""Build roundup / collection pages data from data.json.

Usage: python3 roundups.py data.json roundups.json

Output (read by the website the same way as funding-feed.json):
  {"updated": "YYYY-MM-DD",
   "roundups": [ {slug, kind, title, intro, count, ids: [item ids, best first]} ],
   "weekly":   [ {slug, week, from, to, title, intro, count, ids} ]  # newest week first
  }
Item ids match data.json ids, i.e. grant.php?g=<id>.
Roundups with no items are left out so the site never shows an empty page.
"""
import json, sys, datetime, re
from collections import defaultdict

src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
items = d["items"]
today = datetime.date.fromisoformat(d["updated"])

def dl(it):
    return datetime.date.fromisoformat(it["deadline"]) if it["deadline"] else None

def is_open(it):
    x = dl(it)
    return x is None or x >= today

def text(it):
    return " ".join([it["title"], it["org"], it["summary"], " ".join(it["eligibility"]), it.get("note", "")]).lower()

def by_deadline(xs):  # soonest first, rolling last, then bigger amounts first
    return sorted(xs, key=lambda it: (dl(it) or datetime.date.max, -it["amountMax"]))

def by_amount(xs):
    return sorted(xs, key=lambda it: (-it["amountMax"], dl(it) or datetime.date.max))

def fmt(day):
    return f"{day.day} {day.strftime('%B %Y')}"

def inr(n):
    if n >= 10**7: return f"₹{n/10**7:.1f} crore".replace(".0 ", " ")
    if n >= 10**5: return f"₹{n/10**5:.0f} lakh"
    return f"₹{n:,}"

def intro(lead, xs):
    """Short factual intro built from the list itself, so every page reads differently."""
    parts = [lead]
    rolling = sum(1 for it in xs if not it["deadline"])
    dated = [it for it in xs if it["deadline"]]
    noeq = sum(1 for it in xs if it["equity"] == "No equity")
    parts.append(f"{len(xs)} open {'opportunity' if len(xs) == 1 else 'opportunities'} right now")
    bits = []
    if dated:
        nxt = min(dated, key=dl)
        bits.append(f"the next deadline is {fmt(dl(nxt))} ({nxt['title']})")
    if rolling:
        bits.append(f"{rolling} accept{'s' if rolling == 1 else ''} applications on a rolling basis")
    if noeq:
        bits.append(f"{noeq} take{'s' if noeq == 1 else ''} no equity")
    top = max(xs, key=lambda it: it["amountMax"])
    if top["amountMax"] > 0:
        bits.append(f"the largest is {top['title']} at up to {inr(top['amountMax'])}")
    s = parts[0] + " " + parts[1] + (": " + "; ".join(bits) if bits else "") + "."
    return s[0].upper() + s[1:]

open_items = [it for it in items if is_open(it)]
roundups = []

def add(slug, kind, title, lead, xs, order=by_deadline):
    xs = order(xs)
    if not xs: return
    roundups.append({"slug": slug, "kind": kind, "title": title, "intro": intro(lead, xs),
                     "count": len(xs), "ids": [it["id"] for it in xs]})

# --- time-based ---
new7 = [it for it in open_items if it.get("added") and (today - datetime.date.fromisoformat(it["added"])).days < 7]
add("new-this-week", "time", "New startup funding opportunities this week",
    "Grants, challenges and accelerators added to The Fund Guy in the last 7 days.", new7)
soon = [it for it in open_items if dl(it) and (dl(it) - today).days <= 14]
add("closing-soon", "time", "Startup grants and challenges closing in the next 14 days",
    "Apply soon: these calls close within two weeks.", soon)
add("rolling", "time", "Startup grants and schemes open all year (rolling)",
    "No fixed last date: these schemes take applications throughout the year.",
    [it for it in open_items if not it["deadline"]], by_amount)

# --- money ---
add("no-equity", "money", "Non-dilutive startup funding (no equity taken)",
    "Grants, prizes and schemes that do not take a stake in your company.",
    [it for it in open_items if it["equity"] == "No equity"], by_amount)
add("above-1-crore", "money", "Startup funding of ₹1 crore or more",
    "Large cheques: programmes offering ₹1 crore or more per startup.",
    [it for it in open_items if it["amountMax"] >= 10**7], by_amount)
add("under-10-lakh", "money", "Small startup grants up to ₹10 lakh",
    "Smaller, faster grants for validating an idea or building a prototype.",
    [it for it in open_items if 0 < it["amountMax"] <= 10**6], by_amount)

# --- who ---
women = [it for it in open_items if re.search(r"\bwom[ae]n\b|\bfemale\b|\bfemtech\b|\bshe\b", text(it))]
add("women-founders", "who", "Startup grants and programmes for women founders",
    "Calls that are reserved for, or give priority to, women-led startups.", women)
students = [it for it in open_items if re.search(r"\bstudents?\b|\bcollege\b|\buniversity students?\b", text(it))]
add("students", "who", "Startup funding open to students",
    "Opportunities that student founders and campus teams can apply for.", students)

# --- type / stage / scope ---
TYPE_T = {"Grant": "Startup grants", "Challenge": "Startup challenges and competitions",
          "Accelerator": "Startup accelerators and incubation programmes", "Fellowship": "Founder fellowships",
          "Equity": "Equity investment programmes", "Debt": "Loans and debt schemes for startups"}
for t, title in TYPE_T.items():
    add("type-" + t.lower(), "type", f"{title} open now", f"{title} currently accepting applications.",
        [it for it in open_items if it["type"] == t])
STAGE_T = {"Idea": "idea stage", "Prototype": "prototype stage", "MVP": "MVP stage",
           "Revenue": "early-revenue", "Growth": "growth-stage"}
for s, label in STAGE_T.items():
    add("stage-" + s.lower(), "stage", f"Funding for {label} startups", f"Open calls that fit {label} startups.",
        [it for it in open_items if s in it["stages"]])
add("government", "scope", "Government startup schemes and grants in India",
    "Central ministries, government agencies and state startup missions.",
    [it for it in open_items if re.search(r"govt|government|ministry|department|dst\b|birac|dpiit|niti|mission|council|icmr|meity", it["org"].lower())])
add("india-national", "scope", "Pan-India startup funding opportunities",
    "Open to startups from any Indian state.", [it for it in open_items if it["region"] == "National"])
add("global-open-to-india", "scope", "Global grants and challenges Indian startups can apply for",
    "International calls that accept applications from India.", [it for it in open_items if it["region"] == "Global"])

# --- states ---
states = defaultdict(list)
for it in open_items:
    if it["region"] not in ("National", "Global"):
        states[it["region"]].append(it)
for st, xs in sorted(states.items()):
    add("state-" + re.sub(r"[^a-z0-9]+", "-", st.lower()).strip("-"), "state", f"Startup grants and schemes in {st}",
        f"Funding for startups based in {st}.", xs, by_amount)

# --- sectors (only ones with 3+ open items, to avoid thin pages) ---
SECTOR_GROUPS = {
    "ai": ("AI and deep-tech", r"\bai\b|artificial intelligence|machine learning|deep ?tech|agents"),
    "climate": ("climate, energy and sustainability", r"climate|clean ?energy|energy|sustainab|circular|carbon|water|plastic"),
    "health": ("healthtech, medtech and biotech", r"health|med ?tech|medical|biotech|diagnostic|pharma|femtech"),
    "agri": ("agritech and food", r"agri|farm|food"),
    "fintech": ("fintech", r"fintech|financial|insurance|banking"),
    "social-impact": ("social impact", r"social impact|livelihood|inclusion|rural"),
    "mobility": ("mobility and EV", r"mobility|\bev\b|electric vehicle|transport"),
    "defence": ("defence and aerospace", r"defen[cs]e|aerospace|space"),
}
for key, (label, rx) in SECTOR_GROUPS.items():
    xs = [it for it in open_items if re.search(rx, " ".join(it["sectors"]).lower())]
    if len(xs) >= 3:
        add("sector-" + key, "sector", f"Startup funding for {label}", f"Open calls for {label} startups.", xs)

# --- weekly archive: items added in each ISO week (kept even after they close, for the archive) ---
weeks = defaultdict(list)
for it in items:
    if it.get("added"):
        a = datetime.date.fromisoformat(it["added"])
        y, w, _ = a.isocalendar()
        weeks[(y, w)].append(it)
weekly = []
for (y, w), xs in sorted(weeks.items(), reverse=True):
    start = datetime.date.fromisocalendar(y, w, 1); end = start + datetime.timedelta(days=6)
    xs = by_deadline(xs)
    still = [it for it in xs if is_open(it)]
    lead = f"Startup funding opportunities added to The Fund Guy between {fmt(start)} and {fmt(end)}."
    weekly.append({"slug": f"week-{y}-w{w:02d}", "week": f"{y}-W{w:02d}", "from": start.isoformat(), "to": end.isoformat(),
                   "title": f"{len(xs)} new startup funding {'opportunity' if len(xs) == 1 else 'opportunities'}: week of {fmt(start)}",
                   "intro": lead + (f" {len(still)} of {len(xs)} {'is' if len(still) == 1 else 'are'} still open." if len(xs) > 1 else (" It is still open." if still else " It has now closed.")),
                   "count": len(xs), "ids": [it["id"] for it in xs]})

json.dump({"updated": d["updated"], "roundups": roundups, "weekly": weekly},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(roundups)} roundups, {len(weekly)} weekly archives -> {out}")
