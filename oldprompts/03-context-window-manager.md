# Task: Implement Context Window Manager with Token Counting

**Project**: MAI Conversation Memory Enhancement (`/Users/maxwell/Projects/MAI`)
**Goal**: Add proper token counting with tiktoken and smart context windowing
**Sequence**: 3 of 6
**Depends On**: 02-enhanced-conversation-memory.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `c6bb971d-b3f1-4c6e-813d-89042ae850d1`
- **Project ID**: `b1af63e6-f160-4637-ad68-2f8de402cb5f`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/c6bb971d-b3f1-4c6e-813d-89042ae850d1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/c6bb971d-b3f1-4c6e-813d-89042ae850d1" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous tasks created message format converters and enhanced ConversationMemory. Now we need to ensure conversations don't exceed the model's context window.

**The Problem:**
- LLMs have limited context windows (e.g., 4K, 8K, 32K, 128K tokens)
- Conversations can grow indefinitely
- Exceeding context limits causes errors or truncated responses
- Current token counting uses rough character approximation (inaccurate)

**The Solution:**
- Use `tiktoken` for accurate token counting (OpenAI-compatible models)
- Implement smart context windowing that preserves important messages
- Make context limits configurable per model

---

## Requirements

### 1. Add tiktoken Dependency

First, check if tiktoken is in dependencies. If not, add it:

```bash
# Check if tiktoken is installed
docker exec mai-api pip show tiktoken

# If not installed, add to pyproject.toml:
# tiktoken = "^0.7.0"
```

### 2. Create Context Window Manager Module

Create `src/core/memory/context_manager.py`:

```python
"""
Context window management for conversation memory.

Provides accurate token counting and smart truncation to fit model context limits.
"""

from typing import List, Optional, Sequence
from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    SystemPromptPart,
)

from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


# Default context limits for common models
MODEL_CONTEXT_LIMITS = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-3.5-turbo": 16385,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    # Local models via LM Studio typically have smaller contexts
    "local-default": 4096,
    "gemma": 8192,
}


@dataclass
class TokenCounter:
    """Token counter with tiktoken support and fallbacks."""

    encoding_name: str = "cl100k_base"  # GPT-4/ChatGPT encoding
    _encoder: Optional[any] = None

    def __post_init__(self):
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding(self.encoding_name)
            logger.debug(f"Using tiktoken encoder: {self.encoding_name}")
        except ImportError:
            logger.warning("tiktoken not available, using character approximation")
            self._encoder = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._encoder:
            return len(self._encoder.encode(text))
        # Fallback: ~4 chars per token
        return len(text) // 4

    def count_message_tokens(self, message: ModelMessage) -> int:
        """Count tokens in a ModelMessage."""
        total = 0

        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, (UserPromptPart, SystemPromptPart)):
                    content = part.content
                    if isinstance(content, str):
                        total += self.count_tokens(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, str):
                                total += self.count_tokens(item)
            # Add overhead for message structure (~4 tokens)
            total += 4

        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart):
                    total += self.count_tokens(part.content)
            total += 4

        return total

    def count_messages_tokens(self, messages: Sequence[ModelMessage]) -> int:
        """Count total tokens in a list of messages."""
        return sum(self.count_message_tokens(msg) for msg in messages)


class ContextWindowManager:
    """
    Manages conversation context to fit within model limits.

    Strategies:
    1. Sliding window - Keep most recent messages
    2. Smart truncation - Preserve system prompt and key messages
    3. Summary injection - Replace old messages with summary (future)
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        reserve_tokens: int = 1024,  # Reserve for response
        token_counter: Optional[TokenCounter] = None,
    ):
        """
        Initialize context manager.

        Args:
            max_tokens: Maximum context window size
            reserve_tokens: Tokens to reserve for model response
            token_counter: Optional custom token counter
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.token_counter = token_counter or TokenCounter()
        self.available_tokens = max_tokens - reserve_tokens

    @classmethod
    def for_model(cls, model_name: str, reserve_tokens: int = 1024) -> "ContextWindowManager":
        """Create context manager with appropriate limits for a model."""
        # Normalize model name
        model_lower = model_name.lower()

        # Find matching context limit
        max_tokens = MODEL_CONTEXT_LIMITS.get("local-default", 4096)
        for key, limit in MODEL_CONTEXT_LIMITS.items():
            if key in model_lower:
                max_tokens = limit
                break

        logger.info(f"Context manager for '{model_name}': {max_tokens} tokens")
        return cls(max_tokens=max_tokens, reserve_tokens=reserve_tokens)

    def fit_messages(
        self,
        messages: List[ModelMessage],
        system_prompt_tokens: int = 0,
    ) -> List[ModelMessage]:
        """
        Fit messages within context window using sliding window strategy.

        Args:
            messages: Full conversation history
            system_prompt_tokens: Tokens used by system prompt

        Returns:
            Truncated message list that fits within limits
        """
        if not messages:
            return []

        available = self.available_tokens - system_prompt_tokens
        total_tokens = self.token_counter.count_messages_tokens(messages)

        if total_tokens <= available:
            return messages

        logger.debug(
            f"Truncating messages: {total_tokens} tokens -> {available} available"
        )

        # Sliding window: Remove oldest messages until it fits
        result = list(messages)
        while result and self.token_counter.count_messages_tokens(result) > available:
            removed = result.pop(0)
            logger.debug(f"Removed message: {self.token_counter.count_message_tokens(removed)} tokens")

        return result

    def get_context_stats(
        self,
        messages: List[ModelMessage],
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Get statistics about context usage."""
        system_tokens = self.token_counter.count_tokens(system_prompt) if system_prompt else 0
        message_tokens = self.token_counter.count_messages_tokens(messages)

        return {
            "total_tokens": system_tokens + message_tokens,
            "system_prompt_tokens": system_tokens,
            "message_tokens": message_tokens,
            "max_tokens": self.max_tokens,
            "reserve_tokens": self.reserve_tokens,
            "available_tokens": self.available_tokens,
            "utilization_percent": round(
                (system_tokens + message_tokens) / self.available_tokens * 100, 1
            ),
        }


# Global default counter for convenience
_default_counter = TokenCounter()


def count_tokens(text: str) -> int:
    """Count tokens in text using default counter."""
    return _default_counter.count_tokens(text)
```

