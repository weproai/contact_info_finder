# Troubleshooting Stuck API on EC2

## 1. Check All Logs

SSH into your EC2 instance first:
```bash
ssh -i your-key.pem ubuntu@54.82.217.195
```

### API Logs
```bash
# View recent API logs
sudo tail -n 50 /var/log/contact_api.log

# Follow API logs in real-time
sudo tail -f /var/log/contact_api.log

# Search for errors
sudo grep -i error /var/log/contact_api.log
```

### Ollama Logs
```bash
# Check Ollama service logs
sudo journalctl -u ollama -n 50

# Follow Ollama logs
sudo journalctl -u ollama -f

# Check if Ollama is running
sudo systemctl status ollama
```

### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

## 2. Quick Diagnostics Script

Create and run this diagnostic script:

```bash
cat > diagnose.sh << 'EOF'
#!/bin/bash
echo "=== API Diagnostics ==="

# Check services
echo -e "\n📊 Service Status:"
sudo systemctl is-active ollama && echo "✅ Ollama: Active" || echo "❌ Ollama: Inactive"
sudo supervisorctl status contact_api | grep RUNNING && echo "✅ API: Running" || echo "❌ API: Not Running"
sudo systemctl is-active nginx && echo "✅ Nginx: Active" || echo "❌ Nginx: Inactive"

# Check Ollama
echo -e "\n🤖 Ollama Check:"
curl -s http://localhost:11434/api/tags > /dev/null 2>&1 && echo "✅ Ollama responding" || echo "❌ Ollama not responding"

# Check if model exists
echo -e "\n📦 Models:"
ollama list

# Check API directly
echo -e "\n🔌 API Direct Check:"
curl -s http://localhost:8000/health | jq . || echo "❌ API not responding on port 8000"

# Check system resources
echo -e "\n💾 System Resources:"
echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2 " used"}')"
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " used (" $5 ")"}')"

# Check for port conflicts
echo -e "\n🔍 Port Usage:"
sudo netstat -tlnp | grep -E ':(8000|11434|80)\s'

# Recent errors
echo -e "\n❗ Recent Errors:"
echo "API Errors:"
sudo tail -5 /var/log/contact_api.log | grep -i error || echo "No recent errors"
echo -e "\nOllama Errors:"
sudo journalctl -u ollama -n 5 | grep -i error || echo "No recent errors"
EOF

chmod +x diagnose.sh
./diagnose.sh
```

## 3. Common Issues and Fixes

### Issue: Ollama Not Responding
```bash
# Restart Ollama
sudo systemctl restart ollama

# Wait 10 seconds, then check
sleep 10
curl http://localhost:11434/api/tags
```

### Issue: Model Not Loaded
```bash
# Pull the model again
ollama pull gemma:2b

# List models to verify
ollama list
```

### Issue: API Not Running
```bash
# Restart the API
sudo supervisorctl restart contact_api

# Check if it started
sudo supervisorctl status contact_api

# View startup errors
sudo tail -50 /var/log/contact_api.log
```

### Issue: Out of Memory
```bash
# Check memory
free -h

# If low memory, create swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 4. Test Each Component Separately

### Test Ollama Directly
```bash
# Test Ollama API
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma:2b",
    "prompt": "Hello",
    "stream": false
  }'
```

### Test API Directly (bypass Nginx)
```bash
# Health check
curl http://localhost:8000/health

# Simple extraction
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Call 555-1234"}'
```

## 5. Emergency Restart Everything

```bash
# Full restart script
cat > restart_all.sh << 'EOF'
#!/bin/bash
echo "Restarting all services..."

# Restart Ollama
sudo systemctl restart ollama
echo "Waiting for Ollama to start..."
sleep 15

# Verify Ollama
curl -s http://localhost:11434/api/tags > /dev/null 2>&1 && echo "✅ Ollama started" || echo "❌ Ollama failed"

# Restart API
sudo supervisorctl restart contact_api
sleep 5

# Restart Nginx
sudo systemctl restart nginx

echo "All services restarted. Testing..."
sleep 5

# Test
curl -s http://localhost/health | jq .
EOF

chmod +x restart_all.sh
./restart_all.sh
```

## 6. Watch Logs While Testing

Open multiple SSH sessions:

**Session 1 - API Logs:**
```bash
sudo tail -f /var/log/contact_api.log
```

**Session 2 - Ollama Logs:**
```bash
sudo journalctl -u ollama -f
```

**Session 3 - Run your curl command:**
```bash
curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact John Smith at 555-123-4567"}'
```

## 7. Check Python Dependencies

```bash
# Activate virtual environment
cd /home/ubuntu/contact_info_finder
source venv/bin/activate

# Check if all packages are installed
pip list | grep -E "fastapi|uvicorn|ollama|chromadb"

# Reinstall if needed
pip install -r requirements.txt
```

## 8. Enable Debug Logging

```bash
# Edit .env file
nano /home/ubuntu/contact_info_finder/.env

# Change LOG_LEVEL to DEBUG
LOG_LEVEL=DEBUG

# Restart API
sudo supervisorctl restart contact_api
```

## Most Common Cause: Ollama Model Loading

If gemma:2b is taking too long to load:

```bash
# Try a smaller model temporarily
ollama pull tinyllama

# Update .env
sed -i 's/OLLAMA_MODEL=gemma:2b/OLLAMA_MODEL=tinyllama/' /home/ubuntu/contact_info_finder/.env

# Restart
sudo supervisorctl restart contact_api
```

Let me know what the logs show!