# Task: Connect Gradio to MAI Agent Streaming Endpoint

**Project**: MAI_feat/simple_gui (`/Users/maxwell/Projects/MAI`)
**Goal**: Implement the chat function that calls the MAI agent API with streaming support
**Sequence**: 2 of 4
**Depends On**: 01-gradio-setup.md completed

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `68a363ba-2c24-45e1-a9a5-903c2029719c`
- **Project ID**: `535f9c2a-d087-45e5-bd96-694010bf1ebf`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/68a363ba-2c24-45e1-a9a5-903c2029719c" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/68a363ba-2c24-45e1-a9a5-903c2029719c" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/68a363ba-2c24-45e5-bd96-694010bf1ebf" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous task (01-gradio-setup.md) created a basic Gradio chat interface with:
- A `src/gui/` module with config.py and app.py
- A chat interface with placeholder responses that echo user input
- Gradio running on port 7860

Now we need to replace the placeholder with actual API calls to the MAI agent service. The MAI API provides:

**Streaming endpoint** (preferred for chat UX):
- `POST /api/v1/agents/stream/{agent_name}`
- Request body: `{"user_input": str, "session_id": str | null, "user_id": str | null}`
- Response: Server-Sent Events (SSE) with chunks: `{"content": str, "done": bool}`

**Non-streaming endpoint** (fallback):
- `POST /api/v1/agents/run/{agent_name}`
- Same request body
- Response: `{"success": bool, "result": {"role": str, "content": str}, ...}`

The streaming endpoint provides a better user experience as responses appear progressively.

---

## Requirements

### 1. Create API Client Module

Create `src/gui/api_client.py` to handle communication with the MAI API:

```python
"""API client for communicating with MAI agent service."""
import json
from typing import AsyncGenerator

import httpx

from src.gui.config import gui_settings


class MAIClient:
    """Client for the MAI agent API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or gui_settings.api_base_url

    async def stream_chat(
        self,
        message: str,
        agent_name: str = "chat_agent",
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from the agent.

        Args:
            message: The user's message
            agent_name: Name of the agent to use
            session_id: Optional session ID for conversation continuity

        Yields:
            Content chunks as they arrive
        """
        url = f"{self.base_url}/agents/stream/{agent_name}"
        payload = {
            "user_input": message,
            "session_id": session_id,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip():
                            try:
                                chunk = json.loads(data)
                                if "content" in chunk and chunk["content"]:
                                    yield chunk["content"]
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

    async def chat(
        self,
        message: str,
        agent_name: str = "chat_agent",
        session_id: str | None = None,
    ) -> str:
        """Send a message and get a complete response (non-streaming).

        Args:
            message: The user's message
            agent_name: Name of the agent to use
            session_id: Optional session ID for conversation continuity

        Returns:
            The agent's response content
        """
        url = f"{self.base_url}/agents/run/{agent_name}"
        payload = {
            "user_input": message,
            "session_id": session_id,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and data.get("result"):
                return data["result"].get("content", "")
            return "Error: No response from agent"

    async def list_agents(self) -> list[str]:
        """Get list of available agents.

        Returns:
            List of agent names
        """
        url = f"{self.base_url}/agents/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [agent["name"] for agent in data.get("agents", [])]


# Singleton instance
mai_client = MAIClient()
```

### 2. Update Gradio App with Streaming Support

Update `src/gui/app.py` to use the API client with streaming:

