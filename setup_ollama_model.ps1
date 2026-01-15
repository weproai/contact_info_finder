# Setup Ollama Model Script

Write-Host "Checking Ollama models..." -ForegroundColor Cyan

# Check if Ollama is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get
    $models = $response.models
    
    if ($models.Count -eq 0) {
        Write-Host "No models installed. Installing mistral (fast and good for structured output)..." -ForegroundColor Yellow
        & ollama pull mistral
        
        Write-Host "`nUpdating .env to use mistral..." -ForegroundColor Yellow
        if (Test-Path ".\.env") {
            (Get-Content .\.env) -replace 'OLLAMA_MODEL=.*', 'OLLAMA_MODEL=mistral' | Set-Content .\.env
        }
        
        Write-Host "Model installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Found installed models:" -ForegroundColor Green
        foreach ($model in $models) {
            Write-Host "  - $($model.name)" -ForegroundColor White
        }
        
        $firstModel = $models[0].name
        Write-Host "`nUsing model: $firstModel" -ForegroundColor Cyan
        
        # Update .env to use the first available model
        if (Test-Path ".\.env") {
            (Get-Content .\.env) -replace 'OLLAMA_MODEL=.*', "OLLAMA_MODEL=$firstModel" | Set-Content .\.env
        }
    }
} catch {
    Write-Host "Error: Ollama is not running. Please start it with 'ollama serve'" -ForegroundColor Red
    exit 1
}

Write-Host "`nSetup complete! Restart your API server to use the model." -ForegroundColor Green