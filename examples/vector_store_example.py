"""Example: store embedded chunks in Qdrant and run semantic search."""

from __future__ import annotations

from config.settings import Settings
from embeddings.embedding_models import EmbeddedChunk
from vector_store.qdrant_store import QdrantVectorStore
from vector_store.vector_search_service import VectorSearchService


def build_embedded_chunks(vector_size: int) -> list[EmbeddedChunk]:
    first_vector = [0.001] * vector_size
    second_vector = [0.002] * vector_size

    return [
        EmbeddedChunk(
            chunk_id="7f1cb95f-b01a-4a22-b7d9-989ce76b2f31",
            vector=first_vector,
            text="calculateEmissionFactor computes emissions using distance and mode.",
            metadata={
                "source_type": "code",
                "repo": "core-engine",
                "file_path": "services/carbon/CarbonCalculationService.kt",
                "function": "calculateEmissionFactor",
            },
        ),
        EmbeddedChunk(
            chunk_id="29e10950-c5f2-4545-9f4f-390a5f9cbe19",
            vector=second_vector,
            text="PR discussion about adding cache invalidation for emissions.",
            metadata={
                "source_type": "pull_request",
                "repo": "core-engine",
                "file_path": "pull_requests/421",
                "section": "comment",
            },
        ),
    ]


def main() -> None:
    # Host-side execution uses localhost; inside Docker network this can be qdrant.
    settings = Settings(qdrant_url="http://localhost:6333", qdrant_api_key=None)

    vector_store = QdrantVectorStore(settings)
    search_service = VectorSearchService(vector_store)

    chunks = build_embedded_chunks(settings.qdrant_vector_size)
    vector_store.upsert_chunks(chunks)

    query_vector = [0.001] * settings.qdrant_vector_size
    results = search_service.search_similar(query_vector=query_vector, top_k=5)

    print(f"Stored chunks: {len(chunks)}")
    print(f"Search results: {len(results)}")
    print("-" * 72)

    for index, result in enumerate(results, start=1):
        print(f"[{index}] chunk_id={result.chunk_id} score={result.score:.4f}")
        print(f"    source_type={result.metadata.get('source_type', 'unknown')}")
        print(f"    preview={result.text[:80]}...")


if __name__ == "__main__":
    main()
