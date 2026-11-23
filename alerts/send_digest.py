"""Weekly matched-opportunity emails for The Fund Guy subscribers (via Brevo).

Runs daily from .github/workflows/email-digest.yml. Each subscriber is assigned one weekday
(from a hash of their email), so everyone gets ONE email a week and the daily send stays
under Brevo's free limit (300/day). The email lists opportunities that match the person's
stage / sector / state: new in the last 7 days first, then ones closing in the next 14 days.
Nobody is emailed if nothing matches that week.

Env (GitHub secrets): BREVO_API_KEY, BREVO_LIST_ID, SENDER_EMAIL, UNSUB_SECRET
Optional env: SENDER_NAME (default "The Fund Guy by Scaler Bee"), DRY_RUN=1 (print, don't send),
DAILY_CAP (default 280), FORCE_ALL=1 (ignore weekday buckets, e.g. for a test run).

Subscriber attributes in Brevo (created automatically if missing):
  FG_STAGE  = Idea|Prototype|MVP|Revenue|Growth|any
  FG_SECTOR = ai|climate|health|agri|fintech|social-impact|mobility|defence|any
  FG_STATE  = an Indian state name, or any
"""
import datetime, hashlib, hmac, html, json, os, re, sys, urllib.parse, urllib.request, urllib.error

API = "https://api.brevo.com/v3"
KEY = os.environ.get("BREVO_API_KEY", "")
LIST_ID = int(os.environ.get("BREVO_LIST_ID", "0") or 0)
SENDER = {"email": os.environ.get("SENDER_EMAIL", ""), "name": os.environ.get("SENDER_NAME") or "The Fund Guy by Scaler Bee"}
UNSUB_SECRET = os.environ.get("UNSUB_SECRET", "")
DRY = os.environ.get("DRY_RUN") == "1"
FORCE_ALL = os.environ.get("FORCE_ALL") == "1"
CAP = int(os.environ.get("DAILY_CAP", "280"))
SITE = "https://scalerbee.com/TheFundGuy/"
ATTRS = ["FG_STAGE", "FG_SECTOR", "FG_STATE"]

# Same sector groups as roundups.py, so emails and collection pages agree.
SECTOR_RX = {
    "ai": r"\bai\b|artificial intelligence|machine learning|deep ?tech|agents|quantum",
    "climate": r"climate|clean ?energy|energy|sustainab|circular|carbon|water|plastic",
    "health": r"health|med ?tech|medical|biotech|diagnostic|pharma|femtech",
    "agri": r"agri|farm|food",
    "fintech": r"fintech|financial|insurance|banking",
    "social-impact": r"social impact|livelihood|inclusion|rural",
    "mobility": r"mobility|\bev\b|electric vehicle|transport",
    "defence": r"defen[cs]e|aerospace|space",
}


def call(method, path, body=None, ok=(200, 201, 204)):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": KEY, "accept": "application/json", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        return e.code, {"error": txt}


def ensure_attributes():
    for a in ATTRS:
        code, res = call("POST", f"/contacts/attributes/normal/{a}", {"type": "text"})
        if code not in (200, 201, 204) and "already" not in json.dumps(res).lower():
            print(f"note: could not create attribute {a}: {code} {res}")


def subscribers():
    out, offset = [], 0
    while True:
        code, res = call("GET", f"/contacts/lists/{LIST_ID}/contacts?limit=500&offset={offset}")
        if code != 200:
            sys.exit(f"ERROR reading Brevo list {LIST_ID}: {code} {res}")
        batch = res.get("contacts", [])
        out += [c for c in batch if not c.get("emailBlacklisted")]
        offset += len(batch)
        if not batch or offset >= res.get("count", 0):
            return out


def token(email):
    return hmac.new(UNSUB_SECRET.encode(), email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def bucket(email):
    return int(hashlib.sha256(email.lower().encode()).hexdigest(), 16) % 7


def matches(it, stage, sector, state):
    if stage and stage != "any" and it["stages"] and stage not in it["stages"]:
        return False
    if state and state != "any" and it["region"] not in ("National", "Global", state):
        return False
    if sector and sector != "any":
        rx = SECTOR_RX.get(sector)
        if rx and not re.search(rx, " ".join(it["sectors"]).lower()) and "agnostic" not in " ".join(it["sectors"]).lower() and "all sectors" not in " ".join(it["sectors"]).lower():
            return False
    return True


def pick(items, today, stage, sector, state, n=8):
    def dl(it): return datetime.date.fromisoformat(it["deadline"]) if it["deadline"] else None
    live = [it for it in items if (dl(it) is None or dl(it) >= today + datetime.timedelta(days=2)) and matches(it, stage, sector, state)]
    new = [it for it in live if it.get("added") and (today - datetime.date.fromisoformat(it["added"])).days < 7]
    def rank(it):  # the subscriber's own state first, then pan-India, then global; bigger cheques first
        r = 0 if (state not in ("", "any") and it["region"] == state) else 1 if it["region"] != "Global" else 2
        return (r, -it["amountMax"], dl(it) or datetime.date.max)
    new.sort(key=rank)
    soon = [it for it in live if it not in new and dl(it) and (dl(it) - today).days <= 14]
    soon.sort(key=lambda it: (0 if it["region"] != "Global" else 1, dl(it)))
    return new[:n], soon[: max(0, n - len(new[:n]))]


def fmt(s):
    x = datetime.date.fromisoformat(s)
    return f"{x.day} {x.strftime('%b %Y')}"


def card(it):
    url = SITE + "grant.php?g=" + it["id"] + "&utm_source=brevo&utm_medium=email&utm_campaign=weekly_match"
    when = ("Last date: " + fmt(it["deadline"])) if it["deadline"] else "Rolling applications"
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid #eee">'
            f'<a href="{html.escape(url)}" style="font-size:16px;font-weight:600;color:#1a56db;text-decoration:none">{html.escape(it["title"])}</a>'
            f'<div style="font-size:13px;color:#555;margin:4px 0">{html.escape(it["org"])} · {html.escape(it["amount"])} · <b>{when}</b></div>'
            f'<div style="font-size:14px;color:#222">{html.escape(it["summary"])}</div></td></tr>')


