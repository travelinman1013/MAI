# Task: Integrate Model Messages in Agent Framework

**Project**: MAI Gemini Code Fixes (`/Users/maxwell/Projects/MAI`)
**Goal**: Utilize add_model_messages() in BaseAgentFramework for proper pydantic-ai history storage
**Sequence**: 3 of 4
**Depends On**: 02-summarization-processor.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `fc9b07bf-2e18-4b65-ba3d-e4bbd2c61562`
- **Project ID**: `10d86559-2297-454d-8bae-320b033940d6`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/fc9b07bf-2e18-4b65-ba3d-e4bbd2c61562" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/fc9b07bf-2e18-4b65-ba3d-e4bbd2c61562" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/fc9b07bf-2e18-4b65-ba3d-e4bbd2c61562" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI Framework's `ConversationMemory` class maintains two parallel storage mechanisms:
1. `messages: List[Message]` - Simple role/content format for backward compatibility
2. `model_messages: List[ModelMessage]` - Native pydantic-ai format with full fidelity

Gemini's code check identified that `BaseAgentFramework.run_async()` only updates the simple `messages` list via `add_message()`, leaving the richer `model_messages` unused. This means:
- Tool call information is lost
- Token usage data is not preserved
- Multi-part messages are flattened

The previous tasks implemented tool call extraction (Task 1) and summarization (Task 2). This task connects the agent execution to proper memory storage, enabling features built in those tasks.

---

## Requirements

### 1. Store Model Messages After Agent Execution

Modify `run_async` to store the native pydantic-ai messages:

```python
# In src/core/agents/base.py, in run_async method

# After executing the agent:
result = await self.agent.run(
    user_input,
    deps=deps,
    message_history=message_history_for_agent
)

# Store both formats for compatibility
if conversation_memory:
    # Existing simple format storage
    await conversation_memory.add_message("assistant", result.output.model_dump_json())

    # NEW: Store native pydantic-ai format
    new_messages = result.new_messages()
    if new_messages:
        await conversation_memory.add_model_messages(new_messages)
        self.logger.debug(
            f"Stored {len(new_messages)} model messages for session {deps.session_id}"
        )

self.log_execution(start_time, True)
return result.output
```

### 2. Use Model Messages for History When Available

Modify the history loading to prefer `model_messages` when available:

```python
# In run_async, when loading history, prefer model_messages

if deps.redis and deps.session_id:
    conversation_memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
    deps.conversation_memory = conversation_memory

    await conversation_memory.load_from_redis()

    # Prefer native model_messages if available
    if conversation_memory.model_messages:
        message_history_for_agent = conversation_memory.model_messages
        self.logger.debug(
            f"Using {len(message_history_for_agent)} native model messages for session {deps.session_id}"
        )
    else:
        # Fallback to simple message conversion
        current_message_history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_memory.get_messages()
        ]
        message_history_for_agent = current_message_history
        self.logger.debug(
            f"Using {len(message_history_for_agent)} converted messages for session {deps.session_id}"
        )
```

### 3. Update run_stream for Consistency

Apply the same pattern to `run_stream`:

```python
# In src/core/agents/base.py, in run_stream method

async def run_stream(
    self,
    user_input: str,
    deps: AgentDependencies,
    message_history: Optional[list[Any]] = None
) -> AsyncIterator[Any]:
    """Execute the agent with streaming response."""
    start_time = time.time()
    self.validate_dependencies(deps)

    # Load conversation memory if available
    conversation_memory: Optional[ConversationMemory] = None
    loaded_history = None

    if deps.redis and deps.session_id:
        conversation_memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
        await conversation_memory.load_from_redis()

        # Prefer native format
        if conversation_memory.model_messages:
            loaded_history = conversation_memory.model_messages

    try:
        self.logger.info("Starting agent streaming execution")

        async with self.agent.run_stream(
            user_input,
            deps=deps,
            message_history=loaded_history or message_history
        ) as result:
            async for chunk in result.stream():
                yield chunk

            # After streaming complete, store messages
            if conversation_memory:
                await conversation_memory.add_message("user", user_input)
                await conversation_memory.add_message("assistant", str(result.output))
                # Store native format
                new_msgs = result.new_messages()
                if new_msgs:
                    await conversation_memory.add_model_messages(new_msgs)

        self.log_execution(start_time, True)

    except Exception as e:
        self.log_execution(start_time, False, e)
        raise AgentExecutionError(f"Agent '{self.name}' stream failed: {str(e)}") from e
```

