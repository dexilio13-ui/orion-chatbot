import gradio as gr
import json
import os
from groq import Groq
from dotenv import load_dotenv  # [Ubačeno]

# Učitavanje .env fajla pre nego što klijent pokuša da pročita ključ
load_dotenv()  # [Ubačeno]

# Sada će os.environ.get("GROQ_API_KEY") moći da pronađe tvoj ključ
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
# Učitavanje tvojih podataka 
def nahrani_ai_podacima():
    try:
        with open('komponente.json', 'r', encoding='utf-8') as f:
            podaci = json.load(f)
            # Pretvaramo JSON u tekstualni format koji LLM razume 
            kontekst = ""
            for stavka in podaci:
                kontekst += f"- {stavka['kategorija']}: {stavka['naziv']} | Cena: {stavka['cena_rsd']} RSD\n"
            return kontekst
    except Exception as e:
        return f"Greška pri učitavanju podataka: {e}"

podaci_kontekst = nahrani_ai_podacima()

# Podešavanje Groq klijenta 
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def respond(message, history):
    system_prompt = f"""
    Ti si stručni prodavac hardvera u Orion Computers. 
    Na osnovu ovih realnih podataka iz prodavnice, sastavi konfiguraciju ili daj savet:
    
    Dostupni artikli i cene:
    {podaci_kontekst}
    
    Pravila:
    1. Koristi samo artikle sa liste.
    2. Saberi cene da bi se uklopio u budžet korisnika.
    3. Odgovaraj na srpskom jeziku.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    return response.choices[0].message.content

# Gradio interfejs
demo = gr.ChatInterface(
    respond,
    title="Orion Computers AI Savetnik",
    description="Pitaj me za konfiguraciju na osnovu trenutnih cena u Orionu!"
)

if __name__ == "__main__":
    demo.launch()