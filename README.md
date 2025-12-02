# Uncounsciously Sincere Bot

<div style="height; overflow:hidden; margin:auto; margin-bottom:2rem" align="center">
  <img src="./docs/images/rdm.png" style="width:70%; height:50%; object-fit:cover; object-position:center;" />
</div>

[![Python](https://img.shields.io/badge/Python-3.10-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
![Keras](https://img.shields.io/badge/Keras-D00000?style=for-the-badge&logo=Keras&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![NGROK](https://img.shields.io/badge/ngrok-140648?style=for-the-badge&logo=Ngrok&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Pycharm](https://img.shields.io/badge/PyCharm-000000.svg?&style=for-the-badge&logo=PyCharm&logoColor=white)
![VisualStudioCode](https://img.shields.io/badge/Visual_Studio_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white)
![Overleaf](https://img.shields.io/badge/Overleaf-47A141?style=for-the-badge&logo=Overleaf&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white)
![ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
[![License](https://img.shields.io/badge/MIT-green?style=for-the-badge)](LICENSE)


Questo repository contiene il codice sorgente per il Chatbot Rasa "Unconsciously Sincere Bot".
Il progetto è configurato per essere eseguito interamente su **Docker**, ottimizzato per architetture **Apple Silicon (M1/M2/M3/M4)** e compatibile con **Windows/Linux**.

L'architettura include:
*   **Rasa Core/NLU**: Container principale (basato su Python 3.10).
*   **Rasa Action**: Container per le action del chatbot, usato per il servizio di emailing.
*   **Ngrok**: Tunneling automatico per esporre il bot a Telegram.

---

## 📋 Prerequisiti

Assicurati di avere installato:
1.  **Docker Desktop** (con Docker Compose).
2.  Un account **Telegram** e un Bot creato via BotFather.
3.  Un account **Gmail** e appcode per accedere all'API.
4.  Un account **Ngrok** (gratuito) per il tunneling.

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

### 3. Configura Gmail
Crea il tuo file .env sulla base dell'esempio nella repo e compila i campi con quanto richiesto. 
Si ricorda che la AppCode di google si genera direttamente dalle preferenze dell'account in Gmail.


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

**Attenzione:** si vuole precisare che i dati attuali sono stati creati "manualmente" e non presi da Dataset già pronti; per questo motivo il chatbot potrebbe risultare impreciso, ma siamo certi che costituisca un ottima base di partenza per sviluppi futuri!

## 🛠 Comandi Utili
Azione	Comando
Avviare tutto	*docker-compose up*
Avviare e ricostruire	*docker-compose up --build*
Fermare tutto	*docker-compose down*
Addestrare modello	*docker exec -it rasa_server rasa train*
Shell nel container	*docker exec -it rasa_server /bin/bash*
Vedere i log	*docker-compose logs -f*

Avvia Ollama: 
```bash
export OLLAMA_HOST=0.0.0.0 
export OLLAMA_ORIGINS="*" 
export OLLAMA_MODELS=$(pwd)/ollama_data
ollama serve
```

## 📂 Struttura Cartelle
 
 - data/: Contiene i dati di training (NLU, Stories, Rules).
 
 - models/: Qui vengono salvati i modelli .tar.gz dopo il training.
 
 - config.yml: Configurazione della pipeline NLU.
 
 - domain.yml: Definisce intent, entità, slot e risposte del bot.
 
 - credentials.yml: Token per Telegram e altri canali.
