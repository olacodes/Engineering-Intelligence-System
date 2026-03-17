"""Request and response models for ingestion and indexing APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class RepositoryIngestRequest(BaseModel):
    """Request payload for repository ingestion and indexing."""

    repo_url: str = Field(..., min_length=1, description="Git repository URL")
    branch: str = Field(default="main", min_length=1, description="Git branch")
    repo_name: str | None = Field(
        default=None,
        description="Optional logical repo name (auto-derived when omitted)",
    )
    max_files: int = Field(
        default=500,
        ge=1,
        le=20000,
        description="Maximum number of files to ingest from repository",
    )

    @field_validator("repo_url", "branch")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Normalize non-empty text fields."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be empty")
        return normalized


class PRIngestRequest(BaseModel):
    """Request payload for pull request ingestion and indexing."""

    repo_owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo_name: str = Field(..., min_length=1, description="GitHub repository name")
    max_prs: int = Field(default=100, ge=1, le=500, description="Maximum PRs to ingest")
    status: str = Field(
        default="all",
        description="PR state filter: open | closed | all",
    )
    include_comments: bool = Field(
        default=True,
        description="Whether to ingest PR comments",
    )
    github_token: str | None = Field(
        default=None,
        description="Optional GitHub token override (uses env when omitted)",
    )

    @field_validator("repo_owner", "repo_name", "status")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normalize text fields."""
        return value.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """Validate PR status filter."""
        normalized = value.lower().strip()
        if normalized not in {"open", "closed", "all"}:
            raise ValueError("status must be one of: open, closed, all")
        return normalized


class DocsIngestRequest(BaseModel):
    """Request payload for documentation ingestion and indexing."""

    docs_path: str = Field(..., min_length=1, description="Directory containing docs")
    repo_name: str | None = Field(
        default=None,
        description="Optional source identifier for docs",
    )
    split_on_headers: bool = Field(
        default=False,
        description="Split docs into sections by markdown headers",
    )
    min_section_length: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Minimum section length when splitting docs",
    )

    @field_validator("docs_path")
    @classmethod
    def strip_docs_path(cls, value: str) -> str:
        """Normalize docs path."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("docs_path cannot be empty")
        return normalized


class IndexAllRequest(BaseModel):
    """Request payload for running indexing on multiple source types."""

    repository: RepositoryIngestRequest | None = Field(
        default=None,
        description="Repository ingestion payload",
    )
    docs: DocsIngestRequest | None = Field(
        default=None,
        description="Documentation ingestion payload",
    )
    prs: PRIngestRequest | None = Field(
        default=None,
        description="Pull request ingestion payload",
    )

    @model_validator(mode="after")
    def validate_at_least_one_source(self) -> "IndexAllRequest":
        """Ensure at least one source payload is provided."""
        if not any([self.repository, self.docs, self.prs]):
            raise ValueError("At least one of repository, docs, or prs is required")
        return self


class IndexResponse(BaseModel):
    """Response payload summarizing one ingestion/indexing run."""

    files_ingested: int = Field(..., ge=0, description="Ingested source item count")
    chunks_created: int = Field(..., ge=0, description="Chunk count generated")
    vectors_stored: int = Field(..., ge=0, description="Embedding vectors stored")
    duration_seconds: float = Field(..., ge=0.0, description="Total operation duration")
    source: str = Field(..., description="Source type label")


class IndexAllResponse(BaseModel):
    """Response payload summarizing combined indexing runs."""

    runs: list[IndexResponse] = Field(default_factory=list)
    total_files_ingested: int = Field(..., ge=0)
    total_chunks_created: int = Field(..., ge=0)
    total_vectors_stored: int = Field(..., ge=0)
    duration_seconds: float = Field(..., ge=0.0)


class HealthResponse(BaseModel):
    """Simple system health response."""

    status: str = Field(..., description="Health status")


class StatsResponse(BaseModel):
    """Index statistics response."""

    total_chunks: int = Field(..., ge=0)
    total_sources: int = Field(..., ge=0)
    vector_collection: str = Field(...)


class SourcesResponse(BaseModel):
    """Known indexed source list response."""

    sources: list[str] = Field(default_factory=list)
