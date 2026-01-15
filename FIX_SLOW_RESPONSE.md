# Fix 38-Second Response Time

## Problem Analysis

Your response shows:
- **Waiting (TTFB): 38.25s** ❌ This is the problem!
- Download: 3.14ms ✅
- Processing: 0.47ms ✅

This means the server is taking 38 seconds to START responding, likely because:
1. Ollama is loading the model on first request
2. Server is low on memory
3. Model is too large for the instance

## Immediate Fixes

### 1. SSH into your EC2
```bash
ssh -i your-key.pem ubuntu@54.82.217.195
```

### 2. Check What's Happening
```bash
# Check memory usage
free -h

# Check if Ollama is using CPU
top

# Check Ollama logs during request
sudo journalctl -u ollama -f
```

### 3. Quick Fix - Preload the Model

```bash
# Force load the model
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma:2b",
    "prompt": "test",
    "stream": false
  }'

# This will load the model into memory
```

### 4. Permanent Fix - Keep Model Loaded

Create a keep-alive script:

```bash
cat > /home/ubuntu/keep_model_warm.sh << 'EOF'
#!/bin/bash
# Keep Ollama model warm

while true; do
    # Send a quick request every 5 minutes
    curl -s -X POST http://localhost:11434/api/generate \
        -H "Content-Type: application/json" \
        -d '{
            "model": "gemma:2b",
            "prompt": "1",
            "stream": false
        }' > /dev/null
    
    sleep 300  # 5 minutes
done
EOF

chmod +x /home/ubuntu/keep_model_warm.sh

# Run in background
nohup /home/ubuntu/keep_model_warm.sh > /dev/null 2>&1 &
```

### 5. Use a Smaller Model (Fastest Fix)

```bash
# Switch to tinyllama (much smaller and faster)
ollama pull tinyllama

# Update your .env
cd /home/ubuntu/contact_info_finder
sed -i 's/OLLAMA_MODEL=gemma:2b/OLLAMA_MODEL=tinyllama/' .env

# Restart API
sudo supervisorctl restart contact_api

# Test again - should be < 1 second
```

### 6. Add More Memory (If Needed)

```bash
# Check current memory
free -h

# If less than 4GB available, add swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Performance Optimization Script

Run this complete optimization:

```bash
cat > /home/ubuntu/optimize_performance.sh << 'EOF'
#!/bin/bash

echo "=== Optimizing Contact Info Finder Performance ==="

# 1. Ensure swap is enabled
if ! swapon --show | grep -q swapfile; then
    echo "Adding 4GB swap..."
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
fi

# 2. Preload model
echo "Preloading model..."
curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model": "gemma:2b", "prompt": "test", "stream": false}' > /dev/null

echo "Model preloaded!"

# 3. Optimize Ollama settings
echo "Optimizing Ollama..."
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1

# 4. Restart services with optimizations
sudo systemctl restart ollama
sleep 10
sudo supervisorctl restart contact_api

# 5. Test performance
echo -e "\n=== Testing Performance ==="
time curl -X POST http://localhost/extract \
    -H "Content-Type: application/json" \
    -d '{"text": "Call 555-1234"}'

echo -e "\n✅ Optimization complete!"
EOF

chmod +x /home/ubuntu/optimize_performance.sh
./optimize_performance.sh
```

## Expected Performance After Fixes

With these optimizations:
- **First request**: 2-5 seconds (model loading)
- **Subsequent requests**: 200-500ms
- **With caching**: 50-100ms
- **Fast mode (regex)**: 10-50ms

## Monitor Performance

```bash
# Create performance monitor
cat > /home/ubuntu/monitor_performance.sh << 'EOF'
#!/bin/bash

echo "Testing API performance..."

for i in {1..5}; do
    echo -n "Request $i: "
    time curl -s -X POST http://localhost/extract \
        -H "Content-Type: application/json" \
        -d '{"text": "Test 555-1234"}' > /dev/null
done
EOF

chmod +x monitor_performance.sh
./monitor_performance.sh
```

## Alternative: Use Fast Mode for Simple Extractions

Your request would work perfectly with fast mode (regex-based):

```bash
# Ensure fast mode is enabled
grep ENABLE_FAST_MODE /home/ubuntu/contact_info_finder/.env
# Should show: ENABLE_FAST_MODE=true
```

With fast mode, simple extractions like phone/email will use regex first, bypassing Ollama entirely for ~10ms response times.

## If Still Slow - Emergency Switch

```bash
# Use the fastest possible model
ollama pull qwen:0.5b  # Only 394MB!

# Update config
sed -i 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen:0.5b/' /home/ubuntu/contact_info_finder/.env
sudo supervisorctl restart contact_api
```

Try these fixes and your response time should drop from 38 seconds to under 1 second!