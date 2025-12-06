"""Configuration for the Gradio GUI."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class GUISettings(BaseSettings):
    """Settings for the Gradio chat interface."""

    model_config = SettingsConfigDict(
        env_prefix="GUI_",
        extra="ignore",
    )

    api_base_url: str = "http://localhost:8000/api/v1"
    default_agent: str = "chat_agent"
    app_title: str = "MAI Chat Interface"
    server_port: int = 7860

    # Document and image limits
    max_document_size_mb: int = 10
    max_image_size_mb: int = 5

    # Feature flags
    enable_model_switching: bool = True
    show_debug_info: bool = False


gui_settings = GUISettings()
