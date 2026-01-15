# Fix 38-Second API Delay on EC2

## The Problem Found

- **Direct Ollama**: 5.2 seconds ✅
- **Through API**: 38 seconds ❌
- **Difference**: 33 seconds added by your API

The issue is the complex prompt causing Ollama to take much longer to process.

## Quick Fix: Simplify the Prompt

SSH to your EC2 and create a simpler prompt:

```bash
# Backup original prompts
cp /home/ubuntu/contact_info_finder/app/prompts.py /home/ubuntu/contact_info_finder/app/prompts_original.py

# Create simplified prompt
cat > /home/ubuntu/contact_info_finder/app/prompts.py << 'EOF'
EXTRACTION_PROMPT = """Extract: {text}

Return JSON:
{{
  "client_name": "name or null",
  "company_name": "company or null", 
  "email": "email or null",
  "phone_numbers": [{{"number": "phone", "extension": "ext or null", "type": "primary"}}],
  "address": {{"unit": "unit", "street": "street", "city": "city", "state": "state", "postal_code": "zip", "country": "USA"}},
  "notes": "other info"
}}"""

VALIDATION_PROMPT = """Rate confidence (0.0-1.0):
{extraction}

Return only:
{{"client_name": 0.9, "company_name": 0.9, "phone_numbers": 0.9, "email": 0.9, "address": 0.9}}"""
EOF

# Restart API
sudo supervisorctl restart contact_api
```

## Test the Fix

```bash
# Test the slow text again
time curl -X POST http://localhost/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact John Smith at TechCorp International. Phone: (555) 123-4567 ext 234, email: john.smith@techcorp.com. Office: Suite 1500, 123 Business Blvd, San Francisco, CA 94105",
    "use_cache": false
  }'
```

## Alternative Fix: Optimize Ollama Settings

```bash
# Edit extractor.py to reduce Ollama processing
nano /home/ubuntu/contact_info_finder/app/extractor.py

# Find the options section (around line 138) and change to:
options={
    'temperature': 0.0,  # Was 0.1
    'top_p': 0.1,       # Was 0.9 - much faster
    'num_predict': 200   # Limit output length
}
```

## Why This Happens

1. **Complex prompts** take longer for LLMs to process
2. **Gemma:2b** on CPU is sensitive to prompt length
3. Your original prompt has lots of instructions and examples

## Expected Results After Fix

- Simple prompt: ~5-8 seconds (like direct Ollama)
- Original prompt: 38 seconds

## Permanent Solution Options

### Option 1: Keep Two Prompt Modes
```python
# In prompts.py
SIMPLE_PROMPT = """Extract: {text}
Return JSON: {{"phone_numbers": [...], "address": {{...}}, ...}}"""

DETAILED_PROMPT = """[Your original long prompt]"""

# Use simple for most cases, detailed for complex
```

### Option 2: Use Faster Model for Complex Prompts
```bash
# qwen:0.5b handles long prompts better
ollama pull qwen:0.5b

# For complex texts, use qwen
# For simple texts, use gemma
```

### Option 3: Pre-process Text
```python
# Shorten text before sending to Ollama
if len(text) > 200:
    # Extract key parts first
    text = extract_key_parts(text)
```

Try the simplified prompt first - it should reduce your 38 seconds to about 5-8 seconds!