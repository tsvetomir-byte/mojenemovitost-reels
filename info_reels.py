#!/usr/bin/env python3
"""Moje nemovitost u more - daily INFO Reel (runs in GitHub Actions at about 19:00 Europe/Prague).

One info Reel per day, besides the two property Reels (7:30, 15:00) from reels.py.
Cyprus and Spain alternate; 15 Cyprus + 15 Spain topics = a 30-day cycle starting 2026-11-09,
so the same info never repeats within a month and the cycle starts again next month.
Info comes from realitykypr.web.app and spanelskydomov.web.app; weather and sea temperature are live (Open-Meteo).
Music: own Suno tracks from the "music" release (same as reels.py). Records posts in info_posted.json.
"""
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw

import reels as R
import trend_topics as TT
from reels import W, H, WHITE, font, fit_text, wrap, pill, shadow_text, ff, log

START = date(2026, 11, 9)
NAVY = (11, 37, 69)
SEA = (0, 122, 153)
CY = {"name": "Kypr", "web": "realitykypr.web.app", "dm": "KYPR", "lat": 34.98, "lon": 34.00, "sea": (34.95, 34.05),
      "town": "Ayia Napa", "stock": ["cyprus beach", "ayia napa", "cyprus coast", "limassol", "paphos", "turquoise sea beach"],
      "tags": ["#kypr", "#nemovitostikypr", "#bytnakypru", "#cyprus", "#zivotnakypru"]}
ES = {"name": "Španělsko", "web": "spanelskydomov.web.app", "dm": "ŠPANĚLSKO", "lat": 38.35, "lon": -0.48, "sea": (38.30, -0.45),
      "town": "Alicante", "stock": ["spain beach", "alicante", "costa blanca", "benidorm", "costa del sol", "mallorca beach"],
      "tags": ["#spanelsko", "#nemovitostispanelsko", "#bytvespanelsku", "#costablanca", "#spain"]}
COMMON_TAGS = ["#investicedonemovitosti", "#zivotumore", "#mojenemovitostumore", "#bydleniumore", "#reality", "#reels"]
LEGAL = "Nejedná se o nabídku k uzavření smlouvy. Ceny a údaje jsou orientační, ověřte je na webu."

