# Task: Polish UI and Add Integration Tests

**Project**: MAI_feat/simple_gui (`/Users/maxwell/Projects/MAI`)
**Goal**: Add error handling, agent selector, improved styling, and integration tests
**Sequence**: 4 of 4
**Depends On**: 03-session-history.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `51cb5998-db56-4165-b66b-95cc3278dbd1`
- **Project ID**: `535f9c2a-d087-45e5-bd96-694010bf1ebf`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/51cb5998-db56-4165-b66b-95cc3278dbd1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/51cb5998-db56-4165-b66b-95cc3278dbd1" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/51cb5998-db56-4165-b66b-95cc3278dbd1" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous tasks built a functional Gradio chat interface:
1. (01) Basic Gradio structure with config and UI
2. (02) API integration with streaming responses
3. (03) Session management and conversation history

The GUI now works but needs polish:
- No way to select different agents (currently hardcoded to `chat_agent`)
- Basic error handling could be improved
- No visual feedback during loading states
- No integration tests to verify the GUI works with the API

This final task adds these finishing touches and ensures quality through testing.

---

## Requirements

### 1. Add Agent Selector Dropdown

Update `src/gui/app.py` to include an agent selector:

```python
# Add at the top of create_chat_interface():

# Fetch available agents at startup
async def get_agents_list() -> list[str]:
    try:
        return await mai_client.list_agents()
    except Exception:
        return [gui_settings.default_agent]

# In the UI section, add agent selector:
with gr.Row():
    agent_selector = gr.Dropdown(
        label="Agent",
        choices=[gui_settings.default_agent],  # Will be populated on load
        value=gui_settings.default_agent,
        interactive=True,
        scale=1,
    )
    # ... existing session controls ...

# Add a load event to populate agents on page load
demo.load(
    get_agents_list,
    outputs=[agent_selector],  # This sets the choices
)
```

Update `stream_response` to accept agent selection:

```python
async def stream_response(
    message: str,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, list], None]:
    # ... existing code but use agent_name parameter ...
    async for chunk in mai_client.stream_chat(
        message=message,
        agent_name=agent_name,  # Use selected agent
        session_id=session_id,
    ):
```

### 2. Improve Error Handling and Loading States

Add connection status checking and better error messages:

```python
# Add to api_client.py:
async def health_check(self) -> dict:
    """Check if the API is healthy.

    Returns:
        Health status dict or error info
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url.replace('/api/v1', '')}/health")
            return response.json()
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

Add status indicator to the UI:

```python
# In create_chat_interface():
with gr.Row():
    status_indicator = gr.Markdown("🟡 Checking connection...")

async def check_connection() -> str:
    health = await mai_client.health_check()
    if health.get("status") == "healthy":
        return "🟢 Connected to MAI API"
    else:
        error = health.get("error", "Unknown error")
        return f"🔴 Disconnected: {error}"

demo.load(check_connection, outputs=[status_indicator])
```

### 3. Add Custom CSS Styling

Add custom styling for a polished look:

```python
custom_css = """
.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
}
.chat-message {
    padding: 10px;
    border-radius: 8px;
    margin: 5px 0;
}
footer {
    display: none !important;
}
"""

with gr.Blocks(title=gui_settings.app_title, css=custom_css) as demo:
    # ... rest of UI
```

### 4. Create Integration Tests

Create `tests/gui/test_gui_integration.py`:

```python
"""Integration tests for the Gradio GUI."""
import asyncio
import pytest

from src.gui.api_client import MAIClient
from src.gui.session import generate_session_id, format_history_for_gradio


