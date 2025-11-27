# Uncounsciously Sincere Bot

Questo repository contiene il codice sorgente per il Chatbot Rasa "Unconsciously Sincere Bot".
Il progetto è configurato per essere eseguito interamente su **Docker**, ottimizzato per architetture **Apple Silicon (M1/M2/M3/M4)** e compatibile con **Windows/Linux**.

L'architettura include:
*   **Rasa Core/NLU**: Container principale (basato su Python 3.10).
*   **Ngrok**: Tunneling automatico per esporre il bot a Telegram.

---

## 📋 Prerequisiti

Assicurati di avere installato:
1.  **Docker Desktop** (con Docker Compose).
2.  Un account **Telegram** e un Bot creato via BotFather.
3.  Un account **Ngrok** (gratuito) per il tunneling.

---

## ⚙️ Configurazione Iniziale

Prima di avviare, devi configurare i token segreti.

### 1. Configura Ngrok
Apri il file `docker-compose.yml` e inserisci il tuo Authtoken di Ngrok (ottienilo da [dashboard.ngrok.com](https://dashboard.ngrok.com)):

```yaml
environment:
  NGROK_AUTHTOKEN: "INCOLLA_QUI_IL_TUO_TOKEN_NGROK"
```

### 2. Configura Telegram
Apri il file credentials.yml e inserisci i dati del tuo bot Telegram:


```yaml
telegram:
  access_token: "123456:ABC-DEF..."  # Token dato da BotFather
  verify: "tuo_bot_username"
  webhook_url: "https://....ngrok-free.app/webhooks/telegram/webhook" # Lascia temporaneamente vuoto, lo aggiorneremo dopo l'avvio.
```

## 🚀 Avvio del Bot
Per avviare l'intera infrastruttura (Rasa + Ngrok):

```bash
docker-compose up --build
```

Attendi qualche minuto la prima volta per la compilazione dell'immagine Docker.

**Collegamento a Telegram (Primo Avvio)**
Poiché l'URL di Ngrok cambia ad ogni avvio (nella versione free), devi aggiornarlo:

Con Docker in esecuzione, apri il browser su: http://localhost:4040.
Copia l'URL HTTPS generato (es. https://a1b2-c3d4.ngrok-free.app).
Incolla l'URL in credentials.yml aggiungendo il suffisso obbligatorio:

```yaml
webhook_url: "https://tuo-url-copiato.ngrok-free.app/webhooks/telegram/webhook"
```

Riavvia il container Rasa per applicare la modifica:

```bash
docker-compose restart rasa
```

Ora il bot risponderà su Telegram!

## 🧠 Come Addestrare il Modello (Training)
Ogni volta che modifichi i file nella cartella data/ (es. nlu.yml, stories.yml, rules.yml), devi riaddestrare il modello.

Non serve fermare Docker. Esegui questo comando in un nuovo terminale:

```yaml
docker exec -it rasa_server rasa train
```

Il nuovo modello verrà salvato automaticamente nella cartella models/ locale e caricato dal server appena pronto.

## 🛠 Comandi Utili
Azione	Comando
Avviare tutto	*docker-compose up*
Avviare e ricostruire	*docker-compose up --build*
Fermare tutto	*docker-compose down*
Addestrare modello	*docker exec -it rasa_server rasa train*
Shell nel container	*docker exec -it rasa_server /bin/bash*
Vedere i log	*docker-compose logs -f*

## 📂 Struttura Cartelle
 
 - data/: Contiene i dati di training (NLU, Stories, Rules).
 
 - models/: Qui vengono salvati i modelli .tar.gz dopo il training.
 
 - config.yml: Configurazione della pipeline NLU.
 
 - domain.yml: Definisce intent, entità, slot e risposte del bot.
 
 - credentials.yml: Token per Telegram e altri canali.