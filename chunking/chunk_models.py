"""Pydantic models for chunked knowledge artifacts."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class KnowledgeChunk(BaseModel):
    """A retrieval-ready chunk produced from a larger ``KnowledgeItem``."""

    chunk_id: UUID = Field(default_factory=uuid4, description="Unique chunk identifier")
    parent_id: UUID = Field(description="Parent KnowledgeItem identifier")
    text: str = Field(..., min_length=1, description="Chunk text payload")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata; must include source_type, repo and file_path",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Normalize and validate non-empty chunk text."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("chunk text cannot be empty")
        return normalized

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure mandatory retrieval metadata is always present."""
        required_keys = {"source_type", "repo", "file_path"}
        missing = required_keys.difference(value.keys())
        if missing:
            missing_csv = ", ".join(sorted(missing))
            raise ValueError(f"missing required metadata keys: {missing_csv}")
        return value
