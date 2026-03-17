"""Service entry point for converting knowledge items into semantic chunks."""

from __future__ import annotations

from typing import Protocol

from models.knowledge_models import KnowledgeItem

from .chunk_models import KnowledgeChunk
from .code_chunker import CodeChunker
from .doc_chunker import DocChunker
from .pr_chunker import PRChunker


class Chunker(Protocol):
    """Protocol contract implemented by all chunkers."""

    def chunk(self, item: KnowledgeItem) -> list[KnowledgeChunk]:
        """Return chunks for a single item."""


class ChunkService:
    """Select source-specific chunkers and produce normalized chunks."""

    def __init__(self) -> None:
        self._code_chunker = CodeChunker()
        self._pr_chunker = PRChunker()
        self._doc_chunker = DocChunker()

    def chunk_items(self, items: list[KnowledgeItem]) -> list[KnowledgeChunk]:
        """Chunk a batch of knowledge items."""
        chunks: list[KnowledgeChunk] = []

        for item in items:
            chunker = self._get_chunker(item)
            chunks.extend(chunker.chunk(item))

        return chunks

    def _get_chunker(self, item: KnowledgeItem) -> Chunker:
        source_type = item.source_type.value.lower().strip()

        if source_type in {"code", "code_file"}:
            return self._code_chunker
        if source_type == "pull_request":
            return self._pr_chunker
        if source_type == "documentation":
            return self._doc_chunker

        # Unknown source types default to documentation-safe chunking.
        return self._doc_chunker
