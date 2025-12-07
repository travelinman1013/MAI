"""Health check API endpoints with detailed service status and latency metrics.

This module provides comprehensive health checking:
- Basic health check (GET /health)
- Detailed health with service checks (GET /health/detailed)
- Kubernetes liveness probe (GET /health/live)
- Kubernetes readiness probe (GET /health/ready)

Service checks include:
- PostgreSQL database connectivity
- Redis cache connectivity
- Qdrant vector store connectivity
- LM Studio LLM server connectivity
"""

import asyncio
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.health import (
    BasicHealth,
    DetailedHealth,
    HealthStatus,
    ServiceHealth,
)
from src.core.utils.config import get_settings
from src.infrastructure.database.session import get_db

router = APIRouter(tags=["health"])


def _get_service_urls():
    """Get service URLs from settings."""
    settings = get_settings()
    return {
        "redis_url": settings.redis.url,
        "qdrant_url": settings.qdrant.url,
        "lm_studio_url": settings.lm_studio.base_url.rstrip("/v1"),  # Strip /v1 suffix
    }


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
    urls = _get_service_urls()

    # Run all health checks concurrently
    postgres_task = check_postgres(db)
    redis_task = check_redis(urls["redis_url"])
    qdrant_task = check_qdrant(urls["qdrant_url"])
    llm_task = check_llm(urls["lm_studio_url"])

    results = await asyncio.gather(
        postgres_task,
        redis_task,
        qdrant_task,
        llm_task,
        return_exceptions=True,
    )

    postgres, redis, qdrant, llm = results

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

    settings = get_settings()
    return DetailedHealth(
        status=status,
        services=services,
        total_latency_ms=round(total_latency, 2),
        timestamp=datetime.utcnow(),
        version=settings.app_version,
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


async def check_redis(redis_url: str) -> ServiceHealth:
    """Check Redis connectivity."""
    start = time.time()
    try:
        import redis.asyncio as redis_async

        client = redis_async.from_url(redis_url)
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


async def check_qdrant(qdrant_url: str) -> ServiceHealth:
    """Check Qdrant vector store connectivity."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{qdrant_url}/collections")

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


async def check_llm(lm_studio_url: str) -> ServiceHealth:
    """Check LM Studio LLM server connectivity."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{lm_studio_url}/v1/models")

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
        raise HTTPException(status_code=503, detail="Database not ready")
