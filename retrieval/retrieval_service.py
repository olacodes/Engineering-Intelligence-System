"""Retrieval orchestration from question to assembled query context."""

from __future__ import annotations

from retrieval.context_builder import ContextBuilder
from retrieval.multi_retriever import MultiSourceRetriever
from retrieval.query_embedding_service import QueryEmbeddingService
from retrieval.query_classifier import QueryClassifier
from retrieval.query_models import QueryContext, QueryRequest
from retrieval.reranker import ReRanker
from vector_store.vector_models import VectorSearchResult
from vector_store.vector_search_service import VectorSearchService


class RetrievalService:
    """Coordinates multi-stage retrieval and context assembly for reasoning."""

    def __init__(
        self,
        query_embedding_service: QueryEmbeddingService,
        vector_search_service: VectorSearchService,
        context_builder: ContextBuilder,
        query_classifier: QueryClassifier | None = None,
        multi_source_retriever: MultiSourceRetriever | None = None,
        reranker: ReRanker | None = None,
        max_chunks: int = 8,
    ) -> None:
        if max_chunks < 1:
            raise ValueError("max_chunks must be >= 1")

        self._query_embedding_service = query_embedding_service
        self._vector_search_service = vector_search_service
        self._context_builder = context_builder
        self._query_classifier = query_classifier or QueryClassifier()
        self._multi_source_retriever = multi_source_retriever or MultiSourceRetriever(
            vector_search_service
        )
        self._reranker = reranker or ReRanker()
        self._max_chunks = max_chunks

    def retrieve(self, query_request: QueryRequest) -> list[VectorSearchResult]:
        """Retrieve ranked chunks using classify -> multi-source search -> rerank."""
        query_vector = self._query_embedding_service.embed_question(
            query_request.question
        )
        top_k = min(query_request.top_k, self._max_chunks)
        query_plan = self._query_classifier.classify(
            question=query_request.question,
            top_k=top_k,
        )
        multi_source_results = self._multi_source_retriever.retrieve(
            query_vector=query_vector,
            query_plan=query_plan,
        )
        return self._reranker.rerank(
            question=query_request.question,
            query_plan=query_plan,
            results=multi_source_results,
            final_top_k=top_k,
        )

    def build_context(self, query_request: QueryRequest) -> QueryContext:
        """Run full retrieval flow and return LLM-ready context payload."""
        query_plan = self._query_classifier.classify(
            question=query_request.question,
            top_k=min(query_request.top_k, self._max_chunks),
        )
        query_vector = self._query_embedding_service.embed_question(
            query_request.question
        )
        multi_source_results = self._multi_source_retriever.retrieve(
            query_vector=query_vector,
            query_plan=query_plan,
        )
        retrieved_chunks = self._reranker.rerank(
            question=query_request.question,
            query_plan=query_plan,
            results=multi_source_results,
            final_top_k=min(query_request.top_k, self._max_chunks),
        )
        context_text = self._context_builder.build_context(
            retrieved_chunks,
            query_type=query_plan.query_type,
        )

        return QueryContext(
            question=query_request.question,
            retrieved_chunks=retrieved_chunks,
            context_text=context_text,
            query_type=query_plan.query_type,
        )
