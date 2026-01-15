# Fix API Blocking Other Requests

## The Problem

Your API is running with a single worker/thread, so when one request takes 47 seconds, it blocks all other requests.

## Quick Fix on EC2

### 1. Check Current Configuration

```bash
# Check how API is running
sudo cat /etc/supervisor/conf.d/contact_api.conf
```

### 2. Update to Use Multiple Workers

```bash
# Update supervisor config for multiple workers
sudo nano /etc/supervisor/conf.d/contact_api.conf
```

Change from:
```ini
command=/home/ubuntu/contact_info_finder/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

To:
```ini
command=/home/ubuntu/contact_info_finder/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Or Use Gunicorn (Better for Production)

```bash
# Install gunicorn
cd /home/ubuntu/contact_info_finder
source venv/bin/activate
pip install gunicorn

# Update supervisor config
sudo tee /etc/supervisor/conf.d/contact_api.conf > /dev/null <<'EOF'
[program:contact_api]
command=/home/ubuntu/contact_info_finder/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
directory=/home/ubuntu/contact_info_finder
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/contact_api.log
environment=PATH="/home/ubuntu/contact_info_finder/venv/bin",PYTHONPATH="/home/ubuntu/contact_info_finder"
EOF

# Restart
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart contact_api
```

## Test Concurrent Requests

```bash
# Terminal 1: Start a slow request
curl -X POST http://54.82.217.195/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567 ext 234", "use_cache": false}' &

# Terminal 2: Immediately test a fast request
curl http://54.82.217.195/health
```

## Better Solution: Async Processing

For long-running extractions, consider:

### 1. Add Request Timeout
```python
# In main.py
from fastapi import HTTPException
import asyncio

@app.post("/extract")
async def extract(request: ExtractionRequest):
    try:
        # Add 10 second timeout
        result = await asyncio.wait_for(
            process_extraction(request),
            timeout=10.0
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")
```

### 2. Use Background Tasks
```python
from fastapi import BackgroundTasks

@app.post("/extract-async")
async def extract_async(request: ExtractionRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(process_extraction_background, job_id, request)
    return {"job_id": job_id, "status": "processing"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    # Return result when ready
    pass
```

## Immediate Fix for m5a.xlarge

Your instance has 4 vCPUs, so use them:

```bash
# Quick update
sudo sed -i 's/uvicorn main:app --host/uvicorn main:app --workers 4 --host/' /etc/supervisor/conf.d/contact_api.conf
sudo supervisorctl restart contact_api
```

Now your API can handle 4 concurrent requests!