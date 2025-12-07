"""Model provider module.

Provides LLM integration for Pydantic AI with multiple providers:
- OpenAI API (native support)
- LM Studio (OpenAI-compatible local models)
- Ollama (local model server)
- llama.cpp (direct local inference)
- Automatic provider selection
- Connection health checks
- Streaming support
"""

from src.core.models.base_provider import (
    LLMProviderProtocol,
    ProviderHealthStatus,
    ProviderType,
)
from src.core.models.lmstudio_provider import (
    create_lmstudio_model,
    create_lmstudio_model_async,
    detect_lmstudio_model,
    get_lmstudio_model,
    get_lmstudio_model_async,
    lmstudio_health_check,
    test_lmstudio_connection,
)
from src.core.models.ollama_provider import (
    create_ollama_model,
    create_ollama_model_async,
    detect_ollama_model,
    ollama_health_check,
)
from src.core.models.llamacpp_provider import (
    create_llamacpp_model,
    create_llamacpp_model_async,
    detect_llamacpp_model,
    llamacpp_health_check,
)
from src.core.models.providers import (
    check_all_providers,
    get_model_provider,
    get_model_provider_async,
)

__all__ = [
    # Base provider types
    "ProviderType",
    "ProviderHealthStatus",
    "LLMProviderProtocol",
    # Provider factory (recommended)
    "get_model_provider",
    "get_model_provider_async",
    "check_all_providers",
    # LM Studio specific
    "create_lmstudio_model",
    "create_lmstudio_model_async",
    "detect_lmstudio_model",
    "get_lmstudio_model",
    "get_lmstudio_model_async",
    "lmstudio_health_check",
    "test_lmstudio_connection",
    # Ollama specific
    "create_ollama_model",
    "create_ollama_model_async",
    "detect_ollama_model",
    "ollama_health_check",
    # llama.cpp specific
    "create_llamacpp_model",
    "create_llamacpp_model_async",
    "detect_llamacpp_model",
    "llamacpp_health_check",
]
