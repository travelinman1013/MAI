# Task: Implement History Processors for Context Optimization

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Add message history processors for summarization and context optimization
**Sequence**: 5 of 6
**Depends On**: 04-chatagent-integration.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `b6a235aa-b58b-4910-b7fd-8c0f7baafde5`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/b6a235aa-b58b-4910-b7fd-8c0f7baafde5" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/b6a235aa-b58b-4910-b7fd-8c0f7baafde5" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous task integrated message history into ChatAgent. Now conversations work across turns, but we can optimize further.

**The Problem:**
- Long conversations waste tokens on less relevant old messages
- Simple sliding window may cut off important context
- Some messages are more important than others

**The Solution:**
History processors that can:
1. Filter out redundant or low-value messages
2. Summarize old conversation segments
3. Preserve important messages (user preferences, key facts)
4. Optimize context for the current query

**pydantic-ai supports history_processors:**
```python
# From pydantic-ai docs
agent = Agent(
    model=model,
    history_processors=[my_processor],  # Process messages before sending
)
```

---

## Requirements

### 1. Create History Processors Module

Create `src/core/memory/history_processors.py`:

```python
"""
Message history processors for context optimization.

Processors transform message history before sending to the LLM.
They can filter, summarize, or reorganize messages.
"""

from typing import List, Callable, Awaitable, Union
from abc import ABC, abstractmethod

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    SystemPromptPart,
)

from src.core.memory.context_manager import TokenCounter
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


# Type alias for processor functions
HistoryProcessor = Callable[
    [List[ModelMessage]],
    Union[List[ModelMessage], Awaitable[List[ModelMessage]]]
]


class BaseHistoryProcessor(ABC):
    """Base class for history processors."""

    @abstractmethod
    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Process and return modified message list."""
        pass

    def __call__(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        return self.process(messages)


class RecencyProcessor(BaseHistoryProcessor):
    """Keep only the most recent N turns."""

    def __init__(self, max_turns: int = 10):
        """
        Args:
            max_turns: Maximum conversation turns to keep (1 turn = user + assistant)
        """
        self.max_turns = max_turns

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        if len(messages) <= self.max_turns * 2:
            return messages

        # Keep last N*2 messages (each turn is ~2 messages)
        truncated = messages[-(self.max_turns * 2):]
        logger.debug(
            f"RecencyProcessor: {len(messages)} -> {len(truncated)} messages"
        )
        return truncated


class TokenLimitProcessor(BaseHistoryProcessor):
    """Limit history to fit within token budget."""

    def __init__(
        self,
        max_tokens: int = 3000,
        token_counter: TokenCounter = None,
    ):
        self.max_tokens = max_tokens
        self.counter = token_counter or TokenCounter()

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        total = self.counter.count_messages_tokens(messages)
        if total <= self.max_tokens:
            return messages

        # Remove oldest until we fit
        result = list(messages)
        while result and self.counter.count_messages_tokens(result) > self.max_tokens:
            result.pop(0)

        logger.debug(
            f"TokenLimitProcessor: {total} -> {self.counter.count_messages_tokens(result)} tokens"
        )
        return result


class ImportantMessageProcessor(BaseHistoryProcessor):
    """
    Preserve messages containing important keywords/patterns.

    Ensures key information (names, preferences, facts) isn't truncated.
    """

    def __init__(
        self,
        keywords: List[str] = None,
        always_keep_first: bool = True,
        max_important: int = 5,
    ):
        """
        Args:
            keywords: Words that mark a message as important
            always_keep_first: Always keep the first user message
            max_important: Maximum important messages to preserve
        """
        self.keywords = keywords or [
            "my name is",
            "i am",
            "remember",
            "important",
            "always",
            "never",
            "preference",
        ]
        self.always_keep_first = always_keep_first
        self.max_important = max_important

    def _is_important(self, message: ModelMessage) -> bool:
        """Check if message contains important keywords."""
        content = ""
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    if isinstance(part.content, str):
                        content = part.content.lower()
        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart):
                    content = part.content.lower()

        return any(kw.lower() in content for kw in self.keywords)

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        if not messages:
            return messages

        important_indices = set()

        # Mark first message as important
        if self.always_keep_first and messages:
            important_indices.add(0)
            if len(messages) > 1:
                important_indices.add(1)  # Keep first response too

        # Find important messages
        for i, msg in enumerate(messages):
            if self._is_important(msg) and len(important_indices) < self.max_important * 2:
                important_indices.add(i)
                # Also keep the response/follow-up
                if i + 1 < len(messages):
                    important_indices.add(i + 1)

        # This processor just marks importance - combine with others for truncation
        # For now, return all messages but log what's important
        logger.debug(
            f"ImportantMessageProcessor: {len(important_indices)} important messages identified"
        )
        return messages


class ChainedProcessor(BaseHistoryProcessor):
    """Chain multiple processors together."""

    def __init__(self, processors: List[BaseHistoryProcessor]):
        self.processors = processors

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        result = messages
        for processor in self.processors:
            result = processor.process(result)
        return result


def create_default_processor(
    max_turns: int = 15,
    max_tokens: int = 3000,
) -> ChainedProcessor:
    """Create a sensible default processor chain."""
    return ChainedProcessor([
        ImportantMessageProcessor(),  # Mark important messages
        RecencyProcessor(max_turns=max_turns),  # Keep recent
        TokenLimitProcessor(max_tokens=max_tokens),  # Fit token limit
    ])


# Convenience functions for simple use cases

def limit_by_turns(messages: List[ModelMessage], max_turns: int = 10) -> List[ModelMessage]:
    """Simple function to limit messages by turn count."""
    return RecencyProcessor(max_turns=max_turns).process(messages)


def limit_by_tokens(messages: List[ModelMessage], max_tokens: int = 3000) -> List[ModelMessage]:
    """Simple function to limit messages by token count."""
    return TokenLimitProcessor(max_tokens=max_tokens).process(messages)
```

