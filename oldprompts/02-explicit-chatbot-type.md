# Task: Add Explicit type="messages" to Chatbot Component

**Project**: UI Robustness Overhaul (`/Users/maxwell/Projects/MAI`)
**Goal**: Add type="messages" parameter to gr.Chatbot() for explicit format declaration
**Sequence**: 2 of 4
**Depends On**: 01-fix-stream-response-format.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `219470d8-bba4-4c0d-b159-5859f8eac4bc`
- **Project ID**: `a4058f0e-7162-4ef6-8464-1dfe16809b09`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/219470d8-bba4-4c0d-b159-5859f8eac4bc" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/219470d8-bba4-4c0d-b159-5859f8eac4bc" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/219470d8-bba4-4c0d-b159-5859f8eac4bc" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

In the previous step, we fixed `stream_response_with_attachments()` to use dict format (`{"role": "user", "content": "..."}`) instead of tuple format (`[user_msg, assistant_msg]`).

Now we need to explicitly declare the Chatbot component's expected format. While Gradio 6.0+ defaults to the messages format, explicitly declaring `type="messages"` ensures:
1. Clear documentation of expected format in code
2. Compatibility if defaults change
3. Explicit error messages if format mismatches occur

This is a small but important change for code clarity and future-proofing.

---

## Requirements

### 1. Add type="messages" to gr.Chatbot()

Locate the Chatbot component definition (around line 587) and add the type parameter.

**Current code:**
```python
chatbot = gr.Chatbot(
    label="Conversation",
    height=500,
    avatar_images=(
        "https://api.dicebear.com/7.x/avataaars/svg?seed=user",
        "https://api.dicebear.com/7.x/bottts/svg?seed=mai",
    ),
    elem_classes=["chatbot-container"],
)
```

**Change to:**
```python
chatbot = gr.Chatbot(
    label="Conversation",
    height=500,
    type="messages",  # Explicit OpenAI-style format for Gradio 6.0+
    avatar_images=(
        "https://api.dicebear.com/7.x/avataaars/svg?seed=user",
        "https://api.dicebear.com/7.x/bottts/svg?seed=mai",
    ),
    elem_classes=["chatbot-container"],
)
```

---

## Files to Modify

- `src/gui/app.py` - Line ~587: `gr.Chatbot()` component definition

---

## Success Criteria

```bash
# Verify the type parameter is present
grep -A 5 "gr.Chatbot" /Users/maxwell/Projects/MAI/src/gui/app.py | grep -q 'type="messages"' && echo "type=messages found" || echo "MISSING"
# Expected: type=messages found

# Check for syntax errors
python -c "from src.gui import app; print('Import OK')"
# Expected: Import OK

# Verify exact line
grep -n 'type="messages"' /Users/maxwell/Projects/MAI/src/gui/app.py
# Expected: Should show line number with type="messages"
```

**Checklist:**
- [ ] `type="messages"` parameter added to gr.Chatbot()
- [ ] Comment added explaining the parameter
- [ ] No syntax errors in the file
- [ ] Parameter placed logically (after height, before avatar_images)

---

## Technical Notes

- **Gradio Chatbot type parameter**: Accepts "messages" (OpenAI-style dicts) or "tuples" (legacy format)
- **Reference**: https://www.gradio.app/docs/gradio/chatbot
- **Messages format**: `[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]`
- **Tuples format** (legacy): `[["Hi", "Hello!"]]`

---

## Important

- This is a ONE LINE change - do not modify anything else
- The parameter should be `type="messages"` exactly (string, not a constant)
- Place the parameter in a logical position within the Chatbot constructor

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (03-fix-error-handling.md) depends on this completing successfully
