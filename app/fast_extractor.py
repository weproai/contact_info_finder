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
        # Use fast mode for most texts with clear patterns
        has_phone = bool(re.search(r'\+?\d{10,}|\(\d{3}\)|\d{3}[-.\s]\d{3}[-.\s]\d{4}', text))
        has_structured_format = bool(re.search(r'(Customer|Contact|Name|Phone|Address|Email):', text, re.IGNORECASE))
        
        # Use fast mode if it has phone numbers or structured format
        return len(text) < 1500 and (has_phone or has_structured_format)
    
    @staticmethod
    def extract_fast(text: str) -> Optional[ExtractedContact]:
        """Fast extraction using regex only - millisecond performance"""
        try:
            # Extract phone numbers with extensions (10-50ms)
            phone_ext_pattern = r'(\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\s*(?:ext\.?|extension|x)\s*(\d+)'
            phone_pattern = r'\+?1?(\d{10})\b|\b(\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b'
            
            phone_numbers = []
            
            # First check for phones with extensions
            ext_matches = re.findall(phone_ext_pattern, text, re.IGNORECASE)
            for phone_match, ext in ext_matches:
                # Clean phone number
                phone_clean = re.sub(r'[^\d]', '', phone_match)
                phone_numbers.append(PhoneNumber(
                    number=phone_clean,
                    extension=ext,
                    type='primary'
                ))
            
            # Then find phones without extensions (if no extension matches found)
            if not ext_matches:
                phone_matches = re.findall(phone_pattern, text)
                for match in phone_matches:
                    if match[0]:  # 10-digit format
                        phone = match[0]
                    else:  # formatted
                        phone = re.sub(r'[^\d]', '', match[1])
                    
                    if phone and len(phone) >= 10:
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
            # First try "Address: " pattern
            if 'Address:' in text:
                addr_section = text.split('Address:')[1].split('Service:')[0] if 'Service:' in text else text.split('Address:')[1]
                # Extract zip first (most reliable)
                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', addr_section)
                postal_code = zip_match.group(1) if zip_match else None
                
                # Extract state (before zip)
                state_match = re.search(r'\b(FL|Florida|CA|California|NY|New York|TX|Texas|[A-Z]{2})\b', addr_section, re.IGNORECASE)
                state = state_match.group(1) if state_match else None
                if state and len(state) > 2:
                    # Convert full state names to abbreviations
                    state_map = {'Florida': 'FL', 'California': 'CA', 'New York': 'NY', 'Texas': 'TX'}
                    state = state_map.get(state.title(), state[:2].upper())
                
                # Extract city (word before state)
                if state_match:
                    # Get text before state
                    before_state = addr_section[:state_match.start()].strip()
                    # City is usually the last word(s) before state
                    city_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$', before_state)
                    city = city_match.group(1) if city_match else None
                else:
                    city = None
            else:
                # Fallback: Look for city, state zip pattern
                address_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?\b'
                address_match = re.search(address_pattern, text)
                
                if address_match:
                    city = address_match.group(1).strip()
                    state = address_match.group(2).strip()
                    postal_code = address_match.group(3)
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
            
            # Extract unit/suite (include the label)
            unit_pattern = r'((?:Suite|Unit|Apt|Apartment|#)\s*\d+\w*)'
            unit_match = re.search(unit_pattern, text, re.IGNORECASE)
            unit = unit_match.group(1).strip() if unit_match else None
            
            # Street address (number + street name)
            if 'Address:' in text:
                # Extract from Address: section
                addr_section = text.split('Address:')[1].split('Service:')[0] if 'Service:' in text else text.split('Address:')[1]
                street_pattern = r'\b(\d+\s+[A-Za-z\s]+?)(?:\s+(?:' + (city or 'NoCity') + ')|$)'
                street_match = re.search(street_pattern, addr_section)
                street = street_match.group(1).strip() if street_match else None
            else:
                # Standard pattern
                street_pattern = r'\b(\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Cir|Circle|Ln|Lane|Way|Court|Ct|Place|Pl))\b'
                street_match = re.search(street_pattern, text, re.IGNORECASE)
                street = street_match.group(1) if street_match else None
            
            # Build address if we have components
            address = None
            if any([street, city, state, postal_code]):
                address = Address(
                    unit=unit,
                    street=street,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country="USA" if state else None
                )
            
            # Extract name and company
            client_name = None
            company_name = None
            
            # Pattern 1: "Customer: NAME" or "Client: NAME"
            customer_pattern = r'(?:Customer|Client):\s*([A-Z][A-Z\s]+?)(?:\s+Phone:|$)'
            customer_match = re.search(customer_pattern, text)
            if customer_match:
                client_name = customer_match.group(1).strip()
            
            # Pattern 2: "Contact NAME at COMPANY"
            if not client_name:
                contact_pattern = r'Contact\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+at\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)'
                contact_match = re.search(contact_pattern, text)
                if contact_match:
                    client_name = contact_match.group(1)
                    company_name = contact_match.group(2)
            
            # Build notes - only include unextracted information
            notes_parts = []
            remaining_text = text
            
            # Remove all extracted components
            if client_name and company_name:
                remaining_text = remaining_text.replace(f"Contact {client_name} at {company_name}", "", 1)
            elif client_name:
                remaining_text = remaining_text.replace(f"Contact {client_name}", "", 1)
            
            # Remove phone numbers with their labels
            for phone in phone_numbers:
                # Remove various phone formats and labels
                phone_patterns = [
                    rf'Phone:\s*\(?\d{{3}}\)?[-.\s]?\d{{3}}[-.\s]?\d{{4}}\s*(?:ext\.?\s*\d+)?',
                    rf'\(?\d{{3}}\)?[-.\s]?\d{{3}}[-.\s]?\d{{4}}\s*(?:ext\.?\s*\d+)?',
                ]
                for pattern in phone_patterns:
                    remaining_text = re.sub(pattern, '', remaining_text, count=1, flags=re.IGNORECASE)
            
            # Remove email with label
            if email:
                remaining_text = re.sub(rf'email:\s*{re.escape(email)}', '', remaining_text, flags=re.IGNORECASE)
                remaining_text = remaining_text.replace(email, '')
            
            # Remove address components with labels
            if address:
                # Remove "Office:" or "Address:" labels
                remaining_text = re.sub(r'(?:Office|Address):\s*', '', remaining_text, flags=re.IGNORECASE)
                # Remove unit if extracted
                if address.unit:
                    remaining_text = remaining_text.replace(address.unit + ',', '')
                    remaining_text = remaining_text.replace(address.unit, '')
                if address.street:
                    remaining_text = remaining_text.replace(address.street, '')
                if address.city and address.state and address.postal_code:
                    remaining_text = remaining_text.replace(f"{address.city}, {address.state} {address.postal_code}", '')
            
            # Clean up remaining text
            remaining_text = re.sub(r'[,\s]+', ' ', remaining_text).strip()
            remaining_text = re.sub(r'^[:\.\s,]+|[:\.\s,]+$', '', remaining_text).strip()
            
            # Only set notes if there's actual content left
            notes = remaining_text if remaining_text and len(remaining_text) > 2 else None
            
            return ExtractedContact(
                client_name=client_name,
                company_name=company_name,
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