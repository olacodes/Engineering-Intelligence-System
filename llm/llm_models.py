"""Models for LLM reasoning outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LLMAnswer(BaseModel):
    """Structured answer returned by the reasoning layer."""

    answer: str = Field(..., min_length=1, description="Final answer text")
    sources: list[str] = Field(
        default_factory=list,
        description="List of source identifiers used in the answer",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score normalized to [0.0, 1.0]",
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer cannot be empty")
        return normalized

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for source in value:
            candidate = source.strip()
            if candidate and candidate not in cleaned:
                cleaned.append(candidate)
        return cleaned
