# Engineering Intelligence System (EIS) - Startup Guide

This guide will help you get the entire Engineering Intelligence System up and running from scratch.

## Prerequisites

### Required Software

- **Python 3.11+** - Download from https://www.python.org/
- **Docker** - Download from https://www.docker.com/
- **Git** - Download from https://git-scm.com/
- **Make** (optional, but recommended) - Pre-installed on macOS/Linux, use WSL on Windows

### API Keys (for full functionality)

- **Anthropic API Key** - Get from https://console.anthropic.com/ (Claude LLM)
- **GitHub Token** (optional) - Get from https://github.com/settings/tokens (for higher rate limits)

## Quick Start (5 minutes)

### Option 1: Using Docker Compose (Recommended)

```bash
# Clone or navigate to your EIS project
cd /path/to/eis

# 1. Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # Or use your favorite editor
# Add: ANTHROPIC_API_KEY=sk-your-key-here

# 2. Compile dependencies (generates requirements.txt)
./compile-requirements.sh

# 3. Start all services
docker compose up

# Expected output:
# eis-qdrant-1 | ...
# eis-eis-1    | INFO: Started server process
# eis-eis-1    | Uvicorn running on http://0.0.0.0:8000

# 4. In another terminal, verify it's running
curl http://localhost:8000/health
# Response: {"status":"healthy",...}
```

**Done!** EIS is now running at http://localhost:8000

### Option 2: Using Local Python

```bash
# 1. Navigate to project
cd /path/to/eis

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Compile and install dependencies
./compile-requirements.sh
pip install -r requirements-dev.txt

# 4. Copy environment file
cp .env.example .env
nano .env  # Add your API keys

# 5. Start services manually
# Terminal 1 - Start Qdrant (Docker)
docker run -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Terminal 2 - Start EIS app
cd /path/to/eis
python main.py

# Expected output:
# INFO:     Started server process [12345]
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step-by-Step Detailed Guide

### Step 1: Verify Prerequisites

```bash
# Check Python version
python3 --version        # Should be 3.11 or higher

# Check Docker
docker --version         # Should be 20.10 or higher
docker run hello-world   # Should work

# Check Git
git --version            # Should be 2.30 or higher
```

### Step 2: Navigate to Project

```bash
cd /Users/sodiqolatunde/work/2026/eis
# Or wherever your EIS project is located
```

### Step 3: Environment Configuration

**Create `.env` from template:**

```bash
cp .env.example .env
```

**Edit `.env` with your settings:**

```bash
# On macOS/Linux
nano .env

# On Windows (PowerShell)
notepad .env
```

**Key variables to set:**

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...      # Your Claude API key
QDRANT_URL=http://qdrant:6333     # For Docker, local: http://localhost:6333

# Optional
GITHUB_TOKEN=github_pat_...        # For cloning private repos
ENVIRONMENT=development            # development or production
DEBUG=true                         # Enable debug mode
```

### Step 4: Compile Dependencies

```bash
# This converts requirements.in → requirements.txt with locked versions
./compile-requirements.sh

# To upgrade dependencies
./compile-requirements.sh --upgrade

# Check generated files
ls -la requirements*.txt
# Should see:
# requirements.txt        (base deps, ~50-100 lines)
# requirements-dev.txt    (all deps, ~150-200 lines)
```

### Step 5: Start Services

**Option A: Docker Compose (Recommended)**

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Option B: Local Development**

```bash
# Terminal 1: Start Qdrant (vector database)
docker run --name qdrant -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant

# Terminal 2: Create virtual environment and install
cd /path/to/eis
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Terminal 3: Start FastAPI server
cd /path/to/eis
source venv/bin/activate
python main.py
```

### Step 6: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Expected response (200 OK):
{
  "status": "healthy",
  "timestamp": "2024-01-10T15:30:00Z",
  "version": "0.1.0"
}

# Check API documentation
# Visit in browser: http://localhost:8000/docs
```

## Using Make Commands (Recommended)

If you have `make` installed, these commands work:

```bash
# Build Docker image
make build

# Start services
make up

# View logs
make logs

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Stop services
make down

# See all available commands
make help
```

## Development Workflow

### 1. Start Development Mode

```bash
# Terminal 1: Start services
docker-compose up

# Or use Make
make up
```

### 2. Make Code Changes

Edit files in your favorite editor:

- Add loaders: `eis/ingestion/loaders/`
- Modify models: `eis/models/`
- Create endpoints: `eis/api/`

### 3. Test Changes

```bash
# Run all tests
make test

# Or with Docker
docker-compose exec eis pytest

# Run specific test file
docker-compose exec eis pytest tests/test_ingestion.py

# Run with verbose output
docker-compose exec eis pytest -vv
```

### 4. Format Code

```bash
# Format with Black
make format

# Check formatting
make format-check

# Or directly with Docker
docker-compose exec eis black .
docker-compose exec eis isort .
```

### 5. Lint Code

```bash
# Run all linters
make lint

# Or with Docker
docker-compose exec eis ruff check .
docker-compose exec eis mypy .
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use Docker to check
docker ps | grep 8000
```

### Qdrant Connection Failed

```bash
# Check if Qdrant is running
docker-compose ps qdrant

# Check logs
docker-compose logs qdrant

# Verify it's accessible
curl http://localhost:6333/health

# In Docker container
docker-compose exec eis curl http://qdrant:6333/health
```

### Dependencies Won't Install

```bash
# Make sure requirements.txt was compiled
ls requirements.txt

# If missing, compile:
./compile-requirements.sh

