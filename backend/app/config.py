from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    openai_api_key: str
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Authentication
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/law_rag.db"

    # Qdrant Vector Store
    qdrant_path: str = "./data/qdrant_storage"
    qdrant_api_key: str | None = None

    # Document Ingestion
    watch_folder: str = "./data/watch"
    max_chunk_size: int = 512
    chunk_overlap: int = 50

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
