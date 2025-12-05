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


gui_settings = GUISettings()
