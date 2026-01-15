import re
import phonenumbers
from typing import Optional, Dict, List
from email_validator import validate_email, EmailNotValidError


class ContactValidator:
    """Validate and clean contact information"""
    
    # US state abbreviations
    US_STATES = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming'
    }
    
    @staticmethod
    def validate_phone(phone: str, country: str = "US") -> Optional[str]:
        """Validate and format phone number"""
        try:
            parsed = phonenumbers.parse(phone, country)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            return None
        except phonenumbers.NumberParseException:
            # Try basic validation
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 10:
                return phone  # Return original if has enough digits
            return None
    
    @staticmethod
    def validate_email(email: str) -> Optional[str]:
        """Validate email address"""
        try:
            validated = validate_email(email)
            return validated.email
        except EmailNotValidError:
            return None
    
    @staticmethod
    def validate_postal_code(postal_code: str, country: str = "US") -> Optional[str]:
        """Validate postal/zip code"""
        if not postal_code:
            return None
        
        postal_code = postal_code.strip()
        
        if country == "US":
            # US ZIP code: 5 digits or 5+4 format
            if re.match(r'^\d{5}(-\d{4})?$', postal_code):
                return postal_code
        elif country == "CA":
            # Canadian postal code
            if re.match(r'^[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d$', postal_code):
                return postal_code.upper()
        else:
            # Generic validation - at least some alphanumeric characters
            if re.match(r'^[A-Za-z0-9\s-]{3,10}$', postal_code):
                return postal_code
        
        return None
    
    @staticmethod
    def normalize_state(state: str) -> Optional[str]:
        """Normalize state name or abbreviation"""
        if not state:
            return None
        
        state = state.strip().upper()
        
        # Check if it's already a valid abbreviation
        if state in ContactValidator.US_STATES:
            return state
        
        # Check if it's a full state name
        for abbr, name in ContactValidator.US_STATES.items():
            if name.upper() == state:
                return abbr
        
        # Return original if not found (might be international)
        return state
    
    @staticmethod
    def extract_extension(phone_str: str) -> tuple[str, Optional[str]]:
        """Extract phone number and extension"""
        # Common extension patterns
        ext_patterns = [
            r'(?:ext|extension|x|#)\.?\s*(\d+)',
            r',\s*(\d+)$',
            r'\s+(\d{1,6})$'  # Trailing short number might be extension
        ]
        
        for pattern in ext_patterns:
            match = re.search(pattern, phone_str, re.IGNORECASE)
            if match:
                extension = match.group(1)
                phone = phone_str[:match.start()].strip()
                return phone, extension
        
        return phone_str, None
    
    @staticmethod
    def parse_address_line(address_line: str) -> Dict[str, Optional[str]]:
        """Parse a single address line into components"""
        unit_patterns = [
            r'(?:apt|apartment|suite|ste|unit|#)\s*(\w+)',
            r'(\d+)(?:st|nd|rd|th)\s+floor',
            r'floor\s*(\d+)'
        ]
        
        unit = None
        street = address_line
        
        for pattern in unit_patterns:
            match = re.search(pattern, address_line, re.IGNORECASE)
            if match:
                unit = match.group(0)
                # Remove unit from street address
                street = address_line.replace(match.group(0), '').strip()
                # Clean up any double spaces
                street = ' '.join(street.split())
                break
        
        return {
            'unit': unit,
            'street': street
        }