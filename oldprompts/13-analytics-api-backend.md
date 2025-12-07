# Task: Analytics API Backend

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create backend analytics router with usage stats, agent insights, and model usage endpoints
**Sequence**: 13 of 14
**Depends On**: 12-sessions-api-backend.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `8b6fb82b-c8db-48aa-8394-16953f1c4bfc`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/8b6fb82b-c8db-48aa-8394-16953f1c4bfc" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/8b6fb82b-c8db-48aa-8394-16953f1c4bfc" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With sessions persisted in the database, we can now compute analytics from actual usage data. This task creates:

- **Usage Stats**: Message counts, token usage, session counts over time
- **Agent Insights**: Agent-level metrics with error rates
- **Model Usage**: Distribution of model usage across sessions

The frontend analytics dashboard (prompt 11) currently uses mock data. These APIs will provide real data based on the Session and Message models created in prompt 12.

---

## Requirements

### 1. Create Analytics Schemas

Create `src/api/schemas/analytics.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date


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
```

### 2. Create Analytics Router

Create `src/api/routes/analytics.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, distinct
from datetime import datetime, timedelta, date
from typing import Optional

from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import Session, Message
from src.api.schemas.analytics import (
    UsageStats,
    UsageDataPoint,
    AgentInsights,
    AgentStats,
    ModelUsage,
    ModelStats,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_current_user_id() -> str:
    """Get current user ID. Replace with actual auth when implemented."""
    return "default-user"


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    start_date: Optional[datetime] = Query(
        None,
        description="Start date for analytics (defaults to 30 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date for analytics (defaults to now)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics including daily breakdown."""
    user_id = get_current_user_id()

    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Get overall stats
    overall_query = (
        select(
            func.count(Message.id).label('total_messages'),
            func.sum(Message.token_count).label('total_tokens'),
            func.avg(Message.response_time_ms).label('avg_response_time'),
        )
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at.between(start_date, end_date),
        )
    )
    overall_result = await db.execute(overall_query)
    overall = overall_result.one()

    # Get session count
    session_count_query = (
        select(func.count(distinct(Session.id)))
        .where(
            Session.user_id == user_id,
            Session.created_at.between(start_date, end_date),
        )
    )
    total_sessions = await db.scalar(session_count_query) or 0

    # Get daily breakdown
    daily_query = (
        select(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('messages'),
            func.sum(Message.token_count).label('tokens'),
            func.count(distinct(Message.session_id)).label('sessions'),
        )
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at.between(start_date, end_date),
        )
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )
    daily_result = await db.execute(daily_query)
    daily_data = daily_result.all()

    # Fill in missing dates with zeros
    daily_usage = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    daily_dict = {row.date: row for row in daily_data}

    while current_date <= end_date_only:
        if current_date in daily_dict:
            row = daily_dict[current_date]
            daily_usage.append(
                UsageDataPoint(
                    date=current_date,
                    messages=row.messages or 0,
                    tokens=row.tokens or 0,
                    sessions=row.sessions or 0,
                )
            )
        else:
            daily_usage.append(
                UsageDataPoint(
                    date=current_date,
                    messages=0,
                    tokens=0,
                    sessions=0,
                )
            )
        current_date += timedelta(days=1)

    return UsageStats(
        total_messages=overall.total_messages or 0,
        total_tokens=overall.total_tokens or 0,
        total_sessions=total_sessions,
        avg_response_time_ms=round(overall.avg_response_time, 2) if overall.avg_response_time else None,
        daily_usage=daily_usage,
    )


@router.get("/agents", response_model=AgentInsights)
async def get_agent_insights(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get per-agent usage statistics."""
    user_id = get_current_user_id()

    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Query agent stats
    query = (
        select(
            Message.agent_name,
            func.count(Message.id).label('usage_count'),
            func.sum(Message.token_count).label('total_tokens'),
            func.avg(Message.response_time_ms).label('avg_response_time'),
            func.sum(case((Message.is_error == True, 1), else_=0)).label('error_count'),
        )
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at.between(start_date, end_date),
            Message.role == 'assistant',  # Only count assistant messages for agents
        )
        .group_by(Message.agent_name)
        .order_by(func.count(Message.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    total_calls = sum(row.usage_count or 0 for row in rows)

    agents = [
        AgentStats(
            name=row.agent_name or 'unknown',
            usage_count=row.usage_count or 0,
            total_tokens=row.total_tokens or 0,
            avg_response_time_ms=round(row.avg_response_time, 2) if row.avg_response_time else None,
            error_count=row.error_count or 0,
            error_rate=round((row.error_count or 0) / (row.usage_count or 1) * 100, 2),
        )
        for row in rows
    ]

    return AgentInsights(
        agents=agents,
        total_calls=total_calls,
    )


@router.get("/models", response_model=ModelUsage)
async def get_model_usage(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get model usage distribution."""
    user_id = get_current_user_id()

    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Query model stats
    query = (
        select(
            Message.model_id,
            func.count(Message.id).label('usage_count'),
            func.sum(Message.token_count).label('total_tokens'),
        )
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at.between(start_date, end_date),
            Message.model_id.isnot(None),
        )
        .group_by(Message.model_id)
        .order_by(func.count(Message.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    total_usage = sum(row.usage_count or 0 for row in rows)

    models = [
        ModelStats(
            model_id=row.model_id,
            model_name=_get_model_display_name(row.model_id),
            usage_count=row.usage_count or 0,
            total_tokens=row.total_tokens or 0,
        )
        for row in rows
    ]

    return ModelUsage(
        models=models,
        total_usage=total_usage,
    )


def _get_model_display_name(model_id: str) -> str:
    """Extract human-readable name from model ID."""
    if not model_id:
        return "Unknown"
    # Extract filename and clean up
    name = model_id.split('/')[-1]
    name = name.replace('-', ' ').replace('_', ' ')
    name = name.replace('.gguf', '').replace('.bin', '')
    return name.title()


@router.get("/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get a quick summary for dashboard cards."""
    user_id = get_current_user_id()
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Messages this month
    messages_query = (
        select(func.count(Message.id))
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at >= thirty_days_ago,
        )
    )
    total_messages = await db.scalar(messages_query) or 0

    # Active sessions
    sessions_query = (
        select(func.count(distinct(Session.id)))
        .where(
            Session.user_id == user_id,
            Session.updated_at >= seven_days_ago,
        )
    )
    active_sessions = await db.scalar(sessions_query) or 0

    # Total tokens
    tokens_query = (
        select(func.sum(Message.token_count))
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at >= thirty_days_ago,
        )
    )
    total_tokens = await db.scalar(tokens_query) or 0

    # Average response time
    response_time_query = (
        select(func.avg(Message.response_time_ms))
        .select_from(Message)
        .join(Session, Message.session_id == Session.id)
        .where(
            Session.user_id == user_id,
            Message.created_at >= thirty_days_ago,
            Message.response_time_ms.isnot(None),
        )
    )
    avg_response_time = await db.scalar(response_time_query)

    return {
        "total_messages": total_messages,
        "active_sessions": active_sessions,
        "total_tokens": total_tokens,
        "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
    }
```

