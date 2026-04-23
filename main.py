from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from datetime import datetime
from app.cache_store import local_cache
from app.config import settings
from app.models import ExtractionRequest, ExtractionResponse, HealthResponse
from app.extractor import extractor
from app.database import chroma_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Contact Info Finder API",
    description="Extract contact information from unstructured text using LLM",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Contact Info Finder API...")

    # Check selected LLM provider.
    if not extractor.health_check():
        logger.warning("%s is not accessible.", extractor.provider_name())

    # Check ChromaDB.
    if not chroma_manager.health_check():
        logger.warning("ChromaDB initialization failed.")

    logger.info("API startup complete")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Contact Info Finder API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check health status of all services"""
    llm_status = extractor.provider_status()
    ollama_status = "healthy" if settings.llm_provider == "ollama" and extractor.health_check() else (
        "disabled" if settings.llm_provider != "ollama" else "unhealthy"
    )
    chromadb_status = "healthy" if chroma_manager.health_check() else (
        "disabled" if chroma_manager.disabled_reason else "unhealthy"
    )
    cache_stats = local_cache.get_stats()
    local_cache_status = "healthy" if cache_stats["enabled"] else "disabled"

    overall_status = (
        "healthy"
        if llm_status == "healthy" and chromadb_status in {"healthy", "disabled"}
        else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        ollama_status=ollama_status,
        chromadb_status=chromadb_status,
        llm_provider=settings.llm_provider,
        llm_status=llm_status,
        local_cache_status=local_cache_status,
        timestamp=datetime.now()
    )


@app.post("/extract", response_model=ExtractionResponse, tags=["Extraction"])
async def extract_contact_info(request: ExtractionRequest):
    """
    Extract contact information from text
    
    This endpoint analyzes unstructured text and extracts:
    - Client name
    - Company name
    - Phone numbers (with extensions)
    - Email addresses
    - Physical addresses
    """
    start_time = time.time()
    
    try:
        # Perform extraction
        contact, cache_hit = extractor.extract(request.text, request.use_cache)
        
        processing_time = time.time() - start_time
        
        if not contact:
            if not extractor.health_check():
                return ExtractionResponse(
                    success=False,
                    status="error",
                    data=None,
                    error=extractor.unavailable_error_message(),
                    processing_time=processing_time,
                    cache_hit=cache_hit
                )

            return ExtractionResponse(
                success=True,
                status="not_found",
                data=None,
                error=None,
                processing_time=processing_time,
                cache_hit=cache_hit
            )
        
        # Check if any meaningful data was extracted
        has_data = (
            contact.client_name or 
            contact.company_name or 
            contact.email or 
            len(contact.phone_numbers) > 0 or
            contact.notes or
            (contact.address and any([
                contact.address.street,
                contact.address.city,
                contact.address.state,
                contact.address.postal_code
            ]))
        )
        
        return ExtractionResponse(
            success=True,
            status="found" if has_data else "not_found",
            data=contact,
            error=None,
            processing_time=processing_time,
            cache_hit=cache_hit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        processing_time = time.time() - start_time
        
        return ExtractionResponse(
            success=False,
            status="error",
            data=None,
            error=str(e),
            processing_time=processing_time,
            cache_hit=False
        )


@app.get("/stats", tags=["Statistics"])
async def get_statistics():
    """Get extraction statistics"""
    try:
        stats = chroma_manager.get_stats()
        stats["local_cache"] = local_cache.get_stats()
        stats["llm_provider"] = settings.llm_provider
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback", tags=["Feedback"])
async def submit_feedback(extraction_id: str, corrections: dict):
    """Submit corrections for an extraction to improve future results"""
    # This endpoint can be implemented to store feedback and retrain
    return {
        "success": True,
        "message": "Feedback received",
        "extraction_id": extraction_id
    }