```python
"""Gradio chat interface for MAI agents."""
import asyncio

import gradio as gr

from src.gui.api_client import mai_client
from src.gui.config import gui_settings


async def stream_response(
    message: str,
    history: list,
    session_id: str | None = None,
) -> AsyncGenerator[tuple[str, list], None]:
    """Stream a response from the agent.

    Args:
        message: User's message
        history: Chat history
        session_id: Optional session ID

    Yields:
        Tuple of (empty string for input, updated history)
    """
    if not message.strip():
        yield "", history
        return

    # Add user message to history
    history = history or []
    history.append({"role": "user", "content": message})

    # Add empty assistant message that we'll update
    history.append({"role": "assistant", "content": ""})

    try:
        # Stream the response
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


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""

    with gr.Blocks(title=gui_settings.app_title) as demo:
        gr.Markdown(f"# {gui_settings.app_title}")
        gr.Markdown("Chat with MAI agents powered by Pydantic AI")

        # Hidden state for session ID (will be used in next task)
        session_state = gr.State(value=None)

        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            type="messages",
        )

        msg = gr.Textbox(
            label="Message",
            placeholder="Type your message here...",
            lines=2,
        )

        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear")

        # Status indicator
        status = gr.Markdown("Ready")

        # Wire up the interface with streaming
        submit_btn.click(
            stream_response,
            inputs=[msg, chatbot, session_state],
            outputs=[msg, chatbot],
        )
        msg.submit(
            stream_response,
            inputs=[msg, chatbot, session_state],
            outputs=[msg, chatbot],
        )
        clear_btn.click(lambda: ("", []), outputs=[msg, chatbot])

    return demo


def main():
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.queue()  # Enable queuing for streaming
    demo.launch(
        server_port=gui_settings.server_port,
        share=False,
    )


if __name__ == "__main__":
    main()
```

### 3. Add httpx Dependency

Ensure `httpx` is in the dependencies (it may already be there). Check `pyproject.toml` and add if missing:

```toml
[tool.poetry.dependencies]
httpx = "^0.27"
```

### 4. Update Module Exports

Update `src/gui/__init__.py` to export the client:

```python
"""Gradio GUI module for MAI chat interface."""
from src.gui.api_client import MAIClient, mai_client
from src.gui.app import create_chat_interface, main

__all__ = ["create_chat_interface", "main", "MAIClient", "mai_client"]
```

---

## Files to Create

- `src/gui/api_client.py` - API client with streaming support

## Files to Modify

- `src/gui/app.py` - Replace placeholder with streaming API calls
- `src/gui/__init__.py` - Add api_client exports
- `pyproject.toml` - Add httpx if not present

---

## Success Criteria

```bash
# Verify API client imports
cd /Users/maxwell/Projects/MAI && poetry run python -c "from src.gui.api_client import mai_client; print('API client OK')"
# Expected: API client OK

# Test listing agents (requires API to be running)
cd /Users/maxwell/Projects/MAI && poetry run python -c "
import asyncio
from src.gui.api_client import mai_client
agents = asyncio.run(mai_client.list_agents())
print(f'Available agents: {agents}')
"
# Expected: Available agents: ['simple_agent', 'chat_agent'] (or similar)

# Integration test: Start MAI API first, then GUI
# Terminal 1: cd /Users/maxwell/Projects/MAI && docker compose up -d && poetry run uvicorn src.main:app --reload
# Terminal 2: cd /Users/maxwell/Projects/MAI && poetry run python -m src.gui.app
# Then visit http://localhost:7860 and send a message
# Expected: Response streams in progressively from the agent
```

**Checklist:**
- [ ] `src/gui/api_client.py` created with MAIClient class
- [ ] Streaming chat works - responses appear progressively
- [ ] Non-streaming fallback method available
- [ ] Error handling shows errors in chat interface
- [ ] GUI queue enabled for streaming support

---

## Technical Notes

- **SSE Format**: The MAI API returns Server-Sent Events with `data: {...}` format
- **Async Generator**: Gradio supports async generators for streaming via `demo.queue()`
- **Timeout**: Using 60s timeout for LLM responses which can be slow
- **Existing API schema**: See `src/api/schemas/agents.py` for request/response models
- **Agent routes**: Implementation at `src/api/routes/agents.py:95` for streaming endpoint

---

## Important

- The MAI API must be running for the GUI to work - ensure `docker compose up` or `uvicorn` is running
- Keep session_id handling minimal for now - full implementation in next task
- Don't modify the API - only add client-side code

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (03-session-history.md) depends on this completing successfully
