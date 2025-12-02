FROM python:3.10-slim

WORKDIR /app/actions

# Installazione dipendenze di sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia i requisiti
COPY requirements.txt .

# Installa l'SDK e le dipendenze Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir rasa-sdk
RUN pip install --no-cache-dir -r requirements.txt

# Installa browser per Crawl4AI (Playwright)
RUN playwright install --with-deps chromium

# Copia il codice
COPY . .

# CORREZIONE QUI: Usiamo python -m rasa_sdk invece di "run"
CMD ["python", "-m", "rasa_sdk", "--actions", "actions"]