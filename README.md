# Contact Info Finder API

An intelligent API that extracts contact information from unstructured text using Ollama LLM and ChromaDB for caching and similarity search.

## 🚀 Quick Start

```powershell
# Clone the repository
git clone <your-repo-url>
cd contact_info_finder

# Run everything with one command
.\start.ps1
```

That's it! The script handles everything automatically.

## Features

- **Automatic Extraction** of:
  - Client Name
  - Company Name
  - Phone Numbers (with extensions)
  - Multiple phone numbers support
  - Email addresses
  - Full addresses (street, city, state, zip, country)
  - Apartment/Suite/Unit numbers

- **Smart Caching**: Uses ChromaDB to cache similar extractions
- **Confidence Scoring**: Provides confidence levels for each extracted field
- **Validation**: Built-in validation for phone numbers, emails, and addresses
- **RESTful API**: Easy to integrate with any application

## Prerequisites

1. **Python 3.8+**
2. **Ollama** installed and running locally
   ```bash
   # Install Ollama from https://ollama.ai
   # Pull a model (e.g., llama2)
   ollama pull llama2
   ```

## Quick Start (One Command)

Simply run:
```powershell
.\start.ps1
```

This single command will automatically:
- ✅ Create virtual environment (if needed)
- ✅ Install all dependencies (if needed)
- ✅ Create configuration files
- ✅ Set up directories
- ✅ Start the API server

## Manual Installation (Optional)

If you prefer manual setup:

1. Clone the repository:
   ```bash
   cd contact_info_finder
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file:
   ```bash
   # Copy from the example
   copy .env.example .env  # Windows
   cp .env.example .env    # Unix/MacOS
   ```

## Configuration

Edit `.env` file to configure:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:2b  # Options: gemma:2b, mistral, tinyllama, phi , qwen:0.5b

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=contact_extractions

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Logging
LOG_LEVEL=INFO

# Performance Settings
ENABLE_FAST_MODE=false  # true = 1ms response (regex), false = accurate (LLM)
CACHE_SIMILARITY_THRESHOLD=0.1  # Lower = more strict matching
```

### Performance Modes

1. **Fast Mode** (`ENABLE_FAST_MODE=true`)
   - Response time: 1-5ms
   - Method: Regex pattern matching
   - Accuracy: Lower (good for simple patterns)

2. **Accurate Mode** (`ENABLE_FAST_MODE=false`) - Default
   - Response time: 2-5 seconds
   - Method: LLM extraction
   - Accuracy: High

3. **Cached Responses**
   - Response time: 50-200ms
   - Returns cached results for similar texts

## Running the API

1. Make sure Ollama is running:
   ```bash
   # Check Ollama status
   ollama list
   ```

2. Start the API:
   ```powershell
   .\start.ps1
   ```

3. The API will be available at `http://localhost:8000`
4. Interactive docs at `http://localhost:8000/docs`

## API Endpoints

### Extract Contact Information

**POST** `/extract`

Request:
```json
{
  "text": "John Doe from ABC Corp can be reached at 555-123-4567 ext 123 or john.doe@example.com. Office at Suite 200, 5826 Dumfries Drive, Houston, TX 77096",
  "use_cache": true
}
```

Response:
```json
{
  "success": true,
  "data": {
    "client_name": "John Doe",
    "company_name": "ABC Corp",
    "phone_numbers": [
      {
        "number": "+1 555-123-4567",
        "extension": "123",
        "type": "primary"
      }
    ],
    "email": "john.doe@example.com",
    "address": {
      "unit": "Suite 200",
      "street": "5826 Dumfries Drive",
      "city": "Houston",
      "state": "TX",
      "postal_code": "77096",
      "country": "USA"
    }
  },
  "processing_time": 1.23,
  "cache_hit": false
}
```

### Health Check

**GET** `/health`

Response:
```json
{
  "status": "healthy",
  "ollama_status": "healthy",
  "chromadb_status": "healthy",
  "timestamp": "2024-01-13T10:30:00"
}
```

### Statistics

**GET** `/stats`

Response:
```json
{
  "success": true,
  "stats": {
    "total_extractions": 150,
    "collection_name": "contact_extractions"
  }
}
```

## Usage Examples

### Python
```python
import requests

url = "http://localhost:8000/extract"
data = {
    "text": "Contact Sarah Johnson at Tech Solutions Inc. Phone: (555) 987-6543 x456, email: sarah.j@techsolutions.com"
}

response = requests.post(url, json=data)
result = response.json()
print(result['data'])
```

### cURL
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "Call Mike at 555-123-4567"}'
```

### Real-world Example (Service Request)
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Robert Scheckler\n\n4754195929\n30 Fountain St, Port Charlotte, Florida 33953\nExpert_Garage_door\nGenie Model 2028 garage door repair, new remote needed.\n4–6pm"
  }'
```

## Performance Tips

1. **Model Selection**: Smaller models like `mistral` are faster but may be less accurate
2. **Caching**: Keep `use_cache=true` for repeated similar texts
3. **Batch Processing**: Process multiple texts in parallel for better throughput

## Troubleshooting

1. **Ollama not found**: Ensure Ollama is installed and running
2. **Model not available**: Pull the model with `ollama pull <model_name>`
3. **Port already in use**: Change `API_PORT` in `.env`
4. **Low extraction accuracy**: Try a different model or adjust prompts

## License

MIT License