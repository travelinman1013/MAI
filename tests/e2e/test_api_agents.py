import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.main import app 
from src.core.agents.registry import agent_registry # Import agent_registry

@pytest.fixture(autouse=True) # This fixture will be run for every test
def clear_agent_registry():
    agent_registry._clear()
    yield
    agent_registry._clear() # Clear again after test for good measure

@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client

@pytest.fixture(name="mock_get_current_user")
def mock_get_current_user_fixture():
    with patch("src.core.utils.auth.get_current_user", return_value="test_user") as mock:
        yield mock

@pytest.fixture(name="mock_redis_client")
def mock_redis_client_fixture():
    with patch("src.infrastructure.cache.redis_client.RedisClient", autospec=True) as MockRedisClient:
        mock_redis_instance = MockRedisClient.return_value
        mock_redis_instance.connect = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.get = AsyncMock(return_value=None) 
        mock_redis_instance.set = AsyncMock(return_value=True) 

        with patch("src.infrastructure.cache.redis_client._redis_client", new=mock_redis_instance):
            yield mock_redis_instance

@pytest.fixture(name="mock_conversation_memory")
def mock_conversation_memory_fixture():
    with patch("src.api.routes.agents.ConversationMemory", autospec=True) as mock_cm_class:
        # Create a single AsyncMock for add_message to track all calls
        shared_add_message_mock = AsyncMock()

        def side_effect_cm(*args, **kwargs):
            mock_instance = MagicMock(spec_set=["session_id", "add_message", "get_messages", "save_to_redis", "load_from_redis"])
            mock_instance.session_id = kwargs.get("session_id")
            mock_instance.add_message = shared_add_message_mock # Use the shared mock
            mock_instance.get_messages = MagicMock(return_value=[])
            mock_instance.save_to_redis = AsyncMock()
            mock_instance.load_from_redis = AsyncMock()
            return mock_instance
        
        mock_cm_class.side_effect = side_effect_cm
        mock_cm_class.add_message_mock = shared_add_message_mock # Expose for direct assertion
        yield mock_cm_class

@pytest.fixture(name="mock_pydantic_ai_agent")
def mock_pydantic_ai_agent_fixture():
    with patch("src.core.agents.base.Agent", autospec=True) as MockAgent:
        mock_agent_instance = MockAgent.return_value
        # Simulate StandardResponse(data=ChatResponse(...))
        mock_chat_response = MagicMock(spec_set=["role", "content", "timestamp", "confidence_score", "metadata", "model_dump", "model_dump_json"])
        
        # Mock the methods directly
        mock_chat_response.model_dump.return_value = {"role": "agent", "content": "Mocked Pydantic AI response", "timestamp": "2025-01-01T00:00:00", "confidence_score": 1.0, "metadata": {}}
        mock_chat_response.model_dump_json.return_value = '{"role": "agent", "content": "Mocked Pydantic AI response", "timestamp": "2025-01-01T00:00:00", "confidence_score": 1.0, "metadata": {}}' # For add_message

        mock_standard_response = MagicMock(spec_set=["data"])
        mock_standard_response.data = mock_chat_response
        
        mock_agent_instance.run = AsyncMock(return_value=mock_standard_response)
        yield MockAgent

def test_run_agent_no_session_id(client: TestClient, mock_get_current_user, mock_conversation_memory, mock_redis_client, mock_pydantic_ai_agent):
    user_input = "Hello"
    agent_name = "simple_agent"
    response = client.post(
        f"/api/v1/agents/run/{agent_name}",
        json={"user_input": user_input, "agent_name": agent_name}
    )
    assert response.status_code == 200
    expected_response_content = f"SimpleAgent received: '{user_input}'"
    response_json = response.json()
    assert response_json["agent_response"]["role"] == "agent"
    assert response_json["agent_response"]["content"] == expected_response_content
    assert "timestamp" in response_json["agent_response"]
    assert "confidence_score" in response_json["agent_response"]
    # Removed: assert "metadata" in response_json["agent_response"]
    mock_conversation_memory.assert_not_called()

def test_run_agent_with_session_id(client: TestClient, mock_get_current_user, mock_conversation_memory, mock_redis_client, mock_pydantic_ai_agent):
    session_id = "test_session"
    user_input = "Hi again"
    agent_name = "simple_agent"
    response = client.post(
        f"/api/v1/agents/run/{agent_name}",
        json={"session_id": session_id, "user_input": user_input, "agent_name": agent_name}
    )
    assert response.status_code == 200
    expected_response_content = f"SimpleAgent received: '{user_input}' (Session: {session_id})"
    response_json = response.json()
    assert response_json["agent_response"]["role"] == "agent"
    assert response_json["agent_response"]["content"] == expected_response_content
    assert "timestamp" in response_json["agent_response"]
    assert "confidence_score" in response_json["agent_response"]
    # Removed: assert "metadata" in response_json["agent_response"]
    
    mock_conversation_memory.assert_called_once_with(session_id=session_id, redis=mock_redis_client)
    
    # Assert on the shared add_message mock
    mock_conversation_memory.add_message_mock.assert_any_call(role="user", content=user_input)
    mock_conversation_memory.add_message_mock.assert_any_call(role="agent", content=expected_response_content)
    assert mock_conversation_memory.add_message_mock.call_count == 2