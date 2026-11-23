"""Convert funding-alerts data.json -> Scaler Bee resources-page schema (funding-feed.json)."""
import json, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
TYPE = {"Grant":"Grant","Challenge":"Competition","Accelerator":"Accelerator","Fellowship":"Fellowship","Equity":"Equity Program","Debt":"Scheme"}
STAGE = {"Revenue":"Early Traction"}
def ftype(it):
    if it["type"]=="Debt": return "Debt"
    if it["equity"]=="Takes equity": return "Equity"
    if it["equity"]=="No equity": return "Non-dilutive"
    return it["equity"]
def fsource(it):
    o=(it["org"]+" "+it["title"]).lower()
    if any(k in o for k in ["govt","government","ministry","dst","birac","dpiit","tdb","kits","kerala startup","i-hub","nidhi","ssip","startinup","uttar pradesh"]): return "Government"
    if "csr" in o: return "CSR"
    if any(k in o for k in ["undp","itc &","unccd"]): return "International"
    return "Private"
def fmtdate(s):
    import datetime
    x=datetime.date.fromisoformat(s); return f"{x.day} {x.strftime('%b %Y')}"
STATES = ["Andhra Pradesh","Arunachal","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat","Haryana","Himachal","Jharkhand",
          "Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
          "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Jammu"]
def org_short(it):
    """A short organiser name people actually type into Google (ICMR, BIRAC, Karnataka…), or '' if the title already has it."""
    import re
    t = it["title"].lower()
    m = re.search(r"\(([A-Z][A-Za-z&\-]{1,9})\)", it["org"])
    if m and m.group(1).lower() not in t:
        return m.group(1)
    for s in STATES:
        if s.lower() in it["org"].lower() and s.lower() not in t and it.get("region") not in ("National", "Global"):
            return s
    return ""
def seo_title(it):
    # People search "<organiser> <scheme> last date", so put both in the title.
    import re
    when = (" — Last Date " + fmtdate(it["deadline"])) if it["deadline"] else " — Apply Now (Rolling)"
    pre = org_short(it)
    core = (pre + " " if pre else "") + it["title"]
    if len(core + when) > 70:
        core = re.sub(r"\s*\([^)]*\)", "", core).strip()          # drop bracketed extras first
    if len(core + when) > 70 and it["deadline"]:
        when = " — Last Date " + fmtdate(it["deadline"]).rsplit(" ", 1)[0]  # "30 Nov"
    t = core + when
    return t if len(t) <= 75 else core[:72].rstrip() + "…"
def meta_desc(it):
    lead = ("Last date " + fmtdate(it["deadline"]) + ". ") if it["deadline"] else "Rolling applications. "
    s = lead + it["amount"] + ". " + it["summary"]
    return s if len(s) <= 158 else s[:155].rsplit(" ",1)[0] + "…"
import datetime as _dt
_today = _dt.date.fromisoformat(d["updated"])
# Closed calls stay in the feed (active: false) for 180 days so their pages keep working
# and keep their Google ranking until the next edition. The site hides them from open lists.
_archived = [dict(a, _closed=True) for a in d.get("archive", [])
             if a.get("deadline") and (_today - _dt.date.fromisoformat(a["deadline"])).days <= 180]
feed=[]
for it in d["items"] + _archived:
    stages=[]
    for s in it["stages"]:
        s=STAGE.get(s,s)
        if s not in stages: stages.append(s)
    t=TYPE[it["type"]]
    if it["type"]=="Grant" and it["deadline"] is None and fsource(it)=="Government" and it["id"] not in ("nidhi-prayas","birac-big"): t="Scheme"
    if it["type"]=="Challenge" and it["deadline"] is None: t="Scheme" if fsource(it)=="Government" else t
    feed.append({
        "id": "auto-"+it["id"],
        "title": it["title"],
        "type": t,
        "stages": ", ".join(stages),
        "sectors": ", ".join(it["sectors"]),
        "shortDesc": it["summary"],
        "fundingAmount": it["amount"],
        "provider": it["org"],
        "geography": "India" if it["region"]=="National" else it["region"],
        "deadline": it["deadline"] or "",
        "about": it["summary"] + ((" " + it["note"]) if it.get("note") else ""),
        "eligibility": "\n".join(it["eligibility"]),
        "benefits": "\n".join(it["benefits"]),
        "fundingType": ftype(it),
        "fundingSource": fsource(it),
        "applyLink": it["link"],
        "active": not it.get("_closed", False),
        "source": "auto",
        "addedOn": it.get("added") or d["updated"],
        "slug": it["id"],
        "seoTitle": seo_title(it),
        "seoTitleClosed": ((org_short(it) + " ") if org_short(it) else "") + it["title"] + (" — Closed " + fmtdate(it["deadline"]) if it["deadline"] else ""),
        "metaDescription": meta_desc(it),
        **({"take": it["take"]} if it.get("take") else {})
    })
json.dump({"updated": d["updated"], "items": feed}, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(feed), "items ->", out)
