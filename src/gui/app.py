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
        clear_btn.click(lambda: ("", []), outputs=[msg, chatbot])

    return demo


def main() -> None:
    """Launch the Gradio interface."""
    demo = create_chat_interface()
    demo.launch(
        server_port=gui_settings.server_port,
        share=False,
    )


if __name__ == "__main__":
    main()
