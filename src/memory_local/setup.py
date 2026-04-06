"""
Setup and Health Check Utilities
=================================

Provides tools to verify infrastructure and test the local memory system.

USAGE:
------
    # Run health check
    python -m memory_local.setup check

    # Interactive test
    python -m memory_local.setup test

    # Show configuration
    python -m memory_local.setup config
"""

import asyncio
import sys
from typing import Tuple

from .config import load_config, MemoryConfig


def check_postgres(config: MemoryConfig) -> Tuple[bool, str]:
    """
    Check PostgreSQL connection.

    WHY CHECK?
    - PostgreSQL must be running for vector storage
    - pgvector extension must be available
    """
    try:
        import psycopg2
        conn = psycopg2.connect(config.database.connection_string)
        cur = conn.cursor()

        # Check basic connection
        cur.execute("SELECT 1")

        # Check pgvector extension
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        has_vector = cur.fetchone() is not None

        conn.close()

        if has_vector:
            return True, "PostgreSQL + pgvector OK"
        else:
            return True, "PostgreSQL OK (pgvector extension will be created on first use)"

    except ImportError:
        return False, "psycopg2 not installed. Run: pip install psycopg2-binary"
    except Exception as e:
        return False, f"PostgreSQL connection failed: {e}"


def check_ollama(config: MemoryConfig) -> Tuple[bool, str]:
    """
    Check Ollama availability and required models.

    WHY CHECK?
    - Ollama provides LLM for fact extraction
    - Ollama provides embedding model for vectors
    - Both models must be pulled
    """
    try:
        import requests
        r = requests.get(f"{config.llm.base_url}/api/tags", timeout=5)
        r.raise_for_status()

        models = [m.get("name", "") for m in r.json().get("models", [])]

        # Check for required models
        has_llm = any(config.llm.llm_model.split(":")[0] in m for m in models)
        has_embed = any(config.llm.embed_model.split(":")[0] in m for m in models)

        messages = []
        if has_llm:
            messages.append(f"LLM ({config.llm.llm_model})")
        else:
            messages.append(f"LLM ({config.llm.llm_model}) - NOT FOUND")

        if has_embed:
            messages.append(f"Embedder ({config.llm.embed_model})")
        else:
            messages.append(f"Embedder ({config.llm.embed_model}) - NOT FOUND")

        if has_llm and has_embed:
            return True, f"Ollama OK: {', '.join(messages)}"
        else:
            missing = []
            if not has_llm:
                missing.append(f"ollama pull {config.llm.llm_model}")
            if not has_embed:
                missing.append(f"ollama pull {config.llm.embed_model}")
            return False, f"Ollama missing models. Run:\n  " + "\n  ".join(missing)

    except ImportError:
        return False, "requests not installed. Run: pip install requests"
    except Exception as e:
        return False, f"Ollama connection failed: {e}"


def check_neo4j(config: MemoryConfig) -> Tuple[bool, str]:
    """
    Check Neo4j connection (if graph memory enabled).

    WHY CHECK?
    - Neo4j stores entity relationships
    - Only needed if graph memory is enabled
    """
    if not config.graph.enabled:
        return True, "Neo4j (graph memory disabled - skipped)"

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            config.graph.url,
            auth=(config.graph.user, config.graph.password)
        )
        driver.verify_connectivity()
        driver.close()
        return True, "Neo4j OK"

    except ImportError:
        return False, "neo4j driver not installed. Run: pip install neo4j"
    except Exception as e:
        return False, f"Neo4j connection failed: {e}"


def check_mem0() -> Tuple[bool, str]:
    """
    Check mem0 package installation.

    WHY CHECK?
    - mem0ai package provides Memory class
    - Need postgres extras for pgvector support
    """
    try:
        from mem0 import Memory
        return True, "mem0 package OK"
    except ImportError as e:
        return False, f"mem0 not installed: {e}\nRun: pip install 'mem0ai[postgres]'"


async def test_memory_operations(config: MemoryConfig) -> Tuple[bool, str]:
    """
    Test actual memory operations (add, search, delete).

    WHY TEST?
    - Verifies full integration works end-to-end
    - Catches configuration issues
    """
    try:
        from .client import LocalMemoryClient

        client = LocalMemoryClient(config)

        # Test add
        result = await client.add(
            [{"role": "user", "content": "My name is Yash and I am an AI Engineer"}],
            user_id="test_user"
        )

        if not result:
            return False, "Memory add returned empty result"

        # Test search
        search_result = await client.search("test memory", user_id="test_user") #__health_check__

        if not search_result.get("results"):
            return False, "Memory search returned no results"

        # Cleanup
        await client.delete_all(user_id="test_user")

        return True, "Memory operations OK (add, search, delete tested)"

    except Exception as e:
        return False, f"Memory operations failed: {e}"


