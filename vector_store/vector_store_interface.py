"""Vector store abstraction for embedding persistence and retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod

from embeddings.embedding_models import EmbeddedChunk

from .vector_models import VectorSearchResult


class VectorStore(ABC):
    """Contract for any backing vector database implementation."""

    @abstractmethod
    def create_collection(self) -> None:
        """Create a vector collection if it does not already exist."""

    @abstractmethod
    def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        """Insert or update embedded chunks in the vector store."""

    @abstractmethod
    def search(
        self,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        """Search similar chunks for the provided query embedding."""
