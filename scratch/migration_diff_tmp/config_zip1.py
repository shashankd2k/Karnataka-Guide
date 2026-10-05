"""
Application configuration, deployment profile, database, storage, AI, and security settings.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Stable application base directory (backend root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AppProfile(str, Enum):
    """Supported deployment profiles."""
    DEV = "dev"
    STANDALONE = "standalone"
    CLOUD = "cloud"


class Settings(BaseSettings):
    """Application settings schema."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "AI-Powered Smart Tourist Guide Platform for Karnataka"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Deployment Profile: dev | standalone | cloud
    APP_PROFILE: AppProfile = AppProfile.DEV
    
    # Server network settings
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    
    # CORS configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database (MySQL 8.0) Configuration
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "karnataka_guide"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800

    # Security & JWT Configuration
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Super Admin Bootstrap Configuration (Explicit Command Only)
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@example.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = Field(default="")

    # PDF Document Storage Configuration
    DOCUMENT_STORAGE_DIR: str = "storage/documents"
    MAX_PDF_UPLOAD_BYTES: int = 52_428_800  # 50 MB

    # AI & Knowledge Base Vector Store Configuration
    CHROMA_PERSIST_DIR: str = "storage/chroma"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    CHUNK_TARGET_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # RAG Retrieval Optimization (Phase 7) Configuration
    RETRIEVAL_DENSE_TOP_K: int = 25
    RETRIEVAL_BM25_TOP_K: int = 25
    RETRIEVAL_RRF_K: int = 60
    RETRIEVAL_RERANK_CANDIDATES: int = 15
    RETRIEVAL_FINAL_TOP_K: int = 5
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Multilingual Conversation Engine (Phase 8) Configuration
    CONVERSATION_MAX_TURNS: int = 5
    CONVERSATION_MAX_INPUT_LENGTH: int = 1000
    CONVERSATION_GROUNDING_MIN_SCORE: float = -6.0

    # Ollama Local LLM & Grounded Generation (Phase 9) Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_MAX_CONTEXT_CHARS: int = 2000
    OLLAMA_KEEP_ALIVE: str = "10m"

    @property
    def async_database_url(self) -> str:
        """Construct async MySQL connection URL using asyncmy driver."""
        escaped_user = quote_plus(self.DB_USER)
        escaped_pwd = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+asyncmy://{escaped_user}:{escaped_pwd}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def resolved_storage_path(self) -> Path:
        """Resolve document storage directory from stable application base directory."""
        path = Path(self.DOCUMENT_STORAGE_DIR)
        if path.is_absolute():
            return path.resolve()
        return (BASE_DIR / path).resolve()

    @property
    def resolved_chroma_path(self) -> Path:
        """Resolve ChromaDB persistent storage directory from stable application base directory."""
        path = Path(self.CHROMA_PERSIST_DIR)
        if path.is_absolute():
            return path.resolve()
        return (BASE_DIR / path).resolve()

    @field_validator("APP_PROFILE", mode="before")
    @classmethod
    def validate_app_profile(cls, v: object) -> AppProfile:
        if isinstance(v, str):
            val = v.strip().lower()
            try:
                return AppProfile(val)
            except ValueError:
                raise ValueError(
                    f"Invalid APP_PROFILE '{v}'. Must be one of: "
                    f"{[p.value for p in AppProfile]}"
                )
        if isinstance(v, AppProfile):
            return v
        raise ValueError(f"Invalid APP_PROFILE type: {type(v)}")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Enforce strict security validation in production/standalone environments."""
        if self.APP_PROFILE in (AppProfile.STANDALONE, AppProfile.CLOUD):
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "CHANGE_ME" or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    f"In '{self.APP_PROFILE.value}' profile, JWT_SECRET_KEY must be a secure secret of at least 32 characters."
                )
        elif self.APP_PROFILE == AppProfile.DEV:
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "CHANGE_ME":
                # Fallback for dev mode only
                self.JWT_SECRET_KEY = "dev-insecure-secret-key-for-local-testing-only-32chars"
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
