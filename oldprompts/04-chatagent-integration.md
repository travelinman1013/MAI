# Task: Integrate Message History into ChatAgent

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Update ChatAgent to pass message history to agent.run() and agent.run_stream()
**Sequence**: 4 of 6
**Depends On**: 03-context-window-manager.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `5c28cc63-7dbf-469c-b19e-d9c1a266423f`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/5c28cc63-7dbf-469c-b19e-d9c1a266423f" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/5c28cc63-7dbf-469c-b19e-d9c1a266423f" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous tasks created:
1. Message format converters (Task 01)
2. Enhanced ConversationMemory with ModelMessage support (Task 02)
3. Context window manager with token counting (Task 03)

Now we integrate everything into the ChatAgent. Currently, the agent passes `message_history=None`:

```python
# Current code in chat_agent.py (BROKEN)
result = await self.agent.run(
    user_input,
    deps=deps,
    message_history=None,  # TODO: convert to ModelMessage format if needed
)
```

This task fixes this by passing the actual conversation history.

**Key pydantic-ai pattern:**
```python
# From pydantic-ai docs
result1 = agent.run_sync('Tell me a joke.')
result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
```

---

## Requirements

### 1. Update ChatAgent Imports

Add necessary imports at the top of `src/core/agents/chat_agent.py`:

```python
from pydantic_ai.messages import ModelMessage

from src.core.memory.context_manager import ContextWindowManager
```

### 2. Update run_async Method

Modify the `run_async` method to pass message history:

```python
async def run_async(
    self,
    user_input: str,
    deps: AgentDependencies,
    message_history: Optional[Any] = None,
) -> StandardResponse[ChatResponse]:
    """Execute with LLM, passing conversation history for context."""

    # Initialize conversation memory if we have Redis and session
    conversation_memory: Optional[ConversationMemory] = None
    if deps.redis and deps.session_id:
        conversation_memory = ConversationMemory(
            session_id=deps.session_id, redis=deps.redis
        )
        await conversation_memory.load_from_redis()

    if self._fallback_mode:
        return await self._echo_response(user_input, deps, conversation_memory)

    try:
        # Get message history for context (with token limiting)
        history: List[ModelMessage] = []
        if conversation_memory:
            # Use context manager to fit within limits
            # Reserve tokens for system prompt + user input + response
            history = conversation_memory.get_model_messages_with_limit(
                max_tokens=4096,  # Adjust based on model
                reserve_tokens=1500,  # Space for input + response
                system_prompt=self.system_prompt,
            )
            logger.debug(f"Loaded {len(history)} messages for context")

        # Add user message to memory BEFORE the LLM call
        if conversation_memory:
            await conversation_memory.add_message(role="user", content=user_input)

        # Call Pydantic AI agent WITH message history
        result = await self.agent.run(
            user_input,
            deps=deps,
            message_history=history if history else None,
        )

        # Get response content
        content = result.output

        # Add assistant response to memory
        if conversation_memory:
            await conversation_memory.add_message(role="assistant", content=content)
            # Also store the native model messages for better fidelity
            await conversation_memory.add_model_messages(
                result.new_messages(),
                sync_simple_format=False,  # Already added above
            )

        logger.info(
            "LLM response generated with context",
            agent=self.name,
            history_messages=len(history),
        )

        return StandardResponse(
            data=ChatResponse(role="assistant", content=content)
        )

    except Exception as e:
        logger.warning(
            f"LLM call failed, falling back to echo: {e}", agent=self.name
        )
        return await self._echo_response(user_input, deps, conversation_memory)
```

### 3. Update run_stream Method

Similarly update streaming to use message history:

