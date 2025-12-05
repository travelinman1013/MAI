"""
Agent API Routes.

This module implements the FastAPI endpoints for agent execution,
streaming, and session management.
"""

import time
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime

from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.utils.auth import get_current_user
from src.core.utils.exceptions import AgentExecutionError, ResourceNotFoundError
from src.core.utils.logging import get_logger_with_context
from src.infrastructure.cache.redis_client import get_redis_client
from src.core.agents.registry import agent_registry
from src.core.tools.registry import tool_registry
from src.core.models.responses import ChatResponse
from src.core.models.providers import get_model_provider_async
from src.api.schemas.agents import (
    AgentRunRequest,
    AgentStreamRequest,
    AgentRunResponse,
    AgentStreamChunk,
    ConversationHistoryResponse,
    SessionDeleteResponse,
    AgentErrorResponse,
    ErrorDetail,
    ToolCallInfo
)

router = APIRouter()
logger = get_logger_with_context(module="agent_routes")


@router.get(
    "/",
    summary="List all agents",
    description="Get a list of all registered agents with their descriptions."
)
async def list_agents():
    """
    List all available agents.

    Returns list of agent names and descriptions.
    """
    try:
        agents_dict = agent_registry.list_agents()

        agents_list = []
        for name, agent_class in agents_dict.items():
            agents_list.append({
                "name": name,
                "description": getattr(agent_class, "description", "No description"),
            })

        return {
            "success": True,
            "agents": agents_list,
            "count": len(agents_list)
        }

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "AGENT_LIST_ERROR", "message": str(e)}
        )


async def _create_agent_instance(
    agent_name: str,
    tools_enabled: bool = True,
    require_model: bool = False,
) -> BaseAgentFramework:
    """
    Create an agent instance with proper model and tool configuration.

    Args:
        agent_name: Name of the agent to create
        tools_enabled: Whether to load and register tools with the agent
        require_model: If True, require a valid LLM model; if False, model is optional

    Returns:
        Configured agent instance

    Raises:
        ValueError: If agent not found in registry
        ModelError: If LM Studio model creation fails and require_model is True
    """
    # Get agent class from registry
    AgentClass = agent_registry.get_agent(agent_name)
    if not AgentClass:
        raise ValueError(f"Agent '{agent_name}' not found in registry")

    # Try to get model from configured provider (OpenAI or LM Studio)
    # Some agents (like SimpleAgent) don't need a real model
    model = None
    try:
        model = await get_model_provider_async()
    except Exception as e:
        if require_model:
            raise
        logger.warning(
            f"Could not create model provider for agent '{agent_name}': {e}. "
            "Agent will run without LLM model."
        )

    # Get tools if enabled
    tools = None
    if tools_enabled:
        all_tools = tool_registry.list_all_tools()
        if all_tools:
            tools = all_tools
            logger.info(f"Loaded {len(tools)} tools for agent '{agent_name}'", tool_count=len(tools))

    # Create agent instance
    # Note: AgentClass should have a factory method or accept these parameters
    agent_instance = AgentClass(
        name=agent_name,
        model=model,
        result_type=ChatResponse,
        system_prompt=f"You are a helpful AI assistant named {agent_name}.",
        tools=tools,
    )

    return agent_instance


@router.post(
    "/run/{agent_name}",
    response_model=AgentRunResponse,
    summary="Execute an agent",
    description="Run a single agent interaction with optional session management and tool execution."
)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    current_user: str = Depends(get_current_user)
) -> AgentRunResponse:
    """
    Execute an agent with the provided input.

    - **agent_name**: Name of the agent to execute
    - **user_input**: The user's message/query
    - **session_id**: Optional session ID for conversation history
    - **user_id**: Optional user ID for user-specific context
    - **config**: Optional configuration overrides

    Returns structured response with agent result and tool call information.
    """
    start_time = time.time()

    try:
        logger.info(
            f"Agent run request received",
            agent_name=agent_name,
            user=current_user,
            session_id=request.session_id,
            has_config=request.config is not None
        )

        # Get Redis client
        redis_client = await get_redis_client()

        # Create agent instance
        agent_instance = await _create_agent_instance(agent_name, tools_enabled=True)

        # Set up dependencies
        deps = AgentDependencies(
            redis=redis_client,
            session_id=request.session_id,
            user_id=request.user_id or current_user,
            agent_name=agent_name
        )

        # Execute agent
        result = await agent_instance.run_async(
            user_input=request.user_input,
            deps=deps
        )

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        # Build response
        response = AgentRunResponse(
            success=True,
            agent_name=agent_name,
            session_id=request.session_id,
            result=result.model_dump() if hasattr(result, 'model_dump') else {"data": str(result)},
            tool_calls=[],  # TODO: Extract tool calls from execution
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow()
        )

        logger.info(
            f"Agent execution completed successfully",
            agent_name=agent_name,
            execution_time_ms=execution_time_ms
        )

        return response

    except ValueError as e:
        logger.error(f"Agent not found: {agent_name}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "AGENT_NOT_FOUND", "message": str(e)}
        )

    except AgentExecutionError as e:
        logger.error(f"Agent execution failed: {agent_name}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "AGENT_EXECUTION_ERROR",
                "message": str(e),
                "retryable": True
            }
        )

    except Exception as e:
        import traceback
        logger.error(
            f"Unexpected error in agent execution",
            agent_name=agent_name,
            error=str(e),
            traceback=traceback.format_exc()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"An unexpected error occurred: {str(e)}",
                "retryable": False
            }
        )


