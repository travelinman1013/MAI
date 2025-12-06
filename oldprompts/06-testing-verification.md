# Task: End-to-End Testing and Verification

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Comprehensive testing of multi-turn conversations with full verification
**Sequence**: 6 of 6
**Depends On**: 05-history-processors.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `f8f78248-7288-4342-a60a-8ecfc30f0412`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/f8f78248-7288-4342-a60a-8ecfc30f0412" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/f8f78248-7288-4342-a60a-8ecfc30f0412" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

All implementation tasks are complete:
1. ✅ Message format bridge (converts between Redis and pydantic-ai formats)
2. ✅ Enhanced ConversationMemory (stores ModelMessage objects)
3. ✅ Context window manager (token counting and limiting)
4. ✅ ChatAgent integration (passes history to LLM)
5. ✅ History processors (optimizes context)

This final task verifies everything works together and creates comprehensive tests.

---

## Requirements

### 1. Create Integration Test Suite

Create `tests/integration/test_conversation_memory.py`:

```python
"""
Integration tests for conversation memory enhancement.

Tests multi-turn conversations, memory persistence, and context management.
"""

import pytest
import asyncio
from datetime import datetime

# Test fixtures
@pytest.fixture
async def redis_client():
    """Get connected Redis client."""
    from src.infrastructure.cache.redis_client import RedisClient
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def session_id():
    """Generate unique session ID for tests."""
    return f"test-memory-{datetime.now().timestamp()}"


class TestMessageConverter:
    """Test message format conversion."""

    def test_messages_to_model_messages_basic(self):
        """Test basic conversion from simple to model format."""
        from src.core.memory.models import Message
        from src.core.memory.message_converter import messages_to_model_messages
        from pydantic_ai.messages import ModelRequest, ModelResponse

        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        result = messages_to_model_messages(messages)

        assert len(result) == 2
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[1], ModelResponse)

    def test_round_trip_conversion(self):
        """Test converting to model messages and back."""
        from src.core.memory.models import Message
        from src.core.memory.message_converter import (
            messages_to_model_messages,
            model_messages_to_messages,
        )

        original = [
            Message(role="user", content="What is Python?"),
            Message(role="assistant", content="Python is a programming language."),
            Message(role="user", content="Tell me more"),
            Message(role="assistant", content="It's great for AI and web development."),
        ]

        model_msgs = messages_to_model_messages(original)
        restored = model_messages_to_messages(model_msgs)

        assert len(restored) == len(original)
        for orig, rest in zip(original, restored):
            assert orig.role == rest.role
            assert orig.content == rest.content


class TestConversationMemory:
    """Test enhanced ConversationMemory."""

    @pytest.mark.asyncio
    async def test_add_and_retrieve_messages(self, redis_client, session_id):
        """Test adding messages and retrieving them."""
        from src.core.memory.short_term import ConversationMemory

        memory = ConversationMemory(session_id=session_id, redis=redis_client)

        await memory.add_message(role="user", content="Hello")
        await memory.add_message(role="assistant", content="Hi!")

        messages = memory.get_messages()
        assert len(messages) == 2

        # Cleanup
        await memory.clear()

    @pytest.mark.asyncio
    async def test_get_model_messages(self, redis_client, session_id):
        """Test getting messages in pydantic-ai format."""
        from src.core.memory.short_term import ConversationMemory
        from pydantic_ai.messages import ModelMessage

        memory = ConversationMemory(session_id=session_id, redis=redis_client)

        await memory.add_message(role="user", content="Test question")
        await memory.add_message(role="assistant", content="Test answer")

        model_msgs = memory.get_model_messages()
        assert len(model_msgs) == 2
        assert all(isinstance(m, ModelMessage) for m in model_msgs)

        await memory.clear()

    @pytest.mark.asyncio
    async def test_redis_persistence(self, redis_client, session_id):
        """Test that messages persist to Redis."""
        from src.core.memory.short_term import ConversationMemory

        # Create and save
        memory1 = ConversationMemory(session_id=session_id, redis=redis_client)
        await memory1.add_message(role="user", content="Remember this")
        await memory1.add_message(role="assistant", content="I will remember")

        # Load in new instance
        memory2 = ConversationMemory(session_id=session_id, redis=redis_client)
        await memory2.load_from_redis()

        assert len(memory2.messages) == 2
        assert memory2.messages[0].content == "Remember this"

        await memory1.clear()


class TestContextManager:
    """Test context window management."""

    def test_token_counting(self):
        """Test token counting accuracy."""
        from src.core.memory.context_manager import TokenCounter

        counter = TokenCounter()
        # "Hello world" is typically 2-3 tokens
        count = counter.count_tokens("Hello world")
        assert 1 <= count <= 5  # Reasonable range

    def test_message_fitting(self):
        """Test fitting messages to token limit."""
        from src.core.memory.context_manager import ContextWindowManager
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

        # Create many messages
        messages = []
        for i in range(50):
            messages.append(ModelRequest(parts=[UserPromptPart(content=f"Q{i}: " + "x" * 50)]))
            messages.append(ModelResponse(parts=[TextPart(content=f"A{i}: " + "y" * 100)]))

        # Fit to small limit
        mgr = ContextWindowManager(max_tokens=1000, reserve_tokens=200)
        fitted = mgr.fit_messages(messages)

        # Should have fewer messages
        assert len(fitted) < len(messages)
        # Should fit within limit
        assert mgr.token_counter.count_messages_tokens(fitted) <= 800


class TestHistoryProcessors:
    """Test history processors."""

    def test_recency_processor(self):
        """Test keeping only recent messages."""
        from src.core.memory.history_processors import RecencyProcessor
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

        messages = []
        for i in range(20):
            messages.append(ModelRequest(parts=[UserPromptPart(content=f"Q{i}")]))
            messages.append(ModelResponse(parts=[TextPart(content=f"A{i}")]))

        processor = RecencyProcessor(max_turns=5)
        result = processor.process(messages)

        assert len(result) == 10  # 5 turns * 2 messages

    def test_chained_processors(self):
        """Test chaining multiple processors."""
        from src.core.memory.history_processors import (
            RecencyProcessor,
            TokenLimitProcessor,
            ChainedProcessor,
        )
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        messages = [
            ModelRequest(parts=[UserPromptPart(content=f"Message {i}")])
            for i in range(100)
        ]

        chain = ChainedProcessor([
            RecencyProcessor(max_turns=20),
            TokenLimitProcessor(max_tokens=500),
        ])

        result = chain.process(messages)
        assert len(result) < len(messages)


class TestEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, redis_client, session_id):
        """Test a complete multi-turn conversation flow."""
        from src.core.memory.short_term import ConversationMemory

        memory = ConversationMemory(session_id=session_id, redis=redis_client)

        # Simulate conversation
        turns = [
            ("user", "My name is Bob"),
            ("assistant", "Nice to meet you, Bob!"),
            ("user", "What's the weather like?"),
            ("assistant", "I don't have access to weather data."),
            ("user", "What's my name?"),
        ]

        for role, content in turns:
            await memory.add_message(role=role, content=content)

        # Get history for next LLM call
        history = memory.get_model_messages()
        assert len(history) == 5

        # Verify content is preserved
        messages = memory.get_messages()
        assert "Bob" in messages[0].content

        await memory.clear()


# Run with: pytest tests/integration/test_conversation_memory.py -v
```

