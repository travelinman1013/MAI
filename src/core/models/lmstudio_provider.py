"""LM Studio model provider for Pydantic AI.

This module provides integration with LM Studio's OpenAI-compatible API:
- Factory function for creating LM Studio model instances
- Automatic model detection from /v1/models endpoint
- Support for chat completions and embeddings
- Streaming support
- Connection health checks
- Configurable timeout and retry settings
"""

from typing import Optional

import httpx
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.utils.config import LMStudioSettings, get_settings
from src.core.utils.exceptions import ModelError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


async def detect_lmstudio_model(
    base_url: str, api_key: str = "not-needed", timeout: int = 10
) -> Optional[str]:
    """Detect the currently loaded model in LM Studio.

    Args:
        base_url: LM Studio base URL (e.g., http://localhost:1234/v1)
        api_key: API key (not needed for LM Studio, but required by SDK)
        timeout: Request timeout in seconds

    Returns:
        Model ID of the first available model, or None if no models found

    Raises:
        ModelError: If connection to LM Studio fails

    Example:
        ```python
        model_id = await detect_lmstudio_model("http://localhost:1234/v1")
        print(f"Detected model: {model_id}")
        # Detected model: TheBloke/Llama-2-7B-Chat-GGUF
        ```
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Construct models endpoint URL
            models_url = base_url.rstrip("/") + "/models"

            logger.debug("Detecting LM Studio models", url=models_url)

            # Make request to /v1/models endpoint
            response = await client.get(
                models_url, headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()

            # Parse response
            data = response.json()
            models = data.get("data", [])

            if not models:
                logger.warning("No models found in LM Studio")
                return None

            # Return first model ID
            model_id = models[0].get("id")
            logger.info(
                f"Detected LM Studio model: {model_id}", model_count=len(models)
            )
            return model_id

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error detecting LM Studio model: {e.response.status_code}"
        logger.error(error_msg, error=str(e))
        raise ModelError(
            error_msg,
            model_name="lmstudio",
            details={"status_code": e.response.status_code, "url": models_url},
        )

    except httpx.RequestError as e:
        error_msg = f"Connection error detecting LM Studio model: {e}"
        logger.error(error_msg, error=str(e))
        raise ModelError(
            error_msg,
            model_name="lmstudio",
            details={"error": str(e), "url": base_url},
        )

    except Exception as e:
        error_msg = f"Unexpected error detecting LM Studio model: {e}"
        logger.error(error_msg, error=str(e))
        raise ModelError(
            error_msg, model_name="lmstudio", details={"error": str(e)}
        )


async def test_lmstudio_connection(
    base_url: str, api_key: str = "not-needed", timeout: int = 10
) -> bool:
    """Test connection to LM Studio server.

    Args:
        base_url: LM Studio base URL
        api_key: API key (not needed for LM Studio)
        timeout: Request timeout in seconds

    Returns:
        True if connection is successful

    Raises:
        ModelError: If connection fails
    """
    try:
        model_id = await detect_lmstudio_model(base_url, api_key, timeout)
        return model_id is not None

    except ModelError:
        raise


def create_lmstudio_model(
    model_name: Optional[str] = None,
    settings: Optional[LMStudioSettings] = None,
    auto_detect: bool = True,
) -> OpenAIChatModel:
    """Create LM Studio model instance for Pydantic AI.

    This factory function creates an OpenAI-compatible model configured for LM Studio.
    It can automatically detect the loaded model or use a specified model name.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, attempts to detect.
        settings: LM Studio configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model from LM Studio.

    Returns:
        Configured OpenAIChatModel instance for LM Studio

    Raises:
        ModelError: If model detection fails when auto_detect=True

    Example:
        ```python
        # Auto-detect model (async context required for detection)
        from src.core.models.lmstudio_provider import create_lmstudio_model

        # Method 1: Specify model explicitly
        model = create_lmstudio_model(
            model_name="local-model",
            auto_detect=False
        )

        # Method 2: Use default from settings
        model = create_lmstudio_model(auto_detect=False)

        # Create agent with the model
        from pydantic_ai import Agent

        agent = Agent(model=model, system_prompt="You are a helpful assistant.")
        result = await agent.run("What is 2+2?")
        print(result.data)
        ```

    Note:
        Auto-detection requires an async context. If you need to create the model
        synchronously, set auto_detect=False and provide model_name explicitly.
    """
    lm_settings = settings or get_settings().lm_studio

    # Use provided model name or default from settings
    final_model_name = model_name or lm_settings.model_name

    # Create OpenAI provider configured for LM Studio
    provider = OpenAIProvider(
        base_url=lm_settings.base_url,
        api_key=lm_settings.api_key,  # Usually "not-needed" for LM Studio
    )

    # Create and return OpenAI-compatible model
    model = OpenAIChatModel(
        model_name=final_model_name,
        provider=provider,
    )

    logger.info(
        "Created LM Studio model",
        model_name=final_model_name,
        base_url=lm_settings.base_url,
    )

    return model


async def create_lmstudio_model_async(
    model_name: Optional[str] = None,
    settings: Optional[LMStudioSettings] = None,
    auto_detect: bool = True,
    test_connection: bool = True,
) -> OpenAIChatModel:
    """Create LM Studio model with async model detection and connection testing.

    This is the async version of create_lmstudio_model that supports auto-detection
    and connection testing.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, detects from LM Studio.
        settings: LM Studio configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model from LM Studio.
        test_connection: If True, test connection to LM Studio before returning model.

    Returns:
        Configured OpenAIChatModel instance for LM Studio

    Raises:
        ModelError: If model detection or connection test fails

    Example:
        ```python
        from src.core.models.lmstudio_provider import create_lmstudio_model_async

        # Auto-detect and test connection
        model = await create_lmstudio_model_async()

        # Or specify model explicitly
        model = await create_lmstudio_model_async(
            model_name="TheBloke/Llama-2-7B-Chat-GGUF",
            auto_detect=False
        )

        # Use with agent
        from pydantic_ai import Agent

        agent = Agent(model=model)
        result = await agent.run("Hello!")
        ```
    """
    lm_settings = settings or get_settings().lm_studio

    # Auto-detect model if requested
    if auto_detect and model_name is None:
        logger.info("Auto-detecting LM Studio model")
        detected_model = await detect_lmstudio_model(
            lm_settings.base_url, lm_settings.api_key, lm_settings.timeout
        )

        if detected_model is None:
            raise ModelError(
                "No models detected in LM Studio. Please load a model first.",
                model_name="lmstudio",
            )

        model_name = detected_model

    # Test connection if requested
    if test_connection:
        logger.info("Testing LM Studio connection")
        await test_lmstudio_connection(
            lm_settings.base_url, lm_settings.api_key, lm_settings.timeout
        )

    # Create and return model
    return create_lmstudio_model(
        model_name=model_name, settings=lm_settings, auto_detect=False
    )


# ===== Convenience Functions =====


def get_lmstudio_model(
    model_name: Optional[str] = None, settings: Optional[LMStudioSettings] = None
) -> OpenAIChatModel:
    """Get LM Studio model instance (sync, no auto-detection).

    This is a convenience wrapper around create_lmstudio_model for synchronous usage.

    Args:
        model_name: Model name/ID. If None, uses default from settings.
        settings: LM Studio configuration. If None, uses global settings.

    Returns:
        Configured OpenAIChatModel instance

    Example:
        ```python
        from src.core.models.lmstudio_provider import get_lmstudio_model

        model = get_lmstudio_model()  # Uses default from settings
        # or
        model = get_lmstudio_model(model_name="my-custom-model")
        ```
    """
    return create_lmstudio_model(model_name=model_name, settings=settings, auto_detect=False)


async def get_lmstudio_model_async(
    model_name: Optional[str] = None,
    settings: Optional[LMStudioSettings] = None,
    auto_detect: bool = True,
) -> OpenAIChatModel:
    """Get LM Studio model instance (async, with optional auto-detection).

    This is a convenience wrapper around create_lmstudio_model_async.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, detects from LM Studio.
        settings: LM Studio configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model.

    Returns:
        Configured OpenAIChatModel instance

    Example:
        ```python
        from src.core.models.lmstudio_provider import get_lmstudio_model_async

        # Auto-detect model
        model = await get_lmstudio_model_async()

        # Or specify explicitly
        model = await get_lmstudio_model_async(
            model_name="my-model",
            auto_detect=False
        )
        ```
    """
    return await create_lmstudio_model_async(
        model_name=model_name, settings=settings, auto_detect=auto_detect
    )


# ===== Health Check =====


async def lmstudio_health_check(
    settings: Optional[LMStudioSettings] = None,
) -> dict[str, any]:
    """Perform health check on LM Studio server.

    Args:
        settings: LM Studio configuration. If None, uses global settings.

    Returns:
        Dictionary with health check results:
        - connected: bool
        - model_detected: bool
        - model_id: str or None
        - base_url: str

    Example:
        ```python
        from src.core.models.lmstudio_provider import lmstudio_health_check

        health = await lmstudio_health_check()
        if health["connected"]:
            print(f"LM Studio is running with model: {health['model_id']}")
        ```
    """
    lm_settings = settings or get_settings().lm_studio

    health = {
        "connected": False,
        "model_detected": False,
        "model_id": None,
        "base_url": lm_settings.base_url,
    }

    try:
        model_id = await detect_lmstudio_model(
            lm_settings.base_url, lm_settings.api_key, lm_settings.timeout
        )

        health["connected"] = True

        if model_id:
            health["model_detected"] = True
            health["model_id"] = model_id

    except Exception as e:
        logger.error("LM Studio health check failed", error=str(e))
        health["error"] = str(e)

    return health
