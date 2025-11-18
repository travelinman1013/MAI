"""Async Qdrant vector store client with collection and vector management.

This module provides a production-ready Qdrant client with:
- Async operations using qdrant_client.AsyncQdrantClient
- Collection management (create, delete, get info)
- Vector operations (upsert, search, delete, batch operations)
- Metadata filtering support
- Configurable distance metrics (cosine, dot product, euclidean)
- Health check functionality
- Error handling and retry logic
"""

import uuid
from typing import Any, Optional, Union

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchParams,
    VectorParams,
)

from src.core.utils.config import QdrantSettings, get_settings
from src.core.utils.exceptions import MAIException
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class QdrantClientError(MAIException):
    """Qdrant client operation error."""

    def __init__(self, message: str, operation: str, **kwargs):
        super().__init__(
            error_code="QDRANT_ERROR",
            message=message,
            details={"operation": operation, **kwargs},
            retryable=True,
        )


class QdrantVectorStore:
    """Async Qdrant vector store client.

    Features:
    - Collection management (create, delete, info)
    - Vector upsert and batch upsert operations
    - Semantic search with configurable similarity metrics
    - Metadata filtering for precise searches
    - Health checks for monitoring
    - Configurable vector dimensions and distance metrics

    Example:
        ```python
        from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore
        from src.core.utils.config import get_settings

        settings = get_settings()
        qdrant = QdrantVectorStore(settings.qdrant)

        await qdrant.connect()

        # Create collection
        await qdrant.create_collection("memories", vector_size=1536)

        # Upsert vectors
        await qdrant.upsert(
            collection_name="memories",
            vectors=[embedding1, embedding2],
            payloads=[{"text": "hello"}, {"text": "world"}],
            ids=["id1", "id2"]
        )

        # Search
        results = await qdrant.search(
            collection_name="memories",
            query_vector=query_embedding,
            limit=5,
            filter_metadata={"user_id": "123"}
        )

        await qdrant.disconnect()
        ```
    """

    def __init__(self, settings: Optional[QdrantSettings] = None):
        """Initialize Qdrant vector store client.

        Args:
            settings: Qdrant configuration settings. If None, uses global settings.
        """
        self.settings = settings or get_settings().qdrant
        self.client: Optional[AsyncQdrantClient] = None
        self._connected = False

        logger.info(
            "Qdrant client initialized",
            url=self.settings.url,
            collection=self.settings.collection_name,
            vector_size=self.settings.vector_size,
            distance_metric=self.settings.distance_metric,
        )

    async def connect(self) -> None:
        """Establish connection to Qdrant server.

        Raises:
            QdrantClientError: If connection fails.
        """
        if self._connected:
            logger.warning("Qdrant client already connected")
            return

        try:
            # Create async Qdrant client
            self.client = AsyncQdrantClient(
                url=self.settings.url, api_key=self.settings.api_key, timeout=30
            )

            # Test connection by getting collections
            await self.client.get_collections()

            self._connected = True
            logger.info("Qdrant client connected successfully")

        except Exception as e:
            error_msg = f"Failed to connect to Qdrant: {e}"
            logger.error(error_msg, error=str(e))
            raise QdrantClientError(error_msg, operation="connect", error=str(e))

    async def disconnect(self) -> None:
        """Close Qdrant connection and cleanup resources."""
        if not self._connected:
            logger.warning("Qdrant client not connected")
            return

        try:
            if self.client:
                await self.client.close()

            self._connected = False
            logger.info("Qdrant client disconnected successfully")

        except Exception as e:
            logger.error("Error disconnecting Qdrant client", error=str(e))
            raise QdrantClientError(
                f"Failed to disconnect from Qdrant: {e}", operation="disconnect", error=str(e)
            )

    def _get_distance_metric(self, metric: Optional[str] = None) -> Distance:
        """Convert distance metric string to Qdrant Distance enum.

        Args:
            metric: Distance metric name (Cosine, Dot, Euclidean). If None, uses default.

        Returns:
            Qdrant Distance enum value
        """
        metric_name = metric or self.settings.distance_metric
        metric_map = {
            "Cosine": Distance.COSINE,
            "Dot": Distance.DOT,
            "Euclidean": Distance.EUCLID,
        }

        return metric_map.get(metric_name, Distance.COSINE)

    # ===== Collection Management =====

    async def create_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance_metric: Optional[str] = None,
        recreate: bool = False,
    ) -> bool:
        """Create a new collection.

        Args:
            collection_name: Name of collection. If None, uses default from settings.
            vector_size: Size of vectors. If None, uses default from settings.
            distance_metric: Distance metric (Cosine, Dot, Euclidean). If None, uses default.
            recreate: If True, delete existing collection and recreate

        Returns:
            True if collection was created successfully

        Raises:
            QdrantClientError: If creation fails
        """
        collection = collection_name or self.settings.collection_name
        size = vector_size or self.settings.vector_size
        distance = self._get_distance_metric(distance_metric)

        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_exists = any(c.name == collection for c in collections.collections)

            if collection_exists:
                if recreate:
                    logger.info(f"Deleting existing collection: {collection}")
                    await self.client.delete_collection(collection)
                else:
                    logger.info(f"Collection already exists: {collection}")
                    return True

            # Create collection
            await self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=size, distance=distance),
            )

            logger.info(
                f"Created collection: {collection}",
                vector_size=size,
                distance_metric=distance_metric or self.settings.distance_metric,
            )
            return True

        except Exception as e:
            error_msg = f"Failed to create collection '{collection}': {e}"
            logger.error(error_msg, error=str(e))
            raise QdrantClientError(
                error_msg, operation="create_collection", collection=collection, error=str(e)
            )

    async def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """Delete a collection.

        Args:
            collection_name: Name of collection. If None, uses default from settings.

        Returns:
            True if collection was deleted successfully

        Raises:
            QdrantClientError: If deletion fails
        """
        collection = collection_name or self.settings.collection_name

        try:
            await self.client.delete_collection(collection)
            logger.info(f"Deleted collection: {collection}")
            return True

        except Exception as e:
            error_msg = f"Failed to delete collection '{collection}': {e}"
            logger.error(error_msg, error=str(e))
            raise QdrantClientError(
                error_msg, operation="delete_collection", collection=collection, error=str(e)
            )

    async def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """Check if collection exists.

        Args:
            collection_name: Name of collection. If None, uses default from settings.

        Returns:
            True if collection exists
        """
        collection = collection_name or self.settings.collection_name

        try:
            collections = await self.client.get_collections()
            return any(c.name == collection for c in collections.collections)

        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}", error=str(e))
            return False

    async def get_collection_info(
        self, collection_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Get collection information.

        Args:
            collection_name: Name of collection. If None, uses default from settings.

        Returns:
            Dictionary with collection info (points_count, vector_size, etc.)

        Raises:
            QdrantClientError: If retrieval fails
        """
        collection = collection_name or self.settings.collection_name

        try:
            info = await self.client.get_collection(collection)

            return {
                "name": collection,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value,
                },
            }

        except Exception as e:
            error_msg = f"Failed to get collection info '{collection}': {e}"
            logger.error(error_msg, error=str(e))
            raise QdrantClientError(
                error_msg, operation="get_collection_info", collection=collection, error=str(e)
            )

    # ===== Vector Operations =====

    async def upsert(
        self,
        collection_name: Optional[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """Upsert vectors into collection.

        Args:
            collection_name: Name of collection. If None, uses default.
            vectors: List of vector embeddings
            payloads: List of metadata dictionaries (one per vector)
            ids: List of point IDs. If None, generates UUIDs.

        Returns:
            List of point IDs

        Raises:
            QdrantClientError: If upsert fails
        """
        collection = collection_name or self.settings.collection_name

        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        elif len(ids) != len(vectors):
            raise ValueError("Number of IDs must match number of vectors")

        try:
            # Create PointStruct objects
            points = [
                PointStruct(id=point_id, vector=vector, payload=payload)
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]

            # Upsert points
            await self.client.upsert(collection_name=collection, points=points)

            logger.info(f"Upserted {len(points)} vectors to collection: {collection}")
            return ids

        except Exception as e:
            error_msg = f"Failed to upsert vectors to '{collection}': {e}"
            logger.error(error_msg, error=str(e), count=len(vectors))
            raise QdrantClientError(
                error_msg, operation="upsert", collection=collection, count=len(vectors), error=str(e)
            )

    async def batch_upsert(
        self,
        collection_name: Optional[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: Optional[list[str]] = None,
        batch_size: int = 100,
    ) -> list[str]:
        """Upsert vectors in batches.

        Args:
            collection_name: Name of collection. If None, uses default.
            vectors: List of vector embeddings
            payloads: List of metadata dictionaries
            ids: List of point IDs. If None, generates UUIDs.
            batch_size: Size of each batch

        Returns:
            List of all point IDs

        Raises:
            QdrantClientError: If upsert fails
        """
        all_ids = []

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]

        # Process in batches
        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            batch_result_ids = await self.upsert(
                collection_name=collection_name,
                vectors=batch_vectors,
                payloads=batch_payloads,
                ids=batch_ids,
            )
            all_ids.extend(batch_result_ids)

        logger.info(
            f"Batch upsert completed: {len(all_ids)} vectors in {(len(vectors) + batch_size - 1) // batch_size} batches"
        )
        return all_ids

    async def search(
        self,
        collection_name: Optional[str],
        query_vector: list[float],
        limit: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            collection_name: Name of collection. If None, uses default.
            query_vector: Query vector embedding
            limit: Maximum number of results
            filter_metadata: Metadata filters (e.g., {"user_id": "123"})
            score_threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of search results with id, score, and payload

        Raises:
            QdrantClientError: If search fails
        """
        collection = collection_name or self.settings.collection_name

        try:
            # Build filter if metadata provided
            query_filter = None
            if filter_metadata:
                conditions = [
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filter_metadata.items()
                ]
                query_filter = Filter(must=conditions)

            # Execute search
            search_results = await self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            # Format results
            results = [
                {"id": str(result.id), "score": result.score, "payload": result.payload}
                for result in search_results
            ]

            logger.info(
                f"Search completed: {len(results)} results",
                collection=collection,
                limit=limit,
                has_filter=filter_metadata is not None,
            )
            return results

        except Exception as e:
            error_msg = f"Failed to search in collection '{collection}': {e}"
            logger.error(error_msg, error=str(e))
            raise QdrantClientError(
                error_msg, operation="search", collection=collection, error=str(e)
            )

    async def delete(
        self, collection_name: Optional[str], ids: list[str]
    ) -> bool:
        """Delete vectors by IDs.

        Args:
            collection_name: Name of collection. If None, uses default.
            ids: List of point IDs to delete

        Returns:
            True if deletion was successful

        Raises:
            QdrantClientError: If deletion fails
        """
        collection = collection_name or self.settings.collection_name

        try:
            await self.client.delete(collection_name=collection, points_selector=ids)

            logger.info(f"Deleted {len(ids)} vectors from collection: {collection}")
            return True

        except Exception as e:
            error_msg = f"Failed to delete vectors from '{collection}': {e}"
            logger.error(error_msg, error=str(e), count=len(ids))
            raise QdrantClientError(
                error_msg, operation="delete", collection=collection, count=len(ids), error=str(e)
            )

    # ===== Health Check =====

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health check results:
            - connected: bool
            - collections: list of collection names
            - default_collection_exists: bool
            - default_collection_info: dict (if exists)
        """
        health = {
            "connected": self._connected,
            "collections": [],
            "default_collection_exists": False,
            "default_collection_info": None,
        }

        if not self._connected:
            return health

        try:
            # Get all collections
            collections = await self.client.get_collections()
            health["collections"] = [c.name for c in collections.collections]

            # Check default collection
            default_collection = self.settings.collection_name
            if default_collection in health["collections"]:
                health["default_collection_exists"] = True
                health["default_collection_info"] = await self.get_collection_info(
                    default_collection
                )

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            health["error"] = str(e)

        return health

    # ===== Context Manager Support =====

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False


# ===== Global Client Instance =====

_qdrant_client: Optional[QdrantVectorStore] = None


async def get_qdrant_client() -> QdrantVectorStore:
    """Get or create global Qdrant client instance.

    This is useful for dependency injection in FastAPI endpoints.

    Returns:
        Global QdrantVectorStore instance

    Example:
        ```python
        from fastapi import Depends
        from src.infrastructure.vector_store.qdrant_client import get_qdrant_client

        @app.post("/search")
        async def search_vectors(
            query: list[float],
            qdrant: QdrantVectorStore = Depends(get_qdrant_client)
        ):
            results = await qdrant.search(query_vector=query, limit=5)
            return {"results": results}
        ```
    """
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantVectorStore()
        await _qdrant_client.connect()

    return _qdrant_client


async def close_qdrant_client() -> None:
    """Close global Qdrant client connection.

    Call this during application shutdown.
    """
    global _qdrant_client

    if _qdrant_client is not None:
        await _qdrant_client.disconnect()
        _qdrant_client = None
