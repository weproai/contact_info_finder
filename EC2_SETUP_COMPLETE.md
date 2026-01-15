# Complete EC2 Setup: API + Ollama on One Server

## EC2 Instance Recommendations

### For gemma:2b Model (Your Current Choice)

| Use Case | Instance Type | vCPU | RAM | Storage | Monthly Cost |
|----------|--------------|------|-----|---------|--------------|
| **Development/Testing** | t3.medium | 2 | 4 GB | 30 GB | ~$30 |
| **Light Production** | t3.large | 2 | 8 GB | 50 GB | ~$60 |
| **Recommended Production** | t3.xlarge | 4 | 16 GB | 100 GB | ~$120 |
| **High Performance** | c5.2xlarge | 8 | 16 GB | 100 GB | ~$250 |
| **GPU Accelerated** | g4dn.xlarge | 4 | 16 GB | 125 GB | ~$380 |

### Why These Specs for gemma:2b:
- **Model Size**: ~1.4 GB on disk
- **RAM Needed**: 4-6 GB for model + 2 GB for system/API
- **CPU**: More cores = faster inference
- **Storage**: Models + logs + system

## Complete One-Server Setup Script

Save this as `setup_complete_ec2.sh`:

```bash
#!/bin/bash
# Complete setup script for EC2 - Ollama + Contact Info Finder API

set -e  # Exit on error

echo "=== Complete EC2 Setup for Contact Info Finder ==="

# Update system
echo "1. Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
echo "2. Installing Python 3.11..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies
echo "3. Installing system dependencies..."
sudo apt install -y git curl nginx supervisor build-essential

# Install Ollama
echo "4. Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

# Create ollama systemd service
echo "5. Creating Ollama service..."
sudo tee /etc/systemd/system/ollama.service > /dev/null <<'EOF'
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
EOF

# Start Ollama
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for Ollama to start
echo "6. Waiting for Ollama to start..."
sleep 10

# Pull gemma:2b model
echo "7. Pulling gemma:2b model (this may take a few minutes)..."
ollama pull gemma:2b

# Clone your repository
echo "8. Setting up Contact Info Finder API..."
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/contact_info_finder.git
cd contact_info_finder

# Create Python virtual environment
echo "9. Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "10. Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "11. Creating environment configuration..."
cat > .env <<'EOF'
# Ollama Configuration (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:2b

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=contact_extractions

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
LOG_LEVEL=INFO

# Performance
ENABLE_FAST_MODE=true
CACHE_SIMILARITY_THRESHOLD=0.1
EOF

# Create ChromaDB directory
mkdir -p chroma_db

# Create supervisor configuration for API
echo "12. Setting up API service..."
sudo tee /etc/supervisor/conf.d/contact_api.conf > /dev/null <<'EOF'
[program:contact_api]
command=/home/ubuntu/contact_info_finder/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
directory=/home/ubuntu/contact_info_finder
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/contact_api.log
environment=PATH="/home/ubuntu/contact_info_finder/venv/bin",PYTHONPATH="/home/ubuntu/contact_info_finder"
EOF

# Configure Nginx as reverse proxy
echo "13. Configuring Nginx..."
sudo tee /etc/nginx/sites-available/contact_api > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/contact_api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Start services
echo "14. Starting services..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start contact_api

# Create monitoring script
echo "15. Creating monitoring script..."
cat > /home/ubuntu/check_services.sh <<'EOF'
#!/bin/bash
# Service health check script

echo "=== Service Status Check ==="

# Check Ollama
if systemctl is-active --quiet ollama; then
    echo "✅ Ollama: Running"
    if curl -s http://localhost:11434/api/tags | grep -q "gemma:2b"; then
        echo "✅ Model: gemma:2b loaded"
    else
        echo "❌ Model: gemma:2b not found"
    fi
else
    echo "❌ Ollama: Not running"
fi

# Check API
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ API: Healthy"
else
    echo "❌ API: Not responding"
fi

# Check Nginx
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx: Running"
else
    echo "❌ Nginx: Not running"
fi

# System resources
echo ""
echo "=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
EOF

chmod +x /home/ubuntu/check_services.sh

# Create quick test script
echo "16. Creating test script..."
cat > /home/ubuntu/test_api.sh <<'EOF'
#!/bin/bash
# Quick API test

echo "Testing Contact Info Finder API..."

# Test health endpoint
echo -n "Health check: "
curl -s http://localhost/health | jq .

# Test extraction
echo -e "\nTesting extraction:"
curl -s -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact John Smith at 555-123-4567, email: john@example.com"}' | jq .
EOF

chmod +x /home/ubuntu/test_api.sh

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Your server is ready with:"
echo "✅ Ollama running on port 11434"
echo "✅ API running on port 8000"
echo "✅ Nginx proxy on port 80"
echo ""
echo "Public URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo ""
echo "Test with: ./test_api.sh"
echo "Monitor with: ./check_services.sh"
echo ""
echo "Logs:"
echo "- API: sudo tail -f /var/log/contact_api.log"
echo "- Ollama: sudo journalctl -u ollama -f"
echo "- Nginx: sudo tail -f /var/log/nginx/access.log"
```

## Quick Launch Commands

### 1. Launch EC2 Instance (AWS CLI)

```bash
# Launch t3.large instance
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.large \
  --key-name your-key-name \
  --security-group-ids sg-xxxxxx \
  --subnet-id subnet-xxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ContactInfoFinder}]' \
  --user-data file://setup_complete_ec2.sh
```

### 2. Security Group Rules

```bash
# Create security group
aws ec2 create-security-group \
  --group-name contact-info-finder \
  --description "Contact Info Finder API"

# Add rules
aws ec2 authorize-security-group-ingress \
  --group-name contact-info-finder \
  --protocol tcp --port 22 --cidr YOUR_IP/32  # SSH

aws ec2 authorize-security-group-ingress \
  --group-name contact-info-finder \
  --protocol tcp --port 80 --cidr 0.0.0.0/0  # HTTP

aws ec2 authorize-security-group-ingress \
  --group-name contact-info-finder \
  --protocol tcp --port 443 --cidr 0.0.0.0/0  # HTTPS (if using SSL)
```

## Post-Installation Steps

### 1. Connect to Your Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 2. Run Setup Script

```bash
# Download and run the setup script
curl -O https://raw.githubusercontent.com/YOUR_REPO/main/setup_complete_ec2.sh
chmod +x setup_complete_ec2.sh
./setup_complete_ec2.sh
```

### 3. Verify Everything Works

```bash
# Check services
./check_services.sh

# Test API
./test_api.sh
```

## Production Optimizations

### 1. Enable Swap (for t3.medium)

```bash
# Create 4GB swap file
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. SSL Certificate (with Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Auto-restart on Reboot

```bash
# Already configured with systemd and supervisor
sudo systemctl enable ollama
sudo systemctl enable supervisor
sudo systemctl enable nginx
```

### 4. CloudWatch Monitoring

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

## Monitoring Dashboard

Create `monitor.py` for a simple monitoring endpoint:

```python
from fastapi import FastAPI
import psutil
import subprocess

app = FastAPI()

@app.get("/monitor")
def get_system_status():
    # Check Ollama
    try:
        ollama_status = subprocess.run(
            ["systemctl", "is-active", "ollama"], 
            capture_output=True, text=True
        ).stdout.strip() == "active"
    except:
        ollama_status = False
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total // (1024**3),
            "used": psutil.virtual_memory().used // (1024**3),
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total // (1024**3),
            "used": psutil.disk_usage('/').used // (1024**3),
            "percent": psutil.disk_usage('/').percent
        },
        "services": {
            "ollama": ollama_status,
            "api": True  # If this endpoint responds, API is up
        }
    }
```

## Cost Breakdown

### t3.large (Recommended)
- **Hourly**: $0.0832
- **Daily**: ~$2.00
- **Monthly**: ~$60
- **Annual**: ~$720

### With Reserved Instance (1 year):
- **Monthly**: ~$38 (37% savings)

### With Spot Instance:
- **Monthly**: ~$20-25 (up to 70% savings)

## When to Scale

Upgrade to larger instance if:
- Response time > 2 seconds consistently
- CPU usage > 80% sustained
- Memory usage > 85%
- Multiple concurrent requests fail

This complete setup gives you everything on one EC2 server with production-ready configuration!