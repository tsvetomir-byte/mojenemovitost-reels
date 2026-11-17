#!/usr/bin/env python3
"""Moje nemovitost u more - "style mirror" bot (runs in GitHub Actions, 2x a day ~10:40 and ~16:40 Prague).

Every run:
  1. reads the newest public posts of the watched Instagram profile (WATCH_USERNAME) through the official
     Instagram Graph API "business_discovery" (our own IG business account token, no scraping)
  2. if the profile published something new since the last check, it decides the TYPE of that post
     (long sales text / area poll / good-morning / short hashtag reel)
  3. builds OUR OWN Reel of the same type - our property, our photos, our texts - for the next country
     of OUR rotation (all countries we have, not only the watched profile's countries)
  4. publishes it and records it in mirror_seen.json (+ the property in posted.json so it never repeats)

Never copies the watched profile's photos, videos or texts. Only the type and the style are reused.
Secrets: same as reels.py (IG_TOKEN, IG_USER_ID, PIXABAY_KEY/PEXELS_KEY).
"""
import json
import os
import random
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

import reels as R
from reels import log

WATCH_USERNAME = os.environ.get("WATCH_USERNAME", "andreaspropertyandreas")
SEEN_FILE = "mirror_seen.json"
MAX_AGE_H = 36  # only react to posts from the last 36 hours

# all countries we have (rotation order); locative form for the texts + flag
COUNTRY = {
    "Kypr": ("na Kypru", "🇨🇾"),
    "Španělsko": ("ve Španělsku", "🇪🇸"),
    "Řecko": ("v Řecku", "🇬🇷"),
    "Albánie": ("v Albánii", "🇦🇱"),
    "Chorvatsko": ("v Chorvatsku", "🇭🇷"),
    "Bulharsko": ("v Bulharsku", "🇧🇬"),
    "Egypt": ("v Egyptě", "🇪🇬"),
    "Černá Hora": ("v Černé Hoře", "🇲🇪"),
    "Turecko": ("v Turecku", "🇹🇷"),
    "Malta": ("na Maltě", "🇲🇹"),
    "Gruzie": ("v Gruzii", "🇬🇪"),
    "Kapverdy": ("na Kapverdách", "🇨🇻"),
    "Spojené arabské emiráty": ("v Emirátech", "🇦🇪"),
    "Omán": ("v Ománu", "🇴🇲"),
    "Thajsko": ("v Thajsku", "🇹🇭"),
}
ORDER = list(COUNTRY)


def tag(word):
    return "#" + re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", word.lower()).encode("ascii", "ignore").decode())


# ---------------------------------------------------------------- watched profile
def latest_posts():
    tok, ig = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    fields = "business_discovery.username(%s){media.limit(8){id,caption,timestamp,media_type,permalink}}" % WATCH_USERNAME
    r = requests.get("%s/%s" % (R.GRAPH, ig), params={"fields": fields, "access_token": tok}, timeout=60).json()
    if "business_discovery" not in r:
        raise RuntimeError("business_discovery failed: %s" % r)
    return r["business_discovery"].get("media", {}).get("data", [])


def post_type(caption):
    c = caption or ""
    text = re.sub(r"#\S+", "", c).strip()
    if re.search(r"koment|napište|napiste", c, re.I) and len(re.findall(r"(?m)^\s*\d{1,2}\.", c)) >= 3:
        return "anketa"
    if re.search(r"#goodmorning|dobré ráno|good morning", c, re.I):
        return "rano"
    if len(text) < 40:
        return "kratky"
    return "prodejni"


# ---------------------------------------------------------------- our texts (style: CAPS hook, emoji, ✅ list)
def hook_for(kind, country, f_=None):
    loc = COUNTRY[country][0]
    if kind == "prodejni" and f_ is not None and R.installments(f_):
        return "BYDLENÍ U MOŘE " + loc.upper() + " NA SPLÁTKY!"
    return {
        "prodejni": random.choice(["SPLŇTE SI SEN O BYDLENÍ U MOŘE ", "VLASTNÍ NEMOVITOST U MOŘE ", "MOŘE NA DOSAH "]) + loc.upper() + "!",
        "anketa": "KDE BYSTE CHTĚLI BYDLET " + loc.upper() + "?",
        "rano": "DOBRÉ RÁNO " + loc.upper() + "!",
        "kratky": "MOŘE " + loc.upper(),
    }[kind]