### 2. Create Manual Test Script

Create `scripts/test_conversation_memory.sh`:

```bash
#!/bin/bash
# Manual test script for conversation memory

set -e

API_URL="http://localhost:8000/api/v1"
SESSION_ID="manual-test-$(date +%s)"

echo "=== Testing Conversation Memory ==="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: Basic memory
echo "--- Test 1: Setting up context ---"
curl -s -X POST "$API_URL/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"My name is Charlie and I love programming in Python\", \"session_id\": \"$SESSION_ID\"}"
echo -e "\n"

sleep 2

# Test 2: Recall name
echo "--- Test 2: Should recall name ---"
curl -s -X POST "$API_URL/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my name?\", \"session_id\": \"$SESSION_ID\"}"
echo -e "\n"

sleep 2

# Test 3: Recall preference
echo "--- Test 3: Should recall programming preference ---"
curl -s -X POST "$API_URL/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What programming language do I like?\", \"session_id\": \"$SESSION_ID\"}"
echo -e "\n"

sleep 2

# Test 4: Check history stored
echo "--- Test 4: Checking stored history ---"
curl -s "$API_URL/agents/history/$SESSION_ID" | python3 -m json.tool
echo ""

# Test 5: New session should NOT remember
NEW_SESSION="fresh-$(date +%s)"
echo "--- Test 5: New session should NOT remember Charlie ---"
curl -s -X POST "$API_URL/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my name?\", \"session_id\": \"$NEW_SESSION\"}"
echo -e "\n"

echo "=== Tests Complete ==="
echo ""
echo "Expected results:"
echo "  - Test 2: Should mention 'Charlie'"
echo "  - Test 3: Should mention 'Python'"
echo "  - Test 4: Should show 6 messages"
echo "  - Test 5: Should NOT know the name (different session)"
```

### 3. Verify All Components

Run comprehensive verification:

```bash
# Make script executable
chmod +x scripts/test_conversation_memory.sh

# Rebuild with all changes
docker compose build mai-api
docker compose up -d mai-api
sleep 15

# Run automated tests (if pytest available in container)
docker exec mai-api python -m pytest tests/integration/test_conversation_memory.py -v 2>/dev/null || echo "Pytest not available, using manual tests"

# Run manual test script
./scripts/test_conversation_memory.sh
```

