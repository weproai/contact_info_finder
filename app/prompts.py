EXTRACTION_PROMPT = """Extract contact information from this text: {text}

Instructions:
1. Extract phone numbers (ONLY 10-digit sequences like 2392184565, not street numbers)
2. Extract addresses (street like "13567 Little Gem Cir", city, state, zip)
3. Extract names and emails if present
4. Put EVERYTHING ELSE in notes field (job references, service details, problems, times, etc.)

IMPORTANT: Phone numbers are 10 consecutive digits. Don't combine street numbers with phone numbers.

Rule: Extract actual values from the input text, not examples.
For notes: Include ALL text that isn't a phone number, address, or email. This includes:
- Job references (like "JOBS FOR TOMORROW")
- Service types (like "American garage door")  
- Problems/issues (like "keypad not working")
- Time windows (like "8-10AM")
Don't truncate the notes - include everything that doesn't fit in other fields.

Return this JSON with actual values:
{{
  "client_name": null,
  "company_name": null,
  "email": null,
  "phone_numbers": [{{"number": "actual phone number", "extension": null, "type": "primary"}}],
  "address": {{
    "unit": null,
    "street": "actual street",
    "city": "actual city",
    "state": "actual state", 
    "postal_code": "actual zip",
    "country": "USA"
  }},
  "notes": "copy all remaining text here"
}}"""

VALIDATION_PROMPT = """Rate confidence (0.0-1.0):
{extraction}

Return only:
{{"client_name": 0.9, "company_name": 0.9, "phone_numbers": 0.9, "email": 0.9, "address": 0.9}}"""