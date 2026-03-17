"""
Example usage of the EIS ingestion pipeline.

Demonstrates how to:
1. Ingest Git repositories
2. Fetch and process GitHub pull requests
3. Load markdown documentation
4. Orchestrate multiple loaders with IngestionService
"""

import os
from pathlib import Path

from ingestion import RepoLoader, PRLoader, DocLoader, IngestionService
from utils.logger import get_logger

logger = get_logger(__name__)


def example_1_basic_repo_ingestion():
    """
    Example 1: Ingest a single Git repository.

    This demonstrates how to clone a repository and extract code files.
    """
    print("\n" + "=" * 70)
    print("Example 1: Basic Repository Ingestion")
    print("=" * 70 + "\n")

    # Create a repository loader
    loader = RepoLoader(
        repo_url="https://github.com/facebook/react.git",
        local_path="./temp/react",
        repo_name="facebook/react",
        branch="main",
        max_files=100,  # Limit for the example
    )

    logger.info("Starting repository ingestion...")

    try:
        # Load knowledge items
        items = loader.load()

        print(f"\nIngest Results:")
        print(f"  Total Items: {len(items)}")

        # Show first few items
        if items:
            print(f"\nFirst Item:")
            first = items[0]
            print(f"  ID: {first.id}")
            print(f"  Type: {first.source_type.value}")
            print(f"  Repo: {first.repo}")
            print(f"  File: {first.file_path}")
            print(f"  Language: {first.metadata.language}")
            print(f"  Content Preview: {first.content[:100]}...")

            # Show statistics
            source_types = {}
            languages = {}
            for item in items:
                source_types[item.source_type.value] = (
                    source_types.get(item.source_type.value, 0) + 1
                )
                lang = item.metadata.language or "unknown"
                languages[lang] = languages.get(lang, 0) + 1

            print(f"\nStatistics:")
            print(f"  By Source Type: {source_types}")
            print(f"  By Language: {languages}")

    except Exception as e:
        logger.error(f"Repository ingestion failed: {e}")
        print(f"Error: {e}")


def example_2_pr_ingestion():
    """
    Example 2: Ingest GitHub Pull Requests.

    Note: Requires a valid GitHub personal access token.
    Set GITHUB_TOKEN environment variable or pass directly.
    """
    print("\n" + "=" * 70)
    print("Example 2: GitHub Pull Request Ingestion")
    print("=" * 70 + "\n")

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        print("⚠️  GITHUB_TOKEN not set. Skipping PR ingestion example.")
        print("   To enable: export GITHUB_TOKEN=ghp_xxx")
        return

    logger.info("Creating PR loader...")

    # Create a PR loader
    loader = PRLoader(
        repo_owner="facebook",
        repo_name="react",
        github_token=github_token,
        max_prs=5,  # Limit for the example
        status="closed",
        include_comments=True,
    )

    logger.info("Starting PR ingestion...")

    try:
        # Load knowledge items
        items = loader.load()

        print(f"\nIngestion Results:")
        print(f"  Total Items: {len(items)}")

        # Separate PRs and comments
        prs = [item for item in items if item.source_type.value == "pull_request"]
        comments = [item for item in items if item.source_type.value == "comment"]

        print(f"  Pull Requests: {len(prs)}")
        print(f"  Comments: {len(comments)}")

        # Show first PR
        if prs:
            print(f"\nFirst PR:")
            pr = prs[0]
            print(f"  ID: {pr.id}")
            print(f"  File: {pr.file_path}")
            print(f"  Author: {pr.metadata.author}")
            print(f"  URL: {pr.metadata.source_url}")
            print(f"  Custom Fields: {pr.metadata.custom_fields}")

    except Exception as e:
        logger.error(f"PR ingestion failed: {e}")
        print(f"Error: {e}")


def example_3_doc_ingestion():
    """
    Example 3: Ingest markdown documentation.

    Creates a sample documentation directory for demonstration.
    """
    print("\n" + "=" * 70)
    print("Example 3: Documentation Ingestion")
    print("=" * 70 + "\n")

    # Create sample documentation directory
    doc_dir = Path("./temp/sample_docs")
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Create sample documentation files
    (doc_dir / "README.md").write_text(
        """# Getting Started

This is the main documentation.

## Installation

1. Clone the repository
2. Install dependencies
3. Run the application

## Usage

Use the system as follows...
"""
    )

    (doc_dir / "architecture.md").write_text(
        """# System Architecture

## Overview

The system is divided into layers.

## Components

### Component A
Description of component A.

### Component B
Description of component B.
"""
    )

    (doc_dir / "advanced.md").write_text(
        """# Advanced Topics

## Performance Tuning

Tips for optimizing performance.

## Security

Security best practices.
"""
    )

    logger.info(f"Created sample documentation in {doc_dir}")

    # Create a documentation loader
    loader = DocLoader(
        doc_dir=str(doc_dir),
        repo_name="example-project",
        split_on_headers=True,
        min_section_length=50,
    )

    logger.info("Starting documentation ingestion...")

    try:
        # Load knowledge items
        items = loader.load()

        print(f"\nIngestion Results:")
        print(f"  Total Items: {len(items)}")

        # Show items
        for item in items:
            print(f"\nItem:")
            print(f"  File: {item.file_path}")
            print(f"  Title: {item.metadata.custom_fields.get('title', 'N/A')}")
            print(f"  Content Preview: {item.content[:80]}...")

    except Exception as e:
        logger.error(f"Documentation ingestion failed: {e}")
        print(f"Error: {e}")

    finally:
        # Cleanup
        import shutil

        if doc_dir.exists():
            shutil.rmtree(doc_dir)
            logger.info(f"Cleaned up {doc_dir}")


