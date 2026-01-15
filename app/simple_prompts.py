"""Simplified prompts for smaller/faster models"""

SIMPLE_EXTRACTION_PROMPT = """Extract from: {text}

Find:
- Phone: (10 digit number)
- Street address
- City, State ZIP
- Any other info = notes

Output JSON only:
{{
  "phone_numbers": [{{"number": "PHONE_HERE", "extension": null, "type": "primary"}}],
  "address": {{"street": "STREET", "city": "CITY", "state": "STATE", "postal_code": "ZIP", "country": "USA"}},
  "notes": "OTHER_INFO"
}}"""