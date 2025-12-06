# 01 - Docker Services Setup

## Task Information

| Field | Value |
|-------|-------|
| **Project** | MAI PostgreSQL + Qdrant Implementation |
| **Archon Project ID** | `42e538a6-9b44-4e9c-9a8a-2a8bcb6e2983` |
| **Archon Task ID** | `5614394a-b069-4902-9241-d1e5b6fd2fe1` |
| **Sequence** | 1 of 5 |
| **Depends On** | None (first step) |

---

## Archon Task Management

**Mark task as in-progress when starting:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/5614394a-b069-4902-9241-d1e5b6fd2fe1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Mark task as done when complete:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/5614394a-b069-4902-9241-d1e5b6fd2fe1" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI Framework currently has a `docker-compose.yml` with three services:
- `redis` (working)
- `mai-api` (working)
- `mai-gui` (working)

We need to add PostgreSQL 18 and Qdrant services to enable:
- Persistent database storage for users, conversations, messages, and memories
- Vector similarity search for semantic memory retrieval

The codebase already has:
- SQLAlchemy models defined in `src/infrastructure/database/models.py`
- Qdrant client implemented in `src/infrastructure/vector_store/qdrant_client.py`
- Environment variables configured in `.env.example`

---

## Requirements

### 1. Add PostgreSQL 18 Service

Add a PostgreSQL 18 service using the `pgvector/pgvector:pg18` image (includes pgvector extension for future use):

```yaml
postgres:
  image: pgvector/pgvector:pg18
  container_name: mai-postgres
  ports:
    - "5432:5432"
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: mai_framework
  volumes:
    - postgres_data:/var/lib/postgresql
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres -d mai_framework"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s
  restart: unless-stopped
  networks:
    - mai-network
```

**Important for PostgreSQL 18:** The PGDATA path changed to `/var/lib/postgresql/18/docker`. The volume mount should be at `/var/lib/postgresql` (parent directory).

### 2. Add Qdrant Service

Add a Qdrant service with API key authentication:

```yaml
qdrant:
  image: qdrant/qdrant:latest
  container_name: mai-qdrant
  ports:
    - "6333:6333"
    - "6334:6334"
  environment:
    QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY:-mai-qdrant-secret-key}
  volumes:
    - qdrant_data:/qdrant/storage
  healthcheck:
    test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:6333/readyz"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s
  restart: unless-stopped
  networks:
    - mai-network
```

### 3. Add Volume Definitions

Add to the `volumes` section:

```yaml
volumes:
  redis_data:
    driver: local
  postgres_data:
    driver: local
  qdrant_data:
    driver: local
```

### 4. Update mai-api Dependencies

Update `mai-api` service to depend on postgres and qdrant:

```yaml
mai-api:
  # ... existing config ...
  depends_on:
    redis:
      condition: service_healthy
    postgres:
      condition: service_healthy
    qdrant:
      condition: service_healthy
  environment:
    # ... existing env vars ...
    - DATABASE__URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework
    - QDRANT__URL=http://qdrant:6333
    - QDRANT__API_KEY=${QDRANT_API_KEY:-mai-qdrant-secret-key}
```

---

## Files to Modify

| File | Action |
|------|--------|
| `/Users/maxwell/Projects/MAI/docker-compose.yml` | Add postgres and qdrant services, update volumes, update mai-api |

---

## Success Criteria

After completing this step, verify with these commands:

```bash
# 1. Bring up all services
cd /Users/maxwell/Projects/MAI
docker compose up -d

# 2. Wait for services to be healthy (about 30 seconds)
sleep 30

# 3. Verify all containers are running
docker compose ps
# Expected: All 5 services (redis, postgres, qdrant, mai-api, mai-gui) should show "Up" and "healthy"

# 4. Test PostgreSQL connection
docker exec mai-postgres pg_isready -U postgres -d mai_framework
# Expected: /var/run/postgresql:5432 - accepting connections

# 5. Test Qdrant API (with auth)
curl -H "api-key: mai-qdrant-secret-key" http://localhost:6333/readyz
# Expected: {"title":"...", "result": ...} or similar success response

# 6. Verify Qdrant collections endpoint
curl -H "api-key: mai-qdrant-secret-key" http://localhost:6333/collections
# Expected: {"result":{"collections":[]},"status":"ok","time":...}
```

---

## Technical Notes

- **PostgreSQL 18 Volume Change:** PostgreSQL 18 uses `/var/lib/postgresql/18/docker` for PGDATA. Mount volumes at `/var/lib/postgresql` to support this.
- **Qdrant Ports:**
  - 6333: HTTP REST API
  - 6334: gRPC API (optional, for high-performance clients)
- **API Key:** Using environment variable with fallback default. In production, generate a secure key.
- **Health Checks:** Both services have explicit health checks to ensure dependencies start in correct order.
- **Network:** All services share `mai-network` for internal communication.

---

## On Completion

1. Mark this task as done in Archon (see command above)
2. Proceed to **02-environment-config.md**
3. Keep containers running for next steps
