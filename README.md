# Unconsciously Sincere Bot

<div style="height; overflow:hidden; margin:auto; margin-bottom:2rem" align="center">
  <img src="./docs/images/rdm.png" style="width:70%; height:50%; object-fit:cover; object-position:center;" />
</div>

[![Python](https://img.shields.io/badge/Python-3.10-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
![Keras](https://img.shields.io/badge/Keras-D00000?style=for-the-badge&logo=Keras&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![NGROK](https://img.shields.io/badge/ngrok-140648?style=for-the-badge&logo=Ngrok&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-FFFFFF?style=for-the-badge&logo=ollama&logoColor=black)
![Qwen](https://img.shields.io/badge/Qwen-2.5-blue?style=for-the-badge)
![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white)
[![License](https://img.shields.io/badge/MIT-green?style=for-the-badge)](LICENSE)

Questo repository contiene il codice sorgente per il Chatbot Rasa "Unconsciously Sincere Bot".
Il progetto è configurato per essere eseguito su **Docker** ed è fortemente ottimizzato per architetture **Apple Silicon (M1/M2/M3/M4)**, ma compatibile con Windows e Linux.

L'architettura è **Ibrida (NLU + LLM)** e include:
*   **Rasa Core/NLU**: Gestione del dialogo e intenti strutturati.
*   **Ollama + Qwen 2.5**: Integrazione con LLM locale per capacità di RAG (Retrieval Augmented Generation), ricerca web e risposte generative avanzate.
*   **Rasa Action**: Container per le custom actions (Emailing, Web Search).
*   **Ngrok**: Tunneling automatico per esporre il bot a Telegram.

---

## 💻 Requisiti Hardware

L'utilizzo di **Qwen 2.5** tramite Ollama richiede risorse hardware adeguate per garantire tempi di risposta accettabili.

| Componente | Requisiti Minimi | Requisiti Consigliati |
| :--- | :--- | :--- |
| **CPU** | 4 Core (Intel/AMD) | **Apple Silicon (M-Series)** >8 Core |
| **RAM** | 8 GB (potrebbe rallentare) | **16 GB** o superiore |
| **GPU** | Integrata | **NVIDIA RTX** (6GB+ VRAM) o Apple Neural Engine |
| **Spazio Disco** | 15 GB (Docker + Modelli LLM) | 30 GB SSD |

> **Nota per utenti Mac:** Grazie all'ottimizzazione `metal` di Ollama, i chip Apple Silicon offrono prestazioni eccellenti. È raccomandato utilizzare il container `rasa_ollama` per una configurazione più semplice e integrata.

**Local Ollama per supporto MPS/MLX:** 
```bash
export OLLAMA_HOST=0.0.0.0
export OLLAMA_ORIGINS="*"
export OLLAMA_MODELS=$(pwd)/ollama_data
ollama serve
```     

---

## 📋 Prerequisiti Software

Assicurati di avere installato:
1.  **Docker Desktop** (con Docker Compose).
2.  Un account **Telegram** e un Bot creato via BotFather.
3.  Un account **Gmail** e App Password per le email.
4.  Un account **Ngrok** (gratuito).

---

## ⚙️ Configurazione Iniziale

### 1. Configura Ollama e scarica il modello Qwen 2.5
Con la configurazione Docker fornita, Ollama verrà eseguito in un proprio container. Non è necessario installare o avviare Ollama manualmente sul tuo sistema operativo.

Dopo aver avviato i servizi Docker (vedi sezione "Avvio del Bot"), scarica il modello Qwen 2.5 direttamente nel container Ollama:
```bash
docker exec -it rasa_ollama ollama pull qwen2.5
```
*(Puoi usare versioni specifiche come `qwen2.5:7b` o `qwen2.5:14b` a seconda della tua RAM/VRAM. Il modello base è generalmente `qwen2.5` senza tag specifici.)*

### 2. Configura Ngrok
Apri `docker-compose.yml` e inserisci il tuo Authtoken (da [dashboard.ngrok.com](https://dashboard.ngrok.com)):
```yaml
environment:
  NGROK_AUTHTOKEN: "INCOLLA_QUI_IL_TUO_TOKEN_NGROK"
```

### 3. Configura Telegram
Apri `credentials.yml` e inserisci i dati del bot Telegram:
```yaml
telegram:
  access_token: "123456:ABC-DEF..."
  verify: "tuo_bot_username"
  webhook_url: "https://....ngrok-free.app/webhooks/telegram/webhook" # Aggiornare post-avvio
```

### 4. Configura Variabili d'Ambiente
Crea un file `.env` nella root del progetto con le seguenti variabili (vedi `.env.example`):
```ini
EMAIL_USER=tua_email@gmail.com
EMAIL_PASSWORD=tua_app_password
OLLAMA_URL=http://ollama:11434 # URL per raggiungere il servizio Ollama nel network Docker
```

---

## 🚀 Avvio del Bot

Per avviare l'intera infrastruttura (inclusi Rasa, Ollama e Ngrok):

```bash
docker-compose up --build
```

### Collegamento a Telegram (Primo Avvio)
1.  Apri il browser su: `http://localhost:4040` (Dashboard Ngrok).
2.  Copia l'URL HTTPS (es. `https://a1b2.ngrok-free.app`).
3.  Incolla l'URL in `credentials.yml`:
    ```yaml
    webhook_url: "https://tuo-url.ngrok-free.app/webhooks/telegram/webhook"
    ```
4.  Riavvia Rasa:
    ```bash
    docker-compose restart rasa
    ```

---

## 🧠 Training e Sviluppo

### Addestramento Modello Rasa
Se modifichi i file `data/` (NLU, Stories, Rules), riaddestra il modello:
```bash
docker exec -it rasa_server rasa train
```

### Custom Actions & Ollama
Le azioni personalizzate in `actions/` utilizzano Ollama per:
*   Rispondere a domande complesse non previste dalle regole fisse.
*   Effettuare ricerche web simulate o retrieval di informazioni universitarie.

Se il bot risponde "Non so aiutarti", assicurati che il container `action_server` riesca a comunicare con Ollama tramite l'URL configurato in `.env`.

---

## 🛠 Comandi Utili

| Azione | Comando |
| :--- | :--- |
| **Avviare tutto** | `docker-compose up` |
| **Ricostruire immagini** | `docker-compose up --build` |
| **Fermare tutto** | `docker-compose down` |
| **Addestrare Rasa** | `docker exec -it rasa_server rasa train` |
| **Shell Container** | `docker exec -it rasa_server /bin/bash` |
| **Log in tempo reale** | `docker-compose logs -f` |
| **Pull modello Qwen** | `docker exec -it rasa_ollama ollama pull qwen2.5` |

---

## 📂 Struttura Cartelle
*   `data/`: Dataset di training (NLU, Stories, Rules).
*   `actions/`: Codice Python per le azioni custom (inclusa integrazione Ollama).
*   `models/`: Modelli addestrati (.tar.gz).
*   `config.yml`: Pipeline NLU e Policy.
*   `domain.yml`: Definizione intent, entità, slot e risposte.