"""
GitHub Pull Request loader for ingesting PR discussions and code reviews.

This loader fetches pull requests from GitHub API and extracts knowledge items
from PR titles, descriptions, comments, and file changes.
"""

import time
from typing import List, Optional
from datetime import datetime

import requests

from models import KnowledgeItem, KnowledgeMetadata, SourceType
from ingestion.base_loader import BaseLoader
from utils.logger import get_logger

logger = get_logger(__name__)

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Default headers for GitHub API requests
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "EIS-Ingestion-Pipeline",
}


class PRLoader(BaseLoader):
    """
    Loader for GitHub Pull Requests.

    Fetches pull requests from a GitHub repository and creates KnowledgeItem objects
    from PR metadata, descriptions, comments, and changed files. Handles pagination
    and API rate limits efficiently.

    Supports authenticated requests for higher rate limits and private repositories.

    Example:
        loader = PRLoader(
            repo_owner="facebook",
            repo_name="react",
            github_token="ghp_xxx",
            max_prs=50,
            status="closed"
        )
        items = loader.load()
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        github_token: Optional[str] = None,
        max_prs: int = 100,
        status: str = "all",
        include_comments: bool = True,
    ):
        """
        Initialize the GitHub PR loader.

        Args:
            repo_owner: GitHub repository owner (e.g., "facebook")
            repo_name: GitHub repository name (e.g., "react")
            github_token: GitHub personal access token for authenticated requests
            max_prs: Maximum number of PRs to fetch
            status: PR status filter ("open", "closed", "all")
            include_comments: Whether to include PR comments as separate items

        Example:
            loader = PRLoader(
                repo_owner="facebook",
                repo_name="react",
                github_token="ghp_xxx",  # Optional
                max_prs=50
            )
        """
        super().__init__(name=f"PRLoader({repo_owner}/{repo_name})")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self.max_prs = max_prs
        self.status = status
        self.include_comments = include_comments

        # Setup headers with authentication if provided
        self.headers = DEFAULT_HEADERS.copy()
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

        self._session = requests.Session()
        self._session.headers.update(self.headers)
        self._prs_processed = 0
        self._comments_processed = 0

    def load(self) -> List[KnowledgeItem]:
        """
        Load knowledge items from GitHub pull requests.

        Returns:
            List of KnowledgeItem objects extracted from PRs

        Raises:
            requests.RequestException: If GitHub API calls fail
        """
        start_time = time.time()
        items: List[KnowledgeItem] = []

        try:
            # Fetch pull requests
            prs = self._fetch_pull_requests()
            self.logger.info(f"Fetched {len(prs)} pull requests")

            # Extract knowledge items from each PR
            for pr in prs:
                if len(items) >= self.max_prs:
                    self.logger.info(f"Reached max_prs limit ({self.max_prs})")
                    break

                try:
                    # Create item from PR metadata
                    pr_item = self._create_pr_knowledge_item(pr)
                    items.append(pr_item)
                    self._prs_processed += 1

                    # Extract comments if enabled
                    if self.include_comments and pr.get("comments", 0) > 0:
                        comment_items = self._fetch_and_extract_comments(pr)
                        items.extend(comment_items)
                        self._comments_processed += len(comment_items)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to process PR #{pr.get('number')}: {e}"
                    )

            # Log results
            duration = time.time() - start_time
            self._log_load_result(items, duration)
            self.logger.info(
                f"Processed {self._prs_processed} PRs, {self._comments_processed} comments"
            )

            return items

        finally:
            self._session.close()

    def _fetch_pull_requests(self) -> List[dict]:
        """
        Fetch pull requests from GitHub API.

        Uses pagination to handle repositories with many PRs.

        Returns:
            List of PR objects from GitHub API

        Raises:
            requests.RequestException: If API calls fail
        """
        url = f"{GITHUB_API_BASE}/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params = {
            "state": self.status,
            "sort": "updated",
            "direction": "desc",
            "per_page": 100,
        }

        all_prs = []
        page = 1

        while len(all_prs) < self.max_prs:
            params["page"] = page
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()

            prs = response.json()
            if not prs:
                break

            all_prs.extend(prs)
            page += 1

            # Check for rate limit
            if "X-RateLimit-Remaining" in response.headers:
                remaining = int(response.headers["X-RateLimit-Remaining"])
                if remaining < 10:
                    self.logger.warning(
                        f"GitHub API rate limit nearly exceeded: {remaining} remaining"
                    )
                    break

        return all_prs[: self.max_prs]

    def _fetch_and_extract_comments(self, pr: dict) -> List[KnowledgeItem]:
        """
        Fetch and extract comments from a PR.

        Args:
            pr: Pull request object from GitHub API

        Returns:
            List of KnowledgeItem objects from PR comments
        """
        items: List[KnowledgeItem] = []

        try:
            url = pr["comments_url"]
            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            comments = response.json()
            for comment in comments:
                try:
                    item = self._create_pr_comment_knowledge_item(pr, comment)
                    items.append(item)
                except Exception as e:
                    self.logger.debug(
                        f"Failed to process comment on PR #{pr['number']}: {e}"
                    )

        except Exception as e:
            self.logger.debug(f"Failed to fetch comments for PR #{pr['number']}: {e}")

        return items

    def _create_pr_knowledge_item(self, pr: dict) -> KnowledgeItem:
        """
        Create a KnowledgeItem from a PR.

        Args:
            pr: Pull request object from GitHub API

        Returns:
            KnowledgeItem representing the PR
        """
        # Combine PR title and description as content
        content_parts = [pr.get("title", "")]
        if pr.get("body"):
            content_parts.append(pr["body"])

        content = "\n".join(filter(None, content_parts))

        # Parse timestamps
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))

        # Create metadata
        draft_status = "draft" if pr.get("draft", False) else "ready"
        metadata = KnowledgeMetadata(
            source_url=pr["html_url"],
            author=pr["user"]["login"],
            created_at=created_at,
            updated_at=updated_at,
            tags=["pull_request", pr["state"], draft_status],
            custom_fields={
                "pr_number": pr["number"],
                "state": pr["state"],
                "draft": pr.get("draft", False),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "changed_files": pr.get("changed_files", 0),
                "comments_count": pr.get("comments", 0),
                "review_comments_count": pr.get("review_comments", 0),
            },
        )

        # Create knowledge item
        item = KnowledgeItem(
            source_type=SourceType.PULL_REQUEST,
            repo=f"{self.repo_owner}/{self.repo_name}",
            file_path=f"PR#{pr['number']}",
            content=content,
            metadata=metadata,
        )

        return item

    def _create_pr_comment_knowledge_item(
        self, pr: dict, comment: dict
    ) -> KnowledgeItem:
        """
        Create a KnowledgeItem from a PR comment.

        Args:
            pr: Pull request object from GitHub API
            comment: Comment object from GitHub API

        Returns:
            KnowledgeItem representing the PR comment
        """
        created_at = datetime.fromisoformat(
            comment["created_at"].replace("Z", "+00:00")
        )
        updated_at = datetime.fromisoformat(
            comment["updated_at"].replace("Z", "+00:00")
        )

        metadata = KnowledgeMetadata(
            source_url=comment["html_url"],
            author=comment["user"]["login"],
            created_at=created_at,
            updated_at=updated_at,
            tags=["comment", "pr_comment"],
            custom_fields={
                "pr_number": pr["number"],
                "comment_id": comment["id"],
                "parent_pr_url": pr["html_url"],
            },
        )

        item = KnowledgeItem(
            source_type=SourceType.COMMENT,
            repo=f"{self.repo_owner}/{self.repo_name}",
            file_path=f"PR#{pr['number']}/comment#{comment['id']}",
            content=comment["body"],
            metadata=metadata,
        )

        return item

    def __del__(self):
        """Close the session when the loader is destroyed."""
        if hasattr(self, "_session"):
            self._session.close()
