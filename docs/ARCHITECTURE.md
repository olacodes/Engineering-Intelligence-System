"""
ARCHITECTURE.md - Engineering Intelligence System Architectural Decisions

This document explains the foundational design choices for EIS,
including rationale and trade-offs.
"""

# Engineering Intelligence System - Architecture Decision Record

## 1. Layered Architecture

### Decision

Use a **layered architecture** with clear separation between:

- Ingestion Pipeline
- Chunking + Metadata
- Embedding Generation
- Vector Database
- Retrieval System
- LLM Reasoning
- API Layer
- Configuration/Models

### Rationale

- **Independent Evolution**: Each layer can be updated independently
- **Testability**: Layers can be tested in isolation with mock dependencies
- **Replacability**: Swap implementations (e.g., Qdrant → Weaviate) without affecting other layers
- **Scalability**: Optimize each layer separately for performance
- **Clear Contracts**: Type-safe boundaries using Pydantic models

### Trade-off

- Slightly more boilerplate than a monolithic approach
- Requires careful dependency management

## 2. Pydantic for Domain Models

### Decision

Use **Pydantic models** as the single source of truth for domain objects.

### Rationale

- **Validation**: Automatic validation at layer boundaries
- **Type Safety**: Full type hints with IDE autocomplete
- **API Schema**: Automatic OpenAPI documentation
- **Serialization**: JSON serialization without additional mapping
- **Extensibility**: Built-in support for custom validators and computed fields

### Example

```python
class KnowledgeItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType
    repo: str
    file_path: str
    content: str
    metadata: KnowledgeMetadata
```

Every field has:

- Type hint (validation)
- Default value or required marker
- Field description (for documentation)
- Validators (custom logic)

## 3. Enum for SourceType

### Decision

Use Python **Enum** for source types instead of string literals.

### Rationale

- **Type Safety**: Prevents invalid values
- **IDE Autocomplete**: Discover available options
- **Database Indexing**: Efficient categorical storage
- **API Documentation**: Clear list of valid types

### Sources Supported

- `GIT_COMMIT` - Commits with messages
- `PULL_REQUEST` - PRs and discussions
- `DOCUMENTATION` - Markdown docs
- `CODE_FILE` - Source code
- `ISSUE` - GitHub issues
- `COMMENT` - Code review comments

### Extensible

New source types are added by extending the Enum.

## 4. Metadata as Separate Model

### Decision

Separate **KnowledgeMetadata** from **KnowledgeItem**.

### Rationale

- **Flexibility**: Add metadata without changing core model
- **Composition**: Reuse metadata across different item types
- **Defaults**: Metadata fields have sensible defaults
- **Extensibility**: `custom_fields` dict for domain-specific data

### What Goes in Metadata

- `author` - Who created the source
- `created_at`, `updated_at` - Timestamps for recency weighting
- `tags` - Semantic tags for filtering and categorization
- `language` - Programming language or file type
- `source_url` - External reference for context
- `custom_fields` - Extensible dictionary for domain needs

## 5. UUID for Item IDs

### Decision

Use **UUID4** (random) for knowledge item IDs.

### Rationale

- **Uniqueness**: Guaranteed unique across distributed systems
- **No Coordination**: Don't need central ID authority
- **URL-safe**: Can use in API paths without encoding
- **References**: Easy to create parent-child relationships
- **Privacy**: Random UUIDs don't leak sequential information

### Trade-off

- Larger than sequential integers
- Less human-readable in logs

### Example

```python
id: UUID = Field(default_factory=uuid4)
```

## 6. Enum for Log Levels

### Decision

Configuration uses Python string for log level (e.g., "INFO", "DEBUG").

### Rationale

- **Standard Practice**: Matches logging module expectations
- **Environment Variables**: Easy to set via `LOG_LEVEL=DEBUG`
- **Flexibility**: Support all Python logging levels
- **Lowercase Comparison**: Handled in settings

### In Settings

```python
log_level: str = "INFO"
```

Can be overridden:

```bash
export LOG_LEVEL=DEBUG
```

## 7. Pydantic Settings for Configuration

### Decision

Use **pydantic-settings** for configuration management.

### Rationale

- **Environment Variables**: Automatic `.env` parsing
- **Type Validation**: Validate config on startup
- **Defaults**: Sensible defaults for development
- **Production Safe**: No hardcoded secrets
- **IDE Support**: Full autocomplete in code

### Pattern

