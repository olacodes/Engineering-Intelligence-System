"""Models for semantic vector search results."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VectorSearchResult(BaseModel):
    """A single semantic search result returned by the vector store."""

    chunk_id: UUID = Field(description="Knowledge chunk identifier")
    score: float = Field(description="Similarity score")
    text: str = Field(description="Chunk text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("search result text cannot be empty")
        return normalized
