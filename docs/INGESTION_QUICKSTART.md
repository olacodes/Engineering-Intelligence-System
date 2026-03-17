"""
INGESTION_QUICKSTART.md - Quick Reference Guide

A concise guide to using the EIS ingestion pipeline.
"""

# EIS Ingestion Pipeline - Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

## Quick Examples

### 1. Ingest a Git Repository

```python
from ingestion import RepoLoader

loader = RepoLoader(
    repo_url="https://github.com/olacodes/prog-image",
    local_path="./temp/react",
    repo_name="facebook/react",
    branch="main",
    max_files=1000,
)

items = loader.load()
print(f"Loaded {len(items)} items")

# Access item properties
for item in items[:5]:
    print(f"- {item.file_path} ({item.metadata.language})")
```

### 2. Ingest GitHub Pull Requests

```python
import os
from ingestion import PRLoader

# Set GitHub token
os.environ["GITHUB_TOKEN"] = "ghp_xxx"

loader = PRLoader(
    repo_owner="facebook",
    repo_name="react",
    github_token=os.environ["GITHUB_TOKEN"],
    max_prs=50,
    status="closed",
    include_comments=True,
)

items = loader.load()
print(f"Loaded {len(items)} items (PRs + comments)")

# Filter by type
prs = [i for i in items if i.source_type.value == "pull_request"]
comments = [i for i in items if i.source_type.value == "comment"]
print(f"  PRs: {len(prs)}, Comments: {len(comments)}")
```

### 3. Ingest Markdown Documentation

```python
from ingestion import DocLoader

loader = DocLoader(
    doc_dir="./docs",
    repo_name="my-project",
    split_on_headers=True,    # Split at header boundaries
    min_section_length=200,   # Minimum chars per section
)

items = loader.load()
print(f"Loaded {len(items)} documentation items")

# Access content
for item in items:
    print(f"- {item.file_path}")
    print(f"  Title: {item.metadata.custom_fields.get('title', 'N/A')}")
    print(f"  Lines: {item.metadata.custom_fields.get('lines', 0)}")
```

### 4. Orchestrate Multiple Sources

```python
from ingestion import IngestionService, RepoLoader, PRLoader, DocLoader

# Create loaders
repo_loader = RepoLoader(
    repo_url="https://github.com/torvalds/linux.git",
    local_path="./temp/linux",
    repo_name="torvalds/linux",
    max_files=100,
)

doc_loader = DocLoader(
    doc_dir="./docs",
    repo_name="my-project",
)

# Orchestrate
service = IngestionService(
    loaders=[repo_loader, doc_loader],
    deduplicate=True,
)

items = service.run()
print(f"Total items ingested: {len(items)}")

# Get statistics
stats = service.get_statistics()
print(f"Duration: {stats['duration_seconds']:.2f}s")
print(f"Items/sec: {stats['items_per_second']:.2f}")
print(f"By type: {stats['source_type_distribution']}")
```

### 5. Filter and Export Results

```python
# Filter by source type
code_items = service.get_items_by_source_type("code_file")
doc_items = service.get_items_by_source_type("documentation")
pr_items = service.get_items_by_source_type("pull_request")

print(f"Code: {len(code_items)}, Docs: {len(doc_items)}, PRs: {len(pr_items)}")

# Filter by repository
react_items = service.get_items_by_repo("facebook/react")
print(f"React items: {len(react_items)}")

# Export
json_str = service.export_items(format="json")
service.save_to_file("./ingested.json")
```

## RepoLoader Options

```python
loader = RepoLoader(
    repo_url="...",                # HTTPS clone URL
    local_path="./temp",           # Where to clone
    repo_name="owner/repo",        # Identifier
    branch="main",                 # Branch to clone (default: main)
    max_files=None,                # Max files to process (default: unlimited)
)
```

**Filtering:**

- Allowed extensions: `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.cpp`, `.c`, `.rb`, `.php`, `.sql`, `.json`, `.yaml`, `.sh`, `.dockerfile`
- Max file size: 1 MB
- Excluded dirs: `node_modules`, `.git`, `venv`, `dist`, `build`, `target`, etc.
- Skipped files: binaries (`.exe`, `.dll`, `.pyc`, `.jar`)

## PRLoader Options

```python
loader = PRLoader(
    repo_owner="facebook",         # GitHub owner
    repo_name="react",             # GitHub repo name
    github_token="ghp_xxx",        # Access token (optional)
    max_prs=100,                   # Max PRs to fetch (default: 100)
    status="all",                  # Filter: "open", "closed", "all"
    include_comments=True,         # Extract PR comments (default: True)
)
```

**Note:** Set `GITHUB_TOKEN` env var for higher API rate limits (5000 req/hr vs 60 req/hr).

## DocLoader Options

```python
loader = DocLoader(
    doc_dir="./docs",              # Documentation directory
    repo_name="project",           # Project identifier
    split_on_headers=False,        # Split at headers (default: False)
    min_section_length=100,        # Min chars per section when splitting
)
```

**Supported formats:** `.md`, `.markdown`, `.txt`, `.rst`

## IngestionService Options

```python
service = IngestionService(
    loaders=[loader1, loader2, ...],  # List of loaders
    deduplicate=False,                # Remove duplicates (default: False)
)
```

**Methods:**

- `run()` - Execute pipeline, return items
- `get_statistics()` - Get ingestion metrics
- `get_items_by_source_type(type)` - Filter items
- `get_items_by_repo(repo)` - Filter by repo
- `export_items(format)` - Export as JSON
- `save_to_file(path)` - Save to file

## KnowledgeItem Structure

