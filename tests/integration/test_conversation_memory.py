"""
Comprehensive integration tests for conversation memory system.

Tests the full memory stack including:
- MessageConverter: Message <-> ModelMessage conversion
- ConversationMemory: Redis persistence and retrieval
- ContextManager: Token counting and truncation
- HistoryProcessors: Message filtering and limiting
- End-to-end: Multi-turn conversation flows
"""

import pytest
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    SystemPromptPart,
)

from src.core.memory.models import Message
from src.core.memory.message_converter import (
    messages_to_model_messages,
    model_messages_to_messages,
    serialize_model_messages,
    deserialize_model_messages,
)
from src.core.memory.context_manager import (
    ContextWindowManager,
    TokenCounter,
    count_tokens,
)
from src.core.memory.history_processors import (
    RecencyProcessor,
    TokenLimitProcessor,
    ChainedProcessor,
    create_default_processor,
    limit_by_turns,
    limit_by_tokens,
)
from src.core.memory.short_term import ConversationMemory
from src.infrastructure.cache.redis_client import RedisClient


class TestMessageConverter:
    """Test message format conversion between MAI and pydantic-ai formats."""

    def test_basic_conversion_to_model_messages(self):
        """Test converting simple MAI messages to pydantic-ai ModelMessages."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        model_messages = messages_to_model_messages(messages)

        assert len(model_messages) == 2
        assert isinstance(model_messages[0], ModelRequest)
        assert isinstance(model_messages[1], ModelResponse)

        # Check user message content
        user_parts = model_messages[0].parts
        assert len(user_parts) == 1
        assert isinstance(user_parts[0], UserPromptPart)
        assert user_parts[0].content == "Hello"

        # Check assistant message content
        assistant_parts = model_messages[1].parts
        assert len(assistant_parts) == 1
        assert isinstance(assistant_parts[0], TextPart)
        assert assistant_parts[0].content == "Hi there!"

    def test_conversion_with_system_prompt(self):
        """Test that system prompt is added to first user message."""
        messages = [
            Message(role="user", content="Hello"),
        ]
        system_prompt = "You are a helpful assistant."

        model_messages = messages_to_model_messages(messages, system_prompt=system_prompt)

        assert len(model_messages) == 1
        assert isinstance(model_messages[0], ModelRequest)

        # Should have both system prompt and user prompt
        parts = model_messages[0].parts
        assert len(parts) == 2
        assert isinstance(parts[0], SystemPromptPart)
        assert parts[0].content == system_prompt
        assert isinstance(parts[1], UserPromptPart)
        assert parts[1].content == "Hello"

    def test_round_trip_conversion(self):
        """Test converting messages back and forth preserves content."""
        original_messages = [
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="2+2 equals 4."),
            Message(role="user", content="And 3+3?"),
            Message(role="assistant", content="3+3 equals 6."),
        ]

        # Convert to model messages
        model_messages = messages_to_model_messages(original_messages)

        # Convert back to MAI messages
        converted_back = model_messages_to_messages(model_messages)

        # Check that content is preserved
        assert len(converted_back) == len(original_messages)
        for original, converted in zip(original_messages, converted_back):
            assert original.role == converted.role
            assert original.content == converted.content

    def test_serialization_deserialization(self):
        """Test JSON serialization and deserialization of ModelMessages."""
        model_messages = [
            ModelRequest(parts=[UserPromptPart(content="Test message")]),
            ModelResponse(parts=[TextPart(content="Test response")]),
        ]

        # Serialize
        json_str = serialize_model_messages(model_messages)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Deserialize
        deserialized = deserialize_model_messages(json_str)
        assert len(deserialized) == 2
        assert isinstance(deserialized[0], ModelRequest)
        assert isinstance(deserialized[1], ModelResponse)

    def test_empty_messages(self):
        """Test handling of empty message lists."""
        result = messages_to_model_messages([])
        assert result == []

        result_back = model_messages_to_messages([])
        assert result_back == []


class TestConversationMemory:
    """Test conversation memory storage and retrieval."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client for testing."""
        redis_mock = MagicMock(spec=RedisClient)
        redis_mock.set = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.delete = AsyncMock()
        return redis_mock

    @pytest.fixture
    def conversation_memory(self, mock_redis):
        """Create a ConversationMemory instance for testing."""
        return ConversationMemory(session_id="test-session", redis=mock_redis)

    @pytest.mark.asyncio
    async def test_add_and_retrieve_messages(self, conversation_memory):
        """Test adding messages and retrieving them."""
        await conversation_memory.add_message("user", "Hello")
        await conversation_memory.add_message("assistant", "Hi there!")

        messages = conversation_memory.get_messages()

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    @pytest.mark.asyncio
    async def test_get_last_n_messages(self, conversation_memory):
        """Test retrieving only the last N messages."""
        for i in range(5):
            await conversation_memory.add_message("user", f"Message {i}")

        last_2 = conversation_memory.get_messages(last_n_messages=2)

        assert len(last_2) == 2
        assert last_2[0].content == "Message 3"
        assert last_2[1].content == "Message 4"

    @pytest.mark.asyncio
    async def test_model_messages_conversion(self, conversation_memory):
        """Test getting messages in pydantic-ai ModelMessage format."""
        await conversation_memory.add_message("user", "Test question")
        await conversation_memory.add_message("assistant", "Test answer")

        model_messages = conversation_memory.get_model_messages()

        assert len(model_messages) == 2
        assert isinstance(model_messages[0], ModelRequest)
        assert isinstance(model_messages[1], ModelResponse)

    @pytest.mark.asyncio
    async def test_redis_persistence(self, mock_redis, conversation_memory):
        """Test that messages are saved to Redis."""
        await conversation_memory.add_message("user", "Persistent message")

        # Verify Redis set was called
        mock_redis.set.assert_called()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "conversation_memory:test-session"

    @pytest.mark.asyncio
    async def test_clear_conversation(self, mock_redis, conversation_memory):
        """Test clearing all messages from a conversation."""
        await conversation_memory.add_message("user", "Message to clear")
        await conversation_memory.clear()

        messages = conversation_memory.get_messages()
        assert len(messages) == 0

        # Verify Redis delete was called
        mock_redis.delete.assert_called()