# (key, country, hook, [(big, small), ...], cta_small, extra hashtags)
TOPICS = [
    ("K1", CY, "Letenky na Kypr? Všechny na jednom místě.",
     [("Larnaka i Pafos", "Na celý rok"), ("Ryanair, Wizz Air, Smartwings", "Porovnáte vše na jednom místě"),
      ("Před svátky kupte dřív", "Letenky jsou pak dražší")],
     "Hledejte letenky přímo na webu realitykypr.web.app → Letenky", ["#letenkynakypr", "#larnaka", "#pafos"]),
    ("S1", ES, "Letenky do Španělska z Prahy, Brna i Vídně",
     [("7 měst odletu", "Praha, Brno, Ostrava, Pardubice, Bratislava, Košice, Vídeň"),
      ("15 letišť ve Španělsku", "Alicante, Málaga, Valencie, Mallorca, Kanáry…"),
      ("Před svátky kupte dřív", "Letenky jsou pak dražší")],
     "Hledejte letenky přímo na webu spanelskydomov.web.app → Letenky", ["#letenkyspanelsko", "#alicante", "#malaga"]),
    ("K2", CY, "Kolik dnes vydělá byt na Kypru?",
     [("Kapitálový výnos", "Živě z cenového indexu Eurostatu"), ("Nájem – cena za noc dnes", "Živé hledání Airbnb a Booking"),
      ("Osobní použití", "Kalkulačka přímo na webu")],
     "Podívejte se na aktuální výnos na webu realitykypr.web.app → Výnos", ["#vynosnemovitosti", "#pronajemkypr"]),
    ("S2", ES, "Kolik dnes vydělá byt ve Španělsku?",
     [("Kapitálový výnos", "Živá data na webu"), ("Nájem – cena za noc dnes", "Živé hledání Airbnb a Booking"),
      ("Osobní použití", "Kalkulačka přímo na webu")],
     "Podívejte se na aktuální výnos na webu spanelskydomov.web.app → Výnos", ["#vynosnemovitosti", "#investice"]),
    ("K3", CY, "Pod cenou developera? Ano!",
     [("Rezervujeme už při startu", "Když je stavba ještě louka – nejnižší cena"),
      ("Okamžitá úspora", "Například 30 000 € oproti ceně developera"),
      ("Rezervováno pro vás", "Omezený počet jednotek")],
     "Napište nám do zpráv KYPR – pošleme aktuální nabídku", ["#podcenoudevelopera", "#protaras", "#ayianapa"]),
    ("S3", ES, "Přes 1 400 nemovitostí ve Španělsku česky",
     [("Největší platforma", "Pro Česko a Slovensko"), ("Costa Blanca, Costa del Sol", "Mallorca, Kanárské ostrovy"),
      ("Filtr od moře", "Do 300 m, do 1 km, do 3 km")],
     "Vyberte si na webu spanelskydomov.web.app", ["#torrevieja", "#marbella"]),
    ("K4", CY, "Nekupujte byt jen z fotek.",
     [("3 dny na Kypru", "S českým makléřem"), ("Ubytování + transfer", "2 noci a cesta z letiště i zpět"),
      ("500 € / rodina", "Při rezervaci nemovitosti vše vrátíme")],
     "Kupte si letenky ve Vámi vybraném termínu. O ostatní se postaráme my. Napište KYPR", ["#prohlidkakypr", "#kyprnavlastnioci"]),
    ("S4", ES, "Fotky ukážou byt. Cesta ukáže život.",
     [("3 dny ve Španělsku", "S českým makléřem"), ("Torrevieja, Alicante, Benidorm", "Projdeme lokality i pláže"),
      ("500 € / rodina", "Při rezervaci nemovitosti vše vrátíme")],
     "Napište nám do zpráv ŠPANĚLSKO", ["#prohlidkaspanelsko"]),
    ("K5", CY, "Provize za koupi na Kypru? 0 €.",
     [("0 % provize", "Za zprostředkování neplatíte"), ("Žádná překvapení", "Ostatní náklady vysvětlíme předem"),
      ("100 % servis", "Od výběru po správu přes prověřené partnery")],
     "Napište nám do zpráv KYPR", ["#realitykypr", "#bezprovize"]),
    ("S5", ES, "Nový byt s bazénem v Torrevieje",
     [("Centrum Torrevieji", "Pár minut k moři"), ("2 ložnice, bazén", "Novostavba na Costa Blanca"),
      ("Od cca 259 000 €", "Aktuální cenu ověříte na webu")],
     "Detail najdete na webu spanelskydomov.web.app", ["#torrevieja", "#bytsbazenem"]),
    ("K6", CY, "Byt u moře a platíte postupně?",
     [("Novostavby na splátky", "Stovky nabídek na Kypru"), ("Platíte podle stavby", "Po jednotlivých fázích"),
      ("Do dokončení projektu", "Splátky nejpozději do dokončení")],
     "Vyberte si na webu realitykypr.web.app → Na splátky", ["#novostavbakypr", "#nasplatky"]),
    ("S6", ES, "Ve Španělsku bez čekání na stavbu",
     [("Přes 1 300 hotových bytů", "Dokončené novostavby"), ("Klíče hned", "K okamžitému nastěhování"),
      ("Dovolená už letos", "Nebo pronájem od první sezóny")],
     "Vyberte si na webu spanelskydomov.web.app", ["#bytvespanelsku", "#hotovebyty"]),
    ("K7", CY, "Kolik stojí byt na Kypru měsíčně?",
     [("Příklad 75 m²", "≈ 182 € měsíčně, když byt používáte"), ("≈ 94 € měsíčně", "Když byt nepoužíváte"),
      ("Daň z nemovitosti 0 €", "Pojištění cca 190 € za rok")],
     "Celý příklad najdete na webu realitykypr.web.app → Náklady", ["#nakladynabyt"]),
    ("S7", ES, "Jaké je dnes počasí ve Španělsku?",
     [("{es_air}", "Dnes v Alicante – živě"), ("{es_sea}", "Teplota moře dnes"),
      ("Předpověď na měsíc", "Najdete přímo na webu")],
     "Podívejte se na předpověď na webu spanelskydomov.web.app", ["#pocasispanelsko", "#zimaumore"]),
    ("K8", CY, "U nás zima. Na Kypru moře.",
     [("{cy_sea}", "Teplota moře dnes – Ayia Napa"), ("{cy_air}", "Vzduch dnes – živě"),
      ("Předpověď na 30 dní", "Najdete přímo na webu")],
     "Podívejte se na předpověď na webu realitykypr.web.app", ["#pocasikypr", "#zimaumore"]),
    ("S8", ES, "Nový byt na Costa Blanca od cca 160 000 €",
     [("Jacarilla, Alicante", "Klidné místo u Costa Blanca"), ("Patio, parking, sklep", "Komplex s bazénem"),
      ("Větší byt 96 m²", "Cca 211 000 € – ověřte na webu")],
     "Napište nám do zpráv ŠPANĚLSKO", ["#costablanca", "#alicante"]),
    ("K9", CY, "DPH jen 5 %? Na Kypru ano.",
     [("Snížená sazba 5 %", "Kdy platí a jak se schvaluje"), ("Sazba 19 %", "A jak se vrací"),
      ("Celková cena", "Spočítáte si ji přímo na webu")],
     "Vše o DPH na webu realitykypr.web.app → Vše o koupi", ["#dphkypr"]),
    ("S9", ES, "Byt ve Španělsku a platíte postupně?",
     [("Novostavby na splátky", "Platíte během výstavby"), ("Nejnižší cena na začátku", "Při startu projektu"),
      ("Do dokončení projektu", "Splátky nejpozději do dokončení")],
     "Vyberte si na webu spanelskydomov.web.app → Na splátky", ["#novostavba", "#nasplatky"]),
    ("K10", CY, "Nechcete čekat na stavbu?",
     [("Stovky hotových novostaveb", "Na celém Kypru"), ("Klíče hned", "K okamžitému nastěhování"),
      ("Pronájem od první sezóny", "Správa přes prověřené partnery")],
     "Vyberte si na webu realitykypr.web.app", ["#bytkypr", "#hotovebyty"]),
    ("S10", ES, "Proč Češi kupují byty ve Španělsku?",
     [("Silný trh v EU", "Dlouhodobě stabilní"), ("Turismus a nájmy", "Vysoká poptávka po bydlení"),
      ("Slunce, moře, jídlo", "Investujte tam, kde jiní mají dovolenou")],
     "Více na webu spanelskydomov.web.app → Proč Španělsko", ["#procspanelsko", "#investice"]),
    ("K11", CY, "Byt u moře za polovinu? Jde to.",
     [("Doporučte nás", "Přátelům a známým"), ("2 % z ceny bytu", "Za každou dokončenou koupi"),
      ("25 doporučení", "= polovina ceny vašeho bytu")],
     "Podmínky na webu realitykypr.web.app → Výnos", ["#bytzapolovinu"]),
    ("S11", ES, "Byt ve Španělsku za polovinu?",
     [("Doporučte nás", "Přátelům a známým"), ("2 % z ceny bytu", "Za každou dokončenou koupi"),
      ("25 doporučení", "= polovina ceny vašeho bytu")],
     "Podmínky na webu spanelskydomov.web.app → Výnos", ["#bytzapolovinu"]),
    ("K12", CY, "Nemovitost s garantovaným příjmem",
     [("Garantovaný výnos", "U vybraných projektů"), ("Podle smlouvy", "Podmínky poskytovatele vždy předem"),
      ("Filtr na webu", "Pouze s garantovaným příjmem")],
     "Zapněte filtr na webu realitykypr.web.app", ["#garantovanyprijem"]),
    ("S12", ES, "Vila s bazénem 10 minut od Benidormu",
     [("Nova Polop", "Costa Blanca"), ("217 m² + suterén", "Soukromý bazén"),
      ("Cca 650 000 €", "Aktuální cenu ověříte na webu")],
     "Detail najdete na webu spanelskydomov.web.app", ["#benidorm", "#vila"]),
    ("K13", CY, "Jak se kupuje byt na Kypru?",
     [("Rezervace → smlouva", "Úvodní platba podle smlouvy"), ("ID a DIČ na místě", "Založíme za vás"),
      ("Splátky → klíče", "Plnou moc pro právníka připravíme")],
     "Celý postup na webu realitykypr.web.app → Vše o koupi", ["#koupebytu", "#jakkoupitbyt"]),
    ("S13", ES, "Nový komplex přímo od developera?",
     [("Všechny komplexy", "Na jednom místě"), ("Mapa s cenami", "Ceny od … € přímo na mapě"),
      ("Ceny od developera", "Bez přirážek")],
     "Zobrazte komplexy na webu spanelskydomov.web.app", ["#developer", "#novostavba"]),
    ("K14", CY, "Napálit se můžete jen jednou – s námi ne.",
     [("20 let jen moře", "První firma v oboru"), ("1 500+ majitelů", "Nových majitelů nemovitostí u moře"),
      ("Téměř 1 000 nabídek", "Na celém Kypru")],
     "Napište nám do zpráv KYPR", ["#recenze", "#realitykypr"]),
    ("S14", ES, "Kupujte ve Španělsku česky.",
     [("Český makléř", "Od výběru až po klíče"), ("20 let jen moře", "1 500+ nových majitelů"),
      ("WhatsApp", "Nikša Marinković +420 776 694 123")],
     "Napište nám do zpráv ŠPANĚLSKO", ["#ceskymakler"]),
    ("K15", CY, "Nemáte celou částku? Nevadí.",
     [("Až 2,5 mil. Kč", "ČSOB Půjčka na cokoliv, bez zajištění"), ("Nájem vs. splátka", "Porovnání přímo na webu"),
      ("Toto není nabídka", "K uzavření smlouvy – informativně")],
     "Spočítejte si to na webu realitykypr.web.app → Financování", ["#financovani"]),
    ("S15", ES, "Nevíte, kde začít? Pošleme TOP 5.",
     [("Napište rozpočet", "Lokalitu a účel koupě"), ("TOP 5 nabídek", "Přesně pro vás"),
      ("Nezávazně", "Zdarma a česky")],
     "Pošlete poptávku na webu spanelskydomov.web.app", ["#poptavka"]),
]


