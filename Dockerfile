# Dockerfile
FROM python:3.10-slim

# Installazione tool di base
RUN apt-get update && \
    apt-get install -y build-essential git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

# Installa Rasa
RUN pip install rasa==3.6.13

# Crea cartelle e permessi
RUN mkdir -p /app/models /app/data
USER root
EXPOSE 5005

# --- CORREZIONE QUI SOTTO ---
# Prima era: CMD ["run", ...] -> ERRORE
# Ora diciamo esplicitamente di lanciare "rasa"
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]