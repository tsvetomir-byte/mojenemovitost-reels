"""Trend Reels - varied topics in the formats that perform best on Instagram now
(POV, myth vs fact, this or that, day in the life, quiz, top 3, mistakes, live weather comparison, food).
Not only real estate: lifestyle, food, beaches, travel facts. Used by info_reels.py (interleaved with the Cyprus/Spain
info topics, so the cycle is 60 days and nothing repeats within a month).

Placeholders filled live (Open-Meteo): {t:city} air temperature, {s:city} sea temperature. Cities in CITIES.
Each topic: (key, country, hook, [(big, small), ...], cta, extra hashtags, stock search queries)
"""

CITIES = {
    "praha": ("Praha", 50.08, 14.43, None),
    "limassol": ("Limassol", 34.68, 33.04, (34.62, 33.10)),
    "alicante": ("Alicante", 38.35, -0.48, (38.30, -0.45)),
    "hurghada": ("Hurghada", 27.26, 33.81, (27.20, 33.90)),
    "durres": ("Durrës", 41.32, 19.45, (41.30, 19.38)),
    "heraklion": ("Kréta", 35.34, 25.13, (35.40, 25.15)),
    "valletta": ("Malta", 35.90, 14.51, (35.92, 14.56)),
    "sal": ("Kapverdy", 16.75, -22.95, (16.70, -23.00)),
    "split": ("Split", 43.51, 16.44, (43.48, 16.40)),
    "burgas": ("Burgas", 42.50, 27.47, (42.48, 27.55)),
}

WEB = "mojenemovitostumore.cz"


def C(name, dm, tags, stock):
    return {"name": name, "web": WEB, "dm": dm, "tags": tags, "stock": stock}


KY = C("Kypr", "KYPR", ["#kypr", "#cyprus", "#zivotnakypru"], ["cyprus beach", "ayia napa", "limassol", "paphos"])
SP = C("Španělsko", "ŠPANĚLSKO", ["#spanelsko", "#spain", "#costablanca"], ["alicante beach", "costa blanca", "spain beach"])
AL = C("Albánie", "ALBÁNIE", ["#albanie", "#albania", "#ksamil"], ["ksamil beach", "albania coast", "albanian riviera"])
BG = C("Bulharsko", "BULHARSKO", ["#bulharsko", "#bulgaria", "#cernemore"], ["bulgaria black sea beach", "sozopol", "nessebar"])
GR = C("Řecko", "ŘECKO", ["#recko", "#greece", "#kreta"], ["crete beach", "greece island sea", "santorini"])
HR = C("Chorvatsko", "CHORVATSKO", ["#chorvatsko", "#croatia", "#jadran"], ["croatia coast", "split croatia", "dubrovnik sea"])
EG = C("Egypt", "EGYPT", ["#egypt", "#hurghada", "#rudemore"], ["hurghada beach", "red sea", "egypt red sea coast"])
MT = C("Malta", "MALTA", ["#malta", "#gozo", "#comino"], ["malta coast", "valletta", "comino blue lagoon"])
CV = C("Kapverdy", "KAPVERDY", ["#kapverdy", "#caboverde", "#sal"], ["cape verde beach", "sal island beach", "boa vista beach"])
SEA = C("Moře", "MOŘE", ["#zivotumore", "#dovolena", "#more"], ["turquoise sea beach", "mediterranean coast aerial", "beach sunset"])

