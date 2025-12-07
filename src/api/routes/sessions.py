"""Sessions API router for chat session CRUD operations.

Endpoints:
- GET /sessions - List sessions with search and pagination
- POST /sessions - Create a new session
- GET /sessions/{id} - Get session details with messages
- PATCH /sessions/{id} - Update session title/settings
- DELETE /sessions/{id} - Delete session and messages
- POST /sessions/{id}/messages - Add message to session
- GET /sessions/{id}/messages - List messages for session
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.sessions import (
    MessageCreate,
    MessageResponse,
    SessionCreate,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    SessionUpdate,
)
from src.infrastructure.database.models import ChatMessage, ChatSession
from src.infrastructure.database.session import get_db

router = APIRouter()


def get_current_user_id() -> str:
    """Get current user ID. Replace with actual auth when implemented."""
    return "default-user"


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    search: Optional[str] = Query(None, description="Search sessions by title"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions with pagination and search."""
    user_id = get_current_user_id()

    # Base query
    query = select(ChatSession).where(ChatSession.user_id == user_id)

    # Apply search filter
    if search:
        query = query.where(ChatSession.title.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get sessions with pagination
    query = query.order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build response with message counts
    session_summaries = []
    for session in sessions:
        # Get message count
        msg_count_query = select(func.count()).where(
            ChatMessage.session_id == session.id
        )
        msg_count = await db.scalar(msg_count_query)

        # Get last message preview
        last_msg_query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_query)
        last_msg = last_msg_result.scalar_one_or_none()

        session_summaries.append(
            SessionSummary(
                id=str(session.id),
                title=session.title or "New Chat",
                agent_name=session.agent_name or "chat",
                model_id=session.model_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=msg_count or 0,
                last_message_preview=last_msg.content[:100] if last_msg else None,
            )
        )

    return SessionListResponse(
        sessions=session_summaries,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=SessionDetail, status_code=201)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    user_id = get_current_user_id()

    session = ChatSession(
        id=uuid.uuid4(),
        user_id=user_id,
        title=request.title or "New Chat",
        agent_name=request.agent_name or "chat",
        model_id=request.model_id,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionDetail(
        id=str(session.id),
        title=session.title or "New Chat",
        agent_name=session.agent_name or "chat",
        model_id=session.model_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[],
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get session details with messages."""
    user_id = get_current_user_id()

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    query = (
        select(ChatSession)
        .options(selectinload(ChatSession.chat_messages))
        .where(ChatSession.id == session_uuid, ChatSession.user_id == user_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetail(
        id=str(session.id),
        title=session.title or "New Chat",
        agent_name=session.agent_name or "chat",
        model_id=session.model_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.chat_messages),
        messages=[
            MessageResponse(
                id=str(msg.id),
                session_id=str(msg.session_id),
                role=msg.role,
                content=msg.content,
                token_count=msg.token_count or 0,
                model_id=msg.model_id,
                agent_name=msg.agent_name,
                response_time_ms=msg.response_time_ms,
                is_error=msg.is_error or False,
                created_at=msg.created_at,
            )
            for msg in sorted(session.chat_messages, key=lambda m: m.created_at)
        ],
    )


@router.patch("/{session_id}", response_model=SessionDetail)
async def update_session(
    session_id: str,
    request: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update session title or settings."""
    user_id = get_current_user_id()

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    query = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update fields if provided
    if request.title is not None:
        session.title = request.title
    if request.agent_name is not None:
        session.agent_name = request.agent_name
    if request.model_id is not None:
        session.model_id = request.model_id

    await db.commit()
    await db.refresh(session)

    # Fetch with messages
    return await get_session(session_id, db)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all its messages."""
    user_id = get_current_user_id()

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    query = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Messages will be cascade deleted
    await db.delete(session)
    await db.commit()


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    session_id: str,
    request: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a message to a session."""
    user_id = get_current_user_id()

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    # Verify session exists and belongs to user
    session_query = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == user_id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Estimate token count (rough approximation: ~4 chars per token)
    token_count = len(request.content) // 4

    message = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_uuid,
        role=request.role,
        content=request.content,
        token_count=token_count,
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=str(message.id),
        session_id=str(message.session_id),
        role=message.role,
        content=message.content,
        token_count=message.token_count or 0,
        model_id=message.model_id,
        agent_name=message.agent_name,
        response_time_ms=message.response_time_ms,
        is_error=message.is_error or False,
        created_at=message.created_at,
    )


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a session."""
    user_id = get_current_user_id()

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    # Verify session exists
    session_query = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == user_id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_uuid)
        .order_by(ChatMessage.created_at)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            content=msg.content,
            token_count=msg.token_count or 0,
            model_id=msg.model_id,
            agent_name=msg.agent_name,
            response_time_ms=msg.response_time_ms,
            is_error=msg.is_error or False,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
