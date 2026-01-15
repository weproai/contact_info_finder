#!/bin/bash
# Optimize Ollama for EC2 performance

echo "=== Optimizing Ollama for Fast Extraction ==="

# 1. Try phi model (better balance of speed/accuracy)
echo "Pulling phi model..."
ollama pull phi

# 2. Update to use phi
sed -i 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=phi/' .env

# 3. Test different models for speed
echo -e "\nTesting model speeds..."

TEST_TEXT="Extract: Customer: DAVID WOODWORTH Phone: +12397938642 Address: 2735 Lakeview Dr Naples FL 34112"

# Test phi
echo -e "\n--- Testing phi ---"
time curl -s -X POST http://localhost:11434/api/generate \
  -d "{\"model\": \"phi\", \"prompt\": \"$TEST_TEXT\", \"stream\": false, \"options\": {\"temperature\": 0, \"num_predict\": 100}}" | jq -r .response | head -5

# Test tinyllama  
echo -e "\n--- Testing tinyllama ---"
ollama pull tinyllama > /dev/null 2>&1
time curl -s -X POST http://localhost:11434/api/generate \
  -d "{\"model\": \"tinyllama\", \"prompt\": \"$TEST_TEXT\", \"stream\": false, \"options\": {\"temperature\": 0, \"num_predict\": 100}}" | jq -r .response | head -5

# 4. Keep model warm
echo -e "\nStarting model warmer..."
(while true; do 
    curl -s http://localhost:11434/api/generate \
      -d '{"model": "phi", "prompt": "1", "stream": false}' > /dev/null
    sleep 300
done) &

echo -e "\nRestart API with: sudo supervisorctl restart contact_api"