### 3. Register Analytics Router

Update `src/main.py` to include the analytics router:

```python
# In src/main.py, add import and registration

from src.api.routes import analytics  # Add this import

# Add this line with other router registrations
app.include_router(analytics.router, prefix="/api/v1")
```

### 4. Update Frontend useAnalytics Hook

Update `frontend/src/hooks/useAnalytics.ts` to use the real API:

```tsx
import { useState, useEffect, useCallback } from 'react'

export interface UsageDataPoint {
  date: string
  messages: number
  tokens: number
  sessions: number
}

export interface AgentUsageData {
  name: string
  usageCount: number
  avgResponseTime: number
  errorRate: number
}

export interface ModelUsageData {
  name: string
  usageCount: number
  tokens: number
}

export interface AnalyticsData {
  totalMessages: number
  totalSessions: number
  totalTokens: number
  avgResponseTime: number
  usage: UsageDataPoint[]
  agents: AgentUsageData[]
  models: ModelUsageData[]
}

export function useAnalytics(startDate?: Date, endDate?: Date) {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Build query params
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate.toISOString())
      if (endDate) params.set('end_date', endDate.toISOString())

      // Fetch all analytics data in parallel
      const [usageRes, agentsRes, modelsRes] = await Promise.all([
        fetch(`/api/v1/analytics/usage?${params}`),
        fetch(`/api/v1/analytics/agents?${params}`),
        fetch(`/api/v1/analytics/models?${params}`),
      ])

      if (!usageRes.ok || !agentsRes.ok || !modelsRes.ok) {
        throw new Error('Failed to fetch analytics')
      }

      const [usage, agents, models] = await Promise.all([
        usageRes.json(),
        agentsRes.json(),
        modelsRes.json(),
      ])

      setData({
        totalMessages: usage.total_messages,
        totalSessions: usage.total_sessions,
        totalTokens: usage.total_tokens,
        avgResponseTime: usage.avg_response_time_ms || 0,
        usage: usage.daily_usage.map((d: any) => ({
          date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          messages: d.messages,
          tokens: d.tokens,
          sessions: d.sessions,
        })),
        agents: agents.agents.map((a: any) => ({
          name: a.name,
          usageCount: a.usage_count,
          avgResponseTime: a.avg_response_time_ms || 0,
          errorRate: a.error_rate,
        })),
        models: models.models.map((m: any) => ({
          name: m.model_name,
          usageCount: m.usage_count,
          tokens: m.total_tokens,
        })),
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch analytics'))
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, isLoading, error, refresh: fetchData }
}
```

