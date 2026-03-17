"""Service for embedding user questions for retrieval."""

from __future__ import annotations

from embeddings.embedding_provider import EmbeddingProvider


class QueryEmbeddingService:
    """Converts user questions into embedding vectors via injected provider."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embedding_provider = embedding_provider

    def embed_question(self, question: str) -> list[float]:
        """Embed a normalized user question."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question cannot be empty")
        return self._embedding_provider.embed_text(normalized_question)
