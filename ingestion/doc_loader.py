"""
Markdown documentation loader for ingesting documentation.

This loader reads markdown files from a directory and creates knowledge items,
optionally splitting large documents into sections for better retrieval.
"""

import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models import KnowledgeItem, KnowledgeMetadata, SourceType
from ingestion.base_loader import BaseLoader
from utils.logger import get_logger

logger = get_logger(__name__)

# Markdown file extensions
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".txt", ".rst"}


class DocLoader(BaseLoader):
    """
    Loader for Markdown documentation.

    Reads markdown files from a directory and creates KnowledgeItem objects.
    Can optionally split large documents into sections based on headers for
    improved retrieval during semantic search.

    Features:
    - Recursive directory scanning
    - Section-based splitting at header boundaries
    - Metadata extraction from file attributes
    - Support for multiple markdown formats

    Example:
        loader = DocLoader(
            doc_dir="./docs",
            repo_name="facebook/react",
            split_on_headers=True
        )
        items = loader.load()
    """

    def __init__(
        self,
        doc_dir: str,
        repo_name: str,
        split_on_headers: bool = False,
        min_section_length: int = 100,
    ):
        """
        Initialize the documentation loader.

        Args:
            doc_dir: Directory containing markdown documentation
            repo_name: Repository or project identifier
            split_on_headers: Whether to split documents at header boundaries
            min_section_length: Minimum characters for a section when splitting

        Example:
            loader = DocLoader(
                doc_dir="./docs",
                repo_name="my-project",
                split_on_headers=True
            )
        """
        super().__init__(name=f"DocLoader({repo_name})")
        self.doc_dir = Path(doc_dir)
        self.repo_name = repo_name
        self.split_on_headers = split_on_headers
        self.min_section_length = min_section_length
        self._files_processed = 0
        self._sections_created = 0

    def load(self) -> List[KnowledgeItem]:
        """
        Load knowledge items from markdown documentation.

        Returns:
            List of KnowledgeItem objects extracted from documentation

        Raises:
            FileNotFoundError: If documentation directory doesn't exist
            OSError: If file system operations fail
        """
        start_time = time.time()

        if not self.doc_dir.exists():
            raise FileNotFoundError(
                f"Documentation directory not found: {self.doc_dir}"
            )

        items: List[KnowledgeItem] = []

        try:
            # Scan all markdown files
            for doc_file in self.doc_dir.rglob("*"):
                if not self._is_markdown_file(doc_file):
                    continue

                try:
                    content = doc_file.read_text(encoding="utf-8")

                    if self.split_on_headers:
                        # Split into sections
                        sections = self._split_document_by_headers(doc_file, content)
                        items.extend(sections)
                        self._sections_created += len(sections)
                    else:
                        # Create single item per file
                        item = self._create_knowledge_item(doc_file, content)
                        if item:
                            items.append(item)

                    self._files_processed += 1

                except Exception as e:
                    self.logger.warning(
                        f"Failed to process documentation file {doc_file}: {e}"
                    )

            # Log results
            duration = time.time() - start_time
            self._log_load_result(items, duration)

            if self.split_on_headers:
                self.logger.info(
                    f"Processed {self._files_processed} files, "
                    f"created {self._sections_created} sections"
                )
            else:
                self.logger.info(
                    f"Processed {self._files_processed} documentation files"
                )

            return items

        except Exception as e:
            self.logger.error(f"Documentation loading failed: {e}")
            raise

    def _is_markdown_file(self, file_path: Path) -> bool:
        """
        Check if a file is a markdown documentation file.

        Args:
            file_path: Path to check

        Returns:
            True if file is markdown, False otherwise
        """
        if not file_path.is_file():
            return False

        if file_path.suffix.lower() not in MARKDOWN_EXTENSIONS:
            return False

        return True

    def _create_knowledge_item(
        self,
        file_path: Path,
        content: str,
        section_number: Optional[int] = None,
        section_title: Optional[str] = None,
    ) -> Optional[KnowledgeItem]:
        """
        Create a KnowledgeItem from markdown content.

        Args:
            file_path: Path to the markdown file
            content: File content
            section_number: Section number if split on headers
            section_title: Section title if split on headers

        Returns:
            KnowledgeItem object, or None if content is empty
        """
        # Filter empty content
        if not content.strip():
            return None

        # Get relative path from doc directory
        relative_path = file_path.relative_to(self.doc_dir)

        # Determine file path for the item
        if section_number is not None:
            item_path = f"{relative_path}#{section_number}"
        else:
            item_path = str(relative_path)

        # Get file modification time
        try:
            stat = file_path.stat()
            updated_at = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            updated_at = datetime.utcnow()

        # Extract first heading as title if available
        title = section_title or self._extract_title(content)

        # Create metadata
        metadata = KnowledgeMetadata(
            language="markdown",
            updated_at=updated_at,
            tags=["documentation"],
            custom_fields={
                "file_name": file_path.name,
                "relative_path": str(relative_path),
                "lines": len(content.splitlines()),
                "title": title,
            },
        )

        # Create knowledge item
        item = KnowledgeItem(
            source_type=SourceType.DOCUMENTATION,
            repo=self.repo_name,
            file_path=item_path,
            content=content,
            metadata=metadata,
        )

        return item

    def _split_document_by_headers(
        self, file_path: Path, content: str
    ) -> List[KnowledgeItem]:
        """
        Split a markdown document into sections by headers.

        Creates separate KnowledgeItem for each section (h1, h2, h3).

        Args:
            file_path: Path to the markdown file
            content: Full document content

        Returns:
            List of KnowledgeItem objects, one per section
        """
        sections = []
        lines = content.split("\n")
        current_section = []
        current_section_title: Optional[str] = None
        section_number = 0

        for line in lines:
            # Check if this is a header line
            if line.startswith("#") and line.strip().startswith("#"):
                # Save previous section if it has content
                if (
                    current_section
                    and len("\n".join(current_section)) >= self.min_section_length
                ):
                    section_content = "\n".join(current_section).strip()
                    item = self._create_knowledge_item(
                        file_path,
                        section_content,
                        section_number=section_number,
                        section_title=current_section_title,
                    )
                    if item:
                        sections.append(item)
                        section_number += 1

                # Start new section
                current_section_title = self._extract_header_text(line)
                current_section = [line]
            else:
                current_section.append(line)

        # Don't forget the last section
        if (
            current_section
            and len("\n".join(current_section)) >= self.min_section_length
        ):
            section_content = "\n".join(current_section).strip()
            item = self._create_knowledge_item(
                file_path,
                section_content,
                section_number=section_number,
                section_title=current_section_title,
            )
            if item:
                sections.append(item)

        return sections

    @staticmethod
    def _extract_title(content: str) -> Optional[str]:
        """
        Extract the first heading from markdown content.

        Args:
            content: Markdown content

        Returns:
            First heading text, or None if no headings found
        """
        for line in content.split("\n"):
            if line.startswith("#"):
                return DocLoader._extract_header_text(line)
        return None

    @staticmethod
    def _extract_header_text(header_line: str) -> str:
        """
        Extract text from a markdown header.

        Removes # symbols and whitespace.

        Args:
            header_line: Markdown header line (e.g., "## My Section")

        Returns:
            Header text (e.g., "My Section")
        """
        text = header_line.lstrip("#").strip()
        # Remove inline code formatting if present
        text = text.replace("`", "").replace("*", "")
        return text