---

## Files to Create

- `src/api/schemas/analytics.py` - Pydantic schemas for analytics
- `src/api/routes/analytics.py` - Analytics router with aggregation queries

## Files to Modify

- `src/main.py` - Register analytics router
- `frontend/src/hooks/useAnalytics.ts` - Connect to real API

---

## Success Criteria

```bash
# Verify analytics router exists
ls /Users/maxwell/Projects/MAI/src/api/routes/analytics.py
# Expected: File exists

# Verify schemas exist
ls /Users/maxwell/Projects/MAI/src/api/schemas/analytics.py
# Expected: File exists

# Start the backend server
cd /Users/maxwell/Projects/MAI && python -m uvicorn src.main:app --reload &

# Test usage stats endpoint
curl http://localhost:8000/api/v1/analytics/usage
# Expected: {"total_messages": ..., "daily_usage": [...]}

# Test agent insights endpoint
curl http://localhost:8000/api/v1/analytics/agents
# Expected: {"agents": [...], "total_calls": ...}

# Test model usage endpoint
curl http://localhost:8000/api/v1/analytics/models
# Expected: {"models": [...], "total_usage": ...}

# Test summary endpoint
curl http://localhost:8000/api/v1/analytics/summary
# Expected: Quick summary JSON
```

**Checklist:**
- [ ] Analytics schemas for usage, agents, models
- [ ] GET /analytics/usage - Daily breakdown with totals
- [ ] GET /analytics/agents - Per-agent stats with error rates
- [ ] GET /analytics/models - Model usage distribution
- [ ] GET /analytics/summary - Quick dashboard summary
- [ ] Date filtering via query params
- [ ] Zero-filled daily usage for missing dates
- [ ] Frontend hook connects to real API

---

## Technical Notes

- **Date Range**: Defaults to last 30 days if not specified
- **User Filtering**: All queries filter by user_id
- **Error Rate**: Calculated as error_count / usage_count * 100
- **Daily Fill**: Missing dates are filled with zeros for consistent charts
- **Model Names**: Extracted from model_id paths and cleaned up

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 14-health-api-backend.md (Final)