class TestSessionManagement:
    """Tests for session management utilities."""

    def test_generate_session_id_format(self):
        """Session ID should have expected format."""
        session_id = generate_session_id()
        assert session_id.startswith("gui_")
        parts = session_id.split("_")
        assert len(parts) == 3
        # gui_YYYYMMDD_HHMMSS_xxxxxxxx
        assert len(parts[1]) == 15  # YYYYMMDD_HHMMSS
        assert len(parts[2]) == 8   # short uuid

    def test_generate_session_id_unique(self):
        """Each session ID should be unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_format_history_empty(self):
        """Empty history should return empty list."""
        result = format_history_for_gradio([])
        assert result == []

    def test_format_history_filters_roles(self):
        """Should only include user and assistant roles."""
        api_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "system", "content": "You are helpful"},
            {"role": "tool", "content": "Tool output"},
        ]
        result = format_history_for_gradio(api_messages)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}


@pytest.mark.asyncio
class TestAPIClient:
    """Integration tests for the API client (requires running API)."""

    @pytest.fixture
    def client(self):
        return MAIClient()

    async def test_list_agents(self, client):
        """Should return list of available agents."""
        try:
            agents = await client.list_agents()
            assert isinstance(agents, list)
            assert len(agents) > 0
            assert "simple_agent" in agents or "chat_agent" in agents
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_health_check(self, client):
        """Health check should return status."""
        health = await client.health_check()
        assert "status" in health

    async def test_chat_simple_agent(self, client):
        """Should get response from simple agent."""
        try:
            response = await client.chat(
                message="Hello test",
                agent_name="simple_agent",
                session_id="test_integration_123",
            )
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_stream_chat(self, client):
        """Should stream response chunks."""
        try:
            chunks = []
            async for chunk in client.stream_chat(
                message="Hello",
                agent_name="simple_agent",
                session_id="test_stream_123",
            ):
                chunks.append(chunk)

            assert len(chunks) > 0
            full_response = "".join(chunks)
            assert len(full_response) > 0
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_history_operations(self, client):
        """Should handle history get/clear."""
        try:
            session_id = generate_session_id()

            # New session should have empty history
            history = await client.get_history(session_id)
            assert history == []

            # Send a message to create history
            await client.chat("Test message", "simple_agent", session_id)

            # Now history should exist
            history = await client.get_history(session_id)
            # May have messages now (depends on API behavior)

            # Clear should succeed
            result = await client.clear_history(session_id)
            assert result is True

        except Exception as e:
            pytest.skip(f"API not available: {e}")
```

Create `tests/gui/__init__.py`:

```python
"""GUI integration tests."""
```

### 5. Update Final App with All Improvements

Here's the complete updated `src/gui/app.py`:

```python
"""Gradio chat interface for MAI agents."""
from typing import AsyncGenerator

import gradio as gr

from src.gui.api_client import mai_client
from src.gui.config import gui_settings
from src.gui.session import generate_session_id, format_history_for_gradio


# Custom CSS for polished appearance
CUSTOM_CSS = """
.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
}
footer {
    display: none !important;
}
.status-connected {
    color: #22c55e;
}
.status-disconnected {
    color: #ef4444;
}
"""


async def get_agents_list() -> dict:
    """Fetch available agents for dropdown."""
    try:
        agents = await mai_client.list_agents()
        return gr.Dropdown(choices=agents, value=agents[0] if agents else gui_settings.default_agent)
    except Exception:
        return gr.Dropdown(choices=[gui_settings.default_agent], value=gui_settings.default_agent)


async def check_connection() -> str:
    """Check API connection status."""
    health = await mai_client.health_check()
    if health.get("status") == "healthy":
        services = health.get("services", {})
        service_status = ", ".join(f"{k}: {'✓' if v else '✗'}" for k, v in services.items())
        return f"🟢 Connected | {service_status}"
    else:
        error = health.get("error", "Unknown error")
        return f"🔴 Disconnected: {error}"


async def stream_response(
    message: str,
    history: list,
    session_id: str,
    agent_name: str,
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
            agent_name=agent_name,
            session_id=session_id,
        ):
            history[-1]["content"] += chunk
            yield "", history
    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "refused" in error_msg.lower():
            history[-1]["content"] = "❌ Cannot connect to MAI API. Is the server running?"
        else:
            history[-1]["content"] = f"❌ Error: {error_msg}"
        yield "", history


async def load_session_history(session_id: str) -> tuple[list, str]:
    """Load conversation history for a session."""
    if not session_id:
        return [], "⚠️ No session ID provided"
    try:
        api_messages = await mai_client.get_history(session_id)
        history = format_history_for_gradio(api_messages)
        if history:
            return history, f"✅ Loaded {len(history)} messages"
        return [], "ℹ️ No history found for this session"
    except Exception as e:
        return [], f"❌ Error loading history: {e}"


async def clear_session(session_id: str) -> tuple[str, list, str, str]:
    """Clear the current session and start fresh."""
    if session_id:
        try:
            await mai_client.clear_history(session_id)
        except Exception:
            pass
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`", "✅ Session cleared"


async def new_session() -> tuple[str, list, str, str]:
    """Start a new session without clearing old one."""
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`", "✅ New session started"


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""

    with gr.Blocks(title=gui_settings.app_title, css=CUSTOM_CSS, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# 🤖 {gui_settings.app_title}")
        gr.Markdown("Chat with MAI agents powered by Pydantic AI")

        # Status bar
        status_bar = gr.Markdown("🟡 Checking connection...")

        # Agent and session controls
        with gr.Row():
            agent_selector = gr.Dropdown(
                label="Agent",
                choices=[gui_settings.default_agent],
                value=gui_settings.default_agent,
                interactive=True,
                scale=1,
            )
            session_id = gr.Textbox(
                label="Session ID",
                value=generate_session_id,
                interactive=True,
                scale=2,
            )
            load_btn = gr.Button("📥 Load", scale=1)
            new_btn = gr.Button("🆕 New", scale=1)

        # Feedback message
        feedback = gr.Markdown("")

        # Chat interface
        chatbot = gr.Chatbot(
            label="Conversation",
            height=450,
            type="messages",
            show_copy_button=True,
        )

        # Message input
        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Type your message here... (Enter to send)",
                lines=2,
                scale=4,
            )
            submit_btn = gr.Button("Send 📤", variant="primary", scale=1)

        # Action buttons
        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

        # Session info footer
        session_info = gr.Markdown(f"Session: `{generate_session_id()}`")

        # --- Event Handlers ---

        # Load agents and check connection on page load
        demo.load(get_agents_list, outputs=[agent_selector])
        demo.load(check_connection, outputs=[status_bar])

        # Session management
        load_btn.click(
            load_session_history,
            inputs=[session_id],
            outputs=[chatbot, feedback],
        )
        new_btn.click(
            new_session,
            outputs=[session_id, chatbot, session_info, feedback],
        )
        clear_btn.click(
            clear_session,
            inputs=[session_id],
            outputs=[session_id, chatbot, session_info, feedback],
        )

        # Chat submission
        submit_btn.click(
            stream_response,
            inputs=[msg, chatbot, session_id, agent_selector],
            outputs=[msg, chatbot],
        )
        msg.submit(
            stream_response,
            inputs=[msg, chatbot, session_id, agent_selector],
            outputs=[msg, chatbot],
        )

        # Update session info display
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
        show_error=True,
    )


if __name__ == "__main__":
    main()
```

---

## Files to Create

- `tests/gui/__init__.py` - Test module init
- `tests/gui/test_gui_integration.py` - Integration tests

## Files to Modify

- `src/gui/api_client.py` - Add health_check method
- `src/gui/app.py` - Complete rewrite with all improvements

---

## Success Criteria

```bash
# Run unit tests (no API required)
cd /Users/maxwell/Projects/MAI && poetry run pytest tests/gui/test_gui_integration.py::TestSessionManagement -v
# Expected: All tests pass

# Run integration tests (requires API running)
# First: docker compose up -d && poetry run uvicorn src.main:app --reload
cd /Users/maxwell/Projects/MAI && poetry run pytest tests/gui/test_gui_integration.py::TestAPIClient -v
# Expected: All tests pass (or skip if API not running)

# Visual verification (with API running)
cd /Users/maxwell/Projects/MAI && poetry run python -m src.gui.app
# Visit http://localhost:7860 and verify:
# - Agent dropdown shows available agents
# - Connection status shows green
# - Chat works with streaming
# - Session management works
# - Clear appearance with custom styling
```

**Checklist:**
- [ ] Agent selector dropdown populated dynamically
- [ ] Connection status indicator (green/red)
- [ ] Custom CSS applied for cleaner look
- [ ] Error messages are user-friendly
- [ ] All unit tests pass
- [ ] Integration tests pass (when API running)
- [ ] Copy button on messages works
- [ ] Soft theme applied

---

## Technical Notes

- **Gradio themes**: Using `gr.themes.Soft()` for a modern look
- **Dynamic dropdown**: Use `demo.load()` to populate choices on page load
- **Health endpoint**: MAI API has `/health` at root level (not under /api/v1)
- **Test markers**: Use `@pytest.mark.asyncio` for async tests
- **Skip tests**: Use `pytest.skip()` when API not available for CI/CD compatibility

---

## Important

- Keep tests independent - each test should clean up after itself
- Don't break existing functionality while adding features
- Ensure the GUI still works if the API is temporarily unavailable
- Tests should pass in CI where API may not be running

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. Create completion document (this is the final task)

### Create Completion Document

```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI_feat/simple_gui - Implementation Complete",
    "content": "# MAI Simple GUI - Implementation Complete\n\nAll 4 implementation tasks completed:\n\n1. **Gradio Setup** - Installed Gradio, created basic chat interface structure\n2. **API Integration** - Connected GUI to MAI agent streaming endpoint\n3. **Session Management** - Added session IDs, history persistence, load/clear functions\n4. **Polish & Testing** - Added agent selector, styling, error handling, and tests\n\n## Quick Start\n\n```bash\n# Start the MAI API\ncd /Users/maxwell/Projects/MAI\ndocker compose up -d\npoetry run uvicorn src.main:app --reload\n\n# In another terminal, start the GUI\npoetry run python -m src.gui.app\n# Or: poetry run mai-gui\n\n# Visit http://localhost:7860\n```\n\n## Features\n\n- Streaming chat responses\n- Multiple agent support (dropdown selector)\n- Session management (create, load, clear)\n- Conversation history persistence\n- Connection status indicator\n- Modern UI with Gradio Soft theme\n\n## Files Created\n\n- `src/gui/__init__.py`\n- `src/gui/config.py`\n- `src/gui/app.py`\n- `src/gui/api_client.py`\n- `src/gui/session.py`\n- `tests/gui/__init__.py`\n- `tests/gui/test_gui_integration.py`\n\n## Running Tests\n\n```bash\n# Unit tests (no API needed)\npoetry run pytest tests/gui/ -v\n\n# Integration tests (API must be running)\npoetry run pytest tests/gui/test_gui_integration.py::TestAPIClient -v\n```",
    "project_id": "535f9c2a-d087-45e5-bd96-694010bf1ebf"
  }'
```
