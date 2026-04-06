"""
Local Mem0 Memory Integration
=============================

This module provides a self-hosted alternative to Mem0 cloud API.

WHY LOCAL MEMORY?
-----------------
1. Privacy: Data never leaves your machine
2. Cost: No API fees, just compute resources
3. Latency: ~10-50ms local vs ~100-300ms cloud
4. Control: Full control over models and storage

ARCHITECTURE:
-------------
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Your Agent    │────►│  MemoryClient   │────►│   PostgreSQL    │
│                 │     │  (this module)  │     │   + pgvector    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                │
                                │ Uses
                                ▼
                       ┌─────────────────┐
                       │     Ollama      │
                       │ (LLM + Embed)   │
                       └─────────────────┘

QUICK START:
------------
1. Start infrastructure:
   docker compose -f docker-compose.mem0.yml up -d

2. Pull required Ollama model:
   ollama pull nomic-embed-text

3. Use in your code:
   from memory_local import LocalMemoryClient

   client = LocalMemoryClient()
   await client.add([{"role": "user", "content": "Hello"}], user_id="yash")
   results = await client.search("greeting", user_id="yash")

INTEGRATION:
------------
See README.md for how to integrate with existing memory systems.
"""

from .client import LocalMemoryClient, create_memory_client
from .config import load_config, get_mem0_config, MemoryConfig

__all__ = [
    "LocalMemoryClient",
    "create_memory_client",
    "load_config",
    "get_mem0_config",
    "MemoryConfig",
]
