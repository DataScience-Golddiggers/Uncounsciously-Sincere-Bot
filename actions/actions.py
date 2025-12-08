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

    '''Sends an email with the user's contact details.'''

    def name(self) -> Text:
        return "action_send_email"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_email = tracker.get_slot("email")
        
        if not user_email:
            dispatcher.utter_message(text="I couldn't find the email.")
            return []

        # Retrieve environment variables
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        print(f"DEBUG: Attempting to send email to {sender_email} via {smtp_server}:{smtp_port}")

        if not sender_email or not sender_password:
            error_msg = "CONFIGURATION ERROR: Missing credentials in .env file"
            print(error_msg)
            dispatcher.utter_message(text="Internal error: missing credentials.")
            return []

        subject = "New contact from Rasa Bot"
        body = f"Hello! This is an automated test message forwarded on behalf of: {user_email}\n\nIf you read this, the bot is working!"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = user_email 

        try:
            # SSL vs TLS handling
            if smtp_port == 465:
                # Use direct SSL connection
                print("DEBUG: SSL connection...")
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                # Use TLS connection (Port 587)
                print("DEBUG: TLS connection (starttls)...")
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            # Login and Send
            print("DEBUG: Logging in...")
            server.login(sender_email, sender_password)
            
            print("DEBUG: Sending message...")
            server.sendmail(sender_email, user_email, msg.as_string())
            
            server.quit()
            print("DEBUG: Email sent successfully!")
            
            # Confirmation to user
            dispatcher.utter_message(text=f"Perfect! I've sent a confirmation email to {user_email} (that's you <3).")
            
        except smtplib.SMTPAuthenticationError:
            print("CRITICAL ERROR: Wrong Password or Email. Are you using Google App Password?")
            dispatcher.utter_message(text="Email authentication error.")
        except Exception as e:
            print(f"GENERIC SMTP ERROR: {e}")
            dispatcher.utter_message(text="There was a technical problem sending the email.")

        return []


class ActionGetUniversityInfo(Action):
    """
    Retrieves info from university website using Crawl4AI and summarizes with Ollama.
    """

    def name(self) -> Text:
        return "action_get_university_info"

    # Map of topics to URLs (English only)
    URL_MAP = {
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
        "scholarships": "https://www.univpm.it/Entra/Tasse_e_contributi",
        "general": "https://www.univpm.it/Entra",
    }

    def clean_content(self, text: str) -> str:
        '''
        Clean the extracted content using regex to remove unwanted elements.
        '''

        # Remove Markdown images: ![alt](url)
        text = re.sub(r'!\\\[.*?\\\\]\(.*?\\\)', '', text)
        
        # Remove Markdown links keeping text: [text](url) -> text
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Remove residual HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove lines with too many special characters, preserving tables
        text = re.sub(r'^\s*[-=_*]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Collapse multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()

    async def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 1. Identify the requested topic
        topic = tracker.get_slot("topic")
        if not topic:
            topic = "general"
        
        # Normalize topic (lower case)
        url = self.URL_MAP.get(topic.lower(), self.URL_MAP["general"])
        
        # Immediate feedback to user
        dispatcher.utter_message(text=f"Searching for information about '{topic}' on the official website...")

        # 2. Scrape content with Crawl4AI
        extracted_text = ""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=url)
                extracted_text = result.markdown  # Get clean markdown
                
                if not extracted_text:
                    dispatcher.utter_message(text="I couldn't read the page content.")
                    return []
                
                # Clean text with Regex
                extracted_text = self.clean_content(extracted_text)
                    
                # Limit text length for prompt
                extracted_text = extracted_text[:8000] 

        except Exception as e:
            print(f"CRAWL4AI ERROR: {e}")
            dispatcher.utter_message(text=f"I encountered an issue reading the website: {e}")
            return []

        # 3. Send to Ollama for summarization (English Prompt)
        try:
            user_question = tracker.latest_message.get('text')
            
            system_prompt = "You are a helpful assistant for UnivPM University. Answer in ENGLISH."
            instruction = "ANSWER (be concise, in English, and cite the source if useful):"

            prompt = (
                f"{system_prompt}\n"
                f"Answer the user's question using ONLY the context provided below.\n\n"
                f"CONTEXT (from {url}):\n{extracted_text}\n\n"
                f"USER QUESTION: {user_question}\n\n"
                f"{instruction}"
            )

            # API Call to Ollama
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
                print(f"OLLAMA ERROR: {ollama_response.text}")
                dispatcher.utter_message(text="I read the data but I'm having trouble summarizing it right now.")

        except Exception as e:
            print(f"OLLAMA CALL ERROR: {e}")
            dispatcher.utter_message(text="Error generating the response.")

        return []


