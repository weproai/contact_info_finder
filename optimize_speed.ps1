# Speed optimization script

Write-Host "Optimizing for speed..." -ForegroundColor Cyan

# Option 1: Use tinydolphin (fastest, 636MB)
Write-Host "`nOption 1: Switch to tinydolphin (fastest model)" -ForegroundColor Yellow
Write-Host "Run: ollama pull tinydolphin" -ForegroundColor White
Write-Host "Then update .env: OLLAMA_MODEL=tinydolphin" -ForegroundColor White

# Option 2: Pre-load model in memory
Write-Host "`nOption 2: Keep model loaded in memory" -ForegroundColor Yellow
Write-Host "Run: ollama run gemma:2b" -ForegroundColor White
Write-Host "Keep this terminal open to keep model in memory" -ForegroundColor White

# Option 3: Use Ollama's embedding model for similarity only
Write-Host "`nOption 3: Use embeddings + caching (after first request)" -ForegroundColor Yellow
Write-Host "First request: 2-4 seconds" -ForegroundColor White
Write-Host "Cached requests: 50-200ms" -ForegroundColor White

Write-Host "`nRecommended: Option 2 + Option 3 for best performance" -ForegroundColor Green