### 3. Integrate with ConversationMemory

Update `src/core/memory/short_term.py` to use the context manager:

```python
from src.core.memory.context_manager import ContextWindowManager, count_tokens

class ConversationMemory:
    # ... existing code ...

    def get_model_messages_with_limit(
        self,
        max_tokens: int = 4096,
        reserve_tokens: int = 1024,
        system_prompt: Optional[str] = None,
    ) -> List[ModelMessage]:
        """
        Get message history fitted to token limit.

        Args:
            max_tokens: Maximum context window
            reserve_tokens: Reserve for response
            system_prompt: System prompt to account for

        Returns:
            Messages that fit within the token budget
        """
        context_mgr = ContextWindowManager(
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens,
        )

        all_messages = self.get_model_messages(system_prompt=system_prompt)
        system_tokens = count_tokens(system_prompt) if system_prompt else 0

        return context_mgr.fit_messages(all_messages, system_tokens)
```

---

## Files to Create

- `src/core/memory/context_manager.py` - Token counting and context windowing

## Files to Modify

- `src/core/memory/short_term.py` - Add `get_model_messages_with_limit()` method
- `pyproject.toml` - Add tiktoken dependency if not present

---

## Success Criteria

```bash
# Test tiktoken is working
docker exec mai-api python -c "
import tiktoken
enc = tiktoken.get_encoding('cl100k_base')
tokens = enc.encode('Hello, world!')
print(f'Token count: {len(tokens)}')
"
# Expected: Token count: 4

# Test context manager
docker exec mai-api python -c "
from src.core.memory.context_manager import (
    TokenCounter,
    ContextWindowManager,
    count_tokens,
)

# Test token counting
counter = TokenCounter()
tokens = counter.count_tokens('Hello, this is a test message.')
print(f'Tokens in test: {tokens}')

# Test context manager
mgr = ContextWindowManager.for_model('gpt-4')
print(f'GPT-4 context limit: {mgr.max_tokens}')

mgr2 = ContextWindowManager.for_model('gemma')
print(f'Gemma context limit: {mgr2.max_tokens}')

print('Context manager tests passed!')
"
# Expected: Context manager tests passed!

# Test message fitting
docker exec mai-api python -c "
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from src.core.memory.context_manager import ContextWindowManager

# Create some messages
messages = []
for i in range(50):
    messages.append(ModelRequest(parts=[UserPromptPart(content=f'Question {i}: ' + 'x' * 100)]))
    messages.append(ModelResponse(parts=[TextPart(content=f'Answer {i}: ' + 'y' * 200)]))

# Fit to small context
mgr = ContextWindowManager(max_tokens=2000, reserve_tokens=500)
fitted = mgr.fit_messages(messages)
print(f'Original: {len(messages)} messages, Fitted: {len(fitted)} messages')

stats = mgr.get_context_stats(fitted)
print(f'Utilization: {stats[\"utilization_percent\"]}%')
print('Fitting test passed!')
"
# Expected: Fitting test passed!
```

**Checklist:**
- [ ] tiktoken installed and working
- [ ] TokenCounter accurately counts tokens
- [ ] ContextWindowManager fits messages to limits
- [ ] MODEL_CONTEXT_LIMITS includes common models
- [ ] Integration with ConversationMemory works

---

## Technical Notes

- **tiktoken encoding**: Use `cl100k_base` for GPT-4/ChatGPT models
- **Token overhead**: Each message has ~4 tokens of structure overhead
- **Reserve tokens**: Always reserve space for the model's response
- **Model detection**: Use substring matching for flexible model name handling
- **Fallback**: If tiktoken not available, use 4 chars/token approximation

---

## Important

- Always reserve tokens for the response (default 1024)
- The sliding window removes OLDEST messages first (preserves recency)
- System prompt tokens must be accounted for separately
- Don't count tokens multiple times - cache if needed for performance
- Local models (LM Studio) often have smaller context windows

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (04-chatagent-integration.md) depends on this completing successfully
