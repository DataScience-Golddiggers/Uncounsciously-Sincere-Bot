FROM python:3.10-slim

WORKDIR /app/actions

# Copia i requisiti
COPY requirements.txt .

# Installa l'SDK e le dipendenze
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir rasa-sdk
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice
COPY . .

# CORREZIONE QUI: Usiamo python -m rasa_sdk invece di "run"
CMD ["python", "-m", "rasa_sdk", "--actions", "actions"]