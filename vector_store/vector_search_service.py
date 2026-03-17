"""Application service for semantic vector retrieval."""

from __future__ import annotations

from .vector_models import VectorSearchResult
from .vector_store_interface import VectorStore


class VectorSearchService:
    """Thin service layer orchestrating semantic search over a VectorStore."""

    def __init__(self, vector_store: VectorStore) -> None:
        self._vector_store = vector_store

    def search_similar(
        self,
        query_vector: list[float],
        top_k: int = 5,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        """Search the vector store and return structured results."""
        return self._vector_store.search(
            vector=query_vector,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
