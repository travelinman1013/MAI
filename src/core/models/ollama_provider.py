"""Ollama model provider for Pydantic AI.

This module provides integration with Ollama's OpenAI-compatible API:
- Factory function for creating Ollama model instances
- Automatic model detection from /api/tags endpoint
- Connection health checks
- Configurable timeout and retry settings
"""

from typing import Optional

import httpx
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.config import OllamaSettings, get_settings
from src.core.utils.exceptions import ModelError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


async def detect_ollama_model(
    base_url: str, timeout: int = 10
) -> Optional[str]:
    """Detect available models in Ollama using native API.

    Args:
        base_url: Ollama base URL (e.g., http://localhost:11434/v1)
        timeout: Request timeout in seconds

    Returns:
        Model ID of the first available model, or None if no models found

    Note:
        Uses native /api/tags endpoint, not OpenAI-compatible /v1/models
    """
    # Convert /v1 URL to base URL for native API
    native_url = base_url.replace("/v1", "").rstrip("/")
    tags_url = f"{native_url}/api/tags"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Detecting Ollama models", url=tags_url)
            response = await client.get(tags_url)
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])

            if not models:
                logger.warning("No models found in Ollama")
                return None

            # Return first model name
            model_name = models[0].get("name")
            logger.info(
                f"Detected Ollama model: {model_name}",
                model_count=len(models)
            )
            return model_name

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error detecting Ollama model: {e.response.status_code}")
        raise ModelError(
            f"HTTP error detecting Ollama model: {e.response.status_code}",
            model_name="ollama",
            details={"status_code": e.response.status_code, "url": tags_url},
        )
    except httpx.RequestError as e:
        logger.error(f"Connection error detecting Ollama model: {e}")
        raise ModelError(
            f"Connection error to Ollama: {e}",
            model_name="ollama",
            details={"error": str(e), "url": native_url},
        )
    except Exception as e:
        logger.error(f"Unexpected error detecting Ollama model: {e}")
        raise ModelError(
            f"Unexpected error detecting Ollama model: {e}",
            model_name="ollama",
            details={"error": str(e)},
        )


async def ollama_health_check(
    settings: Optional[OllamaSettings] = None,
) -> ProviderHealthStatus:
    """Perform health check on Ollama server.

    Args:
        settings: Ollama configuration. If None, uses global settings.

    Returns:
        ProviderHealthStatus with connection and model information
    """
    ollama_settings = settings or get_settings().ollama

    health = ProviderHealthStatus(
        connected=False,
        model_detected=False,
        model_id=None,
        base_url=ollama_settings.base_url,
        provider_type="ollama",
    )

    try:
        model_id = await detect_ollama_model(
            ollama_settings.base_url, ollama_settings.timeout
        )

        health.connected = True

        if model_id:
            health.model_detected = True
            health.model_id = model_id

    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        health.error = str(e)

    return health


def create_ollama_model(
    model_name: Optional[str] = None,
    settings: Optional[OllamaSettings] = None,
    auto_detect: bool = False,
) -> OpenAIModel:
    """Create Ollama model instance for Pydantic AI.

    Args:
        model_name: Model name/ID. If None, uses default from settings.
        settings: Ollama configuration. If None, uses global settings.
        auto_detect: If True, requires async context (use create_ollama_model_async)

    Returns:
        Configured OpenAIModel instance for Ollama
    """
    ollama_settings = settings or get_settings().ollama

    final_model_name = model_name or ollama_settings.model_name

    provider = OpenAIProvider(
        base_url=ollama_settings.base_url,
        api_key=ollama_settings.api_key,
    )

    model = OpenAIModel(
        final_model_name,
        provider=provider,
    )

    logger.info(
        "Created Ollama model",
        model_name=final_model_name,
        base_url=ollama_settings.base_url,
    )

    return model


async def create_ollama_model_async(
    model_name: Optional[str] = None,
    settings: Optional[OllamaSettings] = None,
    auto_detect: bool = True,
    test_connection: bool = True,
) -> OpenAIModel:
    """Create Ollama model with async model detection and connection testing.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, detects from Ollama.
        settings: Ollama configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model.
        test_connection: If True, test connection to Ollama before returning.

    Returns:
        Configured OpenAIModel instance for Ollama
    """
    ollama_settings = settings or get_settings().ollama

    if auto_detect and model_name is None:
        logger.info("Auto-detecting Ollama model")
        detected_model = await detect_ollama_model(
            ollama_settings.base_url, ollama_settings.timeout
        )

        if detected_model is None:
            raise ModelError(
                "No models detected in Ollama. Please pull a model first: ollama pull llama3.2",
                model_name="ollama",
            )

        model_name = detected_model

    if test_connection and model_name is None:
        logger.info("Testing Ollama connection")
        await detect_ollama_model(
            ollama_settings.base_url, ollama_settings.timeout
        )

    return create_ollama_model(
        model_name=model_name, settings=ollama_settings, auto_detect=False
    )