### 2. Integrate with ChatAgent

Update `src/core/agents/chat_agent.py` to use processors:

```python
from src.core.memory.history_processors import (
    create_default_processor,
    limit_by_tokens,
)

class ChatAgent(BaseAgentFramework):
    # ... existing code ...

    def __init__(
        self,
        # ... existing params ...
        history_processor: Optional[Callable] = None,
    ):
        # ... existing init ...
        self.history_processor = history_processor or create_default_processor(
            max_turns=15,
            max_tokens=self.max_context_tokens - self.reserve_tokens,
        )
```

Then in `run_async` and `run_stream`, apply the processor:

```python
# Get and process message history
history: List[ModelMessage] = []
if conversation_memory:
    raw_history = conversation_memory.get_model_messages()
    history = self.history_processor(raw_history) if self.history_processor else raw_history
    logger.debug(
        f"History: {len(raw_history)} raw -> {len(history)} processed messages"
    )
```

### 3. Add Async Summary Processor (Advanced - Optional)

For very long conversations, add a summarization processor:

```python
class SummaryProcessor(BaseHistoryProcessor):
    """
    Replace old messages with a summary.

    Note: Requires an LLM call, so use sparingly.
    This is a placeholder - full implementation would need
    access to an agent for summarization.
    """

    def __init__(
        self,
        threshold_messages: int = 20,
        summary_prompt: str = "Summarize the key points from this conversation:",
    ):
        self.threshold = threshold_messages
        self.summary_prompt = summary_prompt

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        if len(messages) < self.threshold:
            return messages

        # For now, just truncate. Full implementation would:
        # 1. Take oldest messages
        # 2. Send to LLM for summary
        # 3. Replace with single summary message
        # 4. Keep recent messages as-is

        logger.info(
            f"SummaryProcessor: Would summarize {len(messages) - 10} old messages"
        )

        # Keep last 10 messages
        return messages[-10:]
```

---

## Files to Create

- `src/core/memory/history_processors.py` - All processor classes

## Files to Modify

- `src/core/agents/chat_agent.py` - Integrate processor into agent
- `src/core/memory/__init__.py` - Export processors (if needed)

---

## Success Criteria

```bash
# Test processors module
docker exec mai-api python -c "
from src.core.memory.history_processors import (
    RecencyProcessor,
    TokenLimitProcessor,
    ChainedProcessor,
    create_default_processor,
    limit_by_turns,
)
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

# Create test messages
messages = []
for i in range(30):
    messages.append(ModelRequest(parts=[UserPromptPart(content=f'Question {i}')]))
    messages.append(ModelResponse(parts=[TextPart(content=f'Answer {i}')]))

print(f'Original: {len(messages)} messages')

# Test recency processor
recency = RecencyProcessor(max_turns=5)
result = recency.process(messages)
print(f'After recency (5 turns): {len(result)} messages')

# Test token limit processor
token_limit = TokenLimitProcessor(max_tokens=500)
result2 = token_limit.process(messages)
print(f'After token limit (500): {len(result2)} messages')

# Test default processor
default = create_default_processor(max_turns=10, max_tokens=1000)
result3 = default.process(messages)
print(f'After default processor: {len(result3)} messages')

print('All processor tests passed!')
"
# Expected: All processor tests passed!

# Rebuild and test integration
docker compose build mai-api && docker compose up -d mai-api && sleep 10

# Test that long conversations still work
for i in {1..5}; do
  curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
    -H "Content-Type: application/json" \
    -d "{\"user_input\": \"Message number $i - remember this\", \"session_id\": \"processor-test\"}" > /dev/null
done

# Should still recall earlier messages
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What number message did I start with?", "session_id": "processor-test"}'
echo ""
# Expected: Should mention "1" or "Message number 1"
```

**Checklist:**
- [ ] All processor classes created and working
- [ ] Processors can be chained together
- [ ] ChatAgent uses processors for history management
- [ ] Token limiting prevents context overflow
- [ ] Recency processor keeps recent messages

---

## Technical Notes

- **Processor order matters**: Run importance detection before truncation
- **Token budget**: Leave room for system prompt + user input + response
- **Async support**: Processors can be sync or async (for future LLM-based summarization)
- **pydantic-ai integration**: Can also pass processors to Agent constructor

**File locations:**
- New processors: `src/core/memory/history_processors.py`
- ChatAgent: `src/core/agents/chat_agent.py`

---

## Important

- Processors should be FAST - they run on every request
- Don't make LLM calls in processors unless absolutely necessary
- The default processor should work for 90% of cases
- Log what's being truncated for debugging
- Test with long conversations to verify no regressions

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (06-testing-verification.md) is the final task
