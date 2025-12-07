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
from src.api.schemas.analytics import (
    UsageDataPoint,
    UsageStats,
    AgentStats,
    AgentInsights,
    ModelStats,
    ModelUsage,
    AnalyticsSummary,
)
from src.api.schemas.messages import (
    TextContent,
    ImageContent,
    MessageContent,
    MultimodalMessage,
)
from src.api.schemas.sessions import (
    MessageBase,
    MessageCreate,
    MessageResponse,
    SessionBase,
    SessionCreate,
    SessionUpdate,
    SessionSummary,
    SessionDetail,
    SessionListResponse,
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
    "ErrorDetail",
    # Analytics schemas
    "UsageDataPoint",
    "UsageStats",
    "AgentStats",
    "AgentInsights",
    "ModelStats",
    "ModelUsage",
    "AnalyticsSummary",
    # Message schemas
    "TextContent",
    "ImageContent",
    "MessageContent",
    "MultimodalMessage",
    # Session schemas
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionSummary",
    "SessionDetail",
    "SessionListResponse",
]
