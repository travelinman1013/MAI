# Task: Create Gradio Chat Interface Structure

**Project**: MAI_feat/simple_gui (`/Users/maxwell/Projects/MAI`)
**Goal**: Install Gradio and create the basic chat interface file structure
**Sequence**: 1 of 4
**Depends On**: None (first step)

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `bfd18468-a918-4fa2-aeed-2fd74fa2f877`
- **Project ID**: `535f9c2a-d087-45e5-bd96-694010bf1ebf`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/bfd18468-a918-4fa2-aeed-2fd74fa2f877" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as blocked if stuck
curl -X PUT "http://localhost:8181/api/tasks/bfd18468-a918-4fa2-aeed-2fd74fa2f877" \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked", "description": "Blocked: [reason]"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/bfd18468-a918-4fa2-aeed-2fd74fa2f877" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI Framework is a Pydantic AI-based agent system with a FastAPI backend. It currently has:
- Agent execution endpoints at `/api/v1/agents/run/{agent_name}` and `/api/v1/agents/stream/{agent_name}`
- Two built-in agents: `chat_agent` (LLM-powered) and `simple_agent` (echo/test)
- Session-based conversation memory via Redis
- Docker Compose setup with Redis and the main API service

However, there is **no frontend UI** - the API is designed to be consumed by external clients. This task creates a simple Gradio-based chat interface to demonstrate the agent service capabilities.

Gradio is mentioned in the Pydantic AI documentation as a suitable choice for building agent UIs, particularly in their weather agent example. It provides built-in chat components with streaming support.

---

## Requirements

### 1. Add Gradio Dependency

Add `gradio` to the project's dependencies in `pyproject.toml`:

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
gradio = "^5.0"
```

Then run `poetry lock` and `poetry install` to update dependencies.

### 2. Create GUI Module Structure

Create a new `gui` module under `src/`:

```
src/
├── gui/
│   ├── __init__.py
│   ├── app.py          # Main Gradio application
│   └── config.py       # GUI configuration (API URL, defaults)
```

### 3. Create GUI Configuration

Create `src/gui/config.py` with configuration for the GUI:

```python
"""Configuration for the Gradio GUI."""
from pydantic_settings import BaseSettings


class GUISettings(BaseSettings):
    """Settings for the Gradio chat interface."""

    api_base_url: str = "http://localhost:8000/api/v1"
    default_agent: str = "chat_agent"
    app_title: str = "MAI Chat Interface"
    server_port: int = 7860

    class Config:
        env_prefix = "GUI_"


gui_settings = GUISettings()
```

### 4. Create Basic Gradio App

Create `src/gui/app.py` with a basic chat interface structure:

```python
"""Gradio chat interface for MAI agents."""
import gradio as gr

from src.gui.config import gui_settings


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""

    with gr.Blocks(title=gui_settings.app_title) as demo:
        gr.Markdown(f"# {gui_settings.app_title}")
        gr.Markdown("Chat with MAI agents powered by Pydantic AI")

        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            type="messages",  # Use OpenAI-style message format
        )

        msg = gr.Textbox(
            label="Message",
            placeholder="Type your message here...",
            lines=2,
        )

        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear")

        # Placeholder function - will be implemented in next step
        def respond(message: str, history: list) -> tuple[str, list]:
            """Placeholder response function."""
            # Add user message to history
            history = history or []
            history.append({"role": "user", "content": message})
            # Add placeholder assistant response
            history.append({"role": "assistant", "content": f"[Placeholder] You said: {message}"})
            return "", history

        # Wire up the interface
        submit_btn.click(
            respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        )
        msg.submit(
            respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        )
        clear_btn.click(lambda: (None, []), outputs=[msg, chatbot])

    return demo


def main():
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.launch(
        server_port=gui_settings.server_port,
        share=False,
    )


if __name__ == "__main__":
    main()
```

### 5. Create Module Init

Create `src/gui/__init__.py`:

```python
"""Gradio GUI module for MAI chat interface."""
from src.gui.app import create_chat_interface, main

__all__ = ["create_chat_interface", "main"]
```

### 6. Add GUI Entry Point to pyproject.toml

Add a script entry point so the GUI can be launched easily:

```toml
[tool.poetry.scripts]
mai-cli = "src.cli:main"
mai-gui = "src.gui.app:main"
```

---

## Files to Create

- `src/gui/__init__.py` - Module init with exports
- `src/gui/config.py` - GUI configuration using pydantic-settings
- `src/gui/app.py` - Main Gradio application with chat interface

## Files to Modify

- `pyproject.toml` - Add gradio dependency and mai-gui script entry point

---

## Success Criteria

```bash
# Verify Gradio is installed
cd /Users/maxwell/Projects/MAI && poetry run python -c "import gradio; print(f'Gradio version: {gradio.__version__}')"
# Expected: Gradio version: 5.x.x (some 5.x version)

# Verify GUI module imports correctly
cd /Users/maxwell/Projects/MAI && poetry run python -c "from src.gui import create_chat_interface; print('GUI module imports OK')"
# Expected: GUI module imports OK

# Launch the GUI (manual test - run then visit http://localhost:7860)
cd /Users/maxwell/Projects/MAI && poetry run python -m src.gui.app
# Expected: Gradio launches on port 7860, shows chat interface with placeholder responses
```

**Checklist:**
- [ ] Gradio ^5.0 added to pyproject.toml dependencies
- [ ] `src/gui/` module created with __init__.py, config.py, app.py
- [ ] GUI launches without errors on port 7860
- [ ] Chat interface displays with message input and send button
- [ ] Placeholder responses work (echoes user input)

---

## Technical Notes

- **Existing patterns**: Follow the structure in `src/core/utils/config.py` for settings
- **Gradio ChatInterface**: Using `gr.Blocks` with `gr.Chatbot` for more control over the UI
- **Message format**: Using `type="messages"` for OpenAI-style message format `[{"role": "user", "content": "..."}, ...]`
- **Pydantic AI reference**: The weather agent example at https://ai.pydantic.dev/examples/weather-agent shows Gradio integration

---

## Important

- Do NOT connect to the actual API yet - that's the next step
- Keep the interface simple - we'll add more features later
- Make sure the GUI can run independently of the main API service

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (02-api-integration.md) depends on this completing successfully
