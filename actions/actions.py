# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import os
import smtplib
import json
import asyncio
import requests
from email.mime.text import MIMEText
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from crawl4ai import AsyncWebCrawler

class ActionSendEmail(Action):

    '''Invia una mail con i dettagli di contatto dell'utente.'''

    def name(self) -> Text:
        return "action_send_email"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_email = tracker.get_slot("email")
        
        if not user_email:
            dispatcher.utter_message(text="Non ho trovato la mail.")
            return []

        # Recupera variabili ambiente
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        print(f"DEBUG: Tentativo invio mail a {sender_email} tramite {smtp_server}:{smtp_port}")

        if not sender_email or not sender_password:
            error_msg = "ERRORE CONFIGURAZIONE: Mancano le credenziali nel file .env"
            print(error_msg)
            dispatcher.utter_message(text="Errore interno: credenziali mancanti.")
            return []

        msg = MIMEText(f"Ciao! Questo è un messaggio automatico di prova inoltrato per conto di: {user_email}\n\nSe leggi questo, il bot funziona!")
        msg['Subject'] = "Nuovo contatto dal Bot Rasa"
        msg['From'] = sender_email
        msg['To'] = user_email 

        try:
            # GESTIONE INTELLIGENTE SSL vs TLS
            if smtp_port == 465:
                # Usa connessione SSL diretta (Più sicura e stabile su Docker)
                print("DEBUG: Connessione SSL in corso...")
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                # Usa connessione TLS classica (Porta 587)
                print("DEBUG: Connessione TLS (starttls) in corso...")
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            # Login e Invio
            print("DEBUG: Login in corso...")
            server.login(sender_email, sender_password)
            
            print("DEBUG: Invio messaggio...")
            server.sendmail(sender_email, user_email, msg.as_string())
            
            server.quit()
            print("DEBUG: Mail inviata con successo!")
            
            # Conferma all'utente
            dispatcher.utter_message(text=f"Perfetto! Ho inviato una mail di conferma a {user_email} (che sei tu <3).")
            
        except smtplib.SMTPAuthenticationError:
            print("ERRORE CRITICO: Password o Mail sbagliata. Stai usando la App Password di Google?")
            dispatcher.utter_message(text="Errore di autenticazione mail.")
        except Exception as e:
            # Stampa l'errore esatto nel terminale Docker
            print(f"ERRORE GENERICO SMTP: {e}")
            dispatcher.utter_message(text="C'è stato un problema tecnico nell'invio.")

        return []


class ActionGetUniversityInfo(Action):
    """
    Recupera informazioni dal sito web dell'università usando Crawl4AI e le riassume con Ollama.
    Retrieves info from university website using Crawl4AI and summarizes with Ollama.
    """

    def name(self) -> Text:
        return "action_get_university_info"

    # Mappa degli argomenti agli URL (IT + EN support)
    URL_MAP = {
        # Italian keys
        "tasse": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "corsi": "https://www.univpm.it/Entra/Offerta_formativa",
        "iscrizione": "https://www.univpm.it/Entra/Immatricolazioni",
        "alloggi": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "generale": "https://www.univpm.it/Entra",
        
        # English keys (mapping to same URLs)
        "fees": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "tuition": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "courses": "https://www.univpm.it/Entra/Offerta_formativa",
        "degrees": "https://www.univpm.it/Entra/Offerta_formativa",
        "enrollment": "https://www.univpm.it/Entra/Immatricolazioni",
        "admission": "https://www.univpm.it/Entra/Immatricolazioni",
        "housing": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "accommodation": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "scholarships": "https://www.univpm.it/Entra/Tasse_e_contributi", # Often related
    }

    async def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 1. Identifica la lingua (default English se non specificato o diverso da 'it')
        # 1. Identify language (default English if not specified or not 'it')
        lang_slot = tracker.get_slot("language")
        language = "it" if lang_slot == "it" else "en"

        # 2. Identifica l'argomento richiesto
        topic = tracker.get_slot("topic")
        if not topic:
            topic = "generale"
        
        # Normalizza il topic (lower case)
        url = self.URL_MAP.get(topic.lower(), self.URL_MAP["generale"])
        
        # Feedback immediato all'utente (Bilingue)
        if language == "it":
            dispatcher.utter_message(text=f"Sto cercando informazioni su '{topic}' dal sito ufficiale...")
        else:
            dispatcher.utter_message(text=f"Searching for information about '{topic}' on the official website...")

        # 3. Scrape del contenuto con Crawl4AI
        extracted_text = ""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=url)
                extracted_text = result.markdown  # Otteniamo il markdown pulito
                
                if not extracted_text:
                    msg = "Non sono riuscito a leggere il contenuto della pagina." if language == "it" else "I couldn't read the page content."
                    dispatcher.utter_message(text=msg)
                    return []
                    
                # Limitiamo la lunghezza del testo per il prompt
                extracted_text = extracted_text[:6000] 

        except Exception as e:
            print(f"ERRORE CRAWL4AI: {e}")
            msg = f"Ho avuto un problema nel leggere il sito: {e}" if language == "it" else f"I encountered an issue reading the website: {e}"
            dispatcher.utter_message(text=msg)
            return []

        # 4. Invia a Ollama per il riassunto (Prompt Bilingue)
        try:
            user_question = tracker.latest_message.get('text')
            
            if language == "it":
                system_prompt = "Sei un assistente utile per l'Università UnivPM. Rispondi in ITALIANO."
                instruction = "RISPOSTA (sii conciso, in italiano, e cita la fonte se utile):"
            else:
                system_prompt = "You are a helpful assistant for UnivPM University. Answer in ENGLISH."
                instruction = "ANSWER (be concise, in English, and cite the source if useful):"

            prompt = (
                f"{system_prompt}\n"
                f"Answer the user's question using ONLY the context provided below.\n\n"
                f"CONTEXT (from {url}):\n{extracted_text}\n\n"
                f"USER QUESTION: {user_question}\n\n"
                f"{instruction}"
            )

            # Chiamata API a Ollama
            ollama_base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
            ollama_url = f"{ollama_base_url}/api/generate"

            ollama_response = requests.post(
                ollama_url,
                json={
                    "model": "qwen2.5:0.5b", 
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )

            if ollama_response.status_code == 200:
                ai_reply = ollama_response.json().get("response", "")
                dispatcher.utter_message(text=ai_reply)
            else:
                print(f"ERRORE OLLAMA: {ollama_response.text}")
                msg = "Ho letto i dati ma ho problemi a riassumerli al momento." if language == "it" else "I read the data but I'm having trouble summarizing it right now."
                dispatcher.utter_message(text=msg)

        except Exception as e:
            print(f"ERRORE CHIAMATA OLLAMA: {e}")
            msg = "Errore nella generazione della risposta." if language == "it" else "Error generating the response."
            dispatcher.utter_message(text=msg)

        return []