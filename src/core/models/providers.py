"""LLM Provider Factory.

This module provides a unified factory for creating LLM model instances,
supporting multiple providers (OpenAI, LM Studio, Ollama, llama.cpp) with
automatic selection and intelligent auto-detection.
"""

from typing import Literal, Optional

from pydantic_ai.models.openai import OpenAIModel

from src.core.models.base_provider import ProviderHealthStatus
from src.core.models.lmstudio_provider import (
    create_lmstudio_model,
    create_lmstudio_model_async,
    lmstudio_health_check,
)
from src.core.models.ollama_provider import (
    create_ollama_model,
    create_ollama_model_async,
    ollama_health_check,
)
from src.core.models.llamacpp_provider import (
    create_llamacpp_model,
    create_llamacpp_model_async,
    llamacpp_health_check,
)
from src.core.utils.config import get_settings
from src.core.utils.exceptions import ConfigurationError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()

ProviderType = Literal["openai", "lmstudio", "ollama", "llamacpp", "auto"]


def _auto_detect_provider() -> str:
    """Sync auto-detection (limited - prefers configured provider).

    For full auto-detection with connectivity checks, use async version.

    Priority:
    1. OpenAI if API key is configured
    2. Configured provider (if not 'auto')
    3. LM Studio as default fallback

    Returns:
        Provider name string
    """
    settings = get_settings()

    # Check OpenAI first if API key is set
    if settings.openai.api_key:
        logger.debug("Auto-detected provider: OpenAI (API key found)")
        return "openai"

    # In sync context, return configured or default to lmstudio
    if settings.llm.provider != "auto":
        return settings.llm.provider

    logger.debug("Auto-detected provider: LM Studio (default)")
    return "lmstudio"


async def _auto_detect_provider_async() -> str:
    """Async auto-detection with connectivity checks.

    Tries providers in this order:
    1. OpenAI if API key is configured
    2. LM Studio
    3. Ollama
    4. llama.cpp

    Returns:
        Provider name string
    """
    settings = get_settings()

    # Check OpenAI first if API key is set
    if settings.openai.api_key:
        logger.info("Auto-detect: Using OpenAI (API key configured)")
        return "openai"

    # Try local providers in order
    local_providers = [
        ("lmstudio", lmstudio_health_check),
        ("ollama", ollama_health_check),
        ("llamacpp", llamacpp_health_check),
    ]

    for provider_name, health_check_fn in local_providers:
        try:
            health = await health_check_fn()
            # Handle both dict and ProviderHealthStatus returns
            if isinstance(health, dict):
                connected = health.get("connected", False)
                model_id = health.get("model_id")
            else:
                connected = health.connected
                model_id = health.model_id

            if connected:
                logger.info(
                    f"Auto-detect: Using {provider_name}",
                    model=model_id,
                )
                return provider_name
        except Exception as e:
            logger.debug(f"Auto-detect: {provider_name} not available: {e}")
            continue

    # Default to lmstudio if nothing else works
    logger.warning("Auto-detect: No providers available, defaulting to lmstudio")
    return "lmstudio"


def _create_openai_model() -> OpenAIModel:
    """Create an OpenAI model instance.

    Returns:
        Configured OpenAIModel instance

    Raises:
        ConfigurationError: If OpenAI API key is not configured
    """
    settings = get_settings()

    if not settings.openai.api_key:
        raise ConfigurationError(
            "OpenAI API key not configured. "
            "Set OPENAI__API_KEY environment variable or use a local provider instead."
        )

    model = OpenAIModel(
        settings.openai.model,
        api_key=settings.openai.api_key,
    )

    logger.info(
        "Created OpenAI model",
        model=settings.openai.model,
    )

    return model


