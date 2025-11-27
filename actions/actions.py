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

        # Recupera le variabili d'ambiente passate dal docker-compose
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        # Converte la porta in intero, default 587
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        if not sender_email or not sender_password:
            dispatcher.utter_message(text="Errore configurazione server: mancano le credenziali.")
            return []

        msg = MIMEText(f"Messaggio inoltrato per conto di: {user_email}")
        msg['Subject'] = "Nuovo contatto dal Bot Rasa"
        msg['From'] = sender_email
        msg['To'] = sender_email 

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, sender_email, msg.as_string())
            server.quit()
            dispatcher.utter_message(text=f"Mail inviata correttamente per {user_email}!")
        except Exception as e:
            dispatcher.utter_message(text="Errore nell'invio della mail.")
            print(f"ERRORE SMTP: {e}")

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
