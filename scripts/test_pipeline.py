"""End-to-end EIS pipeline validation script (pre-LLM reasoning layer).

Pipeline covered:
Ingestion -> Chunking -> Embedding -> Vector Store -> Retrieval
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Allow direct execution via `python scripts/test_pipeline.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings, get_settings
from chunking.chunk_service import ChunkService
from embeddings.embedding_provider import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from embeddings.embedding_service import EmbeddingService
from ingestion.ingestion_service import IngestionService
from ingestion.repo_loader import RepoLoader
from retrieval.query_embedding_service import QueryEmbeddingService
from vector_store.qdrant_store import QdrantVectorStore
from vector_store.vector_models import VectorSearchResult
from vector_store.vector_search_service import VectorSearchService

from utils.logger import get_logger

logger = get_logger(__name__)

COMMON_QUERY_STOPWORDS = {
    "where",
    "what",
    "which",
    "when",
    "how",
    "is",
    "the",
    "a",
    "an",
    "in",
    "to",
    "of",
    "for",
    "and",
    "or",
    "on",
    "defined",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for pipeline test execution."""
    default_repo_url = str(PROJECT_ROOT) if (PROJECT_ROOT / ".git").exists() else None

    parser = argparse.ArgumentParser(
        description="Run end-to-end EIS pipeline test (ingest -> retrieve)."
    )
    parser.add_argument(
        "--repo-url",
        default=default_repo_url,
        help=(
            "Git repository URL/path to ingest. "
            "Defaults to current EIS path only when it is a git repository."
        ),
    )
    parser.add_argument(
        "--repo-name",
        default=None,
        help="Logical repository name to attach to ingested items (auto-derived by default).",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to clone when ingesting remote repository.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=120,
        help="Maximum number of files to ingest for test run.",
    )
    parser.add_argument(
        "--query",
        default="handle_compress?",
        help="Semantic test question.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top retrieval results to print.",
    )
    parser.add_argument(
        "--qdrant-url",
        default=None,
        help="Optional override for Qdrant URL (e.g. http://localhost:6333).",
    )
    parser.add_argument(
        "--upsert-batch-size",
        type=int,
        default=200,
        help="Number of embedded chunks to upsert per Qdrant request.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["auto", "deterministic", "openai"],
        default="auto",
        help="Embedding provider for pipeline test.",
    )
    parser.add_argument(
        "--collection-name",
        default=None,
        help="Optional explicit Qdrant collection name for this run.",
    )
    parser.add_argument(
        "--reuse-collection",
        action="store_true",
        help="Reuse default collection instead of creating an isolated per-run collection.",
    )
    parser.add_argument(
        "--disable-repo-filter",
        action="store_true",
        help="Disable search-time repo metadata filter (not recommended).",
    )

    return parser.parse_args()


def build_settings(
    base_settings: Settings,
    qdrant_url_override: str | None,
    qdrant_collection_name_override: str | None = None,
) -> Settings:
    """Create runtime settings, allowing explicit Qdrant URL override."""
    values = base_settings.model_dump()

    if qdrant_url_override:
        values["qdrant_url"] = qdrant_url_override
    if qdrant_collection_name_override:
        values["qdrant_collection_name"] = qdrant_collection_name_override

    return Settings(**values)


def maybe_host_fallback_qdrant(settings: Settings) -> Settings:
    """Fallback to localhost Qdrant when host-side execution uses Docker hostname."""
    parsed = urlparse(settings.qdrant_url)
    hostname = (parsed.hostname or "").lower()

    if hostname != "qdrant":
        return settings

    localhost_url = "http://localhost:6333"
    logger.warning(
        "QDRANT_URL points to Docker hostname '%s'; using host fallback %s for local script run.",
        settings.qdrant_url,
        localhost_url,
    )
    values = settings.model_dump()
    values["qdrant_url"] = localhost_url
    values["qdrant_api_key"] = None
    return Settings(**values)


def resolve_collection_name(
    base_collection: str,
    repo_name: str,
    explicit_collection_name: str | None,
    reuse_collection: bool,
) -> str:
    """Build collection name to isolate test runs and avoid stale result bleed-through."""
    if explicit_collection_name:
        return explicit_collection_name

    if reuse_collection:
        return base_collection

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", repo_name).strip("_").lower()[:40]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{base_collection}_{slug}_{timestamp}"


