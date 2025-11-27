# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import os
import smtplib
from email.mime.text import MIMEText
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

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

# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
