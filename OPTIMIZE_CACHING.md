# Optimize Caching for Fast Responses

## Understanding the Cache Behavior

When you send a request:
- **`"use_cache": false`** → Always calls Ollama (38 seconds on your EC2)
- **`"use_cache": true`** (default) → Checks cache first (milliseconds if found)

## Test Cache Performance

### 1. First Request (No Cache)
```bash
# This will be slow (calls Ollama)
time curl -X POST http://54.82.217.195/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567"
  }'
```

### 2. Second Request (With Cache)
```bash
# This should be FAST (uses cache)
time curl -X POST http://54.82.217.195/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567"
  }'
```

### 3. Slightly Different Text (Cache Miss)
```bash
# Even small changes might miss cache
time curl -X POST http://54.82.217.195/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567."
  }'
# Note the extra period!
```

## Optimize Cache Settings

### 1. Increase Cache Sensitivity

SSH into your EC2:
```bash
# Edit the .env file
nano /home/ubuntu/contact_info_finder/.env

# Increase the similarity threshold (default 0.1)
# Higher = more cache hits (but less accurate)
CACHE_SIMILARITY_THRESHOLD=0.3

# Save and restart
sudo supervisorctl restart contact_api
```

### 2. Pre-warm Common Patterns

Create a cache warming script:
```bash
cat > /home/ubuntu/warm_cache.sh << 'EOF'
#!/bin/bash
# Pre-populate cache with common patterns

echo "Warming cache with common patterns..."

# Common patterns to cache
patterns=(
    "Call NAME at PHONE"
    "Contact NAME at COMPANY. Phone: PHONE"
    "NAME PHONE ADDRESS"
    "Job #NUMBER - NAME PHONE ADDRESS"
    "Email: EMAIL, Phone: PHONE"
    "COMPANY NAME PHONE EMAIL ADDRESS"
)

# Test data for each pattern
for pattern in "${patterns[@]}"; do
    # Generate test data
    case "$pattern" in
        *PHONE*)
            for area in 239 305 786 813 954; do
                text="${pattern//PHONE/${area}-555-0123}"
                text="${text//NAME/John Doe}"
                text="${text//COMPANY/ABC Corp}"
                text="${text//ADDRESS/123 Main St, Miami, FL 33101}"
                text="${text//EMAIL/test@example.com}"
                text="${text//NUMBER/12345}"
                
                # Cache it
                curl -s -X POST http://localhost/extract \
                    -H "Content-Type: application/json" \
                    -d "{\"text\": \"$text\"}" > /dev/null
                
                echo "Cached: ${text:0:50}..."
            done
            ;;
    esac
done

echo "Cache warming complete!"
EOF

chmod +x /home/ubuntu/warm_cache.sh
./warm_cache.sh
```

### 3. Enable Fast Mode + Cache Combo

```bash
# Ensure fast mode is enabled
grep ENABLE_FAST_MODE /home/ubuntu/contact_info_finder/.env

# This gives you:
# 1. Regex extraction first (milliseconds)
# 2. Cache check second (milliseconds)  
# 3. Ollama only as last resort (seconds)
```

## Monitor Cache Performance

### Check Cache Stats
```bash
# See cache hit rate
curl http://54.82.217.195/stats
```

### Test Cache vs No-Cache
```bash
cat > /home/ubuntu/test_cache_performance.sh << 'EOF'
#!/bin/bash

echo "=== Cache Performance Test ==="

TEST_TEXT="Contact John at 555-123-4567, email: john@example.com"

# Test WITH cache (default)
echo -e "\n1. WITH CACHE (use_cache: true):"
time curl -s -X POST http://localhost/extract \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" > /dev/null

# Test WITHOUT cache
echo -e "\n2. WITHOUT CACHE (use_cache: false):"
time curl -s -X POST http://localhost/extract \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\", \"use_cache\": false}" > /dev/null

# Test WITH cache again (should be instant)
echo -e "\n3. WITH CACHE AGAIN (should be instant):"
time curl -s -X POST http://localhost/extract \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" > /dev/null
EOF

chmod +x test_cache_performance.sh
./test_cache_performance.sh
```

## Best Practices for Your Use Case

### 1. Default to Cache On
```python
# Your requests should look like:
{
    "text": "your text here"
    # Don't include use_cache - defaults to true
}
```

### 2. Only Disable Cache When Needed
```python
# Only use this for testing or when you need fresh extraction
{
    "text": "your text here",
    "use_cache": false  # Only for special cases
}
```

### 3. Cache-Friendly Text Normalization
Before sending to API, normalize text:
```python
# Example normalization
text = text.strip()  # Remove extra spaces
text = " ".join(text.split())  # Normalize whitespace
# This increases cache hits
```

## Expected Performance

With proper caching:
- **First unique request**: 2-38s (depending on model/instance)
- **Cached requests**: 10-50ms ✅
- **Similar requests**: 50-200ms (with similarity matching)
- **Fast mode (simple patterns)**: 5-20ms

## Quick Fix for Your Current Setup

```bash
# Just remove use_cache from your requests!
# Instead of:
curl -X POST http://54.82.217.195/extract \
  -d '{"text": "...", "use_cache": false}'

# Use:
curl -X POST http://54.82.217.195/extract \
  -d '{"text": "..."}'
```

Your discovery is correct - let the cache work for you!