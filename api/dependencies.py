"""Dependency injection providers for the EIS query API."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from config import Settings, get_settings
from chunking.chunk_service import ChunkService
from embeddings.embedding_provider import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from embeddings.embedding_service import EmbeddingService
from llm import ClaudeClient, PromptBuilder, ReasoningService
from retrieval.context_builder import ContextBuilder
from retrieval.query_embedding_service import QueryEmbeddingService
from retrieval.retrieval_service import RetrievalService
from vector_store.qdrant_store import QdrantVectorStore
from vector_store.vector_search_service import VectorSearchService

from utils.logger import get_logger

logger = get_logger(__name__)

from .ingestion_controller import IngestionController
from .query_controller import QueryController


@lru_cache()
def get_app_settings() -> Settings:
    """Return singleton application settings for API dependencies."""
    return get_settings()


def _build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build embedding provider from configuration with safe fallback."""
    if settings.embedding_api_key:
        logger.info("Initializing OpenAI-compatible embedding provider")
        return OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            timeout_seconds=settings.embedding_timeout,
        )

    logger.warning(
        "EMBEDDING_API_KEY not set; using deterministic embeddings for query API"
    )
    return DeterministicEmbeddingProvider(dimension=settings.qdrant_vector_size)


@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    """Return singleton embedding provider instance."""
    settings = get_app_settings()
    return _build_embedding_provider(settings)


@lru_cache()
def get_vector_store() -> QdrantVectorStore:
    """Return singleton Qdrant vector store client."""
    settings = get_app_settings()
    return QdrantVectorStore(settings)


@lru_cache()
def get_retrieval_service() -> RetrievalService:
    """Return singleton retrieval service wired with dependencies."""
    query_embedding_service = QueryEmbeddingService(get_embedding_provider())
    vector_search_service = VectorSearchService(get_vector_store())
    context_builder = ContextBuilder()

    return RetrievalService(
        query_embedding_service=query_embedding_service,
        vector_search_service=vector_search_service,
        context_builder=context_builder,
        max_chunks=20,
    )


@lru_cache()
def get_chunk_service() -> ChunkService:
    """Return singleton chunk service instance."""
    return ChunkService()


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Return singleton embedding service instance."""
    settings = get_app_settings()
    return EmbeddingService(
        provider=get_embedding_provider(),
        batch_size=settings.embedding_batch_size,
    )


@lru_cache()
def get_reasoning_service() -> ReasoningService:
    """Return singleton reasoning service with Claude client and prompt builder."""
    settings = get_app_settings()

    try:
        llm_client = ClaudeClient.from_settings(settings)
    except ValueError as exc:
        logger.error("Unable to initialize Claude client: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="LLM is not configured. Set LLM API key in environment.",
        ) from exc

    return ReasoningService(
        llm_client=llm_client,
        prompt_builder=PromptBuilder(),
    )


@lru_cache()
def get_query_controller() -> QueryController:
    """Return singleton query controller for API route injection."""
    return QueryController(
        retrieval_service=get_retrieval_service(),
        reasoning_service=get_reasoning_service(),
    )


@lru_cache()
def get_ingestion_controller() -> IngestionController:
    """Return singleton ingestion/indexing controller for API route injection."""
    return IngestionController(
        chunk_service=get_chunk_service(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )
