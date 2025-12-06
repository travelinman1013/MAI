# 04 - Service Integration

## Task Information

| Field | Value |
|-------|-------|
| **Project** | MAI PostgreSQL + Qdrant Implementation |
| **Archon Project ID** | `42e538a6-9b44-4e9c-9a8a-2a8bcb6e2983` |
| **Archon Task ID** | `2e21c2ef-feee-446a-bcd3-3302fdb31211` |
| **Sequence** | 4 of 5 |
| **Depends On** | 03-database-migrations.md completed |

---

## Archon Task Management

**Mark task as in-progress when starting:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/2e21c2ef-feee-446a-bcd3-3302fdb31211" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Mark task as done when complete:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/2e21c2ef-feee-446a-bcd3-3302fdb31211" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

Steps 01-03 set up Docker services, environment configuration, and database migrations. The infrastructure is ready, but the mai-api service needs to properly:
1. Initialize connections to PostgreSQL and Qdrant on startup
2. Report service status in health checks
3. Create the Qdrant collection if it doesn't exist

The codebase already has:
- `src/main.py` with `_init_postgresql()` and `_init_qdrant()` functions
- `src/infrastructure/vector_store/qdrant_client.py` with `QdrantVectorStore` class
- `/health` endpoint that reports service status

---

## Requirements

### 1. Verify Qdrant Client Uses API Key

Check `src/infrastructure/vector_store/qdrant_client.py` properly uses the API key from settings:

```python
# In QdrantVectorStore.__init__ or connect():
self.client = AsyncQdrantClient(
    url=self.settings.url,
    api_key=self.settings.api_key,  # Should be set from QDRANT__API_KEY
    timeout=30
)
```

If `api_key` parameter is missing or not being passed, add it.

### 2. Update Qdrant Initialization to Create Collection

In `src/main.py`, update `_init_qdrant()` to create the default collection if it doesn't exist:

```python
async def _init_qdrant() -> None:
    """Initialize Qdrant connection and create default collection."""
    try:
        from src.infrastructure.vector_store.qdrant_client import get_qdrant_client

        qdrant = await get_qdrant_client()
        await qdrant.connect()

        # Create default collection if it doesn't exist
        settings = get_settings()
        collection_name = settings.qdrant.collection_name

        if not await qdrant.collection_exists(collection_name):
            await qdrant.create_collection(
                collection_name=collection_name,
                vector_size=settings.qdrant.vector_size,
                distance_metric=settings.qdrant.distance_metric
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
        else:
            logger.info(f"Qdrant collection exists: {collection_name}")

        _service_status["qdrant"] = True
        logger.info("Qdrant initialized successfully")
    except Exception as e:
        _service_status["qdrant"] = False
        logger.warning(f"Qdrant initialization failed (non-fatal): {e}")
```

### 3. Update Health Endpoint

Ensure the `/health` endpoint in `src/api/` reports all service statuses:

```python
@router.get("/health")
async def health_check():
    """Health check endpoint with service status."""
    from src.main import _service_status

    # Determine overall health
    required_services = ["redis"]  # Redis is required
    optional_services = ["postgresql", "qdrant"]  # These are optional

    required_healthy = all(_service_status.get(s, False) for s in required_services)

    return {
        "status": "healthy" if required_healthy else "degraded",
        "services": {
            "redis": _service_status.get("redis", False),
            "postgresql": _service_status.get("postgresql", False),
            "qdrant": _service_status.get("qdrant", False),
        },
        "version": "0.1.0"
    }
```

### 4. Add Qdrant Health Check Method

If not already present, add a `health_check()` method to `QdrantVectorStore`:

```python
async def health_check(self) -> dict:
    """Check Qdrant connection health.

    Returns:
        dict: Health status with connection info and collections.
    """
    if not self._connected:
        return {"connected": False, "error": "Not connected"}

    try:
        collections = await self.client.get_collections()
        return {
            "connected": True,
            "collections": [c.name for c in collections.collections],
            "url": self.settings.url
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
```

### 5. Verify Database Session Management

Ensure `src/infrastructure/database/session.py` properly handles connection lifecycle:

```python
# Verify init_db() is called on startup
async def init_db() -> None:
    """Initialize database connection."""
    global _engine, _session_factory

    settings = get_settings()
    _engine = create_async_engine(
        settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        echo=settings.database.echo,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
```

---

## Files to Modify

| File | Action |
|------|--------|
| `src/main.py` | Update `_init_qdrant()` to create collection |
| `src/infrastructure/vector_store/qdrant_client.py` | Verify API key is used, add health_check if missing |
| `src/api/routes.py` or `src/api/health.py` | Update health endpoint if needed |
| `src/core/utils/config.py` | Verify QdrantSettings has api_key field |

---

## Success Criteria

```bash
cd /Users/maxwell/Projects/MAI

# 1. Rebuild and restart services
docker compose down
docker compose build mai-api
docker compose up -d
sleep 45  # Wait for all services to initialize

# 2. Check health endpoint shows all services
curl http://localhost:8000/health
# Expected: {"status":"healthy","services":{"redis":true,"postgresql":true,"qdrant":true},"version":"0.1.0"}

# 3. Verify Qdrant collection was created
curl -H "api-key: mai-qdrant-secret-key" http://localhost:6333/collections
# Expected: {"result":{"collections":[{"name":"mai_embeddings"}]},"status":"ok",...}

# 4. Verify collection details
curl -H "api-key: mai-qdrant-secret-key" http://localhost:6333/collections/mai_embeddings
# Expected: Shows collection with vector_size: 1536, distance: Cosine

# 5. Check mai-api logs for initialization messages
docker logs mai-api 2>&1 | grep -E "(Qdrant|PostgreSQL|initialized|collection)"
# Expected: Should show successful initialization messages

# 6. Verify database connection works
docker exec mai-api python -c "
from src.infrastructure.database.session import get_session
import asyncio
async def test():
    async with get_session() as session:
        result = await session.execute('SELECT 1')
        print('DB connection OK:', result.scalar())
asyncio.run(test())
"
# Expected: DB connection OK: 1
```

---

## Technical Notes

- **Graceful Degradation:** PostgreSQL and Qdrant failures should not crash the app. They're logged as warnings.
- **API Key Authentication:** Qdrant requires the API key in the `api-key` header for REST API or in the client constructor.
- **Collection Creation:** The collection is created with the vector size and distance metric from settings (default: 1536 dimensions, Cosine distance).
- **Connection Pooling:** SQLAlchemy uses connection pooling. Default pool_size=20, max_overflow=10.
- **Startup Order:** Docker Compose health checks ensure postgres and qdrant are ready before mai-api starts.

---

## On Completion

1. Mark this task as done in Archon (see command above)
2. Proceed to **05-seed-testing.md**
3. Keep containers running for final testing
