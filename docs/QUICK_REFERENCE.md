# EIS Quick Reference Card

Keep this handy while developing!

## One-Minute Setup

```bash
cp .env.example .env          # Configure
./compile-requirements.sh     # Lock dependencies
docker-compose up             # Start all services
curl http://localhost:8000/health  # Verify
```

## Essential Commands

### Starting & Stopping

```bash
make up              # Start services
make down            # Stop services
make restart         # Restart services
make logs            # View logs (-f to follow)
make shell           # Bash into app container
make health          # Check service health
```

### Development

```bash
make test            # Run tests
make format          # Format code (black + isort)
make lint            # Check code quality (ruff + mypy)
make install-dev     # Install dev dependencies
```

### Dependencies

```bash
./compile-requirements.sh              # Generate from .in files
./compile-requirements.sh --upgrade    # Upgrade and regenerate
pip install package_name               # Add package (then recompile)
cat requirements.txt                   # View locked versions
```

### Docker

```bash
make build           # Build image
docker-compose ps    # List containers
docker-compose logs eis  # App logs only
docker-compose exec eis bash  # Access container
```

## Directory Structure

```
eis/
├── api/               # API endpoints (future)
├── ingestion/         # Data ingestion loaders
│   ├── base_loader.py
│   ├── repo_loader.py
│   ├── pr_loader.py
│   ├── doc_loader.py
│   └── ingestion_service.py
├── models/            # Data models
│   └── knowledge_models.py
├── config/            # Configuration
│   └── settings.py
├── chunking/          # Text chunking (future)
├── embeddings/        # Embeddings generation (future)
├── retrieval/         # Vector search (future)
├── llm/              # LLM integration (future)
├── vector_store/     # Vector store (future)
├── utils/            # Utilities
│   └── logger.py
├── main.py           # FastAPI app
├── config.yaml       # (optional) Configuration override
├── Dockerfile        # Production Docker image
├── Dockerfile.dev    # Development Docker image
├── docker-compose.yml # Service orchestration
├── .env.example      # Environment template
├── Makefile          # Command shortcuts
├── STARTUP.md        # Getting started guide
├── ARCHITECTURE.md   # Design decisions
├── INGESTION.md      # Ingestion details
├── DOCKER.md         # Docker guide
└── README.md         # Overview
```

## API Endpoints (Current)

```bash
# Health check
GET /health          # Returns {"status": "healthy", ...}

# Root info
GET /                # Returns app info

# Future endpoints
POST /api/knowledge/ingest     # Ingest documents
POST /api/search               # Search knowledge
```

## Environment Variables (Quick List)

```env
# Required
ANTHROPIC_API_KEY=sk-...

# Database
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=              # Leave empty for local

# API
API_PORT=8000
API_HOST=0.0.0.0

# Configuration
ENVIRONMENT=development      # development, staging, production
DEBUG=true                   # true or false
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
```

See `.env.example` for complete options.

## Python Code Patterns

### Using Settings

```python
from config.settings import get_settings

settings = get_settings()
print(settings.qdrant_url)
print(settings.llm_model)
```

### Creating KnowledgeItem

```python
from models.knowledge_models import KnowledgeItem, SourceType

item = KnowledgeItem(
    source_type=SourceType.GIT_COMMIT,
    repo="https://github.com/example/repo",
    file_path="src/main.py",
    content="# Code here",
    author="John Doe",
    tags=["python", "main"]
)
```

### Using Loaders

```python
from ingestion.repo_loader import RepoLoader
from ingestion.ingestion_service import IngestionService

loader = RepoLoader(repo_url="https://github.com/example/repo")
items = loader.load()

# Or with service
service = IngestionService([loader])
items = service.run()
stats = service.get_statistics()
```

## Debugging Tips

```bash
# View app logs
docker-compose logs eis

# Follow logs in real-time
docker-compose logs -f eis

# Check specific service
docker-compose logs qdrant

# Access container and run Python
docker-compose exec eis python
# Then:
from config.settings import get_settings
settings = get_settings()
print(settings.dict())

# Run test with verbose output
docker-compose exec eis pytest -vv

# Run single test
docker-compose exec eis pytest tests/test_ingestion.py::test_repo_loader
```

