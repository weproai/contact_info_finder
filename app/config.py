from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"  # or try "mistral" or "llama3" for better results
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "contact_extractions"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # Performance
    enable_fast_mode: bool = False  # Set to True for millisecond responses (less accurate)
    cache_similarity_threshold: float = 0.1
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()