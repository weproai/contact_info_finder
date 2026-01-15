# How to Create the .env Configuration File

## Method 1: Direct Creation (Simplest)

SSH into your EC2 instance and run:

```bash
# Navigate to your project directory
cd /home/ubuntu/contact_info_finder

# Create .env file with nano
nano .env
```

Then paste this content:

```bash
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
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

## Method 2: Using cat Command (As in Script)

```bash
# This is what the script does - creates .env using cat
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
```

## Method 3: Copy from Template

```bash
# If you have env.example in your repo
cp env.example .env

# Then edit it
nano .env
# Update OLLAMA_BASE_URL to http://localhost:11434
```

## Method 4: Using echo Commands

```bash
# Create file line by line
echo "# Ollama Configuration (local)" > .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env
echo "OLLAMA_MODEL=gemma:2b" >> .env
echo "" >> .env
echo "# ChromaDB Configuration" >> .env
echo "CHROMA_PERSIST_DIRECTORY=./chroma_db" >> .env
echo "CHROMA_COLLECTION_NAME=contact_extractions" >> .env
echo "" >> .env
echo "# API Configuration" >> .env
echo "API_HOST=0.0.0.0" >> .env
echo "API_PORT=8000" >> .env
echo "API_RELOAD=false" >> .env
echo "LOG_LEVEL=INFO" >> .env
echo "" >> .env
echo "# Performance" >> .env
echo "ENABLE_FAST_MODE=true" >> .env
echo "CACHE_SIMILARITY_THRESHOLD=0.1" >> .env
```

## Understanding the Configuration

### What Each Setting Does:

1. **OLLAMA_BASE_URL=http://localhost:11434**
   - Points to Ollama running on the same server
   - Use `localhost` since Ollama is on the same EC2 instance

2. **OLLAMA_MODEL=gemma:2b**
   - Specifies which model to use
   - Make sure this model is pulled: `ollama pull gemma:2b`

3. **CHROMA_PERSIST_DIRECTORY=./chroma_db**
   - Where to store the vector database cache
   - Creates a `chroma_db` folder in your project

4. **API_HOST=0.0.0.0**
   - Makes API listen on all network interfaces
   - Required for external access

5. **API_PORT=8000**
   - Port where your API runs
   - Nginx will proxy from port 80 to this port

6. **API_RELOAD=false**
   - Disables auto-reload in production
   - Set to `true` only for development

7. **ENABLE_FAST_MODE=true**
   - Enables regex-based extraction for simple cases
   - Improves response time significantly

## Verify Configuration

After creating the .env file:

```bash
# Check if file exists
ls -la .env

# View contents
cat .env

# Verify no syntax errors
python3 -c "from dotenv import load_dotenv; load_dotenv(); print('✅ .env file is valid')"
```

## Important Notes

1. **Never commit .env to Git**
   - It's already in .gitignore
   - Contains environment-specific settings

2. **Permissions**
   ```bash
   # Secure the file
   chmod 600 .env
   ```

3. **For Different Environments**
   - Development: `OLLAMA_BASE_URL=http://localhost:11434`
   - Production with separate Ollama: `OLLAMA_BASE_URL=http://ollama-server:11434`
   - Docker: `OLLAMA_BASE_URL=http://ollama:11434`

## Test Your Configuration

```bash
# Test if environment loads correctly
python3 << 'EOF'
from dotenv import load_dotenv
import os

load_dotenv()

print(f"Ollama URL: {os.getenv('OLLAMA_BASE_URL')}")
print(f"Model: {os.getenv('OLLAMA_MODEL')}")
print(f"Fast Mode: {os.getenv('ENABLE_FAST_MODE')}")
EOF
```

## Troubleshooting

If the API can't find Ollama:
```bash
# Check if using correct URL
echo $OLLAMA_BASE_URL

# Test Ollama directly
curl http://localhost:11434/api/tags

# Restart API to reload .env
sudo supervisorctl restart contact_api
```