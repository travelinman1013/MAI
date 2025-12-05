"""Model provider module.

Provides LLM integration for Pydantic AI with multiple providers:
- OpenAI API (native support)
- LM Studio (OpenAI-compatible local models)
- Automatic provider selection
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
from src.core.models.providers import (
    get_model_provider,
    get_model_provider_async,
)

__all__ = [
    # Provider factory (recommended)
    "get_model_provider",
    "get_model_provider_async",
    # LM Studio specific
    "create_lmstudio_model",
    "create_lmstudio_model_async",
    "detect_lmstudio_model",
    "get_lmstudio_model",
    "get_lmstudio_model_async",
    "lmstudio_health_check",
    "test_lmstudio_connection",
]