def example_4_multi_loader_orchestration():
    """
    Example 4: Orchestrate multiple loaders with IngestionService.

    Demonstrates the complete ingestion pipeline with multiple sources.
    """
    print("\n" + "=" * 70)
    print("Example 4: Multi-Loader Orchestration")
    print("=" * 70 + "\n")

    # Create sample documentation for demo
    doc_dir = Path("./temp/orchestration_docs")
    doc_dir.mkdir(parents=True, exist_ok=True)

    (doc_dir / "guide.md").write_text(
        """# Quick Guide

## Getting Started

Follow these steps to get started.

## Best Practices

Here are the best practices.
"""
    )

    # Create loaders
    repo_loader = RepoLoader(
        repo_url="https://github.com/torvalds/linux.git",
        local_path="./temp/linux",
        repo_name="torvalds/linux",
        branch="master",
        max_files=20,  # Very limited for demo
    )

    doc_loader = DocLoader(
        doc_dir=str(doc_dir),
        repo_name="example-project",
        split_on_headers=False,
    )

    # Create orchestration service
    service = IngestionService(
        loaders=[repo_loader, doc_loader],
        deduplicate=True,
    )

    logger.info("Starting orchestrated ingestion pipeline...")

    try:
        # Run the complete pipeline
        items = service.run()

        print(f"\nOrchestration Results:")
        print(f"  Total Items: {len(items)}")

        # Get statistics
        stats = service.get_statistics()
        print(f"\nStatistics:")
        print(f"  Duration: {stats.get('duration_seconds', 0):.2f}s")
        print(f"  Items/Second: {stats.get('items_per_second', 0):.2f}")
        print(f"  Total Characters: {stats.get('total_characters', 0):,}")

        # Show distribution
        print(f"\nBy Source Type:")
        for source_type, count in stats.get("source_type_distribution", {}).items():
            print(f"  - {source_type}: {count}")

        print(f"\nBy Repository:")
        for repo, count in stats.get("repository_distribution", {}).items():
            print(f"  - {repo}: {count}")

        # Filter items by type
        code_items = service.get_items_by_source_type("code_file")
        doc_items = service.get_items_by_source_type("documentation")

        print(f"\nFiltered Results:")
        print(f"  Code Files: {len(code_items)}")
        print(f"  Documentation: {len(doc_items)}")

    except Exception as e:
        logger.error(f"Orchestrated ingestion failed: {e}")
        print(f"Error: {e}")

    finally:
        # Cleanup
        import shutil

        for path in [Path("./temp/linux"), doc_dir]:
            if path.exists():
                shutil.rmtree(path)
                logger.info(f"Cleaned up {path}")


def example_5_error_handling():
    """
    Example 5: Error handling and graceful degradation.

    Demonstrates how the ingestion service continues even if one loader fails.
    """
    print("\n" + "=" * 70)
    print("Example 5: Error Handling")
    print("=" * 70 + "\n")

    # Create a loader with invalid repository (will fail)
    bad_repo_loader = RepoLoader(
        repo_url="https://github.com/nonexistent/invalid-repo-xyz.git",
        local_path="./temp/invalid",
        repo_name="invalid/repo",
    )

    # Create documentation loader (will succeed)
    doc_dir = Path("./temp/error_handling_docs")
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "info.md").write_text("# Info\n\nSome documentation.")

    doc_loader = DocLoader(
        doc_dir=str(doc_dir),
        repo_name="test-project",
    )

    # Create service with mixed loaders
    service = IngestionService(
        loaders=[bad_repo_loader, doc_loader],
    )

    logger.info("Starting ingestion with intentional failure...")

    try:
        items = service.run()

        print(f"\nResults (with graceful error handling):")
        print(f"  Total Items: {len(items)}")
        print(f"  Service continued despite failed loader: ✓")

        if items:
            print(f"\nSuccessfully ingested from working loaders:")
            for item in items:
                print(f"  - {item.file_path}")

    finally:
        # Cleanup
        import shutil

        for path in [Path("./temp/error_handling_docs"), Path("./temp/invalid")]:
            if path.exists():
                shutil.rmtree(path)


if __name__ == "__main__":
    """
    Run all ingestion examples.
    """
    print("\n" + "#" * 70)
    print("# EIS Ingestion Pipeline - Examples")
    print("#" * 70)

    # Run examples
    example_1_basic_repo_ingestion()
    example_3_doc_ingestion()
    example_4_multi_loader_orchestration()
    example_5_error_handling()

    # Conditionally run PR example (requires token)
    if os.getenv("GITHUB_TOKEN"):
        example_2_pr_ingestion()
    else:
        print("\n" + "=" * 70)
        print("Example 2: GitHub Pull Request Ingestion (skipped)")
        print("=" * 70)
        print("\nTo run PR ingestion:")
        print("  export GITHUB_TOKEN=your_github_token")
        print("  python ingest_examples.py")

    print("\n" + "#" * 70)
    print("# All examples completed!")
    print("#" * 70 + "\n")
