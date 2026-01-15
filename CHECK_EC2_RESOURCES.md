# Check EC2 Resources for Gemma:2b

Since gemma:2b works fine locally but takes 38 seconds on EC2, the issue is likely:
1. **Insufficient RAM** - EC2 instance too small
2. **No swap space** - Model being loaded from disk each time
3. **CPU throttling** - Instance type limitations

## 1. Check Current EC2 Resources

```bash
# SSH into your EC2
ssh -i your-key.pem ubuntu@54.82.217.195

# Check instance type and resources
echo "=== System Information ==="
echo "Instance Type: $(ec2-metadata --instance-type | cut -d' ' -f2)"
echo "CPU: $(nproc) cores"
echo "RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Available RAM: $(free -h | awk '/^Mem:/ {print $7}')"
echo "Swap: $(free -h | awk '/^Swap:/ {print $2}')"

# Check memory during model load
echo -e "\n=== Memory Usage ==="
free -h

# Check if model is loaded
echo -e "\n=== Ollama Models ==="
ollama list

# Check disk space
echo -e "\n=== Disk Space ==="
df -h
```

## 2. Quick Resource Check Script

```bash
cat > check_resources.sh << 'EOF'
#!/bin/bash

echo "=== EC2 Resource Check for Gemma:2b ==="

# Function to convert memory to MB
to_mb() {
    echo $1 | awk '/[0-9.]+G/ {print int($1 * 1024)} /[0-9.]+M/ {print int($1)}'
}

# Get total RAM in MB
total_ram=$(free -m | awk '/^Mem:/ {print $2}')
available_ram=$(free -m | awk '/^Mem:/ {print $7}')

echo "Total RAM: ${total_ram}MB"
echo "Available RAM: ${available_ram}MB"

# Gemma:2b requirements
echo -e "\n📊 Gemma:2b Requirements:"
echo "- Model size: ~1.4GB"
echo "- RAM needed: ~4-6GB (model + overhead)"
echo "- Your available: ${available_ram}MB"

if [ $available_ram -lt 4000 ]; then
    echo -e "\n❌ INSUFFICIENT RAM! Need at least 4GB available"
    echo "Current instance may be too small for gemma:2b"
else
    echo -e "\n✅ Sufficient RAM available"
fi

# Check swap
swap_total=$(free -m | awk '/^Swap:/ {print $2}')
if [ $swap_total -eq 0 ]; then
    echo -e "\n⚠️  No swap space configured"
    echo "This causes model to reload from disk each time!"
fi

# Test model loading time
echo -e "\n⏱️  Testing model load time..."
start_time=$(date +%s)
curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model": "gemma:2b", "prompt": "test", "stream": false}' > /dev/null
end_time=$(date +%s)
load_time=$((end_time - start_time))

echo "Model load time: ${load_time} seconds"

if [ $load_time -gt 10 ]; then
    echo "❌ Model loading is too slow!"
else
    echo "✅ Model loaded successfully"
fi
EOF

chmod +x check_resources.sh
./check_resources.sh
```

## 3. Fix Based on Your Instance Type

### If you have t3.medium (2 vCPU, 4GB RAM):
```bash
# MUST add swap for gemma:2b
sudo fallocate -l 6G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Optimize memory usage
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

### If you have t3.small or smaller:
```bash
# Instance too small for gemma:2b!
# Must use smaller model
ollama pull qwen:0.5b  # Only 394MB
# OR
ollama pull tinyllama  # 637MB

# Update config
sed -i 's/OLLAMA_MODEL=gemma:2b/OLLAMA_MODEL=qwen:0.5b/' /home/ubuntu/contact_info_finder/.env
sudo supervisorctl restart contact_api
```

## 4. Recommended Fix: Upgrade Instance

If you want to keep using gemma:2b with good performance:

### Option A: Resize Current Instance
```bash
# From AWS Console or CLI
aws ec2 stop-instances --instance-ids i-xxxxx
aws ec2 modify-instance-attribute --instance-id i-xxxxx --instance-type t3.large
aws ec2 start-instances --instance-ids i-xxxxx
```

### Option B: Use Appropriate Model for Instance

| Instance Type | RAM | Recommended Model | Response Time |
|--------------|-----|-------------------|---------------|
| t3.micro | 1GB | ❌ Too small | N/A |
| t3.small | 2GB | qwen:0.5b (394MB) | ~1s |
| t3.medium | 4GB | tinyllama (637MB) | ~1s |
| t3.large | 8GB | gemma:2b (1.4GB) ✅ | <1s |
| t3.xlarge | 16GB | Any model | <500ms |

## 5. Immediate Workaround

While keeping your current instance:

```bash
# 1. Enable fast mode for simple extractions
grep ENABLE_FAST_MODE /home/ubuntu/contact_info_finder/.env
# Should show: ENABLE_FAST_MODE=true

# 2. Use smaller model temporarily
ollama pull tinyllama
sed -i 's/gemma:2b/tinyllama/' /home/ubuntu/contact_info_finder/.env

# 3. Add aggressive caching
echo "CACHE_SIMILARITY_THRESHOLD=0.2" >> /home/ubuntu/contact_info_finder/.env

# 4. Restart
sudo supervisorctl restart contact_api

# 5. Test - should be much faster
time curl -X POST http://54.82.217.195/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact John at 555-123-4567"}'
```

## 6. Performance Comparison

Test with different models:

```bash
# Test script
cat > test_models.sh << 'EOF'
#!/bin/bash

models=("qwen:0.5b" "tinyllama" "gemma:2b")

for model in "${models[@]}"; do
    echo -e "\n=== Testing $model ==="
    
    # Pull if not exists
    ollama pull $model 2>/dev/null
    
    # Update config
    sed -i "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$model/" /home/ubuntu/contact_info_finder/.env
    sudo supervisorctl restart contact_api
    sleep 5
    
    # Time the request
    echo "Response time:"
    time curl -s -X POST http://localhost/extract \
        -H "Content-Type: application/json" \
        -d '{"text": "Call 555-1234"}' > /dev/null
done
EOF

chmod +x test_models.sh
./test_models.sh
```

The 38-second delay is definitely a resource issue on EC2. Check your instance type and add swap space - that should fix it!