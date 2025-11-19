from typing import Any, Type
from pydantic import BaseModel
from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.models.responses import StandardResponse, ChatResponse

class SimpleAgent(BaseAgentFramework):
    name = "simple_agent"
    description = "A very basic agent for testing purposes."

    def __init__(self, model: str = "dummy-model", result_type: Type[BaseModel] = ChatResponse, system_prompt: str = "dummy system prompt"):
        super().__init__(
            name=self.name,
            model=model,
            result_type=result_type,
            system_prompt=system_prompt,
        )

    async def run_async(self, user_input: str, dependencies: AgentDependencies) -> StandardResponse[ChatResponse]:
        response_content = f"SimpleAgent received: '{user_input}'"
        
        if dependencies.conversation_memory:
            await dependencies.conversation_memory.add_message(role="user", content=user_input)
            response_content += f" (Session: {dependencies.conversation_memory.session_id})"
            await dependencies.conversation_memory.add_message(role="agent", content=response_content)
        
        return StandardResponse(
            data=ChatResponse(role="agent", content=response_content)
        )

    async def run_stream(self, user_input: str, dependencies: AgentDependencies) -> AsyncIterator[StandardResponse[ChatResponse]]:
        response_content = f"SimpleAgent streaming received: '{user_input}'"
        if dependencies.conversation_memory:
            response_content += f" (Session: {dependencies.conversation_memory.session_id})"
        
        chunks = response_content.split(" ")
        for i, chunk in enumerate(chunks):
            # Simulate streaming by yielding parts of the response
            yield StandardResponse(
                data=ChatResponse(role="agent", content=f"{chunk}{' ' if i < len(chunks) - 1 else ''}", metadata={"stream_part": i+1})
            )
            import asyncio
            await asyncio.sleep(0.01) # Simulate some processing time