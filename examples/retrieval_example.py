"""Example: question -> embedding -> vector search -> assembled context."""

from __future__ import annotations

from config.settings import Settings
from embeddings.embedding_models import EmbeddedChunk
from embeddings.embedding_provider import DeterministicEmbeddingProvider
from retrieval.context_builder import ContextBuilder
from retrieval.query_embedding_service import QueryEmbeddingService
from retrieval.query_models import QueryRequest
from retrieval.retrieval_service import RetrievalService
from vector_store.qdrant_store import QdrantVectorStore
from vector_store.vector_search_service import VectorSearchService


def _seed_chunks(vector_size: int) -> list[EmbeddedChunk]:
    return [
        EmbeddedChunk(
            chunk_id="b3dca8f9-c9a5-4aa4-9654-66b6391df48b",
            vector=[0.001] * vector_size,
            text="fun calculateEmissionFactor(material: Material): Double { ... }",
            metadata={
                "source_type": "code",
                "repo": "core-engine",
                "file_path": "services/carbon/CarbonCalculationService.kt",
                "function": "calculateEmissionFactor",
            },
        ),
        EmbeddedChunk(
            chunk_id="d508131d-3504-4774-83a0-76abf10d7393",
            vector=[0.002] * vector_size,
            text="PR #412 discussion: introduced emission factor rounding safeguards.",
            metadata={
                "source_type": "pull_request",
                "repo": "core-engine",
                "file_path": "pull_requests/412",
                "section": "discussion",
            },
        ),
    ]


def main() -> None:
    settings = Settings(qdrant_url="http://localhost:6333", qdrant_api_key=None)

    vector_store = QdrantVectorStore(settings)
    vector_store.upsert_chunks(_seed_chunks(settings.qdrant_vector_size))

    embedding_provider = DeterministicEmbeddingProvider(
        dimension=settings.qdrant_vector_size
    )
    query_embedding_service = QueryEmbeddingService(embedding_provider)
    vector_search_service = VectorSearchService(vector_store)
    context_builder = ContextBuilder(max_context_chars=4000)

    retrieval_service = RetrievalService(
        query_embedding_service=query_embedding_service,
        vector_search_service=vector_search_service,
        context_builder=context_builder,
        max_chunks=5,
    )

    query_request = QueryRequest(
        question="Where is emission factor calculated?",
        top_k=5,
    )

    query_context = retrieval_service.build_context(query_request)

    print(f"Question: {query_context.question}")
    print(f"Retrieved chunks: {len(query_context.retrieved_chunks)}")
    print("-" * 72)
    print(query_context.context_text)


if __name__ == "__main__":
    main()
