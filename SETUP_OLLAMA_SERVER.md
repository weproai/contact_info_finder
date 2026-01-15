# Setting Up Ollama Server Separately

This guide shows multiple ways to set up Ollama as a separate service for your Contact Info Finder API.

## Option 1: AWS EC2 Instance (Recommended)

### Quick Setup Script

Save this as `setup_ollama_ec2.sh` and run on your EC2 instance:

```bash
#!/bin/bash
# Ollama EC2 Setup Script

# Update system
sudo apt update && sudo apt upgrade -y

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Create systemd service
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/local/bin/ollama serve
Restart=always
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for service to start
sleep 5

# Pull gemma:2b model
ollama pull gemma:2b

echo "Ollama setup complete!"
echo "Test with: curl http://localhost:11434/api/tags"
```

### Manual EC2 Setup Steps

1. **Launch EC2 Instance**
   ```
   Instance Type: t3.large (minimum) or g4dn.xlarge (for GPU)
   AMI: Ubuntu 22.04 LTS
   Storage: 30GB minimum
   ```

2. **Configure Security Group**
   ```
   Inbound Rules:
   - SSH (22) from your IP
   - Custom TCP (11434) from App Runner subnet or 0.0.0.0/0
   ```

3. **Connect and Install**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama
   ollama serve &
   
   # Pull model
   ollama pull gemma:2b
   ```

4. **Update App Runner Environment**
   ```
   OLLAMA_BASE_URL=http://your-ec2-public-ip:11434
   ```

## Option 2: AWS ECS with Fargate

### 1. Create Task Definition

`ollama-task-definition.json`:

```json
{
  "family": "ollama-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "ollama",
      "image": "ollama/ollama:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 11434,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OLLAMA_HOST",
          "value": "0.0.0.0"
        }
      ],
      "command": ["serve"],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ollama",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 2. Deploy with CLI

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/ollama

# Register task definition
aws ecs register-task-definition --cli-input-json file://ollama-task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster your-cluster \
  --service-name ollama-service \
  --task-definition ollama-service:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Option 3: Docker on Any VPS

### Quick Docker Setup

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Run Ollama container
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --restart always \
  ollama/ollama

# Pull model
docker exec -it ollama ollama pull gemma:2b

# Create docker-compose.yml for easier management
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: always
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama_data:
EOF

# Start with docker-compose
docker-compose up -d
```

## Option 4: Managed Ollama Services

### Replicate.com (Easiest)

1. Sign up at [replicate.com](https://replicate.com)
2. Get API token
3. Use their API endpoint instead:

```python
# In your app, use Replicate instead of Ollama
import replicate

output = replicate.run(
    "meta/llama-2-7b:latest",
    input={"prompt": "Extract contact info..."}
)
```

### Modal.com

1. Install Modal: `pip install modal`
2. Deploy Ollama:

```python
# ollama_modal.py
import modal

stub = modal.Stub("ollama-server")
image = modal.Image.debian_slim().run_commands(
    "apt update && apt install -y curl",
    "curl -fsSL https://ollama.ai/install.sh | sh",
    "ollama pull gemma:2b"
)

@stub.function(image=image, gpu="T4", container_idle_timeout=300)
@modal.web_endpoint(method="POST")
def generate(prompt: str):
    import subprocess
    result = subprocess.run(
        ["ollama", "run", "gemma:2b", prompt],
        capture_output=True,
        text=True
    )
    return {"response": result.stdout}

# Deploy: modal deploy ollama_modal.py
```

## Option 5: Local Development with Ngrok

For testing App Runner with local Ollama:

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Start Ollama locally
ollama serve

# Expose with ngrok
ngrok http 11434

# Use ngrok URL in App Runner
# OLLAMA_BASE_URL=https://your-ngrok-url.ngrok.io
```

## Security Best Practices

### 1. API Key Authentication

Add nginx proxy with basic auth:

```nginx
server {
    listen 80;
    server_name your-ollama-server.com;

    location / {
        auth_basic "Ollama API";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://localhost:11434;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. VPC Peering (AWS)

Connect App Runner to EC2 via VPC:

```bash
# Create VPC endpoint for App Runner
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.apprunner.services
```

### 3. IP Whitelisting

EC2 Security Group:
```
Type: Custom TCP
Port: 11434
Source: App Runner Outbound IPs only
```

## Monitoring & Maintenance

### 1. Health Check Script

```bash
#!/bin/bash
# ollama_health_check.sh

OLLAMA_URL="http://localhost:11434"

# Check if Ollama is running
if curl -s "$OLLAMA_URL/api/tags" > /dev/null; then
    echo "✅ Ollama is healthy"
    
    # Check if model exists
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "gemma:2b"; then
        echo "✅ Model gemma:2b is loaded"
    else
        echo "⚠️  Model gemma:2b not found, pulling..."
        ollama pull gemma:2b
    fi
else
    echo "❌ Ollama is not responding"
    # Restart service
    sudo systemctl restart ollama
fi
```

### 2. Auto-restart with Systemd

```ini
# /etc/systemd/system/ollama.service
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
Environment="OLLAMA_MODELS=/home/ubuntu/.ollama/models"

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### 3. CloudWatch Monitoring (EC2)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure metrics
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

## Cost Optimization

### Instance Recommendations by Budget:

1. **Development/Testing**
   - t3.medium: ~$30/month
   - 2 vCPU, 4GB RAM
   - Good for testing

2. **Production (CPU)**
   - t3.large: ~$60/month
   - 2 vCPU, 8GB RAM
   - Handles moderate load

3. **Production (GPU)**
   - g4dn.xlarge: ~$380/month
   - 4 vCPU, 16GB RAM, 1 GPU
   - Much faster inference

### Auto-shutdown for Development:

```bash
# Auto-stop EC2 after 1 hour of low CPU
aws autoscaling put-scaling-policy \
  --policy-name ollama-scale-down \
  --auto-scaling-group-name ollama-asg \
  --scaling-adjustment -1 \
  --adjustment-type ChangeInCapacity \
  --cooldown 3600
```

## Quick Start Commands

### For EC2:
```bash
# One-liner to install and start
curl -fsSL https://ollama.ai/install.sh | sh && ollama serve & sleep 5 && ollama pull gemma:2b
```

### For Docker:
```bash
# One-liner with Docker
docker run -d -p 11434:11434 -v ollama:/root/.ollama ollama/ollama && docker exec ollama ollama pull gemma:2b
```

### Update App Runner:
```
OLLAMA_BASE_URL=http://your-server-ip:11434
```

## Troubleshooting

### "Connection refused"
- Check security groups/firewall
- Verify Ollama is listening on 0.0.0.0
- Test locally: `curl http://localhost:11434/api/tags`

### "Model not found"
- SSH to server and run: `ollama pull gemma:2b`
- Check disk space: `df -h`

### "Slow responses"
- Upgrade instance type
- Consider GPU instance
- Enable fast mode in your API

Choose the option that best fits your needs and budget!