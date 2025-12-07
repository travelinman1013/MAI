# Task: Enhanced Health API Backend (FINAL)

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Enhance health endpoint with detailed service checks and latency metrics
**Sequence**: 14 of 14 (FINAL)
**Depends On**: 13-analytics-api-backend.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `fbcc85b9-b33b-493c-bd56-4fb66c6c6636`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/fbcc85b9-b33b-493c-bd56-4fb66c6c6636" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/fbcc85b9-b33b-493c-bd56-4fb66c6c6636" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

This is the **final task** in the MAI React Frontend implementation plan. The existing `src/api/routes/health.py` provides a basic health check. This task enhances it to:

- **Service Checks**: Individual health status for Redis, PostgreSQL, Qdrant, LLM
- **Latency Metrics**: Response time for each service check
- **Detailed Status**: Overall status based on critical service health
- **Frontend Integration**: Update useHealth hook to use the real API

After completing this task, the React frontend will be fully functional with real backend APIs.

---

## Requirements

### 1. Create Health Schemas

Create `src/api/schemas/health.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Overall health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health status for individual service."""
    ok: bool = Field(..., description="Whether the service is healthy")
    latency_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Optional[Dict] = Field(None, description="Additional service details")


class DetailedHealth(BaseModel):
    """Detailed health check response."""
    status: HealthStatus = Field(..., description="Overall system status")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service statuses")
    total_latency_ms: float = Field(..., description="Total time to check all services")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: Optional[str] = Field(None, description="Application version")


class BasicHealth(BaseModel):
    """Basic health check response."""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 2. Update Health Router

Update or replace `src/api/routes/health.py`:

```python
import time
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from typing import Optional
import httpx

from src.api.schemas.health import (
    BasicHealth,
    DetailedHealth,
    ServiceHealth,
    HealthStatus,
)
from src.infrastructure.database.session import get_db
from src.core.config import settings  # Adjust import based on your config location

router = APIRouter(tags=["health"])


# Configuration - adjust these based on your setup
REDIS_URL = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
QDRANT_URL = getattr(settings, 'QDRANT_URL', 'http://localhost:6333')
LM_STUDIO_URL = getattr(settings, 'LM_STUDIO_URL', 'http://localhost:1234')


@router.get("/health", response_model=BasicHealth)
async def basic_health():
    """Basic health check endpoint."""
    return BasicHealth(status="ok", timestamp=datetime.utcnow())


@router.get("/health/detailed", response_model=DetailedHealth)
async def detailed_health(
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed health check with individual service status and latency metrics.

    Checks:
    - PostgreSQL database connectivity
    - Redis cache connectivity
    - Qdrant vector store connectivity
    - LM Studio LLM server connectivity
    """
    start_time = time.time()

    # Run all health checks concurrently
    postgres_task = check_postgres(db)
    redis_task = check_redis()
    qdrant_task = check_qdrant()
    llm_task = check_llm()

    postgres, redis, qdrant, llm = await asyncio.gather(
        postgres_task,
        redis_task,
        qdrant_task,
        llm_task,
        return_exceptions=True,
    )

    # Handle exceptions as failed checks
    if isinstance(postgres, Exception):
        postgres = ServiceHealth(ok=False, error=str(postgres))
    if isinstance(redis, Exception):
        redis = ServiceHealth(ok=False, error=str(redis))
    if isinstance(qdrant, Exception):
        qdrant = ServiceHealth(ok=False, error=str(qdrant))
    if isinstance(llm, Exception):
        llm = ServiceHealth(ok=False, error=str(llm))

    services = {
        "postgres": postgres,
        "redis": redis,
        "qdrant": qdrant,
        "llm": llm,
    }

    # Determine overall status
    # Critical services: postgres (required)
    # Non-critical: redis, qdrant, llm (degraded if down)
    if not postgres.ok:
        status = HealthStatus.UNHEALTHY
    elif not all(s.ok for s in [redis, qdrant, llm]):
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.HEALTHY

    total_latency = (time.time() - start_time) * 1000

    return DetailedHealth(
        status=status,
        services=services,
        total_latency_ms=round(total_latency, 2),
        timestamp=datetime.utcnow(),
        version="1.0.0",  # Replace with actual version
    )


async def check_postgres(db: AsyncSession) -> ServiceHealth:
    """Check PostgreSQL database connectivity."""
    start = time.time()
    try:
        result = await db.execute(text("SELECT 1"))
        _ = result.scalar()
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=True,
            latency_ms=round(latency, 2),
            details={"database": "connected"},
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=False,
            latency_ms=round(latency, 2),
            error=str(e),
        )


async def check_redis() -> ServiceHealth:
    """Check Redis connectivity."""
    start = time.time()
    try:
        import redis.asyncio as redis

        client = redis.from_url(REDIS_URL)
        await client.ping()
        await client.close()

        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=True,
            latency_ms=round(latency, 2),
            details={"cache": "connected"},
        )
    except ImportError:
        # Redis not installed - mark as unavailable but not error
        return ServiceHealth(
            ok=False,
            error="Redis client not installed",
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=False,
            latency_ms=round(latency, 2),
            error=str(e),
        )


async def check_qdrant() -> ServiceHealth:
    """Check Qdrant vector store connectivity."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{QDRANT_URL}/collections")

        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            collections = data.get("result", {}).get("collections", [])
            return ServiceHealth(
                ok=True,
                latency_ms=round(latency, 2),
                details={"collections": len(collections)},
            )
        else:
            return ServiceHealth(
                ok=False,
                latency_ms=round(latency, 2),
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=False,
            latency_ms=round(latency, 2),
            error=str(e),
        )