## Common Issues

| Problem               | Solution                                   |
| --------------------- | ------------------------------------------ |
| Port 8000 in use      | `lsof -i :8000` then `kill -9 <PID>`       |
| Qdrant won't start    | `docker-compose logs qdrant`               |
| Dependencies missing  | `./compile-requirements.sh` then rebuild   |
| API returns 500       | Check logs: `make logs`                    |
| Container won't start | Rebuild: `docker-compose build --no-cache` |
| Permission denied     | `chmod +x compile-requirements.sh`         |

## Docker Compose Override

Create `docker-compose.override.yml` for local changes (git-ignored):

```yaml
version: "3.8"
services:
  eis:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./eis:/app/eis # Live reload
    ports:
      - "8000:8000"
```

## Testing Quick Reference

```bash
make test                    # Run all tests
make test-coverage          # With coverage report
make test-verbose           # Verbose output (-vv)

# Or directly
docker-compose exec eis pytest tests/
docker-compose exec eis pytest tests/test_ingestion.py -v
docker-compose exec eis pytest tests/test_models.py::TestSourceType -vv
```

## Git Workflow

```bash
git status                   # See changes
git add eis/                 # Stage changes
git commit -m "Feature description"  # Commit
git push origin branch-name  # Push
git pull origin main         # Update from main
```

## Performance Checks

```bash
# Check container resources
docker stats

# Check volume usage
docker volume inspect eis_qdrant_storage

# Check Qdrant performance
curl http://localhost:6333/metrics

# Check app endpoints
curl http://localhost:8000/docs  # Open in browser for interactive testing
```

## File Editing with Docker

```bash
# Edit file locally in your IDE, changes auto-sync with volume mount

# Or edit inside container
docker-compose exec eis nano eis/main.py
docker-compose exec eis vim eis/config/settings.py

# View file
docker-compose exec eis cat eis/models/knowledge_models.py

# List directory
docker-compose exec eis ls -la eis/ingestion/
```

## Documentation Files

| File                                     | Purpose                     |
| ---------------------------------------- | --------------------------- |
| [README.md](README.md)                   | Project overview & features |
| [STARTUP.md](STARTUP.md)                 | Getting started (detailed)  |
| [ARCHITECTURE.md](ARCHITECTURE.md)       | Design decisions & patterns |
| [INGESTION.md](INGESTION.md)             | Ingestion pipeline details  |
| [DOCKER.md](DOCKER.md)                   | Docker setup & deployment   |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | This file                   |

## Useful Aliases

Add to your shell config (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
alias eis-up='cd /path/to/eis && docker-compose up'
alias eis-down='cd /path/to/eis && docker-compose down'
alias eis-logs='cd /path/to/eis && docker-compose logs -f eis'
alias eis-shell='cd /path/to/eis && docker-compose exec eis bash'
alias eis-test='cd /path/to/eis && docker-compose exec eis pytest'
```

Then just run: `eis-up`, `eis-logs`, etc.

## State Diagram

```
Development Workflow:
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│ Code Change │ --> │ Run Tests    │ --> │ Format   │
└─────────────┘     └──────────────┘     └──────────┘
      ↑                                         ↓
      └──────────────────┬──────────────────────┘
                         ↓
                    ┌──────────┐
                    │  Commit  │
                    └──────────┘
```

## Resource Limits (for stability)

Default Docker resource limits:

```yaml
eis:
  cpus: "2" # Max 2 CPU cores
  mem_limit: 2g # Max 2GB RAM

qdrant:
  cpus: "1" # Max 1 CPU core
  mem_limit: 1g # Max 1GB RAM
```

Modify in `docker-compose.yml` if needed for your machine.

## API Response Examples

### Health Endpoint

```json
GET /health

{
  "status": "healthy",
  "timestamp": "2024-01-10T15:30:00Z",
  "version": "0.1.0"
}
```

### Error Response

```json
{
  "detail": "String error message",
  "type": "error_type"
}
```

---

**Last Updated:** 2024-01-10  
**EIS Version:** 0.1.0  
**Python:** 3.11+  
**Docker:** 20.10+
