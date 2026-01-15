# Why One Request is Fast and Another is Slow

## The Two Extraction Modes

Your API has two modes:

### 1. **Fast Mode** (Milliseconds)
- Uses regex patterns
- No Ollama needed
- Triggers when text is "simple"

### 2. **LLM Mode** (38 seconds on your EC2)
- Uses Ollama/Gemma
- More accurate for complex text
- Slow because of model loading

## Why Your Examples Differ

### Example 1: SLOW (38 seconds)
```
Contact John Smith at TechCorp International. Phone: (555) 123-4567 ext 234, 
email: john.smith@techcorp.com. Office: Suite 1500, 123 Business Blvd, 
San Francisco, CA 94105
```

**Why slow?**
- Has "ext 234" (complex phone format)
- Formal punctuation and structure
- Email with dots in username
- **Doesn't trigger fast mode → Uses Ollama**

### Example 2: FAST (milliseconds)
```
JOBS FOR TOMORROW 2392184565 13567 Little Gem Cir, Fort Myers, 
Florida 33913 American garage door -keypad not working 8-10AM
```

**Why fast?**
- Simple 10-digit phone: `2392184565`
- Less than 500 characters
- Simple patterns
- **Triggers fast mode → Uses regex only**

## Test Fast Mode Detection

SSH into your EC2 and create this test:

```bash
cat > /home/ubuntu/test_fast_mode.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.append('/home/ubuntu/contact_info_finder')

from app.fast_extractor import FastExtractor

# Test your examples
example1 = """Contact John Smith at TechCorp International. Phone: (555) 123-4567 ext 234, email: john.smith@techcorp.com. Office: Suite 1500, 123 Business Blvd, San Francisco, CA 94105"""

example2 = """JOBS FOR TOMORROW 2392184565 13567 Little Gem Cir, Fort Myers, Florida 33913 American garage door -keypad not working 8-10AM"""

print("Example 1 - Complex text:")
print(f"Length: {len(example1)}")
print(f"Can use fast mode: {FastExtractor.can_extract_fast(example1)}")

print("\nExample 2 - Simple text:")
print(f"Length: {len(example2)}")
print(f"Can use fast mode: {FastExtractor.can_extract_fast(example2)}")

# Test modified version
example1_simple = "Contact John Smith at TechCorp International. Phone: 5551234567, email: john@techcorp.com"
print("\nExample 1 - Simplified:")
print(f"Length: {len(example1_simple)}")
print(f"Can use fast mode: {FastExtractor.can_extract_fast(example1_simple)}")
EOF

cd /home/ubuntu/contact_info_finder
source venv/bin/activate
python /home/ubuntu/test_fast_mode.py
```

## Force Fast Mode for All Requests

If you want ALL requests to try fast mode first:

### Option 1: Modify Fast Mode Detection

```bash
# Edit the fast extractor
nano /home/ubuntu/contact_info_finder/app/fast_extractor.py

# Change line 16 from:
return len(text) < 500 and bool(re.search(r'\b\d{10}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', text))

# To (more lenient):
return len(text) < 1000 and bool(re.search(r'\d{3,}', text))  # Any 3+ digits
```

### Option 2: Always Try Fast Mode First

```bash
# Edit extractor.py to always try fast mode
nano /home/ubuntu/contact_info_finder/app/extractor.py

# Find the extract method and ensure fast mode runs first
```

## Make Both Examples Fast

### Solution 1: Simplify Phone Format
```python
# Preprocess text before sending
text = text.replace(" ext ", " ").replace("ext.", " ")
# "(555) 123-4567 ext 234" → "(555) 123-4567 234"
```

### Solution 2: Increase Fast Mode Threshold
```bash
# In .env file
echo "FAST_MODE_LENGTH_LIMIT=1000" >> /home/ubuntu/contact_info_finder/.env
```

### Solution 3: Cache Common Patterns
```bash
# Pre-cache the slow example
curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567 ext 234, email: john.smith@techcorp.com. Office: Suite 1500, 123 Business Blvd, San Francisco, CA 94105"
  }'

# Now it will be fast even with this exact text
```

## Performance Summary

Your API is working correctly:
- **Simple patterns** → Fast mode (milliseconds)
- **Complex patterns** → LLM mode (38 seconds first time, cached after)
- **With caching** → Both become milliseconds on repeat

The 38-second delay only happens when:
1. `use_cache: false` AND
2. Text doesn't trigger fast mode AND
3. Ollama needs to load the model

Want me to help you modify the fast mode detection to handle more cases?