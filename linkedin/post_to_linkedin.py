"""Publish linkedin/post.json to Abhishek's LinkedIn profile (runs inside GitHub Actions).

post.json format:
{
  "id": "2026-11-18-some-grant-id",      # unique; a post with an id already in posted.json is skipped
  "text": "Post text with hashtags and the grant page link",
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
POST_FILE = os.path.join(HERE, "post.json")
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


def fetch_image(urls):
    img = None
    for u in urls:
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
post = json.load(open(POST_FILE, encoding="utf-8"))
log = json.load(open(LOG_FILE, encoding="utf-8")) if os.path.exists(LOG_FILE) else []
if any(e.get("id") == post["id"] for e in log):
    print(f"Post {post['id']} already published; nothing to do.")
    sys.exit(0)

who = requests.get(API + "/v2/userinfo", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
if who.status_code == 401:
    fail("LinkedIn token expired or invalid (401). Generate a new token and update the "
         "LINKEDIN_TOKEN secret in GitHub.")
who.raise_for_status()
OWNER = "urn:li:person:" + who.json()["sub"]

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

img_bytes = fetch_image(post.get("image_sources", []))
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
            "posted_at": dt.datetime.utcnow().isoformat() + "Z"})
json.dump(log, open(LOG_FILE, "w", encoding="utf-8"), indent=1)
