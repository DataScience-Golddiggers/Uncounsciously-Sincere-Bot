#!/bin/bash

# Funzione per controllare se un modello esiste
model_exists() {
    ollama list | grep -q "$1"
}

# Modello da scaricare
MODEL_NAME="qwen2.5:0.5b"

# Avvia il server Ollama in background per permettere l'uso di `ollama list`
ollama serve &
OLLAMA_PID=$!

# Attendi qualche secondo che il server si avvii a sufficienza
echo "Waiting for Ollama server to initialize..."
sleep 5

# Controlla se il modello esiste
if model_exists "$MODEL_NAME"; then
    echo "Model $MODEL_NAME already exists. Skipping pull."
else
    echo "Model $MODEL_NAME not found. Pulling..."
    ollama pull "$MODEL_NAME"
    if [ $? -ne 0 ]; then
        echo "Error pulling $MODEL_NAME. Container might not function correctly."
        # Potresti voler uscire qui o gestire l'errore in altro modo
    fi
fi

# Porta il server Ollama in primo piano come processo principale del container
# Prima, uccidi il processo ollama serve in background se è ancora in esecuzione
kill $OLLAMA_PID &> /dev/null

# Eseguilo in primo piano
exec ollama serve
