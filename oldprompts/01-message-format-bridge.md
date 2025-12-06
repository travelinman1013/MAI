# Task: Create Message Format Bridge for Pydantic-AI

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Create utilities to convert between Redis storage format and pydantic-ai ModelMessage types
**Sequence**: 1 of 6
**Depends On**: None (first step)

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `4715ad90-fcb9-4917-a8d8-3ff4d7d8e22e`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/4715ad90-fcb9-4917-a8d8-3ff4d7d8e22e" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/4715ad90-fcb9-4917-a8d8-3ff4d7d8e22e" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI framework currently stores conversation messages in Redis using a simple format:
```python
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

However, pydantic-ai 1.x requires `ModelMessage` objects for the `message_history` parameter:
- `ModelRequest` - Contains user prompts, system prompts, tool returns
- `ModelResponse` - Contains assistant responses, tool calls

The current `chat_agent.py` passes `message_history=None` because there's no conversion layer. This task creates that bridge.

**From pydantic-ai documentation:**
```python
result1 = agent.run_sync('Tell me a joke.')
result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
# new_messages() returns List[ModelMessage]
```

---

## Requirements

### 1. Create Message Converter Module

Create a new file `src/core/memory/message_converter.py` with utilities to convert between formats.

```python
"""
Message format converter for pydantic-ai compatibility.

Converts between:
- MAI's simple Message format (for Redis storage)
- pydantic-ai's ModelMessage format (ModelRequest, ModelResponse)
"""

from datetime import datetime
from typing import List, Sequence

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    SystemPromptPart,
)

from src.core.memory.models import Message


def messages_to_model_messages(
    messages: List[Message],
    system_prompt: str | None = None,
) -> List[ModelMessage]:
    """
    Convert MAI Message list to pydantic-ai ModelMessage list.

    Args:
        messages: List of MAI Message objects
        system_prompt: Optional system prompt to include in first request

    Returns:
        List of ModelMessage objects suitable for message_history parameter
    """
    # Implementation here
    pass


def model_messages_to_messages(
    model_messages: Sequence[ModelMessage],
) -> List[Message]:
    """
    Convert pydantic-ai ModelMessage list back to MAI Message format.

    Used for storing conversation history after agent runs.

    Args:
        model_messages: Sequence of ModelMessage from agent result

    Returns:
        List of MAI Message objects for Redis storage
    """
    # Implementation here
    pass
```

### 2. Implement messages_to_model_messages

This is the critical function for passing history to the LLM. It must:

1. Group consecutive user messages into `ModelRequest` with `UserPromptPart`
2. Group consecutive assistant messages into `ModelResponse` with `TextPart`
3. Optionally include system prompt in first `ModelRequest`

```python
def messages_to_model_messages(
    messages: List[Message],
    system_prompt: str | None = None,
) -> List[ModelMessage]:
    """Convert MAI Messages to pydantic-ai ModelMessages."""
    if not messages:
        return []

    model_messages: List[ModelMessage] = []

    for i, msg in enumerate(messages):
        if msg.role == "user":
            parts = []
            # Add system prompt to first user message only
            if i == 0 and system_prompt:
                parts.append(SystemPromptPart(content=system_prompt))
            parts.append(UserPromptPart(content=msg.content, timestamp=msg.timestamp))
            model_messages.append(ModelRequest(parts=parts))

        elif msg.role == "assistant":
            model_messages.append(
                ModelResponse(
                    parts=[TextPart(content=msg.content)],
                    model_name=msg.metadata.get("model_name"),
                )
            )

    return model_messages