```python
class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    llm_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### Benefits

- Singleton pattern via `@lru_cache()`
- Environment-specific `.env` files
- Type safe defaults
- Works with CI/CD platforms

## 8. Chunking Configuration Model

### Decision

Create **ChunkingConfig** model for document chunking parameters.

### Rationale

- **Configurability**: Adjust chunk size without code changes
- **Validation**: Ensure overlap < chunk_size
- **Reusability**: Same config across multiple chunking implementations
- **Testing**: Easy to test with different parameters

### Validation Example

```python
@validator("overlap_tokens")
def validate_overlap(cls, v: int, values: Dict[str, Any]) -> int:
    if "chunk_size" in values and v >= values["chunk_size"]:
        raise ValueError("overlap_tokens must be less than chunk_size")
    return v
```

## 9. Embedding Configuration Separation

### Decision

Create **EmbeddingConfig** separate from Settings.

### Rationale

- **Modularity**: Embedding config can be versioned independently
- **Testing**: Easy to test different embedding models
- **Future**: Support multiple embedding models
- **Clear Intent**: Shows embedding is a distinct concern

### Parameters

- `model_id` - Which embedding model to use
- `embedding_dimension` - Output vector size
- `batch_size` - How many items to embed at once
- `max_token_length` - Input truncation limit

## 10. SearchQuery and SearchResult Models

### Decision

Create explicit models for search requests and results.

### Rationale

- **API Specification**: Clear contract for search endpoint
- **Validation**: Validate top_k, filters on input
- **Type Safety**: SearchResult always has score and item
- **Extensibility**: Easy to add result explanation, metadata

### SearchQuery Fields

```python
query_text: str           # Natural language question
top_k: int = 10          # Number of results (1-100)
filters: Optional[Dict]  # repo, source_type, tags, etc.
```

### SearchResult Fields

```python
item: KnowledgeItem      # The retrieved item
score: float             # Relevance (0.0-1.0)
explanation: Optional[str]  # Why it matched
```

## 11. FastAPI Application Structure

### Decision

Use **class-based application factory** pattern.

### Rationale

- **Lifecycle Management**: Clean startup/shutdown hooks
- **Dependency Injection**: Settings and services as dependencies
- **Testing**: Easy to create test instances
- **Modularity**: Routes organized by concern
- **Middleware**: CORS and logging configured centrally

### Pattern

```python
class EISApplication:
    def __init__(self):
        self.settings = get_settings()

    def create_app(self) -> FastAPI:
        app = FastAPI(...)
        self._register_routes()
        return app

    def _register_routes(self) -> None:
        @app.get("/health")
        async def health(): ...
```

## 12. Placeholder Routes with 501 Status

### Decision

Implement placeholder endpoints that return 501 (Not Implemented).

### Rationale

- **API Discovery**: Clients can see available endpoints before implementation
- **Clear Intent**: 501 status signals "planned but not ready"
- **Documentation**: Routes documented in OpenAPI
- **Testing**: Can build frontend against skeleton
- **Gradual Implementation**: Fill in layers incrementally

### Example

```python
@app.post("/api/search")
async def search_knowledge(query: SearchQuery):
    raise HTTPException(status_code=501, detail="Search not yet implemented")
```

## 13. Type Hints Everywhere

### Decision

**Required** type hints on all functions, variables, and class attributes.

### Rationale

- **IDE Support**: Autocomplete and Go to Definition work
- **Documentation**: Code is self-documenting
- **Type Checking**: mypy can catch bugs
- **Maintainability**: Future developers understand contracts
- **API Safety**: FastAPI uses types for validation and docs

### Coverage

- Function parameters and returns
- Class attributes
- Instance variables
- Local variables (especially in complex functions)

### Examples

```python
def get_settings() -> Settings:  # Return type
    ...

def validate_file_path(cls, v: str) -> str:  # Parameter and return
    ...

item: KnowledgeItem = KnowledgeItem(...)  # Variable
```

## 14. Minimum Dependencies

### Decision

Keep external dependencies to the absolute minimum.

### Critical Dependencies

- **fastapi** - Web framework (minimal, fast)
- **pydantic** - Data validation (built into FastAPI)
- **pydantic-settings** - Configuration
- **uvicorn** - ASGI server (FastAPI's standard)
- **qdrant-client** - Vector database client
- **anthropic** - Claude API (LLM provider)
- **python-dotenv** - Environment management

### NOT Included (Yet)

- SQLAlchemy - Not needed, using Qdrant
- Django - Way too heavy for this use case
- Logging frameworks - Python's logging is sufficient
- Async frameworks beyond FastAPI - Keep it simple
- ORM - Vector DB doesn't need ORM

### Manual Logging

Production-grade logging without extra dependencies:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
```

