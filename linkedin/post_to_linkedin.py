"""Publish the next due post from linkedin/queue.json to Abhishek's LinkedIn profile (runs inside GitHub Actions).

queue.json is a list of posts; each run publishes ONE: the earliest item whose post_after time
has passed and whose id is not yet in posted.json. Item format:
{
  "post_after": "2026-11-18T03:30:00Z",   # UTC; don't publish before this time
  "id": "2026-11-18-some-grant-id",      # unique; a post with an id already in posted.json is skipped
  "text": "Post text with hashtags and the grant page link",
  "screenshot_url": "official apply page — its screenshot is used as the image (preferred)",
  "image_sources": ["official opportunity page or image URL", "fallback free-licence photo page"],
  "image_title": "Short alt/title for the image (optional)"
Each source may be a direct image URL or a web page; for a page, its og:image share image is used.
The first source that yields a usable image (min side 200px) wins; if none does, it posts text only.
}
Needs the LINKEDIN_TOKEN secret (scopes: openid profile w_member_social).
"""
import datetime as dt
import io
import json
import os
import re
import sys

import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(HERE, "queue.json")
LOG_FILE = os.path.join(HERE, "posted.json")
TOKEN = os.environ.get("LINKEDIN_TOKEN", "").strip()
API = "https://api.linkedin.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def fail(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def versions():
    """LinkedIn-Version header values (YYYYMM), newest first, last ~12 months."""
    d = dt.date.today().replace(day=1)
    out = []
    for _ in range(14):
        d = (d - dt.timedelta(days=1)).replace(day=1)
        out.append(d.strftime("%Y%m"))
    return out


def rest(method, path, version, **kw):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "LinkedIn-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    return requests.request(method, API + path, headers=headers, timeout=60, **kw)


def pick_version():
    """Find a LinkedIn API version the server currently accepts."""
    for v in versions():
        r = rest("POST", "/rest/images?action=initializeUpload", v,
                 json={"initializeUploadRequest": {"owner": OWNER}})
        if r.status_code == 401:
            fail("LinkedIn token expired or invalid (401). Generate a new token and "
                 "update the LINKEDIN_TOKEN secret in GitHub.")
        if r.status_code in (200, 201):
            return v, r.json()["value"]
        print(f"version {v}: {r.status_code} {r.text[:200]}")
    fail("No accepted LinkedIn-Version found.")


RESERVED = r"\|{}@[]()<>#*_~"


def to_little_text(text):
    """Escape LinkedIn 'little text' reserved chars, keep URLs intact, make #tags clickable."""
    parts = re.split(r"(https?://\S+)", text)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:  # URL
            out.append(p)
            continue
        esc = "".join("\\" + c if c in RESERVED else c for c in p)
        esc = re.sub(r"\\#(\w+)", r"{hashtag|\\#|\1}", esc)
        out.append(esc)
    return "".join(out)


