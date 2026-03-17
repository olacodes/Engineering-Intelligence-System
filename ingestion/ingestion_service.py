"""
Orchestration service for managing the complete ingestion pipeline.

This service coordinates multiple loaders, aggregates results, and provides
a unified interface for ingesting knowledge from diverse sources.
"""

import time
from typing import List, Dict, Any

from models import KnowledgeItem
from ingestion.base_loader import BaseLoader
from utils.logger import get_logger

logger = get_logger(__name__)


class IngestionService:
    """
    Orchestrates the complete ingestion pipeline.

    Manages multiple loaders and coordinates knowledge extraction from diverse
    sources (repositories, PRs, documentation, etc.). Provides aggregated
    statistics and result tracking.

    Features:
    - Modular loader composition
    - Aggregated result collection
    - Execution timing and statistics
    - Error handling and recovery
    - Result deduplication (optional)

    Example:
        from ingestion.repo_loader import RepoLoader
        from ingestion.pr_loader import PRLoader
        from ingestion.doc_loader import DocLoader

        service = IngestionService(
            loaders=[
                RepoLoader(
                    repo_url="https://github.com/user/repo.git",
                    local_path="./temp/repo",
                    repo_name="user/repo"
                ),
                PRLoader(
                    repo_owner="user",
                    repo_name="repo",
                    github_token="ghp_xxx"
                ),
                DocLoader(
                    doc_dir="./docs",
                    repo_name="user/repo"
                ),
            ]
        )

        items = service.run()
        stats = service.get_statistics()
        print(f"Ingested {len(items)} items: {stats}")
    """

    def __init__(
        self,
        loaders: List[BaseLoader],
        deduplicate: bool = False,
    ):
        """
        Initialize the ingestion service.

        Args:
            loaders: List of loader instances to orchestrate
            deduplicate: Whether to deduplicate items by content hash

        Example:
            service = IngestionService(
                loaders=[repo_loader, pr_loader, doc_loader],
                deduplicate=True
            )
        """
        self.loaders = loaders
        self.deduplicate = deduplicate
        self._all_items: List[KnowledgeItem] = []
        self._statistics: Dict[str, Any] = {}
        self._start_time: float = 0
        self._end_time: float = 0

    def run(self) -> List[KnowledgeItem]:
        """
        Execute the complete ingestion pipeline.

        Runs all loaders sequentially and aggregates results.

        Returns:
            List of all KnowledgeItem objects from all loaders

        Example:
            items = service.run()
            print(f"Ingested {len(items)} items")
        """
        self._start_time = time.time()
        self._all_items = []

        logger.info(f"Starting ingestion pipeline with {len(self.loaders)} loaders")

        for loader in self.loaders:
            try:
                logger.info(f"Running loader: {loader.name}")
                items = loader.load()
                self._all_items.extend(items)
                logger.info(f"Loader {loader.name} completed: {len(items)} items")

            except Exception as e:
                logger.error(f"Loader {loader.name} failed: {e}")
                # Continue with next loader instead of failing entirely
                continue

        # Post-processing
        if self.deduplicate:
            self._all_items = self._deduplicate_items(self._all_items)
            logger.info(f"Deduplicated to {len(self._all_items)} unique items")

        self._end_time = time.time()
        self._calculate_statistics()

        logger.info(
            f"Ingestion pipeline completed in {self._end_time - self._start_time:.2f}s"
        )
        logger.info(self._format_statistics())

        return self._all_items

    def _deduplicate_items(self, items: List[KnowledgeItem]) -> List[KnowledgeItem]:
        """
        Deduplicate items by content hash.

        Removes duplicate content while preserving order and the first occurrence.

        Args:
            items: List of items to deduplicate

        Returns:
            Deduplicated list of items
        """
        seen_content_hashes: set = set()
        unique_items: List[KnowledgeItem] = []

        for item in items:
            # Create a hash of content + repo + source_type
            content_hash = hash((item.content, item.repo, item.source_type))

            if content_hash not in seen_content_hashes:
                seen_content_hashes.add(content_hash)
                unique_items.append(item)

        logger.info(
            f"Deduplication removed {len(items) - len(unique_items)} duplicate items"
        )

        return unique_items

    def _calculate_statistics(self) -> None:
        """
        Calculate ingestion statistics.

        Computes metrics about the ingestion run for reporting and monitoring.
        """
        duration = self._end_time - self._start_time

        # Count by source type
        source_type_counts: Dict[str, int] = {}
        for item in self._all_items:
            source_type = item.source_type.value
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

        # Count by repository
        repo_counts: Dict[str, int] = {}
        for item in self._all_items:
            repo = item.repo
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

        # Calculate content statistics
        total_chars = sum(len(item.content) for item in self._all_items)
        avg_content_size = total_chars / len(self._all_items) if self._all_items else 0

        self._statistics = {
            "total_items": len(self._all_items),
            "duration_seconds": duration,
            "items_per_second": len(self._all_items) / duration if duration > 0 else 0,
            "source_type_distribution": source_type_counts,
            "repository_distribution": repo_counts,
            "total_characters": total_chars,
            "avg_content_size": avg_content_size,
            "num_loaders": len(self.loaders),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get ingestion statistics.

        Returns:
            Dictionary containing ingestion metrics

        Example:
            stats = service.get_statistics()
            print(f"Ingested {stats['total_items']} items in {stats['duration_seconds']:.2f}s")
        """
        return self._statistics.copy()

    def _format_statistics(self) -> str:
        """
        Format statistics for logging.

        Returns:
            Formatted statistics string
        """
        stats = self._statistics
        lines = [
            f"Ingestion Statistics:",
            f"  Total Items: {stats.get('total_items', 0)}",
            f"  Duration: {stats.get('duration_seconds', 0):.2f}s",
            f"  Items/Second: {stats.get('items_per_second', 0):.2f}",
            f"  Total Characters: {stats.get('total_characters', 0):,}",
            f"  Avg Content Size: {stats.get('avg_content_size', 0):.0f} chars",
        ]

        # Add source type distribution
        source_types = stats.get("source_type_distribution", {})
        if source_types:
            lines.append("  By Source Type:")
            for source_type, count in source_types.items():
                lines.append(f"    - {source_type}: {count}")

        # Add repository distribution
        repos = stats.get("repository_distribution", {})
        if repos:
            lines.append("  By Repository:")
            for repo, count in sorted(repos.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"    - {repo}: {count}")

        return "\n".join(lines)

    def get_items_by_source_type(self, source_type: str) -> List[KnowledgeItem]:
        """
        Get all items from a specific source type.

        Args:
            source_type: Source type to filter by

        Returns:
            List of items matching the source type

        Example:
            code_items = service.get_items_by_source_type("code_file")
        """
        return [
            item for item in self._all_items if item.source_type.value == source_type
        ]

    def get_items_by_repo(self, repo: str) -> List[KnowledgeItem]:
        """
        Get all items from a specific repository.

        Args:
            repo: Repository identifier

        Returns:
            List of items from the repository

        Example:
            react_items = service.get_items_by_repo("facebook/react")
        """
        return [item for item in self._all_items if item.repo == repo]

    def export_items(self, format: str = "json") -> str:
        """
        Export all ingested items in a specific format.

        Currently supports JSON. Can be extended for other formats (CSV, Parquet, etc.).

        Args:
            format: Export format ("json")

        Returns:
            Serialized items

        Example:
            json_str = service.export_items(format="json")
        """
        if format == "json":
            import json

            return json.dumps(
                [item.dict() for item in self._all_items], default=str, indent=2
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def save_to_file(self, filepath: str, format: str = "json") -> None:
        """
        Save all ingested items to a file.

        Args:
            filepath: Path where to save items
            format: File format ("json")

        Example:
            service.save_to_file("./ingested_items.json")
        """
        content = self.export_items(format=format)
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Saved {len(self._all_items)} items to {filepath}")