class TestContextManager:
    """Test context window management and token counting."""

    def test_token_counter_basic(self):
        """Test basic token counting functionality."""
        counter = TokenCounter()
        text = "This is a test message"

        token_count = counter.count_tokens(text)

        # Token count should be positive
        assert token_count > 0
        # Roughly 4-6 tokens for this simple text
        assert 2 < token_count < 10

    def test_token_counter_message(self):
        """Test counting tokens in ModelMessage objects."""
        counter = TokenCounter()
        message = ModelRequest(parts=[UserPromptPart(content="Hello, how are you?")])

        token_count = counter.count_message_tokens(message)

        # Should count tokens + small overhead
        assert token_count > 0

    def test_context_manager_initialization(self):
        """Test initializing ContextWindowManager."""
        manager = ContextWindowManager(max_tokens=4096, reserve_tokens=1000)

        assert manager.max_tokens == 4096
        assert manager.reserve_tokens == 1000
        assert manager.max_history_tokens == 3096

    def test_context_manager_for_model(self):
        """Test creating manager for specific model."""
        manager = ContextWindowManager.for_model("gpt-4")

        assert manager.max_tokens == 8192  # GPT-4 context limit

    def test_fit_messages_within_limit(self):
        """Test that messages within limit are not truncated."""
        manager = ContextWindowManager(max_tokens=4096, reserve_tokens=1000)

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Short message")]),
            ModelResponse(parts=[TextPart(content="Short reply")]),
        ]

        fitted = manager.fit_messages(messages)

        # All messages should fit
        assert len(fitted) == len(messages)

    def test_fit_messages_truncation(self):
        """Test that messages are truncated when exceeding limit."""
        manager = ContextWindowManager(max_tokens=100, reserve_tokens=20)

        # Create many messages that will exceed limit
        messages = []
        for i in range(20):
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=f"User message {i} with some content")])
            )
            messages.append(
                ModelResponse(parts=[TextPart(content=f"Assistant response {i} with more content")])
            )

        fitted = manager.fit_messages(messages)

        # Should be fewer messages after truncation
        assert len(fitted) < len(messages)
        # Should keep most recent messages
        assert fitted[-1] == messages[-1]

    def test_context_stats(self):
        """Test getting context statistics."""
        manager = ContextWindowManager(max_tokens=4096, reserve_tokens=1000)

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Test message")]),
            ModelResponse(parts=[TextPart(content="Test response")]),
        ]

        stats = manager.get_context_stats(messages)

        assert "total_tokens" in stats
        assert "max_tokens" in stats
        assert "utilization_percent" in stats
        assert "num_messages" in stats
        assert stats["num_messages"] == 2


