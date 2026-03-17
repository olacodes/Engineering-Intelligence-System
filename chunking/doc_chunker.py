"""Chunking strategy for markdown and documentation artifacts."""

from __future__ import annotations

import math
import re
from typing import Any

from models.knowledge_models import KnowledgeItem

from .chunk_models import KnowledgeChunk

MAX_TOKENS_PER_CHUNK = 800
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)\s*$")


class DocChunker:
    """Chunk documentation by markdown headings with size fallback."""

    def chunk(self, item: KnowledgeItem) -> list[KnowledgeChunk]:
        """Create document chunks that preserve heading context."""
        sections = self._split_by_headings(item.content)

        if not sections:
            return [
                self._to_chunk(item, text) for text in self._split_by_size(item.content)
            ]

        chunks: list[KnowledgeChunk] = []
        for heading, body in sections:
            section_text = body if not heading else f"{heading}\n\n{body}".strip()
            parts = self._split_by_size(section_text)
            for part in parts:
                metadata_extra: dict[str, Any] = {}
                if heading:
                    metadata_extra["heading"] = heading
                chunks.append(self._to_chunk(item, part, metadata_extra))

        return chunks

    def _split_by_headings(self, content: str) -> list[tuple[str, str]]:
        lines = content.splitlines()
        if not lines:
            return []

        sections: list[tuple[str, str]] = []
        current_heading = ""
        current_lines: list[str] = []

        for line in lines:
            match = HEADING_PATTERN.match(line)
            if match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines).strip()))
                    current_lines = []
                current_heading = line.strip()
                continue

            current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines).strip()))

        return [section for section in sections if section[1]]

    def _split_by_size(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        if self._estimate_tokens(normalized) <= MAX_TOKENS_PER_CHUNK:
            return [normalized]

        paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
        if not paragraphs:
            return self._hard_split(normalized)

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if self._estimate_tokens(candidate) <= 700:
                current = candidate
                continue

            if current:
                chunks.append(current)
            current = paragraph

        if current:
            chunks.append(current)

        final_chunks: list[str] = []
        for chunk in chunks:
            if self._estimate_tokens(chunk) <= MAX_TOKENS_PER_CHUNK:
                final_chunks.append(chunk)
            else:
                final_chunks.extend(self._hard_split(chunk))

        return [chunk for chunk in final_chunks if chunk]

    def _hard_split(self, text: str) -> list[str]:
        max_chars = 3000
        normalized = text.strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0

        while start < len(normalized):
            end = min(len(normalized), start + max_chars)
            if end < len(normalized):
                split_point = normalized.rfind("\n", start, end)
                if split_point > start + 200:
                    end = split_point
            chunks.append(normalized[start:end].strip())
            start = end

        return [chunk for chunk in chunks if chunk]

    def _to_chunk(
        self,
        item: KnowledgeItem,
        text: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> KnowledgeChunk:
        metadata: dict[str, Any] = {
            "source_type": "documentation",
            "repo": item.repo,
            "file_path": item.file_path,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        return KnowledgeChunk(parent_id=item.id, text=text, metadata=metadata)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / 4))
