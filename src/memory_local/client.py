"""
Local Memory Client
===================
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .config import load_config, get_mem0_config, MemoryConfig

logger = logging.getLogger("memory_local")


class LocalMemoryClient:
    """
    Async-compatible client for local Mem0 memory operations.

    Wraps the sync mem0.Memory class to provide an async interface
    that matches the cloud AsyncMemoryClient API.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize the local memory client.

        Args:
            config: Optional MemoryConfig. Loads from defaults if not provided.
        """
        self._config = config or load_config()
        self._client = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """
        Lazy initialization of the Mem0 Memory client.

        WHY LAZY?
        - Delays import until actually needed
        - Allows graceful handling if mem0 not installed
        - Enables checking infrastructure before connecting
        """
        if self._initialized:
            return self._client is not None

        self._initialized = True

        try:
            from mem0 import Memory
            mem0_config = get_mem0_config(self._config)
            self._client = Memory.from_config(mem0_config)
            logger.info("Local memory client initialized (pgvector + Ollama)")
            return True
        except ImportError as e:
            logger.error(f"mem0 package not installed: {e}")
            logger.error("Install with: pip install 'mem0ai[postgres]'")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize local memory client: {e}")
            logger.error("Make sure Docker containers are running:")
            logger.error("  docker compose -f docker-compose.mem0.yml up -d")
            return False

    def _get_loop(self):
        """Get the current event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.get_event_loop()

    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add messages to memory.

        The Mem0 library will:
        1. Use LLM to extract facts from messages
        2. Generate embeddings for each fact
        3. Store in PostgreSQL with pgvector

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            user_id: Unique identifier for the user (scopes memories)
            metadata: Optional metadata to attach to memories

        Returns:
            Dict with created memory IDs, or empty dict on failure

        Example:
            await client.add(
                [{"role": "user", "content": "I prefer morning meetings"}],
                user_id="yash"
            )
        """
        if not self._ensure_initialized():
            return {}

        try:
            loop = self._get_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._client.add(
                    messages,
                    user_id=user_id,
                    metadata=metadata
                )
            )
            return result or {}
        except Exception as e:
            logger.warning(f"Memory add failed: {e}")
            return {}

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search memories by semantic similarity.

        The query is:
        1. Converted to embedding vector
        2. Compared against stored vectors using cosine similarity
        3. Top matches returned ranked by relevance

        Args:
            query: Natural language search query
            user_id: Filter to this user's memories
            limit: Maximum results to return

        Returns:
            Dict with "results" list of matching memories

        Example:
            results = await client.search("meeting preferences", user_id="yash")
            # results = {"results": [{"memory": "User prefers morning meetings", ...}]}
        """
        if not self._ensure_initialized():
            return {"results": []}

        try:
            loop = self._get_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._client.search(
                    query,
                    user_id=user_id,
                    limit=limit
                )
            )
            return result or {"results": []}
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return {"results": []}

    async def get_all(self, user_id: str) -> Dict[str, Any]:
        """
        Get all memories for a user.

        Args:
            user_id: Filter to this user's memories

        Returns:
            Dict with "results" list of all memories
        """
        if not self._ensure_initialized():
            return {"results": []}

        try:
            loop = self._get_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._client.get_all(user_id=user_id)
            )
            return result or {"results": []}
        except Exception as e:
            logger.warning(f"Memory get_all failed: {e}")
            return {"results": []}

    async def delete(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._ensure_initialized():
            return False

        try:
            loop = self._get_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete(memory_id)
            )
            return True
        except Exception as e:
            logger.warning(f"Memory delete failed: {e}")
            return False

    async def delete_all(self, user_id: str) -> bool:
        """
        Delete all memories for a user.

        Args:
            user_id: The user whose memories to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._ensure_initialized():
            return False

        try:
            loop = self._get_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_all(user_id=user_id)
            )
            return True
        except Exception as e:
            logger.warning(f"Memory delete_all failed: {e}")
            return False

    def close(self) -> None:
        """Explicitly close the underlying client to avoid shutdown errors."""
        if self._client is not None:
            try:
                vector_store = getattr(self._client, "vector_store", None)
                if vector_store is not None:
                    qs = getattr(vector_store, "client", None)
                    if qs is not None:
                        qs.close()
            except Exception:
                pass
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.close()

    def is_available(self) -> bool:
        """Check if the memory client is available and working."""
        return self._ensure_initialized()


def create_memory_client(config: Optional[MemoryConfig] = None) -> LocalMemoryClient:
    """
    Factory function to create a LocalMemoryClient.

    Args:
        config: Optional MemoryConfig

    Returns:
        Configured LocalMemoryClient instance
    """
    return LocalMemoryClient(config)
