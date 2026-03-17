"""Lightweight hybrid reranker combining semantic and lexical signals."""

from __future__ import annotations

import re

from vector_store.vector_models import VectorSearchResult

from .multi_retriever import MultiSourceResults
from .query_classifier import QueryPlan


class ReRanker:
    """Re-rank multi-source candidates by relevance and query intent."""

    def rerank(
        self,
        question: str,
        query_plan: QueryPlan,
        results: MultiSourceResults,
        final_top_k: int,
    ) -> list[VectorSearchResult]:
        """Return globally ranked chunks after source-aware fusion."""
        if final_top_k < 1:
            raise ValueError("final_top_k must be >= 1")

        query_terms = self._tokenize(question)
        scored: list[tuple[float, VectorSearchResult]] = []

        for source, source_results in results.by_source.items():
            source_prior = float(query_plan.source_weight.get(source, 0.2))

            for item in source_results:
                semantic_score = self._normalize_semantic(item.score)
                lexical_score = self._lexical_overlap(query_terms, item)
                symbol_boost = self._symbol_boost(item, query_plan.symbol_hints)

                fused_score = (
                    0.55 * semantic_score
                    + 0.30 * lexical_score
                    + 0.15 * source_prior
                    + symbol_boost
                )

                metadata = dict(item.metadata)
                metadata["retrieval_score"] = round(fused_score, 6)
                scored.append(
                    (
                        fused_score,
                        item.model_copy(update={"metadata": metadata}),
                    )
                )

        scored.sort(key=lambda pair: pair[0], reverse=True)

        deduped: list[VectorSearchResult] = []
        seen = set()
        for _, item in scored:
            key = (
                str(item.metadata.get("file_path", "")),
                item.text[:120],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= final_top_k:
                break

        return deduped

    def _normalize_semantic(self, score: float) -> float:
        # Cosine similarity may arrive in [-1, 1] or [0, 1] depending on backend.
        return max(0.0, min(1.0, (score + 1.0) / 2.0 if score < 0 else score))

    def _lexical_overlap(
        self,
        query_terms: set[str],
        item: VectorSearchResult,
    ) -> float:
        if not query_terms:
            return 0.0

        text_terms = self._tokenize(item.text)
        file_path = str(item.metadata.get("file_path", ""))
        text_terms.update(self._tokenize(file_path))

        if not text_terms:
            return 0.0

        overlap = query_terms.intersection(text_terms)
        return len(overlap) / len(query_terms)

    def _symbol_boost(self, item: VectorSearchResult, symbol_hints: list[str]) -> float:
        if not symbol_hints:
            return 0.0

        haystack = (
            item.text.lower() + "\n" + str(item.metadata.get("file_path", "")).lower()
        )

        for symbol in symbol_hints:
            if symbol.lower() in haystack:
                return 0.08
        return 0.0

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if token}
