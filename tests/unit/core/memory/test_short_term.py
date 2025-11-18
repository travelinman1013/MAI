import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import json

from src.core.memory import Message, ConversationMemory
from src.infrastructure.cache.redis_client import RedisClient

# Helper to create a mock RedisClient
@pytest.fixture
def mock_redis_client():
    mock = AsyncMock(spec=RedisClient)
    mock.get.return_value = None
    mock.set.return_value = None
    return mock

@pytest.fixture
def conversation_memory(mock_redis_client):
    return ConversationMemory(session_id="test_session", redis=mock_redis_client)

@pytest.fixture
def populated_memory(conversation_memory):
    async def _populate():
        await conversation_memory.add_message("user", "Hello")
        await conversation_memory.add_message("assistant", "Hi there!")
        await conversation_memory.add_message("user", "How are you?")
        return conversation_memory
    return _populate

@pytest.mark.asyncio
async def test_conversation_memory_init(mock_redis_client):
    memory = ConversationMemory(session_id="test_session_id", redis=mock_redis_client)
    assert memory.session_id == "test_session_id"
    assert memory.redis == mock_redis_client
    assert memory.messages == []

@pytest.mark.asyncio
async def test_conversation_memory_init_validation():
    with pytest.raises(ValueError, match="session_id must be a non-empty string."):
        ConversationMemory(session_id="", redis=AsyncMock(spec=RedisClient))
    with pytest.raises(TypeError, match="redis must be an instance of RedisClient."):
        ConversationMemory(session_id="test", redis=None)

@pytest.mark.asyncio
async def test_add_message(conversation_memory, mock_redis_client):
    await conversation_memory.add_message("user", "Test content")
    assert len(conversation_memory.messages) == 1
    assert conversation_memory.messages[0].role == "user"
    assert conversation_memory.messages[0].content == "Test content"
    assert isinstance(conversation_memory.messages[0].timestamp, datetime)
    mock_redis_client.set.assert_called_once() # Should call save_to_redis

@pytest.mark.asyncio
async def test_add_message_with_metadata(conversation_memory, mock_redis_client):
    metadata = {"source": "test_source"}
    await conversation_memory.add_message("user", "Content with meta", metadata=metadata)
    assert conversation_memory.messages[0].metadata == metadata
    mock_redis_client.set.assert_called_once()

@pytest.mark.asyncio
async def test_add_message_validation(conversation_memory):
    with pytest.raises(ValueError, match="role must be a non-empty string."):
        await conversation_memory.add_message("", "content")
    with pytest.raises(ValueError, match="content must be a non-empty string."):
        await conversation_memory.add_message("user", "")

@pytest.mark.asyncio
async def test_get_messages(populated_memory):
    memory = await populated_memory()
    messages = memory.get_messages()
    assert len(messages) == 3
    assert messages[0].content == "Hello"
    assert messages[2].content == "How are you?"

    # Test last_n_messages
    last_two = memory.get_messages(last_n_messages=2)
    assert len(last_two) == 2
    assert last_two[0].content == "Hi there!"
    assert last_two[1].content == "How are you?"

    last_one = memory.get_messages(last_n_messages=1)
    assert len(last_one) == 1
    assert last_one[0].content == "How are you?"

    last_zero = memory.get_messages(last_n_messages=0)
    assert len(last_zero) == 0

    last_more_than_exist = memory.get_messages(last_n_messages=5)
    assert len(last_more_than_exist) == 3

@pytest.mark.asyncio
async def test_get_context_string_default(populated_memory):
    memory = await populated_memory()
    context = memory.get_context_string()
    expected_context = "user: Hello\nassistant: Hi there!\nuser: How are you?"
    assert context == expected_context

@pytest.mark.asyncio
async def test_get_context_string_chat(populated_memory):
    memory = await populated_memory()
    context = memory.get_context_string(format="chat")
    expected_context = "<user>Hello</user>\n<assistant>Hi there!</assistant>\n<user>How are you?</user>"
    assert context == expected_context

@pytest.mark.asyncio
async def test_get_context_string_xml(populated_memory):
    memory = await populated_memory()
    await memory.add_message("system", "Special chars: < > &") # Add message with special chars
    context = memory.get_context_string(format="xml")
    
    # Check for escaped characters
    assert "Special chars: &lt; &gt; &amp;" in context
    assert "<user>\n  Hello\n</user>" in context
    assert "<assistant>\n  Hi there!\n</assistant>" in context
    assert "<user>\n  How are you?\n</user>" in context
    assert "<system>\n  Special chars: &lt; &gt; &amp;\n</system>" in context