def hashtags(f_, extra=()):
    f_ = dict(f_, town=" ".join(dict.fromkeys(f_["town"].split())))  # "Burgas Burgas" -> "Burgas"
    tags = [tag(f_["country"]), tag(f_["town"])] if f_["town"] != f_["country"] else [tag(f_["country"])]
    tags += list(extra) + ["#mojenemovitostumore", "#nemovitostiumore", "#apartmanumore"]
    return " ".join(dict.fromkeys(t for t in tags if len(t) > 2))


def caption(kind, f_, track):
    country = f_["country"]
    loc, flag = COUNTRY.get(country, ("u moře", "🌊"))
    where = ", ".join(x for x in dict.fromkeys([f_["town"], country]) if x)
    if kind == "kratky":
        lines = [hashtags(f_, ["#reels", "#more"])]
    elif kind == "rano":
        lines = ["☀️ Dobré ráno " + loc + "! " + flag, "", hashtags(f_, ["#goodmorning", "#dobrerano"])]
    elif kind == "anketa":
        lines = ["Kde byste si nejraději koupili apartmán " + loc + "? Napište do komentáře 😎😎😎", "",
                 "📍 Dnes vám ukazujeme: " + where, ""]
        if f_["price"]:
            lines.append("💶 Cena: " + f_["price"] + " €")
        if f_["sea"]:
            lines.append("🌊 K moři: " + f_["sea"])
        if R.installments(f_):
            lines.append("💳 Na splátky během výstavby")
        lines += ["", "📩 Napište nám, pošleme vám nabídky z dalších míst.",
                  "Najdete na webu " + R.BRAND_NAME + " – ID " + f_["id"], "", hashtags(f_, ["#anketa", "#reality"])]
    else:  # prodejni
        splatky = R.installments(f_)
        head = random.choice(["🌊☀️ SPLŇTE SI SEN O VLASTNÍM BYDLENÍ U MOŘE ", "☀️🌴 VLASTNÍ NEMOVITOST U MOŘE ",
                              "🌊🏖️ MOŘE NA DOSAH "]) + loc.upper() + "! " + flag
        intro = random.choice([
            "Představte si vlastní nemovitost " + loc + ", kde můžete trávit dovolenou, užívat si slunce nebo ji pronajímat.",
            "Ráno káva s výhledem na moře, odpoledne pláž a večer západ slunce. Takový může být váš život " + loc + ".",
            "Hledáte místo, kam se budete rádi vracet? Vlastní bydlení " + loc + " může být právě to pravé.",
        ])
        caps = "NA SPLÁTKY BĚHEM VÝSTAVBY!" if splatky else random.choice(["VÁŠ KOUSEK MOŘE!", "SEN, KTERÝ SE DÁ SPLNIT!"])
        lines = [head, "", "🏠 " + f_["title"], "", intro + " " + caps + " ❤️", "", "💎 CO VÁM NABÍZÍME?"]
        if splatky:
            lines.append("✅ Splátky během výstavby")
        if f_["price"]:
            lines.append("✅ Cena: " + f_["price"] + " €")
        if f_["sea"]:
            lines.append("✅ K moři jen " + f_["sea"])
        if f_["area"]:
            lines.append("✅ Plocha " + f_["area"] + " m²")
        lines += ["✅ Česká realitní kancelář", "✅ Kompletní servis až k podpisu", "",
                  "📩 Napište nám – rádi pošleme podrobnosti.",
                  "Najdete na webu " + R.BRAND_NAME + " – ID " + f_["id"], "",
                  hashtags(f_, ["#luxusnibydleni", "#investicedonemovitosti", "#reality"])]
    if track:
        lines += ["", '🎵 Hudba: "%s" – Kevin MacLeod (incompetech.com), CC BY 4.0' % track]
    return "\n".join(lines)


