"""Database models for MAI Framework.

Models:
- User: User accounts and authentication
- UserSession: User sessions with authentication
- Conversation: Conversation threads
- Message: Individual messages in conversations
- ChatSession: Frontend chat session persistence
- ChatMessage: Messages within chat sessions
- Memory: Memory storage with vector embeddings (pgvector)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.database.base import BaseModel


class User(BaseModel):
    """User model for authentication and identification.

    Attributes:
        username: Unique username.
        email: User email address.
        hashed_password: Bcrypt hashed password.
        is_active: Whether user account is active.
        is_superuser: Whether user has admin privileges.
        full_name: User's full name (optional).
        sessions: User's authentication sessions.
        conversations: User's conversation threads.
        memories: User's stored memories.
    """

    __tablename__ = "users"

    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    full_name = Column(String(255), nullable=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")


class UserSession(BaseModel):
    """User session model for JWT token management.

    Attributes:
        user_id: Foreign key to User.
        access_token: JWT access token (hashed).
        refresh_token: JWT refresh token (hashed).
        expires_at: Token expiration timestamp.
        is_revoked: Whether session is revoked.
        ip_address: Client IP address.
        user_agent: Client user agent.
        user: Related user.
    """

    __tablename__ = "user_sessions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_user_sessions_user_expires", "user_id", "expires_at"),
        Index("idx_user_sessions_revoked", "is_revoked", "expires_at"),
    )


class Conversation(BaseModel):
    """Conversation model for chat threads.

    Attributes:
        user_id: Foreign key to User.
        agent_name: Name of the agent used in conversation.
        title: Conversation title (auto-generated or user-provided).
        is_archived: Whether conversation is archived.
        metadata: Additional metadata (JSON).
        user: Related user.
        messages: Messages in this conversation.
    """

    __tablename__ = "conversations"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    extra_metadata = Column(Text, nullable=True)  # JSON stored as text

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_conversations_user_archived", "user_id", "is_archived", "created_at"),
    )


class Message(BaseModel):
    """Message model for individual chat messages.

    Attributes:
        conversation_id: Foreign key to Conversation.
        role: Message role (user, assistant, system, tool).
        content: Message content.
        tool_name: Tool name (if role is tool).
        tool_result: Tool execution result (if role is tool).
        metadata: Additional metadata (JSON).
        conversation: Related conversation.
    """

    __tablename__ = "messages"

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False, index=True)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_name = Column(String(255), nullable=True, index=True)
    tool_result = Column(Text, nullable=True)
    extra_metadata = Column(Text, nullable=True)  # JSON stored as text

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_role", "role", "created_at"),
    )


class ChatSession(BaseModel):
    """Chat session model for frontend chat persistence.

    Attributes:
        user_id: User identifier (string for flexibility before auth).
        title: Session title (auto-generated or user-provided).
        agent_name: Name of the agent used in session.
        model_id: Model identifier used for the session.
        chat_messages: Messages in this session.
    """

    __tablename__ = "chat_sessions"

    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    agent_name = Column(String(100), default="chat", index=True)
    model_id = Column(String(255), nullable=True)

    # Relationships
    chat_messages = relationship(
        "ChatMessage", back_populates="chat_session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ChatSession {self.id}: {self.title}>"


class ChatMessage(BaseModel):
    """Chat message model for individual messages in a chat session.

    Attributes:
        session_id: Foreign key to ChatSession.
        role: Message role (user, assistant, system).
        content: Message content.
        token_count: Estimated token count.
        model_id: Model that generated this message (for assistant).
        agent_name: Agent that processed this message.
        response_time_ms: Response time in milliseconds.
        is_error: Whether this message represents an error.
        chat_session: Related chat session.
    """

    __tablename__ = "chat_messages"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    model_id = Column(String(255), nullable=True)
    agent_name = Column(String(100), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    is_error = Column(Boolean, default=False)

    # Relationships
    chat_session = relationship("ChatSession", back_populates="chat_messages")

    # Indexes
    __table_args__ = (
        Index("idx_chat_messages_session_created", "session_id", "created_at"),
    )

    def __repr__(self):
        return f"<ChatMessage {self.id}: {self.role}>"


class Memory(BaseModel):
    """Memory model with vector embeddings for semantic search.

    Attributes:
        user_id: Foreign key to User.
        agent_name: Agent that created the memory.
        content: Memory content.
        memory_type: Type of memory (short_term, long_term, semantic).
        importance: Importance score (0.0 to 1.0).
        embedding: Vector embedding for semantic search (pgvector).
        metadata: Additional metadata (JSON).
        accessed_count: Number of times memory was accessed.
        last_accessed_at: Last access timestamp.
        user: Related user.
    """

    __tablename__ = "memories"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(
        String(50), nullable=False, index=True
    )  # short_term, long_term, semantic
    importance = Column(Integer, default=0, nullable=False, index=True)  # 0-100
    qdrant_id = Column(UUID(as_uuid=True), unique=True, nullable=True, index=True) # Link to Qdrant entry
    extra_metadata = Column(Text, nullable=True)  # JSON stored as text
    accessed_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="memories")

    # Indexes
    __table_args__ = (
        Index("idx_memories_user_type", "user_id", "memory_type", "created_at"),
        Index("idx_memories_importance", "importance", "created_at"),
        Index("idx_memories_agent", "agent_name", "created_at"),
        Index("idx_memories_qdrant_id", "qdrant_id"),
    )
