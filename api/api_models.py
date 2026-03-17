"""Request and response models for the EIS query API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    """Incoming request payload for question answering."""

    question: str = Field(..., min_length=1, description="Engineer question")
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve before reasoning",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Normalize and validate the question text."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be empty")
        return normalized


class AskResponse(BaseModel):
    """Structured response returned by the query API."""

    answer: str = Field(..., description="Grounded answer from reasoning layer")
    sources: list[str] = Field(
        default_factory=list,
        description="Source file paths or artifact identifiers cited in answer",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Reasoning confidence score",
    )
