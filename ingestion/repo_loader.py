"""
Git repository loader for ingesting source code.

This loader clones Git repositories and extracts knowledge items from code files.
Supports multiple programming languages and handles large repositories efficiently.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Set

from models import KnowledgeItem, KnowledgeMetadata, SourceType
from ingestion.base_loader import BaseLoader
from utils.logger import get_logger

logger = get_logger(__name__)

# File extensions to ingest
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sql",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".bash",
    ".dockerfile",
    ".makefile",
    ".gradle",
    ".pom",
    ".toml",
    ".cfg",
    ".ini",
}

# Directories to exclude (binary artifacts, dependencies)
EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    ".github",
    "venv",
    "env",
    "dist",
    "build",
    "target",
    ".gradle",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    ".egg-info",
    ".tox",
    ".vscode",
    ".idea",
    ".DS_Store",
    "coverage",
    ".coverage",
    "htmlcov",
    "bin",
    "obj",
    ".next",
    ".nuxt",
}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".so",
    ".exe",
    ".dll",
    ".dylib",
    ".a",
    ".o",
    ".class",
    ".pyc",
    ".pyo",
    ".jar",
    ".war",
}

# Maximum file size to ingest (in bytes)
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB


class RepoLoader(BaseLoader):
    """
    Loader for Git repositories.

    Clones a repository, recursively scans files, and creates KnowledgeItem objects
    for each code file. Handles large repositories efficiently by:
    - Skipping binary files and common artifact directories
    - Enforcing file size limits
    - Supporting incremental ingestion

    Example:
        loader = RepoLoader(
            repo_url="https://github.com/facebook/react.git",
            local_path="./temp/react",
            repo_name="facebook/react"
        )
        items = loader.load()
    """

    def __init__(
        self,
        repo_url: str,
        local_path: str,
        repo_name: str,
        branch: str = "main",
        max_files: Optional[int] = None,
    ):
        """
        Initialize the repository loader.

        Args:
            repo_url: HTTPS URL to the Git repository
            local_path: Directory where repository will be cloned
            repo_name: Repository identifier (e.g., "owner/repo")
            branch: Git branch to clone (default: main)
            max_files: Maximum number of files to ingest (None for unlimited)

        Example:
            loader = RepoLoader(
                repo_url="https://github.com/user/repo.git",
                local_path="./temp/repo",
                repo_name="user/repo"
            )
        """
        super().__init__(name=f"RepoLoader({repo_name})")
        self.repo_url = repo_url
        self.local_path = Path(local_path)
        self.repo_name = repo_name
        self.branch = branch
        self.max_files = max_files
        self._files_processed = 0
        self._files_skipped = 0

    def load(self) -> List[KnowledgeItem]:
        """
        Load knowledge items from a Git repository.

        Returns:
            List of KnowledgeItem objects extracted from repository files

        Raises:
            RuntimeError: If git clone fails or repository is invalid
            OSError: If file system operations fail
        """
        start_time = time.time()
        items: List[KnowledgeItem] = []

        try:
            # Clone or pull repository
            self._prepare_repository()

            # Scan and extract knowledge items
            items = self._scan_repository()

            self.logger.info(
                "Finished scanning repository, extracted %d items",
                len(items),
            )

            # Log results
            duration = time.time() - start_time
            self._log_load_result(items, duration)
            self.logger.info(
                f"Processed {self._files_processed} files, "
                f"skipped {self._files_skipped} files"
            )

            return items

        finally:
            # Cleanup: remove cloned repository
            self._cleanup_repository()

    def _prepare_repository(self) -> None:
        """
        Prepare repository for scanning.

        Clones the repository if it doesn't exist, or pulls latest changes if it does.

        Raises:
            RuntimeError: If git operations fail
        """
        if self.local_path.exists():
            self.logger.info(
                f"Repository already exists at {self.local_path}, pulling latest"
            )
            self._run_git_command(["pull", "origin", self.branch], cwd=self.local_path)
        else:
            self.logger.info(f"Cloning repository to {self.local_path}")
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            self._run_git_command(
                [
                    "clone",
                    "--branch",
                    self.branch,
                    "--depth",
                    "1",
                    self.repo_url,
                    str(self.local_path),
                ]
            )

    def _run_git_command(self, args: List[str], cwd: Optional[Path] = None) -> str:
        """
        Execute a git command safely.

        Args:
            args: Git command arguments
            cwd: Working directory for the command

        Returns:
            Command output

        Raises:
            RuntimeError: If git command fails
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Git command failed: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Git command timed out: {' '.join(args)}")
        except FileNotFoundError:
            raise RuntimeError("Git is not installed or not in PATH")

    def _scan_repository(self) -> List[KnowledgeItem]:
        """
        Recursively scan repository and extract knowledge items.

        Returns:
            List of KnowledgeItem objects from all code files
        """
        items: List[KnowledgeItem] = []

        for file_path in self.local_path.rglob("*"):
            if self.max_files and len(items) >= self.max_files:
                self.logger.info(f"Reached max_files limit ({self.max_files})")
                break

            if not self._should_process_file(file_path):
                self._files_skipped += 1
                continue

            try:
                item = self._create_knowledge_item(file_path)
                if item:
                    items.append(item)
                    self._files_processed += 1
            except Exception as e:
                self.logger.warning(f"Failed to process {file_path}: {e}")

        return items

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be processed.

        Filters based on:
        - File extension (must be in ALLOWED_EXTENSIONS)
        - File size (must be under MAX_FILE_SIZE_BYTES)
        - Excluded directories
        - Binary files

        Args:
            file_path: Path to file to check

        Returns:
            True if file should be processed, False otherwise
        """
        # Skip directories
        if file_path.is_dir():
            return False

        # Check if in excluded directory
        if self._is_in_excluded_dir(file_path):
            return False

        # Check file extension
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return False

        # Skip binary files
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            return False

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                self.logger.debug(f"Skipping {file_path}: exceeds size limit")
                return False
        except OSError:
            return False

        return True

    def _is_in_excluded_dir(self, file_path: Path) -> bool:
        """
        Check if file is in an excluded directory.

        Args:
            file_path: Path to check

        Returns:
            True if file is in excluded directory
        """
        return any(excluded in file_path.parts for excluded in EXCLUDED_DIRS)

    def _create_knowledge_item(self, file_path: Path) -> Optional[KnowledgeItem]:
        """
        Create a KnowledgeItem from a code file.

        Args:
            file_path: Path to the code file

        Returns:
            KnowledgeItem object, or None if file cannot be read

        Raises:
            UnicodeDecodeError: If file cannot be decoded as text
        """
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Filter empty files
            if not content.strip():
                return None

            # Get relative path from repo root
            relative_path = file_path.relative_to(self.local_path)
            language = file_path.suffix.lstrip(".")

            # Create metadata
            metadata = KnowledgeMetadata(
                language=language,
                lines_of_code=len(content.splitlines()),
                custom_fields={
                    "file_size_bytes": len(content.encode("utf-8")),
                    "relative_path": str(relative_path),
                },
            )

            # Create knowledge item
            item = KnowledgeItem(
                source_type=SourceType.CODE_FILE,
                repo=self.repo_name,
                file_path=str(relative_path),
                content=content,
                metadata=metadata,
            )

            return item

        except UnicodeDecodeError:
            self.logger.debug(f"Skipping {file_path}: not valid UTF-8")
            return None

    def _cleanup_repository(self) -> None:
        """Clean up the cloned repository to save disk space."""
        if self.local_path.exists():
            try:
                shutil.rmtree(self.local_path)
                self.logger.debug(f"Cleaned up repository at {self.local_path}")
            except OSError as e:
                self.logger.warning(f"Failed to clean up repository: {e}")