class ActionAskDegreeId(Action):
    def name(self) -> Text:
        return "action_ask_degree_id"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        degree_field = tracker.get_slot("degree_field")
        degree_type = tracker.get_slot("degree_type")
        
        if not degree_field:
            dispatcher.utter_message(text="Please select a degree field first.")
            return []
        
        if not degree_type:
            dispatcher.utter_message(text="Please select a degree type first.")
            return []

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Query to get degrees for selected field and type
            query = "SELECT id, name, type FROM degree WHERE category = %s AND type = %s"
            cur.execute(query, (degree_field, degree_type))
            degrees = cur.fetchall()
            
            cur.close()
            conn.close()

            if not degrees:
                dispatcher.utter_message(text=f"No degrees found for field '{degree_field}' and type '{degree_type}'.")
                return []

            # Build message with list
            message = f"Here are the available degrees for {degree_field} ({degree_type}). Type the ID to choose one:\n"

            for d in degrees:
                # d = (id, name, type)
                message += f"- [{d[0]}] {d[1]}\n"

            dispatcher.utter_message(text=message)

        except Exception as e:
            print(f"DB ERROR: {e}")
            dispatcher.utter_message(text="I cannot access the database right now.")

        return []


class ActionAskSelectedCourses(Action):
    """Shows mandatory courses and asks to choose an optional course."""
    
    def name(self) -> Text:
        return "action_ask_selected_courses"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        degree_id = tracker.get_slot("degree_id")
        
        if not degree_id:
            dispatcher.utter_message(text="Please select a degree first.")
            return []

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Query to get degree name
            cur.execute("SELECT name FROM degree WHERE id = %s", (degree_id,))
            degree_result = cur.fetchone()
            degree_name = degree_result[0] if degree_result else degree_id
            
            # Query to get mandatory courses
            cur.execute("SELECT id, name FROM course WHERE degree_id = %s AND is_mandatory = TRUE", (degree_id,))
            mandatory_courses = cur.fetchall()
            
            # Query to get optional courses
            cur.execute("SELECT id, name FROM course WHERE degree_id = %s AND is_mandatory = FALSE", (degree_id,))
            optional_courses = cur.fetchall()
            
            cur.close()
            conn.close()

            # Build message
            message = f"📚 **{degree_name}**\n\n"
            message += "📋 **Mandatory Courses** (automatically included):\n"

            for course in mandatory_courses:
                message += f"  ✅ {course[1]}\n"

            if optional_courses:
                message += "\n🎯 **Optional Courses** - Choose one by typing the number:\n"
                
                for course in optional_courses:
                    message += f"  [{course[0]}] {course[1]}\n"
            else:
                message += "\n(No optional courses available)"

            dispatcher.utter_message(text=message)

        except Exception as e:
            print(f"DB ERROR: {e}")
            dispatcher.utter_message(text="I cannot access the database right now.")

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
             "Engineering": "Enginering",
             "Economics": "Economics",
             "Medicine": "Medicine",
             "Science": "Science",
             "Agriculture": "Agriculture"
        }

        # Normalize input
        normalized_value = slot_value.capitalize()
        
        # Apply mapping if exists, otherwise keep normalized value
        mapped_value = mapping.get(normalized_value, normalized_value)
        
        # Check if mapped value is valid
        if mapped_value in valid_fields:
             return {"degree_field": mapped_value}
        
        # If invalid
        msg = f"'{slot_value}' is not a valid field. Please choose from: {', '.join(valid_fields)}"
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
            "first cycle", "1st cycle"
        ]
        
        master_keywords = [
            "master", "masters", "master's", "master's degree",
            "graduate", "postgraduate", "post-graduate", "2-year", "two year", "2 year",
            "second cycle", "2nd cycle"
        ]
        
        single_cycle_keywords = [
            "single cycle", "single-cycle", "singlecycle", "single-cycle degree",
            "5-year", "five year", "5 year", "6-year", "six year", "6 year",
            "combined", "long cycle", "integrated", 
            "medicine single cycle"
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
        msg = f"'{slot_value}' is not a valid degree type. Please choose: Bachelor's Degree, Master's Degree, or Single-Cycle Degree."
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
            return {"degree_id": None} 
        if not degree_type:
            return {"degree_id": None}

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
                msg = f"ID '{slot_value}' not found for field '{degree_field}' ({degree_type}). Please try again."
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
            msg = "That doesn't look like a valid email. Please try again."
            dispatcher.utter_message(text=msg)
            return {"email": None}

    def validate_selected_courses(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `selected_courses` value - must be a valid optional course ID."""
        
        degree_id = tracker.get_slot("degree_id")
        
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
            
            # Verify ID is a valid optional course for this degree
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
                dispatcher.utter_message(text=msg)
                return {"selected_courses": None}

        except Exception as e:
            print(f"DB ERROR in validate_selected_courses: {e}")
            return {"selected_courses": None}


class ActionSendEnrollmentEmail(Action):
    '''Sends an enrollment confirmation email with user details.'''

    def name(self) -> Text:
        return "action_send_enrollment_email"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Retrieve data from slots
        student_name = tracker.get_slot("student_name")
        user_email = tracker.get_slot("email")
        degree_field = tracker.get_slot("degree_field")
        degree_id = tracker.get_slot("degree_id")
        selected_course_id = tracker.get_slot("selected_courses")
        
        if not user_email:
            msg = "I couldn't find your email to send the confirmation."
            dispatcher.utter_message(text=msg)
            return []

        # Retrieve environment variables
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")

        if not sender_email or not sender_password:
            print("CONFIGURATION ERROR: Missing credentials in .env file")
            msg = "I can't send the email because server configurations are missing."
            dispatcher.utter_message(text=msg)
            return []

        # Retrieve full data from database
        degree_name = degree_id
        mandatory_courses_list = []
        optional_course_name = selected_course_id
        degree_type = "N/A"
        
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "mydb"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "supersecret")
            )
            cur = conn.cursor()
            
            # Retrieve degree name
            cur.execute("SELECT name, type FROM degree WHERE id = %s", (degree_id,))
            degree_result = cur.fetchone()
            if degree_result:
                degree_name = degree_result[0]
                degree_type = degree_result[1]
            
            # Retrieve mandatory courses
            cur.execute("SELECT name FROM course WHERE degree_id = %s AND is_mandatory = TRUE", (degree_id,))
            mandatory_courses = cur.fetchall()
            mandatory_courses_list = [c[0] for c in mandatory_courses]
            
            # Retrieve optional course name
            if selected_course_id:
                cur.execute("SELECT name FROM course WHERE id = %s", (selected_course_id,))
                optional_result = cur.fetchone()
                if optional_result:
                    optional_course_name = optional_result[0]
            
            cur.close()
            conn.close()

        except Exception as e:
            print(f"DB ERROR in ActionSendEnrollmentEmail: {e}")
            # Continue with available data

        # Format mandatory courses list
        mandatory_str = "\n".join([f"  - {c}" for c in mandatory_courses_list]) if mandatory_courses_list else "  (No mandatory courses found)"

        # Build email body
        subject = f"Enrollment Confirmation: {degree_name}"
        mandatory_header = "MANDATORY COURSES"
        optional_header = "CHOSEN OPTIONAL COURSE"
        summary_header = "ENROLLMENT SUMMARY"
        field_label = "Field of Study"
        course_label = "Degree Course"
        type_label = "Type"
        
        body = (
            f"Hello {student_name},\n\n"
            f"We have successfully registered your interest for the following study program:\n\n"
            f"═══════════════════════════════════════\n"
            f"📌 {summary_header}\n"
            f"═══════════════════════════════════════\n\n"
            f"🎓 {field_label}: {degree_field}\n"
            f"📚 {course_label}: {degree_name} ({degree_id})\n"
            f"📋 {type_label}: {degree_type}\n\n"
            f"───────────────────────────────────────\n"
            f"{mandatory_header}:\n"
            f"───────────────────────────────────────\n"
            f"{mandatory_str}\n\n"
            f"───────────────────────────────────────\n"
            f"{optional_header}:\n"
            f"───────────────────────────────────────\n"
            f"  ⭐ {optional_course_name}\n\n"
            f"═══════════════════════════════════════\n\n"
            f"A counselor will contact you soon at this email address ({user_email}) to provide more details.\n\n"
            f"Best regards,\n"
            f"Your UnivPM Virtual Assistant"
        )

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = user_email 

        try:
            # SMTP Connection
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, msg.as_string())
            server.quit()
            
            print(f"DEBUG: Enrollment email sent to {user_email}")
            
            # User confirmation
            dispatcher.utter_message(text=f"Perfect {student_name}! 🎉 I've sent a summary email to {user_email} with all the details about '{degree_name}'.")
            
        except Exception as e:
            print(f"SMTP ENROLLMENT ERROR: {e}")
            msg = "I saved your data, but there was a technical error sending the confirmation email."
            dispatcher.utter_message(text=msg)
            return []
