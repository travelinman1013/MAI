"""Vector store infrastructure module.

Provides Qdrant-based vector storage functionality with:
- Async Qdrant client wrapper
- Collection management
- Vector operations (upsert, search, delete)
- Batch operations
- Metadata filtering
- Health checks
"""

from src.infrastructure.vector_store.qdrant_client import (
    QdrantVectorStore,
    QdrantClientError,
    get_qdrant_client,
    close_qdrant_client,
)

__all__ = [
    "QdrantVectorStore",
    "QdrantClientError",
    "get_qdrant_client",
    "close_qdrant_client",
]
