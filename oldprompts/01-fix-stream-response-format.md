# Task: Fix stream_response_with_attachments() Message Format

**Project**: UI Robustness Overhaul (`/Users/maxwell/Projects/MAI`)
**Goal**: Convert tuple-based history manipulation to dict-based format in stream_response_with_attachments()
**Sequence**: 1 of 4
**Depends On**: None (first step)

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `558ab83f-93e0-4292-bc3b-60f5769233ce`
- **Project ID**: `a4058f0e-7162-4ef6-8464-1dfe16809b09`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/558ab83f-93e0-4292-bc3b-60f5769233ce" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/558ab83f-93e0-4292-bc3b-60f5769233ce" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/558ab83f-93e0-4292-bc3b-60f5769233ce" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The Gradio chat UI displays multiple error boxes ("Data incompatible with messages format") due to a message format mismatch. Gradio 6.0+ changed the default Chatbot format to OpenAI-style dictionaries (`type="messages"`), but `stream_response_with_attachments()` uses the old tuple format.

**The Problem:**
1. User sends a message
2. `stream_response_with_attachments()` appends tuple format: `history.append([display_message, None])`
3. Chatbot expects dict format: `{"role": "user", "content": "..."}`
4. Error thrown: "Data incompatible with messages format"

The "Load" button temporarily fixes it because `load_session_history()` uses `format_history_for_gradio()` which returns the correct dict format.

This is the **critical fix** - the primary source of the format mismatch.

---

## Requirements

### 1. Replace Tuple-Based History Append with Dict Format

Change how user messages are added to history.

**Current code (line ~440):**
```python
history.append([display_message, None])
```

**Change to:**
```python
history.append({"role": "user", "content": display_message})
```

### 2. Add Assistant Message as Separate Dict Entry

Instead of modifying a tuple index, append a new dict for the assistant.

**Current code (line ~443):**
```python
history[-1][1] = "..."
```

**Change to:**
```python
history.append({"role": "assistant", "content": "..."})
```

### 3. Update Streaming to Modify Dict Content

During streaming, update the assistant message's content field.

**Current code (line ~458):**
```python
history[-1][1] = assistant_response
```

**Change to:**
```python
history[-1]["content"] = assistant_response
```

### 4. Update All Error Handlers in the Function

All error handlers within `stream_response_with_attachments()` (lines ~461-482) use tuple indexing. Update them all.

**Current pattern:**
```python
history[-1][1] = "Connection error: ..."
```

**Change to:**
```python
history[-1]["content"] = "Connection error: ..."
```

Apply this to:
- `ConnectionError` handler (line ~462)
- `TimeoutError` handler (line ~465)
- Generic `Exception` handler (line ~481)

---

## Files to Modify

- `src/gui/app.py` - Lines 383-483: `stream_response_with_attachments()` function

---

## Success Criteria

```bash
# Start the Gradio UI
cd /Users/maxwell/Projects/MAI && python -m src.gui.app &

# Wait for startup
sleep 5

# Check for Python syntax errors
python -c "from src.gui.app import stream_response_with_attachments; print('Import OK')"
# Expected: Import OK

# Verify dict format in code
grep -n "role.*user.*content" src/gui/app.py
# Expected: Should show the new dict format lines

grep -n "role.*assistant.*content" src/gui/app.py
# Expected: Should show assistant dict append

# Kill the test server
pkill -f "src.gui.app"
```

**Checklist:**
- [ ] `history.append([...])` replaced with `history.append({"role": "user", "content": ...})`
- [ ] Assistant message appended as separate dict, not tuple index modification
- [ ] All streaming updates use `history[-1]["content"]` not `history[-1][1]`
- [ ] All error handlers updated to dict format
- [ ] No Python syntax errors

---

## Technical Notes

- **Reference format**: Look at `format_history_for_gradio()` in the same file - it already uses the correct dict format
- **Gradio 6.0+ messages format**: `{"role": "user"|"assistant", "content": "..."}`
- **Streaming pattern**: Append user dict, then append assistant dict with placeholder, then update `history[-1]["content"]` as chunks arrive
- **Yield signature**: The function yields `(msg_input, image_input, doc_input, doc_content, history)` - ensure history is always the list of dicts

---

## Important

- Do NOT change the function signature or yield format (5-tuple)
- Do NOT modify other functions in this step
- The assistant message MUST be a separate dict entry, not modifying a tuple's second element
- Keep all existing error message text - only change the format

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (02-explicit-chatbot-type.md) depends on this completing successfully
