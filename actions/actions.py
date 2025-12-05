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
                    "model": "qwen3:0.6b", #"qwen2.5:0.5b", 
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
        degree_type = tracker.get_slot("degree_type")
        lang = tracker.get_slot("language")
        
        if not degree_field:
            msg = "Please select a degree field first." if lang != "it" else "Per favore seleziona prima un'area di studio."
            dispatcher.utter_message(text=msg)
            return []
        
        if not degree_type:
            msg = "Please select a degree type first." if lang != "it" else "Per favore seleziona prima il tipo di laurea."
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
            
            # Query per ottenere i corsi del field e type selezionati
            query = "SELECT id, name, type FROM degree WHERE category = %s AND type = %s"
            cur.execute(query, (degree_field, degree_type))
            degrees = cur.fetchall()
            
            cur.close()
            conn.close()

            if not degrees:
                msg = f"No degrees found for field '{degree_field}' and type '{degree_type}'." if lang != "it" else f"Nessun corso di laurea trovato per l'area '{degree_field}' e tipo '{degree_type}'."
                dispatcher.utter_message(text=msg)
                return []

            # Costruisci il messaggio con la lista
            if lang == "it":
                message = f"Ecco i corsi di laurea disponibili per {degree_field} ({degree_type}). Scrivi l'ID per sceglierne uno:\n"
            else:
                message = f"Here are the available degrees for {degree_field} ({degree_type}). Type the ID to choose one:\n"

            for d in degrees:
                # d = (id, name, type)
                message += f"- [{d[0]}] {d[1]}\n"

            dispatcher.utter_message(text=message)

        except Exception as e:
            print(f"DB ERROR: {e}")
            msg = "I cannot access the database right now." if lang != "it" else "Non riesco ad accedere al database al momento."
            dispatcher.utter_message(text=msg)

        return []


