"""FastAPI system introspection routes for EIS."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from .dependencies import get_ingestion_controller
from .ingestion_controller import IngestionController
from .ingestion_models import HealthResponse, SourcesResponse, StatsResponse

router = APIRouter(tags=["System API"])


@router.get("/health", response_model=HealthResponse)
async def health(
    controller: IngestionController = Depends(get_ingestion_controller),
) -> HealthResponse:
    """Return runtime service health."""
    return await run_in_threadpool(controller.get_health)


@router.get("/stats", response_model=StatsResponse)
async def stats(
    controller: IngestionController = Depends(get_ingestion_controller),
) -> StatsResponse:
    """Return high-level vector index statistics."""
    return await run_in_threadpool(controller.get_stats)


@router.get("/sources", response_model=SourcesResponse)
async def sources(
    controller: IngestionController = Depends(get_ingestion_controller),
) -> SourcesResponse:
    """Return unique indexed source repositories/documentation identifiers."""
    return await run_in_threadpool(controller.get_sources)