### 4. GUI Verification

Test in the Gradio GUI:

1. Open http://localhost:7860
2. Select `chat_agent`
3. Have a conversation:
   - "My favorite color is blue"
   - "What's my favorite color?"  (should remember blue)
   - "Tell me a joke about that color" (should know it's blue)
4. Click "New" to start fresh session
5. Ask "What's my favorite color?" (should NOT remember)

---

## Files to Create

- `tests/integration/test_conversation_memory.py` - Pytest integration tests
- `scripts/test_conversation_memory.sh` - Manual bash test script

## Files to Modify

- None (verification only)

---

## Success Criteria

```bash
# All these should pass:

# 1. Unit imports work
docker exec mai-api python -c "
from src.core.memory.message_converter import messages_to_model_messages
from src.core.memory.context_manager import ContextWindowManager
from src.core.memory.history_processors import create_default_processor
print('All imports successful')
"

# 2. Multi-turn memory works
SESSION="final-test-$(date +%s)"

# Set context
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"Remember that my favorite number is 42\", \"session_id\": \"$SESSION\"}" > /dev/null

sleep 2

# Recall should work
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"What is my favorite number?\", \"session_id\": \"$SESSION\"}")

echo "$RESPONSE" | grep -q "42" && echo "✅ Memory recall PASSED" || echo "❌ Memory recall FAILED"

# 3. No errors in logs
docker compose logs mai-api --tail 50 2>&1 | grep -i "error" | grep -v "INFO" || echo "✅ No errors in logs"

# 4. History endpoint works
curl -s "http://localhost:8000/api/v1/agents/history/$SESSION" | python3 -c "
import sys, json
data = json.load(sys.stdin)
count = data.get('message_count', 0)
print(f'✅ History has {count} messages' if count >= 2 else '❌ History missing')
"
```

**Final Checklist:**
- [ ] LLM recalls information from earlier in conversation
- [ ] Different sessions have separate memories
- [ ] History persists to Redis and survives restarts
- [ ] Token limiting prevents context overflow
- [ ] GUI multi-turn conversations work
- [ ] No errors in container logs

---

## On Completion

### Mark Task Done

```bash
curl -X PUT "http://localhost:8181/api/tasks/f8f78248-7288-4342-a60a-8ecfc30f0412" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

### Create Completion Document

```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI Conversation Memory Enhancement - Complete",
    "content": "# MAI Conversation Memory Enhancement\n\nAll 6 implementation tasks complete:\n\n1. ✅ Message Format Bridge - Converts between Redis and pydantic-ai formats\n2. ✅ Enhanced ConversationMemory - Stores ModelMessage objects natively\n3. ✅ Context Window Manager - Token counting with tiktoken and smart limiting\n4. ✅ ChatAgent Integration - Passes message history to LLM calls\n5. ✅ History Processors - Recency, token limit, and importance processors\n6. ✅ Testing & Verification - Integration tests and manual verification\n\n## Key Files\n\n- `src/core/memory/message_converter.py` - Format conversion\n- `src/core/memory/context_manager.py` - Token counting and limiting\n- `src/core/memory/history_processors.py` - Context optimization\n- `src/core/memory/short_term.py` - Enhanced ConversationMemory\n- `src/core/agents/chat_agent.py` - LLM integration\n\n## Usage\n\nConversation memory is now automatic. Use the same session_id to maintain context:\n\n```bash\ncurl -X POST \"http://localhost:8000/api/v1/agents/stream/chat_agent\" \\\n  -H \"Content-Type: application/json\" \\\n  -d \u0027{\"user_input\": \"My name is Alice\", \"session_id\": \"my-session\"}\u0027\n\ncurl -X POST \"http://localhost:8000/api/v1/agents/stream/chat_agent\" \\\n  -H \"Content-Type: application/json\" \\\n  -d \u0027{\"user_input\": \"What is my name?\", \"session_id\": \"my-session\"}\u0027\n# Response will mention Alice\n```\n\n## Verification\n\n```bash\n./scripts/test_conversation_memory.sh\n```",
    "project_id": "b1af63e6-f160-4637-ad68-2f8de402cb5f"
  }'
```

---

## Summary

The MAI Conversation Memory Enhancement is complete. The chat agent now:

1. **Remembers conversations** - Messages persist across requests within a session
2. **Uses proper pydantic-ai format** - Native ModelMessage objects for accurate context
3. **Manages context windows** - Token counting prevents overflow
4. **Optimizes history** - Processors keep relevant context, remove noise
5. **Persists to Redis** - Conversations survive container restarts

Multi-turn conversations should now work correctly in both the API and GUI.
