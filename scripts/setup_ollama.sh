#!/usr/bin/env bash
# ==============================================================================
# EvidenceBridge - Ollama Setup Script
# Verifies Ollama installation, starts service, and pulls default model
# ==============================================================================

set -e

DEFAULT_MODEL="${OLLAMA_MODEL:-phi3:mini}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

echo "=========================================================="
echo " EvidenceBridge - Local LLM Setup (Ollama)"
echo " Target Model: ${DEFAULT_MODEL}"
echo "=========================================================="

# 1. Check if Ollama CLI is installed
if ! command -v ollama &> /dev/null; then
    echo "[!] Ollama command not found in PATH."
    echo "    Please install Ollama for your operating system:"
    echo "    - macOS:   brew install ollama  OR download from https://ollama.com/download"
    echo "    - Linux:   curl -fsSL https://ollama.com/install.sh | sh"
    echo "    - Windows: Download installer from https://ollama.com/download"
    exit 1
fi

echo "[✓] Ollama CLI detected: $(ollama --version)"

# 2. Check if Ollama daemon is running
echo "[*] Checking if Ollama server is responding at ${OLLAMA_HOST}..."
if ! curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    echo "[!] Ollama server is not running."
    echo "[*] Attempting to start 'ollama serve' in background..."
    ollama serve &
    sleep 4

    if ! curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
        echo "[✗] Could not connect to Ollama server. Please run 'ollama serve' in a separate terminal."
        exit 1
    fi
fi

echo "[✓] Ollama server is online and responding."

# 3. Pull required local model
echo "[*] Pulling model '${DEFAULT_MODEL}' (this may take a few minutes on first run)..."
ollama pull "${DEFAULT_MODEL}"

echo "=========================================================="
echo "[✓] Successfully configured model: ${DEFAULT_MODEL}"
echo "    Available models in local Ollama instance:"
ollama list
echo "=========================================================="
echo "You can now run EvidenceBridge backend:"
echo "    cd backend"
echo "    uvicorn app.main:app --reload"
echo "=========================================================="
