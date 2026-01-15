# Ollama Windows Installer Script

Write-Host "Installing Ollama for Windows..." -ForegroundColor Cyan

# Download Ollama installer
$downloadUrl = "https://ollama.ai/download/OllamaSetup.exe"
$installerPath = "$env:TEMP\OllamaSetup.exe"

Write-Host "Downloading Ollama..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
    Write-Host "Download complete!" -ForegroundColor Green
} catch {
    Write-Host "Error downloading Ollama: $_" -ForegroundColor Red
    exit 1
}

# Run installer
Write-Host "Running installer..." -ForegroundColor Yellow
Start-Process -FilePath $installerPath -Wait

# Clean up
Remove-Item $installerPath -Force

Write-Host "`nOllama installation complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Close and reopen your terminal" -ForegroundColor White
Write-Host "2. Run: ollama serve" -ForegroundColor White
Write-Host "3. In another terminal run: ollama pull llama2" -ForegroundColor White
Write-Host "4. Then run: .\start.ps1" -ForegroundColor White