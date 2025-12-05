"""LLM Provider Factory.

This module provides a unified factory for creating LLM model instances,
supporting multiple providers (OpenAI, LM Studio) with automatic selection.
"""

from typing import Literal, Optional

from pydantic_ai.models.openai import OpenAIModel

from src.core.models.lmstudio_provider import create_lmstudio_model
from src.core.utils.config import get_settings
from src.core.utils.exceptions import ConfigurationError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()

ProviderType = Literal["openai", "lmstudio", "auto"]


def get_model_provider(
    provider: Optional[ProviderType] = None,
) -> OpenAIModel:
    """Get an LLM model instance based on provider configuration.

    This factory function returns the appropriate model based on:
    1. Explicit provider parameter (if provided)
    2. LLM__PROVIDER environment variable / settings
    3. Auto-detection based on available API keys

    Args:
        provider: Override the configured provider. Options: 'openai', 'lmstudio', 'auto'

    Returns:
        Configured OpenAIModel instance (works for both OpenAI and LM Studio)

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
        ```
    """
    settings = get_settings()

    # Determine which provider to use
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = _auto_detect_provider()

    logger.info(f"Using LLM provider: {selected_provider}")

    if selected_provider == "openai":
        return _create_openai_model()
    elif selected_provider == "lmstudio":
        return _create_lmstudio_model()
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', or 'auto'."
        )


def _auto_detect_provider() -> str:
    """Auto-detect which provider to use based on available configuration.

    Priority:
    1. OpenAI if API key is configured
    2. LM Studio as fallback

    Returns:
        Provider name: 'openai' or 'lmstudio'
    """
    settings = get_settings()

    if settings.openai.api_key:
        logger.debug("Auto-detected provider: OpenAI (API key found)")
        return "openai"

    logger.debug("Auto-detected provider: LM Studio (no OpenAI API key)")
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
            "Set OPENAI__API_KEY environment variable or use LM Studio instead."
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


def _create_lmstudio_model() -> OpenAIModel:
    """Create an LM Studio model instance.

    Returns:
        Configured OpenAIModel instance for LM Studio
    """
    model = create_lmstudio_model(auto_detect=False)
    return model


async def get_model_provider_async(
    provider: Optional[ProviderType] = None,
    test_connection: bool = False,
) -> OpenAIModel:
    """Async version of get_model_provider with optional connection testing.

    For LM Studio, this can auto-detect the loaded model and test the connection.
    For OpenAI, this behaves the same as the sync version.

    Args:
        provider: Override the configured provider. Options: 'openai', 'lmstudio', 'auto'
        test_connection: If True, test connection for LM Studio (ignored for OpenAI)

    Returns:
        Configured OpenAIModel instance

    Example:
        ```python
        from src.core.models.providers import get_model_provider_async

        # With connection testing for LM Studio
        model = await get_model_provider_async(test_connection=True)
        ```
    """
    settings = get_settings()

    # Determine which provider to use
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = _auto_detect_provider()

    logger.info(f"Using LLM provider: {selected_provider}")

    if selected_provider == "openai":
        return _create_openai_model()
    elif selected_provider == "lmstudio":
        if test_connection:
            from src.core.models.lmstudio_provider import create_lmstudio_model_async
            return await create_lmstudio_model_async(auto_detect=True, test_connection=True)
        return _create_lmstudio_model()
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', or 'auto'."
        )