# Clear pip cache and retry
pip install --no-cache-dir -r requirements-dev.txt
```

### API Returns 500 Error

```bash
# Check logs for error details
docker-compose logs eis

# Check application logs
docker-compose exec eis tail -f /app/logs/app.log

# Enable debug mode in .env
DEBUG=true

# Restart server
docker-compose restart eis
```

## Next Steps

### 1. Understand the Architecture

```bash
# Read architecture document
cat ARCHITECTURE.md

# Read Docker setup
cat DOCKER.md

# Read ingestion pipeline docs
cat INGESTION.md
```

### 2. Run Example Ingestion

```bash
# Copy and modify an ingestion example
cp ingest_examples.py my_ingest.py

# Edit my_ingest.py with your repositories

# Run it
docker-compose exec eis python my_ingest.py
```

### 3. Try the API

```bash
# Interactive API docs
# Visit: http://localhost:8000/docs

# Or use curl to test
curl -X POST http://localhost:8000/api/knowledge/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "GIT_COMMIT",
    "repo": "https://github.com/example/repo.git",
    "content": "Example knowledge"
  }'
```

### 4. Implement Next Layer

Development phases after setup:

1. ✅ Architecture (done)
2. ✅ Ingestion (done)
3. ✅ Dependency & Docker setup (done)
4. ⏳ Chunking layer
5. ⏳ Embeddings layer
6. ⏳ Retrieval system
7. ⏳ LLM reasoning
8. ⏳ API endpoints

## Useful Commands Reference

### Docker Compose

```bash
# Lifecycle
docker-compose up              # Start services
docker-compose up -d           # Start in background
docker-compose down            # Stop services
docker-compose restart         # Restart services
docker-compose ps              # Show running services

# Logs and debugging
docker-compose logs -f         # Follow all logs
docker-compose logs eis        # Just app logs
docker-compose exec eis bash   # Access shell
docker-compose exec eis python # Python REPL

# Build
docker-compose build           # Build all images
docker-compose build --no-cache # Force rebuild
```

### Make Commands

```bash
make build          # Build Docker image
make up            # Start services
make down          # Stop services
make logs          # View logs
make shell         # Access container
make test          # Run tests
make format        # Format code
make lint          # Check code quality
make health        # Check service health
make help          # Show all commands
```

### Python in Docker

```bash
# Run Python script
docker-compose exec eis python my_script.py

# Python interactive shell
docker-compose exec eis python

# Run pytest
docker-compose exec eis pytest

# Install a package
docker-compose exec eis pip install package_name
```

## Configuration Reference

### Minimal .env for Development

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ENVIRONMENT=development
DEBUG=true
```

### Complete .env for Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

ANTHROPIC_API_KEY=sk-ant-xxxxx
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your-api-key

API_HOST=0.0.0.0
API_PORT=8000

API_SECRET_KEY=generate-random-string
JWT_SECRET=generate-random-string
```

## Database Persistence

### Qdrant Data

```bash
# Check volume
docker volume ls | grep qdrant

# Inspect volume
docker volume inspect eis_qdrant_storage

# Backup Qdrant data
docker-compose exec qdrant tar czf - /qdrant/storage > qdrant_backup.tar.gz

# Restore from backup
docker-compose exec -T qdrant tar xzf - < qdrant_backup.tar.gz
```

## Performance Tips

1. **Use local Python for development** (faster iteration than Docker)
2. **Use Docker Compose for testing** (matches production environment)
3. **Limit Qdrant memory** during development to prevent slowdowns
4. **Use `.dockerignore`** to speed up builds (already configured)
5. **Cache Docker layers** by ordering Dockerfile statements strategically (already done)

## Getting Help

```bash
# See all Make commands
make help

# See Docker Compose help
docker-compose help

# View logs for debugging
docker-compose logs -f eis

# Check .env configuration
grep -v '^#' .env | grep -v '^$'  # Show non-commented lines
```

## Common Tasks

### Add a New Python Package

```bash
# 1. Add to requirements.in or requirements-dev.in
echo "new-package>=1.0.0" >> requirements-dev.in

# 2. Recompile
./compile-requirements.sh

# 3. Rebuild Docker image
docker-compose build

# 4. Restart
docker-compose up
```

### Update All Dependencies

```bash
# Compile with upgrade flag
./compile-requirements.sh --upgrade

# Rebuild and restart
docker-compose build
docker-compose up
```

### Debug a Specific Function

```bash
# Access Docker shell
docker-compose exec eis bash

# Run Python with debugger
python -m pdb your_script.py

# Or use ipython (more interactive)
ipython
```

### Run a One-off Command in Docker

```bash
# Run Python script
docker-compose run --rm eis python my_script.py

# Run with volume mount for local changes
docker-compose run --rm -v $(pwd):/app eis python my_script.py
```

---

**Summary:**

1. ✅ Install prerequisites (Python 3.11+, Docker, Git)
2. ✅ Clone this project or navigate to it
3. ✅ `cp .env.example .env` and edit with API keys
4. ✅ `./compile-requirements.sh` to generate dependency locks
5. ✅ `docker-compose up` to start all services
6. ✅ Visit http://localhost:8000/health to verify
7. ✅ Visit http://localhost:8000/docs for interactive API docs

**For detailed information:**

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [INGESTION.md](INGESTION.md) - Data ingestion system
- [DOCKER.md](DOCKER.md) - Docker & containerization
- [README.md](README.md) - Project overview

Need help? Check the troubleshooting section above or review the relevant documentation file.
