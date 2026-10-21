# ==============================================================================
# EvidenceBridge - Ollama Setup Script (PowerShell for Windows)
# ==============================================================================

param (
    [string]$Model = "phi3:mini",
    [string]$HostUrl = "http://localhost:11434"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " EvidenceBridge - Local LLM Setup (Windows / Ollama)" -ForegroundColor Cyan
Write-Host " Target Model: $Model" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if Ollama CLI is installed
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Ollama command not found in PATH." -ForegroundColor Yellow
    Write-Host "    Please download and run the installer from:"
    Write-Host "    https://ollama.com/download/OllamaSetup.exe" -ForegroundColor Green
    Write-Host "    After installing, restart your terminal and re-run this script."
    exit 1
}

Write-Host "[✓] Ollama CLI detected." -ForegroundColor Green

# 2. Check if Ollama is running
try {
    $response = Invoke-RestMethod -Uri "$HostUrl/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[✓] Ollama server is online and responding at $HostUrl." -ForegroundColor Green
} catch {
    Write-Host "[!] Ollama server is not responding at $HostUrl." -ForegroundColor Yellow
    Write-Host "    Starting 'ollama serve' in background..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# 3. Pull required model
Write-Host "[*] Pulling model '$Model' (this may take a few minutes on first run)..." -ForegroundColor Cyan
ollama pull $Model

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[✓] Model '$Model' is ready for EvidenceBridge." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
