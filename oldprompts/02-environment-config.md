# 02 - Environment Configuration

## Task Information

| Field | Value |
|-------|-------|
| **Project** | MAI PostgreSQL + Qdrant Implementation |
| **Archon Project ID** | `42e538a6-9b44-4e9c-9a8a-2a8bcb6e2983` |
| **Archon Task ID** | `89649319-d528-4061-9540-35393cc989e1` |
| **Sequence** | 2 of 5 |
| **Depends On** | 01-docker-services.md completed |

---

## Archon Task Management

**Mark task as in-progress when starting:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/89649319-d528-4061-9540-35393cc989e1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Mark task as done when complete:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/89649319-d528-4061-9540-35393cc989e1" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

Step 01 added PostgreSQL and Qdrant services to docker-compose.yml. Now we need to:
1. Update `.env.example` with proper Docker service URLs
2. Create a working `.env` file for local development
3. Generate a secure Qdrant API key
4. Ensure all environment variables are correctly configured

The existing `.env.example` has localhost URLs which work for local development without Docker, but need Docker service names when running in containers.

---

## Requirements

### 1. Update .env.example

Update the `.env.example` file to document both local and Docker configurations:

**Database section:**
```bash
# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL) - REQUIRED for persistence
# -----------------------------------------------------------------------------
# Local development (host machine):
# DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework
#
# Docker Compose (use service name as host):
DATABASE__URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=10
DATABASE__POOL_TIMEOUT=30
DATABASE__ECHO=false
```

**Qdrant section:**
```bash
# -----------------------------------------------------------------------------
# Qdrant Vector Store Configuration - REQUIRED for semantic search
# -----------------------------------------------------------------------------
# Local development (host machine):
# QDRANT__URL=http://localhost:6333
#
# Docker Compose (use service name as host):
QDRANT__URL=http://qdrant:6333
QDRANT__API_KEY=mai-qdrant-secret-key
QDRANT__COLLECTION_NAME=mai_embeddings
QDRANT__VECTOR_SIZE=1536
QDRANT__DISTANCE_METRIC=Cosine
```

### 2. Create .env File

Create a working `.env` file (if it doesn't exist) with Docker-ready configuration:

```bash
# =============================================================================
# MAI Framework Configuration - Docker Compose
# =============================================================================

# Application Settings
APP_NAME=mai-framework
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Database Configuration (PostgreSQL)
DATABASE__URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=10
DATABASE__POOL_TIMEOUT=30
DATABASE__ECHO=false

# Redis Configuration
REDIS__URL=redis://redis:6379/0
REDIS__MAX_CONNECTIONS=50
REDIS__TIMEOUT=5

# Qdrant Vector Store Configuration
QDRANT__URL=http://qdrant:6333
QDRANT__API_KEY=mai-qdrant-secret-key
QDRANT__COLLECTION_NAME=mai_embeddings
QDRANT__VECTOR_SIZE=1536
QDRANT__DISTANCE_METRIC=Cosine

# LLM Provider Configuration
LLM__PROVIDER=lmstudio
LM_STUDIO__BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO__API_KEY=not-needed
LM_STUDIO__MODEL_NAME=local-model
LM_STUDIO__MAX_TOKENS=2048
LM_STUDIO__TEMPERATURE=0.7
LM_STUDIO__TIMEOUT=30

# Memory Configuration
SHORT_TERM_MEMORY_TTL=3600
LONG_TERM_MEMORY_ENABLED=true
SEMANTIC_SEARCH_ENABLED=true
MEMORY_MAX_HISTORY=50

# JWT Authentication
JWT_SECRET=dev-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Testing (uses different database)
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework_test
TEST_REDIS_URL=redis://redis:6379/1
```

### 3. Generate Secure API Key (Production Note)

Add a note in `.env.example` about generating secure keys:

```bash
# To generate a secure API key for production:
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Update docker-compose.yml Environment Variables

Ensure docker-compose.yml uses the correct environment variable format. The mai-api service should have:

```yaml
environment:
  - REDIS__URL=redis://redis:6379/0
  - DATABASE__URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework
  - QDRANT__URL=http://qdrant:6333
  - QDRANT__API_KEY=${QDRANT_API_KEY:-mai-qdrant-secret-key}
  - ENVIRONMENT=development
  - LOG_LEVEL=INFO
  - LLM__PROVIDER=lmstudio
  - LM_STUDIO__BASE_URL=http://host.docker.internal:1234/v1
  - LM_STUDIO__MODEL_NAME=google/gemma-3-12b
```

---

## Files to Modify

| File | Action |
|------|--------|
| `/Users/maxwell/Projects/MAI/.env.example` | Update with Docker service URLs and documentation |
| `/Users/maxwell/Projects/MAI/.env` | Create with working Docker configuration |
| `/Users/maxwell/Projects/MAI/docker-compose.yml` | Verify environment variables use double-underscore format |

---

## Success Criteria

```bash
cd /Users/maxwell/Projects/MAI

# 1. Verify .env exists
test -f .env && echo ".env exists" || echo ".env missing"
# Expected: .env exists

# 2. Verify DATABASE__URL uses Docker service name
grep "DATABASE__URL=.*@postgres:" .env
# Expected: DATABASE__URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mai_framework

# 3. Verify QDRANT__URL uses Docker service name
grep "QDRANT__URL=.*qdrant:" .env
# Expected: QDRANT__URL=http://qdrant:6333

# 4. Verify QDRANT__API_KEY is set
grep "QDRANT__API_KEY=" .env
# Expected: QDRANT__API_KEY=mai-qdrant-secret-key (or custom key)

# 5. Restart services and verify they pick up new config
docker compose down && docker compose up -d
sleep 30

# 6. Verify mai-api can see environment variables
docker exec mai-api printenv | grep -E "(DATABASE|QDRANT|REDIS)"
# Expected: Should show all three service URLs
```

---

## Technical Notes

- **Double Underscore Format:** Pydantic-settings uses `__` as nested delimiter. `DATABASE__URL` maps to `settings.database.url`.
- **Docker Service Names:** Inside Docker network, services reach each other by service name (e.g., `postgres`, `qdrant`, `redis`), not `localhost`.
- **host.docker.internal:** Special DNS name that resolves to host machine from inside Docker. Used for LM Studio which runs on host.
- **API Key Security:** The default key is fine for development. For production, generate a cryptographically secure key.

---

## On Completion

1. Mark this task as done in Archon (see command above)
2. Proceed to **03-database-migrations.md**
3. Keep containers running for next steps
