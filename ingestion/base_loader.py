"""
Abstract base class for all knowledge loaders.

This module defines the interface that all loaders must implement,
ensuring consistent behavior across different data sources.
"""

from abc import ABC, abstractmethod
from typing import List

from models import KnowledgeItem
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseLoader(ABC):
    """
    Abstract base class for knowledge source loaders.

    All loaders must implement the load() method to convert external data sources
    into a unified list of KnowledgeItem objects.
    """

    def __init__(self, name: str):
        """
        Initialize the loader.

        Args:
            name: Human-readable name for this loader
        """
        self.name = name
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def load(self) -> List[KnowledgeItem]:
        """
        Load knowledge items from the data source.

        Returns:
            List of KnowledgeItem objects extracted from the source

        Raises:
            Exception: Various exceptions depending on the loader implementation
        """
        pass

    def _log_load_result(
        self, items: List[KnowledgeItem], duration_seconds: float
    ) -> None:
        """
        Log the results of a load operation.

        Args:
            items: List of loaded items
            duration_seconds: Time taken to load
        """
        self.logger.info(
            f"{self.name} loaded {len(items)} items in {duration_seconds:.2f}s"
        )