META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image)["\'][^>]*>', re.I)


def image_from(url):
    """Return a PIL image from a direct image URL, or from a web page's og:image/twitter:image."""
    from urllib.parse import urljoin
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    if "image" not in r.headers.get("content-type", ""):
        m = None
        for tag in META_RE.findall(r.text):
            m = re.search(r'content=["\']([^"\']+)', tag)
            if m:
                break
        if not m:
            raise ValueError("page has no og:image")
        img_url = urljoin(url, m.group(1).replace("&amp;", "&"))
        print("Found share image:", img_url)
        r = requests.get(img_url, headers={"User-Agent": UA, "Referer": url}, timeout=60)
        r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    img.load()
    if min(img.size) < 200:
        raise ValueError(f"image too small {img.size}")
    return img


def screenshot(url):
    """Screenshot the top of the official apply page (1200x675, 2x for sharpness)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2,
                        user_agent=UA, locale="en-IN")
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        # close common cookie / popup banners if present
        for label in ["Accept", "Accept all", "Accept All", "I agree", "Got it", "OK", "Close"]:
            try:
                btn = pg.get_by_role("button", name=label, exact=True)
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=2000)
                    pg.wait_for_timeout(800)
            except Exception:  # noqa: BLE001
                pass
        pg.wait_for_timeout(2500)
        # hide small floating widgets (WhatsApp/chat bubbles, notification bells)
        pg.evaluate("""() => document.querySelectorAll('body *').forEach(e => {
            const s = getComputedStyle(e);
            if ((s.position === 'fixed' || s.position === 'sticky') && e.offsetWidth < 450
                && e.offsetHeight < 300) e.style.visibility = 'hidden';
        })""")
        data = pg.screenshot(type="png")
        b.close()
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def fetch_image(urls, shot_url=None):
    img = None
    if shot_url:
        try:
            img = screenshot(shot_url)
            print("Using screenshot of", shot_url)
            os.makedirs(os.path.join(HERE, "images"), exist_ok=True)
            img.save(os.path.join(HERE, "images", post["id"] + ".png"))
        except Exception as e:  # noqa: BLE001
            print(f"Screenshot failed for {shot_url}: {e}")
            img = None
    for u in ([] if img is not None else urls):
        try:
            img = image_from(u)
            print("Using image from", u)
            break
        except Exception as e:  # noqa: BLE001
            print(f"No usable image from {u}: {e}")
    if img is None:
        print("No image found; posting text only.")
        return None
    img = img.convert("RGB")
    if max(img.size) > 4000:
        img.thumbnail((4000, 4000))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------- main
if not TOKEN:
    fail("LINKEDIN_TOKEN secret is missing.")
log = json.load(open(LOG_FILE, encoding="utf-8")) if os.path.exists(LOG_FILE) else []
done = {e.get("id") for e in log}
queue = json.load(open(QUEUE_FILE, encoding="utf-8")) if os.path.exists(QUEUE_FILE) else []
now = dt.datetime.now(dt.timezone.utc)


def due(item):
    t = item.get("post_after")
    if not t:
        return True
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")) <= now


pending = [q for q in queue if q.get("id") not in done and due(q)]
if not pending:
    print("Nothing due in linkedin/queue.json; nothing to do.")
    sys.exit(0)
post = sorted(pending, key=lambda q: q.get("post_after") or "")[0]
print("Publishing", post["id"])
PREVIEW = bool(post.get("preview")) or os.environ.get("PREVIEW_ONLY") == "1"

who = requests.get(API + "/v2/userinfo", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
if who.status_code == 401:
    fail("LinkedIn token expired or invalid (401). Generate a new token and update the "
         "LINKEDIN_TOKEN secret in GitHub.")
who.raise_for_status()
OWNER = "urn:li:person:" + who.json()["sub"]
print("Token OK for", who.json().get("name", "member"))

img_bytes = fetch_image(post.get("image_sources", []), post.get("screenshot_url"))
if PREVIEW:
    print("Preview only: image saved in linkedin/images, nothing posted.")
    sys.exit(0)

version, upload = pick_version()
body = {
    "author": OWNER,
    "commentary": to_little_text(post["text"]),
    "visibility": "PUBLIC",
    "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                     "thirdPartyDistributionChannels": []},
    "lifecycleState": "PUBLISHED",
    "isReshareDisabledByAuthor": False,
}
if img_bytes:
    put = requests.put(upload["uploadUrl"], data=img_bytes,
                       headers={"Authorization": f"Bearer {TOKEN}"}, timeout=120)
    if put.status_code in (200, 201):
        body["content"] = {"media": {"id": upload["image"],
                                     "title": post.get("image_title", "")[:200]}}
    else:
        print(f"Image upload failed {put.status_code}; posting without image.")

r = rest("POST", "/rest/posts", version, json=body)
if r.status_code not in (200, 201):
    fail(f"Post failed {r.status_code}: {r.text[:500]}")
urn = r.headers.get("x-restli-id", "")
url = f"https://www.linkedin.com/feed/update/{urn}/"
print("Posted:", url)

log.append({"id": post["id"], "urn": urn, "url": url, "image": bool(body.get("content")),
            "posted_at": now.isoformat()})
json.dump(log, open(LOG_FILE, "w", encoding="utf-8"), indent=1)
