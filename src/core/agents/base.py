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
from src.core.memory.short_term import ConversationMemory

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
    conversation_memory: Optional[ConversationMemory] = None


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

    async def get_conversation_context(self, deps: AgentDependencies, limit: int = 10) -> list[dict]:
        """
        Retrieve conversation history from memory.

        Args:
            deps: AgentDependencies containing the session_id and redis client.
            limit: Max number of messages to retrieve

        Returns:
            List of messages (type depends on memory implementation)
        """
        if not deps.redis or not deps.session_id:
            self.logger.warning(
                "Cannot retrieve conversation context: Redis client or session ID not provided."
            )
            return []

        try:
            memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
            await memory.load_from_redis()
            # Convert Message objects to dictionaries for Pydantic AI agent
            history = [{"role": msg.role, "content": msg.content} for msg in memory.get_messages(last_n_messages=limit)]
            return history
        except Exception as e:
            self.logger.error(f"Failed to retrieve conversation history for session {deps.session_id}: {e}")
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

        conversation_memory: Optional[ConversationMemory] = None
        current_message_history: list[dict] = []

        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
            deps.conversation_memory = conversation_memory # Attach to deps for potential future use by agent itself

            # Load existing history from Redis into this memory instance
            await conversation_memory.load_from_redis()
            current_message_history = [{"role": msg.role, "content": msg.content} for msg in conversation_memory.get_messages()]
            self.logger.debug(f"Loaded {len(current_message_history)} messages for session {deps.session_id}")

            # Append user input to memory
            await conversation_memory.add_message("user", user_input)

        try:
            self.logger.info("Starting agent execution", input_length=len(user_input))
            
            # Execute Pydantic AI agent
            
            message_history_for_agent = None
            if conversation_memory:
                # Combine loaded history with new user input for the agent
                # Pydantic AI expects message_history as a list of dicts with role and content
                message_history_for_agent = current_message_history + [{"role": "user", "content": user_input}]
            
            result = await self.agent.run(
                user_input,
                deps=deps,
                message_history=message_history_for_agent
            )
            
            # Append agent's structured response to memory
            if conversation_memory:
                await conversation_memory.add_message("assistant", result.output.model_dump_json())
                self.logger.debug(f"Appended assistant response to session {deps.session_id}")
            
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