```python
async def run_stream(
    self,
    user_input: str,
    deps: AgentDependencies,
    message_history: Optional[Any] = None,
) -> AsyncIterator[StandardResponse[ChatResponse]]:
    """Stream with LLM, using conversation history for context."""

    # Initialize conversation memory
    conversation_memory: Optional[ConversationMemory] = None
    if deps.redis and deps.session_id:
        conversation_memory = ConversationMemory(
            session_id=deps.session_id, redis=deps.redis
        )
        await conversation_memory.load_from_redis()

    if self._fallback_mode:
        async for chunk in self._echo_stream(user_input, deps, conversation_memory):
            yield chunk
        return

    try:
        # Get message history with token limiting
        history: List[ModelMessage] = []
        if conversation_memory:
            history = conversation_memory.get_model_messages_with_limit(
                max_tokens=4096,
                reserve_tokens=1500,
                system_prompt=self.system_prompt,
            )
            logger.debug(f"Streaming with {len(history)} history messages")

        # Add user message to memory before streaming
        if conversation_memory:
            await conversation_memory.add_message(role="user", content=user_input)

        # Stream from Pydantic AI agent WITH message history
        async with self.agent.run_stream(
            user_input,
            deps=deps,
            message_history=history if history else None,
        ) as result:
            # pydantic-ai 1.x stream() yields accumulated text, not deltas
            previous_text = ""
            async for chunk in result.stream():
                accumulated = str(chunk)
                delta = accumulated[len(previous_text):]
                previous_text = accumulated
                if delta:
                    yield StandardResponse(
                        data=ChatResponse(role="assistant", content=delta)
                    )
            full_response = previous_text

        # Save response to memory after streaming completes
        if conversation_memory and full_response:
            await conversation_memory.add_message(
                role="assistant", content=full_response
            )
            # Store native model messages
            await conversation_memory.add_model_messages(
                result.new_messages(),
                sync_simple_format=False,
            )

        logger.info(
            "LLM streaming completed with context",
            agent=self.name,
            history_messages=len(history),
        )

    except Exception as e:
        logger.warning(
            f"LLM streaming failed, falling back to echo: {e}", agent=self.name
        )
        async for chunk in self._echo_stream(user_input, deps, conversation_memory):
            yield chunk
```

### 4. Add Context Configuration

Add configuration for context window size:

```python
class ChatAgent(BaseAgentFramework):
    """Production chat agent with LLM support and conversation memory."""

    name = "chat_agent"
    description = "AI-powered chat agent with conversation memory"

    # Context window configuration
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_RESERVE_TOKENS = 1500

    def __init__(
        self,
        name: str = "chat_agent",
        model: Optional[Model] = None,
        result_type: Type[BaseModel] = ChatResponse,
        system_prompt: str = "You are a helpful AI assistant. Be concise and helpful in your responses.",
        tools: Optional[List[tuple[Callable[..., Any], ToolMetadata]]] = None,
        max_context_tokens: int = DEFAULT_MAX_TOKENS,
        reserve_tokens: int = DEFAULT_RESERVE_TOKENS,
    ):
        self._fallback_mode = model is None
        self.max_context_tokens = max_context_tokens
        self.reserve_tokens = reserve_tokens

        # ... rest of existing __init__ ...
```

---

## Files to Modify

- `src/core/agents/chat_agent.py` - Full integration as described above

---

## Success Criteria

```bash
# Rebuild the container
docker compose build mai-api && docker compose up -d mai-api && sleep 10

# Test multi-turn conversation
echo "Testing multi-turn conversation..."

# Turn 1
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "My name is Alice", "session_id": "memory-test-1"}'
echo ""

# Turn 2 - should remember the name
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What is my name?", "session_id": "memory-test-1"}'
echo ""
# Expected: Response should mention "Alice"

# Turn 3 - follow-up
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Tell me a joke about my name", "session_id": "memory-test-1"}'
echo ""
# Expected: Response should include a joke related to "Alice"

# Verify memory was stored
curl -s "http://localhost:8000/api/v1/agents/history/memory-test-1"
# Expected: Should show all 6 messages (3 user, 3 assistant)
```

**Checklist:**
- [ ] Agent correctly recalls information from earlier in conversation
- [ ] Message history is passed to `agent.run()` and `agent.run_stream()`
- [ ] Context window limiting prevents token overflow
- [ ] Messages are stored in both simple and ModelMessage format
- [ ] No regression in echo fallback mode

---

## Technical Notes

- **message_history parameter**: Pass `None` if empty, not empty list
- **result.new_messages()**: Returns only messages from current run
- **result.all_messages()**: Returns all messages including history
- **Context limit**: Start conservative (4096), can increase for larger context models
- **Reserve tokens**: Must account for user input + expected response length

**Important file locations:**
- Chat agent: `src/core/agents/chat_agent.py`
- ConversationMemory: `src/core/memory/short_term.py`
- Context manager: `src/core/memory/context_manager.py`

---

## Important

- Test with SAME session_id to verify memory works
- The LLM MUST be able to recall previous messages in the conversation
- Don't break streaming - the delta extraction logic must remain intact
- Log the number of history messages for debugging
- Handle edge case: first message in conversation (empty history)

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass - especially that the LLM recalls "Alice"
3. The next task (05-history-processors.md) depends on this completing successfully
