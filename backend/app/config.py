from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # ── LLM Provider ─────────────────────────────────────────────────────────
    # Set to "ollama" to use a local Ollama instance instead of OpenAI.
    llm_provider: Literal["openai", "ollama"] = "openai"

    # OpenAI (used when llm_provider = "openai")
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Ollama (used when llm_provider = "ollama")
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_llm_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # ── Embedding dimension ───────────────────────────────────────────────────
    # Must match the model in use.  Change before first ingest if switching providers.
    # OpenAI text-embedding-3-small → 1536
    # Ollama nomic-embed-text       → 768
    # Ollama mxbai-embed-large      → 1024
    embedding_dim: int = 1536

    # ── Authentication ────────────────────────────────────────────────────────
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/law_rag.db"

    # ── Qdrant Vector Store ───────────────────────────────────────────────────
    # Set qdrant_url to use server mode (e.g. http://qdrant:6333 in Docker).
    # Leave unset to fall back to embedded/local mode using qdrant_path.
    qdrant_url: str | None = None
    qdrant_path: str = "./data/qdrant_storage"
    qdrant_api_key: str | None = None

    # ── Document Ingestion ────────────────────────────────────────────────────
    watch_folder: str = "./data/watch"
    data_dir: str = "./data"
    max_chunk_size: int = 512
    chunk_overlap: int = 50
    # Largest single upload accepted, in megabytes. Uploads are read in
    # chunks and rejected as soon as this is exceeded, so an oversized
    # file is never fully buffered or written to disk.
    max_upload_size_mb: int = 50

    # ── Seed admin user ───────────────────────────────────────────────────────
    admin_email: str = "admin@lawfirm.local"
    admin_password: str = "changeme"
    admin_name: str = "Admin Partner"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
