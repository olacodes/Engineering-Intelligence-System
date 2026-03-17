"""Query understanding utilities for multi-stage retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


SOURCE_TYPES = ("code", "pr", "doc")


@dataclass(frozen=True)
class QueryPlan:
    """Classifier output used to drive retrieval strategy."""

    query_type: str
    source_top_k: dict[str, int]
    source_weight: dict[str, float]
    metadata_filters: dict[str, dict[str, object]] = field(default_factory=dict)
    symbol_hints: list[str] = field(default_factory=list)


class QueryClassifier:
    """Classify engineering questions to select retrieval strategy."""

    _IMPLEMENTATION_PATTERNS = (
        "where is",
        "implemented",
        "implementation",
        "defined",
        "located",
        "calculate",
        "how does",
    )
    _DEPENDENCY_PATTERNS = (
        "depend",
        "dependency",
        "uses",
        "used by",
        "calls",
        "invokes",
        "references",
        "coupled",
    )
    _HISTORY_PATTERNS = (
        "why",
        "introduced",
        "history",
        "when was",
        "pr",
        "pull request",
        "rationale",
        "decision",
    )

    def classify(self, question: str, top_k: int) -> QueryPlan:
        """Return a query plan with per-source retrieval budgets and priorities."""
        normalized = question.strip().lower()
        if not normalized:
            raise ValueError("question cannot be empty")

        query_type = self._infer_query_type(normalized)
        source_weight = self._source_weights_for(query_type)
        source_top_k = self._source_topk_for(top_k=top_k, query_type=query_type)
        symbol_hints = self._extract_symbol_hints(question)

        metadata_filters = {source: {"source_type": source} for source in SOURCE_TYPES}
        if symbol_hints:
            # If chunk metadata stores symbols as arrays, Qdrant match can still hit when value is present.
            metadata_filters["code"]["symbols"] = symbol_hints[0]

        return QueryPlan(
            query_type=query_type,
            source_top_k=source_top_k,
            source_weight=source_weight,
            metadata_filters=metadata_filters,
            symbol_hints=symbol_hints,
        )

    def _infer_query_type(self, normalized_question: str) -> str:
        if any(p in normalized_question for p in self._HISTORY_PATTERNS):
            return "history"
        if any(p in normalized_question for p in self._DEPENDENCY_PATTERNS):
            return "dependency"
        if any(p in normalized_question for p in self._IMPLEMENTATION_PATTERNS):
            return "implementation"
        return "implementation"

    def _source_weights_for(self, query_type: str) -> dict[str, float]:
        if query_type == "history":
            return {"code": 0.15, "pr": 0.60, "doc": 0.25}
        if query_type == "dependency":
            return {"code": 0.60, "pr": 0.10, "doc": 0.30}
        return {"code": 0.55, "pr": 0.15, "doc": 0.30}

    def _source_topk_for(self, top_k: int, query_type: str) -> dict[str, int]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        # Over-retrieve per source to improve reranking quality.
        retrieval_budget = max(6, top_k * 2)

        weights = self._source_weights_for(query_type)
        raw = {
            source: max(2, int(round(retrieval_budget * weights[source])))
            for source in SOURCE_TYPES
        }

        # Keep total near budget while preserving minimum coverage from each source.
        while sum(raw.values()) > retrieval_budget:
            richest = max(raw, key=raw.get)
            if raw[richest] > 2:
                raw[richest] -= 1
            else:
                break

        return raw

    def _extract_symbol_hints(self, question: str) -> list[str]:
        backtick_symbols = re.findall(r"`([^`]+)`", question)

        token_candidates = re.findall(r"[A-Za-z_]\w{2,}", question)
        symbolish = [
            token
            for token in token_candidates
            if "_" in token or any(char.isupper() for char in token[1:])
        ]

        ordered: list[str] = []
        for value in backtick_symbols + symbolish:
            cleaned = value.strip()
            if cleaned and cleaned not in ordered:
                ordered.append(cleaned)

        return ordered
