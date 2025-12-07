"""Analytics schemas for MAI Framework.

These schemas define the response models for analytics endpoints including
usage statistics, agent insights, and model usage distribution.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class UsageDataPoint(BaseModel):
    """Daily usage data point."""

    date: date
    messages: int
    tokens: int
    sessions: int


class UsageStats(BaseModel):
    """Overall usage statistics."""

    total_messages: int
    total_tokens: int
    total_sessions: int
    avg_response_time_ms: Optional[float]
    daily_usage: List[UsageDataPoint]


class AgentStats(BaseModel):
    """Per-agent statistics."""

    name: str
    usage_count: int
    total_tokens: int
    avg_response_time_ms: Optional[float]
    error_count: int
    error_rate: float  # Percentage


class AgentInsights(BaseModel):
    """Agent usage insights."""

    agents: List[AgentStats]
    total_calls: int


class ModelStats(BaseModel):
    """Per-model statistics."""

    model_id: str
    model_name: str
    usage_count: int
    total_tokens: int


class ModelUsage(BaseModel):
    """Model usage distribution."""

    models: List[ModelStats]
    total_usage: int


class AnalyticsSummary(BaseModel):
    """Quick summary for dashboard cards."""

    total_messages: int
    active_sessions: int
    total_tokens: int
    avg_response_time_ms: Optional[float]