TREND = [
    ("T1", SEA, "Kde je dnes nejtepleji u moře?",
     [("Hurghada {t:hurghada}", "Moře {s:hurghada}"), ("Kypr {t:limassol}", "Moře {s:limassol}"),
      ("Alicante {t:alicante}", "Moře {s:alicante}"), ("A Praha? {t:praha}", "Živě – dnešní teploty")],
     "Kam byste jeli? Napište do komentářů 👇", ["#pocasi", "#zimaumore"], ["beach sunny", "red sea beach", "sunny mediterranean beach"]),
    ("T2", KY, "Mýtus vs fakt: Kypr",
     [("Mýtus: Kypr je daleko", "Fakt: let z Prahy cca 3,5 hodiny"), ("Mýtus: jiná měna", "Fakt: na Kypru platíte eurem"),
      ("Fakt, který vás překvapí", "Na Kypru se jezdí vlevo")],
     "Věděli jste to? Napište do zpráv KYPR", ["#mytusvsfakt"], ["cyprus coast", "cyprus road sea", "paphos"]),
    ("T3", SP, "POV: Je listopad a vy snídáte na terase",
     [("Alicante dnes {t:alicante}", "Živě – venku u moře"), ("Moře {s:alicante}", "Procházka po pláži místo bundy"),
      ("Praha dnes {t:praha}", "…a tady to vypadá takhle")],
     "Chcete taky? Napište do zpráv ŠPANĚLSKO", ["#pov", "#zimaumore"], ["breakfast terrace sea view", "alicante beach", "spain terrace sea"]),
    ("T4", AL, "Ksamil: Maledivy Evropy?",
     [("Ksamil", "Jih Albánie, naproti Korfu"), ("Tyrkysové moře", "Malé ostrůvky kousek od břehu"),
      ("Albánie", "Kandidát na vstup do EU")],
     "Napište do zpráv ALBÁNIE – pošleme tipy", ["#maledivyevropy", "#skryteperly"], ["ksamil beach", "albania turquoise sea", "albanian riviera"]),
    ("T5", SEA, "3 chyby při koupi bytu u moře",
     [("1. Kupovat jen z fotek", "Lokalitu vždy uvidět na vlastní oči"), ("2. Nepočítat náklady", "Správa, energie, daně – předem"),
      ("3. Bez ověřeného makléře", "Smlouvy a převod v češtině")],
     "Uložte si to 🔖 a napište nám MOŘE", ["#tipy", "#koupebytu", "#reality"], ["seaside apartment", "sea view balcony", "coastal town aerial"]),
    ("T6", GR, "3 jídla, která musíte ochutnat na Krétě",
     [("Dakos", "Krétský chléb, rajčata, sýr, olivový olej"), ("Gyros", "Klasika, kterou zná každý"),
      ("Tzatziki", "Jogurt, okurka, česnek")],
     "Které je vaše oblíbené? Napište do komentářů", ["#reckejidlo", "#jidlo"], ["greek food", "crete taverna", "greek salad"]),
    ("T7", SEA, "Tohle nebo tohle? Kypr vs Španělsko",
     [("Kypr", "Teplo skoro celý rok, jezdí se vlevo"), ("Španělsko", "Spousta přímých letů z ČR i SR"),
      ("Obojí", "Euro, EU, moře a slunce")],
     "Kypr, nebo Španělsko? Napište do komentářů 👇", ["#tohlenebotohle"], ["cyprus beach", "spain beach", "mediterranean coast"]),
    ("T8", KY, "Den v životě na Kypru",
     [("7:30", "Káva na terase s výhledem na moře"), ("13:00", "Meze v taverně u pláže"),
      ("17:00", "Procházka při západu slunce")],
     "Takový den chcete? Napište do zpráv KYPR", ["#denvzivote", "#zivotumore"], ["coffee sea view", "cyprus taverna", "sunset beach walk"]),
    ("T9", BG, "Bulharsko a euro? Ano.",
     [("Od 1. 1. 2026", "Bulharsko platí eurem"), ("Černé moře", "Sozopol, Nesebar, Burgas"),
      ("Blízko", "Let z Prahy zhruba 2 hodiny")],
     "Napište do zpráv BULHARSKO", ["#euro", "#sozopol"], ["sozopol", "nessebar old town", "black sea beach"]),
    ("T10", SEA, "Kvíz: Kde se jezdí vlevo?",
     [("A) Kypr", "B) Malta  C) Chorvatsko"), ("Správně: A i B", "Kypr i Malta jezdí vlevo"),
      ("Chorvatsko", "Jezdí se vpravo jako u nás")],
     "Kolik jste uhodli? Napište do komentářů", ["#kviz", "#zajimavosti"], ["malta coast", "cyprus coast road", "croatia coast road"]),
    ("T11", HR, "Chorvatsko: euro i Schengen",
     [("Od roku 2023", "Euro a bez hraničních kontrol"), ("Autem z ČR", "Moře za jeden den jízdy"),
      ("Zlatni Rat", "Ikonická pláž na ostrově Brač")],
     "Napište do zpráv CHORVATSKO", ["#jadran", "#brac"], ["zlatni rat", "croatia coast", "split croatia"]),
    ("T12", EG, "U nás zima. V Hurghadě léto.",
     [("Hurghada dnes {t:hurghada}", "Živě"), ("Rudé moře {s:hurghada}", "Koupání po celý rok"),
      ("Praha dnes {t:praha}", "Rozdíl vidíte sami")],
     "Napište do zpráv EGYPT", ["#zimaumore", "#rudemore"], ["hurghada beach", "red sea coral", "egypt beach resort"]),
    ("T13", SP, "3 jídla, která musíte ochutnat ve Španělsku",
     [("Paella", "Rýže s mořskými plody z Valencie"), ("Tapas", "Malé chody k vínu"), ("Churros", "S horkou čokoládou")],
     "Které ochutnáte jako první? Napište do komentářů", ["#spanelskejidlo", "#tapas"], ["paella", "tapas bar spain", "churros chocolate"]),
    ("T14", MT, "Malta: moře a angličtina",
     [("Angličtina", "Úřední jazyk vedle maltštiny"), ("Blue Lagoon", "Tyrkysová zátoka na ostrově Comino"),
      ("EU a euro", "Bez starostí s měnou")],
     "Napište do zpráv MALTA", ["#bluelagoon"], ["comino blue lagoon", "malta coast", "valletta harbour"]),
    ("T15", SEA, "Uložte si: checklist před koupí bytu u moře",
     [("✔ Vzdálenost k moři", "V metrech, ne „kousek“"), ("✔ Měsíční náklady", "Správa, energie, pojištění"),
      ("✔ Pronájem", "Je v komplexu povolený?"), ("✔ Prohlídka na místě", "Ideálně mimo sezónu")],
     "Uložte si to 🔖 a napište nám MOŘE", ["#checklist", "#koupebytu"], ["sea view apartment", "seaside residence pool", "coastal town"]),
    ("T16", KY, "Top 3 pláže Kypru",
     [("Nissi Beach", "Ayia Napa"), ("Fig Tree Bay", "Protaras"), ("Coral Bay", "Pafos")],
     "Kterou znáte? Napište do komentářů", ["#plaze", "#ayianapa", "#protaras"], ["nissi beach", "protaras beach", "paphos coral bay"]),
    ("T17", AL, "3 jídla, která musíte ochutnat v Albánii",
     [("Byrek", "Listové těsto se sýrem nebo špenátem"), ("Tavë kosi", "Pečené jehněčí s jogurtem"),
      ("Fërgesë", "Papriky, rajčata a sýr")],
     "Napište do zpráv ALBÁNIE", ["#albanskejidlo"], ["albanian food", "byrek", "albania restaurant sea"]),
    ("T18", SEA, "Tohle nebo tohle? Řecko vs Chorvatsko",
     [("Řecko", "Ostrovy, tavérny, teplejší moře"), ("Chorvatsko", "Autem z Česka za jeden den"),
      ("Obojí", "EU, euro, moře")],
     "Řecko, nebo Chorvatsko? Napište do komentářů 👇", ["#tohlenebotohle"], ["greek island", "croatia coast", "adriatic sea"]),
    ("T19", CV, "Kapverdy: léto i v zimě",
     [("Sal {t:sal}", "Živě – dnes"), ("Oceán {s:sal}", "Teplota vody dnes"), ("Sal a Boa Vista", "Ostrovy dlouhých pláží")],
     "Napište do zpráv KAPVERDY", ["#zimaumore"], ["sal cape verde beach", "cape verde ocean", "boa vista dunes"]),
    ("T20", SEA, "Mýtus vs fakt: byt u moře",
     [("Mýtus: jen pro bohaté", "Fakt: novostavby i na splátky"), ("Mýtus: složitý převod", "Fakt: s makléřem česky krok za krokem"),
      ("Mýtus: jen na dovolenou", "Fakt: mimo sezónu se dá pronajímat")],
     "Napište nám MOŘE – odpovíme česky", ["#mytusvsfakt", "#investice"], ["sea view apartment", "pool sea view", "coastal residence"]),
    ("T21", GR, "Balos: pláž jako z pohlednice",
     [("Balos", "Severozápad Kréty"), ("Laguna", "Mělká tyrkysová voda"), ("Kréta", "Největší řecký ostrov")],
     "Napište do zpráv ŘECKO", ["#balos", "#kreta"], ["balos crete", "crete lagoon", "crete beach"]),
    ("T22", SEA, "Kde je dnes moře nejteplejší?",
     [("Kapverdy {s:sal}", "Živě"), ("Rudé moře {s:hurghada}", "Hurghada"), ("Kypr {s:limassol}", "Limassol"),
      ("Malta {s:valletta}", "Živě – dnešní data")],
     "Kam skočíte do vody? Napište do komentářů", ["#more", "#zimaumore"], ["swimming sea", "turquoise water", "beach swim"]),
    ("T23", BG, "3 jídla, která musíte ochutnat v Bulharsku",
     [("Šopský salát", "Rajčata, okurky, sirene"), ("Banica", "Pečivo se sýrem"), ("Tarator", "Studená okurková polévka")],
     "Které znáte? Napište do komentářů", ["#bulharskejidlo"], ["bulgarian food", "shopska salad", "black sea restaurant"]),
    ("T24", SEA, "POV: Váš home office na příští měsíc",
     [("Notebook a moře", "Místo šedé kanceláře"), ("Polední pauza", "Na pláži, ne v jídelně"),
      ("Večer", "Západ slunce z terasy")],
     "Chcete to taky? Napište nám MOŘE", ["#pov", "#homeoffice", "#digitalninomad"], ["laptop sea view", "remote work beach", "terrace sunset sea"]),
    ("T25", HR, "Den v životě v Dalmácii",
     [("8:00", "Trh s rybami a zeleninou"), ("12:00", "Koupání v průzračné vodě"), ("20:00", "Večeře na nábřeží")],
     "Napište do zpráv CHORVATSKO", ["#dalmacie", "#denvzivote"], ["split croatia riva", "adriatic swim", "croatia harbour evening"]),
    ("T26", SEA, "Kvíz: uhodnete zemi podle jídla?",
     [("Halloumi", "Kypr"), ("Paella", "Španělsko"), ("Byrek", "Albánie")],
     "Kolik jste dali? Napište do komentářů", ["#kviz", "#jidlo"], ["halloumi grill", "paella", "mediterranean food"]),
    ("T27", EG, "3 jídla, která musíte ochutnat v Egyptě",
     [("Koshari", "Rýže, čočka, těstoviny a omáčka"), ("Ful medames", "Fazole na snídani"), ("Ta'ameya", "Egyptské falafely")],
     "Napište do zpráv EGYPT", ["#egyptskejidlo"], ["egyptian food", "falafel", "red sea restaurant"]),
    ("T28", SEA, "Neodkládejte to: kolik let ještě budete snít?",
     [("Rok 1", "„Jednou si koupíme byt u moře“"), ("Rok 5", "„Až bude lepší doba“"), ("Dnes", "Udělejte první krok")],
     "Napište nám MOŘE – nezávazně a česky", ["#motivace", "#sen"], ["sunrise sea", "beach couple walk", "sea view terrace"]),
    ("T29", MT, "Gozo: klidnější sestra Malty",
     [("Gozo", "Druhý největší maltský ostrov"), ("Trajekt", "Z Malty zhruba 25 minut"), ("Klid", "Útesy, zátoky, potápění")],
     "Napište do zpráv MALTA", ["#gozo"], ["gozo malta", "malta cliffs sea", "diving malta"]),
    ("T30", SEA, "Tohle nebo tohle? Albánie vs Bulharsko",
     [("Albánie", "Riviéra, kandidát na vstup do EU"), ("Bulharsko", "Černé moře, EU, euro"),
      ("Obojí", "Blízko, let cca 2 hodiny")],
     "Albánie, nebo Bulharsko? Napište do komentářů 👇", ["#tohlenebotohle"], ["albanian riviera", "black sea beach", "balkan coast"]),
]