@pytest.mark.asyncio
async def test_get_context_string_last_n_messages(populated_memory):
    memory = await populated_memory()
    context = memory.get_context_string(last_n_messages=1)
    expected_context = "user: How are you?"
    assert context == expected_context

@pytest.mark.asyncio
async def test_count_tokens(populated_memory):
    memory = await populated_memory()
    # "Hello" (5) + "Hi there!" (9) + "How are you?" (12) + "user" (4)*2 + "assistant" (9) = 39 chars
    # APPROX_CHARS_PER_TOKEN = 4
    # 39 // 4 = 9 (approx)
    expected_tokens = (len("user") + len("Hello") + len("assistant") + len("Hi there!") + len("user") + len("How are you?")) // 4
    assert memory.count_tokens() == expected_tokens

@pytest.mark.asyncio
async def test_truncate_to_fit(conversation_memory):
    # Add messages that will exceed a small token limit
    for i in range(10):
        await conversation_memory.add_message("user", f"message {i}")
        await conversation_memory.add_message("assistant", f"response {i}")
    
    # Calculate initial tokens
    initial_tokens = conversation_memory.count_tokens()
    assert len(conversation_memory.messages) == 20
    
    # Define a max_tokens that forces truncation
    # Each message content + role is roughly (8+4)/4 = 3 tokens. 20 messages * 3 tokens = 60 tokens
    # Let's aim for 3 messages (user, assistant, user) = 9 tokens approx
    max_tokens = ((len("user") + len("message 8")) + (len("assistant") + len("response 8")) + (len("user") + len("message 9"))) // 4 
    max_tokens += 2 # Give a small buffer

    conversation_memory.truncate_to_fit(max_tokens)
    
    # Check if messages were truncated
    assert conversation_memory.count_tokens() <= max_tokens
    assert conversation_memory.messages[-1].content == "response 9" # Newest message
    assert conversation_memory.messages[-2].content == "message 9"
    assert conversation_memory.messages[-3].content == "response 8"
    assert len(conversation_memory.messages) == 3 # Only three messages fit

    # Test with max_tokens = 0, should clear all messages
    conversation_memory.truncate_to_fit(0)
    assert len(conversation_memory.messages) == 0
    assert conversation_memory.count_tokens() == 0

    # Test with max_tokens larger than current, should do nothing
    await conversation_memory.add_message("user", "single message")
    initial_tokens = conversation_memory.count_tokens()
    conversation_memory.truncate_to_fit(initial_tokens + 10)
    assert conversation_memory.count_tokens() == initial_tokens
    assert len(conversation_memory.messages) == 1

@pytest.mark.asyncio
async def test_save_and_load_from_redis(mock_redis_client):
    memory = ConversationMemory(session_id="test_redis_session", redis=mock_redis_client)
    await memory.add_message("user", "First message")
    await memory.add_message("assistant", "Second message")

    # Simulate saving to Redis
    assert mock_redis_client.set.called

    # Get the value that was supposedly set
    # The set call happens inside add_message, so we need to inspect the call arguments
    set_args, _ = mock_redis_client.set.call_args
    redis_key = set_args[0]
    stored_json = set_args[1]

    # Clear current messages in memory to simulate loading into a fresh object
    memory.messages = []
    assert len(memory.messages) == 0

    # Mock RedisClient.get to return the stored JSON
    mock_redis_client.get.return_value = stored_json

    # Load from Redis
    await memory.load_from_redis()

    assert len(memory.messages) == 2
    assert memory.messages[0].role == "user"
    assert memory.messages[0].content == "First message"
    assert memory.messages[1].role == "assistant"
    assert memory.messages[1].content == "Second message"

@pytest.mark.asyncio
async def test_load_from_redis_no_data(mock_redis_client):
    memory = ConversationMemory(session_id="new_session", redis=mock_redis_client)
    mock_redis_client.get.return_value = None # Simulate no data in Redis
    await memory.load_from_redis()
    assert len(memory.messages) == 0
    mock_redis_client.get.assert_called_once_with(f"{memory.REDIS_KEY_PREFIX}new_session")

@pytest.mark.asyncio
async def test_load_from_redis_invalid_data(mock_redis_client):
    memory = ConversationMemory(session_id="invalid_session", redis=mock_redis_client)
    mock_redis_client.get.return_value = b"invalid json data"
    await memory.load_from_redis()
    assert len(memory.messages) == 0 # Should clear messages on error
    # Check if a warning or error was logged (can't assert directly without capturing logs)
