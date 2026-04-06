"""
Configuration management for the Engineering Intelligence System.

This module centralizes all configuration, supporting multiple environments
(development, staging, production) via environment variables.
"""

import json
from typing import Optional
from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    Configuration is loaded from environment variables with sensible defaults
    for development. Override via environment variables or .env file.
    """

    # Application
    app_name: str = "Engineering Intelligence System"
    app_version: str = "0.1.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False
    log_level: str = "INFO"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_root_path: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:8000"

    # Vector Database (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "engineering_knowledge"
    qdrant_vector_size: int = 3072

    # Embedding Service
    embedding_model: str = Field(
        default="text-embedding-3-large",
        validation_alias=AliasChoices("embedding_model", "embeddings_model"),
    )
    embedding_dimension: int = Field(
        default=3072,
        validation_alias=AliasChoices("embedding_dimension", "embeddings_dimension"),
    )
    embedding_api_key: Optional[str] = None  # For OpenAI or similar
    embedding_batch_size: int = Field(
        default=100,
        validation_alias=AliasChoices("embedding_batch_size", "embeddings_batch_size"),
    )
    embedding_timeout: int = 30

    # LLM Configuration (Claude)
    llm_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "anthropic_api_key", "llm_api_key", "openai_api_key"
        ),
    )
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7
    llm_timeout: int = 60

    # Chunking Configuration
    chunk_size: int = 1024
    chunk_overlap: int = 100

    # Ingestion
    max_file_size_mb: int = 10
    allowed_file_extensions: list[str] = [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".cpp",
        ".c",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
    ]

    # Data Paths
    data_dir: str = "./data"
    cache_dir: str = "./cache"

    # Feature Flags
    enable_cache: bool = True
    enable_metrics: bool = True
    enable_request_logging: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Example document for IDE autocomplete
        json_schema_extra={
            "app_name": {"description": "Application name for branding"},
            "environment": {"description": "Deployment environment"},
            "qdrant_url": {"description": "Qdrant vector database URL"},
            "llm_api_key": {"description": "API key for Claude LLM"},
        },
    )

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from JSON array or comma-separated string."""
        raw = (self.cors_origins or "").strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                # Fall back to comma-separated parsing for malformed JSON.
                pass

        return [item.strip() for item in raw.split(",") if item.strip()]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_qdrant_url(self) -> str:
        """Get full Qdrant connection URL."""
        return self.qdrant_url

    def get_embedding_config(self) -> dict:
        """Get embedding service configuration as dictionary."""
        return {
            "model": self.embedding_model,
            "dimension": self.embedding_dimension,
            "batch_size": self.embedding_batch_size,
            "timeout": self.embedding_timeout,
        }

    def get_llm_config(self) -> dict:
        """Get LLM configuration as dictionary."""
        return {
            "model": self.llm_model,
            "max_tokens": self.llm_max_tokens,
            "temperature": self.llm_temperature,
            "timeout": self.llm_timeout,
        }

    def get_chunking_config(self) -> dict:
        """Get chunking configuration as dictionary."""
        return {
            "chunk_size": self.chunk_size,
            "overlap": self.chunk_overlap,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get or create the Settings singleton.

    Uses LRU cache to ensure only one Settings instance is created,
    reducing environment variable parsing overhead.

    Returns:
        Settings: The application settings singleton
    """
    return Settings()