# 60-day cycle: info topic and trend topic alternate (trend = varied, not only real estate)
INFO_TOPICS = TOPICS
TOPICS = [t for pair in zip(INFO_TOPICS, TT.TREND) for t in pair]
CREDITS = []


def city_weather(key):
    name, lat, lon, sea = TT.CITIES[key]
    air = s = None
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=40,
                         params={"latitude": lat, "longitude": lon, "current": "temperature_2m"}).json()
        air = round(r["current"]["temperature_2m"])
    except Exception as e:
        log("air temp failed", key, e)
    if sea:
        try:
            r = requests.get("https://marine-api.open-meteo.com/v1/marine", timeout=40,
                             params={"latitude": sea[0], "longitude": sea[1], "current": "sea_surface_temperature"}).json()
            s = round(r["current"]["sea_surface_temperature"])
        except Exception as e:
            log("sea temp failed", key, e)
    return air, s


def live_fill(topic):
    """fill {t:city} / {s:city} placeholders with live temperatures; returns dict for fill()."""
    text = json.dumps(topic[2:5], ensure_ascii=False)
    wx = {}
    for kind, key in set(re.findall(r"\{([ts]):(\w+)\}", text)):
        air, sea = city_weather(key)
        v = air if kind == "t" else sea
        if v is None:
            return None  # no live data -> caller picks another topic (never show made-up numbers)
        wx[kind + ":" + key] = "%d °C" % v
    return wx


