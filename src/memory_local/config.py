"""
Configuration Management for Local Mem0
========================================

Settings come from two sources:
  - config.json  : all non-credential settings (backend, paths, models, ports)
  - .env         : credentials only (DATABASEUSER, DATABASEPASSWORD, DATABASE, GRAPHUSER, GRAPHPASSWORD)

Set MEM0_LOCAL_CONFIG env var to point to a custom config file path.
Default config is looked up at infra/config.json relative to the project.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from .dataclassconfig import (
    DatabaseConfig,
    LocalStorageConfig,
    LLMConfig,
    GraphConfig,
    MemoryConfig,
)

load_dotenv()

logger = logging.getLogger("memory_local")

DEFAULT_CONFIG_PATH = os.environ.get(
    "MEM0_LOCAL_CONFIG",
    str(Path(__file__).parents[2] / "infra" / "config.json")
)


def load_config(config_path: Optional[str] = None) -> MemoryConfig:
    """
    Load configuration from config.json + credentials from .env.

    Priority:
    1. config.json  (settings)
    2. .env         (credentials only)
    3. Dataclass defaults (fallback)
    """
    config = MemoryConfig()

    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        logger.warning(f"Config file not found at {path}, using defaults")
        return config

    try:
        with open(path, "r") as f:
            data = json.load(f)

        if "backend" in data:
            config.backend = data["backend"]

        if "database" in data:
            db = data["database"]
            config.database = DatabaseConfig(
                host=db.get("host", config.database.host),
                port=db.get("port", config.database.port),
            )

        if "local_storage" in data:
            ls = data["local_storage"]
            data_dir = ls.get("data_dir", config.local_storage.data_dir)
            config.local_storage = LocalStorageConfig(
                data_dir=str(Path(data_dir).expanduser())
            )

        if "llm" in data:
            llm = data["llm"]
            config.llm = LLMConfig(
                provider=llm.get("provider", config.llm.provider),
                base_url=llm.get("base_url", config.llm.base_url),
                llm_model=llm.get("llm_model", config.llm.llm_model),
                embed_provider=llm.get("embed_provider", config.llm.embed_provider),
                embed_model=llm.get("embed_model", config.llm.embed_model),
                embed_dimensions=llm.get("embed_dimensions", config.llm.embed_dimensions),
            )

        if "graph" in data:
            graph = data["graph"]
            config.graph = GraphConfig(
                enabled=graph.get("enabled", config.graph.enabled),
                url=graph.get("url", config.graph.url),
            )

        logger.info(f"Loaded config from {path}")

    except Exception as e:
        logger.warning(f"Failed to load config from {path}: {e}")

    return config


def get_mem0_config(config: Optional[MemoryConfig] = None) -> Dict[str, Any]:
    """
    Convert MemoryConfig to Mem0-compatible configuration dict.

    backend=local  → Qdrant + SQLite  (no Docker)
    backend=docker → pgvector + PostgreSQL  (requires Docker)
    """
    if config is None:
        config = load_config()

    def _provider_config(provider: str, model: str, base_url: str) -> dict:
        if provider == "openai":
            return {
                "model": model,
                "openai_base_url": f"{base_url}/v1",
                "api_key": config.llm.api_key,
            }
        return {
            "model": model,
            "ollama_base_url": base_url,
        }

    mem0_config = {
        "llm": {
            "provider": config.llm.provider,
            "config": _provider_config(config.llm.provider, config.llm.llm_model, config.llm.base_url),
        },
        "embedder": {
            "provider": config.llm.embed_provider,
            "config": _provider_config(config.llm.embed_provider, config.llm.embed_model, config.llm.base_url),
        },
    }

    if config.backend == "local":
        Path(config.local_storage.qdrant_path).mkdir(parents=True, exist_ok=True)
        mem0_config["vector_store"] = {
            "provider": "qdrant",
            "config": {
                "collection_name": "mem0",
                "path": config.local_storage.qdrant_path,
                "embedding_model_dims": config.llm.embed_dimensions,
                "on_disk": True,
            }
        }
        mem0_config["history_db"] = {
            "provider": "sqlite",
            "config": {
                "path": config.local_storage.history_path,
            }
        }
        logger.info(f"Using local backend (Qdrant + SQLite) at {config.local_storage.data_dir}")

    else:
        mem0_config["vector_store"] = {
            "provider": "pgvector",
            "config": {
                "connection_string": config.database.connection_string,
                "embedding_model_dims": config.llm.embed_dimensions,
            }
        }
        mem0_config["history_db"] = {
            "provider": "postgresql",
            "config": {
                "connection_string": config.database.connection_string,
            }
        }
        logger.info("Using docker backend (pgvector + PostgreSQL)")

        if config.graph.enabled:
            mem0_config["graph_store"] = {
                "provider": "neo4j",
                "config": {
                    "url": config.graph.url,
                    "username": config.graph.user,
                    "password": config.graph.password,
                }
            }

    return mem0_config