class ActionAskSelectedCourses(Action):
    """Mostra i corsi obbligatori e fa scegliere un corso opzionale."""
    
    def name(self) -> Text:
        return "action_ask_selected_courses"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        degree_id = tracker.get_slot("degree_id")
        lang = tracker.get_slot("language")
        
        if not degree_id:
            msg = "Please select a degree first." if lang != "it" else "Per favore seleziona prima un corso di laurea."
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
            
            # Query per ottenere il nome della laurea
            cur.execute("SELECT name FROM degree WHERE id = %s", (degree_id,))
            degree_result = cur.fetchone()
            degree_name = degree_result[0] if degree_result else degree_id
            
            # Query per ottenere i corsi obbligatori
            cur.execute("SELECT id, name FROM course WHERE degree_id = %s AND is_mandatory = TRUE", (degree_id,))
            mandatory_courses = cur.fetchall()
            
            # Query per ottenere i corsi opzionali
            cur.execute("SELECT id, name FROM course WHERE degree_id = %s AND is_mandatory = FALSE", (degree_id,))
            optional_courses = cur.fetchall()
            
            cur.close()
            conn.close()

            # Costruisci il messaggio
            if lang == "it":
                message = f"📚 **{degree_name}**\n\n"
                message += "📋 **Corsi Obbligatori** (inclusi automaticamente):\n"
            else:
                message = f"📚 **{degree_name}**\n\n"
                message += "📋 **Mandatory Courses** (automatically included):\n"

            for course in mandatory_courses:
                message += f"  ✅ {course[1]}\n"

            if optional_courses:
                if lang == "it":
                    message += "\n🎯 **Corsi Opzionali** - Scegli uno scrivendo il numero:\n"
                else:
                    message += "\n🎯 **Optional Courses** - Choose one by typing the number:\n"
                
                for course in optional_courses:
                    message += f"  [{course[0]}] {course[1]}\n"
            else:
                if lang == "it":
                    message += "\n(Nessun corso opzionale disponibile)"
                else:
                    message += "\n(No optional courses available)"

            dispatcher.utter_message(text=message)

        except Exception as e:
            print(f"DB ERROR: {e}")
            msg = "I cannot access the database right now." if lang != "it" else "Non riesco ad accedere al database al momento."
            dispatcher.utter_message(text=msg)

        return []

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
        # Valid fields from DB Enum (Note: 'Enginering' has a typo in DB)
        valid_fields = ['Enginering', 'Economics', 'Medicine', 'Science', 'Agriculture']
        
        # Mapping for user input to DB values
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

        # Normalize input
        normalized_value = slot_value.capitalize()
        
        # Apply mapping if exists, otherwise keep normalized value
        mapped_value = mapping.get(normalized_value, normalized_value)
        
        # Check if mapped value is valid
        if mapped_value in valid_fields:
             return {"degree_field": mapped_value}
        
        # Se non valido
        lang = tracker.get_slot("language")
        msg = f"'{slot_value}' is not a valid field. Please choose from: {', '.join(valid_fields)}"
        if lang == "it":
            msg = f"'{slot_value}' non è un'area valida. Scegli tra: {', '.join(valid_fields)}"
            
        dispatcher.utter_message(text=msg)
        return {"degree_field": None}

    def validate_degree_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `degree_type` value and map user input to DB values."""
        # Valid types from DB
        valid_types = ["Bachelor's Degree", "Master's Degree", "Single-Cycle Degree"]
        
        # Normalize input to lowercase for matching
        input_lower = slot_value.lower().strip()
        
        # Mapping for various user inputs to DB values
        bachelor_keywords = [
            "bachelor", "bachelors", "bachelor's", "bachelor's degree",
            "undergraduate", "undergrad", "3-year", "three year", "3 year",
            "first cycle", "triennale", "laurea triennale", "l1", "1st cycle"
        ]
        
        master_keywords = [
            "master", "masters", "master's", "master's degree",
            "graduate", "postgraduate", "post-graduate", "2-year", "two year", "2 year",
            "second cycle", "magistrale", "laurea magistrale", "lm", "2nd cycle"
        ]
        
        single_cycle_keywords = [
            "single cycle", "single-cycle", "singlecycle", "single-cycle degree",
            "5-year", "five year", "5 year", "6-year", "six year", "6 year",
            "combined", "long cycle", "integrated", "ciclo unico", "laurea a ciclo unico",
            "medicine single cycle", "lcu"
        ]
        
        # Check which type matches
        if any(kw in input_lower for kw in bachelor_keywords):
            return {"degree_type": "Bachelor's Degree"}
        elif any(kw in input_lower for kw in master_keywords):
            return {"degree_type": "Master's Degree"}
        elif any(kw in input_lower for kw in single_cycle_keywords):
            return {"degree_type": "Single-Cycle Degree"}
        
        # If already a valid type, return it
        for valid_type in valid_types:
            if valid_type.lower() in input_lower:
                return {"degree_type": valid_type}
        
        # Invalid input
        lang = tracker.get_slot("language")
        msg = f"'{slot_value}' is not a valid degree type. Please choose: Bachelor's Degree, Master's Degree, or Single-Cycle Degree."
        if lang == "it":
            msg = f"'{slot_value}' non è un tipo di laurea valido. Scegli tra: Laurea Triennale (Bachelor's), Laurea Magistrale (Master's), o Ciclo Unico (Single-Cycle)."
            
        dispatcher.utter_message(text=msg)
        return {"degree_type": None}

    def validate_degree_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `degree_id` value against DB."""
        degree_field = tracker.get_slot("degree_field")
        degree_type = tracker.get_slot("degree_type")
        
        if not degree_field:
            return {"degree_id": None} # Should not happen if flow is correct
        if not degree_type:
            return {"degree_id": None} # Should not happen if flow is correct

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Check if ID exists and belongs to the selected category and type
            query = "SELECT name FROM degree WHERE id = %s AND category = %s AND type = %s"
            cur.execute(query, (slot_value, degree_field, degree_type))
            result = cur.fetchone()
            
            cur.close()
            conn.close()

            if result:
                # Valid ID
                return {"degree_id": slot_value}
            else:
                lang = tracker.get_slot("language")
                msg = f"ID '{slot_value}' not found for field '{degree_field}' ({degree_type}). Please try again."
                if lang == "it":
                    msg = f"ID '{slot_value}' non trovato per l'area '{degree_field}' ({degree_type}). Riprova."
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
        """Validate `selected_courses` value - deve essere un ID di corso opzionale valido."""
        
        degree_id = tracker.get_slot("degree_id")
        lang = tracker.get_slot("language")
        
        if not degree_id:
            return {"selected_courses": None}
        
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Verifica che l'ID sia un corso opzionale valido per questa laurea
            cur.execute(
                "SELECT name FROM course WHERE id = %s AND degree_id = %s AND is_mandatory = FALSE",
                (slot_value, degree_id)
            )
            result = cur.fetchone()
            
            cur.close()
            conn.close()

            if result:
                return {"selected_courses": slot_value}
            else:
                msg = f"'{slot_value}' is not a valid optional course. Please choose from the list above."
                if lang == "it":
                    msg = f"'{slot_value}' non è un corso opzionale valido. Scegli dalla lista sopra."
                dispatcher.utter_message(text=msg)
                return {"selected_courses": None}

        except Exception as e:
            print(f"DB ERROR in validate_selected_courses: {e}")
            return {"selected_courses": None}


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
        degree_field = tracker.get_slot("degree_field")
        degree_id = tracker.get_slot("degree_id")
        selected_course_id = tracker.get_slot("selected_courses")
        lang = tracker.get_slot("language")
        
        if not user_email:
            msg = "I couldn't find your email to send the confirmation." if lang != "it" else "Non ho trovato la mail per inviare la conferma."
            dispatcher.utter_message(text=msg)
            return []

        # Recupera variabili ambiente
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        if not sender_email or not sender_password:
            print("ERRORE CONFIGURAZIONE: Mancano le credenziali nel file .env")
            msg = "I can't send the email because server configurations are missing." if lang != "it" else "Non posso inviare la mail perché mancano le configurazioni del server."
            dispatcher.utter_message(text=msg)
            return []

        # Recupera dati completi dal database
        degree_name = degree_id
        mandatory_courses_list = []
        optional_course_name = selected_course_id
        
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Recupera il nome della laurea
            cur.execute("SELECT name, type FROM degree WHERE id = %s", (degree_id,))
            degree_result = cur.fetchone()
            if degree_result:
                degree_name = degree_result[0]
                degree_type = degree_result[1]
            else:
                degree_type = "N/A"
            
            # Recupera i corsi obbligatori
            cur.execute("SELECT name FROM course WHERE degree_id = %s AND is_mandatory = TRUE", (degree_id,))
            mandatory_courses = cur.fetchall()
            mandatory_courses_list = [c[0] for c in mandatory_courses]
            
            # Recupera il nome del corso opzionale scelto
            if selected_course_id:
                cur.execute("SELECT name FROM course WHERE id = %s", (selected_course_id,))
                optional_result = cur.fetchone()
                if optional_result:
                    optional_course_name = optional_result[0]
            
            cur.close()
            conn.close()

        except Exception as e:
            print(f"DB ERROR in ActionSendEnrollmentEmail: {e}")
            # Continua comunque con i dati che abbiamo

        # Formatta la lista dei corsi obbligatori
        mandatory_str = "\n".join([f"  - {c}" for c in mandatory_courses_list]) if mandatory_courses_list else "  (Nessun corso obbligatorio trovato)"

        # Costruzione del corpo della mail
        subject = f"Conferma Iscrizione: {degree_name}"
        body = (
            f"Ciao {student_name},\n\n"
            f"Abbiamo registrato con successo il tuo interesse per il seguente percorso di studi:\n\n"
            f"═══════════════════════════════════════\n"
            f"📌 RIEPILOGO ISCRIZIONE\n"
            f"═══════════════════════════════════════\n\n"
            f"🎓 Area di Studio: {degree_field}\n"
            f"📚 Corso di Laurea: {degree_name} ({degree_id})\n"
            f"📋 Tipo: {degree_type}\n\n"
            f"───────────────────────────────────────\n"
            f"CORSI OBBLIGATORI:\n"
            f"───────────────────────────────────────\n"
            f"{mandatory_str}\n\n"
            f"───────────────────────────────────────\n"
            f"CORSO OPZIONALE SCELTO:\n"
            f"───────────────────────────────────────\n"
            f"  ⭐ {optional_course_name}\n\n"
            f"═══════════════════════════════════════\n\n"
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
            if lang == "it":
                dispatcher.utter_message(text=f"Perfetto {student_name}! 🎉 Ho inviato una mail di riepilogo a {user_email} con tutti i dettagli del corso '{degree_name}'.")
            else:
                dispatcher.utter_message(text=f"Perfect {student_name}! 🎉 I've sent a summary email to {user_email} with all the details about '{degree_name}'.")
            
        except Exception as e:
            print(f"ERRORE SMTP ENROLLMENT: {e}")
            msg = "I saved your data, but there was a technical error sending the confirmation email." if lang != "it" else "Ho salvato i tuoi dati, ma c'è stato un errore tecnico nell'invio dell'email di conferma."
            dispatcher.utter_message(text=msg)

        return []
            