def get_model_provider(
    provider: Optional[ProviderType] = None,
) -> OpenAIModel:
    """Get an LLM model instance based on provider configuration.

    This factory function returns the appropriate model based on:
    1. Explicit provider parameter (if provided)
    2. LLM__PROVIDER environment variable / settings
    3. Auto-detection based on available API keys

    Args:
        provider: Override the configured provider. Options:
                  'openai', 'lmstudio', 'ollama', 'llamacpp', 'auto'

    Returns:
        Configured OpenAIModel instance (works for all OpenAI-compatible providers)

    Raises:
        ConfigurationError: If provider is invalid or required credentials are missing

    Example:
        ```python
        from src.core.models.providers import get_model_provider

        # Use configured provider
        model = get_model_provider()

        # Force OpenAI
        model = get_model_provider(provider="openai")

        # Force LM Studio
        model = get_model_provider(provider="lmstudio")

        # Force Ollama
        model = get_model_provider(provider="ollama")

        # Force llama.cpp
        model = get_model_provider(provider="llamacpp")
        ```
    """
    settings = get_settings()

    # Determine which provider to use
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = _auto_detect_provider()

    logger.info(f"Creating model for provider: {selected_provider}")

    if selected_provider == "openai":
        return _create_openai_model()
    elif selected_provider == "lmstudio":
        return create_lmstudio_model(auto_detect=False)
    elif selected_provider == "ollama":
        return create_ollama_model()
    elif selected_provider == "llamacpp":
        return create_llamacpp_model()
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', or 'auto'."
        )


async def get_model_provider_async(
    provider: Optional[ProviderType] = None,
    test_connection: bool = False,
    auto_detect_model: bool = True,
) -> OpenAIModel:
    """Async version of get_model_provider with full auto-detection.

    For local providers (LM Studio, Ollama, llama.cpp), this can auto-detect
    the loaded model and test the connection. For OpenAI, this behaves the
    same as the sync version.

    Args:
        provider: Override the configured provider. Options:
                  'openai', 'lmstudio', 'ollama', 'llamacpp', 'auto'
        test_connection: If True, verify connection before returning.
        auto_detect_model: If True, auto-detect model from provider.

    Returns:
        Configured OpenAIModel instance

    Raises:
        ConfigurationError: If provider is invalid
        ModelError: If connection test fails

    Example:
        ```python
        from src.core.models.providers import get_model_provider_async

        # With full auto-detection
        model = await get_model_provider_async()

        # With connection testing for Ollama
        model = await get_model_provider_async(
            provider="ollama",
            test_connection=True
        )
        ```
    """
    settings = get_settings()

    # Determine which provider to use
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = await _auto_detect_provider_async()

    logger.info(f"Creating async model for provider: {selected_provider}")

    if selected_provider == "openai":
        return _create_openai_model()
    elif selected_provider == "lmstudio":
        return await create_lmstudio_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    elif selected_provider == "ollama":
        return await create_ollama_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    elif selected_provider == "llamacpp":
        return await create_llamacpp_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', or 'auto'."
        )


async def check_all_providers() -> dict[str, ProviderHealthStatus]:
    """Check health of all configured providers.

    Performs health checks on all supported providers and returns
    a dictionary with the results. This is useful for diagnostics
    and for determining which providers are available.

    Returns:
        Dict mapping provider name to ProviderHealthStatus

    Example:
        ```python
        from src.core.models.providers import check_all_providers

        results = await check_all_providers()
        for name, status in results.items():
            if status.connected:
                print(f"{name}: connected, model={status.model_id}")
            else:
                print(f"{name}: not available - {status.error}")
        ```
    """
    results: dict[str, ProviderHealthStatus] = {}

    # Check OpenAI (just config validation - no actual connection test)
    settings = get_settings()
    results["openai"] = ProviderHealthStatus(
        connected=bool(settings.openai.api_key),
        model_detected=bool(settings.openai.api_key),
        model_id=settings.openai.model if settings.openai.api_key else None,
        base_url="https://api.openai.com/v1",
        provider_type="openai",
    )

    # Check local providers
    for name, health_fn in [
        ("lmstudio", lmstudio_health_check),
        ("ollama", ollama_health_check),
        ("llamacpp", llamacpp_health_check),
    ]:
        try:
            health = await health_fn()
            # Handle lmstudio_health_check which returns dict instead of ProviderHealthStatus
            if isinstance(health, dict):
                results[name] = ProviderHealthStatus(
                    connected=health.get("connected", False),
                    model_detected=health.get("model_detected", False),
                    model_id=health.get("model_id"),
                    base_url=health.get("base_url", ""),
                    error=health.get("error"),
                    provider_type=name,
                )
            else:
                results[name] = health
        except Exception as e:
            results[name] = ProviderHealthStatus(
                connected=False,
                model_detected=False,
                model_id=None,
                base_url="",
                error=str(e),
                provider_type=name,
            )

    return results