```python
from models import KnowledgeItem

item = KnowledgeItem(
    id="uuid4",                    # Auto-generated
    source_type="code_file",       # Enum: code_file, pull_request, documentation, etc.
    repo="facebook/react",         # Repository identifier
    file_path="src/index.js",      # Path within repo
    content="...",                 # Full content
    metadata=KnowledgeMetadata(
        language="js",             # Programming language
        author="Dan Abramov",       # Author/contributor
        source_url="...",          # External URL
        created_at=datetime(...),  # Timestamp
        updated_at=datetime(...),  # Last update
        tags=["core", "exports"],  # Semantic tags
        custom_fields={            # Extensible metadata
            "lines": 42,
            "pr_number": 123,
        },
    ),
)

# Useful methods
search_text = item.to_search_text()  # Combined searchable text
```

## Common Patterns

### Pattern: Large Repository with File Limit

```python
loader = RepoLoader(
    repo_url="https://github.com/torvalds/linux.git",
    local_path="./temp/linux",
    repo_name="torvalds/linux",
    max_files=500,  # Process only 500 files
)
items = loader.load()  # Fast iteration for testing
```

### Pattern: Multiple Repositories

```python
service = IngestionService(
    loaders=[
        RepoLoader("https://github.com/user/repo1.git", "./temp/1", "user/repo1"),
        RepoLoader("https://github.com/user/repo2.git", "./temp/2", "user/repo2"),
        RepoLoader("https://github.com/user/repo3.git", "./temp/3", "user/repo3"),
    ]
)
items = service.run()
```

### Pattern: Documentation-First Approach

```python
service = IngestionService(
    loaders=[
        DocLoader("./docs", "my-project", split_on_headers=True),
        DocLoader("./guides", "my-project", split_on_headers=True),
        DocLoader("./api", "my-project", split_on_headers=False),
    ]
)
items = service.run()
```

### Pattern: PR Analysis

```python
loader = PRLoader(
    repo_owner="facebook",
    repo_name="react",
    github_token=token,
    max_prs=200,
    status="closed",  # Only merged PRs
    include_comments=True,
)
items = loader.load()

# Analyze PR patterns
prs = service.get_items_by_source_type("pull_request")
print(f"Total PRs: {len(prs)}")
print(f"Total PR authors: {len(set(i.metadata.author for i in prs))}")
```

### Pattern: Export and Batch Processing

```python
service = IngestionService([...])
items = service.run()

# Save for later processing
service.save_to_file("./checkpoint.json")

# Or export for analysis
import json
json_data = service.export_items("json")
data = json.loads(json_data)
print(f"First item: {data[0]}")
```

## Troubleshooting

### Issue: Git Clone Failed

```
Error: RuntimeError: Git command failed: fatal: repository not found
```

**Solution:** Check repository URL

```python
loader = RepoLoader(
    repo_url="https://github.com/facebook/react.git",  # Use .git suffix
    ...
)
```

### Issue: GitHub Rate Limited

```
Error: 403 Forbidden (API rate limit exceeded)
```

**Solution:** Use authentication token

```bash
export GITHUB_TOKEN=ghp_xxx
```

Or pass directly:

```python
loader = PRLoader(
    github_token="ghp_xxx",
    ...
)
```

### Issue: File Not Found

```
Error: FileNotFoundError: Documentation directory not found
```

**Solution:** Provide full path

```python
loader = DocLoader(
    doc_dir="./docs",  # Current directory relative
    ...
)
# Or:
from pathlib import Path
doc_dir = Path(__file__).parent / "docs"
loader = DocLoader(doc_dir=str(doc_dir), ...)
```

### Issue: Memory Usage High

**Solution:** Reduce file limits

```python
loader = RepoLoader(
    max_files=100,  # Process fewer files
    ...
)
```

Or use deduplication to reduce final result:

```python
service = IngestionService(
    [...],
    deduplicate=True,
)
```

## Performance Tips

1. **Use shallow clones** - Automatic with RepoLoader
2. **Limit max_files** - Process in batches for large repos
3. **Use deduplication** - When ingesting from multiple sources
4. **Filter by extension** - Automatic, not changeable
5. **Run in parallel** - Create separate service instances for different repos

### Example: Parallel Ingestion

```python
import concurrent.futures

repos = [
    "facebook/react",
    "facebook/jest",
    "facebook/flipper",
]

def ingest_repo(repo_name):
    owner, repo = repo_name.split("/")
    loader = RepoLoader(
        repo_url=f"https://github.com/{repo_name}.git",
        local_path=f"./temp/{repo}",
        repo_name=repo_name,
        max_files=200,
    )
    return loader.load()

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    all_items = []
    for items in executor.map(ingest_repo, repos):
        all_items.extend(items)

print(f"Ingested {len(all_items)} items from {len(repos)} repos")
```

## Next Steps

After ingestion, items flow to:

1. **Chunking** - Further split if needed

   ```python
   from chunking import Chunker
   chunker = Chunker(chunk_size=512)
   chunks = chunker.chunk(items)
   ```

2. **Embeddings** - Generate vectors

   ```python
   from embeddings import EmbeddingService
   svc = EmbeddingService()
   embeddings = svc.embed(chunks)
   ```

3. **Vector Store** - Store in Qdrant
   ```python
   from vector_store import VectorStore
   store = VectorStore()
   store.index(chunks, embeddings)
   ```

## Running Examples

```bash
# Run all examples
python ingest_examples.py

# Run specific example (requires modifying file)
python -c "from ingest_examples import example_1_basic_repo_ingestion; example_1_basic_repo_ingestion()"
```

## API Reference

See [INGESTION.md](INGESTION.md) for complete documentation.

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture decisions
- [README.md](README.md) - Project overview
- [models/knowledge_models.py](models/knowledge_models.py) - Domain models
