"""Custom Gradio theme for MAI application."""

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
        code_background_fill="*neutral_100",
    )
