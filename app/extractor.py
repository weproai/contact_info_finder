import json
import logging
import re
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import ollama
import phonenumbers
from openai import OpenAI

from app.cache_store import local_cache
from app.config import settings
from app.database import chroma_manager
from app.fast_extractor import FastExtractor
from app.models import Address, ExtractedContact, PhoneNumber
from app.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class ContactExtractor:
    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.openai_model if self.provider == "openai" else settings.ollama_model
        self.openai_client = None
        self.ollama_client = None

        if self.provider == "openai" and settings.openai_api_key:
            self.openai_client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout_seconds,
            )
        else:
            self.ollama_client = ollama.Client(host=settings.ollama_base_url)
    
    def extract(self, text: str, use_cache: bool = True) -> Tuple[Optional[ExtractedContact], bool]:
        """Extract contact information from text"""
        cache_hit = False
        fast_result = None

        # Try fast extraction first.
        if settings.enable_fast_mode and FastExtractor.can_extract_fast(text):
            logger.info("Using fast regex extraction")
            fast_result = FastExtractor.extract_fast(text)
            if fast_result and self._can_serve(fast_result):
                if use_cache:
                    self._store_cached_result(text, fast_result)
                return fast_result, cache_hit

        # Then try local memory / exact cache.
        if use_cache:
            cached = local_cache.get(text)
            if cached:
                logger.info("Local cache hit - returning previous extraction")
                cache_hit = True
                return ExtractedContact(**cached), cache_hit

        if not settings.llm_enabled:
            logger.warning("LLM fallback is disabled")
            return fast_result, cache_hit

        # Only then call the configured provider.
        if not self.health_check():
            logger.error("%s is not accessible", self.provider_name())
            return fast_result, cache_hit

        try:
            extraction_json = self._extract_with_provider(text)
            if not extraction_json:
                return fast_result, cache_hit

            contact = self._parse_extraction(extraction_json, text)
            contact = self._merge_contacts(fast_result, contact)
            contact = self._post_process_contact(contact, text)

            if use_cache and contact and self._can_serve(contact):
                self._store_cached_result(text, contact)

            return contact, cache_hit
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            logger.error(f"Full traceback: ", exc_info=True)
            return None, cache_hit
    
    def provider_name(self) -> str:
        return "OpenAI" if self.provider == "openai" else "Ollama"

    def provider_status(self) -> str:
        if not settings.llm_enabled:
            return "disabled"
        if self.provider == "openai":
            return "healthy" if bool(settings.openai_api_key) else "unhealthy"
        return "healthy" if self.health_check() else "unhealthy"

    def unavailable_error_message(self) -> str:
        if not settings.llm_enabled:
            return "LLM fallback is disabled."
        if self.provider == "openai":
            return "OpenAI is not configured. Please set OPENAI_API_KEY."
        return "Ollama is not running. Please start Ollama with: ollama serve"

    def _store_cached_result(self, text: str, extraction: ExtractedContact):
        local_cache.set(text, extraction, self.provider, self.model)
        chroma_manager.add_extraction(text, extraction)

    def _extract_with_provider(self, text: str) -> Optional[Dict]:
        if self.provider == "openai":
            return self._extract_with_openai(text)
        return self._extract_with_ollama(text)

    def _extract_with_openai(self, text: str) -> Optional[Dict]:
        """Use OpenAI to extract information with retry logic."""
        if not self.openai_client:
            logger.error("OpenAI client is not configured")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                prompt = self._build_prompt(text)
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Extract contact information from the user text. "
                                "Return a single valid JSON object only. "
                                "Do not return markdown, backticks, code, comments, or explanations."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=256,
                )
                response_text = (response.choices[0].message.content or "").strip()
                logger.info(f"OpenAI response (attempt {attempt + 1}): {response_text[:500]}...")
                result = self._parse_json_response(response_text)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"OpenAI extraction error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts")
                    return None
        return None

    def _extract_with_ollama(self, text: str) -> Optional[Dict]:
        """Use Ollama to extract information with retry logic."""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                prompt = self._build_prompt(text)

                response = self.ollama_client.chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'system',
                            'content': (
                                'Extract contact information from the user text. '
                                'Return a single valid JSON object only. '
                                'Do not return markdown, backticks, Python code, '
                                'comments, or explanations.'
                            )
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    format='json',
                    options={
                        'temperature': 0.0,
                        'top_p': 0.1,
                        'num_predict': 256,
                        'num_ctx': 1024,
                        'num_thread': 4,
                        'repeat_penalty': 1.0,
                        'seed': 42
                    }
                )
            
                response_text = response['message']['content'].strip()
                logger.info(f"Ollama response (attempt {attempt + 1}): {response_text[:500]}...")
                result = self._parse_json_response(response_text)
                if result is not None:
                    return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return None
            except Exception as e:
                logger.error(f"LLM extraction error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts")
                    return None
                continue
        
        return None

    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt with current date context."""
        return EXTRACTION_PROMPT.format(
            text=text,
            today=date.today().isoformat(),
        )

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        json_str = response_text.strip()

        if not json_str.startswith('{'):
            json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group()

        json_str = json_str.replace('"postaL_code"', '"postal_code"')
        json_str = json_str.replace('"postalCode"', '"postal_code"')
        json_str = json_str.replace('"ext or null"', 'null')
        json_str = json_str.replace('"null"', 'null')

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            return None

    def _merge_contacts(
        self,
        regex_contact: Optional[ExtractedContact],
        llm_contact: Optional[ExtractedContact],
    ) -> Optional[ExtractedContact]:
        if regex_contact and not llm_contact:
            return regex_contact
        if llm_contact and not regex_contact:
            return llm_contact
        if not regex_contact and not llm_contact:
            return None

        regex_address = regex_contact.address if regex_contact else None
        llm_address = llm_contact.address if llm_contact else None
        merged_address = None
        if regex_address or llm_address:
            merged_address = Address(
                unit=(regex_address.unit if regex_address else None) or (llm_address.unit if llm_address else None),
                street=(regex_address.street if regex_address else None) or (llm_address.street if llm_address else None),
                city=(regex_address.city if regex_address else None) or (llm_address.city if llm_address else None),
                state=(regex_address.state if regex_address else None) or (llm_address.state if llm_address else None),
                postal_code=(regex_address.postal_code if regex_address else None) or (llm_address.postal_code if llm_address else None),
                country=(regex_address.country if regex_address else None) or (llm_address.country if llm_address else None),
            )

        return ExtractedContact(
            client_name=(regex_contact.client_name if regex_contact else None) or (llm_contact.client_name if llm_contact else None),
            company_name=(regex_contact.company_name if regex_contact else None) or (llm_contact.company_name if llm_contact else None),
            phone_numbers=(regex_contact.phone_numbers if regex_contact and regex_contact.phone_numbers else llm_contact.phone_numbers),
            email=(regex_contact.email if regex_contact else None) or (llm_contact.email if llm_contact else None),
            address=merged_address,
            notes=(regex_contact.notes if regex_contact else None) or (llm_contact.notes if llm_contact else None),
            raw_text=llm_contact.raw_text if llm_contact else regex_contact.raw_text,
        )

    def _post_process_contact(self, contact: ExtractedContact, text: str) -> ExtractedContact:
        fixed_phones = []
        for phone in contact.phone_numbers:
            phone_matches = re.findall(r'\b(\d{10})\b', phone.number.replace('-', '').replace(' ', ''))
            for match in phone_matches:
                if len(match) == 10:
                    fixed_phone = PhoneNumber(
                        number=self._normalize_phone(match),
                        extension=phone.extension,
                        type=phone.type
                    )
                    fixed_phones.append(fixed_phone)
                    break

        if fixed_phones:
            contact.phone_numbers = fixed_phones

        if len(contact.phone_numbers) == 0:
            phone_pattern = r'\b(\d{10})\b|\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b'
            phone_matches = re.findall(phone_pattern, text)
            for match in phone_matches:
                phone_num = match[0] if match[0] else match[1]
                if phone_num and len(phone_num.replace('-', '').replace(' ', '')) >= 10:
                    phone = PhoneNumber(
                        number=self._normalize_phone(phone_num),
                        extension=None,
                        type='primary'
                    )
                    contact.phone_numbers.append(phone)
                    logger.info(f"Post-processing found phone number: {phone_num}")

        return contact

    def _can_serve(self, contact: Optional[ExtractedContact]) -> bool:
        if not contact:
            return False
        return bool(
            contact.client_name
            or contact.company_name
            or contact.email
            or contact.phone_numbers
            or (contact.address and any([
                contact.address.street,
                contact.address.city,
                contact.address.state,
                contact.address.postal_code,
            ]))
        )
    
    def _parse_extraction(self, extraction_data: Dict, raw_text: str) -> ExtractedContact:
        """Parse and validate extracted data"""
        # Parse phone numbers
        phone_numbers = []
        if extraction_data.get('phone_numbers'):
            for phone_data in extraction_data['phone_numbers']:
                if isinstance(phone_data, dict) and phone_data.get('number'):
                    try:
                        # Extract extension from phone number if included
                        phone_num = phone_data['number']
                        extension = phone_data.get('extension')
                        
                        # If extension is in the phone number, extract it
                        if 'ext' in phone_num.lower() or 'x' in phone_num:
                            phone_num, extracted_ext = self._extract_extension(phone_num)
                            if not extension or extension == "ext or null":
                                extension = extracted_ext
                        
                        phone = PhoneNumber(
                            number=self._normalize_phone(phone_num),
                            extension=extension if extension != "ext or null" else None,
                            type=phone_data.get('type', 'primary')
                        )
                        phone_numbers.append(phone)
                    except Exception as e:
                        logger.error(f"Error parsing phone number: {e}, data: {phone_data}")
                elif isinstance(phone_data, str):
                    # Handle case where phone number is just a string
                    try:
                        phone = PhoneNumber(
                            number=self._normalize_phone(phone_data),
                            extension=None,
                            type='primary'
                        )
                        phone_numbers.append(phone)
                    except Exception as e:
                        logger.error(f"Error parsing phone string: {e}, data: {phone_data}")
        
        # Parse address
        address = None
        if extraction_data.get('address') and isinstance(extraction_data['address'], dict):
            addr_data = extraction_data['address']
            address = Address(
                unit=addr_data.get('unit'),
                street=addr_data.get('street'),
                city=addr_data.get('city'),
                state=addr_data.get('state'),
                postal_code=addr_data.get('postal_code'),
                country=addr_data.get('country')
            )
        
        # Clean up "not provided" or similar values
        client_name = extraction_data.get('client_name')
        if client_name and isinstance(client_name, str) and 'not provided' in client_name.lower():
            client_name = None
            
        company_name = extraction_data.get('company_name')
        if company_name and isinstance(company_name, str) and 'not provided' in company_name.lower():
            company_name = None
            
        email = extraction_data.get('email')
        if email and isinstance(email, str) and ('not provided' in email.lower() or '@' not in email):
            email = None

        job_type = extraction_data.get('job_type')
        if job_type and isinstance(job_type, str):
            job_type = job_type.strip().lower()
        if not job_type:
            job_type = None

        scheduled_date = extraction_data.get('scheduled_date')
        if scheduled_date and isinstance(scheduled_date, str):
            scheduled_date = scheduled_date.strip()
        if scheduled_date:
            lowered_date = scheduled_date.lower()
            if lowered_date == "today":
                scheduled_date = date.today().isoformat()
            elif lowered_date == "tomorrow":
                scheduled_date = (date.today() + timedelta(days=1)).isoformat()
        if not scheduled_date:
            scheduled_date = None

        appointment_time = (
            extraction_data.get('appointment_time')
            or extraction_data.get('time_window')
        )
        if appointment_time and isinstance(appointment_time, str):
            appointment_time = appointment_time.strip()
        if not appointment_time:
            appointment_time = None
        
        # Extract notes if present
        notes = extraction_data.get('notes')
        if notes and isinstance(notes, str):
            if 'not provided' in notes.lower():
                notes = None
            else:
                # Remove already extracted information from notes
                import re
                
                # Remove phone numbers that were already extracted
                for phone in phone_numbers:
                    if phone.number:
                        # Remove various formats of the phone number from notes
                        clean_number = re.sub(r'[^\d]', '', phone.number)  # Just digits
                        if len(clean_number) >= 10:
                            # Remove the exact number that appears in the text
                            notes = re.sub(r'\b' + clean_number[-10:] + r'\b', '', notes)
                
                # Remove address components that were already extracted
                if address:
                    if address.street:
                        notes = notes.replace(address.street, '')
                    if address.city:
                        notes = notes.replace(address.city, '')
                    if address.state:
                        notes = notes.replace(address.state, '')
                    if address.postal_code:
                        notes = notes.replace(str(address.postal_code), '')
                
                # Clean up extra spaces and commas
                notes = re.sub(r'\s+', ' ', notes)
                notes = re.sub(r',\s*,', ',', notes)
                notes = re.sub(r',\s*$', '', notes)
                notes = notes.strip()
                
                # If notes is empty after cleanup, set to None
                if not notes or notes == ',':
                    notes = None
            
        return ExtractedContact(
            client_name=client_name,
            company_name=company_name,
            phone_numbers=phone_numbers,
            email=email,
            address=address,
            job_type=job_type,
            scheduled_date=scheduled_date,
            appointment_time=appointment_time,
            notes=notes,
            raw_text=raw_text
        )
    
    def _extract_extension(self, phone_str: str) -> tuple[str, Optional[str]]:
        """Extract phone number and extension"""
        # Common extension patterns
        import re
        ext_patterns = [
            r'(?:ext|extension|x)\.?\s*(\d+)',
            r',\s*(\d+)$'
        ]
        
        for pattern in ext_patterns:
            match = re.search(pattern, phone_str, re.IGNORECASE)
            if match:
                extension = match.group(1)
                phone = phone_str[:match.start()].strip()
                return phone, extension
        
        return phone_str, None
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format"""
        try:
            # Try to parse with phonenumbers library
            # Assume US if no country code
            parsed = phonenumbers.parse(phone, "US")
            if phonenumbers.is_valid_number(parsed):
                # Format as international
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            pass
        
        # Fallback: basic cleaning
        cleaned = re.sub(r'[^\d+\-\(\)\s]', '', phone)
        return cleaned.strip()
    
    
    def health_check(self) -> bool:
        """Check if the selected provider is accessible."""
        if not settings.llm_enabled:
            return False

        if self.provider == "openai":
            return bool(settings.openai_api_key)

        try:
            self.ollama_client.list()
            return True
        except Exception:
            return False


# Singleton instance
extractor = ContactExtractor()