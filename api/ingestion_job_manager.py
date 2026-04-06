"""In-memory background job manager for long-running ingestion operations."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Callable
from uuid import uuid4

from .ingestion_models import IndexResponse


@dataclass
class IngestionJobRecord:
    """Mutable state for one ingestion background job."""

    job_id: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    result: IndexResponse | None = None
    error: str | None = None


class IngestionJobManager:
    """Tracks and executes ingestion jobs in a bounded background executor."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, IngestionJobRecord] = {}
        self._lock = Lock()

    def submit(self, source: str, task: Callable[[], IndexResponse]) -> str:
        """Submit a background ingestion task and return its job ID."""
        now = datetime.now(UTC)
        job_id = str(uuid4())

        with self._lock:
            self._jobs[job_id] = IngestionJobRecord(
                job_id=job_id,
                status="queued",
                source=source,
                created_at=now,
                updated_at=now,
            )

        future = self._executor.submit(task)
        future.add_done_callback(lambda fut: self._on_complete(job_id, fut))

        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.updated_at = datetime.now(UTC)

        return job_id

    def get(self, job_id: str) -> IngestionJobRecord | None:
        """Return job state if available."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return IngestionJobRecord(
                job_id=job.job_id,
                status=job.status,
                source=job.source,
                created_at=job.created_at,
                updated_at=job.updated_at,
                result=job.result,
                error=job.error,
            )

    def _on_complete(self, job_id: str, future: Future[IndexResponse]) -> None:
        """Persist terminal state for a completed background task."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.updated_at = datetime.now(UTC)

            try:
                job.result = future.result()
                job.status = "succeeded"
                job.error = None
            except Exception as exc:  # pragma: no cover - runtime path
                job.result = None
                job.status = "failed"
                job.error = str(exc)


job_manager = IngestionJobManager()