async def check_llm() -> ServiceHealth:
    """Check LM Studio LLM server connectivity."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LM_STUDIO_URL}/v1/models")

        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            model_name = models[0].get("id") if models else None
            return ServiceHealth(
                ok=True,
                latency_ms=round(latency, 2),
                details={
                    "model_count": len(models),
                    "active_model": model_name,
                },
            )
        else:
            return ServiceHealth(
                ok=False,
                latency_ms=round(latency, 2),
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            ok=False,
            latency_ms=round(latency, 2),
            error=str(e),
        )


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe - checks database is accessible."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not ready")
```

### 3. Update Frontend useHealth Hook

Update `frontend/src/hooks/useHealth.ts` to use the real API:

```tsx
import { useState, useEffect, useCallback } from 'react'

export interface ServiceHealth {
  ok: boolean
  latency_ms?: number
  error?: string
  details?: Record<string, any>
}

export interface DetailedHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  services: {
    redis: ServiceHealth
    postgres: ServiceHealth
    qdrant: ServiceHealth
    llm: ServiceHealth
  }
  total_latency_ms: number
  timestamp: string
  version?: string
}

export function useHealth(pollInterval = 30000) {
  const [health, setHealth] = useState<DetailedHealth | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch('/health/detailed')

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`)
      }

      const data = await response.json()
      setHealth(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch health'))
      // Don't clear existing health data on error - show stale data
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, pollInterval)
    return () => clearInterval(interval)
  }, [fetchHealth, pollInterval])

  return { health, isLoading, error, refresh: fetchHealth }
}
```

### 4. Ensure Health Router is Registered

In `src/main.py`, ensure the health router is registered at the root level (no prefix):

```python
from src.api.routes import health

# Register health at root (not under /api/v1)
app.include_router(health.router)
```

---

## Files to Create

- `src/api/schemas/health.py` - Pydantic schemas for health responses

## Files to Modify

- `src/api/routes/health.py` - Enhanced health checks with latency
- `src/main.py` - Ensure health router is registered
- `frontend/src/hooks/useHealth.ts` - Connect to real API

---

## Success Criteria

```bash
# Verify health schemas exist
ls /Users/maxwell/Projects/MAI/src/api/schemas/health.py
# Expected: File exists

# Start the backend server
cd /Users/maxwell/Projects/MAI && python -m uvicorn src.main:app --reload &

# Test basic health endpoint
curl http://localhost:8000/health
# Expected: {"status": "ok", "timestamp": "..."}

# Test detailed health endpoint
curl http://localhost:8000/health/detailed
# Expected: {"status": "healthy|degraded|unhealthy", "services": {...}, "total_latency_ms": ...}

# Test liveness probe
curl http://localhost:8000/health/live
# Expected: {"status": "alive"}

# Test readiness probe
curl http://localhost:8000/health/ready
# Expected: {"status": "ready"} or 503 if DB down

# Verify frontend health polling
cd /Users/maxwell/Projects/MAI/frontend && npm run dev &
# Open browser and check analytics page system health
# Expected: Shows real service statuses with latencies
```

**Checklist:**
- [ ] Health schemas for basic and detailed responses
- [ ] GET /health - Basic status check
- [ ] GET /health/detailed - All services with latency
- [ ] GET /health/live - Kubernetes liveness probe
- [ ] GET /health/ready - Kubernetes readiness probe
- [ ] PostgreSQL check with query latency
- [ ] Redis check with ping latency
- [ ] Qdrant check with collections query
- [ ] LLM check with models endpoint
- [ ] Overall status based on service health
- [ ] Frontend displays real health data

---

## Technical Notes

- **Concurrent Checks**: All service checks run in parallel with asyncio.gather
- **Timeouts**: 5 second timeout for external service checks
- **Critical vs Non-Critical**: Only PostgreSQL failure = unhealthy; others = degraded
- **Error Handling**: Exceptions from checks are caught and returned as errors
- **Kubernetes Probes**: /health/live and /health/ready for container orchestration

---

## On Completion

This is the **final task** in the MAI React Frontend implementation plan.

### Final Steps:

1. Mark Archon task as `done`:
```bash
curl -X PUT "http://localhost:8181/api/tasks/fbcc85b9-b33b-493c-bd56-4fb66c6c6636" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Verify ALL success criteria pass

3. Create completion document in Archon:
```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI React Frontend - Implementation Complete",
    "content": "# MAI React Frontend Implementation Complete\n\n## Summary\nAll 14 tasks in the React Frontend implementation plan have been completed successfully.\n\n## Completed Tasks\n1. Foundation Setup - shadcn/ui dependencies and configuration\n2. Core UI Components - 18 shadcn primitives\n3. Zustand State Management - chatStore, uiStore, settingsStore\n4. Layout & Routing - MainLayout, Header, React Router\n5. Chat Components - ChatContainer with split-view, ChatPanel, MessageList\n6. Message Input & Files - FileUploadZone, FilePreview, StreamingIndicator\n7. Model & Agent Selectors - ModelSelector, AgentSelector, LLMStatusBadge\n8. Sidebar & Sessions - SessionList with date grouping, search, context menu\n9. Settings Panel - SettingsDialog with API, Model, Theme, Keyboard tabs\n10. Command Palette - cmdk integration with Cmd+K\n11. Analytics Dashboard - Chart.js charts, usage stats, system health\n12. Sessions API Backend - CRUD endpoints, Session/Message models\n13. Analytics API Backend - Usage, agents, models aggregations\n14. Health API Backend - Detailed health checks with latency\n\n## Tech Stack\n- Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui\n- State: Zustand with localStorage persistence\n- Charts: Chart.js + react-chartjs-2\n- Backend: FastAPI, SQLAlchemy, PostgreSQL\n\n## Status\nAll features implemented and tested. Ready for integration testing.",
    "project_id": "17384994-d1d6-4286-992b-bf82d7485830",
    "doc_type": "completion"
  }'
```

4. Run full integration test:
```bash
# Start backend
cd /Users/maxwell/Projects/MAI && python -m uvicorn src.main:app --reload &

# Start frontend
cd /Users/maxwell/Projects/MAI/frontend && npm run dev &

# Open http://localhost:5173 and verify:
# - Chat interface works
# - Sessions persist
# - Analytics show real data
# - Settings persist
# - Command palette opens with Cmd+K
# - System health displays correctly
```

---

## Congratulations!

The MAI React Frontend implementation is now complete. The dashboard includes:

- Full shadcn/ui component library
- Split-view chat with file uploads
- Model and agent selection with LLM status
- Session management with date grouping
- Comprehensive settings panel
- Command palette for power users
- Real-time analytics dashboard
- System health monitoring
- Persistent backend APIs

All frontend components are connected to real backend APIs for a fully functional experience.