## 15. Docstring Standards

### Decision

All public functions, classes, and modules have comprehensive docstrings.

### Format

- Module: Describe purpose and contents
- Class: Purpose and usage
- Function: What it does, args, returns, examples
- Type hints: Included as inline documentation

### Example

```python
def search_knowledge(query: SearchQuery) -> list[SearchResult]:
    """
    Search for knowledge items based on natural language query.

    Args:
        query: Search query parameters including text and filters

    Returns:
        List of matching knowledge items ranked by relevance

    Raises:
        HTTPException: If search service is unavailable

    Example:
        query = SearchQuery(query_text="how to...", top_k=10)
        results = await search_knowledge(query)
    """
    ...
```

## 16. Composition Over Inheritance

### Decision

Use composition (nested models) instead of inheritance.

### Example

```python
# Good: Composition
class KnowledgeItem(BaseModel):
    metadata: KnowledgeMetadata

# Bad: Inheritance
class KnowledgeItem(KnowledgeMetadata):
    ...
```

### Rationale

- **Flexibility**: Reuse metadata without coupling
- **Clear Intent**: What's core vs. auxiliary is obvious
- **Testing**: Easier to test independently

## 17. Validators for Business Logic

### Decision

Use Pydantic **@validator** decorators for field-level validation.

### Example

```python
@validator("file_path")
def validate_file_path(cls, v: str) -> str:
    if not v or not v.strip():
        raise ValueError("file_path cannot be empty")
    return v.strip()
```

### When to Use

- Single field validation
- Cross-field validation
- Automatic data cleaning (trim, normalize)
- Clear error messages

### When NOT to Use

- Complex business logic (goes in services)
- Cross-model validation (goes in application layer)

## 18. Async/Await

### Decision

Full async support in FastAPI, but blocking implementations initially.

### Rationale

- **Future-Proof**: Can plug in async I/O later (Qdrant, Claude APIs)
- **Scalability**: Handle many concurrent requests
- **FastAPI Native**: Natural fit with async framework
- **Progressive**: Start simple, add concurrency later

### Current

```python
@app.get("/health", response_model=SystemHealth)
async def health_check() -> SystemHealth:
    return SystemHealth(status="healthy")
```

### Future

```python
async def search_knowledge(query: SearchQuery):
    embeddings = await embedding_service.embed(query.query_text)
    results = await vector_db.search(embeddings)
    return results
```

## 19. Config vs. Secrets

### Decision

All configuration in Settings, use environment variables for secrets.

### Public Config (can be in code)

- API ports, hosts
- Default model names
- Standard timeouts

### Secrets (must be in environment)

- API keys (LLM, embeddings)
- Database credentials
- Auth tokens

### Pattern

```python
# Public - in code
qdrant_url: str = "http://localhost:6333"

# Secret - from environment only
llm_api_key: Optional[str] = None  # Must set via env
```

### Benefits

- No secrets in version control
- Works with CI/CD platforms
- Docker-friendly (pass env vars)
- Prod-safe (no defaults for secrets)

## 20. Health Check Endpoint

### Decision

Implement `/health` endpoint returning SystemHealth model.

### Rationale

- **Load Balancers**: Standard health check endpoint
- **Monitoring**: Track system status over time
- **Diagnostics**: Identify failing components
- **Extensible**: Add more status fields as system grows

### Fields

- `status` - "healthy" or "degraded"
- `indexed_items` - Count of indexed knowledge
- `vector_db_healthy` - Qdrant connection status
- `last_ingestion` - Timestamp of last import
- `errors` - List of recent issues

### Implementation

```python
@app.get("/health", response_model=SystemHealth)
async def health_check() -> SystemHealth:
    return SystemHealth(status="healthy")
```

## Summary

The EIS foundation is designed for:

1. **Modularity** - Independent layers, clear contracts
2. **Scalability** - Handle 100k+ files, concurrent requests
3. **Maintainability** - Type hints, docstrings, validation
4. **Extensibility** - Easy to add new source types, embeddings, etc.
5. **Production-Readiness** - Error handling, logging, health checks
6. **Developer Experience** - IDE autocomplete, clear errors, documentation

These architectural decisions enable rapid, confident implementation of the remaining layers without rework.
