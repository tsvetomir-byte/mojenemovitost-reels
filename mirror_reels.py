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
import hashlib
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

# watched profiles -> style family, from the secret WATCH_PROFILES ("user:nabidka,user:makler");
# the names are kept out of this public code and never appear in our posts
WATCH = dict(p.split(":", 1) for p in os.environ.get("WATCH_PROFILES", "").replace(" ", "").split(",") if ":" in p)
ABOUT = "mojenemovitostumore.cz/i2/o-nas?aff=sflvv4sn32"
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
def latest_posts(username):
    tok, ig = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    fields = "business_discovery.username(%s){media.limit(8){id,caption,timestamp,media_type,permalink}}" % username
    r = requests.get("%s/%s" % (R.GRAPH, ig), params={"fields": fields, "access_token": tok}, timeout=60).json()
    if "business_discovery" not in r:
        raise RuntimeError("business_discovery failed: %s" % r)
    return r["business_discovery"].get("media", {}).get("data", [])


def post_type(caption, family="nabidka"):
    c = caption or ""
    if family == "makler":
        if re.search(r"A\)|B\)|označte|oznacte|kdo z vás|kdo z vas", c, re.I):
            return "otazka"
        if re.search(r"moře|more|pláž|plaz|léto|leto|pobřeží|pobrezi|dovolen", c, re.I):
            return "vzpominky"
        return "makler"
    text = re.sub(r"#\S+", "", c).strip()
    if re.search(r"koment|napište|napiste", c, re.I) and len(re.findall(r"(?m)^\s*\d{1,2}\.", c)) >= 3:
        return "anketa"
    if re.search(r"#goodmorning|dobré ráno|good morning", c, re.I):
        return "rano"
    if len(text) < 40:
        return "kratky"
    return "prodejni"


# ---------------------------------------------------------------- our texts (style: CAPS hook, emoji, ✅ list)
DAY = ["Krásné pondělí", "Krásné úterý", "Krásnou středu", "Krásný čtvrtek", "Krásný pátek", "Krásnou sobotu", "Krásnou neděli"]
TEAM = "🇨🇿 Jsme česká společnost a naši specialisté pocházejí ze zemí, které nabízíme. Kdo jsme? " + ABOUT
TAGS_MAKLER = ["#zezivotamaklere", "#realitnihumor", "#reality", "#viral"]


def hook_for(kind, country, f_=None):
    loc = COUNTRY[country][0]
    if kind == "makler":
        return random.choice(["KLASIKA V REALITÁCH", "ZNÁTE TO TAKY?", "TENHLE VÝHLED NIKDY NEOMRZÍ"])
    if kind == "otazka":
        return "KDE BYSTE PILI KÁVU S VÝHLEDEM NA MOŘE?"
    if kind == "vzpominky":
        return "NEZAPOMENUTELNÉ CHVÍLE U MOŘE " + loc.upper()
    if kind == "prodejni" and f_ is not None and R.installments(f_):
        return "BYDLENÍ U MOŘE " + loc.upper() + " NA SPLÁTKY!"
    return {
        "prodejni": random.choice(["SPLŇTE SI SEN O BYDLENÍ U MOŘE ", "VLASTNÍ NEMOVITOST U MOŘE ", "MOŘE NA DOSAH "]) + loc.upper() + "!",
        "anketa": "KDE BYSTE CHTĚLI BYDLET " + loc.upper() + "?",
        "rano": "DOBRÉ RÁNO " + loc.upper() + "!",
        "kratky": "MOŘE " + loc.upper(),
    }[kind]


def clean_town(t):
    t = re.sub(r"^(u|v|ve|na)\s+", "", t.strip(), flags=re.I)
    return " ".join(dict.fromkeys(t.split()))  # "Burgas Burgas" -> "Burgas"


def hashtags(f_, extra=()):
    f_ = dict(f_, town=clean_town(f_["town"]))
    tags = [tag(f_["country"]), tag(f_["town"])] if f_["town"] != f_["country"] else [tag(f_["country"])]
    tags += list(extra) + ["#mojenemovitostumore", "#nemovitostiumore", "#apartmanumore"]
    return " ".join(dict.fromkeys(t for t in tags if len(t) > 2))


