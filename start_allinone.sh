#!/bin/bash
# All-in-one startup script for App Runner

echo "=== Starting Contact Info Finder with Ollama ==="

# Function to check if Ollama is responding
check_ollama() {
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1
    return $?
}

# Start Ollama in background
echo "Starting Ollama service..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in {1..30}; do
    if check_ollama; then
        echo "Ollama is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Check if Ollama started successfully
if ! check_ollama; then
    echo "ERROR: Ollama failed to start!"
    echo "Ollama logs:"
    cat /tmp/ollama.log
    exit 1
fi

# Check if model exists, pull if not
echo "Checking for gemma:2b model..."
if ! ollama list | grep -q "gemma:2b"; then
    echo "Pulling gemma:2b model (this may take a few minutes)..."
    ollama pull gemma:2b || {
        echo "WARNING: Failed to pull gemma:2b, trying tinyllama as fallback..."
        ollama pull tinyllama
        export OLLAMA_MODEL=tinyllama
    }
else
    echo "Model gemma:2b already available!"
fi

# Update environment variable if needed
if [ -n "$OLLAMA_MODEL" ]; then
    echo "Using model: $OLLAMA_MODEL"
fi

# Start the API server
echo "Starting API server..."
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000