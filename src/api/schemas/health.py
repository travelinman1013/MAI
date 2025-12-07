"""Health check schemas for API responses.

This module provides Pydantic models for health check endpoints including:
- Basic health status
- Detailed health with individual service checks
- Service-level health with latency metrics
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


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
    services: Dict[str, ServiceHealth] = Field(
        ..., description="Individual service statuses"
    )
    total_latency_ms: float = Field(..., description="Total time to check all services")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: Optional[str] = Field(None, description="Application version")


class BasicHealth(BaseModel):
    """Basic health check response."""

    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