### 4. Add Helper Method for Getting Proper History

Add a convenience method to the agent for getting properly formatted history:

```python
# In BaseAgentFramework class

async def get_message_history(
    self,
    deps: AgentDependencies,
    use_native_format: bool = True
) -> Optional[list]:
    """
    Get conversation history in the appropriate format.

    Args:
        deps: Agent dependencies with redis and session_id
        use_native_format: If True, return ModelMessage list when available

    Returns:
        Message history suitable for agent.run() or None
    """
    if not deps.redis or not deps.session_id:
        return None

    memory = ConversationMemory(session_id=deps.session_id, redis=deps.redis)
    await memory.load_from_redis()

    if use_native_format and memory.model_messages:
        return memory.model_messages

    # Fallback to simple dict format
    return [{"role": msg.role, "content": msg.content} for msg in memory.get_messages()]
```

---

## Files to Modify

- `src/core/agents/base.py` - Update `run_async`, `run_stream`, and add helper method

---

## Success Criteria

```bash
# Start Redis if not running
docker compose up -d redis

# Test conversation persistence with model messages
cd /Users/maxwell/Projects/MAI

cat > /tmp/test_memory.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/Users/maxwell/Projects/MAI')

from src.infrastructure.cache.redis_client import RedisClient
from src.core.memory.short_term import ConversationMemory

async def test():
    redis = RedisClient()
    await redis.connect()

    session_id = "test-model-messages-001"
    memory = ConversationMemory(session_id=session_id, redis=redis)

    # Clear any existing
    await memory.clear()

    # Simulate what the agent would store
    from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

    test_messages = [
        ModelRequest(parts=[UserPromptPart(content="Hello")]),
        ModelResponse(parts=[TextPart(content="Hi there!")])
    ]

    await memory.add_model_messages(test_messages)

    # Reload and verify
    memory2 = ConversationMemory(session_id=session_id, redis=redis)
    await memory2.load_from_redis()

    print(f"Stored model_messages: {len(memory2.model_messages)}")
    print(f"First message type: {type(memory2.model_messages[0])}")
    assert len(memory2.model_messages) == 2, "Should have 2 model messages"
    print("SUCCESS: Model messages stored and retrieved correctly")

    await memory.clear()
    await redis.close()

asyncio.run(test())
EOF

poetry run python /tmp/test_memory.py
# Expected: SUCCESS message
```

**Checklist:**
- [ ] `run_async` stores `model_messages` via `add_model_messages()`
- [ ] `run_async` loads `model_messages` when available for history
- [ ] `run_stream` follows the same pattern
- [ ] Fallback to simple message format works when `model_messages` empty
- [ ] No breaking changes to existing sessions without `model_messages`

---

## Technical Notes

- **Dual Storage**: Keep both formats - simple `messages` for API/UI display, `model_messages` for agent re-runs
- **Migration**: Old sessions without `model_messages` still work via fallback
- **Serialization**: `ModelMessagesTypeAdapter` handles JSON serialization in `ConversationMemory`
- **Order Matters**: Store user message before assistant response for proper conversation flow
- **Reference**: See `src/core/memory/short_term.py` for `add_model_messages()` implementation

---

## Important

- Do NOT remove the simple `add_message()` calls - they're needed for backward compatibility
- The `model_messages` may grow large - consider token limits in future tasks
- Test with BOTH new sessions and sessions that have existing simple messages only
- Ensure Redis connection errors don't crash agent execution

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (04-documentation-update.md) depends on this completing successfully
