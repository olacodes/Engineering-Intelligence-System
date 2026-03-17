"""
Ingestion pipeline layer for the Engineering Intelligence System.

This module provides loaders for extracting knowledge from:
- Git repositories (source code)
- GitHub Pull Requests (engineering discussions)
- Markdown documentation (architecture and guides)

Example:
    from ingestion.repo_loader import RepoLoader
    from ingestion.pr_loader import PRLoader
    from ingestion.doc_loader import DocLoader
    from ingestion.ingestion_service import IngestionService

    service = IngestionService(
        loaders=[
            RepoLoader(...),
            PRLoader(...),
            DocLoader(...),
        ]
    )
    items = service.run()
"""

from .base_loader import BaseLoader
from .repo_loader import RepoLoader
from .pr_loader import PRLoader
from .doc_loader import DocLoader
from .ingestion_service import IngestionService

__all__ = [
    "BaseLoader",
    "RepoLoader",
    "PRLoader",
    "DocLoader",
    "IngestionService",
]
