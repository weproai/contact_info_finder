import re
from typing import Optional, Dict, List
from app.models import ExtractedContact, PhoneNumber, Address
import logging

logger = logging.getLogger(__name__)


class FastExtractor:
    """Ultra-fast regex-based extractor for simple cases"""
    
    @staticmethod
    def can_extract_fast(text: str) -> bool:
        """Check if text is simple enough for fast extraction"""
        # More aggressive fast mode - try regex first for most texts
        # Check if text has any phone-like pattern
        return len(text) < 1000 and bool(re.search(r'\d{3,}', text))
    
    @staticmethod
    def extract_fast(text: str) -> Optional[ExtractedContact]:
        """Fast extraction using regex only - millisecond performance"""
        try:
            # Extract phone numbers (10-50ms)
            phone_pattern = r'\b(\d{10})\b|\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b'
            phone_matches = re.findall(phone_pattern, text)
            
            phone_numbers = []
            for match in phone_matches:
                if match[0]:  # 10-digit format
                    phone = match[0]
                else:  # formatted
                    phone = f"{match[1]}{match[2]}{match[3]}"
                
                phone_numbers.append(PhoneNumber(
                    number=phone,
                    extension=None,
                    type='primary'
                ))
            
            # Extract email (5-10ms)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, text)
            email = email_match.group(0) if email_match else None
            
            # Extract address components (20-40ms)
            # Look for state + zip pattern first (more reliable)
            state_zip_pattern = r'\b([A-Za-z\s]+),\s*([A-Z]{2}|[A-Za-z]+)\s+(\d{5})(?:-\d{4})?\b'
            state_zip_match = re.search(state_zip_pattern, text)
            
            if state_zip_match:
                city = state_zip_match.group(1).strip()
                state = state_zip_match.group(2).strip()
                postal_code = state_zip_match.group(3)
            else:
                # Fallback patterns
                zip_pattern = r'\b(\d{5})(?:-\d{4})?\b'
                zip_matches = re.findall(zip_pattern, text)
                # Take the last 5-digit number (more likely to be zip than street number)
                postal_code = zip_matches[-1] if zip_matches else None
                
                # State pattern - look for common state names or abbreviations
                state_pattern = r'\b(FL|Florida|CA|California|NY|New York|TX|Texas|[A-Z]{2})\b'
                state_match = re.search(state_pattern, text, re.IGNORECASE)
                state = state_match.group(1) if state_match else None
                
                # City - word(s) before state
                city = None
                if state:
                    city_pattern = r'\b([A-Za-z]+(?:\s+[A-Za-z]+)*),?\s+' + re.escape(state)
                    city_match = re.search(city_pattern, text)
                    city = city_match.group(1) if city_match else None
            
            # Street address (number + street name)
            street_pattern = r'\b(\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Cir|Circle|Ln|Lane|Way|Court|Ct|Place|Pl))\b'
            street_match = re.search(street_pattern, text, re.IGNORECASE)
            street = street_match.group(1) if street_match else None
            
            # Build address if we have components
            address = None
            if any([street, city, state, postal_code]):
                address = Address(
                    street=street,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country="USA" if state else None
                )
            
            # Extract name (first capitalized words before phone/email)
            name_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            name_match = re.search(name_pattern, text)
            client_name = name_match.group(1) if name_match else None
            
            # Everything else goes to notes
            notes = text
            # Remove extracted components
            for phone in phone_numbers:
                notes = re.sub(r'\b' + phone.number + r'\b', '', notes)
            if email:
                notes = notes.replace(email, '')
            if address and address.street:
                notes = notes.replace(address.street, '')
            # Clean up
            notes = re.sub(r'\s+', ' ', notes).strip()
            
            return ExtractedContact(
                client_name=client_name,
                company_name=None,
                phone_numbers=phone_numbers,
                email=email,
                address=address,
                notes=notes if notes else None,
                raw_text=text,
                confidence_scores={
                    "client_name": 0.7,
                    "company_name": 0.5,
                    "phone_numbers": 0.9,
                    "email": 0.9,
                    "address": 0.8
                }
            )
            
        except Exception as e:
            logger.error(f"Fast extraction failed: {e}")
            return None