class TestHistoryProcessors:
    """Test history processors for filtering and limiting messages."""

    def test_recency_processor(self):
        """Test keeping only recent conversation turns."""
        processor = RecencyProcessor(max_turns=2)

        messages = []
        for i in range(10):
            messages.append(ModelRequest(parts=[UserPromptPart(content=f"User {i}")]))
            messages.append(ModelResponse(parts=[TextPart(content=f"Assistant {i}")]))

        processed = processor.process(messages)

        # Should keep only last 2 turns (4 messages)
        assert len(processed) == 4
        # Should be most recent messages
        assert "User 8" in str(processed[0].parts[0].content)
        assert "User 9" in str(processed[2].parts[0].content)

    def test_token_limit_processor(self):
        """Test limiting messages by total token count."""
        processor = TokenLimitProcessor(max_tokens=100, model_name="default")

        # Create messages that exceed token limit
        messages = []
        for i in range(20):
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=f"Message {i} with content" * 10)])
            )

        processed = processor.process(messages)

        # Should be fewer messages after processing
        assert len(processed) < len(messages)

    def test_chained_processor(self):
        """Test chaining multiple processors together."""
        processor = ChainedProcessor([
            RecencyProcessor(max_turns=10),
            TokenLimitProcessor(max_tokens=500),
        ])

        messages = []
        for i in range(30):
            messages.append(ModelRequest(parts=[UserPromptPart(content=f"Message {i}")]))

        processed = processor.process(messages)

        # Should be limited by both processors
        assert len(processed) <= 20  # Max from recency processor

    def test_create_default_processor(self):
        """Test factory function for default processor."""
        processor = create_default_processor(max_turns=5, max_tokens=1000)

        assert processor is not None
        # Should be a chained processor
        assert isinstance(processor, ChainedProcessor)

    def test_convenience_functions(self):
        """Test convenience functions for creating processors."""
        recency = limit_by_turns(5)
        assert isinstance(recency, RecencyProcessor)

        token_limit = limit_by_tokens(1000)
        assert isinstance(token_limit, TokenLimitProcessor)


