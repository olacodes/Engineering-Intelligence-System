"""Example: convert KnowledgeChunk objects into EmbeddedChunk vectors."""

from __future__ import annotations

from chunking.chunk_models import KnowledgeChunk
from embeddings.embedding_provider import DeterministicEmbeddingProvider
from embeddings.embedding_service import EmbeddingService


def build_chunks() -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            parent_id="e3803ba7-27df-4dd2-b4fc-a8dcfe5eecf4",
            text="calculateEmissionFactor(distanceKm) returns distance * 0.21",
            metadata={
                "source_type": "code",
                "repo": "core-engine",
                "file_path": "services/carbon/CarbonCalculationService.kt",
                "function": "calculateEmissionFactor",
            },
        ),
        KnowledgeChunk(
            parent_id="8d57a181-2027-4f54-9f81-f384057a6441",
            text="PR summary: add cache invalidation to emission pipeline.",
            metadata={
                "source_type": "pull_request",
                "repo": "core-engine",
                "file_path": "pull_requests/421",
                "section": "description",
            },
        ),
    ]


def main() -> None:
    chunks = build_chunks()

    provider = DeterministicEmbeddingProvider(dimension=32)
    embedding_service = EmbeddingService(provider=provider, batch_size=2)
    embedded_chunks = embedding_service.embed_chunks(chunks)

    print(f"Input chunks: {len(chunks)}")
    print(f"Embedded chunks: {len(embedded_chunks)}")
    print("-" * 72)

    for idx, embedded in enumerate(embedded_chunks, start=1):
        print(f"[{idx}] chunk_id={embedded.chunk_id}")
        print(f"    vector_dim={len(embedded.vector)}")
        print(f"    source_type={embedded.metadata['source_type']}")
        print(f"    preview={embedded.text[:80]}...")


if __name__ == "__main__":
    main()
