# Docker Setup & Containerization Guide

This guide covers setting up and using Docker with the Engineering Intelligence System (EIS).

## Quick Start

### Option 1: Development Setup (Recommended)

```bash
# Compile dependencies
./compile-requirements.sh

# Start full stack with Docker Compose
docker-compose up

# In another terminal, test the API
curl http://localhost:8000/health
```

### Option 2: Production Deployment

```bash
# Build production image
docker build -t eis:latest .

# Run with Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
docker run -d --name eis -p 8000:8000 \
  --env ENVIRONMENT=production \
  --env QDRANT_URL=http://qdrant:6333 \
  eis:latest
```

## Architecture Overview

### Three Docker Setups

#### 1. **Dockerfile** (Production)

Multi-stage optimized build for deployment:

- **Stage 1 (Builder)**: Installs all Python dependencies into venv
- **Stage 2 (Runtime)**: Copies only venv, minimal base image
- **Final Size**: ~200-300 MB (vs ~1 GB with single-stage)
- **Security**: Non-root user `eis:1000`
- **Health Check**: Built-in `/health` endpoint check

**Key Features:**

```dockerfile
# Multi-stage build reduces final image size
FROM python:3.11-slim AS builder
# ... install dependencies into /opt/venv ...

FROM python:3.11-slim
# ... copy venv, minimal runtime ...
```

#### 2. **Dockerfile.dev** (Development)

Full-featured environment for developers:

- **Base**: `python:3.11-slim`
- **Tools**: git, vim, nano, build-essential, curl
- **Debug Utilities**: postgresql-client, sqlite3
- **Dev Dependencies**: pytest, black, ruff, mypy, ipython
- **Size**: ~500-600 MB (not optimized, includes tools)

**Key Features:**

```dockerfile
# Rich development environment
RUN apt-get update && apt-get install -y \
  git build-essential vim nano \
  postgresql-client sqlite3 curl

RUN pip install -r requirements-dev.txt
```

#### 3. **docker-compose.yml** (Orchestration)

Coordinates multiple services locally:

- **qdrant**: Vector database (port 6333-6334)
- **eis**: Main application (port 8000)
- **dev**: Optional development container (bash shell)

## Files & Configuration

### Dependency Files

#### `requirements.in` (Base Dependencies)

Specifies core application dependencies:

```txt
fastapi>=0.104.0          # Web framework
pydantic>=2.5.0           # Data validation
qdrant-client>=1.17.0      # Vector store
anthropic>=0.7.0          # LLM provider
requests>=2.31.0          # HTTP client
```

**Format Notes:**

- Uses `>=` (not pinned) for flexibility
- Allows patch/minor updates
- Must be compiled before use

#### `requirements-dev.in` (Development)

Extends base with development tools:

```txt
-r requirements.in        # Include base dependencies
pytest>=7.4.0            # Testing framework
black>=23.11.0           # Code formatting
ruff>=0.11.0             # Linting
mypy>=1.7.0              # Type checking
isort>=5.12.0            # Import sorting
```

### Compilation Script

#### `compile-requirements.sh`

Automates pip-compile dependency locking:

```bash
# Generate locked requirements
./compile-requirements.sh

# Upgrade all dependencies
./compile-requirements.sh --upgrade
```

**What It Does:**

1. Installs pip-tools if needed
2. Resolves all transitive dependencies
3. Generates `requirements.txt` (production)
4. Generates `requirements-dev.txt` (development)
5. Creates `.txt` files with exact versions for reproducibility

### Build Optimization

#### `.dockerignore`

Excludes unnecessary files from build context:

```
.git/                     # Version control
__pycache__/              # Python cache
*.pyc, *.pyo             # Bytecode
venv/, .venv/            # Virtual environments
node_modules/            # Node packages
.pytest_cache/           # Test cache
.mypy_cache/             # Type checking cache
.ruff_cache/             # Linter cache
```

**Impact**: Reduces build context from 500MB+ to ~10MB

## Docker Commands

### Using Makefile (Recommended)