def check_qdrant_local(config: MemoryConfig) -> Tuple[bool, str]:
    """Check Qdrant embedded (local mode, no server needed)."""
    try:
        from qdrant_client import QdrantClient
        from pathlib import Path
        Path(config.local_storage.qdrant_path).mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=config.local_storage.qdrant_path)
        client.get_collections()
        return True, f"Qdrant OK (path: {config.local_storage.qdrant_path})"
    except ImportError:
        return False, "qdrant-client not installed. Run: uv pip install qdrant-client"
    except Exception as e:
        return False, f"Qdrant check failed: {e}"


def run_health_check(config: MemoryConfig = None) -> bool:
    """
    Run all health checks and print results.

    Returns:
        True if all checks pass, False otherwise
    """
    if config is None:
        config = load_config()

    print("=" * 60)
    print("Local Memory Health Check")
    print("=" * 60)
    print()

    if config.backend == "local":
        checks = [
            ("Qdrant (local)", lambda: check_qdrant_local(config)),
            ("Ollama", lambda: check_ollama(config)),
            ("Mem0 Package", lambda: check_mem0()),
        ]
    else:
        checks = [
            ("PostgreSQL", lambda: check_postgres(config)),
            ("Ollama", lambda: check_ollama(config)),
            ("Neo4j", lambda: check_neo4j(config)),
            ("Mem0 Package", lambda: check_mem0()),
        ]

    all_passed = True

    for name, check_fn in checks:
        try:
            passed, message = check_fn()
            status = "[OK]" if passed else "[FAILED]"
            print(f"{status:10} {name}: {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"{'[ERROR]':10} {name}: {e}")
            all_passed = False

    print()

    # Run async memory test if basic checks pass
    if all_passed:
        print("Running memory operations test...")
        try:
            passed, message = asyncio.run(test_memory_operations(config))
            status = "[OK]" if passed else "[FAILED]"
            print(f"{status:10} Memory Test: {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"{'[ERROR]':10} Memory Test: {e}")
            all_passed = False

    print()
    print("=" * 60)
    if all_passed:
        print("All checks passed! Local memory is ready.")
    else:
        print("Some checks failed. Please fix the issues above.")
        print()
        print("Quick Start:")
        print("  1. Start containers: docker compose -f docker-compose.mem0.yml up -d")
        print("  2. Pull models: ollama pull nomic-embed-text && ollama pull llama3.1:8b")
        print("  3. Install deps: pip install 'mem0ai[postgres]' psycopg2-binary")
    print("=" * 60)

    return all_passed


def show_config(config: MemoryConfig = None) -> None:
    """Print current configuration."""
    if config is None:
        config = load_config()

    print("=" * 60)
    print("Local Memory Configuration")
    print("=" * 60)
    print()
    print("Database (PostgreSQL + pgvector):")
    print(f"  Host: {config.database.host}")
    print(f"  Port: {config.database.port}")
    print(f"  User: {config.database.user}")
    print(f"  Database: {config.database.database}")
    print(f"  Connection: {config.database.connection_string}")
    print()
    print("Ollama (LLM + Embeddings):")
    print(f"  URL: {config.llm.base_url}")
    print(f"  LLM Model: {config.llm.llm_model}")
    print(f"  Embed Model: {config.llm.embed_model}")
    print(f"  Embed Dimensions: {config.llm.embed_dimensions}")
    print()
    print("Graph Store (Neo4j):")
    print(f"  Enabled: {config.graph.enabled}")
    if config.graph.enabled:
        print(f"  URL: {config.graph.url}")
        print(f"  User: {config.graph.user}")
    print("=" * 60)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Local Memory Setup Utilities")
    parser.add_argument(
        "command",
        choices=["check", "config", "test"],
        help="Command to run: check (health check), config (show config), test (interactive test)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file",
        default=None
    )

    args = parser.parse_args()

    config = load_config(args.config) if args.config else load_config()

    if args.command == "check":
        success = run_health_check(config)
        sys.exit(0 if success else 1)

    elif args.command == "config":
        show_config(config)

    elif args.command == "test":
        print("Running interactive memory test...")
        print()

        async def interactive_test():
            from .client import LocalMemoryClient
            client = LocalMemoryClient(config)

            # Add test memory
            print("Adding test memory: 'User likes coffee in the morning'")
            await client.add(
                [{"role": "user", "content": "I like coffee in the morning"}],
                user_id="test_user"
            )
            print("  -> Added successfully")
            print()

            # Search
            print("Searching for: 'morning preferences'")
            results = await client.search("morning preferences", user_id="test_user")
            print(f"  -> Found {len(results.get('results', []))} results:")
            for r in results.get("results", []):
                print(f"     - {r.get('memory', r.get('text', 'N/A'))}")
            print()

            # Cleanup
            print("Cleaning up test data...")
            await client.delete_all(user_id="test_user")
            print("  -> Cleaned up")

        asyncio.run(interactive_test())


if __name__ == "__main__":
    main()