def caption(kind, f_, track):
    f_ = dict(f_, town=clean_town(f_["town"]))
    country = f_["country"]
    loc, flag = COUNTRY.get(country, ("u moře", "🌊"))
    where = ", ".join(x for x in dict.fromkeys([f_["town"], country]) if x)
    price = ("💶 " + f_["price"] + " €") if f_["price"] else ""
    if kind == "makler":
        opener = random.choice([
            "Klasika v realitách: klient chce první linii u moře, výhled, bazén… a cenu jako za garáž 😅",
            "Když klient na prohlídce poprvé vyjde na terasu a uvidí moře… ten výraz nikdy neomrzí 😍",
            "Ráno letadlo, odpoledne prohlídky, večer západ slunce nad mořem. Tak vypadá náš běžný pracovní den 😄✈️",
        ])
        lines = [opener, "", "Dnes vám ukazujeme " + loc + " tohle 👇", "📍 " + where]
        if price:
            lines.append(price)
        if R.installments(f_):
            lines.append("💳 Na splátky během výstavby")
        lines += ["", DAY[datetime.now(ZoneInfo("Europe/Prague")).weekday()] + " všem! Hlavně těm, kdo hledají svůj kousek moře. Do toho! 💪",
                  "", TEAM, "", hashtags(f_, TAGS_MAKLER)]
    elif kind == "otazka":
        other = random.choice([c for c in ORDER[:7] if c != country])
        lines = ["Otázka pro vás: kde byste raději pili ranní kávu s výhledem na moře? ☕🌊", "",
                 "A) " + country + " " + flag, "B) " + other + " " + COUNTRY[other][1], "",
                 "Napište do komentáře A nebo B a označte někoho, kdo by jel s vámi! 👇", "",
                 "📍 Ve videu: " + where + ((" · " + price) if price else ""), "", TEAM, "",
                 hashtags(f_, TAGS_MAKLER + ["#anketa"])]
    elif kind == "vzpominky":
        lines = ["Nezapomenutelné chvíle u moře " + loc + "! 🌊☀️ Čisté moře, slunce a pohoda… zážitky, které hřejí u srdce celý rok. 💛", "",
                 "Jestli sníte o ranní kávě s výhledem na moře, můžete mít vlastní místo, kam se budete vracet.", "",
                 "📍 " + where + ((" · " + price) if price else ""), "",
                 "📩 Napište nám – rádi pošleme další nabídky.", TEAM, "",
                 hashtags(f_, ["#dovolenaumore", "#zivotumore", "#reality"])]
    elif kind == "kratky":
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
    if not WATCH and not os.environ.get("TEST_TYPE"):
        log("WATCH_PROFILES secret is empty - nothing to watch")
        return
    if not force and now.hour not in (10, 11, 16, 17):
        log("Not checking time in Prague (%s) - skip" % now.strftime("%H:%M"))
        return
    seen = json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else {"seen": [], "next_country": 0, "posts": {}}
    slot = now.strftime("%Y-%m-%d-") + ("am" if now.hour < 13 else "pm")
    if not force and slot in seen["posts"]:
        log("Already handled slot", slot)
        return

    limit = now - timedelta(hours=MAX_AGE_H)
    new = []
    known = seen.setdefault("profiles", [])
    for user, family in WATCH.items():
        try:
            media = latest_posts(user)
        except Exception as e:
            log("watched profile failed:", family, e)
            continue
        log("watched profile (", family, ") posts:", len(media))
        key = hashlib.sha1(user.encode()).hexdigest()[:10]  # no names in the public repo
        if key not in known:  # first check of this profile: only remember its current posts
            known.append(key)
            seen["seen"] = list(dict.fromkeys([m["id"] for m in media] + seen["seen"]))[:400]
            log("first check of a", family, "profile - remembering current posts")
            continue
        for m in media:
            ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            if m["id"] not in seen["seen"] and ts > limit:
                new.append(dict(m, family=family))
        seen["seen"] = list(dict.fromkeys([m["id"] for m in media] + seen["seen"]))[:400]
    new.sort(key=lambda m: m["timestamp"], reverse=True)
    if not new and os.environ.get("TEST_TYPE"):
        new = [{"id": "test", "caption": "", "timestamp": now.isoformat(), "family": "nabidka"}]
    if not new:
        log("no new post on the watched profile")
        json.dump(seen, open(SEEN_FILE, "w"), indent=1)
        return

    src = new[0]  # newest
    kind = os.environ.get("TEST_TYPE") or post_type(src.get("caption"), src.get("family", "nabidka"))
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
