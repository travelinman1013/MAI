# Task: Enhance ConversationMemory for Pydantic-AI Native Storage

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Update ConversationMemory to store pydantic-ai native messages with proper serialization
**Sequence**: 2 of 6
**Depends On**: 01-message-format-bridge.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `25087d77-c56e-445d-b74e-664c777cb94e`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/25087d77-c56e-445d-b74e-664c777cb94e" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/25087d77-c56e-445d-b74e-664c777cb94e" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous task (01-message-format-bridge.md) created converter utilities to transform between MAI's simple Message format and pydantic-ai's ModelMessage format.

Now we need to enhance the `ConversationMemory` class to:
1. Store pydantic-ai native `ModelMessage` objects directly
2. Provide methods to get history in the format pydantic-ai expects
3. Maintain backward compatibility with existing simple Message format
4. Handle serialization/deserialization to Redis properly

The current `ConversationMemory` class (in `src/core/memory/short_term.py`) stores messages as:
```python
self.messages: List[Message] = []  # Simple Message objects
```

We need to add support for:
```python
self.model_messages: List[ModelMessage] = []  # Pydantic-AI native format
```

---

## Requirements

### 1. Add ModelMessage Storage to ConversationMemory

Update `src/core/memory/short_term.py` to store both formats:

```python
from typing import List, Optional, Dict, Any, Sequence
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from src.core.memory.message_converter import (
    messages_to_model_messages,
    model_messages_to_messages,
)

class ConversationMemory:
    REDIS_KEY_PREFIX = "conversation_memory:"
    REDIS_MODEL_KEY_PREFIX = "conversation_model_memory:"  # New prefix for native format

    def __init__(self, session_id: str, redis: RedisClient):
        # ... existing init code ...
        self.messages: List[Message] = []
        self.model_messages: List[ModelMessage] = []  # NEW: Native pydantic-ai format
        self._model_messages_adapter = ModelMessagesTypeAdapter
```

### 2. Add Method to Store Agent Result Messages

After an agent run, store the messages from the result:

```python
async def add_model_messages(
    self,
    model_messages: Sequence[ModelMessage],
    sync_simple_format: bool = True,
) -> None:
    """
    Add ModelMessage objects from an agent run result.

    Args:
        model_messages: Messages from result.new_messages() or result.all_messages()
        sync_simple_format: If True, also update self.messages for backward compat

    Example:
        result = await agent.run(user_input, message_history=memory.get_model_messages())
        await memory.add_model_messages(result.new_messages())
    """
    self.model_messages.extend(model_messages)

    if sync_simple_format:
        # Convert and sync to simple format for backward compatibility
        simple_messages = model_messages_to_messages(model_messages)
        self.messages.extend(simple_messages)

    await self.save_to_redis()
```

### 3. Add Method to Get Message History for Agent

```python
def get_model_messages(
    self,
    last_n_turns: Optional[int] = None,
    system_prompt: Optional[str] = None,
) -> List[ModelMessage]:
    """
    Get message history in pydantic-ai format for agent.run().

    Args:
        last_n_turns: Limit to last N conversation turns (user+assistant pairs)
        system_prompt: Optional system prompt to include

    Returns:
        List of ModelMessage objects for message_history parameter

    Example:
        history = memory.get_model_messages(last_n_turns=10)
        result = await agent.run(user_input, message_history=history)
    """
    if self.model_messages:
        # If we have native format, use it directly
        messages = self.model_messages
        if last_n_turns:
            # Approximate: each turn is ~2 messages (request + response)
            messages = messages[-(last_n_turns * 2):]
        return list(messages)

    # Fallback: Convert from simple format
    messages = self.messages
    if last_n_turns:
        messages = messages[-(last_n_turns * 2):]

    return messages_to_model_messages(messages, system_prompt=system_prompt)
```

### 4. Update Redis Persistence

Add methods to save/load ModelMessages:

