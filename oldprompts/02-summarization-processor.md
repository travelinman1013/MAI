# Task: Implement LLM-Based Summarization Processor

**Project**: MAI Gemini Code Fixes (`/Users/maxwell/Projects/MAI`)
**Goal**: Implement actual LLM summarization logic in the SummaryProcessor class
**Sequence**: 2 of 4
**Depends On**: 01-tool-execution-reporting.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `1d5e6ccd-34c9-4b19-94dc-9cf9ef63dd9d`
- **Project ID**: `10d86559-2297-454d-8bae-320b033940d6`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/1d5e6ccd-34c9-4b19-94dc-9cf9ef63dd9d" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/1d5e6ccd-34c9-4b19-94dc-9cf9ef63dd9d" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/1d5e6ccd-34c9-4b19-94dc-9cf9ef63dd9d" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI Framework includes a `SummaryProcessor` class in `src/core/memory/history_processors.py` that is designed to summarize old conversation messages to reduce token usage. Currently, this class has a TODO comment and simply returns messages unchanged without any summarization.

Gemini's code check identified this as incomplete functionality. When conversations grow long, they can exceed context window limits. The SummaryProcessor should use an LLM to create compact summaries of older messages while preserving key information.

The previous task (01-tool-execution-reporting) modified the agent execution flow. This task focuses on the memory/history processing layer.

---

## Requirements

### 1. Implement Async Summarization Method

Add an async method to call an LLM for summarization:

```python
# In src/core/memory/history_processors.py

from typing import List, Optional
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai import Agent
from pydantic import BaseModel

class SummaryOutput(BaseModel):
    """Structured output for conversation summary."""
    summary: str
    key_points: List[str]
    preserved_context: str

class SummaryProcessor(BaseHistoryProcessor):
    """
    Summarizes old messages using an LLM to reduce token count
    while preserving key information.
    """

    def __init__(
        self,
        summary_threshold: int = 20,
        keep_recent: int = 6,
        model_name: str = "openai:gpt-4o-mini",
    ):
        """
        Initialize summary processor.

        Args:
            summary_threshold: Number of messages before summarization kicks in
            keep_recent: Number of recent messages to always keep intact
            model_name: LLM model to use for summarization
        """
        self.summary_threshold = summary_threshold
        self.keep_recent = keep_recent
        self.model_name = model_name
        self._summary_agent: Optional[Agent] = None

    def _get_summary_agent(self) -> Agent:
        """Lazy initialization of summary agent."""
        if self._summary_agent is None:
            self._summary_agent = Agent(
                self.model_name,
                output_type=SummaryOutput,
                system_prompt="""You are a conversation summarizer. Given a conversation history,
create a concise summary that preserves:
1. Key decisions and conclusions
2. Important facts mentioned
3. User preferences or requirements stated
4. Any action items or todos

Be concise but preserve context needed to continue the conversation meaningfully."""
            )
        return self._summary_agent
```

### 2. Implement Message-to-Text Conversion

Add a helper to convert ModelMessages to text for summarization:

```python
def _messages_to_text(self, messages: List[ModelMessage]) -> str:
    """Convert ModelMessages to readable text for summarization."""
    lines = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if hasattr(part, 'content'):
                    lines.append(f"User: {part.content}")
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    lines.append(f"Assistant: {part.content}")
    return "\n\n".join(lines)
```

### 3. Implement Async Process Method

Create an async version of the process method:

```python
async def process_async(self, messages: List[ModelMessage]) -> List[ModelMessage]:
    """
    Async summarization of old messages.

    Args:
        messages: Full conversation history

    Returns:
        Messages with older portion summarized into a single message
    """
    if len(messages) <= self.summary_threshold:
        return messages

    # Split: old messages to summarize, recent messages to keep
    split_point = len(messages) - self.keep_recent
    old_messages = messages[:split_point]
    recent_messages = messages[split_point:]

    # Convert old messages to text
    conversation_text = self._messages_to_text(old_messages)

    # Get summary from LLM
    agent = self._get_summary_agent()
    result = await agent.run(
        f"Summarize this conversation:\n\n{conversation_text}"
    )

    # Create summary message
    summary_text = f"""[CONVERSATION SUMMARY]
{result.output.summary}

Key Points:
{chr(10).join(f"- {point}" for point in result.output.key_points)}

Context: {result.output.preserved_context}
[END SUMMARY]"""

    # Create a ModelRequest with the summary as a system-like message
    summary_message = ModelRequest(
        parts=[UserPromptPart(content=f"[Previous conversation summary]: {summary_text}")]
    )

    return [summary_message] + recent_messages
```

### 4. Keep Sync Process Method as Fallback

The sync `process` method should remain for compatibility but log a warning:

```python
def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
    """
    Synchronous fallback - returns messages unchanged.

    For actual summarization, use process_async().
    """
    import logging
    logger = logging.getLogger(__name__)

    if len(messages) > self.summary_threshold:
        logger.warning(
            f"SummaryProcessor: {len(messages)} messages exceed threshold "
            f"({self.summary_threshold}), but sync processing cannot summarize. "
            "Use process_async() for LLM summarization."
        )

    return messages
```

---

## Files to Modify

- `src/core/memory/history_processors.py` - Implement full SummaryProcessor class

---

## Success Criteria

```bash
# Run the test to verify SummaryProcessor works
cd /Users/maxwell/Projects/MAI

# Create a quick test script
cat > /tmp/test_summary.py << 'EOF'
import asyncio
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

# Add project to path
import sys
sys.path.insert(0, '/Users/maxwell/Projects/MAI')

from src.core.memory.history_processors import SummaryProcessor

async def test():
    processor = SummaryProcessor(summary_threshold=4, keep_recent=2)

    # Create test messages
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Hello, I need help with Python")]),
        ModelResponse(parts=[TextPart(content="Hi! I'd be happy to help with Python.")]),
        ModelRequest(parts=[UserPromptPart(content="How do I read a file?")]),
        ModelResponse(parts=[TextPart(content="Use open() with a context manager.")]),
        ModelRequest(parts=[UserPromptPart(content="What about JSON files?")]),
        ModelResponse(parts=[TextPart(content="Use the json module with json.load().")]),
    ]

    print(f"Original: {len(messages)} messages")
    result = await processor.process_async(messages)
    print(f"After processing: {len(result)} messages")
    print(f"First message preview: {str(result[0])[:200]}...")

asyncio.run(test())
EOF

poetry run python /tmp/test_summary.py
# Expected: Shows reduced message count with summary
```

**Checklist:**
- [ ] `SummaryProcessor` has `process_async` method implemented
- [ ] LLM is called to generate summaries when threshold exceeded
- [ ] Recent messages are preserved intact
- [ ] Sync `process` method logs warning and returns unchanged
- [ ] Proper error handling for LLM failures

---

## Technical Notes

- **Lazy Agent Init**: Initialize the summarization agent lazily to avoid startup overhead
- **Model Choice**: Use a fast/cheap model like `gpt-4o-mini` for summarization
- **Structured Output**: Use `SummaryOutput` Pydantic model for reliable extraction
- **Token Efficiency**: The summary should be significantly shorter than the original messages
- **Fallback**: If LLM fails, return original messages rather than crashing
- **Reference**: Pydantic-AI has built-in `history_processors` parameter - search Archon for examples

---

## Important

- Do NOT block the sync `process` method with async calls - keep it as a passthrough
- Handle LLM API failures gracefully - log error and return original messages
- Preserve the most recent messages ALWAYS - they contain immediate context
- The summary should be human-readable if a user inspects conversation history

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (03-memory-integration.md) depends on this completing successfully
