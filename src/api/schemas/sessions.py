"""Pydantic schemas for chat sessions and messages.

Schemas for:
- Session CRUD operations
- Message CRUD operations
- List/pagination responses
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Message Schemas ---


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
    response_time_ms: Optional[int]
    is_error: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Session Schemas ---


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
