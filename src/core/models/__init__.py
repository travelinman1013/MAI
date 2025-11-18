"""Model provider module.

Provides LM Studio integration for Pydantic AI:
- OpenAI-compatible model provider
- Automatic model detection
- Connection health checks
- Streaming support
"""

from src.core.models.lmstudio_provider import (
    create_lmstudio_model,
    create_lmstudio_model_async,
    detect_lmstudio_model,
    get_lmstudio_model,
    get_lmstudio_model_async,
    lmstudio_health_check,
    test_lmstudio_connection,
)

__all__ = [
    "create_lmstudio_model",
    "create_lmstudio_model_async",
    "detect_lmstudio_model",
    "get_lmstudio_model",
    "get_lmstudio_model_async",
    "lmstudio_health_check",
    "test_lmstudio_connection",
]
