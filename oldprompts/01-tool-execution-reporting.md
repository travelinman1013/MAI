# Task: Implement Tool Execution Reporting

**Project**: MAI Gemini Code Fixes (`/Users/maxwell/Projects/MAI`)
**Goal**: Extract and return tool calls from pydantic-ai agent execution results
**Sequence**: 1 of 4
**Depends On**: None (first step)

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `b66e850b-bafb-4c53-8c37-80e50f9bcf3c`
- **Project ID**: `10d86559-2297-454d-8bae-320b033940d6`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/b66e850b-bafb-4c53-8c37-80e50f9bcf3c" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/b66e850b-bafb-4c53-8c37-80e50f9bcf3c" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/b66e850b-bafb-4c53-8c37-80e50f9bcf3c" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI Framework uses pydantic-ai for agent execution. Currently, the `/api/agents/run/{agent_name}` endpoint returns an empty `tool_calls` array (line 330 in `agents.py`), which means the frontend has no visibility into what tools the agent used during execution.

Gemini's code check identified this as a missing feature that should be implemented. The pydantic-ai library provides access to tool call information through the `result.all_messages()` method, which returns a list of `ModelMessage` objects containing `ToolCallPart` and `ToolReturnPart` for each tool invocation.

This task will modify the agent execution flow to capture tool calls and return them in the API response, giving the React frontend full visibility into agent tool usage.

---

## Requirements

### 1. Modify BaseAgentFramework to Return Full Result

The `run_async` method currently returns only `result.output`. Modify it to return the full result object so tool calls can be extracted.

```python
# In src/core/agents/base.py, modify run_async return
# Currently returns: result.output
# Should return: result (the full AgentRunResult object)

# The caller can then access:
# - result.output (the structured output)
# - result.all_messages() (full message history including tool calls)
# - result.new_messages() (just messages from this run)
```

### 2. Create Tool Call Extraction Helper

Create a helper function to extract tool calls from pydantic-ai messages:

```python
# In src/api/routes/agents.py or a new utility file

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from src.api.schemas.agents import ToolCallInfo
from typing import List
import time

def extract_tool_calls(messages: List[ModelMessage]) -> List[ToolCallInfo]:
    """
    Extract tool call information from pydantic-ai message history.

    Args:
        messages: List of ModelMessage from result.all_messages() or result.new_messages()

    Returns:
        List of ToolCallInfo objects for the API response
    """
    tool_calls = []
    tool_call_parts = {}  # Map tool_call_id to ToolCallPart

    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    # Store the call for matching with return
                    tool_call_parts[part.tool_call_id] = {
                        'tool_name': part.tool_name,
                        'arguments': part.args if hasattr(part, 'args') else {},
                        'start_time': time.time()
                    }
                elif isinstance(part, ToolReturnPart):
                    # Match with the call and create ToolCallInfo
                    call_info = tool_call_parts.get(part.tool_call_id)
                    if call_info:
                        tool_calls.append(ToolCallInfo(
                            tool_name=call_info['tool_name'],
                            arguments=call_info['arguments'],
                            result=part.content,
                            duration_ms=0.0,  # Not tracked at message level
                            success=True,
                            error=None
                        ))

    return tool_calls
```

### 3. Update run_agent Endpoint

Modify the `run_agent` function to extract and return tool calls:

```python
# In src/api/routes/agents.py, in the run_agent function

# Execute agent with optional images
result = await agent_instance.run_async(
    user_input=request.user_input,
    deps=deps,
    images=request.images,
)

# Extract tool calls from execution
# Note: This requires run_async to return the full result
tool_calls = extract_tool_calls(result.new_messages())

# Build response with actual tool calls
response = AgentRunResponse(
    success=True,
    agent_name=agent_name,
    session_id=request.session_id,
    result=result.output.model_dump() if hasattr(result.output, 'model_dump') else {"data": str(result.output)},
    tool_calls=tool_calls,  # Now populated!
    execution_time_ms=execution_time_ms,
    timestamp=datetime.utcnow()
)
```

---

## Files to Modify

- `src/core/agents/base.py` - Modify `run_async` to return full result object (create wrapper type if needed)
- `src/api/routes/agents.py` - Add `extract_tool_calls` helper and update `run_agent` endpoint

---

## Success Criteria

```bash
# Start the API server
cd /Users/maxwell/Projects/MAI && poetry run python -m uvicorn src.api.main:app --reload &

# Test with an agent that uses tools (if available)
curl -X POST "http://localhost:8000/api/agents/run/simple" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello, what can you do?"}'
# Expected: Response includes "tool_calls" array (may be empty if no tools used)

# Verify the response schema
curl -s -X POST "http://localhost:8000/api/agents/run/simple" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test"}' | python -c "import sys,json; d=json.load(sys.stdin); print('tool_calls' in d)"
# Expected: True
```

**Checklist:**
- [ ] `run_async` returns information needed to extract tool calls
- [ ] `extract_tool_calls` helper function implemented
- [ ] `run_agent` endpoint populates `tool_calls` in response
- [ ] No breaking changes to existing API consumers
- [ ] Type hints and docstrings added

---

## Technical Notes

- **Pydantic-AI Result API**: `result.all_messages()` returns full history, `result.new_messages()` returns only messages from this run
- **Message Types**: `ModelResponse` contains `ToolCallPart` (the call) and `ToolReturnPart` (the result) in its `parts` list
- **ToolCallPart attributes**: `tool_name`, `tool_call_id`, `args` (dict of arguments)
- **ToolReturnPart attributes**: `tool_call_id`, `content` (the return value)
- **Reference**: Search Archon for "pydantic-ai ToolCallPart ToolReturnPart" for detailed API docs

---

## Important

- Do NOT change the `AgentRunResponse` schema - it already has `tool_calls: List[ToolCallInfo]`
- Maintain backward compatibility - agents that don't use tools should return empty `tool_calls` list
- Handle cases where tool calls fail gracefully (set `success=False`, populate `error`)

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (02-summarization-processor.md) depends on this completing successfully
