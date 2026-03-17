"""
Example usage and testing of the Engineering Intelligence System.

This module demonstrates how to create and work with KnowledgeItem instances,
showcasing the core domain models before the full ingestion pipeline is implemented.
"""

from datetime import datetime
from uuid import uuid4

from models import (
    KnowledgeItem,
    KnowledgeMetadata,
    SourceType,
    SearchQuery,
    ChunkingConfig,
)


def example_knowledge_item_creation() -> None:
    """
    Example 1: Create a KnowledgeItem representing a code file.

    This demonstrates instantiating domain models with proper type hints and validation.
    """
    print("\n" + "=" * 70)
    print("Example 1: Creating a KnowledgeItem from a Code File")
    print("=" * 70 + "\n")

    # Create metadata for the code file
    metadata = KnowledgeMetadata(
        source_url="https://github.com/facebook/react/blob/main/packages/react/src/index.js",
        author="Dan Abramov",
        language="js",
        tags=["core", "exports", "public-api"],
    )

    # Create a knowledge item for React's main export file
    react_item = KnowledgeItem(
        source_type=SourceType.CODE_FILE,
        repo="facebook/react",
        file_path="packages/react/src/index.js",
        content="""export { default as React } from './React';
export * from './React';
export { default as ReactVersion } from './ReactVersion';""",
        metadata=metadata,
    )

    print(f"Created Knowledge Item:")
    print(f"  ID: {react_item.id}")
    print(f"  Type: {react_item.source_type.value}")
    print(f"  Repository: {react_item.repo}")
    print(f"  Path: {react_item.file_path}")
    print(f"  Author: {react_item.metadata.author}")
    print(f"  Language: {react_item.metadata.language}")
    print(f"  Tags: {', '.join(react_item.metadata.tags)}")
    print(f"  Created: {react_item.metadata.created_at.isoformat()}")
    print(f"\nContent Preview:\n{react_item.content[:100]}...")


def example_pr_documentation() -> None:
    """
    Example 2: Create a KnowledgeItem from a Pull Request.

    Demonstrates capturing PR-related engineering knowledge.
    """
    print("\n" + "=" * 70)
    print("Example 2: Creating a KnowledgeItem from a Pull Request")
    print("=" * 70 + "\n")

    metadata = KnowledgeMetadata(
        source_url="https://github.com/facebook/react/pull/27732",
        author="acdlite",
        language="md",
        tags=["feature", "hooks", "performance"],
        custom_fields={
            "pr_number": 27732,
            "status": "merged",
            "review_count": 5,
        },
    )

    pr_item = KnowledgeItem(
        source_type=SourceType.PULL_REQUEST,
        repo="facebook/react",
        file_path="PR#27732/description",
        content="""## Optimize useTransition for fast bailed out updates

This PR optimizes useTransition to detect fast bailed out updates earlier,
allowing transitions to complete faster when the state update doesn't result
in visible changes or yields too quickly.""",
        metadata=metadata,
    )

    print(f"Created Knowledge Item (Pull Request):")
    print(f"  ID: {pr_item.id}")
    print(f"  Type: {pr_item.source_type.value}")
    print(f"  Author: {pr_item.metadata.author}")
    print(f"  Custom Fields: {pr_item.metadata.custom_fields}")
    print(f"\nPR Description:\n{pr_item.content}")


def example_documentation() -> None:
    """
    Example 3: Create a KnowledgeItem from documentation.

    Shows how to capture knowledge from markdown documentation files.
    """
    print("\n" + "=" * 70)
    print("Example 3: Creating a KnowledgeItem from Documentation")
    print("=" * 70 + "\n")

    metadata = KnowledgeMetadata(
        language="md",
        tags=["documentation", "hooks", "state-management"],
    )

    doc_item = KnowledgeItem(
        source_type=SourceType.DOCUMENTATION,
        repo="facebook/react",
        file_path="docs/hooks/useReducer.md",
        content="""# useReducer

useReducer is usually preferable to useState when you have complex state logic
that involves multiple sub-values. It also lets you optimize performance for
components that trigger deep updates because you can pass dispatch down
instead of callbacks.""",
        metadata=metadata,
    )

    print(f"Created Knowledge Item (Documentation):")
    print(f"  ID: {doc_item.id}")
    print(f"  Type: {doc_item.source_type.value}")
    print(f"  Path: {doc_item.file_path}")
    print(f"  Tags: {', '.join(doc_item.metadata.tags)}")
    print(f"\nDocumentation:\n{doc_item.content}")


