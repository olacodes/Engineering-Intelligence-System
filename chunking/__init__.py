"""Chunking layer for transforming knowledge items into retrieval-ready chunks."""

from .chunk_models import KnowledgeChunk
from .chunk_service import ChunkService

__all__ = ["KnowledgeChunk", "ChunkService"]
