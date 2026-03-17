"""Code-aware chunking strategy for source files."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from models.knowledge_models import KnowledgeItem

from .chunk_models import KnowledgeChunk

MAX_TOKENS_PER_CHUNK = 800


@dataclass(frozen=True)
class _CodeBlock:
    """Internal representation of a code block boundary."""

    start_line: int
    end_line: int
    text: str
    function_name: str | None
    class_name: str | None


class CodeChunker:
    """Chunk code with function/class boundaries first, size fallback second."""

    _function_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("),
        re.compile(r"^\s*function\s+([A-Za-z_]\w*)\s*\("),
        re.compile(
            r"^\s*(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
        ),
        re.compile(
            r"^\s*(?:public|private|protected|internal|static|final|override|suspend|async|virtual|inline|\w+)\s+"
            r"(?:[A-Za-z_]\w*[<>\[\],? ]*\s+)?([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?"
        ),
    )
    _class_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
        re.compile(
            r"^\s*(?:public|private|protected|internal|abstract|final)?\s*class\s+([A-Za-z_]\w*)"
        ),
    )

    def chunk(self, item: KnowledgeItem) -> list[KnowledgeChunk]:
        """Create code chunks while preserving semantic boundaries where possible."""
        blocks = self._extract_blocks(item.content)
        if not blocks:
            blocks = [
                _CodeBlock(
                    start_line=1,
                    end_line=max(1, len(item.content.splitlines())),
                    text=item.content,
                    function_name=None,
                    class_name=None,
                )
            ]

        chunks: list[KnowledgeChunk] = []
        for block in blocks:
            if self._estimate_tokens(block.text) <= MAX_TOKENS_PER_CHUNK:
                chunks.append(
                    self._to_chunk(
                        item, block.text, block.function_name, block.class_name
                    )
                )
                continue

            for part in self._split_large_block(block.text):
                chunks.append(
                    self._to_chunk(item, part, block.function_name, block.class_name)
                )

        return chunks

    def _extract_blocks(self, content: str) -> list[_CodeBlock]:
        """Find function-level (or class-level) block boundaries by line signatures."""
        lines = content.splitlines()
        if not lines:
            return []

        boundaries: list[tuple[int, str | None, str | None]] = []
        current_class: str | None = None

        for index, line in enumerate(lines):
            class_name = self._extract_class_name(line)
            if class_name:
                current_class = class_name
                boundaries.append((index, None, class_name))
                continue

            function_name = self._extract_function_name(line)
            if function_name:
                boundaries.append((index, function_name, current_class))

        if not boundaries:
            return []

        blocks: list[_CodeBlock] = []

        if boundaries[0][0] > 0:
            preamble_text = "\n".join(lines[0 : boundaries[0][0]]).strip()
            if preamble_text:
                blocks.append(
                    _CodeBlock(
                        start_line=1,
                        end_line=boundaries[0][0],
                        text=preamble_text,
                        function_name=None,
                        class_name=None,
                    )
                )

        for index, (start, function_name, class_name) in enumerate(boundaries):
            next_start = (
                boundaries[index + 1][0] if index + 1 < len(boundaries) else len(lines)
            )
            text = "\n".join(lines[start:next_start]).strip()
            if not text:
                continue
            blocks.append(
                _CodeBlock(
                    start_line=start + 1,
                    end_line=next_start,
                    text=text,
                    function_name=function_name,
                    class_name=class_name,
                )
            )

        return blocks

    def _extract_function_name(self, line: str) -> str | None:
        for pattern in self._function_patterns:
            match = pattern.match(line)
            if match:
                return match.group(1)
        return None

    def _extract_class_name(self, line: str) -> str | None:
        for pattern in self._class_patterns:
            match = pattern.match(line)
            if match:
                return match.group(1)
        return None

    def _split_large_block(self, text: str) -> list[str]:
        """Fallback splitter for oversized blocks using line-aware windows."""
        lines = text.splitlines()
        if not lines:
            return []

        target_tokens = 700
        parts: list[str] = []
        current_lines: list[str] = []

        for line in lines:
            candidate_lines = current_lines + [line]
            candidate = "\n".join(candidate_lines).strip()
            if (
                candidate
                and self._estimate_tokens(candidate) > target_tokens
                and current_lines
            ):
                parts.append("\n".join(current_lines).strip())
                current_lines = [line]
            else:
                current_lines = candidate_lines

        if current_lines:
            parts.append("\n".join(current_lines).strip())

        final_parts: list[str] = []
        for part in parts:
            if self._estimate_tokens(part) <= MAX_TOKENS_PER_CHUNK:
                final_parts.append(part)
                continue

            final_parts.extend(self._hard_split(part))

        return [part for part in final_parts if part.strip()]

    def _hard_split(self, text: str) -> list[str]:
        """Last-resort splitter to guarantee chunk size constraints."""
        max_chars = 3000
        step = 2800
        normalized = text.strip()
        if not normalized:
            return []
        if len(normalized) <= max_chars:
            return [normalized]

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + max_chars)
            if end < len(normalized):
                split_point = normalized.rfind("\n", start, end)
                if split_point > start + 200:
                    end = split_point
            chunks.append(normalized[start:end].strip())
            start = max(end, start + step)

        return [chunk for chunk in chunks if chunk]

    def _to_chunk(
        self,
        item: KnowledgeItem,
        text: str,
        function_name: str | None,
        class_name: str | None,
    ) -> KnowledgeChunk:
        metadata: dict[str, Any] = {
            "source_type": self._normalize_source_type(item.source_type.value),
            "repo": item.repo,
            "file_path": item.file_path,
        }
        if function_name:
            metadata["function"] = function_name
        if class_name:
            metadata["class"] = class_name

        return KnowledgeChunk(parent_id=item.id, text=text, metadata=metadata)

    def _normalize_source_type(self, value: str) -> str:
        if value in {"code", "code_file"}:
            return "code"
        return value

    def _estimate_tokens(self, text: str) -> int:
        # ~4 characters/token is a conservative estimate for code-like text.
        return max(1, math.ceil(len(text) / 4))
