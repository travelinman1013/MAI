"""API Schemas for MAI Framework."""

from src.api.schemas.agents import (
    AgentRunRequest,
    AgentStreamRequest,
    AgentRunResponse,
    AgentStreamChunk,
    ConversationHistoryResponse,
    SessionDeleteResponse,
    AgentErrorResponse,
    ToolCallInfo,
    ErrorDetail
)

__all__ = [
    "AgentRunRequest",
    "AgentStreamRequest",
    "AgentRunResponse",
    "AgentStreamChunk",
    "ConversationHistoryResponse",
    "SessionDeleteResponse",
    "AgentErrorResponse",
    "ToolCallInfo",
    "ErrorDetail"
]
