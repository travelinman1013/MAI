
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse # Import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.core.utils.auth import get_current_user
from src.infrastructure.cache.redis_client import get_redis_client 
from src.core.agents.registry import agent_registry 
from src.core.models.responses import ChatResponse # Import ChatResponse

router = APIRouter()

class AgentInput(BaseModel):
    session_id: Optional[str] = Field(None, description="Optional session ID for multi-turn conversations.")
    user_input: str = Field(..., description="The user's input message to the agent.")
    agent_name: str = Field(..., description="The name of the agent to interact with.")

@router.post("/run/{agent_name}", summary="Run a single-turn agent interaction or continue a conversation")
async def run_agent(
    agent_name: str,
    input_data: AgentInput,
    current_user: str = Depends(get_current_user) # Placeholder for authentication
):
    """
    Runs a single interaction with the specified agent.
    If a session_id is provided, it continues a multi-turn conversation.
    """
    redis_client = await get_redis_client() 
    
    try:
        # Retrieve agent from registry
        AgentClass = agent_registry.get_agent(agent_name)
        agent_instance = AgentClass(model="dummy-model", result_type=ChatResponse, system_prompt="dummy system prompt")

        dependencies = AgentDependencies(
            conversation_memory=ConversationMemory(session_id=input_data.session_id, redis=redis_client) if input_data.session_id else None
        )

        # Run the agent
        result = await agent_instance.run_async(user_input=input_data.user_input, dependencies=dependencies)
        
        # Return the structured response
        return {"agent_response": result.data.model_dump()}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/stream/{agent_name}", summary="Stream agent interaction or continue a conversation")
async def stream_agent(
    agent_name: str,
    input_data: AgentInput,
    current_user: str = Depends(get_current_user) # Placeholder for authentication
):
    """
    Streams an interaction with the specified agent.
    If a session_id is provided, it continues a multi-turn conversation.
    """
    redis_client = await get_redis_client()

    try:
        AgentClass = agent_registry.get_agent(agent_name)
        agent_instance = AgentClass(model="dummy-model", result_type=ChatResponse, system_prompt="dummy system prompt")

        dependencies = AgentDependencies(
            conversation_memory=ConversationMemory(session_id=input_data.session_id, redis=redis_client) if input_data.session_id else None
        )

        async def event_generator():
            full_response_content = "" # To reconstruct for the agent's full response for memory
            async for chunk in agent_instance.run_stream(user_input=input_data.user_input, dependencies=dependencies):
                chunk_data = chunk.data.model_dump()
                full_response_content += chunk_data["content"]
                yield f"data: {chunk.data.model_dump_json()}\n\n"
            
            # Save the full agent response to memory after streaming is complete
            if dependencies.conversation_memory:
                await dependencies.conversation_memory.add_message("assistant", full_response_content)


        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
