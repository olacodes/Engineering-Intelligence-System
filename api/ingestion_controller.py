"""Controller for ingestion, indexing, and index introspection APIs."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse

from chunking.chunk_service import ChunkService
from embeddings.embedding_service import EmbeddingService
from ingestion.doc_loader import DocLoader
from ingestion.ingestion_service import IngestionService
from ingestion.pr_loader import PRLoader
from ingestion.repo_loader import RepoLoader
from vector_store.qdrant_store import QdrantVectorStore

from utils.logger import get_logger

from .ingestion_models import (
    DocsIngestRequest,
    HealthResponse,
    IndexAllRequest,
    IndexAllResponse,
    IndexResponse,
    PRIngestRequest,
    RepositoryIngestRequest,
    SourcesResponse,
    StatsResponse,
)

logger = get_logger(__name__)


class IngestionController:
    """Coordinates source loading, chunking, embeddings, and vector upserts."""

    def __init__(
        self,
        chunk_service: ChunkService,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        upsert_batch_size: int = 200,
    ) -> None:
        if upsert_batch_size < 1:
            raise ValueError("upsert_batch_size must be >= 1")

        self._chunk_service = chunk_service
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._upsert_batch_size = upsert_batch_size

    def ingest_repository(self, request: RepositoryIngestRequest) -> IndexResponse:
        """Run full indexing pipeline for a git repository source."""
        repo_name = request.repo_name or self._derive_repo_name(request.repo_url)

        with tempfile.TemporaryDirectory(prefix="eis_ingest_repo_") as tmp_dir:
            loader = RepoLoader(
                repo_url=request.repo_url,
                local_path=str(Path(tmp_dir) / "repo"),
                repo_name=repo_name,
                branch=request.branch,
                max_files=request.max_files,
            )
            return self._index_with_loader(loader=loader, source="repository")

    def ingest_docs(self, request: DocsIngestRequest) -> IndexResponse:
        """Run full indexing pipeline for local documentation files."""
        repo_name = request.repo_name or Path(request.docs_path).resolve().name
        loader = DocLoader(
            doc_dir=request.docs_path,
            repo_name=repo_name,
            split_on_headers=request.split_on_headers,
            min_section_length=request.min_section_length,
        )
        return self._index_with_loader(loader=loader, source="docs")

    def ingest_prs(self, request: PRIngestRequest) -> IndexResponse:
        """Run full indexing pipeline for GitHub pull requests."""
        github_token = request.github_token or os.getenv("GITHUB_TOKEN")
        loader = PRLoader(
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
            github_token=github_token,
            max_prs=request.max_prs,
            status=request.status,
            include_comments=request.include_comments,
        )
        return self._index_with_loader(loader=loader, source="prs")

    def index_all(self, request: IndexAllRequest) -> IndexAllResponse:
        """Run indexing for all provided source payloads in one operation."""
        started = time.perf_counter()
        runs: list[IndexResponse] = []

        if request.repository is not None:
            runs.append(self.ingest_repository(request.repository))
        if request.docs is not None:
            runs.append(self.ingest_docs(request.docs))
        if request.prs is not None:
            runs.append(self.ingest_prs(request.prs))

        duration = time.perf_counter() - started
        return IndexAllResponse(
            runs=runs,
            total_files_ingested=sum(run.files_ingested for run in runs),
            total_chunks_created=sum(run.chunks_created for run in runs),
            total_vectors_stored=sum(run.vectors_stored for run in runs),
            duration_seconds=duration,
        )

    def get_health(self) -> HealthResponse:
        """Return service health based on vector database accessibility."""
        try:
            self._vector_store.create_collection()
            return HealthResponse(status="ok")
        except Exception as exc:  # pragma: no cover - runtime/network failure
            logger.exception("Health check failed: %s", exc)
            return HealthResponse(status="degraded")

    def get_stats(self) -> StatsResponse:
        """Return basic index statistics for current vector collection."""
        client = self._vector_store._client
        collection_name = self._vector_store._collection_name

        try:
            collection_info = client.get_collection(collection_name=collection_name)
            total_chunks = int(getattr(collection_info, "points_count", 0) or 0)
        except Exception as exc:  # pragma: no cover - runtime/network failure
            logger.warning(
                "Unable to read collection stats for '%s': %s",
                collection_name,
                exc,
            )
            total_chunks = 0

        sources = self._list_sources(limit=5000)

        return StatsResponse(
            total_chunks=total_chunks,
            total_sources=len(sources),
            vector_collection=collection_name,
        )

    def get_sources(self) -> SourcesResponse:
        """Return unique indexed source repository names from vector payload metadata."""
        return SourcesResponse(sources=self._list_sources(limit=10000))

    def _index_with_loader(self, loader: object, source: str) -> IndexResponse:
        """Execute ingestion->chunking->embedding->upsert pipeline for one loader."""
        started = time.perf_counter()
        logger.info("Starting %s ingestion/indexing run", source)

        ingestion_service = IngestionService(loaders=[loader], deduplicate=True)
        knowledge_items = ingestion_service.run()
        knowledge_chunks = self._chunk_service.chunk_items(knowledge_items)
        embedded_chunks = self._embedding_service.embed_chunks(knowledge_chunks)

        for start in range(0, len(embedded_chunks), self._upsert_batch_size):
            batch = embedded_chunks[start : start + self._upsert_batch_size]
            self._vector_store.upsert_chunks(batch)

        duration = time.perf_counter() - started
        logger.info(
            "%s ingestion/indexing complete: items=%d chunks=%d vectors=%d duration=%.2fs",
            source,
            len(knowledge_items),
            len(knowledge_chunks),
            len(embedded_chunks),
            duration,
        )

        return IndexResponse(
            files_ingested=len(knowledge_items),
            chunks_created=len(knowledge_chunks),
            vectors_stored=len(embedded_chunks),
            duration_seconds=duration,
            source=source,
        )

    def _list_sources(self, limit: int) -> list[str]:
        """Read unique `metadata.repo` values from current vector collection."""
        client = self._vector_store._client
        collection_name = self._vector_store._collection_name

        try:
            points, _ = client.scroll(
                collection_name=collection_name,
                with_payload=True,
                with_vectors=False,
                limit=limit,
            )
        except Exception as exc:  # pragma: no cover - runtime/network failure
            logger.warning(
                "Unable to list sources from collection '%s': %s",
                collection_name,
                exc,
            )
            return []

        unique_sources: list[str] = []
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
            repo = str(metadata.get("repo", "")).strip()
            if repo and repo not in unique_sources:
                unique_sources.append(repo)

        return sorted(unique_sources)

    def _derive_repo_name(self, repo_url: str) -> str:
        """Derive owner/repo slug from URL/path input."""
        candidate = repo_url.strip().rstrip("/")
        if candidate.endswith(".git"):
            candidate = candidate[:-4]

        parsed = urlparse(candidate)
        if parsed.scheme and parsed.path:
            path = parsed.path.strip("/")
            if path:
                return path

        return Path(candidate).name or "unknown/repo"