@router.post(
    "/stream/{agent_name}",
    summary="Stream agent responses",
    description="Execute an agent with Server-Sent Events (SSE) streaming for real-time responses."
)
async def stream_agent(
    agent_name: str,
    request: AgentStreamRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Stream agent responses using Server-Sent Events.

    - **agent_name**: Name of the agent to execute
    - **user_input**: The user's message/query
    - **session_id**: Optional session ID for conversation history
    - **user_id**: Optional user ID for user-specific context
    - **config**: Optional configuration overrides

    Returns a stream of chunks as they are generated.
    """
    try:
        logger.info(
            f"Agent stream request received",
            agent_name=agent_name,
            user=current_user,
            session_id=request.session_id
        )

        # Get Redis client
        redis_client = await get_redis_client()

        # Create agent instance
        agent_instance = await _create_agent_instance(agent_name, tools_enabled=True)

        # Set up dependencies
        deps = AgentDependencies(
            redis=redis_client,
            session_id=request.session_id,
            user_id=request.user_id or current_user,
            agent_name=agent_name
        )

        # Generator function for streaming
        async def event_generator():
            try:
                full_response = ""
                chunk_count = 0

                # Stream from agent
                async for chunk in agent_instance.run_stream(
                    user_input=request.user_input,
                    deps=deps
                ):
                    chunk_count += 1

                    # Extract content from chunk
                    # StandardResponse has data.content, ChatResponse has content directly
                    if hasattr(chunk, 'data') and hasattr(chunk.data, 'content'):
                        content = chunk.data.content
                    elif hasattr(chunk, 'content'):
                        content = chunk.content
                    elif hasattr(chunk, 'data'):
                        content = chunk.data.get('content', '') if isinstance(chunk.data, dict) else str(chunk.data)
                    else:
                        content = str(chunk)

                    full_response += content

                    # Create chunk response
                    chunk_data = AgentStreamChunk(
                        content=content,
                        done=False
                    )

                    # Send as SSE
                    yield f"data: {chunk_data.model_dump_json()}\n\n"

                # Send final chunk
                final_chunk = AgentStreamChunk(
                    content="",
                    done=True
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"

                logger.info(
                    f"Agent streaming completed",
                    agent_name=agent_name,
                    chunk_count=chunk_count,
                    response_length=len(full_response)
                )

            except Exception as e:
                logger.error(f"Error during streaming", agent_name=agent_name, error=str(e))
                error_chunk = AgentStreamChunk(
                    content=f"Error: {str(e)}",
                    done=True
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except ValueError as e:
        logger.error(f"Agent not found: {agent_name}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "AGENT_NOT_FOUND", "message": str(e)}
        )

    except Exception as e:
        logger.error(f"Unexpected error in agent streaming", agent_name=agent_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        )


@router.get(
    "/history/{session_id}",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Retrieve the conversation history for a specific session."
)
async def get_conversation_history(
    session_id: str,
    current_user: str = Depends(get_current_user),
    limit: Optional[int] = None
) -> ConversationHistoryResponse:
    """
    Retrieve conversation history for a session.

    - **session_id**: The session ID to retrieve history for
    - **limit**: Optional limit on number of messages to return

    Returns the conversation messages for the session.
    """
    try:
        logger.info(f"Retrieving conversation history", session_id=session_id, user=current_user)

        # Get Redis client
        redis_client = await get_redis_client()

        # Load conversation memory
        memory = ConversationMemory(session_id=session_id, redis=redis_client)
        await memory.load_from_redis()

        # Get messages
        messages = memory.get_messages(last_n_messages=limit)

        # Convert to dict format
        message_dicts = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            }
            for msg in messages
        ]

        return ConversationHistoryResponse(
            success=True,
            session_id=session_id,
            messages=message_dicts,
            message_count=len(message_dicts)
        )

    except Exception as e:
        logger.error(f"Error retrieving conversation history", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "HISTORY_RETRIEVAL_ERROR",
                "message": str(e)
            }
        )


@router.delete(
    "/history/{session_id}",
    response_model=SessionDeleteResponse,
    summary="Delete conversation session",
    description="Delete all conversation history for a specific session."
)
async def delete_conversation_session(
    session_id: str,
    current_user: str = Depends(get_current_user)
) -> SessionDeleteResponse:
    """
    Delete a conversation session and all its history.

    - **session_id**: The session ID to delete

    Returns confirmation of deletion.
    """
    try:
        logger.info(f"Deleting conversation session", session_id=session_id, user=current_user)

        # Get Redis client
        redis_client = await get_redis_client()

        # Delete session data from Redis
        # Note: The key uses ConversationMemory.REDIS_KEY_PREFIX = "conversation_memory:"
        # The RedisClient will add "MAI:" prefix, so we just use the memory key format
        session_key = f"conversation_memory:{session_id}"
        deleted = await redis_client.delete(session_key)

        if deleted:
            logger.info(f"Session deleted successfully", session_id=session_id)
            return SessionDeleteResponse(
                success=True,
                session_id=session_id,
                message="Session deleted successfully"
            )
        else:
            logger.warning(f"Session not found", session_id=session_id)
            return SessionDeleteResponse(
                success=True,
                session_id=session_id,
                message="Session not found (may have already been deleted)"
            )

    except Exception as e:
        logger.error(f"Error deleting conversation session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SESSION_DELETE_ERROR",
                "message": str(e)
            }
        )
