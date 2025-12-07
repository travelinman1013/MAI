# Task: Implement llama.cpp Provider

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Create llama.cpp provider module with health checks and client utilities
**Sequence**: 4 of 10
**Depends On**: 03-ollama-provider.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `[TO_BE_ASSIGNED]`
- **Project ID**: `[TO_BE_ASSIGNED]`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous task implemented the Ollama provider. Now we implement the llama.cpp provider.

llama.cpp server (`llama-server` or `llama-cpp-python`) provides:
1. **OpenAI-compatible API**: `/v1/models`, `/v1/chat/completions`
2. **Server-specific endpoints**: `/health`, `/props`, `/slots`

Unlike Ollama, llama.cpp loads a single model at server startup. The model cannot be changed at runtime - you must restart the server with a different model file.

---

## Requirements

### 1. Create llama.cpp Provider Module

Create `src/core/models/llamacpp_provider.py`:

```python
"""llama.cpp server model provider for Pydantic AI.

This module provides integration with llama.cpp's OpenAI-compatible server:
- Factory function for creating llama.cpp model instances
- Server health checks via /health endpoint
- Model detection from /v1/models endpoint
- Support for both llama-server and llama-cpp-python
"""

from typing import Optional, Any

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
```

### 2. Create llama.cpp Client Module

Create `src/infrastructure/llm/llamacpp_client.py`:

```python
"""llama.cpp server client for server management and monitoring.

Provides access to llama.cpp server-specific endpoints for health,
slots, and property information.
"""

from typing import Any, Optional

import httpx

from src.core.utils.config import LlamaCppSettings, get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class LlamaCppClient:
    """Client for llama.cpp server management APIs.

    Accesses server-specific endpoints that are not part of OpenAI API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize llama.cpp client.

        Args:
            base_url: Server URL (without /v1). If None, uses settings.
            timeout: Request timeout in seconds
        """
        settings = get_settings().llamacpp
        url = base_url or settings.base_url
        # Strip /v1 if present
        self.base_url = url.replace("/v1", "").rstrip("/")
        self.timeout = timeout

    async def health_check(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health status dict with 'status' key ('ok' or 'loading model' etc.)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def get_slots(self) -> list[dict[str, Any]]:
        """Get slot information.

        Returns:
            List of slot info dicts with id, state, prompt, etc.

        Note:
            Slots represent concurrent request handling capacity.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/slots")
            response.raise_for_status()
            return response.json()

    async def get_props(self) -> dict[str, Any]:
        """Get server properties.

        Returns:
            Server properties dict with model info, settings, etc.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/props")
            response.raise_for_status()
            return response.json()

    async def list_models(self) -> list[dict[str, Any]]:
        """List loaded model via OpenAI-compatible endpoint.

        Returns:
            List with single model info dict
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def is_running(self) -> bool:
        """Check if llama.cpp server is running.

        Returns:
            True if server responds to health check
        """
        try:
            health = await self.health_check()
            return health.get("status") == "ok"
        except Exception:
            return False

    async def is_model_loaded(self) -> bool:
        """Check if model is fully loaded and ready.

        Returns:
            True if model is loaded and ready for inference
        """
        try:
            health = await self.health_check()
            status = health.get("status", "")
            return status == "ok"
        except Exception:
            return False
```

### 3. Update Models Package Exports

Update `src/core/models/__init__.py` to include llama.cpp exports:

```python
from src.core.models.llamacpp_provider import (
    create_llamacpp_model,
    create_llamacpp_model_async,
    detect_llamacpp_model,
    llamacpp_health_check,
)
```

---

## Files to Create

- `src/core/models/llamacpp_provider.py` - Provider functions for llama.cpp
- `src/infrastructure/llm/llamacpp_client.py` - llama.cpp server management client

## Files to Modify

- `src/core/models/__init__.py` - Add llama.cpp provider exports

---

## Success Criteria

```bash
# Verify llamacpp_provider imports work
python -c "from src.core.models.llamacpp_provider import create_llamacpp_model, llamacpp_health_check; print('Imports OK')"
# Expected: Imports OK

# Verify LlamaCppClient imports work
python -c "from src.infrastructure.llm.llamacpp_client import LlamaCppClient; print('Client OK')"
# Expected: Client OK

# Verify create_llamacpp_model works (without running server)
python -c "from src.core.models.llamacpp_provider import create_llamacpp_model; m = create_llamacpp_model(model_name='test'); print(type(m).__name__)"
# Expected: OpenAIModel

# Verify health check returns proper structure (server not running)
python -c "
import asyncio
from src.core.models.llamacpp_provider import llamacpp_health_check
h = asyncio.run(llamacpp_health_check())
print(f'connected={h.connected}, provider={h.provider_type}')
"
# Expected: connected=False, provider=llamacpp

# Verify package exports
python -c "from src.core.models import create_llamacpp_model, llamacpp_health_check; print('Package exports OK')"
# Expected: Package exports OK
```

**Checklist:**
- [ ] `llamacpp_provider.py` created with all functions
- [ ] `llamacpp_client.py` created with LlamaCppClient class
- [ ] detect_llamacpp_model uses /v1/models endpoint
- [ ] llamacpp_health_check uses /health endpoint first
- [ ] Health check stores server status in metadata
- [ ] Package `__init__.py` exports llama.cpp functions

---

## Technical Notes

- **Single Model**: llama.cpp loads one model at startup - no runtime model switching
- **Health Endpoint**: `/health` returns `{"status": "ok"}` when ready, or loading status
- **Slots Endpoint**: `/slots` shows concurrent request capacity
- **Props Endpoint**: `/props` shows server configuration and loaded model info
- **Pattern Reference**: Follow the structure from `ollama_provider.py` and `lmstudio_provider.py`

---

## Important

- Do NOT modify other provider files
- The model_name parameter is mainly for identification/logging
- Health check should check `/health` before trying `/v1/models`
- Handle the case where server is loading model (not yet ready)

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (05-provider-factory.md) depends on this completing successfully