def email_html(email, new, soon, prefs):
    unsub = SITE + "unsubscribe.php?" + urllib.parse.urlencode({"e": email, "t": token(email)})
    rows = ""
    if new:
        rows += '<tr><td style="padding-top:10px;font-size:13px;letter-spacing:.5px;color:#888">NEW THIS WEEK</td></tr>' + "".join(card(i) for i in new)
    if soon:
        rows += '<tr><td style="padding-top:18px;font-size:13px;letter-spacing:.5px;color:#888">CLOSING SOON</td></tr>' + "".join(card(i) for i in soon)
    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:8px;padding:24px">
<tr><td style="font-size:20px;font-weight:700;color:#111">Your startup funding matches this week</td></tr>
<tr><td style="font-size:14px;color:#555;padding-top:6px">Picked for: {html.escape(prefs)}. Every listing is checked against the official source.</td></tr>
{rows}
<tr><td style="padding-top:20px"><a href="{SITE}resources.html?utm_source=brevo&utm_medium=email&utm_campaign=weekly_match" style="background:#1a56db;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-size:14px">See all open opportunities</a></td></tr>
<tr><td style="font-size:13px;color:#555;padding-top:18px">Need help with an application? Just reply to this email and the Scaler Bee team will get back to you.</td></tr>
<tr><td style="font-size:11px;color:#999;padding-top:22px">You get this because you signed up for The Fund Guy alerts on scalerbee.com. <a href="{html.escape(unsub)}" style="color:#999">Unsubscribe</a></td></tr>
</table></td></tr></table></body></html>"""


def main():
    data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data.json"), encoding="utf-8"))
    items = data["items"]
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).date()
    if not DRY:
        missing = [k for k, v in {"BREVO_API_KEY": KEY, "BREVO_LIST_ID": LIST_ID, "SENDER_EMAIL": SENDER["email"], "UNSUB_SECRET": UNSUB_SECRET}.items() if not v]
        if missing:
            sys.exit("ERROR missing secrets: " + ", ".join(missing))
        ensure_attributes()
        subs = subscribers()
    else:
        subs = json.loads(os.environ.get("DRY_SUBS", '[{"email":"test@example.com","attributes":{"FG_STAGE":"MVP","FG_SECTOR":"health","FG_STATE":"Karnataka"}}]'))
        UNSUB = UNSUB_SECRET or "dry"
        globals()["UNSUB_SECRET"] = UNSUB
    day = today.weekday()
    sent = skipped = 0
    for c in subs:
        email = c["email"]
        if not FORCE_ALL and bucket(email) != day:
            continue
        a = c.get("attributes", {}) or {}
        stage, sector, state = (a.get("FG_STAGE") or "any"), (a.get("FG_SECTOR") or "any"), (a.get("FG_STATE") or "any")
        new, soon = pick(items, today, stage, sector, state)
        if not new and not soon:
            skipped += 1
            continue
        if sent >= CAP:
            print(f"Daily cap {CAP} reached; remaining subscribers wait for next week.")
            break
        prefs = " · ".join(x for x in [stage if stage != "any" else "any stage", sector if sector != "any" else "any sector", state if state != "any" else "all India"])
        n = len(new) + len(soon)
        subject = f"{n} funding {'opportunity' if n == 1 else 'opportunities'} for your startup this week"
        body = email_html(email, new, soon, prefs)
        if DRY:
            print("DRY", email, subject, [i["id"] for i in new], [i["id"] for i in soon])
            open("/tmp/digest_preview.html", "w").write(body)
            sent += 1
            continue
        code, res = call("POST", "/smtp/email", {"sender": SENDER, "to": [{"email": email}], "subject": subject,
                                                  "htmlContent": body, "replyTo": {"email": SENDER["email"]},
                                                  "tags": ["fundguy-weekly"],
                                                  "headers": {"List-Unsubscribe-Post": "List-Unsubscribe=One-Click", "List-Unsubscribe": "<" + SITE + "unsubscribe.php?" + urllib.parse.urlencode({"e": email, "t": token(email)}) + ">"}})
        if code in (200, 201):
            sent += 1
        else:
            print(f"ERROR sending to subscriber #{sent + skipped + 1}: {code} {res}")
    print(f"Sent {sent}, no matches {skipped}, subscribers {len(subs)}, weekday bucket {day}")


if __name__ == "__main__":
    main()
