import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import time

URL = "http://www.orioncomputers.rs/konfigurator_nov.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": URL,
}

# DropDownList4 je duplikat 3 ("Memorija #2"), 6 je duplikat 5 ("Hard disk #2"),
# a 17 je duplikat 16 ("Licencirani program #2") -- svi imaju identican skup opcija,
# pa skrepujemo samo prvi slot da ne bismo duplirali iste artikle.
MAPA = {
    "DropDownList1": "Maticna ploca",
    "DropDownList2": "Procesor",
    "DropDownList3": "RAM",
    "DropDownList5": "SSD/HDD",
    "DropDownList7": "Graficka karta",
    "DropDownList8": "Monitor",
    "DropDownList9": "Opticki uredjaj",
    "DropDownList10": "Kuciste",
    "DropDownList11": "Mis",
    "DropDownList12": "Podloga",
    "DropDownList13": "Tastatura",
    "DropDownList14": "Zvucnik",
    "DropDownList15": "Stampac",
    "DropDownList16": "Licencirani program",
    "DropDownList18": "Napajanje",
    "DropDownList19": "Web kamera",
    "DropDownList20": "Mrezna oprema",
    "DropDownList21": "USB fles",
    "DropDownList22": "Razni delovi",
}

IZLAZ = "komponente.json"
PAUZA = float(os.environ.get("SKREPAUZA", "0.6"))   # sekundi izmedju dva artikla
POKUSAJA = int(os.environ.get("SKREPOKUSAJA", "3"))  # broj ponavljanja za jedan artikal

# Ako vise od ovog procenta artikala ostane bez cene, ne upisujemo nista --
# bolje da stare (ali dobre) cene ostanu nego da se prepisu null vrednostima.
GRANICA_BEZ_CENE = 0.05
# Ako novi scrape ima manje od 80% artikala od prethodnog fajla, verovatno je
# nesto puklo na sajtu pa ne prelazimo na novi fajl.
GRANICA_PAD_ARTIKALA = 0.80
# Apsolutni minimum. Ako sajt vrati HTML bez <select> elemenata (ili promeni
# id-jeve), scrape vraca 0-5 artikala. Bez ove granice bi se fajl prepisao
# praznim i bot bi ostao bez ijedne cene.
MINIMALNO_ARTIKALA = 100

GREŠKE = []


def validne_opcije(select):
    return [o for o in select.find_all("option")
            if o.get("value") != "nista"
            and o.text.strip() not in ["---", "xxxxxx", ""]]


def _vrednost(soup, ident):
    el = soup.find("input", id=ident)
    return el["value"] if el else ""


def dohvati_cenu(dropdown_id, sifra):
    """Vraca cenu u dinarima, ili None ako je sajt ne odgovori kako ocekujemo."""
    zadnja_greska = None
    for pokusaj in range(POKUSAJA):
        try:
            session = requests.Session()
            r1 = session.get(URL, headers=HEADERS, timeout=30)
            if r1.status_code != 200:
                zadnja_greska = f"GET {r1.status_code}"
                continue
            soup1 = BeautifulSoup(r1.text, "html.parser")
            viewstate = soup1.find("input", id="__VIEWSTATE")
            if not viewstate:
                zadnja_greska = "nema __VIEWSTATE"
                continue

            r2 = session.post(URL, headers=HEADERS, data={
                "__EVENTTARGET": dropdown_id,
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate["value"],
                "__VIEWSTATEGENERATOR": _vrednost(soup1, "__VIEWSTATEGENERATOR"),
                "__EVENTVALIDATION": _vrednost(soup1, "__EVENTVALIDATION"),
                dropdown_id: sifra,
            }, timeout=30)

            if r2.status_code != 200 or "Server Error" in r2.text:
                zadnja_greska = f"POST {r2.status_code}"
                time.sleep(2 * (pokusaj + 1))
                continue

            label = BeautifulSoup(r2.text, "html.parser").find("span", id="LabelSuma")
            if not label:
                zadnja_greska = "nema LabelSuma"
                time.sleep(2 * (pokusaj + 1))
                continue

            return float(label.text.strip().replace(",", ""))
        except Exception as e:
            zadnja_greska = f"{type(e).__name__}: {e}"
            time.sleep(2 * (pokusaj + 1))

    GREŠKE.append(f"{dropdown_id}/{sifra}: {zadnja_greska}")
    return None


def skrepuj_sve():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    plan = []
    for dropdown_id, kategorija in MAPA.items():
        select = soup.find("select", id=dropdown_id)
        if not select:
            print(f"  UPOZORENJE: {dropdown_id} ne postoji na sajtu, preskacem")
            continue
        for o in validne_opcije(select):
            plan.append((dropdown_id, kategorija, o.text.strip(), o.get("value")))

    ukupno = len(plan)
    print(f"Ukupno komponenti za skrejpovanje: {ukupno}\n")
    baza = []
    for i, (dropdown_id, kategorija, naziv, sifra) in enumerate(plan, 1):
        cena = dohvati_cenu(dropdown_id, sifra)
        status = f"{cena:.2f} RSD" if cena is not None else "NEMA CENE"
        if cena is None:
            print(f" [{i}/{ukupno}] {naziv[:55]} -> {status}")
        elif i % 25 == 0:
            print(f" [{i}/{ukupno}] ... (zadnji: {naziv[:40]} -> {status})")
        baza.append({
            "kategorija": kategorija,
            "naziv": naziv,
            "sifra": sifra,
            "cena_rsd": cena,
        })
        time.sleep(PAUZA)

    bez_cene = [x for x in baza if x["cena_rsd"] is None]
    print(f"\nUkupno: {len(baza)} | sa cenom: {len(baza) - len(bez_cene)} | bez cene: {len(bez_cene)}")

    if GREŠKE:
        print(f"\n{len(GREŠKE)} gresaka pri konekciji/sajtu (prvih 10):")
        for g in GREŠKE[:10]:
            print(f"  - {g}")

    # ── zastita: ne prepisujemo dobar fajl losim scrape-om ──
    if len(baza) < MINIMALNO_ARTIKALA:
        print(f"\nGRESKA: samo {len(baza)} artikala (minimum {MINIMALNO_ARTIKALA}). "
              f"Verovatno se je promenila struktura sajta. Fajl NIJE azuriran.")
        return 1

    if baza:
        udeo = len(bez_cene) / len(baza)
        if udeo > GRANICA_BEZ_CENE:
            print(f"\nGRESKA: {udeo:.1%} artikala nema cenu (granica "
                  f"{GRANICA_BEZ_CENE:.0%}). Fajl NIJE azuriran.")
            return 1

    stari_broj = 0
    if os.path.exists(IZLAZ):
        try:
            with open(IZLAZ, encoding="utf-8") as f:
                stari_broj = len(json.load(f))
        except Exception:
            stari_broj = 0

    if stari_broj and len(baza) < stari_broj * GRANICA_PAD_ARTIKALA:
        print(f"\nGRESKA: novi scrape ima {len(baza)} artikala, prethodni "
              f"{stari_broj} (padoo ispod {GRANICA_PAD_ARTIKALA:.0%}). Fajl NIJE azuriran.")
        return 1

    with open(IZLAZ, "w", encoding="utf-8") as f:
        json.dump(baza, f, indent=4, ensure_ascii=False)

    kategorije = len({x["kategorija"] for x in baza})
    print(f"\nOK: sacuvano {len(baza)} komponenti u {kategorije} kategorija -> {IZLAZ}")
    return 0


if __name__ == "__main__":
    sys.exit(skrepuj_sve())