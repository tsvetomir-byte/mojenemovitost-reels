#!/usr/bin/env python3
"""Moje nemovitost u more - HeyGen presenter Reel (runs in GitHub Actions, Mon/Wed/Fri about 12:00 Europe/Prague).

A young woman presenter (a different HeyGen avatar for every country) says a short Czech script.
The bot asks the HeyGen API for the talking video, adds big gold titles, subtitles and quiet Suno music,
and publishes it as a Reel with the same publisher as reels.py. Records posts in heygen_posted.json.

Needs the repository secret HEYGEN_API_KEY (HeyGen > Developers > API Keys). Without it the bot does nothing.
The HeyGen API is paid from a separate pay-as-you-go balance (not from the Creator plan).

MODE=list  -> only prints the avatars and voices of the HeyGen account (free, no video is made)
DRY_RUN=1  -> makes the video (this costs HeyGen API balance) but does not publish it
TOPIC=K1   -> use this topic instead of the next one in the rotation
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw

import reels as R
from reels import W, H, WHITE, font, wrap, ff, log

API = "https://api.heygen.com"
DAYS = (0, 2, 4)  # Monday, Wednesday, Friday
HOUR = 12
GOLD = (244, 200, 96)
GOLD_DARK = (176, 128, 40)
POSTED = "heygen_posted.json"
LEGAL = "Nejedná se o nabídku k uzavření smlouvy. Údaje jsou orientační, ověřte je na webu."
COMMON_TAGS = ["#investicedonemovitosti", "#zivotumore", "#mojenemovitostumore", "#bydleniumore", "#novostavby", "#reels"]

# every country has its own presenter: name of the avatar in HeyGen (My Avatars) and name of its voice
PRESENTERS = {
    "CY": {"avatar": "Kypr - Eliska", "voice": "Iona", "name": "Kypr", "dm": "KYPR",
           "tags": ["#kypr", "#nemovitostinakypru", "#bytnakypru", "#cyprus", "#pafos", "#larnaka", "#limassol"]},
    "ES": {"avatar": "Spanelsko - Sofie", "voice": "Kyliee", "name": "Španělsko", "dm": "ŠPANĚLSKO",
           "tags": ["#spanelsko", "#nemovitostivespanelsku", "#bytvespanelsku", "#costablanca", "#spain"]},
    "AL": {"avatar": "Albanie - Klara", "voice": "Ellie Faye", "name": "Albánie", "dm": "ALBÁNIE",
           "tags": ["#albanie", "#nemovitostivalbanii", "#bytvalbanii", "#albania", "#buyalbania"]},
}

# key, country, script (what the presenter says), gold titles (small line, big line), caption hook, caption points, web line
TOPICS = [
    ("K1", "CY",
     "Kdy je nemovitost na Kypru nejlevnější? Na úplném začátku. Když developer spustí prodej a na pozemku ještě nic "
     "nestojí, nabízí nejnižší, takzvanou startovací cenu. S postupem stavby ceny obvykle rostou. A nejlepší byty, "
     "s výhledem na moře a nejlepší dispozicí, mizí jako první. Navíc neplatíte všechno najednou. Platíte postupně, "
     "podle toho, jak stavba roste, a splátky končí dokončením projektu. My spolupracujeme přímo s developery "
     "a o nových projektech víme hned na startu. Chcete vědět, které projekty se na Kypru právě spouštějí? "
     "Napište nám, nebo se podívejte na realitykypr.cz.",
     [("KYPR", "KDY JE NEJLEVNĚJŠÍ?"), ("CENA", "NA STARTU"), ("NEJLEPŠÍ BYTY", "MIZÍ PRVNÍ"),
      ("PLATBA", "POSTUPNĚ"), ("VÍCE NA", "REALITYKYPR.CZ")],
     "Kdy je nemovitost na Kypru nejlevnější? Na úplném začátku.",
     ["Startovací cena při spuštění prodeje", "Největší výběr bytů s výhledem na moře",
      "Platba postupně, splátky končí dokončením projektu"],
     "Projekty, které se právě spouštějí, najdete na webu realitykypr.cz"),
    ("S1", "ES",
     "Proč lidé kupují novostavbu ve Španělsku ještě dřív, než je dokončená? Protože na začátku prodeje mají největší "
     "výběr. Mohou si vybrat patro, výhled i dispozici, dokud je z čeho vybírat. Cena se neplatí celá najednou, "
     "ale postupně podle toho, jak stavba pokračuje. A do předání klíčů je dost času si všechno v klidu připravit. "
     "My vám ukážeme projekty u moře a provedeme vás celou koupí česky. Chcete vidět aktuální novostavby "
     "ve Španělsku? Napište nám do zpráv slovo Španělsko.",
     [("ŠPANĚLSKO", "PROČ KOUPIT VČAS?"), ("NEJVĚTŠÍ", "VÝBĚR BYTŮ"), ("PLATBA", "POSTUPNĚ"),
      ("CELÁ KOUPĚ", "ČESKY"), ("NAPIŠTE NÁM", "ŠPANĚLSKO")],
     "Proč lidé kupují novostavbu ve Španělsku dřív, než je dokončená?",
     ["Největší výběr pater, výhledů a dispozic", "Cena se platí postupně podle postupu stavby",
      "Celou koupí vás provedeme česky"],
     "Aktuální novostavby u moře najdete na webu spanelskydomov.web.app"),
    ("A1", "AL",
     "Proč se teď tolik mluví o Albánii? Moře máte pár kroků od domu. Počasí je podobné jako v Itálii. "
     "Čeká vás skvělé jídlo, citrusy a pohostinní lidé. A Albánie je kandidátskou zemí Evropské unie, "
     "takže se mluví o jejím možném budoucím vstupu. Nemovitosti ve výstavbě se tu prodávají na splátky, "
     "takže neplatíte všechno najednou. Chcete vidět byty u moře v Albánii? Napište nám do zpráv slovo Albánie, "
     "nabídku najdete na webu BuyAlbania.eu.",
     [("ALBÁNIE", "PROČ PRÁVĚ TEĎ?"), ("MOŘE", "PÁR KROKŮ"), ("POČASÍ", "JAKO V ITÁLII"),
      ("VE VÝSTAVBĚ", "NA SPLÁTKY"), ("NAJDETE NA", "BUYALBANIA.EU")],
     "Proč se teď tolik mluví o Albánii?",
     ["Moře pár kroků od domu, počasí jako v Itálii", "Skvělé jídlo, citrusy a pohostinní lidé",
      "Nemovitosti ve výstavbě na splátky"],
     "Nabídku bytů u moře najdete na webu BuyAlbania.eu"),
    ("K2", "CY",
     "Jak se vlastně platí novostavba na Kypru? Nejdřív si vyberete byt a zarezervujete ho. Potom podepíšete "
     "kupní smlouvu. A cenu neplatíte najednou, ale po částech, jak stavba roste. Poslední splátka přichází "
     "při dokončení projektu. Všechno, co je ve výstavbě, se u nás prodává na splátky. Celým postupem vás "
     "provedeme česky, od výběru bytu až po předání klíčů. Chcete vědět, jak by splátky vypadaly u konkrétního bytu? "
     "Napište nám do zpráv slovo Kypr.",
     [("KYPR", "JAK SE PLATÍ?"), ("1. KROK", "REZERVACE"), ("2. KROK", "KUPNÍ SMLOUVA"),
      ("PLATBA", "PO ČÁSTECH"), ("NAPIŠTE NÁM", "KYPR")],
     "Jak se platí novostavba na Kypru?",
     ["Rezervace vybraného bytu a kupní smlouva", "Cena po částech podle postupu stavby",
      "Splátky končí dokončením projektu"],
     "Novostavby na Kypru najdete na webu realitykypr.cz"),
]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("-", " ").split())


# ---------------------------------------------------------------- HeyGen API
KEY = []


def api_key():
    """the HeyGen key from the secret; if the secret was pasted with more lines, the part that HeyGen accepts"""
    if not KEY:
        parts = list(dict.fromkeys(os.environ.get("HEYGEN_API_KEY", "").split()))
        KEY.append(parts[0] if parts else "")
        if len(parts) > 1:
            log("HEYGEN_API_KEY has %d parts - trying each" % len(parts))
            for p in parts:
                try:
                    if requests.get(API + "/v2/voices", headers={"X-Api-Key": p}, timeout=60).status_code == 200:
                        KEY[0] = p
                        break
                except Exception:
                    pass
    return KEY[0]


def hg(method, path, **kw):
    r = requests.request(method, API + path, timeout=90,
                         headers={"X-Api-Key": api_key(), "Accept": "application/json"}, **kw)
    try:
        j = r.json()
    except Exception:
        raise RuntimeError("HeyGen %s %s: HTTP %s %s" % (method, path, r.status_code, r.text[:300]))
    if r.status_code >= 400 or j.get("error"):
        raise RuntimeError("HeyGen %s %s: HTTP %s %s" % (method, path, r.status_code, json.dumps(j)[:400]))
    return j.get("data") or {}


def my_avatars():
    """name -> (type, id) for photo avatars (talking photos / looks) and normal avatars of the account"""
    out = {}
    try:
        d = hg("GET", "/v2/avatars")
        for p in d.get("talking_photos") or []:
            out.setdefault(norm(p.get("talking_photo_name")), ("talking_photo", p.get("talking_photo_id")))
        for a in d.get("avatars") or []:
            out.setdefault(norm(a.get("avatar_name")), ("avatar", a.get("avatar_id")))
    except Exception as e:
        log("avatars list failed:", e)
    try:
        groups = hg("GET", "/v2/avatar_group.list").get("avatar_group_list") or []
        for g in groups:
            looks = hg("GET", "/v2/avatar_group/%s/avatars" % g["id"]).get("avatar_list") or []
            if looks:
                out[norm(g.get("name"))] = ("talking_photo", looks[0]["id"])
    except Exception as e:
        log("avatar groups list failed:", e)
    return out


def my_voices():
    return hg("GET", "/v2/voices").get("voices") or []


def find_voice(voices, want):
    if os.environ.get("HEYGEN_VOICE_ID"):
        return os.environ["HEYGEN_VOICE_ID"]
    w = norm(want)
    hits = [v for v in voices if norm(v.get("name")) == w] or [v for v in voices if norm(v.get("name")).startswith(w)] or [v for v in voices if w in norm(v.get("name"))]
    if not hits:
        raise RuntimeError("voice '%s' not found in HeyGen - run MODE=list to see the names" % want)
    return hits[0]["voice_id"]


def heygen_video(kind, avatar_id, voice_id, script, out):
    character = {"type": kind, ("talking_photo_id" if kind == "talking_photo" else "avatar_id"): avatar_id}
    if kind == "talking_photo" and os.environ.get("HEYGEN_AVATAR_IV") == "1":
        character["use_avatar_iv_model"] = True
    body = {"title": "MNM reel " + datetime.now().strftime("%Y-%m-%d"), "dimension": {"width": W, "height": H},
            "video_inputs": [{"character": character,
                              "voice": {"type": "text", "input_text": script, "voice_id": voice_id, "speed": 1.05}}]}
    vid = hg("POST", "/v2/video/generate", json=body)["video_id"]
    log("HeyGen video id", vid)
    for _ in range(120):  # up to 30 minutes
        time.sleep(15)
        s = hg("GET", "/v1/video_status.get", params={"video_id": vid})
        log("HeyGen status:", s.get("status"))
        if s.get("status") == "completed":
            data = requests.get(s["video_url"], timeout=300).content
            open(out, "wb").write(data)
            return float(s.get("duration") or 0)
        if s.get("status") == "failed":
            raise RuntimeError("HeyGen video failed: %s" % json.dumps(s.get("error"))[:300])
    raise RuntimeError("HeyGen video not ready after 30 minutes")


def share_video(ref, out):
    """download a video made on the HeyGen web from its share page (shared as 'Anyone with the link'); ref = video id or share link"""
    urls = [ref]
    if "/share/" in ref or not ref.startswith("http"):
        vid = ref.rstrip("/").split("/")[-1].split("?")[0]
        html = requests.get("https://app.heygen.com/share/" + vid, headers=R.UA, timeout=60).text
        html = re.sub(r"\\+u0026", "&", html)
        html = re.sub(r"\\+/", "/", html).replace("&amp;", "&")
        urls = list(dict.fromkeys(re.findall(r'https://[a-z0-9.]*heygen\.ai/[^"\\\s<]+?\.mp4[^"\\\s<]*', html)))
        urls.sort(key=lambda u: "transcode" not in u)
    for u in urls:
        r = requests.get(u, timeout=300)
        log("video file:", u.split("?")[0].split("/")[-1], r.status_code, len(r.content))
        if r.status_code == 200 and len(r.content) > 200000:
            open(out, "wb").write(r.content)
            return
    raise RuntimeError("no downloadable video found for " + ref.split("?")[0])


# ---------------------------------------------------------------- titles, subtitles, music
def gold_text(d, xy, text, f):
    x, y = xy
    for dx, dy in ((5, 6), (3, 4)):
        d.text((x + dx, y + dy), text, font=f, fill=(0, 0, 0, 170), anchor="ma")
    d.text((x, y + 3), text, font=f, fill=GOLD_DARK + (255,), anchor="ma")
    d.text((x, y), text, font=f, fill=GOLD + (255,), anchor="ma")


def title_png(out, small, big):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fs = font(R.FONT_BOLD, 62)
    for dx, dy in ((3, 3), (2, 2)):
        d.text((W // 2 + dx, 880 + dy), small, font=fs, fill=(0, 0, 0, 170), anchor="ma")
    d.text((W // 2, 880), small, font=fs, fill=WHITE + (255,), anchor="ma")
    fb = R.fit_text(d, big, R.FONT_BOLD, 132, W - 90)
    gold_text(d, (W // 2, 955), big, fb)
    im.save(out)


def sub_png(out, text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(R.FONT_BOLD, 54)
    lines = wrap(d, text, f, W - 200)
    asc, desc = f.getmetrics()
    lh = asc + desc + 14
    y = 1500 - lh * len(lines) // 2
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 26, y - 6, W / 2 + tw / 2 + 26, y + asc + desc + 8], radius=22, fill=(0, 0, 0, 165))
        d.text((W // 2, y), ln, font=f, fill=WHITE + (255,), anchor="ma")
        y += lh
    im.save(out)


def chunks(script, n=6):
    """the script cut into short subtitle pieces of about n words, never across a sentence end"""
    out, cur = [], []
    for w_ in script.split():
        cur.append(w_)
        if len(cur) >= n or w_[-1] in ".?!" or (len(cur) >= 4 and w_[-1] == ","):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def finish(src, topic, dur, out):
    """gold titles + subtitles + quiet music on the HeyGen video, encoded for Instagram"""
    os.makedirs(R.WORK, exist_ok=True)
    script, titles = topic[2], topic[3]
    overlays = []  # (png, start, end)
    seg = dur / len(titles)
    for i, (small, big) in enumerate(titles):
        p = "%s/hg_title%d.png" % (R.WORK, i)
        title_png(p, small, big)
        overlays.append((p, i * seg + 0.15, min(dur, i * seg + min(seg - 0.25, 4.5))))
    parts = chunks(script)
    total = float(sum(len(p) for p in parts))
    t = 0.0
    for i, part in enumerate(parts):
        p = "%s/hg_sub%d.png" % (R.WORK, i)
        sub_png(p, part.rstrip(","))
        e = t + dur * len(part) / total
        overlays.append((p, t, e))
        t = e
    track = None
    mp3 = "%s/hg_music.mp3" % R.WORK
    try:
        track, _ = R.music(mp3)
    except Exception as e:
        log("music failed:", e)
    args = ["-i", src]
    for p, _, _ in overlays:
        args += ["-i", p]
    flt = ["[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1[v0]" % (W, H, W, H)]
    for i, (_, s, e) in enumerate(overlays):
        flt.append("[v%d][%d:v]overlay=0:0:enable='between(t,%.2f,%.2f)'[v%d]" % (i, i + 1, s, e, i + 1))
    amap = "0:a"
    if track and os.path.exists(mp3):
        args += ["-stream_loop", "-1", "-i", mp3]
        flt.append("[%d:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" % (len(overlays) + 1))
        amap = "[a]"
    ff(args + ["-filter_complex", ";".join(flt), "-map", "[v%d]" % len(overlays), "-map", amap, "-t", "%.2f" % dur]
       + R.IG_ENC + [out])
    return track


def probe(path):
    import subprocess
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip()
    return float(o or 0)


def caption(topic, track):
    key, cc, script, titles, hook, points, web = topic
    c = PRESENTERS[cc]
    lines = ["🌊 " + hook, ""] + ["✅ " + p for p in points]
    lines += ["", "👉 " + web, "📩 Napište nám do zpráv " + c["dm"] + " – odpovíme česky.",
              "🇨🇿 17 let jen nemovitosti u moře · kompletní servis",
              "", "ℹ️ " + LEGAL, "🤖 Videem provází AI průvodkyně.", "",
              " ".join(list(dict.fromkeys(c["tags"] + COMMON_TAGS))[:15])]
    return "\n".join(lines)


# ---------------------------------------------------------------- main
def main():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    force = os.environ.get("FORCE") == "1"
    dry = os.environ.get("DRY_RUN") == "1"
    mode = os.environ.get("MODE", "").strip()
    video_url = os.environ.get("VIDEO_URL", "").strip()
    if video_url:  # a video already made on the HeyGen web: no API key needed
        topic = next(t for t in TOPICS if t[0] == (os.environ.get("TOPIC", "").strip() or "K1"))
        os.makedirs(R.WORK, exist_ok=True)
        raw = "%s/heygen_raw.mp4" % R.WORK
        share_video(video_url, raw)
        log("downloaded video", os.path.getsize(raw), "bytes, topic", topic[0])
        track = finish(raw, topic, probe(raw), "final.mp4")
        cap = caption(topic, track)
        log(cap)
        if dry:
            log("DRY RUN - not publishing")
            return
        if not os.environ.get("IG_TOKEN"):
            log("IG_TOKEN is not set yet - nothing to publish")
            return
        mid = R.publish_reel("final.mp4", cap)
        posted = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
        posted[now.strftime("%Y-%m-%d")] = {"topic": topic[0], "media": mid, "at": now.isoformat()}
        json.dump(posted, open(POSTED, "w"), indent=1, ensure_ascii=False)
        log("Published HeyGen reel", mid, topic[0])
        return
    if not os.environ.get("HEYGEN_API_KEY"):
        log("HEYGEN_API_KEY is not set yet - nothing to do")
        return
    if mode == "list":
        for n, (k, i) in sorted(my_avatars().items()):
            log("AVATAR  %-40s %-14s %s" % (n, k, i))
        for v in my_voices():
            if (v.get("gender") or "").lower() != "male":
                log("VOICE   %-40s %-12s %s" % (v.get("name"), v.get("language"), v.get("voice_id")))
        return
    if not os.environ.get("IG_TOKEN") and not dry:
        log("IG_TOKEN is not set yet - nothing to publish")
        return
    if not force and (now.weekday() not in DAYS or now.hour != HOUR):
        log("Not HeyGen-reel time in Prague (%s) - skip" % now.strftime("%a %H:%M"))
        return
    posted = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
    day = now.strftime("%Y-%m-%d")
    if not force and day in posted:
        log("HeyGen reel already posted today")
        return
    avatars = my_avatars()
    ready = [t for t in TOPICS if norm(PRESENTERS[t[1]]["avatar"]) in avatars]
    if not ready:
        log("No presenter avatar found in HeyGen. Avatars there:", ", ".join(sorted(avatars)) or "none")
        return
    only = os.environ.get("TOPIC", "").strip()
    if only:
        topic = next(t for t in ready if t[0] == only)
    else:  # the topic that was posted longest ago (never posted first), in the order of the list
        last = {v["topic"]: d for d, v in sorted(posted.items())}
        topic = min(ready, key=lambda t: last.get(t[0], ""))
    c = PRESENTERS[topic[1]]
    kind, avatar_id = avatars[norm(c["avatar"])]
    voice_id = find_voice(my_voices(), c["voice"])
    log("topic", topic[0], "presenter", c["avatar"], kind, avatar_id, "voice", voice_id)
    os.makedirs(R.WORK, exist_ok=True)
    raw = "%s/heygen_raw.mp4" % R.WORK
    dur = heygen_video(kind, avatar_id, voice_id, topic[2], raw) or 0
    dur = probe(raw) or dur
    track = finish(raw, topic, dur, "final.mp4")
    cap = caption(topic, track)
    log(cap)
    if dry:
        log("DRY RUN - not publishing")
        return
    mid = R.publish_reel("final.mp4", cap)
    posted[day] = {"topic": topic[0], "media": mid, "at": now.isoformat()}
    json.dump(posted, open(POSTED, "w"), indent=1, ensure_ascii=False)
    log("Published HeyGen reel", mid, topic[0])


if __name__ == "__main__":
    main()
