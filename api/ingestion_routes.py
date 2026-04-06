"""FastAPI routes for ingestion and indexing operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from .dependencies import get_ingestion_controller
from .ingestion_controller import IngestionController
from .ingestion_job_manager import job_manager
from .ingestion_models import (
    AsyncJobAcceptedResponse,
    DocsIngestRequest,
    IngestionJobStatusResponse,
    IndexAllRequest,
    IndexAllResponse,
    IndexResponse,
    PRIngestRequest,
    RepositoryIngestRequest,
)

router = APIRouter(tags=["Ingestion API"])


@router.post("/ingest/repository")
async def ingest_repository(
    request: RepositoryIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> IndexResponse:
    """Ingest and index a source code repository."""
    return await run_in_threadpool(controller.ingest_repository, request)


@router.post("/ingest/repository/async")
async def ingest_repository_async(
    request: RepositoryIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> AsyncJobAcceptedResponse:
    """Start repository ingestion in the background and return a polling handle."""
    job_id = job_manager.submit(
        source="repository",
        task=lambda: controller.ingest_repository(request),
    )

    return AsyncJobAcceptedResponse(
        job_id=job_id,
        status="running",
        source="repository",
        status_url=f"/ingest/jobs/{job_id}",
    )


@router.post("/ingest/docs")
async def ingest_docs(
    request: DocsIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> IndexResponse:
    """Ingest and index documentation content."""
    return await run_in_threadpool(controller.ingest_docs, request)


@router.post("/ingest/docs/async")
async def ingest_docs_async(
    request: DocsIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> AsyncJobAcceptedResponse:
    """Start docs ingestion in the background and return a polling handle."""
    job_id = job_manager.submit(
        source="docs",
        task=lambda: controller.ingest_docs(request),
    )

    return AsyncJobAcceptedResponse(
        job_id=job_id,
        status="running",
        source="docs",
        status_url=f"/ingest/jobs/{job_id}",
    )


@router.post("/ingest/prs")
async def ingest_prs(
    request: PRIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> IndexResponse:
    """Ingest and index pull request discussions."""
    return await run_in_threadpool(controller.ingest_prs, request)


@router.post("/ingest/prs/async")
async def ingest_prs_async(
    request: PRIngestRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> AsyncJobAcceptedResponse:
    """Start PR ingestion in the background and return a polling handle."""
    job_id = job_manager.submit(
        source="prs",
        task=lambda: controller.ingest_prs(request),
    )

    return AsyncJobAcceptedResponse(
        job_id=job_id,
        status="running",
        source="prs",
        status_url=f"/ingest/jobs/{job_id}",
    )


@router.post("/index/all")
async def index_all(
    request: IndexAllRequest,
    controller: Annotated[IngestionController, Depends(get_ingestion_controller)],
) -> IndexAllResponse:
    """Run indexing pipeline for all provided source request payloads."""
    return await run_in_threadpool(controller.index_all, request)


@router.get(
    "/ingest/jobs/{job_id}",
    responses={404: {"description": "Ingestion job not found"}},
)
async def get_ingestion_job_status(job_id: str) -> IngestionJobStatusResponse:
    """Return the current status and optional result for an async ingestion job."""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Ingestion job '{job_id}' not found"
        )

    return IngestionJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        source=job.source,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
        error=job.error,
    )
