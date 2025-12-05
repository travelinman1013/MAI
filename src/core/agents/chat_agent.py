"""
LLM-enabled Chat Agent for MAI Framework.

This agent uses the configured LLM provider (OpenAI or LM Studio)
with intelligent fallback to echo behavior if the LLM is unavailable.
"""

import asyncio
from typing import Any, Type, AsyncIterator, Optional, List, Callable

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model

from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.models.responses import StandardResponse, ChatResponse
from src.core.tools.models import ToolMetadata
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class ChatAgent(BaseAgentFramework):
    """
    Production chat agent with LLM support and graceful fallback.

    Features:
    - Uses LM Studio or OpenAI based on configuration
    - Falls back to echo behavior if LLM unavailable
    - Full streaming support
    - Conversation memory integration
    """

    name = "chat_agent"
    description = "AI-powered chat agent using LM Studio or OpenAI"

    def __init__(
        self,
        name: str = "chat_agent",
        model: Optional[Model] = None,
        result_type: Type[BaseModel] = ChatResponse,
        system_prompt: str = "You are a helpful AI assistant. Be concise and helpful in your responses.",
        tools: Optional[List[tuple[Callable[..., Any], ToolMetadata]]] = None,
    ):
        self._fallback_mode = model is None

        if model is None:
            # Use a placeholder for fallback mode
            model = "dummy-model"

        # Call parent init to set up common properties
        super().__init__(
            name=name,
            model=model,
            result_type=result_type,
            system_prompt=system_prompt,
            tools=tools,
        )

        # Override the agent to use str result_type instead of complex model
        # This fixes "Exceeded maximum retries for result validation" errors
        # because the LLM returns plain text, not structured JSON
        if not self._fallback_mode:
            self.agent = Agent(
                model=self.model,
                result_type=str,  # Simple string - LLM returns text, we wrap it
                system_prompt=self.system_prompt,
                deps_type=AgentDependencies,
                retries=self.retries,
            )

    async def run_async(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
    ) -> StandardResponse[ChatResponse]:
        """Execute with LLM or fallback to echo."""

        # Initialize conversation memory if we have Redis and session
        conversation_memory: Optional[ConversationMemory] = None
        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(
                session_id=deps.session_id, redis=deps.redis
            )
            await conversation_memory.load_from_redis()

        if self._fallback_mode:
            return await self._echo_response(user_input, deps, conversation_memory)

        # Try LLM, fall back to echo on failure
        try:
            # Add user message to memory before LLM call
            if conversation_memory:
                await conversation_memory.add_message(role="user", content=user_input)

            # Get conversation history for context
            current_history = []
            if conversation_memory:
                messages = conversation_memory.get_messages()
                # Convert to pydantic-ai format (excluding current user message we just added)
                for msg in messages[:-1]:  # Exclude the message we just added
                    current_history.append({"role": msg.role, "content": msg.content})

            # Call Pydantic AI agent - it returns a RunResult with .data containing the output
            # Note: message_history requires proper ModelMessage objects, not plain dicts
            # For now, we don't pass history - the LLM context comes from system prompt
            result = await self.agent.run(
                user_input,
                deps=deps,
                message_history=None,  # TODO: convert to ModelMessage format if needed
            )

            # result.data is now a string (we use str as result_type)
            content = result.data

            # Add assistant response to memory
            if conversation_memory:
                await conversation_memory.add_message(role="assistant", content=content)

            logger.info("LLM response generated successfully", agent=self.name)

            return StandardResponse(
                data=ChatResponse(role="assistant", content=content)
            )

        except Exception as e:
            logger.warning(
                f"LLM call failed, falling back to echo: {e}", agent=self.name
            )
            return await self._echo_response(user_input, deps, conversation_memory)

    async def run_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
    ) -> AsyncIterator[StandardResponse[ChatResponse]]:
        """Stream with LLM or fallback to echo."""

        # Initialize conversation memory if we have Redis and session
        conversation_memory: Optional[ConversationMemory] = None
        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(
                session_id=deps.session_id, redis=deps.redis
            )
            await conversation_memory.load_from_redis()

        if self._fallback_mode:
            async for chunk in self._echo_stream(user_input, deps, conversation_memory):
                yield chunk
            return

        try:
            # Add user message to memory before LLM call
            if conversation_memory:
                await conversation_memory.add_message(role="user", content=user_input)

            # Get conversation history for context
            current_history = []
            if conversation_memory:
                current_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in conversation_memory.get_messages()
                ]

            # Stream from Pydantic AI agent
            # Note: message_history requires proper ModelMessage objects, not dicts
            # For now, we don't pass history to streaming - the LLM context comes from system prompt
            full_response = ""
            async with self.agent.run_stream(
                user_input,
                deps=deps,
                message_history=None,  # TODO: convert to ModelMessage format if needed
            ) as result:
                async for chunk in result.stream():
                    chunk_str = str(chunk)
                    full_response += chunk_str
                    yield StandardResponse(
                        data=ChatResponse(role="assistant", content=chunk_str)
                    )

            # Add full response to memory after streaming completes
            if conversation_memory and full_response:
                await conversation_memory.add_message(
                    role="assistant", content=full_response
                )

            logger.info("LLM streaming completed successfully", agent=self.name)

        except Exception as e:
            logger.warning(
                f"LLM streaming failed, falling back to echo: {e}", agent=self.name
            )
            async for chunk in self._echo_stream(user_input, deps, conversation_memory):
                yield chunk

    async def _echo_response(
        self,
        user_input: str,
        deps: AgentDependencies,
        conversation_memory: Optional[ConversationMemory] = None,
    ) -> StandardResponse[ChatResponse]:
        """Echo fallback for when LLM is unavailable."""
        content = f"[Echo Mode - LLM unavailable] You said: {user_input}"

        if conversation_memory:
            await conversation_memory.add_message(role="user", content=user_input)
            await conversation_memory.add_message(role="assistant", content=content)

        return StandardResponse(data=ChatResponse(role="assistant", content=content))

    async def _echo_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        conversation_memory: Optional[ConversationMemory] = None,
    ) -> AsyncIterator[StandardResponse[ChatResponse]]:
        """Stream echo fallback."""
        content = f"[Echo Mode - LLM unavailable] You said: {user_input}"
        words = content.split(" ")

        # Add to memory at the start
        if conversation_memory:
            await conversation_memory.add_message(role="user", content=user_input)
            await conversation_memory.add_message(role="assistant", content=content)

        for i, word in enumerate(words):
            yield StandardResponse(
                data=ChatResponse(
                    role="assistant",
                    content=f"{word}{' ' if i < len(words) - 1 else ''}",
                )
            )
            await asyncio.sleep(0.03)