```bash
make build              # Build Docker image
make up                 # Start services
make down               # Stop services
make logs               # View logs
make shell              # Access container shell
make test               # Run tests
make lint               # Run linters
make format             # Format code
make health             # Check service health
make clean              # Remove containers
```

### Using Docker CLI Directly

#### Building Images

```bash
# Build production image
docker build -t eis:latest .

# Build with tag (date-based versioning)
docker build -t eis:$(date +%Y%m%d) .

# Build development image
docker build -f Dockerfile.dev -t eis:dev .

# Build with custom build args
docker build --build-arg ENVIRONMENT=production -t eis:latest .
```

#### Running Containers

```bash
# Run production container (single command)
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e QDRANT_URL=http://qdrant:6333 \
  eis:latest

# Run interactive bash
docker run -it --rm eis:latest bash

# Run with volume mount (for development)
docker run -it \
  -v $(pwd):/app \
  -e ENVIRONMENT=development \
  eis:dev bash
```

### Using Docker Compose

#### Basic Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f        # All services
docker-compose logs -f eis    # Just app
docker-compose logs -f qdrant # Just database

# Execute command in running container
docker-compose exec eis bash
docker-compose exec eis python -m pytest
```

#### Development Workflow

```bash
# Start core services
docker-compose up qdrant eis

# Start development container with shell
docker-compose run --rm dev bash

# Within dev container, run tests
docker-compose exec eis pytest

# Run with environment variable override
docker-compose -e DEBUG=true up
```

#### Service Management

```bash
# Restart services
docker-compose restart
docker-compose restart eis

# Stop specific service
docker-compose stop eis

# Remove everything including volumes
docker-compose down -v
```

## Environment Configuration

### `.env` File

Create a `.env` file in project root for environment variables:

```env
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=Engineering Intelligence System

# Qdrant Vector Store
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=          # Leave empty for local, set for cloud

# Embeddings
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIMENSION=1536

# LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=sk-...

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**Loading in Docker:**

```yaml
# docker-compose.yml
services:
  eis:
    env_file: .env
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      DEBUG: ${DEBUG}
```

**Loading in Python:**

```python
from config.settings import get_settings

settings = get_settings()
print(settings.environment)
print(settings.qdrant_url)
```

## Health Checks

### Built-in Health Endpoint

```bash
# Check API health
curl http://localhost:8000/health

# Response (200 OK):
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-10T15:30:00Z"
}
```

### Docker Compose Health Checks

```yaml
services:
  qdrant:
    healthcheck:
      test: ["CMD-SHELL", "bash -c '</dev/tcp/127.0.0.1/6333'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  eis:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Check Status

```bash
# View health status
docker-compose ps

# Manual check
make health

# Check Qdrant specifically (from host)
curl http://localhost:6333/health
```

## Volume Management

### Persistent Data

```yaml
volumes:
  qdrant_storage:
    driver: local
```

**Mount Locations:**

- **Qdrant**: `/qdrant/storage` → `qdrant_storage` volume
- **EIS App**: `/app` → current directory (bind mount)

### Development Volume Mounts

```bash
# Mount entire project for live reloading
docker-compose run -v $(pwd):/app --rm dev bash

# Mount only source code
docker-compose run -v $(pwd)/eis:/app/eis --rm dev pytest
```

## Common Workflows

### Development Workflow

```bash
# 1. Compile dependencies (one-time)
./compile-requirements.sh

# 2. Start services
make up

# 3. In another terminal, run tests
make test

# 4. Format and lint code
make format
make lint

# 5. View logs
make logs

# 6. Stop services
make down
```

### Deployment Workflow

```bash
# 1. Build production image
make build-prod

# 2. Tag for registry
docker tag eis:latest myregistry.azurecr.io/eis:latest

# 3. Push to registry
docker push myregistry.azurecr.io/eis:latest

# 4. Deploy (e.g., Kubernetes)
kubectl apply -f k8s/deployment.yaml
```

### Debugging Workflow

```bash
# 1. Start with debug logging
DEBUG=true LOG_LEVEL=DEBUG docker-compose up

