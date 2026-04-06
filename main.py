"""
Engineering Intelligence System (EIS) - Main Application Entry Point

This module initializes and runs the EIS application. It sets up:
- FastAPI application with middleware
- Configuration loading
- Dependency injection
- Health check endpoints
- API route registration
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.ingestion_routes import router as ingestion_router
from api.routes import router as query_router
from api.system_routes import router as system_router
from config import get_settings, Settings
from models.knowledge_models import (
    KnowledgeItem,
    SearchQuery,
    SearchResult,
)
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class EISApplication:
    """
    Core application class managing EIS lifecycle and dependencies.

    This class encapsulates the application state, configuration, and
    shared dependencies used across the system.
    """

    def __init__(self):
        """Initialize the EIS application."""
        self.settings: Settings = get_settings()
        self.app: Optional[FastAPI] = None
        logger.info(
            f"EIS initialized: {self.settings.app_name} v{self.settings.app_version}"
        )

    def create_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application.

        Returns:
            Configured FastAPI application instance
        """

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage application lifecycle events."""
            logger.info("EIS application starting up")
            # Startup logic would go here (connect to Qdrant, etc.)
            yield
            logger.info("EIS application shutting down")
            # Cleanup logic would go here

        # Create FastAPI application
        self.app = FastAPI(
            title=self.settings.app_name,
            description="A Retrieval Augmented Generation system for engineering knowledge",
            version=self.settings.app_version,
            root_path=self.settings.api_root_path,
            lifespan=lifespan,
            debug=self.settings.debug,
        )

        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.get_cors_origins(),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._register_routes()

        logger.info(
            f"FastAPI application created (host={self.settings.api_host}:{self.settings.api_port})"
        )
        return self.app

    def _register_routes(self) -> None:
        """Register all API routes."""

        @self.app.get("/", tags=["System"])
        async def root() -> dict:
            """Root endpoint with system information."""
            return {
                "app": self.settings.app_name,
                "version": self.settings.app_version,
                "environment": self.settings.environment,
                "docs": "/docs",
                "health": "/health",
                "ask": "/api/ask",
                "ingest_repository": "/ingest/repository",
                "ingest_repository_async": "/ingest/repository/async",
                "ingest_docs": "/ingest/docs",
                "ingest_docs_async": "/ingest/docs/async",
                "ingest_prs": "/ingest/prs",
                "ingest_prs_async": "/ingest/prs/async",
                "ingest_job_status": "/ingest/jobs/{job_id}",
                "index_all": "/index/all",
                "stats": "/stats",
                "sources": "/sources",
            }

        # Placeholder routes for future implementation
        @self.app.post("/api/knowledge/ingest", tags=["Ingestion"])
        async def ingest_knowledge(item: KnowledgeItem) -> dict:
            """
            Ingest a knowledge item into the system.

            Args:
                item: Knowledge item to ingest

            Returns:
                Confirmation of ingestion

            Note:
                Implementation pending - use ingestion pipeline layer
            """
            logger.info(f"[PLACEHOLDER] Ingesting knowledge item: {item.id}")
            return {
                "status": "pending",
                "item_id": str(item.id),
                "message": "Ingestion pipeline not yet implemented",
            }

        @self.app.post(
            "/api/search", response_model=list[SearchResult], tags=["Retrieval"]
        )
        async def search_knowledge(query: SearchQuery) -> list[SearchResult]:
            """
            Search for knowledge items based on natural language query.

            Args:
                query: Search query parameters

            Returns:
                List of matching knowledge items ranked by relevance

            Note:
                Implementation pending - use retrieval system layer
            """
            logger.info(f"[PLACEHOLDER] Searching knowledge base: {query.query_text}")
            raise HTTPException(
                status_code=501, detail="Search functionality not yet implemented"
            )

        @self.app.get("/api/config", tags=["System"])
        async def get_config() -> dict:
            """
            Get current system configuration (safe subset).

            Does not expose sensitive information like API keys.
            """
            return {
                "embedding": self.settings.get_embedding_config(),
                "llm": self.settings.get_llm_config(),
                "chunking": self.settings.get_chunking_config(),
            }

        self.app.include_router(query_router, prefix="/api")
        self.app.include_router(ingestion_router)
        self.app.include_router(system_router)

        logger.info("API routes registered successfully")


def create_application() -> FastAPI:
    """
    Application factory function.

    Creates and returns a configured FastAPI application ready for deployment.

    Returns:
        Configured FastAPI application

    Example:
        ```python
        if __name__ == "__main__":
            app = create_application()
            uvicorn.run(app, host="0.0.0.0", port=8000)
        ```
    """
    eis = EISApplication()
    return eis.create_app()


# Create the application instance
app = create_application()


if __name__ == "__main__":
    """
    Run the application with uvicorn.

    Command:
        python main.py

    For production:
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    import uvicorn

    settings = get_settings()

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Server: {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        # Running via `python main.py` requires reload=False; reload mode needs import string.
        reload=False,
    )
