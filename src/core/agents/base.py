"""
Base Agent Framework for MAI.

This module provides the base class for all agents in the framework,
integrating Pydantic AI with the MAI infrastructure (logging, auth, memory).
"""

from typing import Any, Generic, AsyncIterator, TypeVar, Optional
from dataclasses import dataclass
import contextvars
import time

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.utils.logging import get_logger_with_context
from src.core.utils.config import Settings, get_settings
from src.core.utils.exceptions import AgentExecutionError, ConfigurationError
from src.infrastructure.cache.redis_client import RedisClient
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

# Define generic type for result
ResultT = TypeVar("ResultT", bound=BaseModel)


@dataclass
class AgentDependencies:
    """Dependencies available to agents during execution."""
    db: Optional[AsyncSession] = None
    redis: Optional[RedisClient] = None
    qdrant: Optional[QdrantVectorStore] = None
    settings: Optional[Settings] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_name: Optional[str] = None


class BaseAgentFramework(Generic[ResultT]):
    """
    Base class for AI agents in MAI Framework.

    Provides common functionality for all agents including:
    - System prompt management
    - Tool registration
    - Dependency injection
    - Result validation
    - Logging and metrics
    """

    def __init__(
        self,
        name: str,
        model: Model | Any,
        result_type: type[ResultT],
        system_prompt: str,
        retries: int = 3,
    ):
        """
        Initialize the agent framework.

        Args:
            name: Unique name of the agent
            model: Pydantic AI model instance (e.g. OpenAIModel)
            result_type: Pydantic model class for structured output
            system_prompt: System instructions for the agent
            retries: Number of retries for failed executions
        """
        self.name = name
        self.model = model
        self.result_type = result_type
        self.system_prompt = system_prompt
        self.retries = retries
        self.logger = get_logger_with_context(agent_name=name)
        
        # Initialize Pydantic AI Agent
        # We use AgentDependencies as the dependency type
        self.agent = Agent(
            model=self.model,
            output_type=self.result_type,
            system_prompt=self.system_prompt,
            deps_type=AgentDependencies,
            retries=self.retries
        )

    def validate_dependencies(self, deps: AgentDependencies) -> None:
        """
        Validate that required dependencies are present.
        
        Override this method in subclasses to enforce specific dependency requirements.
        """
        if not deps:
             raise ConfigurationError("Dependencies object cannot be None")

    async def get_conversation_context(self, session_id: str, limit: int = 10) -> list[Any]:
        """
        Retrieve conversation history from memory.
        
        Args:
            session_id: The conversation session ID
            limit: Max number of messages to retrieve
            
        Returns:
            List of messages (type depends on memory implementation)
        """
        # TODO: Implement connection to ShortTermMemory when available
        # For now, return empty list or implement basic Redis retrieval if needed directly
        # This is a placeholder as per the task order (Memory is next)
        return []

    def log_execution(self, start_time: float, success: bool, error: Optional[Exception] = None) -> None:
        """Log execution metrics and status."""
        duration = time.time() - start_time
        
        if success:
            self.logger.info(
                "Agent execution completed successfully",
                duration_seconds=duration,
                agent_name=self.name
            )
        else:
            self.logger.error(
                "Agent execution failed",
                duration_seconds=duration,
                agent_name=self.name,
                error=str(error) if error else "Unknown error"
            )

    async def run_async(
        self, 
        user_input: str, 
        deps: AgentDependencies,
        message_history: Optional[list[Any]] = None
    ) -> ResultT:
        """
        Execute the agent asynchronously.

        Args:
            user_input: The user's prompt/question
            deps: Dependencies to inject (DB, Redis, etc.)
            message_history: Optional history of messages

        Returns:
            Structured result of type ResultT

        Raises:
            AgentExecutionError: If execution fails after retries
        """
        start_time = time.time()
        self.validate_dependencies(deps)
        
        # Update logger context with runtime info
        if deps.user_id:
            # contextvars could be used here if logger supports it, 
            # but we initialized logger with agent_name already.
            pass

        try:
            self.logger.info("Starting agent execution", input_length=len(user_input))
            
            # Execute Pydantic AI agent
            # message_history can be passed if Pydantic AI supports it in run() 
            # currently Pydantic AI manages history via its own mechanisms or we pass it 
            # In this base implementation, we trust the agent's internal history management 
            # or explicit history passing if supported.
            
            result = await self.agent.run(
                user_input,
                deps=deps,
                message_history=message_history
            )
            
            self.log_execution(start_time, True)
            return result.output

        except Exception as e:
            self.log_execution(start_time, False, e)
            raise AgentExecutionError(
                f"Agent '{self.name}' failed to execute: {str(e)}",
                details={"input": user_input}
            ) from e

    async def run_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[list[Any]] = None
    ) -> AsyncIterator[Any]:
        """
        Execute the agent with streaming response.
        
        Note: Pydantic AI streaming might return partial structures or text.
        """
        start_time = time.time()
        self.validate_dependencies(deps)

        try:
            self.logger.info("Starting agent streaming execution")
            
            async with self.agent.run_stream(
                user_input,
                deps=deps,
                message_history=message_history
            ) as result:
                async for chunk in result.stream():
                    yield chunk
            
            self.log_execution(start_time, True)

        except Exception as e:
            self.log_execution(start_time, False, e)
            raise AgentExecutionError(
                f"Agent '{self.name}' stream failed: {str(e)}"
            ) from e

    def run(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[list[Any]] = None
    ) -> ResultT:
        """Synchronous wrapper for run_async."""
        import asyncio
        return asyncio.run(self.run_async(user_input, deps, message_history))
