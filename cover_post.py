#!/usr/bin/env python3
"""Moje nemovitost u more - weekly magazine cover post "U MOŘE" (runs in GitHub Actions, Sunday about 10:00 Prague).

Once a week the bot publishes one feed photo (4:5) styled like a magazine cover (like FOLIO):
  - full-bleed photo of a luxury sea-view property from mojenemovitostumore.cz (never repeated on a cover)
  - masthead "U MOŘE", issue number and date
  - 4 headlines: the cover property, live weather/sea temperature (Cyprus / Spain alternate),
    one Cyprus topic and one Spain topic from info_reels.TOPICS (rotating, so issues don't repeat)
Records issues in cover_posted.json.
"""
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import reels as R
import info_reels as I

CW, CH = 1080, 1350  # Instagram portrait feed photo 4:5
MAST = "U MOŘE"
F_MAST = "fonts/Oswald-Bold.ttf"
F_HEAD = "fonts/Oswald-Bold.ttf"
F_SUB = "fonts/Poppins-Medium.ttf"
WHITE = (255, 255, 255)
GOLD = (236, 214, 160)
LOG = "cover_posted.json"
# cover headline for the property (rotates by issue)
PROP_HEADS = ["První řada u moře", "Klenot týdne u moře", "Probuďte se s výhledem", "Luxus na pobřeží",
              "Domov, kde začíná dovolená", "Výhled, který neomrzí"]
SKIP_TOPICS = {"K8", "S7"}  # weather topics - the weather headline is already live on the cover
TAGS = ["#mojenemovitostumore", "#magazin", "#zivotumore", "#bydleniumore", "#nemovitostiumore", "#luxusnibydleni",
        "#vyhlednamore", "#investicedonemovitosti", "#kypr", "#spanelsko", "#reality", "#dovolenaumore"]


def font(path, size):
    return ImageFont.truetype(path, size)


def spaced(d, xy, text, f, spacing, fill=WHITE, anchor_center=False, shadow=True):
    """text with letter spacing (magazine look)."""
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x = x - total / 2
    for ch, w in zip(text, widths):
        if shadow:
            d.text((x + 3, y + 3), ch, font=f, fill=(0, 0, 0, 110))
        d.text((x, y), ch, font=f, fill=fill)
        x += w + spacing
    return total


def fit_lines(d, text, path, size, max_w, max_lines):
    while size > 24:
        f = font(path, size)
        lines = R.wrap(d, text, f, max_w)
        if len(lines) <= max_lines and all(d.textlength(l, font=f) <= max_w for l in lines):
            return f, lines
        size -= 2
    f = font(path, size)
    return f, R.wrap(d, text, f, max_w)


def load_photo(url):
    """try a bigger version of the CDN photo first."""
    for u in (url.replace("_w1440", "_w2560"), url.replace("_w1440", "_w1920"), url):
        try:
            r = requests.get(u, headers=R.UA, timeout=60)
            if r.status_code == 200 and len(r.content) > 20000:
                return Image.open(BytesIO(r.content)).convert("RGB")
        except Exception as e:
            R.log("photo failed", u, e)
    return None


