# Check if virtual environment exists, create if needed, install dependencies, and start server

# Check if venv exists
if (-Not (Test-Path ".\venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# Check if requirements are installed by checking if uvicorn exists
$uvicornPath = ".\venv\Scripts\uvicorn.exe"
if (-Not (Test-Path $uvicornPath)) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Check if .env file exists, create from example if not
if (-Not (Test-Path ".\.env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:2b

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=contact_extractions

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Logging
LOG_LEVEL=INFO

# Performance Settings
ENABLE_FAST_MODE=false
CACHE_SIMILARITY_THRESHOLD=0.1
"@ | Out-File -FilePath ".\.env" -Encoding UTF8
}

# Create chroma_db directory if it doesn't exist
if (-Not (Test-Path ".\chroma_db")) {
    Write-Host "Creating chroma_db directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path ".\chroma_db" | Out-Null
}

# Set Python cache directory inside venv
$env:PYTHONPYCACHEPREFIX = ".\venv\.pycache"

# Create cache directory if it doesn't exist
if (-Not (Test-Path ".\venv\.pycache")) {
    New-Item -ItemType Directory -Path ".\venv\.pycache" | Out-Null
}

# Start the server
Write-Host "Starting Contact Info Finder API..." -ForegroundColor Cyan
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Green
Write-Host "Interactive docs at: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "" # Empty line for clarity

uvicorn main:app --reload