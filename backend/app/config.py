"""
Application configuration for EvidenceBridge using Pydantic Settings.
Reads environment variables or fallback defaults.
"""

from functools import lru_cache
from typing import Optional
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
    # Supports MONGODB_URI (e.g. from Atlas / cloud deployment) or fallback MONGODB_URL
    MONGODB_URI: Optional[str] = None
    MONGODB_URL: Optional[str] = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "evidencebridge"
    MONGODB_USERS_COLLECTION: str = "users"
    MONGODB_CLAIMS_COLLECTION: str = "claims"
    MONGODB_VERIFICATIONS_COLLECTION: str = "verifications"
    MONGODB_AUDIT_TRAILS_COLLECTION: str = "audit_trails"
    MONGODB_TRUST_DENSITY_COLLECTION: str = "trust_density"
    MONGODB_COMMUNITY_STORIES_COLLECTION: str = "community_stories"
    MONGODB_TIMEOUT_MS: int = 5000

    # JWT / Auth Configuration
    AUTH_SECRET_KEY: str = "evidencebridge_jwt_secret_portfolio_key_change_in_prod_2026"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def mongodb_connection_uri(self) -> str:
        """
        Securely returns MongoDB connection URI from MONGODB_URI or MONGODB_URL.
        Strict security rule: never log, print, or expose this string.
        """
        return self.MONGODB_URI or self.MONGODB_URL or "mongodb://localhost:27017"

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

    # Hyperlocal Trust Density Configuration
    TRUST_DENSITY_SUPPORT_WEIGHT: float = 0.45
    TRUST_DENSITY_ANOMALY_WEIGHT: float = 0.35
    TRUST_DENSITY_VOLUME_WEIGHT: float = 0.20
    TRUST_DENSITY_MIN_VOLUME: int = 5
    TRUST_DENSITY_TIME_DECAY_DAYS: float = 45.0

    # Vector Store Configuration
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "evidencebridge_claims"
    CHROMA_GUIDELINES_COLLECTION: str = "evidencebridge_guidelines"

    # Evaluation Configuration (Layer 6)
    MONGODB_EVALUATIONS_COLLECTION: str = "evaluation_runs"
    EVALUATION_DATASET_PATH: str = "./data/evaluation/controlled_cases.json"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