# 2. Access container shell
make shell

# 3. Run Python debugger
docker-compose exec eis python -m pdb ./your_script.py

# 4. Inspect logs
docker-compose logs -f --tail 100 eis
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs eis

# Check if port is already in use
lsof -i :8000

# Kill process using port
kill -9 <PID>

# Rebuild without cache
docker-compose build --no-cache
```

### Qdrant Connection Failed

```bash
# Verify Qdrant is running
docker-compose ps qdrant

# Check Qdrant logs
docker-compose logs qdrant

# Verify network connectivity
docker-compose exec eis ping qdrant

# Check Qdrant endpoint
docker-compose exec eis curl http://qdrant:6333/health
```

### Permission Issues

```bash
# Check user inside container
docker-compose exec eis whoami  # Should be 'eis'

# Fix volume permissions
sudo chown -R 1000:1000 ./

# Or rebuild with different user
docker build --build-arg USER_ID=1000 .
```

### Out of Disk Space

```bash
# Clean up Docker resources
docker system prune -a

# Remove specific image
docker rmi eis:latest

# Check disk usage
docker system df
```

## Performance Optimization

### Image Size Reduction

```dockerfile
# Multi-stage build (already in Dockerfile)
FROM python:3.11-slim AS builder
# ... build ...
FROM python:3.11-slim  # ~150MB base
# ... copy only venv ...
# Result: ~200-300MB total vs ~1GB
```

### Build Speed

```bash
# Use BuildKit (faster)
DOCKER_BUILDKIT=1 docker build .

# Use cache effectively
docker build --cache-from eis:latest .

# Parallel builds (docker-compose)
docker-compose build --parallel
```

### Runtime Performance

```yaml
# Limit resources
services:
  eis:
    cpus: "1.5"
    memswap_limit: 2g
    mem_limit: 2g
```

## Production Considerations

### Security Best Practices

1. ✅ Non-root user (`eis:1000`)
2. ✅ Read-only filesystem (optional):
   ```yaml
   security_opt:
     - read_only:true
   ```
3. ✅ Health checks configured
4. ✅ Resource limits set
5. ✅ Environment variables for secrets

### Network Security

```yaml
networks:
  eis-network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_ip_masquerade: "true"
```

### Logging

```bash
# Centralized logging (example with journald)
docker run \
  --log-driver=journald \
  --log-opt tag=eis \
  eis:latest

# View logs
journalctl CONTAINER_NAME=eis -f
```

### Secrets Management

```bash
# Using Docker secrets (Swarm)
docker secret create anthropic_key ./anthropic_key.txt

# Using environment variables (development)
export ANTHROPIC_API_KEY=sk-...
docker-compose up

# Using .env file (development only!)
# Never commit .env to version control
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t eis:${{ github.sha }} .

      - name: Run tests in container
        run: docker run --rm eis:${{ github.sha }} pytest

      - name: Push to registry
        run: docker push eis:${{ github.sha }}
```

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best Practices for Python Docker Images](https://docs.docker.com/language/python/build-images/)
- [Qdrant Docker Documentation](https://qdrant.tech/documentation/guides/installation/#docker)

## Quick Reference

| Task   | Command                                                         |
| ------ | --------------------------------------------------------------- |
| Build  | `make build` or `docker-compose build`                          |
| Start  | `make up` or `docker-compose up`                                |
| Stop   | `make down` or `docker-compose down`                            |
| Logs   | `make logs` or `docker-compose logs -f eis`                     |
| Shell  | `make shell` or `docker-compose exec eis bash`                  |
| Test   | `make test` or `docker-compose exec eis pytest`                 |
| Format | `make format` or `docker-compose exec eis black .`              |
| Lint   | `make lint` or `docker-compose exec eis ruff check .`           |
| Clean  | `make clean` or `docker-compose down && docker system prune -f` |

---

**For more information:**

- Development setup: See `INGESTION_QUICKSTART.md`
- Architecture details: See `ARCHITECTURE.md`
- API documentation: See `/docs` endpoint after starting with `make up`
