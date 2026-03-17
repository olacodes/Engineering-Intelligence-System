"""FastAPI routes for ingestion and indexing operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from .dependencies import get_ingestion_controller
from .ingestion_controller import IngestionController
from .ingestion_models import (
    DocsIngestRequest,
    IndexAllRequest,
    IndexAllResponse,
    IndexResponse,
    PRIngestRequest,
    RepositoryIngestRequest,
)

router = APIRouter(tags=["Ingestion API"])


@router.post("/ingest/repository", response_model=IndexResponse)
async def ingest_repository(
    request: RepositoryIngestRequest,
    controller: IngestionController = Depends(get_ingestion_controller),
) -> IndexResponse:
    """Ingest and index a source code repository."""
    return await run_in_threadpool(controller.ingest_repository, request)


@router.post("/ingest/docs", response_model=IndexResponse)
async def ingest_docs(
    request: DocsIngestRequest,
    controller: IngestionController = Depends(get_ingestion_controller),
) -> IndexResponse:
    """Ingest and index documentation content."""
    return await run_in_threadpool(controller.ingest_docs, request)


@router.post("/ingest/prs", response_model=IndexResponse)
async def ingest_prs(
    request: PRIngestRequest,
    controller: IngestionController = Depends(get_ingestion_controller),
) -> IndexResponse:
    """Ingest and index pull request discussions."""
    return await run_in_threadpool(controller.ingest_prs, request)


@router.post("/index/all", response_model=IndexAllResponse)
async def index_all(
    request: IndexAllRequest,
    controller: IngestionController = Depends(get_ingestion_controller),
) -> IndexAllResponse:
    """Run indexing pipeline for all provided source request payloads."""
    return await run_in_threadpool(controller.index_all, request)
