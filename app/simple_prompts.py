EXTRACTION_PROMPT = """Extract contact info from: {text}

Return JSON with extracted values (use null if not found):
{{
  "client_name": "extracted name or null",
  "company_name": "extracted company or null",
  "email": "extracted email or null",
  "phone_numbers": [{{"number": "extracted phone", "extension": "ext if any", "type": "primary"}}],
  "address": {{"unit": null, "street": "extracted street", "city": "extracted city", "state": "extracted state", "postal_code": "extracted zip", "country": "USA"}},
  "notes": "any other text"
}}"""