```

### 3. Implement model_messages_to_messages

This extracts simple messages from pydantic-ai's complex format:

```python
def model_messages_to_messages(
    model_messages: Sequence[ModelMessage],
) -> List[Message]:
    """Convert pydantic-ai ModelMessages back to MAI Messages."""
    messages: List[Message] = []

    for model_msg in model_messages:
        if isinstance(model_msg, ModelRequest):
            for part in model_msg.parts:
                if isinstance(part, UserPromptPart):
                    messages.append(Message(
                        role="user",
                        content=part.content if isinstance(part.content, str) else str(part.content),
                        timestamp=part.timestamp or datetime.utcnow(),
                    ))
                # Skip SystemPromptPart - not stored in conversation

        elif isinstance(model_msg, ModelResponse):
            content_parts = []
            for part in model_msg.parts:
                if isinstance(part, TextPart):
                    content_parts.append(part.content)

            if content_parts:
                messages.append(Message(
                    role="assistant",
                    content="".join(content_parts),
                    metadata={"model_name": model_msg.model_name} if model_msg.model_name else {},
                ))

    return messages
```

### 4. Add Serialization Helpers

For storing ModelMessages directly in Redis (used in later tasks):

```python
def serialize_model_messages(messages: Sequence[ModelMessage]) -> str:
    """Serialize ModelMessages to JSON string for Redis storage."""
    import json
    from pydantic_ai.messages import ModelMessagesTypeAdapter

    return ModelMessagesTypeAdapter.dump_json(list(messages)).decode('utf-8')


def deserialize_model_messages(json_str: str) -> List[ModelMessage]:
    """Deserialize JSON string back to ModelMessages."""
    from pydantic_ai.messages import ModelMessagesTypeAdapter

    return list(ModelMessagesTypeAdapter.validate_json(json_str))
```

---

## Files to Create

- `src/core/memory/message_converter.py` - Main converter module with all functions above

## Files to Modify

- `src/core/memory/__init__.py` - Export the new converter functions (if exists)

---

## Success Criteria

```bash
# Test the converter module loads without errors
docker exec mai-api python -c "
from src.core.memory.message_converter import (
    messages_to_model_messages,
    model_messages_to_messages,
    serialize_model_messages,
    deserialize_model_messages,
)
print('All imports successful')
"
# Expected: All imports successful

# Test basic conversion
docker exec mai-api python -c "
from datetime import datetime
from src.core.memory.models import Message
from src.core.memory.message_converter import messages_to_model_messages, model_messages_to_messages

# Create test messages
msgs = [
    Message(role='user', content='Hello'),
    Message(role='assistant', content='Hi there!'),
    Message(role='user', content='How are you?'),
]

# Convert to model messages
model_msgs = messages_to_model_messages(msgs)
print(f'Converted to {len(model_msgs)} model messages')

# Convert back
restored = model_messages_to_messages(model_msgs)
print(f'Restored {len(restored)} messages')

# Verify content preserved
assert restored[0].content == 'Hello'
assert restored[1].content == 'Hi there!'
print('Round-trip conversion successful!')
"
# Expected: Round-trip conversion successful!
```

**Checklist:**
- [ ] `message_converter.py` created with all 4 functions
- [ ] Imports from pydantic_ai.messages work correctly
- [ ] Round-trip conversion preserves message content
- [ ] No errors in container logs

---

## Technical Notes

- **pydantic-ai message types**: Import from `pydantic_ai.messages`
- **ModelMessagesTypeAdapter**: Built-in adapter for JSON serialization
- **Existing Message model**: Located at `src/core/memory/models.py`
- **Part types to handle**:
  - `UserPromptPart` - User input
  - `TextPart` - Assistant text response
  - `SystemPromptPart` - System instructions
  - `ToolCallPart`, `ToolReturnPart` - Tool interactions (handle gracefully, may skip for now)

**Reference documentation**: Search Archon for "pydantic-ai message-history" for detailed API info.

---

## Important

- DO NOT modify the existing `Message` model - it's used throughout the codebase
- Handle cases where `part.content` might not be a string (could be list for multimodal)
- The converter must be stateless - no side effects
- Timestamp handling: Use `part.timestamp` if available, fallback to `datetime.utcnow()`

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (02-enhanced-conversation-memory.md) depends on this completing successfully