# ---------------------------------------------------------------- property for the country of the turn
def pick_property(start_idx, posted):
    ids = R.collect_ids()
    fresh = [i for i in ids if i not in posted]
    random.shuffle(fresh)
    cache = {}
    for step in range(len(ORDER)):
        country = ORDER[(start_idx + step) % len(ORDER)]
        for pid in fresh[:60]:
            if pid not in cache:
                try:
                    cache[pid] = R.property_facts(pid, ids[pid])
                except Exception as e:
                    log("detail failed", pid, e)
                    cache[pid] = None
            f_ = cache[pid]
            if not f_ or f_["country"] != country:
                continue
            if re.search(r"pozemek|pronájem", f_["title"], re.I) or len(f_["images"]) < R.MIN_PHOTOS:
                continue
            return (start_idx + step) % len(ORDER), f_
        log("no fresh property for", country, "- next country")
    return None, None


# ---------------------------------------------------------------- main
def main():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    force = os.environ.get("FORCE") == "1"
    dry = os.environ.get("DRY_RUN") == "1"
    if not os.environ.get("IG_TOKEN"):
        log("IG_TOKEN is not set - nothing to do")
        return
    if not force and now.hour not in (10, 11, 16, 17):
        log("Not checking time in Prague (%s) - skip" % now.strftime("%H:%M"))
        return
    seen = json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else {"seen": [], "next_country": 0, "posts": {}}
    slot = now.strftime("%Y-%m-%d-") + ("am" if now.hour < 13 else "pm")
    if not force and slot in seen["posts"]:
        log("Already handled slot", slot)
        return

    media = latest_posts()
    log("watched profile posts:", len(media))
    limit = now - timedelta(hours=MAX_AGE_H)
    new = []
    for m in media:
        ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if m["id"] not in seen["seen"] and ts > limit:
            new.append(m)
    first_run = not seen["seen"]
    seen["seen"] = list(dict.fromkeys([m["id"] for m in media] + seen["seen"]))[:200]
    if first_run and not force:
        log("first run - remembering current posts, nothing published")
        json.dump(seen, open(SEEN_FILE, "w"), indent=1)
        return
    if not new and os.environ.get("TEST_TYPE"):
        new = [{"id": "test", "caption": "", "timestamp": now.isoformat()}]
    if not new:
        log("no new post on the watched profile")
        if not dry:
            json.dump(seen, open(SEEN_FILE, "w"), indent=1)
        return

    src = new[0]  # newest
    kind = os.environ.get("TEST_TYPE") or post_type(src.get("caption"))
    log("new post", src["id"], "type:", kind)

    posted = json.load(open("posted.json")) if os.path.exists("posted.json") else {}
    idx, f_ = pick_property(seen.get("next_country", 0), posted)
    if not f_:
        sys.exit("No suitable property found")
    country = f_["country"]
    log("our property", f_["id"], f_["title"], country)

    for attempt in range(5):
        R.HOOKS_MORNING = R.HOOKS_EVENING = [hook_for(kind, country, f_)]
        try:
            video, track, hook = R.build_video(f_, now.hour)
            break
        except Exception as e:
            log("video failed for", f_["id"], e, "- trying another property")
            posted[f_["id"]] = {"skipped": True, "at": now.isoformat()}
            idx, f_ = pick_property(idx, posted)
            if not f_:
                sys.exit("No suitable property found")
            country = f_["country"]
    else:
        sys.exit("video failed 5 times")
    cap = caption(kind, f_, track)
    log(cap)
    if dry:
        log("DRY RUN - not publishing")
        return
    mid = R.publish_reel(video, cap)
    posted[f_["id"]] = {"media": mid, "at": now.isoformat(), "slot": "mirror-" + slot, "type": "mirror-" + kind}
    json.dump(posted, open("posted.json", "w"), indent=1)
    seen["next_country"] = (idx + 1) % len(ORDER)
    seen["posts"][slot] = {"source": src["id"], "type": kind, "media": mid, "property": f_["id"], "country": country}
    json.dump(seen, open(SEEN_FILE, "w"), indent=1)
    log("Published mirror reel", mid, "for", country, f_["id"])


if __name__ == "__main__":
    main()
