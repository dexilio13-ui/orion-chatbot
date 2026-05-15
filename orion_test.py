import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

url = "http://www.orioncomputers.rs/konfigurator_nov.aspx"
response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, 'html.parser')

# Sačuvaj ceo HTML u fajl da možemo da vidimo strukturu
with open("orion_konfigurator.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Stranica sačuvana! Veličina: {len(response.text)} karaktera")
print("\n--- Tražimo komponente ---")

# Pokušaj da nađeš select/dropdown elemente (tu su obično komponente)
selecti = soup.find_all('select')
print(f"Broj dropdown menija: {len(selecti)}")
for s in selecti:
    print(f"\nID: {s.get('id', 'nema')} | Name: {s.get('name', 'nema')}")
    opcije = s.find_all('option')[:5]  # prvih 5 opcija
    for o in opcije:
        print(f"  → {o.text.strip()}")