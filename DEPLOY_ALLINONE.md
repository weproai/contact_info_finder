# Deploy All-in-One to AWS App Runner

This guide deploys both Ollama and your API in a single App Runner container.

## ⚠️ Important Limitations

**Running Ollama inside App Runner has significant constraints:**

1. **Performance**: App Runner has limited CPU/memory (max 4 vCPU, 12GB RAM)
2. **Storage**: Models are downloaded on each deployment (no persistent storage)
3. **Cost**: Larger instances required, increasing costs
4. **Startup Time**: 2-5 minutes to download models on each start
5. **No GPU**: CPU-only inference is slower

**Recommended**: Use separate Ollama server for production. This all-in-one approach is for testing/demo only.

## Quick Deploy Steps

### 1. Update Your Repository

Add these files to your GitHub repository:

```bash
git add Dockerfile.allinone apprunner-allinone.yaml start_allinone.py
git commit -m "Add all-in-one App Runner configuration"
git push origin main
```

### 2. Create App Runner Service

1. Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner)
2. Click **"Create service"**
3. Choose **"Source code repository"**
4. Connect your GitHub repository

### 3. Configure Build Settings

- **Configuration file**: Select `apprunner-allinone.yaml`
- App Runner will use the Docker runtime automatically

### 4. Configure Service Settings

**Important**: Ollama needs more resources!

- **CPU**: 2 vCPU (minimum, 4 vCPU recommended)
- **Memory**: 4 GB (minimum, 8 GB recommended)
- **Auto-scaling**: 
  - Min: 1 instance
  - Max: 2 instances (to control costs)

### 5. Deploy

Click **"Create & deploy"**

The first deployment will take 5-10 minutes as it:
1. Builds the Docker image
2. Downloads Ollama
3. Pulls the gemma:2b model (~1.4GB)

## Monitoring Deployment

Watch the deployment logs in App Runner console:

```
[STARTUP] Starting Ollama service...
[STARTUP] Waiting for Ollama... (1/30)
[STARTUP] Ollama is ready!
[STARTUP] Checking for model: gemma:2b
[STARTUP] Pulling gemma:2b model (this may take a few minutes)...
[STARTUP] Successfully pulled gemma:2b
[STARTUP] Starting API server...
```

## Testing

Once deployed:

```bash
# Get your App Runner URL
APP_URL="https://xxxxx.region.awsapprunner.com"

# Test health
curl $APP_URL/health

# Test extraction
curl -X POST $APP_URL/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Call John at 555-123-4567"}'
```

## Optimizations for App Runner

### 1. Use Smaller Models

Edit `apprunner-allinone.yaml`:

```yaml
- name: OLLAMA_MODEL
  value: "tinyllama"  # Smaller than gemma:2b
```

### 2. Enable Fast Mode

Already enabled in configuration for regex-based fallback.

### 3. Reduce Startup Time

Create a custom Docker image with pre-downloaded models:

```dockerfile
FROM python:3.11
# ... other steps ...
RUN ollama serve & sleep 10 && ollama pull gemma:2b && pkill ollama
```

## Cost Considerations

**Monthly costs (estimate)**:
- 2 vCPU, 4GB RAM: ~$50-80/month
- 4 vCPU, 8GB RAM: ~$150-200/month

**To reduce costs**:
1. Use auto-pause (automatically pauses after inactivity)
2. Set minimum instances to 0
3. Use smaller models (tinyllama)
4. Enable fast mode for most requests

## Troubleshooting

### "Service unhealthy"
- Check if 4GB+ memory allocated
- View logs for Ollama startup errors

### "Model download failed"
- App Runner might timeout during model download
- Try smaller model (tinyllama)

### "Slow responses"
- CPU inference is slow
- Enable fast mode: `ENABLE_FAST_MODE=true`
- Consider separate Ollama server

## Alternative: Hybrid Approach

For better performance, run only the API in App Runner:

1. **Ollama**: Run on EC2 with GPU
2. **API**: Run in App Runner
3. Update `OLLAMA_BASE_URL` to point to EC2

This gives you:
- ✅ Better performance
- ✅ Lower App Runner costs
- ✅ Persistent model storage
- ✅ GPU acceleration option

## Production Recommendations

1. **Don't use all-in-one for production** - Performance and cost issues
2. **Use separate Ollama server** - EC2, ECS, or managed service
3. **Enable CloudWatch alarms** - Monitor memory/CPU usage
4. **Set up health checks** - Ensure Ollama stays running
5. **Use caching aggressively** - Reduce Ollama calls

The all-in-one approach works but has significant trade-offs. For production, strongly consider running Ollama separately!