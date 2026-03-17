"""Pydantic query and retrieval-context models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from vector_store.vector_models import VectorSearchResult


class QueryRequest(BaseModel):
    """Incoming question payload for semantic retrieval."""

    question: str = Field(..., min_length=1, description="Engineer question")
    top_k: int = Field(
        default=5, ge=1, le=50, description="Number of chunks to retrieve"
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be empty")
        return normalized


class QueryContext(BaseModel):
    """Structured retrieval output for downstream LLM reasoning."""

    question: str = Field(description="Original user question")
    retrieved_chunks: list[VectorSearchResult] = Field(
        default_factory=list,
        description="Top retrieved semantic chunks",
    )
    context_text: str = Field(description="Assembled context to feed reasoning layer")
    query_type: str = Field(
        default="implementation",
        description="Classifier output used for retrieval strategy",
    )
