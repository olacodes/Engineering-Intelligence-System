"""Qdrant-backed vector store implementation."""

from __future__ import annotations

import importlib
from typing import Any
from uuid import UUID

from config import Settings
from embeddings.embedding_models import EmbeddedChunk

from utils.logger import get_logger

from .vector_models import VectorSearchResult
from .vector_store_interface import VectorStore

logger = get_logger(__name__)


class QdrantVectorStore(VectorStore):
    """VectorStore implementation using the official Qdrant Python client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collection_name = settings.qdrant_collection_name
        self._vector_size = settings.qdrant_vector_size

        qdrant_client_module = importlib.import_module("qdrant_client")
        qdrant_models_module = importlib.import_module("qdrant_client.http.models")
        qdrant_client_class = getattr(qdrant_client_module, "QdrantClient")
        self._qdrant_models = qdrant_models_module

        self._client = qdrant_client_class(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )

    def create_collection(self) -> None:
        """Create Qdrant collection if missing."""
        if self._collection_exists(self._collection_name):
            logger.info("Qdrant collection '%s' already exists", self._collection_name)
            return

        logger.info(
            "Creating Qdrant collection '%s' with vector size=%d",
            self._collection_name,
            self._vector_size,
        )

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=self._qdrant_models.VectorParams(
                size=self._vector_size,
                distance=self._qdrant_models.Distance.COSINE,
            ),
        )

    def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        """Batch upsert embedded chunks into Qdrant."""
        if not chunks:
            logger.info("No embedded chunks to upsert")
            return

        self.create_collection()

        for chunk in chunks:
            self._validate_vector_dimensions(chunk)

        points = [self._chunk_to_point(chunk) for chunk in chunks]

        logger.info(
            "Upserting %d chunks into collection '%s'",
            len(points),
            self._collection_name,
        )

        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        """Run semantic similarity search in Qdrant."""
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if not vector:
            raise ValueError("query vector cannot be empty")
        if len(vector) != self._vector_size:
            raise ValueError(
                f"query vector dimension {len(vector)} does not match configured size {self._vector_size}"
            )

        query_filter = self._build_query_filter(metadata_filter)
        search_points = self._search_points(
            vector=vector,
            top_k=top_k,
            query_filter=query_filter,
        )

        results: list[VectorSearchResult] = []
        for point in search_points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {})
            text = str(payload.get("text", "")).strip()

            if not text:
                continue

            try:
                chunk_id = UUID(str(point.id))
            except ValueError:
                logger.warning(
                    "Skipping search point with invalid UUID id: %s", point.id
                )
                continue

            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    score=float(point.score or 0.0),
                    text=text,
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
            )

        return results

    def _search_points(
        self,
        vector: list[float],
        top_k: int,
        query_filter: Any = None,
    ) -> list[Any]:
        """Execute search while supporting multiple qdrant-client versions."""
        if hasattr(self._client, "search"):
            search_kwargs: dict[str, Any] = {
                "collection_name": self._collection_name,
                "query_vector": vector,
                "limit": top_k,
                "with_payload": True,
            }
            if query_filter is not None:
                search_kwargs["query_filter"] = query_filter

            return self._client.search(**search_kwargs)

        query_kwargs: dict[str, Any] = {
            "collection_name": self._collection_name,
            "query": vector,
            "limit": top_k,
            "with_payload": True,
        }
        if query_filter is not None:
            query_kwargs["query_filter"] = query_filter

        query_response = self._client.query_points(**query_kwargs)
        return list(getattr(query_response, "points", []))

    def _build_query_filter(self, metadata_filter: dict[str, object] | None) -> Any:
        """Build a Qdrant payload filter for metadata equality matching."""
        if not metadata_filter:
            return None

        conditions = []
        for key, value in metadata_filter.items():
            if value is None:
                continue

            conditions.append(
                self._qdrant_models.FieldCondition(
                    key=f"metadata.{key}",
                    match=self._qdrant_models.MatchValue(value=value),
                )
            )

        if not conditions:
            return None

        return self._qdrant_models.Filter(must=conditions)

    def _collection_exists(self, collection_name: str) -> bool:
        """Check collection existence using the client API."""
        try:
            existing = self._client.get_collections().collections
        except Exception as exc:  # pragma: no cover - network/runtime failure path
            logger.exception("Unable to list Qdrant collections: %s", exc)
            raise

        return any(collection.name == collection_name for collection in existing)

    def _validate_vector_dimensions(self, chunk: EmbeddedChunk) -> None:
        if len(chunk.vector) != self._vector_size:
            raise ValueError(
                f"chunk {chunk.chunk_id} vector dimension {len(chunk.vector)} does not match "
                f"configured size {self._vector_size}"
            )

    def _chunk_to_point(self, chunk: EmbeddedChunk) -> Any:
        payload: dict[str, Any] = {
            "text": chunk.text,
            "metadata": dict(chunk.metadata),
        }

        return self._qdrant_models.PointStruct(
            id=str(chunk.chunk_id),
            vector=chunk.vector,
            payload=payload,
        )
