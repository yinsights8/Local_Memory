# Configuration Data Classes


from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATA_DIR = Path.home() / ".memory_local"


@dataclass
class DatabaseConfig:
    """
    PostgreSQL + pgvector configuration.

    WHY POSTGRESQL?
    - Rock-solid reliability
    - pgvector extension adds vector similarity search
    - Single database for both vectors and history
    """
    host: str = "localhost"
    port: int = 5433  # Non-standard port to avoid conflicts
    user: str = field(default_factory=lambda: os.getenv("DATABASEUSER", ""))
    password: str = field(default_factory=lambda: os.getenv("DATABASEPASSWORD", ""))
    database: str = field(default_factory=lambda: os.getenv("DATABASE", ""))

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """
    Ollama configuration for LLM and embeddings.

    WHY OLLAMA?
    - Runs models locally (privacy)
    - Supports both LLM (fact extraction) and embeddings (vectors)
    - No API costs

    MODELS:
    - llm_model: Used to extract facts from conversations
      "I have a meeting tomorrow" → "User has meeting scheduled tomorrow"

    - embed_model: Converts text to vectors for similarity search
      "meeting tomorrow" → [0.12, -0.34, 0.56, ...]
    """
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    embed_provider: str = "ollama"
    embed_model: str = "nomic-embed-text"
    embed_dimensions: int = 768
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "ollama"))  # nomic-embed-text outputs 768 dimensions


@dataclass
class GraphConfig:
    """
    Neo4j graph store configuration (optional).

    WHY GRAPH MEMORY?
    - Tracks relationships between entities
    - Enables queries like "Who do I know at company X?"
    - Richer context than text similarity alone

    WHEN TO ENABLE:
    - Many interconnected entities (people, companies, projects)
    - Need relationship-based queries
    - Want entity extraction and linking

    WHEN TO SKIP:
    - Simple personal assistant
    - Limited entities
    - Want simpler infrastructure
    """
    enabled: bool = False  # Disabled by default - Ollama has compatibility issues with mem0 graph memory
    url: str = "bolt://localhost:7688"
    user: str = field(default_factory=lambda: os.getenv("GRAPHUSER", ""))
    password: str = field(default_factory=lambda: os.getenv("GRAPHPASSWORD", ""))


@dataclass
class LocalStorageConfig:
    """Qdrant + SQLite configuration (local mode, no Docker)."""
    data_dir: str = str(DEFAULT_DATA_DIR)

    @property
    def qdrant_path(self) -> str:
        return str(Path(self.data_dir) / "qdrant")

    @property
    def history_path(self) -> str:
        return str(Path(self.data_dir) / "history.db")


@dataclass
class MemoryConfig:
    """Complete configuration for local memory system."""
    backend: str = "docker"  # overridden by config.json
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    local_storage: LocalStorageConfig = field(default_factory=LocalStorageConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
