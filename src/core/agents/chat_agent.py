"""
LLM-enabled Chat Agent for MAI Framework.

This agent uses the configured LLM provider (OpenAI or LM Studio)
with intelligent fallback to echo behavior if the LLM is unavailable.
"""

import asyncio
import base64
from typing import Any, Type, AsyncIterator, Optional, List, Callable, Union

from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent, ImageUrl
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelMessage

from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.memory.context_manager import ContextWindowManager
from src.core.memory.history_processors import create_default_processor, limit_by_tokens, HistoryProcessor
from src.core.models.responses import StandardResponse, ChatResponse
from src.core.tools.models import ToolMetadata
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


def process_multimodal_message(
    message: str,
    images: List[str] | None = None,
) -> List[Union[str, BinaryContent, ImageUrl]]:
    """Convert message and images into Pydantic AI format.

    Args:
        message: Text message
        images: List of image URLs or base64 data URIs

    Returns:
        List of content items for Pydantic AI
    """
    content: List[Union[str, BinaryContent, ImageUrl]] = []

    # Always add the text message first
    if message:
        content.append(message)

    if images:
        for img in images:
            if img.startswith("data:"):
                # Base64 data URI - extract and convert
                # Format: data:image/png;base64,<base64_data>
                try:
                    header, data = img.split(",", 1)
                    media_type = header.split(":")[1].split(";")[0]
                    content.append(
                        BinaryContent(
                            data=base64.b64decode(data),
                            media_type=media_type,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse base64 image: {e}")
            else:
                # URL
                content.append(ImageUrl(url=img))

    return content if content else [message]


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

    # Context window configuration
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_RESERVE_TOKENS = 1500

    def __init__(
        self,
        name: str = "chat_agent",
        model: Optional[Model] = None,
        result_type: Type[BaseModel] = ChatResponse,
        system_prompt: str = "You are a helpful AI assistant. Be concise and helpful in your responses.",
        tools: Optional[List[tuple[Callable[..., Any], ToolMetadata]]] = None,
        history_processor: Optional[HistoryProcessor] = None,
    ):
        self._fallback_mode = model is None
        self.history_processor = history_processor

        if model is None:
            # Use TestModel for fallback mode (won't actually be called)
            model = TestModel()

        # Call parent init to set up common properties
        super().__init__(
            name=name,
            model=model,
            result_type=result_type,
            system_prompt=system_prompt,
            tools=tools,
        )

        # Override the agent to use str output_type instead of complex model
        # This fixes "Exceeded maximum retries for result validation" errors
        # because the LLM returns plain text, not structured JSON
        # Note: pydantic-ai 1.x renamed result_type to output_type
        if not self._fallback_mode:
            self.agent = Agent(
                model=self.model,
                output_type=str,  # Simple string - LLM returns text, we wrap it
                system_prompt=self.system_prompt,
                deps_type=AgentDependencies,
                retries=self.retries,
            )

    async def run_async(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
        images: Optional[List[str]] = None,
    ) -> StandardResponse[ChatResponse]:
        """Execute with LLM or fallback to echo.

        Args:
            user_input: The user's text message
            deps: Agent dependencies (redis, session_id, etc.)
            message_history: Optional message history
            images: Optional list of image URLs or base64 data URIs

        Returns:
            StandardResponse containing the ChatResponse
        """

        # Initialize conversation memory if we have Redis and session
        conversation_memory: Optional[ConversationMemory] = None
        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(
                session_id=deps.session_id, redis=deps.redis
            )
            await conversation_memory.load_from_redis()

        if self._fallback_mode:
            return await self._echo_response(user_input, deps, conversation_memory, images)

        # Try LLM, fall back to echo on failure
        try:
            # Get conversation history BEFORE adding user message
            history: Optional[List[ModelMessage]] = None
            if conversation_memory:
                # Get model name from deps or use default
                model_name = getattr(self.model, 'name', lambda: 'default')() if hasattr(self.model, 'name') else 'default'
                raw_history = conversation_memory.get_model_messages_with_limit(
                    model_name=model_name,
                    reserve_tokens=self.DEFAULT_RESERVE_TOKENS,
                )
                # Process history through the processor if configured
                history = self.history_processor(raw_history) if self.history_processor else raw_history

            # Add user message to memory
            if conversation_memory:
                await conversation_memory.add_message(role="user", content=user_input)

            # Prepare multimodal content if images are provided
            input_content: Any = user_input
            if images:
                input_content = process_multimodal_message(user_input, images)
                logger.info(f"Processing multimodal message with {len(images)} image(s)", agent=self.name)

            # Call Pydantic AI agent with message history
            result = await self.agent.run(
                input_content,
                deps=deps,
                message_history=history if history else None,
            )

            # result.output is a string (we use str as output_type)
            content = result.output

            # Add assistant response to memory
            if conversation_memory:
                await conversation_memory.add_message(role="assistant", content=content)
                # Store native model messages for future use
                await conversation_memory.add_model_messages(result.new_messages())

            logger.info("LLM response generated successfully", agent=self.name)

            return StandardResponse(
                data=ChatResponse(role="assistant", content=content)
            )

        except Exception as e:
            logger.warning(
                f"LLM call failed, falling back to echo: {e}", agent=self.name
            )
            return await self._echo_response(user_input, deps, conversation_memory, images)

    async def run_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[StandardResponse[ChatResponse]]:
        """Stream with LLM or fallback to echo.

        Args:
            user_input: The user's text message
            deps: Agent dependencies (redis, session_id, etc.)
            message_history: Optional message history
            images: Optional list of image URLs or base64 data URIs

        Yields:
            StandardResponse chunks containing ChatResponse with content deltas
        """

        # Initialize conversation memory if we have Redis and session
        conversation_memory: Optional[ConversationMemory] = None
        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(
                session_id=deps.session_id, redis=deps.redis
            )
            await conversation_memory.load_from_redis()

        if self._fallback_mode:
            async for chunk in self._echo_stream(user_input, deps, conversation_memory, images):
                yield chunk
            return

        try:
            # Get conversation history BEFORE adding user message
            history: Optional[List[ModelMessage]] = None
            if conversation_memory:
                # Get model name from deps or use default
                model_name = getattr(self.model, 'name', lambda: 'default')() if hasattr(self.model, 'name') else 'default'
                raw_history = conversation_memory.get_model_messages_with_limit(
                    model_name=model_name,
                    reserve_tokens=self.DEFAULT_RESERVE_TOKENS,
                )
                # Process history through the processor if configured
                history = self.history_processor(raw_history) if self.history_processor else raw_history

            # Add user message to memory
            if conversation_memory:
                await conversation_memory.add_message(role="user", content=user_input)

            # Prepare multimodal content if images are provided
            input_content: Any = user_input
            if images:
                input_content = process_multimodal_message(user_input, images)
                logger.info(f"Processing multimodal stream with {len(images)} image(s)", agent=self.name)

            # Stream from Pydantic AI agent with message history
            async with self.agent.run_stream(
                input_content,
                deps=deps,
                message_history=history if history else None,
            ) as result:
                # pydantic-ai 1.x stream() yields accumulated text, not deltas
                # Track previous text to extract only the new portion (delta)
                previous_text = ""
                async for chunk in result.stream():
                    accumulated = str(chunk)
                    # Extract only the new content since last chunk
                    delta = accumulated[len(previous_text):]
                    previous_text = accumulated
                    if delta:  # Only yield if there's new content
                        yield StandardResponse(
                            data=ChatResponse(role="assistant", content=delta)
                        )
                full_response = previous_text

            # Add full response to memory after streaming completes
            if conversation_memory and full_response:
                await conversation_memory.add_message(
                    role="assistant", content=full_response
                )
                # Store native model messages for future use
                await conversation_memory.add_model_messages(result.new_messages())

            logger.info("LLM streaming completed successfully", agent=self.name)

        except Exception as e:
            logger.warning(
                f"LLM streaming failed, falling back to echo: {e}", agent=self.name
            )
            async for chunk in self._echo_stream(user_input, deps, conversation_memory, images):
                yield chunk

    async def _echo_response(
        self,
        user_input: str,
        deps: AgentDependencies,
        conversation_memory: Optional[ConversationMemory] = None,
        images: Optional[List[str]] = None,
    ) -> StandardResponse[ChatResponse]:
        """Echo fallback for when LLM is unavailable."""
        image_note = f" (with {len(images)} image(s))" if images else ""
        content = f"[Echo Mode - LLM unavailable] You said: {user_input}{image_note}"

        if conversation_memory:
            await conversation_memory.add_message(role="user", content=user_input)
            await conversation_memory.add_message(role="assistant", content=content)

        return StandardResponse(data=ChatResponse(role="assistant", content=content))

    async def _echo_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        conversation_memory: Optional[ConversationMemory] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[StandardResponse[ChatResponse]]:
        """Stream echo fallback."""
        image_note = f" (with {len(images)} image(s))" if images else ""
        content = f"[Echo Mode - LLM unavailable] You said: {user_input}{image_note}"
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
