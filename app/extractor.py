import ollama
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
import phonenumbers
from app.config import settings
from app.models import ExtractedContact, PhoneNumber, Address
from app.simple_prompts import EXTRACTION_PROMPT, VALIDATION_PROMPT
from app.database import chroma_manager
from app.fast_extractor import FastExtractor

logger = logging.getLogger(__name__)


class ContactExtractor:
    def __init__(self):
        self.ollama_client = ollama.Client(host=settings.ollama_base_url)
        self.model = settings.ollama_model
    
    def extract(self, text: str, use_cache: bool = True) -> Tuple[Optional[ExtractedContact], bool]:
        """Extract contact information from text"""
        cache_hit = False
        
        # Try fast extraction first for simple cases
        if settings.enable_fast_mode and FastExtractor.can_extract_fast(text):
            logger.info("Using fast regex extraction")
            fast_result = FastExtractor.extract_fast(text)
            if fast_result:
                # For better accuracy, enhance with LLM if available and fast result is incomplete
                if (self.health_check() and 
                    (not fast_result.address or 
                     not fast_result.address.city or 
                     not fast_result.address.state)):
                    logger.info("Enhancing fast extraction with LLM")
                    # Use LLM to enhance the extraction
                    # But keep it fast by using a focused prompt
                else:
                    # Store in cache for consistency
                    if use_cache:
                        chroma_manager.add_extraction(text, fast_result)
                    return fast_result, cache_hit
        
        # Check if Ollama is available
        if not self.health_check():
            logger.error("Ollama is not running or accessible")
            # Fall back to fast extraction even for complex cases
            fast_result = FastExtractor.extract_fast(text)
            return fast_result, cache_hit
        
        # Check cache first if enabled
        if use_cache:
            similar = chroma_manager.find_similar(text, n_results=1)
            if similar and similar[0].get('distance', 1.0) < 0.1:  # Very similar text
                logger.info("Cache hit - returning previous extraction")
                cache_hit = True
                extraction_data = similar[0]['extraction']
                return ExtractedContact(**extraction_data), cache_hit
        
        # Extract using Ollama
        try:
            extraction_json = self._extract_with_llm(text)
            if not extraction_json:
                return None, cache_hit
            
            # Parse and validate extraction
            contact = self._parse_extraction(extraction_json, text)
            
            # Post-process: Fix phone numbers and check if we missed any
            import re
            
            # Fix phone numbers that might have extra digits
            fixed_phones = []
            for phone in contact.phone_numbers:
                # Extract just 10-digit phone numbers from the phone field
                phone_matches = re.findall(r'\b(\d{10})\b', phone.number.replace('-', '').replace(' ', ''))
                for match in phone_matches:
                    if len(match) == 10:  # Valid phone number
                        fixed_phone = PhoneNumber(
                            number=self._normalize_phone(match),
                            extension=phone.extension,
                            type=phone.type
                        )
                        fixed_phones.append(fixed_phone)
                        break
            
            # If we fixed any phones, use the fixed list
            if fixed_phones:
                contact.phone_numbers = fixed_phones
            
            # If still no phones, search the original text
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
            
            # Confidence scores removed for performance
            
            # Store in database
            chroma_manager.add_extraction(text, contact)
            
            return contact, cache_hit
            
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            logger.error(f"Full traceback: ", exc_info=True)
            return None, cache_hit
    
    def _extract_with_llm(self, text: str) -> Optional[Dict]:
        """Use Ollama to extract information with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                prompt = EXTRACTION_PROMPT.format(text=text)
                
                response = self.ollama_client.chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You MUST return ONLY valid JSON for contact extraction. No explanations, no code.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    options={
                        'temperature': 0.1,  # Low temperature for consistent output
                        'top_p': 0.9,
                        'seed': 42  # For more consistent results
                    }
                )
            
                # Extract JSON from response
                response_text = response['message']['content']
                logger.info(f"LLM Response (attempt {attempt + 1}): {response_text[:500]}...")
                
                # Try to find JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    
                    # Fix common JSON issues from LLM
                    json_str = json_str.replace('"postaL_code"', '"postal_code"')
                    json_str = json_str.replace('"postalCode"', '"postal_code"')
                    json_str = json_str.replace('"ext or null"', 'null')
                    json_str = json_str.replace('"null"', 'null')  # Fix quoted null
                    
                    try:
                        result = json.loads(json_str)
                        logger.info(f"Successfully extracted JSON on attempt {attempt + 1}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
                        if attempt == max_retries - 1:
                            logger.error(f"Failed to parse JSON after {max_retries} attempts")
                            return None
                        continue
                else:
                    logger.warning(f"No JSON found in response on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        logger.error(f"No valid JSON found after {max_retries} attempts")
                        return None
                    continue
            
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
        """Check if Ollama is accessible"""
        try:
            self.ollama_client.list()
            return True
        except Exception:
            return False


# Singleton instance
extractor = ContactExtractor()