BOT_UA = {"User-Agent": "MojeNemovitostReels/1.0 (https://mojenemovitostumore.cz; info@mojenemovitostumore.cz)"}
OK_LIC = ("cc0", "public domain", "pd", "cc by")


def commons_photo(path, query):
    """free photo from Wikimedia Commons (CC0 / public domain / CC BY / CC BY-SA, no key needed)."""
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", timeout=30, headers=BOT_UA, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 40,
            "gsrsearch": query + " filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 1600}).json()
        pages = list(r.get("query", {}).get("pages", {}).values())
        random.shuffle(pages)
        for pg in pages:
            ii = (pg.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = re.sub(r"<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", "")).strip()
            if (ii.get("width") or 0) < 1200 or not lic.lower().startswith(OK_LIC) or pg["pageid"] in R._USED_STOCK:
                continue
            if re.search(r"map|logo|diagram|flag|coat of arms|plan|svg", pg.get("title", ""), re.I):
                continue
            try:
                data = requests.get(ii.get("thumburl") or ii["url"], timeout=40, headers=BOT_UA).content
                open(path, "wb").write(data)
                Image.open(path).convert("RGB").save(path, "JPEG", quality=92)
            except Exception as e:
                log("photo download failed", e)
                continue
            R._USED_STOCK.add(pg["pageid"])
            artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:40] or "autor neuveden"
            CREDITS.append("%s (%s)" % (artist, lic))
            log("photo (commons):", query, ii.get("descriptionurl"))
            return path
    except Exception as e:
        log("commons failed:", e)
    return None


