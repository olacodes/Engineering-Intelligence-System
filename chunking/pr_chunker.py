"""Chunking strategy for pull request artifacts."""

from __future__ import annotations

import math
import re
from typing import Any

from models.knowledge_models import KnowledgeItem

from .chunk_models import KnowledgeChunk

MAX_TOKENS_PER_CHUNK = 800
BULLET_PATTERN = re.compile(r"^(?:- |\* |\d+\.\s)")


class PRChunker:
    """Chunk PR content into title, description and comment chunks."""

    def chunk(self, item: KnowledgeItem) -> list[KnowledgeChunk]:
        """Create semantically grouped chunks from PR payloads."""
        title, description, comments = self._extract_pr_sections(item)

        chunks: list[KnowledgeChunk] = []

        for part in self._fit_to_limit(title):
            chunks.append(self._to_chunk(item, part, section="title"))

        for part in self._fit_to_limit(description):
            chunks.append(self._to_chunk(item, part, section="description"))

        for index, comment in enumerate(comments, start=1):
            for part in self._fit_to_limit(comment):
                chunks.append(
                    self._to_chunk(
                        item,
                        part,
                        section="comment",
                        extra_metadata={"comment_index": index},
                    )
                )

        if not chunks:
            for part in self._fit_to_limit(item.content):
                chunks.append(self._to_chunk(item, part, section="body"))

        return chunks

    def _extract_pr_sections(self, item: KnowledgeItem) -> tuple[str, str, list[str]]:
        metadata_fields = item.metadata.custom_fields or {}
        title = self._to_non_empty_str(metadata_fields.get("title"))
        description = self._to_non_empty_str(metadata_fields.get("description"))
        comments = self._extract_comments_from_metadata(metadata_fields.get("comments"))

        if title or description or comments:
            return title, description, comments

        return self._parse_from_text(item.content)

    def _parse_from_text(self, content: str) -> tuple[str, str, list[str]]:
        lines = content.splitlines()
        title = ""
        description_lines: list[str] = []
        comments: list[str] = []

        in_comments = False
        current_comment: list[str] = []

        for raw_line in lines:
            line = raw_line.strip()
            lower = line.lower()

            if not title:
                extracted_title = self._extract_title_candidate(line, lower)
                if extracted_title:
                    title = extracted_title
                    continue

            in_comments, consumed = self._consume_comment_line(
                in_comments=in_comments,
                line=line,
                lowered_line=lower,
                current_comment=current_comment,
                comments=comments,
            )
            if consumed:
                continue

            description_lines.append(raw_line)

        self._flush_comment(current_comment, comments)

        description = "\n".join(description_lines).strip()
        return title, description, [comment for comment in comments if comment]

    def _extract_comments_from_metadata(self, raw_comments: Any) -> list[str]:
        if not isinstance(raw_comments, list):
            return []

        comments: list[str] = []
        for comment in raw_comments:
            candidate = ""
            if isinstance(comment, dict):
                candidate = self._to_non_empty_str(
                    comment.get("body") or comment.get("text")
                )
            else:
                candidate = self._to_non_empty_str(comment)

            if candidate:
                comments.append(candidate)

        return comments

    def _extract_title_candidate(self, line: str, lowered_line: str) -> str:
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if lowered_line.startswith("title:"):
            return line.split(":", 1)[1].strip()
        return ""

    def _consume_comment_line(
        self,
        in_comments: bool,
        line: str,
        lowered_line: str,
        current_comment: list[str],
        comments: list[str],
    ) -> tuple[bool, bool]:
        if lowered_line.startswith("comments:"):
            self._flush_comment(current_comment, comments)
            return True, True

        if not in_comments:
            return False, False

        if BULLET_PATTERN.match(line):
            self._flush_comment(current_comment, comments)
            current_comment.append(BULLET_PATTERN.sub("", line).strip())
            return True, True

        if line:
            current_comment.append(line)
        return True, True

    def _flush_comment(self, current_comment: list[str], comments: list[str]) -> None:
        if current_comment:
            comments.append("\n".join(current_comment).strip())
            current_comment.clear()

    def _fit_to_limit(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        if self._estimate_tokens(normalized) <= MAX_TOKENS_PER_CHUNK:
            return [normalized]

        paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
        if not paragraphs:
            return self._hard_split(normalized)

        parts: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if self._estimate_tokens(candidate) <= 700:
                current = candidate
                continue

            if current:
                parts.append(current)
            current = paragraph

        if current:
            parts.append(current)

        final_parts: list[str] = []
        for part in parts:
            if self._estimate_tokens(part) <= MAX_TOKENS_PER_CHUNK:
                final_parts.append(part)
            else:
                final_parts.extend(self._hard_split(part))

        return [part for part in final_parts if part]

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
                split_point = normalized.rfind(" ", start, end)
                if split_point > start + 200:
                    end = split_point
            chunks.append(normalized[start:end].strip())
            start = end

        return [chunk for chunk in chunks if chunk]

    def _to_chunk(
        self,
        item: KnowledgeItem,
        text: str,
        section: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> KnowledgeChunk:
        metadata: dict[str, Any] = {
            "source_type": "pull_request",
            "repo": item.repo,
            "file_path": item.file_path,
            "section": section,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        return KnowledgeChunk(parent_id=item.id, text=text, metadata=metadata)

    def _to_non_empty_str(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text

    def _estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / 4))