```python
async def save_to_redis(self) -> None:
    """Save both message formats to Redis."""
    try:
        # Save simple format (existing behavior)
        messages_json = self._message_adapter.dump_json(self.messages).decode('utf-8')
        await self.redis.set(self._get_redis_key(), messages_json)

        # Save native ModelMessage format
        if self.model_messages:
            model_json = self._model_messages_adapter.dump_json(
                self.model_messages
            ).decode('utf-8')
            await self.redis.set(self._get_model_redis_key(), model_json)

        logger.debug(f"Conversation memory saved for session {self.session_id}")
    except Exception as e:
        logger.error(f"Failed to save conversation memory: {e}")

def _get_model_redis_key(self) -> str:
    """Get Redis key for ModelMessage storage."""
    return f"{self.REDIS_MODEL_KEY_PREFIX}{self.session_id}"

async def load_from_redis(self) -> None:
    """Load both message formats from Redis."""
    try:
        # Load simple format (existing behavior)
        messages_data = await self.redis.get(self._get_redis_key())
        if messages_data:
            if isinstance(messages_data, str):
                self.messages = self._message_adapter.validate_json(messages_data)
            elif isinstance(messages_data, list):
                self.messages = self._message_adapter.validate_python(messages_data)

        # Load native ModelMessage format
        model_data = await self.redis.get(self._get_model_redis_key())
        if model_data:
            if isinstance(model_data, str):
                self.model_messages = list(
                    self._model_messages_adapter.validate_json(model_data)
                )
            elif isinstance(model_data, list):
                self.model_messages = list(
                    self._model_messages_adapter.validate_python(model_data)
                )

        logger.debug(
            f"Loaded {len(self.messages)} simple messages, "
            f"{len(self.model_messages)} model messages for session {self.session_id}"
        )
    except Exception as e:
        logger.error(f"Failed to load conversation memory: {e}")
        self.messages = []
        self.model_messages = []
```

### 5. Add Clear Method for Both Formats

```python
async def clear(self) -> None:
    """Clear all conversation history."""
    self.messages = []
    self.model_messages = []
    await self.redis.delete(self._get_redis_key())
    await self.redis.delete(self._get_model_redis_key())
    logger.debug(f"Cleared conversation memory for session {self.session_id}")
```

---

## Files to Modify

- `src/core/memory/short_term.py` - Add ModelMessage support as described above

---

## Success Criteria

```bash
# Test enhanced ConversationMemory
docker exec mai-api python -c "
import asyncio
from src.core.memory.short_term import ConversationMemory
from src.infrastructure.cache.redis_client import RedisClient

async def test():
    redis = RedisClient()
    await redis.connect()

    memory = ConversationMemory(session_id='test-enhanced', redis=redis)
    await memory.load_from_redis()

    # Add simple message
    await memory.add_message(role='user', content='Hello')
    await memory.add_message(role='assistant', content='Hi there!')

    # Get as model messages
    model_msgs = memory.get_model_messages()
    print(f'Got {len(model_msgs)} model messages')

    # Verify round-trip through Redis
    memory2 = ConversationMemory(session_id='test-enhanced', redis=redis)
    await memory2.load_from_redis()
    print(f'Loaded {len(memory2.messages)} messages from Redis')

    # Cleanup
    await memory.clear()
    await redis.disconnect()
    print('Test passed!')

asyncio.run(test())
"
# Expected: Test passed!

# Verify no import errors
docker exec mai-api python -c "
from src.core.memory.short_term import ConversationMemory
from pydantic_ai.messages import ModelMessage
print('Imports successful')
"
# Expected: Imports successful
```

**Checklist:**
- [ ] `ConversationMemory` has `model_messages` attribute
- [ ] `get_model_messages()` method returns pydantic-ai format
- [ ] `add_model_messages()` method accepts agent result messages
- [ ] Both formats persist to Redis correctly
- [ ] Backward compatibility maintained (existing `add_message`, `get_messages` still work)

---

## Technical Notes

- **ModelMessagesTypeAdapter**: Import from `pydantic_ai.messages` - handles serialization
- **Dual storage**: Keep both formats for backward compatibility during migration
- **Redis keys**: Use different prefixes to avoid conflicts
- **Existing code location**: `src/core/memory/short_term.py`
- **Message converter**: `src/core/memory/message_converter.py` (from task 01)

---

## Important

- DO NOT break existing `add_message()` and `get_messages()` methods
- Handle Redis connection errors gracefully
- The `model_messages` list should stay in sync with `messages` when possible
- Test with both empty and populated conversation histories

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (03-context-window-manager.md) depends on this completing successfully