def openverse_photo(path, query):
    """Wikimedia Commons first, Openverse as a second source."""
    if commons_photo(path, query):
        return path
    try:
        r = requests.get("https://api.openverse.org/v1/images/", timeout=30, headers=BOT_UA,
                         params={"q": query, "license": "cc0,pdm,by,by-sa", "size": "large", "page_size": 30,
                                 "mature": "false"}).json()
        hits = [h for h in r.get("results", []) if (h.get("width") or 0) >= 1000 and h.get("url")
                and h["id"] not in R._USED_STOCK]
        random.shuffle(hits)
        for h in hits[:6]:
            try:
                data = requests.get(h["url"], timeout=40, headers=BOT_UA).content
                open(path, "wb").write(data)
                Image.open(path).convert("RGB").save(path, "JPEG", quality=92)
                R._USED_STOCK.add(h["id"])
                lic = (h.get("license") or "").upper()
                CREDITS.append("%s (%s%s)" % (h.get("creator") or "autor neuveden", "CC " if lic not in ("CC0", "PDM") else "", lic))
                log("photo (openverse):", query, h.get("foreign_landing_url"))
                return path
            except Exception as e:
                log("photo download failed", e)
    except Exception as e:
        log("openverse failed:", e)
    return None


def weather(c):
    """live air + sea temperature (Open-Meteo). returns (air, sea) strings or None."""
    air = sea = None
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=30,
                         params={"latitude": c["lat"], "longitude": c["lon"], "current": "temperature_2m"}).json()
        air = round(r["current"]["temperature_2m"])
    except Exception as e:
        log("air temp failed", e)
    try:
        r = requests.get("https://marine-api.open-meteo.com/v1/marine", timeout=30,
                         params={"latitude": c["sea"][0], "longitude": c["sea"][1], "current": "sea_surface_temperature"}).json()
        sea = round(r["current"]["sea_surface_temperature"])
    except Exception as e:
        log("sea temp failed", e)
    return air, sea


def fill(text, wx):
    for k, v in wx.items():
        text = text.replace("{" + k + "}", v)
    return text


