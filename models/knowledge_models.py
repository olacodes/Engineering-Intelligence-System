"""
Core domain models for the Engineering Intelligence System.

This module defines the fundamental data structures used across all layers
of the EIS, including knowledge items, metadata, and embedding configurations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, validator


class SourceType(str, Enum):
    """Enumeration of supported source types for knowledge ingestion."""

    GIT_COMMIT = "git_commit"
    PULL_REQUEST = "pull_request"
    DOCUMENTATION = "documentation"
    CODE_FILE = "code_file"
    ISSUE = "issue"
    COMMENT = "comment"


class KnowledgeMetadata(BaseModel):
    """
    Metadata associated with a knowledge item.

    This model captures contextual information about the source material,
    enabling better retrieval and reasoning during the query phase.
    """

    source_url: Optional[str] = Field(
        None, description="External URL reference (GitHub, GitLab, etc.)"
    )
    author: Optional[str] = Field(
        None, description="Author or contributor of the source material"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the source was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the source was last updated",
    )
    tags: List[str] = Field(
        default_factory=list, description="Semantic tags for categorization"
    )
    language: Optional[str] = Field(
        default="unknown",
        description="Programming language or file type (js, py, md, etc.)",
    )
    lines_of_code: Optional[int] = Field(
        None, description="Number of lines in the source (for code)"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible field for domain-specific metadata",
    )

    class Config:
        frozen = False


class KnowledgeItem(BaseModel):
    """
    Core domain model representing a unit of engineering knowledge.

    A knowledge item represents a discrete piece of engineering information
    (code, documentation, PR, etc.) that will be indexed and retrieved by the system.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this knowledge item"
    )
    source_type: SourceType = Field(
        description="The type/category of the source material"
    )
    repo: str = Field(..., description="Repository identifier (org/repo format)")
    file_path: str = Field(
        ..., description="Path to the source file or resource identifier"
    )
    content: str = Field(..., description="The actual knowledge content")
    metadata: KnowledgeMetadata = Field(
        default_factory=KnowledgeMetadata,
        description="Associated metadata for this knowledge item",
    )
    chunk_index: Optional[int] = Field(
        None, description="Index if this item is a chunk from a larger document"
    )
    total_chunks: Optional[int] = Field(
        None, description="Total number of chunks from the parent document"
    )
    parent_id: Optional[UUID] = Field(
        None, description="Reference to parent item if this is a chunk"
    )

    class Config:
        use_enum_values = False
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "source_type": "code_file",
                "repo": "facebook/react",
                "file_path": "packages/react/src/index.js",
                "content": "export { default as React } from './React';",
                "metadata": {
                    "language": "js",
                    "author": "Dan Abramov",
                    "tags": ["core", "exports"],
                },
            }
        }

    def to_search_text(self) -> str:
        """Generate searchable text combining content and metadata."""
        parts = [
            self.content,
            self.file_path,
            self.repo,
            " ".join(self.metadata.tags),
        ]
        return " | ".join(filter(None, parts))

    @validator("file_path")
    def validate_file_path(cls, v: str) -> str:
        """Ensure file path is non-empty."""
        if not v or not v.strip():
            raise ValueError("file_path cannot be empty")
        return v.strip()

    @validator("content")
    def validate_content(cls, v: str) -> str:
        """Ensure content is non-empty."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model_config = ConfigDict(protected_namespaces=(), frozen=False)

    model_id: str = Field(
        default="text-embedding-3-large",
        description="Identifier for the embedding model",
    )
    embedding_dimension: int = Field(
        default=3072, description="Dimensionality of generated embeddings"
    )
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Batch size for embedding generation"
    )
    timeout_seconds: int = Field(
        default=30, ge=1, description="Timeout for embedding API calls"
    )
    max_token_length: int = Field(
        default=8191, description="Maximum tokens per embedding input"
    )


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = Field(
        default=1024, ge=100, le=10000, description="Size of each chunk in tokens"
    )
    overlap_tokens: int = Field(
        default=100,
        ge=0,
        le=1000,
        description="Token overlap between consecutive chunks",
    )
    separator: str = Field(default="\n\n", description="Primary separator for chunking")

    @validator("overlap_tokens")
    def validate_overlap(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure overlap is less than chunk size."""
        if "chunk_size" in values and v >= values["chunk_size"]:
            raise ValueError("overlap_tokens must be less than chunk_size")
        return v

    class Config:
        frozen = False


class SearchQuery(BaseModel):
    """Model for knowledge base search queries."""

    query_text: str = Field(
        ..., min_length=1, description="Natural language search query"
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Number of results to return"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional filters (repo, source_type, tags)"
    )

    class Config:
        frozen = False


class SearchResult(BaseModel):
    """Model for knowledge base search results."""

    item: KnowledgeItem = Field(description="The retrieved knowledge item")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0 to 1")
    explanation: Optional[str] = Field(
        None, description="Explanation of why this result matches"
    )

    class Config:
        frozen = False


class SystemHealth(BaseModel):
    """System health and status information."""

    status: str = Field(..., description="Overall system status")
    indexed_items: int = Field(default=0, description="Total indexed knowledge items")
    vector_db_healthy: bool = Field(
        default=False, description="Vector database connection status"
    )
    last_ingestion: Optional[datetime] = Field(
        None, description="Timestamp of last successful ingestion"
    )
    errors: List[str] = Field(default_factory=list, description="List of recent errors")

    class Config:
        frozen = False
