import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.memory.short_term import ConversationMemory
from src.infrastructure.cache.redis_client import RedisClient

class MockResult(BaseModel):
    """A simple Pydantic model for agent results."""
    message: str
    status: str = "success"

# This mock now completely replaces pydantic_ai.Agent
class MockPydanticAIAgent:
    """Mocks the pydantic_ai.Agent for testing purposes."""
    def __init__(self, model: MagicMock, output_type: type[BaseModel], system_prompt: str, deps_type: type, retries: int):
        self.model = model
        self.output_type = output_type
        self.system_prompt = system_prompt
        self.deps_type = deps_type
        self.retries = retries
        self.run_mock = AsyncMock()

    async def run(self, user_input: str, deps: AgentDependencies, message_history: list[dict]):
        # Simulate Pydantic AI's behavior
        response_message = f"Agent processed: {user_input}"
        if message_history:
            response_message += f" (History length: {len(message_history)})"
        
        mock_output = self.output_type(message=response_message)
        
        # Pydantic AI's run method returns a RunContext which contains the output
        mock_run_context = MagicMock(spec=RunContext)
        mock_run_context.output = mock_output
        return mock_run_context

@pytest.fixture
def mock_redis_client():
    """Fixture for a mock RedisClient."""
    mock = MagicMock(spec=RedisClient)
    # Mock set to simply store the value
    mock.set = AsyncMock()
    # Mock get to return a stored value, simulating Redis
    mock_store = {}
    async def mock_get(key):
        return mock_store.get(key)
    async def mock_set(key, value, ex=None):
        mock_store[key] = value
    mock.get.side_effect = mock_get
    mock.set.side_effect = mock_set
    return mock

@pytest.fixture
def base_agent_framework(mock_redis_client, monkeypatch):
    """Fixture for BaseAgentFramework with mocked dependencies and pydantic_ai.Agent."""
    name = "TestAgent"
    system_prompt = "You are a test agent."
    result_type = MockResult
    
    # Monkeypatch pydantic_ai.Agent to use our mock
    monkeypatch.setattr("src.core.agents.base.Agent", MockPydanticAIAgent)

    agent_framework = BaseAgentFramework(
        name=name,
        model=MagicMock(), # This will now be passed to MockPydanticAIAgent
        result_type=result_type,
        system_prompt=system_prompt,
    )
    # The agent_framework.agent will now be an instance of MockPydanticAIAgent
    return agent_framework

@pytest.mark.asyncio
async def test_agent_state_management_with_session_id(base_agent_framework, mock_redis_client):
    """
    Test that the agent correctly uses ShortTermMemory for state management
    across multiple turns with a session_id.
    """
    session_id = "test_session_123"
    user_id = "test_user_456"

    deps = AgentDependencies(redis=mock_redis_client, session_id=session_id, user_id=user_id)

    # Simulate first turn
    user_input_1 = "Hello, agent!"
    response_1 = await base_agent_framework.run_async(user_input_1, deps)

    assert response_1.message == "Agent processed: Hello, agent! (History length: 1)"
    assert mock_redis_client.set.call_count == 2 # 1 for user, 1 for assistant

    # Check if history was saved in redis
    # The get_conversation_context calls ConversationMemory.load_from_redis which calls redis.get
    history_key = f"conversation_memory:{session_id}"
    mock_redis_client.get.assert_called_with(history_key)

    # Simulate second turn
    user_input_2 = "How are you?"
    response_2 = await base_agent_framework.run_async(user_input_2, deps)

    # The mock agent's response message will now reflect the history length
    assert "History length: 3" in response_2.message
    assert response_2.message == "Agent processed: How are you? (History length: 3)"
    assert mock_redis_client.set.call_count == 4 # 2 for user, 2 for assistant

    # Verify get_conversation_context works
    retrieved_history = await base_agent_framework.get_conversation_context(deps)
    assert len(retrieved_history) == 4 # After two turns, 4 messages expected
    assert retrieved_history[0]["content"] == "Hello, agent!"
    assert "Agent processed: Hello, agent!" in retrieved_history[1]["content"]
    assert retrieved_history[2]["content"] == "How are you?"
    assert "Agent processed: How are you?" in retrieved_history[3]["content"]


@pytest.mark.asyncio
async def test_agent_state_management_no_session_id(base_agent_framework, mock_redis_client):
    """
    Test that state management is skipped if no session_id is provided.
    """
    deps = AgentDependencies(redis=mock_redis_client) # No session_id

    user_input = "Stateless query"
    response = await base_agent_framework.run_async(user_input, deps)

    assert response.message == "Agent processed: Stateless query"
    mock_redis_client.set.assert_not_called()
    mock_redis_client.get.assert_not_called()

    # Verify get_conversation_context returns empty if no session_id
    retrieved_history = await base_agent_framework.get_conversation_context(deps)
    assert retrieved_history == []