def build_embedding_provider(
    settings: Settings,
    provider_choice: str,
) -> EmbeddingProvider:
    """Create embedding provider based on CLI selection and settings."""
    if provider_choice == "deterministic":
        logger.warning(
            "Using deterministic embeddings (smoke-test mode). Relevance quality will be limited."
        )
        return DeterministicEmbeddingProvider(dimension=settings.qdrant_vector_size)

    if provider_choice == "openai":
        if not settings.embedding_api_key:
            raise ValueError(
                "--embedding-provider openai requires EMBEDDING_API_KEY in environment."
            )
        return OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            timeout_seconds=settings.embedding_timeout,
        )

    # auto mode
    if settings.embedding_api_key:
        logger.info("Using OpenAI embedding provider (auto mode)")
        return OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            timeout_seconds=settings.embedding_timeout,
        )

    logger.warning(
        "No EMBEDDING_API_KEY detected; falling back to deterministic embeddings. "
        "Results validate pipeline wiring but are not high-quality semantic rankings."
    )
    return DeterministicEmbeddingProvider(dimension=settings.qdrant_vector_size)


def derive_repo_name(repo_url: str, explicit_repo_name: str | None) -> str:
    """Derive repository label for metadata when not provided explicitly."""
    if explicit_repo_name:
        return explicit_repo_name

    candidate = repo_url.rstrip("/")
    if candidate.endswith(".git"):
        candidate = candidate[:-4]

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.path:
        path = parsed.path.strip("/")
        if path:
            return path

    return Path(candidate).name or "unknown/repo"


def extract_query_terms(query: str) -> list[str]:
    """Extract identifier-like query terms for lexical reranking."""
    raw_terms = re.findall(r"[A-Za-z_]\w{2,}", query.lower())
    filtered_terms = [term for term in raw_terms if term not in COMMON_QUERY_STOPWORDS]

    unique_terms: list[str] = []
    for term in filtered_terms:
        if term not in unique_terms:
            unique_terms.append(term)

    return unique_terms


def lexical_match_count(file_path: str, text: str, query_terms: list[str]) -> int:
    """Count query-term hits in file path and chunk text."""
    haystack_path = file_path.lower()
    haystack_text = text.lower()

    count = 0
    for term in query_terms:
        if term in haystack_path or term in haystack_text:
            count += 1

    return count


def deduplicate_results(results: list) -> list:
    """Drop near-duplicate hits from the same file/chunk prefix."""
    deduped = []
    seen_keys: set[tuple[str, str]] = set()

    for result in results:
        file_path = str(result.metadata.get("file_path", "unknown"))
        text_key = " ".join(result.text.split())[:100].lower()
        key = (file_path, text_key)
        if key in seen_keys:
            continue

        seen_keys.add(key)
        deduped.append(result)

    return deduped


def rerank_results(results: list, query: str) -> list:
    """Rerank semantic hits with lexical signal for identifier-heavy questions."""
    terms = extract_query_terms(query)
    if not terms:
        return results

    def rank_key(result: object) -> tuple[int, float]:
        file_path = str(getattr(result, "metadata", {}).get("file_path", "unknown"))
        text = str(getattr(result, "text", ""))
        lexical_hits = lexical_match_count(file_path, text, terms)
        semantic_score = float(getattr(result, "score", 0.0))
        return lexical_hits, semantic_score

    return sorted(results, key=rank_key, reverse=True)


