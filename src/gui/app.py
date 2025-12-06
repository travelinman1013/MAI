"""Gradio chat interface for MAI agents."""

import base64
from collections.abc import AsyncGenerator
from pathlib import Path

import gradio as gr

from src.gui.api_client import mai_client
from src.gui.config import gui_settings
from src.gui.session import format_history_for_gradio, generate_session_id
from src.gui.theme import create_mai_theme


# Custom CSS for polished appearance
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

/* Status bar styling - works with dark theme */
.status-bar {
    background: transparent;
    padding: 0.5rem 0;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    opacity: 0.7;
    text-align: center;
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

/* Image upload styling */
.image-upload-container {
    border: 2px dashed #d1d5db;
    border-radius: 8px;
    padding: 0.5rem;
    transition: border-color 0.2s;
}
.image-upload-container:hover {
    border-color: #4f46e5;
}
.image-upload-container .upload-container {
    min-height: 100px;
}
.image-upload-container .upload-text {
    font-size: 0.75rem;
    line-height: 1.2;
}

/* Document upload styling */
.document-upload-container {
    border: 2px dashed #d1d5db;
    border-radius: 8px;
    padding: 0.5rem;
    transition: border-color 0.2s;
}
.document-upload-container:hover {
    border-color: #10b981;
}

/* Document status */
.document-status {
    font-size: 0.875rem;
    color: #059669;
    padding: 0.5rem;
    background: #d1fae5;
    border-radius: 6px;
    margin-top: 0.5rem;
}
"""


async def get_agents_list() -> dict:
    """Fetch available agents for dropdown."""
    try:
        agents = await mai_client.list_agents()
        # Use configured default if available, otherwise first agent
        default = gui_settings.default_agent if gui_settings.default_agent in agents else (agents[0] if agents else gui_settings.default_agent)
        return gr.Dropdown(choices=agents, value=default)
    except Exception:
        return gr.Dropdown(choices=[gui_settings.default_agent], value=gui_settings.default_agent)


async def get_current_model() -> str:
    """Fetch the currently loaded model from LM Studio."""
    try:
        models = await mai_client.list_models()
        if not models:
            return "No model loaded"

        # LM Studio /v1/models returns only loaded models
        loaded = [m.get("id", "unknown") for m in models]
        if loaded:
            return loaded[0]
        return "No model loaded"
    except Exception:
        return "Error fetching model"


async def check_connection() -> str:
    """Check API connection status."""
    health = await mai_client.health_check()
    llm_status = await mai_client.get_llm_status()

    parts = []

    if health.get("status") == "healthy":
        parts.append("[Connected]")
    else:
        error = health.get("error", "Unknown error")
        return f"[Disconnected]: {error}"

    # LLM status
    if llm_status.get("connected"):
        model_name = llm_status.get("model_name", "unknown")
        # Shorten model name if too long
        if len(model_name) > 25:
            model_name = model_name[:22] + "..."
        parts.append(f"LLM: OK ({model_name})")
    else:
        parts.append("LLM: X (fallback mode)")

    # Other services
    services = health.get("services", {})
    for k, v in services.items():
        if k != "llm":  # Skip LLM since we handle it separately
            parts.append(f"{k}: {'OK' if v else 'X'}")

    return " | ".join(parts)


async def check_llm_warning() -> dict:
    """Check if LLM is unavailable and return warning message with visibility."""
    llm_status = await mai_client.get_llm_status()
    if not llm_status.get("connected"):
        error = llm_status.get("error", "LLM unavailable")
        return gr.update(
            value=f"**Warning:** LLM unavailable - responses are in echo mode. ({error})",
            visible=True
        )
    return gr.update(value="", visible=False)


def encode_image(image_path: str) -> str | None:
    """Encode an image file to base64 data URI.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 data URI string or None if encoding fails
    """
    if not image_path:
        return None
    try:
        path = Path(image_path)
        if not path.exists():
            return None

        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")

        # Read and encode
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        return f"data:{media_type};base64,{data}"
    except Exception:
        return None


async def process_document(document_path: str) -> tuple[str | None, str]:
    """Process a document file and extract its content.

    Args:
        document_path: Path to the document file

    Returns:
        Tuple of (extracted_content, status_message)
    """
    if not document_path:
        return None, ""

    try:
        # Call the API to extract document content
        result = await mai_client.extract_document(document_path)
        if result:
            filename = result.get("filename", "document")
            char_count = result.get("char_count", 0)
            truncated = result.get("truncated", False)
            content = result.get("content", "")

            status = f"**Document loaded:** {filename} ({char_count:,} chars)"
            if truncated:
                status += " **[truncated]**"

            return content, status
        return None, "Failed to process document"
    except Exception as e:
        return None, f"Error: {str(e)}"


async def stream_response(
    message: str,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, list], None]:
    """Stream a response from the agent (text only).

    Args:
        message: User's message
        history: Chat history
        session_id: Session ID for conversation continuity
        agent_name: Name of the agent to use

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
            agent_name=agent_name,
            session_id=session_id,
        ):
            history[-1]["content"] += chunk
            yield "", history

    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "refused" in error_msg.lower():
            history[-1]["content"] = "Cannot connect to MAI API. Is the server running?"
        else:
            history[-1]["content"] = f"Error: {error_msg}"
        yield "", history


