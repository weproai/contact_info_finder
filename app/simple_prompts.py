EXTRACTION_PROMPT = """Extract: {text}

JSON:
{{
  "client_name": "name",
  "company_name": "company",
  "email": "email",
  "phone_numbers": [{{"number": "phone", "extension": "ext", "type": "primary"}}],
  "address": {{"unit": null, "street": "street", "city": "city", "state": "state", "postal_code": "zip", "country": "USA"}},
  "notes": "other"
}}"""