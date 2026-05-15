import requests
from bs4 import BeautifulSoup
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://www.orioncomputers.rs/konfigurator_nov.aspx"
}

MAPA = {
    "DropDownList1": "Maticna ploca",
    "DropDownList2": "Procesor",
    "DropDownList3": "RAM",
    "DropDownList5": "SSD/HDD",
    "DropDownList7": "Graficka karta",
    "DropDownList10": "Kuciste",
    "DropDownList18": "Napajanje"
}

def dohvati_cenu(dropdown_id, sifra):
    session = requests.Session()
    r1 = session.get("http://www.orioncomputers.rs/konfigurator_nov.aspx", headers=HEADERS)
    soup1 = BeautifulSoup(r1.text, 'html.parser')

    data = {
        "__EVENTTARGET": dropdown_id,
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": soup1.find('input', id='__VIEWSTATE')['value'],
        "__VIEWSTATEGENERATOR": soup1.find('input', id='__VIEWSTATEGENERATOR')['value'] if soup1.find('input', id='__VIEWSTATEGENERATOR') else "",
        "__EVENTVALIDATION": soup1.find('input', id='__EVENTVALIDATION')['value'] if soup1.find('input', id='__EVENTVALIDATION') else "",
        dropdown_id: sifra,
    }

    r2 = session.post("http://www.orioncomputers.rs/konfigurator_nov.aspx", headers=HEADERS, data=data)
    
    if 'Server Error' in r2.text:
        return None

    soup2 = BeautifulSoup(r2.text, 'html.parser')
    label = soup2.find('span', id='LabelSuma')
    if label:
        cena_tekst = label.text.strip()
        return float(cena_tekst.replace(',', ''))
    return None

def skrepuj_sve():
    # Uzmi početnu stranicu za listu komponenti
    r = requests.get("http://www.orioncomputers.rs/konfigurator_nov.aspx", headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    baza = []
    ukupno = sum(
        len([o for o in soup.find('select', id=did).find_all('option')
             if o.get('value') != 'nista' and o.text.strip() not in ['---', 'xxxxxx', '']])
        for did in MAPA if soup.find('select', id=did)
    )
    
    print(f"Ukupno komponenti za skrejpovanje: {ukupno}\n")
    brojac = 0

    for dropdown_id, kategorija in MAPA.items():
        select = soup.find('select', id=dropdown_id)
        if not select:
            continue

        opcije = [o for o in select.find_all('option')
                  if o.get('value') != 'nista' and o.text.strip() not in ['---', 'xxxxxx', '']]

        print(f"[{kategorija}] — {len(opcije)} komponenti")

        for o in opcije:
            naziv = o.text.strip()
            sifra = o.get('value')
            brojac += 1

            cena = dohvati_cenu(dropdown_id, sifra)
            status = f"{cena:.2f} RSD" if cena else "nema cene"
            print(f"  [{brojac}/{ukupno}] {naziv[:55]} → {status}")

            baza.append({
                "kategorija": kategorija,
                "naziv": naziv,
                "sifra": sifra,
                "cena_rsd": cena
            })

            time.sleep(0.5)

    with open('komponente.json', 'w', encoding='utf-8') as f:
        json.dump(baza, f, indent=4, ensure_ascii=False)

    print(f"\n✓ Gotovo! Sačuvano {len(baza)} komponenti u komponente.json")

if __name__ == "__main__":
    skrepuj_sve()