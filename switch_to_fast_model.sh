#!/bin/bash
# Switch to a faster Ollama model for 2-3 second response times

echo "=== Switching to Faster Ollama Model ==="

# Pull the fastest model - qwen:0.5b (only 394MB)
echo "Pulling qwen:0.5b (fastest model)..."
ollama pull qwen:0.5b

# Update .env to use the faster model
echo "Updating configuration..."
sed -i 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen:0.5b/' .env

# Preload the model
echo "Preloading model..."
curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen:0.5b", "prompt": "test", "stream": false}' > /dev/null

echo "Model switched to qwen:0.5b"

# Test direct Ollama speed
echo -e "\nTesting Ollama speed..."
time curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen:0.5b",
    "prompt": "Extract: Customer: DAVID Phone: +12397938642 Address: 2735 Lakeview Dr Naples FL 34112",
    "stream": false,
    "options": {"temperature": 0, "num_predict": 100}
  }' > /dev/null

echo -e "\nDone! Restart API to use the new model:"
echo "sudo supervisorctl restart contact_api"