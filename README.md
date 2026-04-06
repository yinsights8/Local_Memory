# Local Mem0 Memory Integration

Self-hosted memory system using PostgreSQL + pgvector + Ollama.

## Why Local Memory?

| Aspect | Cloud (api.mem0.ai) | Local (this package) |
|--------|---------------------|----------------------|
| **Privacy** | Data sent to Mem0 servers | Data stays 
| **Cost** | Per API call | Just compute |
| **Control** | Mem0 manages models | You choose models |

## Project Structure

```
memory_local/
├── pyproject.toml           # Package configuration
├── README.md
├── src/
│   └── memory_local/        # Python package
│       ├── __init__.py
│       ├── client.py        # LocalMemoryClient
│       ├── config.py        # Configuration management
│       └── setup.py         # Health check CLI
└── infra/                   # Infrastructure (separate)
    ├── docker-compose.mem0.yml
    ├── config.json
    └── config.example.json
```

## Quick Start

### Step 1: Install the Package

```bash
# Install with uv
uv pip install -e ".[all]"

# Or with pip
pip install -e ".[all]"
```

### Step 2: Start Infrastructure

```bash
cd infra
docker compose -f docker-compose.mem0.yml up -d
```

This starts:
- **PostgreSQL** (port 5433) - Vector storage with pgvector
- **Neo4j** (port 7688) - Optional graph memory

### Step 3: Pull Ollama Models

```bash
# Embedding model (required)
ollama pull nomic-embed-text

# LLM for fact extraction (required)
ollama pull llama3.2:3b
```

### Step 4: Run Health Check

```bash
memory-local check
```

Expected output:
```
============================================================
Local Memory Health Check
============================================================

[OK]       PostgreSQL: PostgreSQL + pgvector OK
[OK]       Ollama: Ollama OK: LLM (llama3.2:3b), Embedder (nomic-embed-text)
[OK]       Neo4j: Neo4j OK
[OK]       Mem0 Package: mem0 package OK

Running memory operations test...
[OK]       Memory Test: Memory operations OK (add, search, delete tested)

============================================================
All checks passed! Local memory is ready.
============================================================
```

## Usage

### Basic Usage

```python
from memory_local import LocalMemoryClient

# Create client
client = LocalMemoryClient()

# Add memory
await client.add(
    [{"role": "user", "content": "I prefer morning meetings"}],
    user_id="yash"
)

# Search memories
results = await client.search("meeting preferences", user_id="yash")
for memory in results.get("results", []):
    print(memory["memory"])

# Get all memories
all_memories = await client.get_all(user_id="yash")

# Delete specific memory
await client.delete(memory_id="...")

# Delete all user memories
await client.delete_all(user_id="yash")
```

### CLI Commands

```bash
# Health check
memory-local check

# Show configuration
memory-local config

# Interactive test
memory-local test
```

## Configuration

The package uses sensible defaults for local development. No config file needed!

### Default Values

| Setting | Default |
|---------|---------|
| PostgreSQL Host | localhost |
| PostgreSQL Port | 5433 |
| Ollama URL | http://localhost:11434 |
| LLM Model | llama3.2:3b |
| Embed Model | nomic-embed-text |
| Neo4j URL | bolt://localhost:7688 |

### Environment Variables (override defaults)

```bash
# Database
MEM0_DB_HOST=localhost
MEM0_DB_PORT=5433
MEM0_DB_USER=mem0
MEM0_DB_PASSWORD=mem0secret
MEM0_DB_NAME=mem0

# Ollama
MEM0_OLLAMA_URL=http://localhost:11434
MEM0_LLM_MODEL=llama3.2:3b
MEM0_EMBED_MODEL=nomic-embed-text
MEM0_EMBED_DIMS=768

# Graph (optional)
MEM0_GRAPH_ENABLED=true
MEM0_NEO4J_URL=bolt://localhost:7688
MEM0_NEO4J_USER=neo4j
MEM0_NEO4J_PASSWORD=mem0graph
```

### Config File (optional)

Set `MEM0_LOCAL_CONFIG` env var to point to a JSON config file:

```bash
export MEM0_LOCAL_CONFIG=/path/to/config.json
```

See `infra/config.example.json` for the format.

## How Memory Storage Works

### Adding a Memory

```
User says: "I have a meeting with John tomorrow at 3pm"
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Fact Extraction (Ollama LLM)                           │
│  Input: "I have a meeting with John tomorrow at 3pm"            │
│  Output: ["User has meeting with John tomorrow at 3pm"]         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Embedding Generation (Ollama nomic-embed-text)         │
│  Input: "User has meeting with John tomorrow at 3pm"            │
│  Output: [0.12, -0.34, 0.56, 0.78, ...] (768 dimensions)        │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Storage (PostgreSQL + pgvector)                        │
│  INSERT INTO memories (user_id, memory, embedding)              │
│  VALUES ('yash', 'User has meeting...', '[0.12, -0.34, ...]')   │
└─────────────────────────────────────────────────────────────────┘
```

### Searching Memories

```
User asks: "When is my meeting?"
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Embed Query                                            │
│  Input: "When is my meeting?"                                   │
│  Output: [0.15, -0.30, 0.52, ...] (768 dimensions)              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Vector Similarity Search (pgvector)                    │
│  SELECT memory, embedding <=> query_embedding AS distance       │
│  FROM memories WHERE user_id = 'yash'                           │
│  ORDER BY distance LIMIT 5;                                     │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Return Results                                         │
│  [{"memory": "User has meeting with John tomorrow at 3pm",      │
│    "score": 0.92}]                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### PostgreSQL Connection Failed

```bash
# Check if container is running
docker ps | grep mem0-postgres

# Check logs
docker logs mem0-postgres

# Restart container
cd infra && docker compose -f docker-compose.mem0.yml restart mem0-postgres
```

### Ollama Models Not Found

```bash
# List installed models
ollama list

# Pull missing models
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

### Memory Operations Failing

```bash
# Run full health check
memory-local check

# Run interactive test
memory-local test
```
