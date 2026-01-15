EXTRACTION_PROMPT = """Extract from: {text}

JSON output:
{{
  "client_name": null,
  "company_name": null,
  "email": null,
  "phone_numbers": [{{"number": "phone", "extension": null, "type": "primary"}}],
  "address": {{"unit": null, "street": "street", "city": "city", "state": "state", "postal_code": "zip", "country": "USA"}},
  "notes": "other text"
}}"""