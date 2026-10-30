"""Checks data.json before every publish. Usage: python3 validate.py data.json"""
import json, sys, re, datetime
p = sys.argv[1] if len(sys.argv) > 1 else "data.json"
d = json.load(open(p, encoding="utf-8"))
req = ["id","title","org","type","amount","amountMax","deadline","region","stages","sectors","equity","summary","eligibility","benefits","link"]
types = {"Grant","Challenge","Accelerator","Fellowship","Equity","Debt"}
stages = {"Idea","Prototype","MVP","Revenue","Growth"}
ids, errs = set(), []
for i, it in enumerate(d["items"]):
    for k in req:
        if k not in it: errs.append(f"{i} {it.get('id')}: missing {k}")
    if it.get("id") in ids: errs.append(f"duplicate id {it['id']}")
    ids.add(it.get("id"))
    if it.get("type") not in types: errs.append(f"{it.get('id')}: bad type {it.get('type')}")
    if not set(it.get("stages", [])) <= stages: errs.append(f"{it.get('id')}: bad stage")
    if it.get("deadline") is not None:
        try: datetime.date.fromisoformat(it["deadline"])
        except Exception: errs.append(f"{it.get('id')}: bad deadline")
    if not re.match(r"^https?://", it.get("link", "")): errs.append(f"{it.get('id')}: bad link")
datetime.date.fromisoformat(d["updated"])
if errs: print("\n".join(errs)); sys.exit(1)
print(f"OK: {len(d['items'])} items, updated {d['updated']}")