async def safe_stream_response(
    stream_func,
    *args,
    **kwargs,
) -> AsyncGenerator:
    """Wrapper for streaming responses with enhanced error handling.

    Args:
        stream_func: The streaming function to wrap
        *args: Positional arguments for the stream function
        **kwargs: Keyword arguments for the stream function

    Yields:
        Results from the wrapped stream function
    """
    try:
        async for result in stream_func(*args, **kwargs):
            yield result
    except ConnectionError as e:
        # Extract the history from the last yielded result or args
        history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
        if history and len(history) > 0:
            history[-1]["content"] = "Connection error: Cannot reach the MAI API server. Please check that the server is running."
        yield "", None, None, "", history
    except TimeoutError as e:
        history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
        if history and len(history) > 0:
            history[-1]["content"] = "Request timeout: The server took too long to respond. Please try again."
        yield "", None, None, "", history
    except Exception as e:
        history = kwargs.get("history", []) if kwargs else (args[4] if len(args) > 4 else [])
        error_msg = str(e)
        user_friendly_msg = f"An error occurred: {error_msg}"

        # Make common errors more user-friendly
        if "Connection" in error_msg or "refused" in error_msg.lower():
            user_friendly_msg = "Cannot connect to MAI API. Is the server running?"
        elif "timeout" in error_msg.lower():
            user_friendly_msg = "Request timed out. The model may be too slow or the server is overloaded."
        elif "404" in error_msg:
            user_friendly_msg = "API endpoint not found. Please check your API configuration."
        elif "500" in error_msg or "503" in error_msg:
            user_friendly_msg = "Server error. Please check the server logs."

        if history and len(history) > 0:
            history[-1]["content"] = user_friendly_msg
        yield "", None, None, "", history


