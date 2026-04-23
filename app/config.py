from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    # Provider Configuration
    llm_provider: Literal["ollama", "openai"] = "ollama"
    llm_enabled: bool = True

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"  # or try "mistral" or "llama3" for better results

    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 15.0
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "contact_extractions"

    # Local Cache Configuration
    local_cache_enabled: bool = True
    local_cache_db_path: str = "./cache/extraction_cache.sqlite3"
    local_cache_memory_entries: int = 1000
    cache_normalization_version: str = "v1"
    
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