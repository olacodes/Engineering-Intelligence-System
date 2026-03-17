"""Assemble vector-search results into LLM-ready context text."""

from __future__ import annotations

from collections import defaultdict

from vector_store.vector_models import VectorSearchResult


class ContextBuilder:
    """Formats retrieved chunks while preserving source traceability."""

    def __init__(
        self, max_context_chars: int = 12000, max_context_chunks: int = 12
    ) -> None:
        if max_context_chars < 500:
            raise ValueError("max_context_chars must be >= 500")
        if max_context_chunks < 1:
            raise ValueError("max_context_chunks must be >= 1")
        self._max_context_chars = max_context_chars
        self._max_context_chunks = max_context_chunks

    def build_context(
        self,
        chunks: list[VectorSearchResult],
        query_type: str = "implementation",
    ) -> str:
        """Return structured context string bounded by configured char limit."""
        if not chunks:
            return "Context:\n\nNo relevant chunks were retrieved."

        sections: list[str] = [
            "Context:",
            f"Query type: {query_type}",
            "",
            "Chunks are grouped by source type and reranked globally.",
        ]
        current_length = len(sections[0])
        included = 0

        grouped = self._group_by_source_type(chunks)

        index = 1
        for source_type in ("code", "doc", "pr", "unknown"):
            source_chunks = grouped.get(source_type, [])
            if not source_chunks:
                continue

            header = f"=== Source: {source_type} ==="
            if current_length + len(header) + 2 <= self._max_context_chars:
                sections.append(header)
                current_length += len(header) + 2

            for chunk in source_chunks:
                if included >= self._max_context_chunks:
                    sections.append("[Context truncated: chunk limit reached]")
                    return "\n\n".join(sections)

                block = self._format_chunk(index=index, chunk=chunk)

                if current_length + len(block) + 2 > self._max_context_chars:
                    sections.append("[Context truncated: character limit reached]")
                    return "\n\n".join(sections)

                sections.append(block)
                current_length += len(block) + 2
                included += 1
                index += 1

        return "\n\n".join(sections)

    def _group_by_source_type(
        self, chunks: list[VectorSearchResult]
    ) -> dict[str, list[VectorSearchResult]]:
        grouped: dict[str, list[VectorSearchResult]] = defaultdict(list)
        for chunk in chunks:
            source_type = str(chunk.metadata.get("source_type") or "unknown").lower()
            grouped[source_type].append(chunk)
        return grouped

    def _format_chunk(self, index: int, chunk: VectorSearchResult) -> str:
        metadata = chunk.metadata
        source = str(metadata.get("file_path") or metadata.get("source", "unknown"))
        source_type = str(metadata.get("source_type", "unknown"))
        repo = str(metadata.get("repo", "unknown"))
        function_name = metadata.get("function")
        class_name = metadata.get("class")
        section = metadata.get("section")
        retrieval_score = metadata.get("retrieval_score")
        symbols = metadata.get("symbols")

        lines: list[str] = [
            f"[{index}] Source: {source}",
            f"Type: {source_type}",
            f"Repository: {repo}",
            f"Score: {chunk.score:.4f}",
        ]

        if class_name:
            lines.append(f"Class: {class_name}")
        if function_name:
            lines.append(f"Function: {function_name}")
        if section:
            lines.append(f"Section: {section}")
        if retrieval_score is not None:
            lines.append(f"Re-rank score: {retrieval_score}")
        if symbols:
            lines.append(f"Symbols: {symbols}")

        lines.extend(["", "Content:", chunk.text.strip()])
        return "\n".join(lines)
