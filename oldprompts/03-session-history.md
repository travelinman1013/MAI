# Task: Add Session and Conversation History Management

**Project**: MAI_feat/simple_gui (`/Users/maxwell/Projects/MAI`)
**Goal**: Add session ID management, conversation history persistence, and history loading
**Sequence**: 3 of 4
**Depends On**: 02-api-integration.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `0b165c17-e21d-4da8-bb47-33f6599305d5`
- **Project ID**: `535f9c2a-d087-45e5-bd96-694010bf1ebf`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/0b165c17-e21d-4da8-bb47-33f6599305d5" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/0b165c17-e21d-4da8-bb47-33f6599305d5" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/0b165c17-e21d-4da8-bb47-33f6599305d5" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous tasks established:
1. (01) A Gradio chat interface structure with config and UI components
2. (02) API integration with streaming support via `MAIClient`

Currently, the chat works but:
- Each page refresh loses conversation history
- No session ID is passed to the API, so the backend can't maintain conversation context
- Users can't see or manage their conversation sessions

The MAI API supports session-based conversations:
- Pass `session_id` in requests to maintain conversation context on the backend
- `GET /api/v1/agents/history/{session_id}` retrieves conversation history
- `DELETE /api/v1/agents/history/{session_id}` clears a session

This task adds proper session management and history persistence.

---

## Requirements

### 1. Add Session Management Methods to API Client

Update `src/gui/api_client.py` to add history-related methods:

```python
# Add these methods to the MAIClient class:

async def get_history(self, session_id: str) -> list[dict]:
    """Get conversation history for a session.

    Args:
        session_id: The session ID

    Returns:
        List of messages [{"role": str, "content": str, "timestamp": str}, ...]
    """
    url = f"{self.base_url}/agents/history/{session_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return data.get("messages", [])

async def clear_history(self, session_id: str) -> bool:
    """Clear conversation history for a session.

    Args:
        session_id: The session ID

    Returns:
        True if successful
    """
    url = f"{self.base_url}/agents/history/{session_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(url)
        return response.status_code == 200
```

### 2. Create Session Manager

Create `src/gui/session.py` to manage session state:

```python
"""Session management for the Gradio GUI."""
import uuid
from datetime import datetime


def generate_session_id() -> str:
    """Generate a new unique session ID.

    Returns:
        A unique session ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"gui_{timestamp}_{short_uuid}"


def format_history_for_gradio(api_messages: list[dict]) -> list[dict]:
    """Convert API message format to Gradio chatbot format.

    Args:
        api_messages: Messages from API [{"role": str, "content": str, ...}, ...]

    Returns:
        Messages in Gradio format [{"role": str, "content": str}, ...]
    """
    gradio_messages = []
    for msg in api_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Gradio expects "user" or "assistant" roles
        if role in ("user", "assistant"):
            gradio_messages.append({"role": role, "content": content})
    return gradio_messages
```

### 3. Update Gradio App with Session UI

Update `src/gui/app.py` to include session management in the UI:

```python
"""Gradio chat interface for MAI agents."""
import asyncio
from typing import AsyncGenerator

import gradio as gr

from src.gui.api_client import mai_client
from src.gui.config import gui_settings
from src.gui.session import generate_session_id, format_history_for_gradio


async def stream_response(
    message: str,
    history: list,
    session_id: str,
) -> AsyncGenerator[tuple[str, list], None]:
    """Stream a response from the agent."""
    if not message.strip():
        yield "", history
        return

    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})

    try:
        async for chunk in mai_client.stream_chat(
            message=message,
            agent_name=gui_settings.default_agent,
            session_id=session_id,
        ):
            history[-1]["content"] += chunk
            yield "", history
    except Exception as e:
        history[-1]["content"] = f"Error: {str(e)}"
        yield "", history


async def load_session_history(session_id: str) -> list:
    """Load conversation history for a session."""
    if not session_id:
        return []
    try:
        api_messages = await mai_client.get_history(session_id)
        return format_history_for_gradio(api_messages)
    except Exception:
        return []


async def clear_session(session_id: str) -> tuple[str, list, str]:
    """Clear the current session and start fresh."""
    if session_id:
        await mai_client.clear_history(session_id)
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`"


async def new_session() -> tuple[str, list, str]:
    """Start a new session without clearing old one."""
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`"


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""

    with gr.Blocks(title=gui_settings.app_title) as demo:
        gr.Markdown(f"# {gui_settings.app_title}")
        gr.Markdown("Chat with MAI agents powered by Pydantic AI")

        # Session management row
        with gr.Row():
            session_id = gr.Textbox(
                label="Session ID",
                value=generate_session_id,
                interactive=True,
                scale=3,
            )
            load_btn = gr.Button("Load History", scale=1)
            new_btn = gr.Button("New Session", scale=1)

        # Session info display
        session_info = gr.Markdown(f"Session: `{generate_session_id()}`")

        chatbot = gr.Chatbot(
            label="Conversation",
            height=450,
            type="messages",
        )

        msg = gr.Textbox(
            label="Message",
            placeholder="Type your message here...",
            lines=2,
        )

        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear Chat", variant="secondary")

        # Wire up session management
        load_btn.click(
            load_session_history,
            inputs=[session_id],
            outputs=[chatbot],
        )

        new_btn.click(
            new_session,
            outputs=[session_id, chatbot, session_info],
        )

        clear_btn.click(
            clear_session,
            inputs=[session_id],
            outputs=[session_id, chatbot, session_info],
        )

        # Wire up chat with session
        submit_btn.click(
            stream_response,
            inputs=[msg, chatbot, session_id],
            outputs=[msg, chatbot],
        )
        msg.submit(
            stream_response,
            inputs=[msg, chatbot, session_id],
            outputs=[msg, chatbot],
        )

        # Update session info when session_id changes
        session_id.change(
            lambda sid: f"Session: `{sid}`",
            inputs=[session_id],
            outputs=[session_info],
        )

    return demo


def main():
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.queue()
    demo.launch(
        server_port=gui_settings.server_port,
        share=False,
    )


if __name__ == "__main__":
    main()
```

### 4. Update Module Exports

Update `src/gui/__init__.py`:

```python
"""Gradio GUI module for MAI chat interface."""
from src.gui.api_client import MAIClient, mai_client
from src.gui.app import create_chat_interface, main
from src.gui.session import generate_session_id, format_history_for_gradio

__all__ = [
    "create_chat_interface",
    "main",
    "MAIClient",
    "mai_client",
    "generate_session_id",
    "format_history_for_gradio",
]
```

---

## Files to Create

- `src/gui/session.py` - Session ID generation and history formatting utilities

## Files to Modify

- `src/gui/api_client.py` - Add get_history and clear_history methods
- `src/gui/app.py` - Add session management UI and functionality
- `src/gui/__init__.py` - Export session utilities

---

## Success Criteria

```bash
# Verify session module imports
cd /Users/maxwell/Projects/MAI && poetry run python -c "
from src.gui.session import generate_session_id
sid = generate_session_id()
print(f'Generated session ID: {sid}')
assert sid.startswith('gui_')
print('Session module OK')
"
# Expected: Generated session ID: gui_YYYYMMDD_HHMMSS_xxxxxxxx

# Test history methods (requires API running)
cd /Users/maxwell/Projects/MAI && poetry run python -c "
import asyncio
from src.gui.api_client import mai_client

async def test():
    # This will return empty list for non-existent session
    history = await mai_client.get_history('test_session_123')
    print(f'History for new session: {history}')
    return True

result = asyncio.run(test())
print('History methods OK' if result else 'FAILED')
"
# Expected: History for new session: [] (or actual history if session exists)

# Integration test (with API running)
# 1. Start GUI: poetry run python -m src.gui.app
# 2. Send a message, note the session ID
# 3. Refresh the page
# 4. Enter the same session ID
# 5. Click "Load History"
# Expected: Previous conversation loads into chat
```

**Checklist:**
- [ ] Session ID auto-generated on app load
- [ ] Session ID visible and editable in UI
- [ ] "Load History" button loads previous conversation
- [ ] "New Session" creates fresh session ID
- [ ] "Clear Chat" clears both UI and backend history
- [ ] Session ID passed to all API calls
- [ ] Conversation persists across page refreshes when same session ID used

---

## Technical Notes

- **Session ID format**: `gui_YYYYMMDD_HHMMSS_xxxxxxxx` for easy identification
- **API history endpoint**: `src/api/routes/agents.py:130` - returns messages with timestamps
- **Redis storage**: Sessions stored in Redis via `ConversationMemory` class
- **Message format mapping**: API returns `{role, content, timestamp}`, Gradio needs `{role, content}`

---

## Important

- Session IDs should be user-visible so they can be shared or resumed later
- Don't store sensitive data in session IDs
- Handle 404 gracefully when loading non-existent sessions
- The backend may have conversation size limits - don't assume unlimited history

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (04-polish-testing.md) depends on this completing successfully
