# Task: Sessions API Backend

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create backend sessions router with CRUD endpoints, Session/Message models, and Pydantic schemas
**Sequence**: 12 of 14
**Depends On**: 11-analytics-dashboard.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `4cfd5acb-0b49-4036-85b3-4bf0b583a337`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/4cfd5acb-0b49-4036-85b3-4bf0b583a337" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/4cfd5acb-0b49-4036-85b3-4bf0b583a337" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the frontend chat components complete, we need backend persistence for chat sessions. This task creates:

- **Session Model**: SQLAlchemy model for chat sessions
- **Message Model**: SQLAlchemy model for individual messages
- **Pydantic Schemas**: Request/response validation
- **Sessions Router**: FastAPI endpoints for CRUD operations

The frontend currently uses Zustand state which is lost on refresh. These APIs will enable persistent storage.

---

## Requirements

### 1. Create Session & Message Models

Check if models exist in `src/infrastructure/database/models.py`. If not, add them:

```python
# src/infrastructure/database/models.py

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# Add to existing Base from your models file

class Session(Base):
    """Chat session model."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    agent_name = Column(String(100), default="chat")
    model_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.id}: {self.title}>"


class Message(Base):
    """Chat message model."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    model_id = Column(String(255), nullable=True)
    agent_name = Column(String(100), nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_error = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to session
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id}: {self.role}>"
```

### 2. Create Session Schemas

Create `src/api/schemas/sessions.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    images: Optional[List[str]] = Field(None, description="Base64 encoded images")
    documents: Optional[List[str]] = Field(None, description="Document filenames")


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    session_id: str
    token_count: int
    model_id: Optional[str]
    agent_name: Optional[str]
    response_time_ms: Optional[float]
    is_error: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SessionBase(BaseModel):
    """Base session schema."""
    title: Optional[str] = Field("New Chat", description="Session title")


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    agent_name: Optional[str] = Field("chat", description="Default agent for session")
    model_id: Optional[str] = Field(None, description="Default model for session")


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    title: Optional[str] = None
    agent_name: Optional[str] = None
    model_id: Optional[str] = None


class SessionSummary(BaseModel):
    """Schema for session list item."""
    id: str
    title: str
    agent_name: str
    model_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    last_message_preview: Optional[str] = None

    class Config:
        from_attributes = True


class SessionDetail(SessionSummary):
    """Schema for session detail with messages."""
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for paginated session list."""
    sessions: List[SessionSummary]
    total: int
    limit: int
    offset: int
```

### 3. Create Sessions Router

Create `src/api/routes/sessions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import uuid

from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import Session, Message
from src.api.schemas.sessions import (
    SessionCreate,
    SessionUpdate,
    SessionSummary,
    SessionDetail,
    SessionListResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


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
    query = select(Session).where(Session.user_id == user_id)

    # Apply search filter
    if search:
        query = query.where(Session.title.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get sessions with pagination
    query = query.order_by(Session.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build response with message counts
    session_summaries = []
    for session in sessions:
        # Get message count
        msg_count_query = select(func.count()).where(Message.session_id == session.id)
        msg_count = await db.scalar(msg_count_query)

        # Get last message preview
        last_msg_query = (
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_query)
        last_msg = last_msg_result.scalar_one_or_none()

        session_summaries.append(
            SessionSummary(
                id=session.id,
                title=session.title,
                agent_name=session.agent_name,
                model_id=session.model_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=msg_count,
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

    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=request.title or "New Chat",
        agent_name=request.agent_name or "chat",
        model_id=request.model_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionDetail(
        id=session.id,
        title=session.title,
        agent_name=session.agent_name,
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

    query = (
        select(Session)
        .options(selectinload(Session.messages))
        .where(Session.id == session_id, Session.user_id == user_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetail(
        id=session.id,
        title=session.title,
        agent_name=session.agent_name,
        model_id=session.model_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                token_count=msg.token_count,
                model_id=msg.model_id,
                agent_name=msg.agent_name,
                response_time_ms=msg.response_time_ms,
                is_error=msg.is_error,
                created_at=msg.created_at,
            )
            for msg in sorted(session.messages, key=lambda m: m.created_at)
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

    query = select(Session).where(Session.id == session_id, Session.user_id == user_id)
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

    session.updated_at = datetime.utcnow()

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

    query = select(Session).where(Session.id == session_id, Session.user_id == user_id)
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

    # Verify session exists and belongs to user
    session_query = select(Session).where(Session.id == session_id, Session.user_id == user_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=request.role,
        content=request.content,
        token_count=len(request.content.split()),  # Rough estimate
        created_at=datetime.utcnow(),
    )

    db.add(message)

    # Update session's updated_at
    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        token_count=message.token_count,
        model_id=message.model_id,
        agent_name=message.agent_name,
        response_time_ms=message.response_time_ms,
        is_error=message.is_error,
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

    # Verify session exists
    session_query = select(Session).where(Session.id == session_id, Session.user_id == user_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    query = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            token_count=msg.token_count,
            model_id=msg.model_id,
            agent_name=msg.agent_name,
            response_time_ms=msg.response_time_ms,
            is_error=msg.is_error,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
```