async def stream_response_with_attachments(
    message: str,
    image: str | None,
    document: str | None,
    document_content: str | None,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, None, None, str, list], None]:
    """Stream a response from the agent, optionally with image and/or document.

    Args:
        message: User's text message
        image: Optional image file path
        document: Optional document file path
        document_content: Pre-extracted document content (if any)
        history: Chat history
        session_id: Session ID for conversation continuity
        agent_name: Name of the agent to use

    Yields:
        Tuple of (empty message, None image, None document, empty doc status, updated history)
    """
    if not message.strip() and not image and not document:
        yield "", None, None, "", history
        return

    history = history or []

    # Build the actual message to send to the API
    api_message = message

    # If we have document content, inject it into the message
    if document_content:
        doc_filename = Path(document).name if document else "document"
        formatted_doc = f"""<document filename="{doc_filename}">
{document_content}
</document>

{message}"""
        api_message = formatted_doc

    # Build user message for display
    display_message = message
    if document_content:
        doc_filename = Path(document).name if document else "document"
        display_message += f"\n\n[Document attached: {doc_filename}]"

    # Encode image if provided
    image_data = None
    if image:
        image_data = encode_image(image)
        if image_data:
            # Add image indicator to display message
            display_message += f"\n[Image attached]"

    # Add user message to history (dict format for Gradio 6.0+)
    history.append({"role": "user", "content": display_message})

    # Add assistant message with loading indicator
    history.append({"role": "assistant", "content": "..."})

    try:
        # Prepare images for API
        images = [image_data] if image_data else None

        # Stream the response, accumulating in the last history item
        assistant_response = ""
        async for chunk in mai_client.stream_chat(
            message=api_message,
            agent_name=agent_name,
            session_id=session_id,
            images=images,
        ):
            assistant_response += chunk
            history[-1]["content"] = assistant_response
            yield "", None, None, "", history

    except ConnectionError:
        history[-1]["content"] = "Connection error: Cannot reach the MAI API server. Please check that the server is running."
        yield "", None, None, "", history
    except TimeoutError:
        history[-1]["content"] = "Request timeout: The server took too long to respond. Please try again."
        yield "", None, None, "", history
    except Exception as e:
        error_msg = str(e)
        user_friendly_msg = f"An error occurred: {error_msg}"

        # Make common errors more user-friendly
        if "Connection" in error_msg or "refused" in error_msg.lower():
            user_friendly_msg = "Cannot connect to MAI API. Is the server running?"
        elif "timeout" in error_msg.lower():
            user_friendly_msg = "Request timed out. The model may be too slow or the server is overloaded."
        elif "404" in error_msg:
            user_friendly_msg = "API endpoint not found. Please check your API configuration."
        elif "500" in error_msg or "503" in error_msg:
            user_friendly_msg = "Server error. Please check the server logs."

        history[-1]["content"] = user_friendly_msg
        yield "", None, None, "", history


async def load_session_history(session_id: str) -> tuple[list, dict]:
    """Load conversation history for a session.

    Args:
        session_id: The session ID to load history for

    Returns:
        Tuple of (history list, feedback update)
    """
    if not session_id:
        return [], gr.update(value="No session ID provided", visible=True)
    try:
        api_messages = await mai_client.get_history(session_id)
        history = format_history_for_gradio(api_messages)
        if history:
            return history, gr.update(value=f"Loaded {len(history)} messages", visible=True)
        return [], gr.update(value="No history found for this session", visible=True)
    except Exception as e:
        return [], gr.update(value=f"Error loading history: {e}", visible=True)


