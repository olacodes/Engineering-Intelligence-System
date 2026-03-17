"""Multi-source retrieval stage with per-source metadata filtering."""

from __future__ import annotations

from dataclasses import dataclass

from vector_store.vector_models import VectorSearchResult
from vector_store.vector_search_service import VectorSearchService

from .query_classifier import SOURCE_TYPES, QueryPlan


@dataclass(frozen=True)
class MultiSourceResults:
    """Container for source-specific retrieval output."""

    by_source: dict[str, list[VectorSearchResult]]

    def flatten(self) -> list[VectorSearchResult]:
        """Flatten results preserving source group order."""
        merged: list[VectorSearchResult] = []
        for source in SOURCE_TYPES:
            merged.extend(self.by_source.get(source, []))
        return merged


class MultiSourceRetriever:
    """Retrieve candidate chunks independently for code, PR, and docs."""

    def __init__(self, vector_search_service: VectorSearchService) -> None:
        self._vector_search_service = vector_search_service

    def retrieve(
        self,
        query_vector: list[float],
        query_plan: QueryPlan,
    ) -> MultiSourceResults:
        """Run filtered semantic retrieval for each source type."""
        by_source: dict[str, list[VectorSearchResult]] = {}

        for source in SOURCE_TYPES:
            source_top_k = max(1, int(query_plan.source_top_k.get(source, 2)))
            metadata_filter = query_plan.metadata_filters.get(
                source, {"source_type": source}
            )

            results = self._vector_search_service.search_similar(
                query_vector=query_vector,
                top_k=source_top_k,
                metadata_filter=metadata_filter,
            )

            normalized: list[VectorSearchResult] = []
            for item in results:
                if item.metadata.get("source_type") == source:
                    normalized.append(item)
                    continue

                metadata = dict(item.metadata)
                metadata.setdefault("source_type", source)
                normalized.append(item.model_copy(update={"metadata": metadata}))

            by_source[source] = normalized

        return MultiSourceResults(by_source=by_source)
