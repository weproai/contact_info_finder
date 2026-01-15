EXTRACTION_PROMPT = """Extract contact from text: {text}

Return JSON only:
{{
  "client_name": "<actual name>",
  "company_name": "<actual company>",
  "email": "<actual email>",
  "phone_numbers": [{{"number": "<digits only>", "extension": null, "type": "primary"}}],
  "address": {{"unit": null, "street": "<number and street>", "city": "<city>", "state": "<state>", "postal_code": "<zip>", "country": "USA"}},
  "notes": "<other info>"
}}

Example: Customer: John Doe Phone: 5551234567 Address: 123 Main St Miami FL 33101
Output: {{"client_name": "John Doe", "phone_numbers": [{{"number": "5551234567"}}], "address": {{"street": "123 Main St", "city": "Miami", "state": "FL", "postal_code": "33101"}}}}"""