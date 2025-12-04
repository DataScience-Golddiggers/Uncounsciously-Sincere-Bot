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
import re
import psycopg2
from email.mime.text import MIMEText
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
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
        "tasse universitarie": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "retta": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "costo annuale": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "borse di studio": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "corsi": "https://www.univpm.it/Entra/Offerta_formativa",
        "iscrizione": "https://www.univpm.it/Entra/Immatricolazioni",
        "alloggi": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "generale": "https://www.univpm.it/Entra",
        
        # English keys (mapping to same URLs)
        "fees": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "tuition fees": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "tuition fee": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "annual fee": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "prices": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "tuition": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "courses": "https://www.univpm.it/Entra/Offerta_formativa",
        "degrees": "https://www.univpm.it/Entra/Offerta_formativa",
        "enrollment": "https://www.univpm.it/Entra/Immatricolazioni",
        "admission": "https://www.univpm.it/Entra/Immatricolazioni",
        "housing": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "accommodation": "https://www.univpm.it/Entra/Servizi_agli_studenti/Alloggi",
        "scholarships": "https://www.univpm.it/Entra/Tasse_e_contributi", # Often related
    }

    def clean_content(self, text: str) -> str:
        '''
        Clean the extracted content using regex to remove unwanted elements.
        :summary: Pulisce il contenuto estratto usando regex per rimuovere elementi indesiderati.
        
        :param self: Instance of the ActionGetUniversityInfo class
        :param text: Description of the text to be cleaned
        :type text: str
        :return: Descrizione
        :rtype: str
        '''

        # Rimuove immagini Markdown: ![alt](url)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        
        # Rimuove link Markdown mantenendo il testo: [testo](url) -> testo
        # Nota: Utile per risparmiare token, ma si perde il link.
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Rimuove tag HTML residui
        text = re.sub(r'<[^>]+>', '', text)
        
        # Rimuove righe con troppi caratteri speciali (separatori, ecc.), ma preserva tabelle
        # Le tabelle markdown usano | e -
        # Rimuoviamo linee che sono solo === o --- o *** se non sembrano tabelle
        text = re.sub(r'^\s*[-=_*]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Collassa newline multipli
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Rimuove spazi multipli
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()

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
                
                # Pulizia del testo con Regex
                extracted_text = self.clean_content(extracted_text)
                    
                # Limitiamo la lunghezza del testo per il prompt
                extracted_text = extracted_text[:8000] 

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
            # Quando si usa Docker Compose, il nome del servizio 'ollama' viene risolto automaticamente
            # nell'indirizzo IP del container. Quindi 'http://ollama:11434' è corretto.
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


class ActionAskDegreeId(Action):
    def name(self) -> Text:
        return "action_ask_degree_id"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        degree_field = tracker.get_slot("degree_field")
        lang = tracker.get_slot("language")
        
        if not degree_field:
            msg = "Please select a degree field first." if lang != "it" else "Per favore seleziona prima un'area di studio."
            dispatcher.utter_message(text=msg)
            return []

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Query per ottenere i corsi del field selezionato
            query = "SELECT id, name, type FROM degree WHERE category = %s"
            cur.execute(query, (degree_field,))
            degrees = cur.fetchall()
            
            cur.close()
            conn.close()

            if not degrees:
                msg = f"No degrees found for field '{degree_field}'." if lang != "it" else f"Nessun corso di laurea trovato per l'area '{degree_field}'."
                dispatcher.utter_message(text=msg)
                return []

            # Costruisci il messaggio con la lista
            if lang == "it":
                message = f"Ecco i corsi di laurea disponibili per {degree_field}. Scrivi l'ID per sceglierne uno:\n"
            else:
                message = f"Here are the available degrees for {degree_field}. Type the ID to choose one:\n"

            for d in degrees:
                # d = (id, name, type)
                message += f"- [{d[0]}] {d[1]} ({d[2]})\n"

            dispatcher.utter_message(text=message)

        except Exception as e:
            print(f"DB ERROR: {e}")
            msg = "I cannot access the database right now." if lang != "it" else "Non riesco ad accedere al database al momento."
            dispatcher.utter_message(text=msg)

        return []


class ValidateEnrollmentForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_enrollment_form"

    def validate_degree_field(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `degree_field` value."""
        # Valid fields from DB Enum
        valid_fields = ['Enginering', 'Economics', 'Medicine', 'Science', 'Agriculture']
        
        # Case insensitive check
        if slot_value.capitalize() in valid_fields: # DB has 'Enginering' typo, keep it or fix it? User provided SQL has 'Enginering'.
             # Mappa input utente (es. 'Ingegneria') ai valori DB se necessario, ma per ora assumiamo input diretto o entity mapping
             # Se l'entity extraction funziona bene, dovrebbe darci il valore corretto se mappato.
             # Ma controlliamo se l'utente ha scritto "Ingegneria" e mappiamolo a "Enginering"
             mapping = {
                 "Ingegneria": "Enginering",
                 "Engineering": "Enginering",
                 "Economia": "Economics",
                 "Economics": "Economics",
                 "Medicina": "Medicine",
                 "Medicine": "Medicine",
                 "Scienze": "Science",
                 "Science": "Science",
                 "Agraria": "Agriculture",
                 "Agriculture": "Agriculture"
             }
             mapped_value = mapping.get(slot_value.capitalize(), slot_value)
             
             if mapped_value in valid_fields:
                 return {"degree_field": mapped_value}
        
        # Se non valido
        lang = tracker.get_slot("language")
        msg = f"'{slot_value}' is not a valid field. Please choose from: {', '.join(valid_fields)}"
        if lang == "it":
            msg = f"'{slot_value}' non è un'area valida. Scegli tra: {', '.join(valid_fields)}"
            
        dispatcher.utter_message(text=msg)
        return {"degree_field": None}

    def validate_degree_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `degree_id` value against DB."""
        degree_field = tracker.get_slot("degree_field")
        if not degree_field:
            return {"degree_id": None} # Should not happen if flow is correct

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Check if ID exists and belongs to the selected category
            query = "SELECT name FROM degree WHERE id = %s AND category = %s"
            cur.execute(query, (slot_value, degree_field))
            result = cur.fetchone()
            
            cur.close()
            conn.close()

            if result:
                # Valid ID
                return {"degree_id": slot_value}
            else:
                lang = tracker.get_slot("language")
                msg = f"ID '{slot_value}' not found for field '{degree_field}'. Please try again."
                if lang == "it":
                    msg = f"ID '{slot_value}' non trovato per l'area '{degree_field}'. Riprova."
                dispatcher.utter_message(text=msg)
                return {"degree_id": None}

        except Exception as e:
            print(f"DB ERROR: {e}")
            return {"degree_id": None}

    def validate_email(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `email` value."""
        # Simple regex for email validation
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        
        if re.match(email_regex, slot_value):
            return {"email": slot_value}
        else:
            lang = tracker.get_slot("language")
            msg = "That doesn't look like a valid email. Please try again."
            if lang == "it":
                msg = "Non sembra un'email valida. Riprova per favore."
            dispatcher.utter_message(text=msg)
            return {"email": None}

    def validate_selected_courses(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `selected_courses` value."""
        
        # Se slot_value è una lista, bene. Se è un singolo valore, lo rendiamo lista.
        if isinstance(slot_value, str):
            selected_ids = [slot_value]
        else:
            selected_ids = slot_value

        # Lista dei corsi validi (hardcoded come da richiesta)
        # 10x: Informatica, 20x: Economia, 30x: Default
        valid_courses = [
            "101", "102", "103", "104", "105",
            "201", "202", "203", "204", "205",
            "301", "302", "303", "304", "305"
        ]
        
        # Filtra solo gli ID validi
        valid_selection = [cid for cid in selected_ids if cid in valid_courses]
        
        # Rimuovi duplicati
        valid_selection = list(set(valid_selection))

        if len(valid_selection) < 2:
            dispatcher.utter_message(text="Please select at least 2 valid courses from the list (e.g., 101 and 102).")
            return {"selected_courses": None}
        
        return {"selected_courses": valid_selection}


class ActionSendEnrollmentEmail(Action):
    '''Invia una mail di conferma registrazione corso con i dettagli dell'utente.'''

    def name(self) -> Text:
        return "action_send_enrollment_email"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Recupero dati dagli slot
        student_name = tracker.get_slot("student_name")
        user_email = tracker.get_slot("email")
        course_name = tracker.get_slot("course_name")
        degree_type = tracker.get_slot("degree_type")
        
        if not user_email:
            dispatcher.utter_message(text="Non ho trovato la mail per inviare la conferma.")
            return []

        # Recupera variabili ambiente (stessa logica di ActionSendEmail)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        if not sender_email or not sender_password:
            print("ERRORE CONFIGURAZIONE: Mancano le credenziali nel file .env")
            dispatcher.utter_message(text="Non posso inviare la mail perché mancano le configurazioni del server.")
            return []

        # Costruzione del corpo della mail
        subject = f"Conferma interesse: {course_name}"
        body = (
            f"Ciao {student_name},\n\n"
            f"Abbiamo registrato con successo il tuo interesse per il seguente corso di studi:\n\n"
            f"- Corso: {course_name}\n"
            f"- Tipo di Laurea: {degree_type}\n\n"
            f"Un orientatore ti contatterà presto a questo indirizzo email ({user_email}) per fornirti maggiori dettagli.\n\n"
            f"Cordiali saluti,\n"
            f"Il tuo Assistente Virtuale UnivPM"
        )

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = user_email 

        try:
            # Connessione SMTP
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, msg.as_string())
            server.quit()
            
            print(f"DEBUG: Mail di enrollment inviata a {user_email}")
            
            # Conferma all'utente
            dispatcher.utter_message(text=f"Perfetto {student_name}! Ho inviato una mail di riepilogo a {user_email} con i dettagli del corso '{course_name}'.")
            
        except Exception as e:
            print(f"ERRORE SMTP ENROLLMENT: {e}")
            dispatcher.utter_message(text="Ho salvato i tuoi dati, ma c'è stato un errore tecnico nell'invio dell'email di conferma.")

        return []
            