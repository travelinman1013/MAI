"""Session management for the Gradio GUI."""

import uuid
from datetime import datetime


def generate_session_id() -> str:
    """Generate a new unique session ID.

    Returns:
        A unique session ID string in format gui_YYYYMMDD_HHMMSS_xxxxxxxx
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
