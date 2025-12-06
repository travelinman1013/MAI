# 01 - Visual Theme & Polish

**Project**: MAI Frontend Enhancement
**Sequence**: 1 of 5
**Depends On**: None (first step)

---

## Archon Task Management

**Task ID**: `a47570cf-8b62-4112-b4a0-464a53768ca7`
**Project ID**: `118ddd94-6aef-48cf-9397-43816f499907`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/a47570cf-8b62-4112-b4a0-464a53768ca7" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/a47570cf-8b62-4112-b4a0-464a53768ca7" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The MAI project currently uses Gradio 6.0.2 for its chat interface. The current UI uses:
- `gr.themes.Soft()` theme
- Basic custom CSS (container width, hidden footer, status colors)
- Default Gradio styling for all components

This task modernizes the visual appearance to create a more polished, professional AI chat experience.

---

## Requirements

### 1. Create a Custom Gradio Theme

Create a new file `src/gui/theme.py` with a custom theme that:

```python
import gradio as gr

def create_mai_theme() -> gr.themes.Base:
    """Create a custom MAI theme with modern styling."""
    return gr.themes.Soft(
        # Primary colors - Use a sophisticated blue/purple palette
        primary_hue=gr.themes.colors.indigo,
        secondary_hue=gr.themes.colors.slate,
        neutral_hue=gr.themes.colors.gray,

        # Sizing
        spacing_size=gr.themes.sizes.spacing_md,
        radius_size=gr.themes.sizes.radius_md,
        text_size=gr.themes.sizes.text_md,

        # Fonts - Modern, clean fonts
        font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
    ).set(
        # Customize specific CSS variables
        body_background_fill="*neutral_50",
        block_background_fill="white",
        block_border_width="1px",
        block_shadow="0 1px 3px 0 rgb(0 0 0 / 0.1)",
        button_primary_background_fill="*primary_600",
        button_primary_background_fill_hover="*primary_700",
        input_background_fill="white",
        chatbot_code_background_fill="*neutral_100",
    )
```

### 2. Enhance Custom CSS

Update `CUSTOM_CSS` in `src/gui/app.py` with improved styling:

```python
CUSTOM_CSS = """
/* Container styling */
.gradio-container {
    max-width: 1000px !important;
    margin: auto !important;
    padding: 1rem !important;
}

/* Hide footer */
footer {
    display: none !important;
}

/* Status indicators */
.status-connected {
    color: #22c55e;
    font-weight: 500;
}
.status-disconnected {
    color: #ef4444;
    font-weight: 500;
}
.status-warning {
    color: #f59e0b;
    font-weight: 500;
}

/* Header styling */
.app-header {
    text-align: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e5e7eb;
}
.app-header h1 {
    color: #4f46e5;
    margin-bottom: 0.25rem;
}

/* Chatbot styling */
.chatbot-container {
    border-radius: 12px !important;
    border: 1px solid #e5e7eb !important;
}

/* Message bubbles */
.message-bubble-border {
    border-radius: 16px !important;
}

/* Input styling */
.input-container textarea {
    border-radius: 12px !important;
}

/* Button styling */
.primary-btn {
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* Status bar styling */
.status-bar {
    background: linear-gradient(to right, #f8fafc, #f1f5f9);
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.875rem;
}

/* Session info styling */
.session-info {
    font-size: 0.75rem;
    color: #6b7280;
    text-align: center;
    margin-top: 0.5rem;
}

/* Warning banner */
.warning-banner {
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 1rem;
}
"""
```

### 3. Add Avatar Images

Create avatar images for user and assistant, or use emoji placeholders:

In `src/gui/app.py`, update the Chatbot component:

```python
chatbot = gr.Chatbot(
    label="Conversation",
    height=500,  # Slightly taller
    type="messages",
    avatar_images=(
        "https://api.dicebear.com/7.x/avataaars/svg?seed=user",  # User avatar
        "https://api.dicebear.com/7.x/bottts/svg?seed=mai",      # Assistant avatar
    ),
    show_copy_button=True,
    show_copy_all_button=True,
    bubble_full_width=False,  # More conversational look
    render_markdown=True,
    elem_classes=["chatbot-container"],
)
```

### 4. Improve Layout Structure

Update the interface layout in `create_chat_interface()`:

```python
def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""
    from src.gui.theme import create_mai_theme

    initial_session_id = generate_session_id()

    with gr.Blocks(
        title=gui_settings.app_title,
        theme=create_mai_theme(),
        css=CUSTOM_CSS,
    ) as demo:
        # Header with branding
        with gr.Column(elem_classes=["app-header"]):
            gr.Markdown(f"# {gui_settings.app_title}")
            gr.Markdown("*Your private AI assistant powered by local LLMs*")

        # Status bar with better formatting
        status_bar = gr.Markdown(
            "Checking connection...",
            elem_classes=["status-bar"],
        )

        # LLM warning banner
        llm_warning = gr.Markdown("", visible=True, elem_classes=["warning-banner"])

        # Controls row with better grouping
        with gr.Row():
            with gr.Column(scale=2):
                agent_selector = gr.Dropdown(
                    label="Agent",
                    choices=[gui_settings.default_agent],
                    value=gui_settings.default_agent,
                    interactive=True,
                    container=True,
                )
            with gr.Column(scale=3):
                session_id = gr.Textbox(
                    label="Session ID",
                    value=initial_session_id,
                    interactive=True,
                    container=True,
                )
            with gr.Column(scale=1):
                with gr.Row():
                    load_btn = gr.Button("Load", size="sm")
                    new_btn = gr.Button("New", size="sm", variant="secondary")

        # Feedback area
        feedback = gr.Markdown("")

        # ... rest of the interface
```

### 5. Update main() Function

Ensure the theme is applied correctly:

```python
def main() -> None:
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=gui_settings.server_port,
        share=False,
        show_error=True,
    )
```

Note: Move CSS and theme into `gr.Blocks()` constructor instead of `launch()`.

---

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| CREATE | `src/gui/theme.py` |
| MODIFY | `src/gui/app.py` |
| MODIFY | `src/gui/__init__.py` (export theme if needed) |

---

## Success Criteria

```bash
# 1. Start the services
docker compose up -d

# 2. Check GUI is accessible
curl -s http://localhost:7860 | head -20
# Expected: HTML content with Gradio interface

# 3. Visual verification (manual)
# Open http://localhost:7860 in browser and verify:
# - Custom color scheme (indigo/slate)
# - Inter font for text
# - JetBrains Mono for code blocks
# - Avatar images appear in chat
# - Rounded corners on chatbot and inputs
# - Status bar has gradient background
# - Buttons have consistent styling

# 4. No Python errors in logs
docker compose logs mai-gui --tail=20 2>&1 | grep -i error
# Expected: No error output
```

---

## Technical Notes

- Gradio 6.0.2 supports `gr.themes.Soft()` as base theme with `.set()` for CSS variable overrides
- Google Fonts are loaded automatically by Gradio when using `gr.themes.GoogleFont()`
- Avatar images can be URLs or local file paths
- The `type="messages"` parameter uses the OpenAI-style message format (role/content dicts)
- CSS classes can be applied via `elem_classes` parameter on components

**Reference**: Search Archon for "Gradio theming" for detailed documentation.

---

## On Completion

1. Mark Archon task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/a47570cf-8b62-4112-b4a0-464a53768ca7" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Proceed to: `02-model-switching.md`
