"""Example script to ingest PRs from a GitHub repository (default: facebook/react).

Usage:
  GITHUB_TOKEN=ghp_xxx python scripts/ingest_react_prs.py --max-prs 20

If no token is provided, the script will run unauthenticated (limited to ~60 requests/hour).
"""

from __future__ import annotations

import os
import argparse
from typing import List

from ingestion.pr_loader import PRLoader


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest pull requests from a GitHub repository into knowledge items"
    )
    parser.add_argument("--repo-owner", default="facebook", help="GitHub repo owner")
    parser.add_argument("--repo-name", default="react", help="GitHub repo name")
    parser.add_argument(
        "--max-prs", type=int, default=50, help="Maximum number of PRs to fetch"
    )
    parser.add_argument(
        "--status",
        default="all",
        choices=["open", "closed", "all"],
        help="PR state to fetch",
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        default=True,
        help="Include PR comments",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub token or set GITHUB_TOKEN env var",
    )

    args = parser.parse_args()

    loader = PRLoader(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        github_token=args.token,
        max_prs=args.max_prs,
        status=args.status,
        include_comments=args.include_comments,
    )

    items: List = loader.load()

    print(
        f"Loaded {len(items)} knowledge items from {args.repo_owner}/{args.repo_name}"
    )
    for item in items:
        try:
            print(f"- {item.file_path} | author={item.metadata.author}")
        except Exception:
            print(f"- {getattr(item, 'file_path', '<unknown>')}")


if __name__ == "__main__":
    main()
