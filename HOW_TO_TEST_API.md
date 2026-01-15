# How to Test Your Contact Info Finder API

## Using the test_api.sh Script

The setup script creates `test_api.sh` in your home directory. Here's how to use it:

```bash
# Make sure you're in the home directory
cd /home/ubuntu

# Run the test script
./test_api.sh
```

## What test_api.sh Does

The script tests two endpoints:

1. **Health Check** - Verifies the API is running
2. **Extraction Test** - Tests actual contact extraction

Here's what's inside the script:

```bash
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
```

## Expected Output

When you run `./test_api.sh`, you should see:

```json
Testing Contact Info Finder API...
Health check: {
  "status": "healthy",
  "ollama": "connected",
  "model": "gemma:2b"
}

Testing extraction:
{
  "success": true,
  "status": "found",
  "data": {
    "client_name": "John Smith",
    "company_name": null,
    "phone_numbers": [
      {
        "number": "555-123-4567",
        "extension": null,
        "type": "primary"
      }
    ],
    "email": "john@example.com",
    "address": null,
    "notes": null,
    "raw_text": "Contact John Smith at 555-123-4567, email: john@example.com",
    "extracted_at": "2024-01-15T10:30:45.123456"
  },
  "error": null,
  "processing_time": 0.234,
  "cache_hit": false
}
```

## Manual Testing Options

### 1. Test Health Endpoint

```bash
# Simple health check
curl http://localhost/health

# Pretty JSON output
curl -s http://localhost/health | jq .

# From external machine (use public IP)
curl http://YOUR_EC2_PUBLIC_IP/health
```

### 2. Test Extraction - Simple

```bash
# Basic extraction test
curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Call me at 239-555-0123"}'
```

### 3. Test Extraction - Complex

```bash
# Test with full contact info
curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Doe from ABC Corp. Phone: (555) 123-4567 ext 234, email: john.doe@abc.com. Office: Suite 200, 123 Main St, Miami, FL 33101",
    "use_cache": false
  }' | jq .
```

### 4. Test Your Actual Use Cases

```bash
# Service request format (like your examples)
curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "JOBS FOR TOMORROW 2392184565 13567 Little Gem Cir, Fort Myers, Florida 33913 American garage door -keypad not working 8-10AM",
    "use_cache": false
  }' | jq .
```

## Create Custom Test Script

Create your own `test_custom.sh`:

```bash
#!/bin/bash
# Custom test cases for Contact Info Finder

API_URL="http://localhost"

echo "=== Contact Info Finder API Tests ==="

# Function to test extraction
test_extraction() {
    local test_name=$1
    local text=$2
    
    echo -e "\n📝 Test: $test_name"
    echo "Input: $text"
    echo "Response:"
    
    curl -s -X POST "$API_URL/extract" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$text\", \"use_cache\": false}" | jq .
}

# Test cases
test_extraction "Phone Only" "Call me at 555-123-4567"

test_extraction "Email Only" "Email: contact@example.com"

test_extraction "Full Address" "123 Main St, Suite 100, Miami, FL 33101"

test_extraction "Service Request" "Job #76621 - Priscilla 2393450047 10125 North Golden Elm Dr, Estero, FL 33928 Expert garage door garage door is dent 4:30-6:30pm"

test_extraction "Multiple Phones" "Primary: 555-1234, Cell: 555-5678 ext 90"

# Performance test
echo -e "\n⚡ Performance Test (10 requests):"
start_time=$(date +%s.%N)

for i in {1..10}; do
    curl -s -X POST "$API_URL/extract" \
        -H "Content-Type: application/json" \
        -d '{"text": "Test contact 555-1234"}' > /dev/null
done

end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)
avg_time=$(echo "scale=3; $duration / 10" | bc)

echo "Average response time: ${avg_time}s"
```

## Testing from Your Local Machine

If you want to test from your Windows machine:

### PowerShell:

```powershell
# Set your EC2 public IP
$API_URL = "http://YOUR_EC2_PUBLIC_IP"

# Test health
Invoke-RestMethod -Uri "$API_URL/health" -Method Get

# Test extraction
$body = @{
    text = "Contact John at 555-123-4567"
    use_cache = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "$API_URL/extract" -Method Post -ContentType "application/json" -Body $body
```

### Using Your test_api.py:

```bash
# Update the URL in test_api.py to point to your EC2
# Then run:
python test_api.py
```

## Load Testing

Test how many requests your server can handle:

```bash
# Install Apache Bench
sudo apt-get install -y apache2-utils

# Test 100 requests with 10 concurrent
ab -n 100 -c 10 -p test_data.json -T application/json http://localhost/extract

# Create test_data.json first:
echo '{"text": "Call 555-1234"}' > test_data.json
```

## Monitor While Testing

In another terminal, watch the logs:

```bash
# Watch API logs
sudo tail -f /var/log/contact_api.log

# Watch all services
./check_services.sh

# Watch system resources
htop
```

## Troubleshooting Test Failures

### "Connection refused"
```bash
# Check if services are running
sudo supervisorctl status
systemctl status nginx
systemctl status ollama
```

### "Ollama not connected"
```bash
# Test Ollama directly
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama
```

### Slow responses
```bash
# Check system resources
free -h
top

# Check if fast mode is enabled
grep ENABLE_FAST_MODE .env
```

The test script is a quick way to verify everything is working correctly!