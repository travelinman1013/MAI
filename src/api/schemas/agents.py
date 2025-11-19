"""
API Schemas for Agent Endpoints.

This module defines request and response models for agent execution endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


# ===== Request Schemas =====


class AgentRunRequest(BaseModel):
    """Request schema for running an agent."""

    user_input: str = Field(
        ...,
        description="The user's input message to the agent.",
        min_length=1,
        max_length=10000
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for multi-turn conversations. If provided, conversation history will be loaded from Redis."
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user ID for user-specific context and memory."
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional configuration overrides for this specific run (e.g., temperature, max_tokens)."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "What is the weather like today?",
                "session_id": "session_abc123",
                "user_id": "user_xyz789",
                "config": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
        }


class AgentStreamRequest(BaseModel):
    """Request schema for streaming agent responses."""

    user_input: str = Field(
        ...,
        description="The user's input message to the agent.",
        min_length=1,
        max_length=10000
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for multi-turn conversations."
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user ID for user-specific context."
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional configuration overrides."
    )


# ===== Response Schemas =====


class ToolCallInfo(BaseModel):
    """Information about a tool call made during agent execution."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    arguments: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    result: Any = Field(..., description="Result returned by the tool")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    success: bool = Field(..., description="Whether the tool call succeeded")
    error: Optional[str] = Field(None, description="Error message if the tool call failed")


class AgentRunResponse(BaseModel):
    """Response schema for agent execution."""

    success: bool = Field(..., description="Whether the agent execution succeeded")
    agent_name: str = Field(..., description="Name of the agent that was executed")
    session_id: Optional[str] = Field(None, description="Session ID if provided")
    result: Dict[str, Any] = Field(..., description="Structured result from the agent")
    tool_calls: List[ToolCallInfo] = Field(
        default_factory=list,
        description="List of tool calls made during execution"
    )
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the response")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "agent_name": "weather_agent",
                "session_id": "session_abc123",
                "result": {
                    "role": "assistant",
                    "content": "The weather today is sunny with a high of 72°F."
                },
                "tool_calls": [
                    {
                        "tool_name": "get_weather",
                        "arguments": {"location": "San Francisco"},
                        "result": {"temperature": 72, "condition": "sunny"},
                        "duration_ms": 150.5,
                        "success": True,
                        "error": None
                    }
                ],
                "execution_time_ms": 1250.0,
                "timestamp": "2025-11-19T19:30:00Z"
            }
        }


class AgentStreamChunk(BaseModel):
    """Schema for a single chunk in a streaming response."""

    content: str = Field(..., description="Chunk of content being streamed")
    done: bool = Field(False, description="Whether this is the final chunk")
    tool_call: Optional[ToolCallInfo] = Field(None, description="Tool call information if this chunk represents a tool call")


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history retrieval."""

    success: bool = Field(..., description="Whether the retrieval succeeded")
    session_id: str = Field(..., description="Session ID for the conversation")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in the conversation")
    message_count: int = Field(..., description="Total number of messages")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "session_abc123",
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": "2025-11-19T19:25:00Z"},
                    {"role": "assistant", "content": "Hi! How can I help you?", "timestamp": "2025-11-19T19:25:01Z"}
                ],
                "message_count": 2
            }
        }


class SessionDeleteResponse(BaseModel):
    """Response schema for session deletion."""

    success: bool = Field(..., description="Whether the deletion succeeded")
    session_id: str = Field(..., description="Session ID that was deleted")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "session_abc123",
                "message": "Session deleted successfully"
            }
        }


class ErrorDetail(BaseModel):
    """Detailed error information."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retryable: bool = Field(False, description="Whether the error is retryable")


class AgentErrorResponse(BaseModel):
    """Error response schema for agent endpoints."""

    success: bool = Field(False, description="Always False for error responses")
    error: ErrorDetail = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the error")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "error_code": "AGENT_EXECUTION_ERROR",
                    "message": "Agent failed to execute due to model timeout",
                    "details": {"timeout_seconds": 30},
                    "retryable": True
                },
                "timestamp": "2025-11-19T19:30:00Z"
            }
        }