class TestEndToEnd:
    """End-to-end integration tests for multi-turn conversations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client that simulates storage."""
        storage = {}

        async def mock_set(key, value):
            storage[key] = value

        async def mock_get(key):
            return storage.get(key)

        async def mock_delete(key):
            storage.pop(key, None)

        redis_mock = MagicMock(spec=RedisClient)
        redis_mock.set = AsyncMock(side_effect=mock_set)
        redis_mock.get = AsyncMock(side_effect=mock_get)
        redis_mock.delete = AsyncMock(side_effect=mock_delete)

        return redis_mock

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_flow(self, mock_redis):
        """Test a complete multi-turn conversation with memory."""
        memory = ConversationMemory(session_id="test-convo", redis=mock_redis)

        # Turn 1
        await memory.add_message("user", "My name is Alice")
        await memory.add_message("assistant", "Nice to meet you, Alice!")

        # Turn 2
        await memory.add_message("user", "What's my name?")
        await memory.add_message("assistant", "Your name is Alice.")

        # Turn 3
        await memory.add_message("user", "My favorite color is blue")
        await memory.add_message("assistant", "Got it, your favorite color is blue!")

        messages = memory.get_messages()

        assert len(messages) == 6
        assert messages[0].content == "My name is Alice"
        assert messages[-1].content == "Got it, your favorite color is blue!"

    @pytest.mark.asyncio
    async def test_context_window_management_in_conversation(self, mock_redis):
        """Test that long conversations are properly truncated."""
        memory = ConversationMemory(session_id="long-convo", redis=mock_redis)

        # Add many messages
        for i in range(50):
            await memory.add_message("user", f"Question {i}" * 20)
            await memory.add_message("assistant", f"Answer {i}" * 20)

        # Get messages with context limit
        model_messages = memory.get_model_messages_with_limit(
            model_name="gpt-4",
            reserve_tokens=1000,
        )

        # Should be truncated
        assert len(model_messages) < 100

        # Should keep most recent messages
        last_message = model_messages_to_messages([model_messages[-1]])[0]
        assert "Answer 49" in last_message.content

    @pytest.mark.asyncio
    async def test_session_isolation(self, mock_redis):
        """Test that different sessions don't interfere with each other."""
        memory1 = ConversationMemory(session_id="session-1", redis=mock_redis)
        memory2 = ConversationMemory(session_id="session-2", redis=mock_redis)

        await memory1.add_message("user", "Session 1 message")
        await memory2.add_message("user", "Session 2 message")

        messages1 = memory1.get_messages()
        messages2 = memory2.get_messages()

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content == "Session 1 message"
        assert messages2[0].content == "Session 2 message"

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, mock_redis):
        """Test that memory persists when creating new instances."""
        # First instance adds messages
        memory1 = ConversationMemory(session_id="persist-test", redis=mock_redis)
        await memory1.add_message("user", "Remember this")
        await memory1.add_message("assistant", "I will remember")

        # Second instance loads from Redis
        memory2 = ConversationMemory(session_id="persist-test", redis=mock_redis)
        await memory2.load_from_redis()

        messages = memory2.get_messages()

        assert len(messages) == 2
        assert messages[0].content == "Remember this"
        assert messages[1].content == "I will remember"

    @pytest.mark.asyncio
    async def test_model_message_format_persistence(self, mock_redis):
        """Test that ModelMessage format is properly persisted and restored."""
        memory = ConversationMemory(session_id="model-msg-test", redis=mock_redis)

        # Create model messages
        model_messages = [
            ModelRequest(parts=[UserPromptPart(content="Test question")]),
            ModelResponse(parts=[TextPart(content="Test answer")]),
        ]

        # Store them
        await memory.add_model_messages(model_messages)

        # Create new instance and load
        memory2 = ConversationMemory(session_id="model-msg-test", redis=mock_redis)
        await memory2.load_from_redis()

        retrieved = memory2.get_model_messages()

        assert len(retrieved) == 2
        assert isinstance(retrieved[0], ModelRequest)
        assert isinstance(retrieved[1], ModelResponse)

    @pytest.mark.asyncio
    async def test_clear_preserves_session_isolation(self, mock_redis):
        """Test that clearing one session doesn't affect others."""
        memory1 = ConversationMemory(session_id="session-clear-1", redis=mock_redis)
        memory2 = ConversationMemory(session_id="session-clear-2", redis=mock_redis)

        await memory1.add_message("user", "Session 1")
        await memory2.add_message("user", "Session 2")

        # Clear session 1
        await memory1.clear()

        # Session 1 should be empty
        assert len(memory1.get_messages()) == 0

        # Session 2 should still have messages
        await memory2.load_from_redis()
        assert len(memory2.get_messages()) == 1
        assert memory2.get_messages()[0].content == "Session 2"
