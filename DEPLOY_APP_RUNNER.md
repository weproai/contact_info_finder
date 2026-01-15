# Deploy to AWS App Runner

This guide shows how to deploy the Contact Info Finder API to AWS App Runner using GitHub as the source.

## Prerequisites

1. AWS Account with App Runner access
2. GitHub repository with your code
3. Ollama server running somewhere accessible (e.g., EC2, ECS, or external service)

## Important Note About Ollama

**AWS App Runner cannot run Ollama directly** because:
- Ollama requires GPU/significant CPU resources
- App Runner containers are stateless and lightweight

You need to run Ollama separately on:
- AWS EC2 instance with GPU (recommended)
- AWS ECS with GPU-enabled tasks
- External Ollama API service
- Your own server with public endpoint

## Deployment Steps

### 1. Push Code to GitHub

```bash
git add .
git commit -m "Prepare for App Runner deployment"
git push origin main
```

### 2. Create App Runner Service

1. Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner)
2. Click "Create service"
3. Choose **Source code repository**
4. Connect to GitHub:
   - Click "Add new" under GitHub connection
   - Authorize AWS to access your GitHub
   - Select your repository and branch

### 3. Configure Build Settings

App Runner will automatically detect `apprunner.yaml` in your repository.

If not detected:
- **Runtime**: Python 3.11
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- **Port**: 8000

### 4. Configure Environment Variables

In the App Runner console, set these environment variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `OLLAMA_BASE_URL` | `http://your-ollama-server:11434` | Your Ollama server URL |
| `OLLAMA_MODEL` | `gemma:2b` | The model to use |
| `ENABLE_FAST_MODE` | `true` | Enable regex fallback for speed |
| `LOG_LEVEL` | `INFO` | Logging level |

### 5. Configure Service Settings

- **CPU**: 0.25 vCPU (minimum)
- **Memory**: 0.5 GB (minimum)
- **Auto scaling**: 
  - Min: 1 instance
  - Max: 3 instances (adjust based on load)

### 6. Deploy

Click "Create & deploy" and wait for deployment to complete.

## Setting Up Ollama Server

### Option 1: EC2 Instance

```bash
# Launch EC2 instance (t3.medium or larger)
# SSH into instance and run:
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull gemma:2b
```

### Option 2: Docker on EC2

```dockerfile
FROM ollama/ollama
RUN ollama pull gemma:2b
EXPOSE 11434
CMD ["serve"]
```

### Security Configuration

1. Configure Security Group:
   - Allow port 11434 from App Runner service
   - Use VPC endpoint for private communication

2. For public Ollama endpoint:
   - Use API key authentication
   - Implement rate limiting
   - Use HTTPS

## Testing Your Deployment

Once deployed, test your API:

```bash
# Get your App Runner URL from console
APP_URL="https://xxxxx.region.awsapprunner.com"

# Test health endpoint
curl $APP_URL/health

# Test extraction
curl -X POST $APP_URL/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John at 555-123-4567",
    "use_cache": false
  }'
```

## Monitoring

1. **CloudWatch Logs**: Automatically enabled
2. **Metrics**: CPU, Memory, Request count, Latency
3. **Health checks**: App Runner monitors `/health` endpoint

## Cost Optimization

1. **Use Fast Mode**: Set `ENABLE_FAST_MODE=true` for regex-based extraction
2. **Enable Caching**: ChromaDB caching reduces Ollama calls
3. **Auto-scaling**: Set appropriate min/max instances
4. **Ollama Server**: Use spot instances for cost savings

## Troubleshooting

### "Ollama connection failed"
- Check `OLLAMA_BASE_URL` is correct
- Ensure Ollama server is accessible from App Runner
- Check security groups and network configuration

### "Slow response times"
- Enable fast mode: `ENABLE_FAST_MODE=true`
- Check Ollama server performance
- Consider using smaller model (gemma:2b is already optimized)

### "Out of memory"
- Increase App Runner memory allocation
- Check for memory leaks in logs

## Production Best Practices

1. **Environment Variables**: Never commit `.env` file
2. **Secrets**: Use AWS Secrets Manager for sensitive data
3. **Monitoring**: Set up CloudWatch alarms
4. **Backup**: Regular ChromaDB backups if using persistent storage
5. **API Keys**: Implement authentication for production use

## Example Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  App Runner  │────▶│   Ollama    │
│             │     │  (Your API)  │     │   Server    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  ChromaDB    │
                    │   (Cache)    │
                    └──────────────┘
```

## Next Steps

1. Set up custom domain
2. Implement API authentication
3. Add rate limiting
4. Set up monitoring alerts
5. Configure auto-scaling policies