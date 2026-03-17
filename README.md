# Engineering Intelligence System (EIS)

Engineering Intelligence System (EIS) is a FastAPI-based RAG platform for indexing engineering artifacts (code, pull requests, documentation) into Qdrant and answering engineering questions with grounded, source-cited responses.

## What EIS Does

- Ingests repositories, pull requests, and documentation into a unified knowledge base.
- Chunks and embeds content with metadata-rich payloads.
- Stores vectors in Qdrant for semantic retrieval.
- Runs a multi-stage retrieval pipeline (query classification + multi-source retrieval + reranking + context assembly).
- Generates final answers through an LLM reasoning layer constrained to retrieved context.

## Core Features

- Multi-source ingestion:
- `RepoLoader` for repository files.
- `PRLoader` for GitHub pull requests and optional comments.
- `DocLoader` for markdown/text docs.
- End-to-end indexing pipeline:
- `KnowledgeItem -> chunk -> embedding -> Qdrant upsert`.
- Multi-stage retrieval:
- Query intent classification (`implementation`, `dependency`, `history`).
- Source-type separated retrieval (`code`, `pr`, `doc`).
- Hybrid reranking (semantic + lexical + source priors + symbol hints).
- Context-size control to avoid LLM overload.
- Query API response fields:
- `answer`.
- `sources`.
- `confidence`.

## Architecture

EIS follows a layered architecture:

1. API Layer (`FastAPI`)
2. Ingestion Controller
3. Chunking Service
4. Embedding Service
5. Vector Store (`Qdrant`)
6. Retrieval Service (multi-stage)
7. LLM Reasoning Service

Data flow:

`source content -> knowledge items -> chunks -> embeddings -> Qdrant -> retrieval -> reasoning -> answer`

## Project Structure

- `main.py`: app entrypoint and route registration.
- `api/`: request models, routes, dependency wiring, controllers.
- `ingestion/`: loaders and ingestion orchestration.
- `chunking/`: chunk strategies and chunk service.
- `embeddings/`: embedding provider and batching service.
- `vector_store/`: Qdrant integration and vector search service.
- `retrieval/`: query models, classifier, multi-retriever, reranker, context builder, orchestrator.
- `llm/`: prompt builder, LLM client, reasoning service.
- `config/`: strongly typed settings loaded from environment.
- `models/`: domain models (`KnowledgeItem`, metadata, enums).

## API Endpoints

### Query

- `POST /api/ask`
- Purpose: ask engineering questions over indexed memory.

Request example:

```json
{
  "question": "Where is emission factor calculated?",
  "top_k": 5
}
```

Response shape:

```json
{
  "answer": "...",
  "sources": ["services/emissions/carbon_calculator.py", "PR#412"],
  "confidence": 0.82
}
```

### Ingestion

- `POST /ingest/repository`
- `POST /ingest/docs`
- `POST /ingest/prs`
- `POST /index/all`

### System

- `GET /`
- `GET /health`
- `GET /stats`
- `GET /sources`
- `GET /api/config`

## Quick Start

### Docker Compose (Recommended)

```bash
cp .env.example .env
./compile-requirements.sh
docker compose up --build -d
curl http://localhost:8000/health
```

API docs: `http://localhost:8000/docs`

### Local Python

```bash
python3.11 -m venv venv
source venv/bin/activate
./compile-requirements.sh
pip install -r requirements-dev.txt
cp .env.example .env
python main.py
```

If not using Compose, run Qdrant separately:

```bash
docker run -p 6333:6333 qdrant/qdrant:latest
```

## Configuration

Settings are loaded from `.env` via `pydantic-settings` in `config/settings.py`.

Most important environment variables:

- `QDRANT_URL`: Qdrant endpoint.
- `QDRANT_API_KEY`: optional for local, required for secured/cloud Qdrant.
- `QDRANT_COLLECTION_NAME`: vector collection name.
- `EMBEDDING_API_KEY`: enables OpenAI-compatible embeddings.
- `EMBEDDING_MODEL`: embedding model name.
- `EMBEDDING_DIMENSION`: vector size (must align with collection/model).
- `LLM_API_KEY` or `ANTHROPIC_API_KEY`: enables reasoning layer.
- `LLM_MODEL`: LLM model identifier.
- `API_HOST`, `API_PORT`, `CORS_ORIGINS`.
- `GITHUB_TOKEN`: optional, recommended for higher PR ingestion limits.

## Ingestion Examples

### Ingest a Repository

```bash
curl -X POST "http://localhost:8000/ingest/repository" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/facebook/react.git",
    "branch": "main",
    "repo_name": "facebook/react",
    "max_files": 500
  }'
```

### Ingest Pull Requests

```bash
curl -X POST "http://localhost:8000/ingest/prs" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_owner": "facebook",
    "repo_name": "react",
    "max_prs": 100,
    "status": "closed",
    "include_comments": true
  }'
```

Notes:

- Public repository PRs can be ingested without a token.
- `GITHUB_TOKEN` is recommended for higher rate limits and private repo access.

### Ingest Documentation

```bash
curl -X POST "http://localhost:8000/ingest/docs" \
  -H "Content-Type: application/json" \
  -d '{
    "docs_path": "./docs",
    "repo_name": "my-project-docs",
    "split_on_headers": true,
    "min_section_length": 100
  }'
```

## Retrieval Pipeline (Implemented)

EIS uses a multi-stage retrieval pipeline in `retrieval/`:

1. `QueryClassifier`

- Classifies question intent (`implementation`, `dependency`, `history`).
- Produces per-source retrieval budgets and weights.

1. `MultiSourceRetriever`

- Runs separate vector searches for `code`, `pr`, and `doc` using metadata filters.

1. `ReRanker`

- Fuses semantic score, lexical overlap, source priors, and symbol hints.

1. `ContextBuilder`

- Groups selected chunks by source type.
- Enforces character/chunk limits for stable LLM prompts.

1. `RetrievalService`

- Orchestrates all stages and returns `QueryContext` for reasoning.

## LLM Reasoning

`ReasoningService` builds prompts from retrieved context and parses structured model output into:

- `answer`: final explanation text.
- `sources`: source identifiers cited in the answer.
- `confidence`: normalized value in `[0.0, 1.0]`.

Prompt constraints are defined in `llm/prompt_builder.py`.

## Makefile Commands

```bash
make help
make up
make down
make logs
make test
make lint
make format
make health
```

## Troubleshooting

- `/health` returns `degraded`:
- Check Qdrant status and `QDRANT_URL`.
- Embedding failures:
- Verify `EMBEDDING_API_KEY`, model selection, and network/TLS connectivity.
- PR ingestion is rate-limited:
- Set `GITHUB_TOKEN`.
- API response does not reflect recent code changes:
- Restart or rebuild service (`docker compose up --build -d`).

## Additional Documentation

- `STARTUP.md`: step-by-step setup.
- `DOCKER.md`: containerization and deployment.
- `ARCHITECTURE.md`: design decisions.
- `INGESTION.md`: ingestion deep dive.
- `INGESTION_QUICKSTART.md`: ingestion usage examples.
- `QUICK_REFERENCE.md`: command cheat sheet.

## License

Apache 2.0
