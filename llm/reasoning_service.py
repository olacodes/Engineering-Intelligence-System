"""Reasoning orchestration: QueryContext -> Prompt -> LLM -> LLMAnswer."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from retrieval.query_models import QueryContext

from utils.logger import get_logger

from .llm_client import LLMClient
from .llm_models import LLMAnswer
from .prompt_builder import PromptBuilder

logger = get_logger(__name__)


class ReasoningService:
    """Service that transforms retrieval output into grounded engineering answers."""

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder,
    ) -> None:
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder

    def answer_question(self, query_context: QueryContext) -> LLMAnswer:
        """Generate a structured answer constrained to retrieved sources."""
        allowed_sources = self._extract_allowed_sources(query_context)

        prompt = self._prompt_builder.build_prompt(
            question=query_context.question,
            context=query_context.context_text,
            allowed_sources=allowed_sources,
        )

        logger.info(
            "Generating LLM answer for question with %d retrieved chunks",
            len(query_context.retrieved_chunks),
        )
        raw_response = self._llm_client.generate(prompt)
        answer = self._parse_llm_response(raw_response, allowed_sources)

        logger.info(
            "Generated structured LLM answer with %d cited sources",
            len(answer.sources),
        )
        return answer

    def _extract_allowed_sources(self, query_context: QueryContext) -> list[str]:
        """Collect deduplicated source identifiers from retrieved chunks."""
        sources: list[str] = []

        for chunk in query_context.retrieved_chunks:
            source = str(chunk.metadata.get("file_path") or "unknown")
            if source != "unknown" and source not in sources:
                sources.append(source)

        return sources

    def _parse_llm_response(
        self,
        raw_response: str,
        allowed_sources: list[str],
    ) -> LLMAnswer:
        """Parse model JSON and sanitize output to prevent source hallucinations."""
        parsed = self._parse_json_payload(raw_response)

        answer_text = str(parsed.get("answer", "")).strip()
        if not answer_text:
            answer_text = PromptBuilder.FALLBACK_ANSWER

        confidence = self._coerce_confidence(parsed.get("confidence", 0.0))
        sources = self._sanitize_sources(parsed.get("sources", []), allowed_sources)

        if answer_text == PromptBuilder.FALLBACK_ANSWER:
            confidence = min(confidence, 0.2)
            sources = []
        elif not sources and allowed_sources:
            # Preserve traceability when model gives useful answer but malformed citations.
            sources = allowed_sources[: min(3, len(allowed_sources))]
            confidence = min(confidence, 0.75)

        return LLMAnswer(answer=answer_text, sources=sources, confidence=confidence)

    def _parse_json_payload(self, raw_response: str) -> dict[str, Any]:
        """Parse a JSON object from model output with tolerant fallback."""
        candidate = raw_response.strip()

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end > start:
            snippet = candidate[start : end + 1]
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                logger.warning(
                    "LLM response was not valid JSON; returning fallback answer"
                )

        return {
            "answer": PromptBuilder.FALLBACK_ANSWER,
            "sources": [],
            "confidence": 0.0,
        }

    def _sanitize_sources(
        self,
        candidate_sources: object,
        allowed_sources: list[str],
    ) -> list[str]:
        """Keep only source citations that exist in the retrieved chunk set."""
        if not isinstance(candidate_sources, list):
            return []

        canonical_map = self._build_source_canonical_map(allowed_sources)
        cleaned: list[str] = []
        for source in candidate_sources:
            text = str(source).strip()
            if not text:
                continue

            resolved = self._resolve_source(text, canonical_map)
            if resolved and resolved not in cleaned:
                cleaned.append(resolved)

        return cleaned

    def _build_source_canonical_map(self, allowed_sources: list[str]) -> dict[str, str]:
        """Build lookup map for exact and basename-based source matching."""
        canonical: dict[str, str] = {}
        for source in allowed_sources:
            key = source.strip().lower()
            if not key:
                continue
            canonical[key] = source

            basename = PurePosixPath(source).name.strip().lower()
            if basename and basename not in canonical:
                canonical[basename] = source

        return canonical

    def _resolve_source(
        self, candidate: str, canonical_map: dict[str, str]
    ) -> str | None:
        """Resolve LLM-cited source text to a canonical allowed source value."""
        normalized = candidate.strip().lower()
        if not normalized:
            return None

        if normalized in canonical_map:
            return canonical_map[normalized]

        basename = PurePosixPath(normalized).name
        if basename in canonical_map:
            return canonical_map[basename]

        return None

    def _coerce_confidence(self, value: object) -> float:
        """Normalize confidence into [0.0, 1.0]."""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0

        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric
