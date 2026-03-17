"""Embedding service that batches chunk inputs through a provider."""

from __future__ import annotations

from chunking.chunk_models import KnowledgeChunk

from .embedding_models import EmbeddedChunk
from .embedding_provider import EmbeddingProvider


class EmbeddingService:
    """Generate embeddings for chunk collections with configurable batching."""

    def __init__(self, provider: EmbeddingProvider, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")

        self._provider = provider
        self._batch_size = batch_size

    def embed_chunks(self, chunks: list[KnowledgeChunk]) -> list[EmbeddedChunk]:
        """Embed all chunks and return enriched chunk records."""
        if not chunks:
            return []

        embedded_chunks: list[EmbeddedChunk] = []
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            texts = [chunk.text for chunk in batch]
            vectors = self._provider.embed_batch(texts)

            if len(vectors) != len(batch):
                raise RuntimeError(
                    "provider returned mismatched vector count "
                    f"(expected {len(batch)}, got {len(vectors)})"
                )

            for chunk, vector in zip(batch, vectors):
                embedded_chunks.append(
                    EmbeddedChunk(
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        text=chunk.text,
                        metadata=dict(chunk.metadata),
                    )
                )

        return embedded_chunks
