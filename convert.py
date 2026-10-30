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
feed=[]
for it in d["items"]:
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
        "active": True,
        "source": "auto",
        "addedOn": d["updated"],
        "slug": it["id"],
        **({"take": it["take"]} if it.get("take") else {})
    })
json.dump({"updated": d["updated"], "items": feed}, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(feed), "items ->", out)
