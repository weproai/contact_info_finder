from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime


class PhoneNumber(BaseModel):
    number: str
    extension: Optional[str] = None
    type: str = "primary"  # primary, secondary, mobile, work, etc.
    
    @validator('number')
    def validate_phone(cls, v):
        # Basic phone validation - can be enhanced with phonenumbers library
        import re
        # Remove all non-numeric characters except + for international
        cleaned = re.sub(r'[^\d+]', '', v)
        if len(cleaned) < 10:
            raise ValueError('Phone number too short')
        return v


class Address(BaseModel):
    unit: Optional[str] = None  # Apartment, suite, floor
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class ExtractedContact(BaseModel):
    client_name: Optional[str] = None
    company_name: Optional[str] = None
    phone_numbers: List[PhoneNumber] = Field(default_factory=list)
    email: Optional[EmailStr] = None
    address: Optional[Address] = None
    notes: Optional[str] = None  # Additional information/notes
    raw_text: str
    extracted_at: datetime = Field(default_factory=datetime.now)


class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text containing contact information")
    use_cache: bool = True
    
    @validator('text')
    def clean_text(cls, v):
        # Remove excessive whitespace
        return ' '.join(v.split())


class ExtractionResponse(BaseModel):
    success: bool
    status: str = "not_found"  # "found" or "not_found"
    data: Optional[ExtractedContact] = None
    error: Optional[str] = None
    processing_time: float
    cache_hit: bool = False


class HealthResponse(BaseModel):
    status: str
    ollama_status: str
    chromadb_status: str
    timestamp: datetime