# Task: Fix safe_stream_response() Error Handling for Consistency

**Project**: UI Robustness Overhaul (`/Users/maxwell/Projects/MAI`)
**Goal**: Update error handlers in safe_stream_response() to use dict format instead of tuple indexing
**Sequence**: 3 of 4
**Depends On**: 02-explicit-chatbot-type.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `b5a50e79-5621-4387-84a5-552810d96abe`
- **Project ID**: `a4058f0e-7162-4ef6-8464-1dfe16809b09`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/b5a50e79-5621-4387-84a5-552810d96abe" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/b5a50e79-5621-4387-84a5-552810d96abe" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/b5a50e79-5621-4387-84a5-552810d96abe" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

In previous steps, we:
1. Fixed `stream_response_with_attachments()` to use dict format
2. Added explicit `type="messages"` to the Chatbot component

Now we need to fix `safe_stream_response()` for consistency. This wrapper function handles errors from streaming responses and currently uses tuple indexing (`history[-1][1] = ...`). While this function may not be actively used in the main flow (errors are handled inline), it should be updated to use dict format for:
1. Code consistency across the codebase
2. Preventing future bugs if this wrapper is used
3. Clean architecture

---

## Requirements

### 1. Fix ConnectionError Handler (line ~356)

**Current code:**
```python
except ConnectionError as e:
    history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
    if history and len(history) > 0:
        history[-1][1] = "Connection error: Cannot reach the MAI API server. Please check that the server is running."
    yield "", None, None, "", history
```

**Change to:**
```python
except ConnectionError as e:
    history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
    if history and len(history) > 0:
        history[-1]["content"] = "Connection error: Cannot reach the MAI API server. Please check that the server is running."
    yield "", None, None, "", history
```

### 2. Fix TimeoutError Handler (line ~361)

**Current code:**
```python
except TimeoutError as e:
    history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
    if history and len(history) > 0:
        history[-1][1] = "Request timeout: The server took too long to respond. Please try again."
    yield "", None, None, "", history
```

**Change to:**
```python
except TimeoutError as e:
    history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
    if history and len(history) > 0:
        history[-1]["content"] = "Request timeout: The server took too long to respond. Please try again."
    yield "", None, None, "", history
```

### 3. Fix Generic Exception Handler (line ~379)

**Current code:**
```python
if history and len(history) > 0:
    history[-1][1] = user_friendly_msg
yield "", None, None, "", history
```

**Change to:**
```python
if history and len(history) > 0:
    history[-1]["content"] = user_friendly_msg
yield "", None, None, "", history
```

---

## Files to Modify

- `src/gui/app.py` - Lines 334-380: `safe_stream_response()` function

---

## Success Criteria

```bash
# Verify no tuple indexing remains in safe_stream_response
grep -A 50 "async def safe_stream_response" /Users/maxwell/Projects/MAI/src/gui/app.py | grep -c '\[-1\]\[1\]'
# Expected: 0 (no matches)

# Verify dict format is used
grep -A 50 "async def safe_stream_response" /Users/maxwell/Projects/MAI/src/gui/app.py | grep -c '\["content"\]'
# Expected: 3 (three error handlers)

# Check for syntax errors
python -c "from src.gui.app import safe_stream_response; print('Import OK')"
# Expected: Import OK

# Verify the entire file has consistent format
grep -n '\[-1\]\[1\]' /Users/maxwell/Projects/MAI/src/gui/app.py
# Expected: No output (no remaining tuple indexing)
```

**Checklist:**
- [ ] All `history[-1][1] = ...` replaced with `history[-1]["content"] = ...`
- [ ] ConnectionError handler updated
- [ ] TimeoutError handler updated
- [ ] Generic Exception handler updated
- [ ] No tuple indexing remains in the entire file

---

## Technical Notes

- **Function location**: `safe_stream_response()` at lines 334-380
- **Pattern**: Replace `history[-1][1]` with `history[-1]["content"]`
- **Three handlers to update**: ConnectionError, TimeoutError, Exception
- **Keep error messages**: Only change the indexing, not the error message text

---

## Important

- Do NOT change the error message text - only the indexing method
- Do NOT modify the yield format or return values
- The history parameter extraction logic should remain unchanged
- This function may be unused, but fix it for consistency

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (04-validation-testing.md) depends on this completing successfully