def cover_crop(im):
    r = max(CW / im.width, CH / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x = (im.width - CW) // 2
    y = max(0, int((im.height - CH) * 0.55))
    im = im.crop((x, y, x + CW, y + CH))
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(1.08)
    return im


def shade(img):
    """soft darkening: top (masthead), left (headlines), bottom (issue line)."""
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    px = ov.load()
    for y in range(CH):
        top = max(0.0, 1 - y / 420) * 150
        bot = max(0.0, (y - CH + 260) / 260) * 170
        for x in range(0, CW, 4):
            left = max(0.0, 1 - x / 760) * 120
            a = int(min(220, top + bot + left))
            for k in range(4):
                if x + k < CW:
                    px[x + k, y] = (0, 0, 0, a)
    return Image.alpha_composite(img.convert("RGBA"), ov)


def render(photo, issue, day, heads, out):
    img = shade(cover_crop(photo))
    d = ImageDraw.Draw(img)
    # top strapline
    spaced(d, (CW / 2, 34), "NEMOVITOSTI · ŽIVOT · INVESTICE · CESTOVÁNÍ", font(F_SUB, 20), 4, anchor_center=True)
    # masthead
    mf = font(F_MAST, 210)
    spaced(d, (CW / 2, 30), MAST, mf, 26, anchor_center=True)
    spaced(d, (CW / 2, 300), "MOJENEMOVITOSTUMORE.CZ", font(F_SUB, 22), 9, fill=GOLD, anchor_center=True)
    # headlines (left column)
    y = 400
    max_w = 540
    for i, (big, small) in enumerate(heads):
        f, lines = fit_lines(d, big.upper(), F_HEAD, 56 if i == 0 else 46, max_w, 2)
        for ln in lines:
            R.shadow_text(d, (60, y), ln, f, fill=GOLD if i == 0 else WHITE)
            y += int(f.size * 1.18)
        if small:
            sf = R.fit_text(d, small, F_SUB, 24, max_w + 60)
            R.shadow_text(d, (62, y + 8), small, sf)
            y += 42
        y += 30
    # thin rule + issue line at the bottom
    d.line([(60, CH - 96), (CW - 60, CH - 96)], fill=(255, 255, 255, 170), width=2)
    spaced(d, (60, CH - 74), "ČÍSLO %d" % issue, font(F_SUB, 26), 5)
    dt = day.strftime("%d/%m/%Y")
    dfnt = font(F_SUB, 26)
    w = spaced(d, (0, -500), dt, dfnt, 5, shadow=False)  # measure only (drawn off canvas)
    spaced(d, (CW - 60 - w, CH - 74), dt, dfnt, 5)
    img.convert("RGB").save(out, quality=95)
    return out


def pick_property(covers, reels_posted):
    used = {v.get("property") for v in covers.values()}
    ids = R.collect_ids()
    cand = [i for i in ids if i not in used]
    fresh = [i for i in cand if i not in reels_posted] or cand
    random.shuffle(fresh)
    for pid in fresh[:25]:
        f_ = R.facts(R.get(ids[pid]).text, pid)
        if re.search(r"pozemek|pronájem", f_["title"], re.I) or not f_["images"]:
            continue
        photo = load_photo(f_["images"][0])
        if photo and photo.width >= 1000:
            return f_, photo
    sys.exit("No property for the cover")


def topics_for(issue):
    ky = [t for t in I.TOPICS if t[0].startswith("K") and t[0] not in SKIP_TOPICS]
    sp = [t for t in I.TOPICS if t[0].startswith("S") and t[0] not in SKIP_TOPICS]
    return ky[(issue - 1) % len(ky)], sp[(issue + 5) % len(sp)]


def weather_head(issue):
    c = I.CY if issue % 2 else I.ES
    air, sea = I.weather(c)
    if air is None:
        return ("Slunce i v zimě", "Předpověď počasí najdete na webu " + c["web"]), c
    small = "%s dnes %d °C" % (c["town"], air) + (" · moře %d °C" % sea if sea is not None else "")
    big = ("Zima? Na Kypru %d °C" if c is I.CY else "Zima? Ve Španělsku %d °C") % air
    return (big, small), c


def headlines(f_, issue):
    town = f_["town"]
    if town == f_["country"] and re.search(r"\s[–-]\s", f_["title"]):
        t = re.split(r"\s[–-]\s", f_["title"])[-1].strip()
        if 2 < len(t) <= 22:
            town = t
    where = town if town == f_["country"] else "%s, %s" % (town, f_["country"])
    bits = [where]
    if f_["sea"]:
        bits.append("%s od moře" % f_["sea"])
    if f_["price"]:
        bits.append("%s €" % f_["price"])
    prop = (PROP_HEADS[(issue - 1) % len(PROP_HEADS)], " · ".join(b for b in bits if b))
    wx, _ = weather_head(issue)
    k, s = topics_for(issue)
    return [prop, wx, (k[2], k[3][0][0] + " · " + k[3][0][1]), (s[2], s[3][0][0] + " · " + s[3][0][1])], (k, s)


def caption(f_, issue, day, heads, topics):
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    lines = ["📰 U MOŘE · číslo %d · %s" % (issue, day.strftime("%d. %m. %Y")),
             "Týdeník o životě, cestování a nemovitostech u moře.", "", "V tomto čísle:"]
    for n, (b, s) in zip(nums, heads):
        lines.append("%s %s%s" % (n, b, (" – " + s) if s else ""))
    lines += ["", "🏡 Na titulní straně: %s (ID %s). Najdete na webu MojeNemovitostUMore.cz" % (f_["title"] or "nemovitost u moře", f_["id"])]
    k, s = topics
    lines += ["👉 Kypr: " + k[4], "👉 Španělsko: " + s[4],
              "📩 Napište nám do zpráv MAGAZÍN – pošleme detaily česky.",
              "🇨🇿 20 let jen nemovitosti u moře · 1 500+ nových majitelů · kompletní servis",
              "", "ℹ️ " + I.LEGAL, "", " ".join(TAGS)]
    return "\n".join(lines)


# ---------------------------------------------------------------- instagram (photo post)
def host_image(path):
    gh, repo = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    h = {"Authorization": "Bearer " + gh, "Accept": "application/vnd.github+json"}
    api = "https://api.github.com/repos/" + repo
    rel = requests.get(api + "/releases/tags/covers", headers=h, timeout=30)
    if rel.status_code == 404:
        rel = requests.post(api + "/releases", headers=h, timeout=30,
                            json={"tag_name": "covers", "name": "Magazine covers", "body": "Weekly U MOŘE covers"})
    rel.raise_for_status()
    rel = rel.json()
    name = "cover-%s.jpg" % datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d-%H%M%S")
    with open(path, "rb") as fh:
        up = requests.post("https://uploads.github.com/repos/%s/releases/%d/assets" % (repo, rel["id"]), params={"name": name},
                           headers=dict(h, **{"Content-Type": "image/jpeg"}), data=fh, timeout=120)
    if up.status_code not in (200, 201):
        raise RuntimeError("image hosting failed: %s %s" % (up.status_code, up.text[:200]))
    return up.json()["browser_download_url"]


def publish_photo(path, cap):
    tok, ig = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    url = host_image(path)
    R.log("image url:", url)
    last = None
    for attempt in range(1, 4):
        try:
            r = requests.post("%s/%s/media" % (R.GRAPH, ig), data={"image_url": url, "caption": cap, "access_token": tok},
                              timeout=60).json()
            if "id" not in r:
                raise RuntimeError("container error: %s" % r)
            for _ in range(12):
                s = requests.get("%s/%s" % (R.GRAPH, r["id"]), params={"fields": "status_code", "access_token": tok}, timeout=30).json()
                if s.get("status_code") in ("FINISHED", None):
                    break
                time.sleep(5)
            p = requests.post("%s/%s/media_publish" % (R.GRAPH, ig), data={"creation_id": r["id"], "access_token": tok},
                              timeout=60).json()
            if "id" in p:
                return p["id"]
            raise RuntimeError("publish error: %s" % p)
        except Exception as e:
            last = e
            R.log("attempt %d failed: %s" % (attempt, e))
            time.sleep(20 * attempt)
    raise RuntimeError("cover publish failed: %s" % last)


def main():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    force = os.environ.get("FORCE") == "1"
    dry = os.environ.get("DRY_RUN") == "1"
    if not os.environ.get("IG_TOKEN") and not dry:
        R.log("IG_TOKEN is not set yet - nothing to publish")
        return
    if not force and (now.weekday() != 6 or now.hour != 10):
        R.log("Not cover time (Sunday 10:00 Prague), now %s - skip" % now.strftime("%a %H:%M"))
        return
    covers = json.load(open(LOG)) if os.path.exists(LOG) else {}
    day = now.strftime("%Y-%m-%d")
    if not force and day in covers:
        R.log("Cover already posted today")
        return
    reels_posted = json.load(open("posted.json")) if os.path.exists("posted.json") else {}
    issue = len(covers) + 1
    f_, photo = pick_property(covers, reels_posted)
    heads, topics = headlines(f_, issue)
    render(photo, issue, now, heads, "cover.jpg")
    cap = caption(f_, issue, now, heads, topics)
    R.log(cap)
    if dry:
        R.log("DRY RUN - not publishing (see the cover.jpg artifact)")
        return
    mid = publish_photo("cover.jpg", cap)
    covers[day] = {"issue": issue, "property": f_["id"], "media": mid, "topics": [topics[0][0], topics[1][0]], "at": now.isoformat()}
    json.dump(covers, open(LOG, "w"), indent=1, ensure_ascii=False)
    R.log("Published cover", issue, mid)


if __name__ == "__main__":
    main()
