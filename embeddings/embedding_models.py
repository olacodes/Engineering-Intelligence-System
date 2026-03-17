"""Pydantic models for chunk embeddings."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EmbeddedChunk(BaseModel):
    """Knowledge chunk enriched with its embedding vector."""

    chunk_id: UUID = Field(description="Source chunk identifier")
    vector: list[float] = Field(description="Dense embedding vector")
    text: str = Field(description="Original chunk text")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata propagated from chunking stage",
    )

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("embedding vector cannot be empty")
        return value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("embedded chunk text cannot be empty")
        return normalized
