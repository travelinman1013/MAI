"""Analytics API router for usage statistics and insights.

Endpoints:
- GET /analytics/usage - Daily usage breakdown with totals
- GET /analytics/agents - Per-agent statistics with error rates
- GET /analytics/models - Model usage distribution
- GET /analytics/summary - Quick dashboard summary
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.analytics import (
    AgentInsights,
    AgentStats,
    AnalyticsSummary,
    ModelStats,
    ModelUsage,
    UsageDataPoint,
    UsageStats,
)
from src.infrastructure.database.models import ChatMessage, ChatSession
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_current_user_id() -> str:
    """Get current user ID. Replace with actual auth when implemented."""
    return "default-user"


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    start_date: Optional[datetime] = Query(
        None, description="Start date for analytics (defaults to 30 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date for analytics (defaults to now)"
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
            func.count(ChatMessage.id).label("total_messages"),
            func.sum(ChatMessage.token_count).label("total_tokens"),
            func.avg(ChatMessage.response_time_ms).label("avg_response_time"),
        )
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at.between(start_date, end_date),
        )
    )
    overall_result = await db.execute(overall_query)
    overall = overall_result.one()

    # Get session count
    session_count_query = select(func.count(distinct(ChatSession.id))).where(
        ChatSession.user_id == user_id,
        ChatSession.created_at.between(start_date, end_date),
    )
    total_sessions = await db.scalar(session_count_query) or 0

    # Get daily breakdown
    daily_query = (
        select(
            func.date(ChatMessage.created_at).label("date"),
            func.count(ChatMessage.id).label("messages"),
            func.sum(ChatMessage.token_count).label("tokens"),
            func.count(distinct(ChatMessage.session_id)).label("sessions"),
        )
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at.between(start_date, end_date),
        )
        .group_by(func.date(ChatMessage.created_at))
        .order_by(func.date(ChatMessage.created_at))
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
        avg_response_time_ms=(
            round(overall.avg_response_time, 2) if overall.avg_response_time else None
        ),
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
            ChatMessage.agent_name,
            func.count(ChatMessage.id).label("usage_count"),
            func.sum(ChatMessage.token_count).label("total_tokens"),
            func.avg(ChatMessage.response_time_ms).label("avg_response_time"),
            func.sum(case((ChatMessage.is_error == True, 1), else_=0)).label(
                "error_count"
            ),
        )
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at.between(start_date, end_date),
            ChatMessage.role == "assistant",  # Only count assistant messages for agents
        )
        .group_by(ChatMessage.agent_name)
        .order_by(func.count(ChatMessage.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    total_calls = sum(row.usage_count or 0 for row in rows)

    agents = [
        AgentStats(
            name=row.agent_name or "unknown",
            usage_count=row.usage_count or 0,
            total_tokens=row.total_tokens or 0,
            avg_response_time_ms=(
                round(row.avg_response_time, 2) if row.avg_response_time else None
            ),
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
            ChatMessage.model_id,
            func.count(ChatMessage.id).label("usage_count"),
            func.sum(ChatMessage.token_count).label("total_tokens"),
        )
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at.between(start_date, end_date),
            ChatMessage.model_id.isnot(None),
        )
        .group_by(ChatMessage.model_id)
        .order_by(func.count(ChatMessage.id).desc())
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
    name = model_id.split("/")[-1]
    name = name.replace("-", " ").replace("_", " ")
    name = name.replace(".gguf", "").replace(".bin", "")
    return name.title()


@router.get("/summary", response_model=AnalyticsSummary)
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
        select(func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at >= thirty_days_ago,
        )
    )
    total_messages = await db.scalar(messages_query) or 0

    # Active sessions
    sessions_query = select(func.count(distinct(ChatSession.id))).where(
        ChatSession.user_id == user_id,
        ChatSession.updated_at >= seven_days_ago,
    )
    active_sessions = await db.scalar(sessions_query) or 0

    # Total tokens
    tokens_query = (
        select(func.sum(ChatMessage.token_count))
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at >= thirty_days_ago,
        )
    )
    total_tokens = await db.scalar(tokens_query) or 0

    # Average response time
    response_time_query = (
        select(func.avg(ChatMessage.response_time_ms))
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.created_at >= thirty_days_ago,
            ChatMessage.response_time_ms.isnot(None),
        )
    )
    avg_response_time = await db.scalar(response_time_query)

    return AnalyticsSummary(
        total_messages=total_messages,
        active_sessions=active_sessions,
        total_tokens=total_tokens,
        avg_response_time_ms=(
            round(avg_response_time, 2) if avg_response_time else None
        ),
    )
