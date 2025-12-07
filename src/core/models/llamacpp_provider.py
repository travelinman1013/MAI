"""llama.cpp server model provider for Pydantic AI.

This module provides integration with llama.cpp's OpenAI-compatible server:
- Factory function for creating llama.cpp model instances
- Server health checks via /health endpoint
- Model detection from /v1/models endpoint
- Support for both llama-server and llama-cpp-python
"""

from typing import Optional

import httpx
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.config import LlamaCppSettings, get_settings
from src.core.utils.exceptions import ModelError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


async def detect_llamacpp_model(
    base_url: str, timeout: int = 10
) -> Optional[str]:
    """Detect the loaded model in llama.cpp server.

    Args:
        base_url: llama.cpp server base URL (e.g., http://localhost:8080/v1)
        timeout: Request timeout in seconds

    Returns:
        Model ID if available, or None

    Note:
        llama.cpp loads one model at startup. The /v1/models endpoint
        returns info about the loaded model.
    """
    models_url = base_url.rstrip("/") + "/models"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Detecting llama.cpp model", url=models_url)
            response = await client.get(models_url)
            response.raise_for_status()

            data = response.json()
            models = data.get("data", [])

            if not models:
                logger.warning("No model info from llama.cpp server")
                return None

            model_id = models[0].get("id")
            logger.info(f"Detected llama.cpp model: {model_id}")
            return model_id

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error detecting llama.cpp model: {e.response.status_code}")
        raise ModelError(
            f"HTTP error detecting llama.cpp model: {e.response.status_code}",
            model_name="llamacpp",
            details={"status_code": e.response.status_code, "url": models_url},
        )
    except httpx.RequestError as e:
        logger.error(f"Connection error detecting llama.cpp model: {e}")
        raise ModelError(
            f"Connection error to llama.cpp server: {e}",
            model_name="llamacpp",
            details={"error": str(e), "url": base_url},
        )
    except Exception as e:
        logger.error(f"Unexpected error detecting llama.cpp model: {e}")
        raise ModelError(
            f"Unexpected error detecting llama.cpp model: {e}",
            model_name="llamacpp",
            details={"error": str(e)},
        )


async def llamacpp_health_check(
    settings: Optional[LlamaCppSettings] = None,
) -> ProviderHealthStatus:
    """Perform health check on llama.cpp server.

    Args:
        settings: llama.cpp configuration. If None, uses global settings.

    Returns:
        ProviderHealthStatus with connection and model information
    """
    llamacpp_settings = settings or get_settings().llamacpp

    # Get base URL without /v1 for health endpoint
    base_url = llamacpp_settings.base_url.replace("/v1", "").rstrip("/")

    health = ProviderHealthStatus(
        connected=False,
        model_detected=False,
        model_id=None,
        base_url=llamacpp_settings.base_url,
        provider_type="llamacpp",
    )

    try:
        # First check /health endpoint
        async with httpx.AsyncClient(timeout=llamacpp_settings.timeout) as client:
            health_url = f"{base_url}/health"
            response = await client.get(health_url)

            if response.status_code == 200:
                health.connected = True
                health_data = response.json()
                health.metadata["status"] = health_data.get("status", "unknown")

        # Then try to detect model
        if health.connected:
            model_id = await detect_llamacpp_model(
                llamacpp_settings.base_url, llamacpp_settings.timeout
            )
            if model_id:
                health.model_detected = True
                health.model_id = model_id

    except Exception as e:
        logger.error("llama.cpp health check failed", error=str(e))
        health.error = str(e)

    return health


def create_llamacpp_model(
    model_name: Optional[str] = None,
    settings: Optional[LlamaCppSettings] = None,
) -> OpenAIModel:
    """Create llama.cpp model instance for Pydantic AI.

    Args:
        model_name: Model name/ID (for logging). If None, uses default from settings.
        settings: llama.cpp configuration. If None, uses global settings.

    Returns:
        Configured OpenAIModel instance for llama.cpp

    Note:
        The model_name is mainly for logging/identification purposes since
        llama.cpp loads a single model at server startup.
    """
    llamacpp_settings = settings or get_settings().llamacpp

    final_model_name = model_name or llamacpp_settings.model_name

    provider = OpenAIProvider(
        base_url=llamacpp_settings.base_url,
        api_key=llamacpp_settings.api_key,
    )

    model = OpenAIModel(
        final_model_name,
        provider=provider,
    )

    logger.info(
        "Created llama.cpp model",
        model_name=final_model_name,
        base_url=llamacpp_settings.base_url,
    )

    return model


async def create_llamacpp_model_async(
    model_name: Optional[str] = None,
    settings: Optional[LlamaCppSettings] = None,
    auto_detect: bool = True,
    test_connection: bool = True,
) -> OpenAIModel:
    """Create llama.cpp model with async detection and connection testing.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, detects from server.
        settings: llama.cpp configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model.
        test_connection: If True, test connection before returning.

    Returns:
        Configured OpenAIModel instance for llama.cpp
    """
    llamacpp_settings = settings or get_settings().llamacpp

    if auto_detect and model_name is None:
        logger.info("Auto-detecting llama.cpp model")
        detected_model = await detect_llamacpp_model(
            llamacpp_settings.base_url, llamacpp_settings.timeout
        )

        if detected_model:
            model_name = detected_model

    if test_connection:
        logger.info("Testing llama.cpp connection")
        health = await llamacpp_health_check(llamacpp_settings)
        if not health.connected:
            raise ModelError(
                f"Cannot connect to llama.cpp server: {health.error}",
                model_name="llamacpp",
            )

    return create_llamacpp_model(
        model_name=model_name, settings=llamacpp_settings
    )
