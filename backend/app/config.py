"""
Application configuration for EvidenceBridge using Pydantic Settings.
Reads environment variables or fallback defaults.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "EvidenceBridge"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "evidencebridge"
    MONGODB_CLAIMS_COLLECTION: str = "claims"
    MONGODB_VERIFICATIONS_COLLECTION: str = "verifications"
    MONGODB_AUDIT_TRAILS_COLLECTION: str = "audit_trails"
    MONGODB_TIMEOUT_MS: int = 4000

    # Ollama Local LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # Knowledge Base & Verification
    KNOWLEDGE_BASE_DIR: str = "./data/knowledge"
    COST_ANOMALY_THRESHOLD_MULTIPLIER: float = 3.0
    RETRIEVAL_RELEVANCE_THRESHOLD: float = 0.35
    MIN_CONFIDENCE_THRESHOLD: float = 0.40
    ABSTAIN_ON_UNBENCHMARKED_HIGH_COST: bool = True

    # Vector Store Configuration
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "evidencebridge_claims"
    CHROMA_GUIDELINES_COLLECTION: str = "evidencebridge_guidelines"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