### 4. Register Sessions Router

Update `src/main.py` to include the sessions router:

```python
# In src/main.py, add import and registration

from src.api.routes import sessions  # Add this import

# Add this line with other router registrations
app.include_router(sessions.router, prefix="/api/v1")
```

### 5. Create Database Migration (if using Alembic)

If using Alembic for migrations:

```bash
cd /Users/maxwell/Projects/MAI
alembic revision --autogenerate -m "Add sessions and messages tables"
alembic upgrade head
```

If not using migrations, ensure tables are created on startup.

---

## Files to Create

- `src/api/schemas/sessions.py` - Pydantic schemas for sessions/messages
- `src/api/routes/sessions.py` - Sessions CRUD router

## Files to Modify

- `src/infrastructure/database/models.py` - Add Session and Message models (if not present)
- `src/main.py` - Register sessions router

---

## Success Criteria

```bash
# Verify sessions router exists
ls /Users/maxwell/Projects/MAI/src/api/routes/sessions.py
# Expected: File exists

# Verify schemas exist
ls /Users/maxwell/Projects/MAI/src/api/schemas/sessions.py
# Expected: File exists

# Start the backend server
cd /Users/maxwell/Projects/MAI && python -m uvicorn src.main:app --reload &

# Test list sessions endpoint
curl http://localhost:8000/api/v1/sessions
# Expected: {"sessions": [], "total": 0, ...}

# Test create session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'
# Expected: {"id": "...", "title": "Test Chat", ...}

# Test get session
curl http://localhost:8000/api/v1/sessions/{session_id}
# Expected: Session details with messages array

# Test delete session
curl -X DELETE http://localhost:8000/api/v1/sessions/{session_id}
# Expected: 204 No Content
```

**Checklist:**
- [ ] Session model with id, user_id, title, agent_name, model_id, timestamps
- [ ] Message model with id, session_id, role, content, token_count, timestamps
- [ ] Pydantic schemas for create/update/response
- [ ] GET /sessions - List with search and pagination
- [ ] POST /sessions - Create new session
- [ ] GET /sessions/{id} - Get with messages
- [ ] PATCH /sessions/{id} - Update title/agent/model
- [ ] DELETE /sessions/{id} - Delete with cascade
- [ ] POST /sessions/{id}/messages - Add message
- [ ] GET /sessions/{id}/messages - List messages

---

## Technical Notes

- **user_id**: Currently hardcoded as "default-user" - replace with auth when implemented
- **Cascade Delete**: Deleting a session removes all its messages
- **Token Count**: Rough estimate based on word count - can be improved with tiktoken
- **Pagination**: Default limit of 50 sessions, max 100

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 13-analytics-api-backend.md
