from typing import Any, Type, AsyncIterator, Optional, List, Callable
from pydantic import BaseModel
from pydantic_ai.models import Model
from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.models.responses import StandardResponse, ChatResponse
from src.core.tools.models import ToolMetadata


class SimpleAgent(BaseAgentFramework):
    """A simple agent for testing the MAI framework.

    This agent echoes back user input without calling an LLM model,
    making it useful for testing the API endpoints and infrastructure.
    """

    name = "simple_agent"
    description = "A very basic agent for testing purposes."

    def __init__(
        self,
        name: str = "simple_agent",
        model: Optional[Model] = None,
        result_type: Type[BaseModel] = ChatResponse,
        system_prompt: str = "You are a helpful AI assistant.",
        tools: Optional[List[tuple[Callable[..., Any], ToolMetadata]]] = None,
    ):
        # If no model provided, use a dummy string that won't be used
        # since we override run_async to not use the model
        self._skip_model = model is None
        if model is None:
            # Use a placeholder - we won't actually use it since we override run_async
            model = "dummy-model"

        super().__init__(
            name=name,
            model=model,
            result_type=result_type,
            system_prompt=system_prompt,
            tools=tools,
        )

    async def run_async(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
    ) -> StandardResponse[ChatResponse]:
        """Execute the agent, echoing back the user input.

        This is a test implementation that doesn't use the LLM model.
        It stores messages in conversation memory if available.
        """
        response_content = f"SimpleAgent received: '{user_input}'"

        # Initialize conversation memory if we have Redis and session
        conversation_memory: Optional[ConversationMemory] = None
        if deps.redis and deps.session_id:
            conversation_memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
            await conversation_memory.load_from_redis()

            # Add user message to memory
            await conversation_memory.add_message(role="user", content=user_input)
            response_content += f" (Session: {deps.session_id})"

            # Add agent response to memory
            await conversation_memory.add_message(role="assistant", content=response_content)

        return StandardResponse(
            data=ChatResponse(role="assistant", content=response_content)
        )

    async def run_stream(
        self,
        user_input: str,
        deps: AgentDependencies,
        message_history: Optional[Any] = None,
    ) -> AsyncIterator[StandardResponse[ChatResponse]]:
        """Stream the agent response, yielding chunks.

        This is a test implementation that doesn't use the LLM model.
        """
        import asyncio

        response_content = f"SimpleAgent streaming received: '{user_input}'"
        if deps.session_id:
            response_content += f" (Session: {deps.session_id})"

        chunks = response_content.split(" ")
        for i, chunk in enumerate(chunks):
            # Simulate streaming by yielding parts of the response
            yield StandardResponse(
                data=ChatResponse(
                    role="assistant",
                    content=f"{chunk}{' ' if i < len(chunks) - 1 else ''}",
                    metadata={"stream_part": i + 1},
                )
            )
            await asyncio.sleep(0.01)  # Simulate some processing time