def build_lexical_fallback_results(
    query: str,
    chunks: list,
    limit: int,
) -> list[VectorSearchResult]:
    """Build lexical fallback results directly from current-run chunks."""
    terms = extract_query_terms(query)
    if not terms:
        return []

    scored = []
    for chunk in chunks:
        file_path = str(chunk.metadata.get("file_path", "unknown"))
        matches = lexical_match_count(file_path, chunk.text, terms)
        if matches < 1:
            continue

        # Lexical scores are synthetic and only used for fallback ranking.
        score = float(matches)
        scored.append(
            VectorSearchResult(
                chunk_id=chunk.chunk_id,
                score=score,
                text=chunk.text,
                metadata=dict(chunk.metadata),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def merge_results(
    primary_results: list[VectorSearchResult],
    fallback_results: list[VectorSearchResult],
    limit: int,
) -> list[VectorSearchResult]:
    """Merge primary and fallback hits without duplicates."""
    merged: list[VectorSearchResult] = []
    seen_ids: set[str] = set()

    for result in [*primary_results, *fallback_results]:
        key = str(result.chunk_id)
        if key in seen_ids:
            continue
        seen_ids.add(key)
        merged.append(result)
        if len(merged) >= limit:
            break

    return merged


def run_pipeline(args: argparse.Namespace) -> int:
    """Execute the full ingestion-to-retrieval pipeline."""
    if not args.repo_url:
        logger.error(
            "No --repo-url provided and current workspace is not a git repository. "
            "Provide a git URL/path, e.g. --repo-url https://github.com/user/repo.git"
        )
        return 1

    logger.info("=" * 80)
    logger.info("EIS End-to-End Pipeline Test")
    logger.info("=" * 80)

    base_settings = get_settings()
    repo_name = derive_repo_name(args.repo_url, args.repo_name)
    collection_name = resolve_collection_name(
        base_collection=base_settings.qdrant_collection_name,
        repo_name=repo_name,
        explicit_collection_name=args.collection_name,
        reuse_collection=args.reuse_collection,
    )
    runtime_settings = build_settings(
        base_settings,
        args.qdrant_url,
        qdrant_collection_name_override=collection_name,
    )
    runtime_settings = maybe_host_fallback_qdrant(runtime_settings)

    logger.info("Using Qdrant collection: %s", runtime_settings.qdrant_collection_name)

    logger.info("Stage 1/5 - Ingestion")
    with tempfile.TemporaryDirectory(prefix="eis_pipeline_ingest_") as tmp_dir:
        loader = RepoLoader(
            repo_url=args.repo_url,
            local_path=str(Path(tmp_dir) / "repo"),
            repo_name=repo_name,
            branch=args.branch,
            max_files=args.max_files,
        )
        ingestion_service = IngestionService(loaders=[loader], deduplicate=True)
        knowledge_items = ingestion_service.run()

    if not knowledge_items:
        logger.error("Ingestion produced 0 knowledge items. Aborting pipeline test.")
        return 1

    logger.info("Ingested knowledge items: %d", len(knowledge_items))

    logger.info("Stage 2/5 - Chunking")
    chunk_service = ChunkService()
    knowledge_chunks = chunk_service.chunk_items(knowledge_items)

    if not knowledge_chunks:
        logger.error("Chunking produced 0 chunks. Aborting pipeline test.")
        return 1

    logger.info("Generated chunks: %d", len(knowledge_chunks))

    logger.info("Stage 3/5 - Embedding")
    embedding_provider = build_embedding_provider(
        settings=runtime_settings,
        provider_choice=args.embedding_provider,
    )
    embedding_service = EmbeddingService(
        provider=embedding_provider,
        batch_size=runtime_settings.embedding_batch_size,
    )
    embedded_chunks = embedding_service.embed_chunks(knowledge_chunks)

    if not embedded_chunks:
        logger.error("Embedding produced 0 vectors. Aborting pipeline test.")
        return 1

    logger.info("Generated embeddings: %d", len(embedded_chunks))

    logger.info("Stage 4/5 - Vector Storage (Qdrant)")
    vector_store = QdrantVectorStore(runtime_settings)
    for start in range(0, len(embedded_chunks), args.upsert_batch_size):
        batch = embedded_chunks[start : start + args.upsert_batch_size]
        vector_store.upsert_chunks(batch)

    logger.info("Stored embeddings in Qdrant: %d", len(embedded_chunks))

    logger.info("Stage 5/5 - Semantic Retrieval")
    query_embedding_service = QueryEmbeddingService(embedding_provider)
    query_vector = query_embedding_service.embed_question(args.query)

    vector_search_service = VectorSearchService(vector_store)
    metadata_filter = None
    if not args.disable_repo_filter:
        metadata_filter = {"repo": repo_name}

    # Over-fetch before post-processing so final top-k quality is more stable.
    search_limit = max(args.top_k * 8, args.top_k)
    results = vector_search_service.search_similar(
        query_vector=query_vector,
        top_k=search_limit,
        metadata_filter=metadata_filter,
    )

    if metadata_filter and not results:
        logger.warning(
            "No results found with repo metadata filter %s. Retrying without filter.",
            metadata_filter,
        )
        results = vector_search_service.search_similar(
            query_vector=query_vector,
            top_k=search_limit,
            metadata_filter=None,
        )

    results = deduplicate_results(results)
    results = rerank_results(results, args.query)

    lexical_fallback = build_lexical_fallback_results(
        query=args.query,
        chunks=knowledge_chunks,
        limit=args.top_k,
    )
    if lexical_fallback:
        results = merge_results(
            primary_results=results,
            fallback_results=lexical_fallback,
            limit=max(args.top_k * 2, args.top_k),
        )

    results = rerank_results(results, args.query)
    results = deduplicate_results(results)
    results = results[: args.top_k]

    logger.info("Retrieved results: %d", len(results))

    print("\n" + "=" * 80)
    print("PIPELINE TEST SUMMARY")
    print("=" * 80)
    print(f"Repository:           {args.repo_url}")
    print(f"Question:             {args.query}")
    print(f"Files ingested:       {len(knowledge_items)}")
    print(f"Chunks generated:     {len(knowledge_chunks)}")
    print(f"Embeddings stored:    {len(embedded_chunks)}")
    print(f"Top results returned: {len(results)}")
    print("=" * 80)

    if not results:
        print("\nNo retrieval results returned.")
        return 2

    print("\nTop Retrieval Results")
    print("-" * 80)
    for index, result in enumerate(results, start=1):
        file_path = str(result.metadata.get("file_path", "unknown"))
        preview = " ".join(result.text.split())[:180]
        print(f"[{index}] score={result.score:.4f}  file={file_path}")
        print(f"     preview={preview}...")

    return 0


def main() -> None:
    args = parse_args()
    exit_code = run_pipeline(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