def example_chunked_content() -> None:
    """
    Example 4: Create a KnowledgeItem representing a chunk from a larger document.

    Shows how to handle chunked content with parent reference.
    """
    print("\n" + "=" * 70)
    print("Example 4: Creating a Chunked KnowledgeItem")
    print("=" * 70 + "\n")

    parent_id = uuid4()

    chunk_1 = KnowledgeItem(
        source_type=SourceType.DOCUMENTATION,
        repo="facebook/react",
        file_path="docs/advanced-patterns.md",
        content="Render props pattern: A technique for sharing code between React components.",
        metadata=KnowledgeMetadata(
            tags=["pattern", "advanced"], custom_fields={"section": "Advanced Patterns"}
        ),
        chunk_index=0,
        total_chunks=3,
        parent_id=parent_id,
    )

    chunk_2 = KnowledgeItem(
        source_type=SourceType.DOCUMENTATION,
        repo="facebook/react",
        file_path="docs/advanced-patterns.md",
        content="A render prop is a function prop that a component uses to know what to render.",
        metadata=KnowledgeMetadata(
            tags=["pattern", "advanced"], custom_fields={"section": "Advanced Patterns"}
        ),
        chunk_index=1,
        total_chunks=3,
        parent_id=parent_id,
    )

    print(f"Created Chunked Knowledge Items:")
    print(f"  Parent ID: {parent_id}")
    print(f"\n  Chunk 1:")
    print(f"    Index: {chunk_1.chunk_index}/{chunk_1.total_chunks}")
    print(f"    Content: {chunk_1.content[:50]}...")
    print(f"\n  Chunk 2:")
    print(f"    Index: {chunk_2.chunk_index}/{chunk_2.total_chunks}")
    print(f"    Content: {chunk_2.content[:50]}...")


def example_search_to_text() -> None:
    """
    Example 5: Generate searchable text from a knowledge item.

    Shows the to_search_text() helper method for full-text search integration.
    """
    print("\n" + "=" * 70)
    print("Example 5: Generate Searchable Text")
    print("=" * 70 + "\n")

    item = KnowledgeItem(
        source_type=SourceType.CODE_FILE,
        repo="nodejs/node",
        file_path="lib/events.js",
        content="class EventEmitter extends Object { }",
        metadata=KnowledgeMetadata(
            language="js",
            tags=["events", "core-module"],
        ),
    )

    search_text = item.to_search_text()
    print(f"Original Items:")
    print(f"  File: {item.file_path}")
    print(f"  Repo: {item.repo}")
    print(f"  Tags: {', '.join(item.metadata.tags) if item.metadata.tags else 'None'}")
    print(f"\nSearchable Text:")
    print(f"  {search_text}")


def example_search_query() -> None:
    """
    Example 6: Create a SearchQuery for knowledge retrieval.

    Demonstrates the search query model with filters.
    """
    print("\n" + "=" * 70)
    print("Example 6: Creating a SearchQuery")
    print("=" * 70 + "\n")

    query = SearchQuery(
        query_text="How do I manage state in React without Redux?",
        top_k=5,
        filters={
            "repo": "facebook/react",
            "source_type": "documentation",
            "tags": ["state-management"],
        },
    )

    print(f"Search Query Created:")
    print(f"  Question: {query.query_text}")
    print(f"  Top Results: {query.top_k}")
    print(f"  Filters: {query.filters}")


def example_configuration() -> None:
    """
    Example 7: Load and review configuration.

    Shows how to access the system configuration.
    """
    print("\n" + "=" * 70)
    print("Example 7: System Configuration")
    print("=" * 70 + "\n")

    from config import get_settings

    settings = get_settings()

    print(f"Application Configuration:")
    print(f"  App Name: {settings.app_name}")
    print(f"  Version: {settings.app_version}")
    print(f"  Environment: {settings.environment}")
    print(f"\nVector Database (Qdrant):")
    print(f"  URL: {settings.qdrant_url}")
    print(f"  Collection: {settings.qdrant_collection_name}")
    print(f"  Vector Size: {settings.qdrant_vector_size}")
    print(f"\nEmbedding Service:")
    print(f"  Model: {settings.embedding_model}")
    print(f"  Dimension: {settings.embedding_dimension}")
    print(f"  Batch Size: {settings.embedding_batch_size}")
    print(f"\nLLM (Claude):")
    print(f"  Model: {settings.llm_model}")
    print(f"  Max Tokens: {settings.llm_max_tokens}")
    print(f"  Temperature: {settings.llm_temperature}")


def example_chunking_config() -> None:
    """
    Example 8: Create chunking configuration.

    Shows how chunking parameters are configured.
    """
    print("\n" + "=" * 70)
    print("Example 8: Chunking Configuration")
    print("=" * 70 + "\n")

    config = ChunkingConfig(
        chunk_size=512,
        overlap_tokens=50,
    )

    print(f"Chunking Configuration:")
    print(f"  Chunk Size: {config.chunk_size} tokens")
    print(f"  Overlap: {config.overlap_tokens} tokens")
    print(f"  Separator: {repr(config.separator)}")


if __name__ == "__main__":
    """
    Run all examples demonstrating EIS domain models and usage patterns.
    """
    print("\n" + "#" * 70)
    print("# Engineering Intelligence System (EIS) - Examples")
    print("#" * 70)

    example_knowledge_item_creation()
    example_pr_documentation()
    example_documentation()
    example_chunked_content()
    example_search_to_text()
    example_search_query()
    example_configuration()
    example_chunking_config()

    print("\n" + "#" * 70)
    print("# All examples completed successfully!")
    print("#" * 70 + "\n")
