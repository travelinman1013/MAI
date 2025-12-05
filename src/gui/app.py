"""Gradio chat interface for MAI agents."""

from collections.abc import AsyncGenerator

import gradio as gr

from src.gui.api_client import mai_client
from src.gui.config import gui_settings
from src.gui.session import format_history_for_gradio, generate_session_id


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
        # Use configured default if available, otherwise first agent
        default = gui_settings.default_agent if gui_settings.default_agent in agents else (agents[0] if agents else gui_settings.default_agent)
        return gr.Dropdown(choices=agents, value=default)
    except Exception:
        return gr.Dropdown(choices=[gui_settings.default_agent], value=gui_settings.default_agent)


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


async def check_llm_warning() -> str:
    """Check if LLM is unavailable and return warning message."""
    llm_status = await mai_client.get_llm_status()
    if not llm_status.get("connected"):
        error = llm_status.get("error", "LLM unavailable")
        return f"**Warning:** LLM unavailable - responses are in echo mode. ({error})"
    return ""


async def stream_response(
    message: str,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, list], None]:
    """Stream a response from the agent.

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


async def load_session_history(session_id: str) -> tuple[list, str]:
    """Load conversation history for a session.

    Args:
        session_id: The session ID to load history for

    Returns:
        Tuple of (history list, feedback message)
    """
    if not session_id:
        return [], "No session ID provided"
    try:
        api_messages = await mai_client.get_history(session_id)
        history = format_history_for_gradio(api_messages)
        if history:
            return history, f"Loaded {len(history)} messages"
        return [], "No history found for this session"
    except Exception as e:
        return [], f"Error loading history: {e}"


async def clear_session(session_id: str) -> tuple[str, list, str, str]:
    """Clear the current session and start fresh.

    Args:
        session_id: The session ID to clear

    Returns:
        Tuple of (new session ID, empty history, session info text, feedback)
    """
    if session_id:
        try:
            await mai_client.clear_history(session_id)
        except Exception:
            pass
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`", "Session cleared"


async def new_session() -> tuple[str, list, str, str]:
    """Start a new session without clearing old one.

    Returns:
        Tuple of (new session ID, empty history, session info text, feedback)
    """
    new_session_id = generate_session_id()
    return new_session_id, [], f"Session: `{new_session_id}`", "New session started"


def create_chat_interface() -> gr.Blocks:
    """Create the Gradio chat interface."""
    initial_session_id = generate_session_id()

    with gr.Blocks(title=gui_settings.app_title) as demo:
        gr.Markdown(f"# {gui_settings.app_title}")
        gr.Markdown("Chat with MAI agents powered by Pydantic AI")

        # Status bar
        status_bar = gr.Markdown("Checking connection...")

        # LLM warning banner (hidden by default)
        llm_warning = gr.Markdown("", visible=True)

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
                value=initial_session_id,
                interactive=True,
                scale=2,
            )
            load_btn = gr.Button("Load", scale=1)
            new_btn = gr.Button("New", scale=1)

        # Feedback message
        feedback = gr.Markdown("")

        # Chat interface
        chatbot = gr.Chatbot(
            label="Conversation",
            height=450,
            buttons=["copy", "copy_all"],
        )

        # Message input
        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Type your message here... (Enter to send)",
                lines=2,
                scale=4,
            )
            submit_btn = gr.Button("Send", variant="primary", scale=1)

        # Action buttons
        with gr.Row():
            clear_btn = gr.Button("Clear Chat", variant="secondary")

        # Session info footer
        session_info = gr.Markdown(f"Session: `{initial_session_id}`")

        # --- Event Handlers ---

        # Load agents and check connection on page load
        demo.load(get_agents_list, outputs=[agent_selector])
        demo.load(check_connection, outputs=[status_bar])
        demo.load(check_llm_warning, outputs=[llm_warning])

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

    return demo  # type: ignore[no-any-return]


def main() -> None:
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.queue()  # Enable queuing for streaming
    demo.launch(
        server_name="0.0.0.0",  # Bind to all interfaces for Docker
        server_port=gui_settings.server_port,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