def info_overlay(out, tag, big, small, badge=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pill(d, (60, 140), tag, font(R.FONT_BOLD, 40))
    if badge:
        bf = font(R.FONT_BOLD, 36)
        pill(d, (60, 240), badge, bf, fill=WHITE, color=NAVY, pad=(30, 14))
    grad = Image.new("RGBA", (W, 900), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(900):
        gd.line([(0, i), (W, i)], fill=(0, 0, 0, int(210 * i / 900)))
    img.alpha_composite(grad, (0, H - 900))
    y = H - 640
    f = font(R.FONT_BOLD, 100)
    lines = wrap(d, big, f, W - 120)
    if len(lines) > 2:
        f = fit_text(d, big, R.FONT_BOLD, 90, (W - 120) * 2)
        lines = wrap(d, big, f, W - 120)
    for ln in lines:
        shadow_text(d, (60, y), ln, f)
        y += f.getmetrics()[0] + f.getmetrics()[1] + 4
    if small:
        sf = font(R.FONT_REG, 52)
        y += 14
        for ln in wrap(d, small, sf, W - 120):
            shadow_text(d, (60, y), ln, sf)
            y += 68
    img.save(out)


def info_hook(out, tag, hook, badge=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pill(d, (60, 140), tag, font(R.FONT_BOLD, 40))
    if badge:
        pill(d, (60, 240), badge, font(R.FONT_BOLD, 36), fill=WHITE, color=NAVY, pad=(30, 14))
    f = font(R.FONT_BOLD, 104)
    lines = wrap(d, hook, f, W - 140)
    y = (H - len(lines) * 128) // 2 - 60
    for ln in lines:
        shadow_text(d, (W // 2, y), ln, f, anchor="ma")
        y += 128
    img.save(out)


def info_end(out, c):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    shadow_text(d, (W // 2, 500), "Moje nemovitost", font(R.FONT_BOLD, 100), anchor="ma")
    shadow_text(d, (W // 2, 620), "u moře", font(R.FONT_BOLD, 100), anchor="ma")
    d.text((W // 2, 770), "20 let jen nemovitosti u moře", font=font(R.FONT_REG, 52), fill=WHITE, anchor="ma")
    pf = font(R.FONT_BOLD, 66)
    t = "Napište nám " + c["dm"]
    pill(d, (int((W - d.textlength(t, font=pf)) / 2) - 60, 910), t, pf, fill=WHITE, color=NAVY, pad=(60, 30))
    d.text((W // 2, 1160), "Najdete na webu", font=font(R.FONT_REG, 50), fill=WHITE, anchor="ma")
    d.text((W // 2, 1230), c["web"], font=font(R.FONT_BOLD, 60), fill=WHITE, anchor="ma")
    d.text((W // 2, 1360), "Česká realitní kancelář · kompletní servis", font=font(R.FONT_REG, 42), fill=WHITE, anchor="ma")
    img.save(out, quality=95)


def sea_background(out, seed):
    """fallback picture when no stock video: navy -> sea gradient."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    top, bot = NAVY, SEA if rnd.random() < 0.5 else (0, 150, 170)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    img.save(out, quality=95)


def clip(c, query, ovl, dur, out, n):
    sv = R.stock_clip("%s/s%d.mp4" % (R.WORK, n), query) or R.stock_clip("%s/s%d.mp4" % (R.WORK, n), random.choice(c["stock"]))
    if sv:
        R.clip_from_video(sv, ovl, dur, out)
        return
    ph = openverse_photo("%s/ph%d.jpg" % (R.WORK, n), query) or openverse_photo("%s/ph%d.jpg" % (R.WORK, n), random.choice(c["stock"]))
    if ph:
        bg = "%s/bgp%d.jpg" % (R.WORK, n)
        R.photo_frame(ph, bg) if Image.open(ph).width > Image.open(ph).height * 0.75 else Image.open(ph).save(bg)
        R.clip_from_image(bg, ovl, dur, out, move=n)
    else:
        bg = "%s/bg%d.jpg" % (R.WORK, n)
        sea_background(bg, n)
        R.clip_from_image(bg, ovl, dur, out, move=n)


def build(topic, wx, badge):
    key, c, hook, screens, cta = topic[:5]
    os.makedirs(R.WORK, exist_ok=True)
    tag = c["name"].upper() + (" · INFO" if key[0] in "KS" else "")
    queries = list(topic[6]) if len(topic) > 6 else c["stock"][:]
    random.shuffle(queries)
    clips, durs = [], []
    info_hook(R.WORK + "/ih.png", tag, hook, badge)
    clip(c, queries[0], R.WORK + "/ih.png", 3.0, R.WORK + "/i0.mp4", 0)
    clips.append(R.WORK + "/i0.mp4"); durs.append(3.0)
    for i, (big, small) in enumerate(screens, 1):
        ov = "%s/io%d.png" % (R.WORK, i)
        info_overlay(ov, tag, fill(big, wx), fill(small, wx), badge)
        out = "%s/i%d.mp4" % (R.WORK, i)
        clip(c, queries[i % len(queries)], ov, 2.8, out, i)
        clips.append(out); durs.append(2.8)
    ov = R.WORK + "/icta.png"
    info_overlay(ov, tag, "Napište nám " + c["dm"], cta, badge)
    clip(c, queries[-1], ov, 3.0, R.WORK + "/icta.mp4", 9)
    clips.append(R.WORK + "/icta.mp4"); durs.append(3.0)
    info_end(R.WORK + "/iend.jpg", c)
    empty = R.WORK + "/empty.png"
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(empty)
    R.clip_from_image(R.WORK + "/iend.jpg", empty, 3.0, R.WORK + "/iend.mp4", move=0)
    clips.append(R.WORK + "/iend.mp4"); durs.append(3.0)
    R.join_with_transitions(clips, durs, R.WORK + "/video.mp4")
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                         R.WORK + "/video.mp4"]).strip())
    track, credit = R.music(R.WORK + "/music.mp3")
    if track:
        ff(["-i", R.WORK + "/video.mp4", "-ss", "1.5", "-stream_loop", "-1", "-i", R.WORK + "/music.mp3",
            "-filter_complex", "[1:a]volume=0.9,afade=t=in:d=0.2,afade=t=out:st=%.2f:d=1.5[a]" % (dur - 1.5),
            "-map", "0:v", "-map", "[a]"] + R.IG_ENC + ["-t", "%.2f" % dur, "final.mp4"])
    else:
        ff(["-i", R.WORK + "/video.mp4", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"] + R.IG_ENC + ["-shortest", "final.mp4"])
    return "final.mp4", (track if credit else None)


def caption(topic, wx, badge, track):
    key, c, hook, screens, cta, extra = topic[:6]
    lines = ["🌊 " + hook, ""]
    lines += ["✅ " + fill(b, wx) + (" – " + fill(s, wx) if s else "") for b, s in screens]
    if badge:
        lines += ["", "☀️ " + badge]
    lines += ["", "👉 " + cta, "📩 Napište nám do zpráv " + c["dm"] + " – odpovíme česky.",
              "🇨🇿 20 let jen nemovitosti u moře · 1 500+ nových majitelů · kompletní servis",
              "", "ℹ️ " + LEGAL, "", " ".join(list(dict.fromkeys(extra + c["tags"] + COMMON_TAGS))[:15])]
    if CREDITS:
        lines += ["", "📷 Foto: " + ", ".join(dict.fromkeys(CREDITS)) + ""]
    if track:
        lines += ["", '🎵 Hudba: "%s" – Kevin MacLeod (incompetech.com), CC BY 4.0' % track]
    return "\n".join(lines)


def main():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    force = os.environ.get("FORCE") == "1"
    dry = os.environ.get("DRY_RUN") == "1"
    if not os.environ.get("IG_TOKEN") and not dry:
        log("IG_TOKEN is not set yet - nothing to publish")
        return
    if not force and now.hour != 19:
        log("Not info-reel time in Prague (%s) - skip" % now.strftime("%H:%M"))
        return
    posted = json.load(open("info_posted.json")) if os.path.exists("info_posted.json") else {}
    day = now.strftime("%Y-%m-%d")
    if not force and day in posted:
        log("Info reel already posted today")
        return
    only = os.environ.get("TOPIC", "").strip()
    if only:
        topic = next(t for t in TOPICS if t[0] == only)
    else:
        topic = TOPICS[(now.date() - START).days % len(TOPICS)]
    c = topic[1]
    air = sea = None
    wx = {}
    if "lat" in c:
        air, sea = weather(c)
        pre = "cy_" if c is CY else "es_"
        wx = {pre + "air": ("%d °C" % air) if air is not None else "Živé počasí",
              pre + "sea": ("Moře %d °C" % sea) if sea is not None else "Teplé moře"}
    live = live_fill(topic)
    if live is None:
        i = TOPICS.index(topic)
        topic = next(t for t in TOPICS[i + 1:] + TOPICS[:i] if "{" not in json.dumps(t[2:5], ensure_ascii=False))
        log("live weather unavailable - using topic", topic[0])
        c = topic[1]
        air = sea = None
        wx = {}
    else:
        wx.update(live)
    badge = None
    if air is not None:
        badge = "Dnes %s: %d °C" % (c["town"], air) + (" · moře %d °C" % sea if sea is not None else "")
    log("topic", topic[0], "weather", air, sea)
    video, track = build(topic, wx, badge)
    cap = caption(topic, wx, badge, track)
    log(cap)
    if dry:
        log("DRY RUN - not publishing")
        return
    mid = R.publish_reel(video, cap)
    posted[day] = {"topic": topic[0], "media": mid, "at": now.isoformat()}
    json.dump(posted, open("info_posted.json", "w"), indent=1, ensure_ascii=False)
    log("Published info reel", mid, topic[0])


if __name__ == "__main__":
    main()