async def clear_session(session_id: str) -> tuple[str, list, str, dict]:
    """Clear the current session and start fresh.

    Args:
        session_id: The session ID to clear

    Returns:
        Tuple of (new session ID, empty history, session info text, feedback update)
    """
    if session_id:
        try:
            await mai_client.clear_history(session_id)
        except Exception:
            pass
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`", gr.update(value="", visible=False)


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""
    initial_session_id = generate_session_id()

    with gr.Blocks(title=gui_settings.app_title) as demo:
        # Header with branding
        with gr.Column(elem_classes=["app-header"]):
            gr.Markdown(f"# {gui_settings.app_title}")
            gr.Markdown("*Your private AI assistant powered by local LLMs*")

        # Status bar with better formatting
        status_bar = gr.Markdown(
            "Checking connection...",
            elem_classes=["status-bar"],
        )

        # LLM warning banner (hidden when empty)
        llm_warning = gr.Markdown("", visible=False, elem_classes=["warning-banner"])

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
            with gr.Column(scale=2):
                with gr.Row():
                    model_display = gr.Textbox(
                        label="Model",
                        value="Loading...",
                        interactive=False,
                        container=True,
                        scale=4,
                    )
                    refresh_model_btn = gr.Button("↻", size="sm", scale=1)
            with gr.Column(scale=3):
                session_id = gr.Textbox(
                    label="Session ID",
                    value=initial_session_id,
                    interactive=True,
                    container=True,
                )
            with gr.Column(scale=1):
                load_btn = gr.Button("Load Session", size="sm")

        # Feedback area (hidden when empty)
        feedback = gr.Markdown("", visible=False)

        # Chat interface with avatars and multimodal support
        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            avatar_images=(
                "https://api.dicebear.com/7.x/avataaars/svg?seed=user",
                "https://api.dicebear.com/7.x/bottts/svg?seed=mai",
            ),
            elem_classes=["chatbot-container"],
        )

        # Message input with attachments in tabs
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Tabs():
                    with gr.Tab("Image"):
                        image_input = gr.Image(
                            label="Attach Image",
                            type="filepath",
                            height=150,
                            sources=["upload", "clipboard"],
                            show_label=False,
                            elem_classes=["image-upload-container"],
                        )
                    with gr.Tab("Document"):
                        document_input = gr.File(
                            label="Attach Document",
                            type="filepath",
                            file_types=[".pdf", ".txt", ".md", ".markdown"],
                            show_label=False,
                            elem_classes=["document-upload-container"],
                        )
                        document_status = gr.Markdown(
                            "",
                            visible=True,
                            elem_classes=["document-status"],
                        )
            with gr.Column(scale=4):
                msg = gr.Textbox(
                    label="Message",
                    placeholder="Type your message here... (Enter to send, Shift+Enter for new line)",
                    lines=3,
                    show_label=True,
                )
            with gr.Column(scale=1):
                submit_btn = gr.Button("Send", variant="primary", size="lg", elem_classes=["primary-btn"])

        # Action buttons
        with gr.Row():
            clear_btn = gr.Button("Clear Chat", variant="secondary")

        # Session info footer
        session_info = gr.Markdown(
            f"Session: `{initial_session_id}`",
            elem_classes=["session-info"],
        )

        # Hidden state for document content
        document_content_state = gr.State(None)

        # --- Event Handlers ---

        # Load agents, models and check connection on page load
        demo.load(get_agents_list, outputs=[agent_selector])
        demo.load(get_current_model, outputs=[model_display])
        demo.load(check_connection, outputs=[status_bar])
        demo.load(check_llm_warning, outputs=[llm_warning])

        # Model refresh button
        refresh_model_btn.click(
            get_current_model,
            outputs=[model_display],
        )

        # Session management
        load_btn.click(
            load_session_history,
            inputs=[session_id],
            outputs=[chatbot, feedback],
        )
        clear_btn.click(
            clear_session,
            inputs=[session_id],
            outputs=[session_id, chatbot, session_info, feedback],
        )

        # Document upload processing
        document_input.change(
            process_document,
            inputs=[document_input],
            outputs=[document_content_state, document_status],
        )

        # Chat submission (with image and document support)
        submit_btn.click(
            stream_response_with_attachments,
            inputs=[msg, image_input, document_input, document_content_state, chatbot, session_id, agent_selector],
            outputs=[msg, image_input, document_input, document_status, chatbot],
        )
        msg.submit(
            stream_response_with_attachments,
            inputs=[msg, image_input, document_input, document_content_state, chatbot, session_id, agent_selector],
            outputs=[msg, image_input, document_input, document_status, chatbot],
        )

        # Update session info display
        session_id.change(
            lambda sid: f"Session: `{sid}`",
            inputs=[session_id],
            outputs=[session_info],
        )

    return demo


def main() -> None:
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=gui_settings.server_port,
        share=False,
        show_error=True,
        theme=create_mai_theme(),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
