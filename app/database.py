import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional, List, Dict
import json
import logging
from app.config import settings
from app.models import ExtractedContact

logger = logging.getLogger(__name__)


class ChromaDBManager:
    def __init__(self):
        # Disable telemetry to avoid errors
        import os
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get or create the contact extractions collection"""
        try:
            return self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Contact information extractions"}
            )
        except Exception as e:
            logger.error(f"Error creating/getting collection: {e}")
            # Fallback: try to get existing collection
            return self.client.get_collection(settings.chroma_collection_name)
    
    def add_extraction(self, text: str, extraction: ExtractedContact, embedding: Optional[List[float]] = None):
        """Store an extraction in the database"""
        try:
            # Convert extraction to dict for metadata
            metadata = {
                "client_name": extraction.client_name or "",
                "company_name": extraction.company_name or "",
                "email": extraction.email or "",
                "has_address": bool(extraction.address),
                "phone_count": len(extraction.phone_numbers),
                "extracted_at": extraction.extracted_at.isoformat()
            }
            
            # Store full extraction as JSON in metadata
            metadata["full_extraction"] = json.dumps(extraction.dict(), default=str)
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[f"extraction_{extraction.extracted_at.timestamp()}"],
                embeddings=[embedding] if embedding else None
            )
            logger.info(f"Stored extraction for text: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error storing extraction: {str(e)}")
            return False
    
    def find_similar(self, text: str, n_results: int = 5) -> List[Dict]:
        """Find similar previously extracted texts"""
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=n_results
            )
            
            similar_extractions = []
            for i in range(len(results['ids'][0])):
                if results['metadatas'][0][i].get('full_extraction'):
                    extraction_data = json.loads(results['metadatas'][0][i]['full_extraction'])
                    similar_extractions.append({
                        'text': results['documents'][0][i],
                        'extraction': extraction_data,
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })
            
            return similar_extractions
        except Exception as e:
            logger.error(f"Error finding similar texts: {str(e)}")
            return []
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_extractions": count,
                "collection_name": settings.chroma_collection_name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}
    
    def health_check(self) -> bool:
        """Check if ChromaDB is healthy"""
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False


# Singleton instance
chroma_manager = ChromaDBManager()