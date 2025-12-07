# Task: Implement Ollama Provider

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Create Ollama provider module with model detection, health checks, and client utilities
**Sequence**: 3 of 10
**Depends On**: 02-configuration-extension.md

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

The previous tasks created the provider abstraction layer and configuration settings. Now we implement the Ollama provider.

Ollama has two API interfaces:
1. **Native API** (port 11434): `/api/tags`, `/api/pull`, `/api/show`, `/api/chat`
2. **OpenAI-compatible API** (port 11434/v1): `/v1/models`, `/v1/chat/completions`

We use the OpenAI-compatible API for model inference (via Pydantic AI) and the native API for model management (listing, pulling, deleting).

The existing `lmstudio_provider.py` serves as the template for structure and conventions.

---

## Requirements

### 1. Create Ollama Provider Module

Create `src/core/models/ollama_provider.py`:

```python
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
```

### 2. Create Ollama Client Module

Create `src/infrastructure/llm/ollama_client.py` for model management:

```python
"""Ollama API client for model management.

Supports both native Ollama API and OpenAI-compatible endpoints.
"""

from typing import Any, AsyncIterator, Optional

import httpx

from src.core.utils.config import OllamaSettings, get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class OllamaClient:
    """Client for Ollama model management APIs.

    Uses native Ollama API endpoints for model management operations.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama server URL (without /v1). If None, uses settings.
            timeout: Request timeout in seconds
        """
        settings = get_settings().ollama
        # Strip /v1 if present to get native API base
        url = base_url or settings.base_url
        self.base_url = url.replace("/v1", "").rstrip("/")
        self.timeout = timeout

    async def list_models(self) -> list[dict[str, Any]]:
        """List all available models.

        Returns:
            List of model info dictionaries with keys: name, size, digest, modified_at
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])

    async def pull_model(
        self, model_name: str, stream: bool = True
    ) -> AsyncIterator[dict[str, Any]]:
        """Pull a model from Ollama registry.

        Args:
            model_name: Name of model to pull (e.g., "llama3.2", "codellama:7b")
            stream: If True, yields progress updates

        Yields:
            Progress dictionaries with status, completed, total
        """
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": stream},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        yield json.loads(line)

    async def get_model_info(self, model_name: str) -> dict[str, Any]:
        """Get detailed model information.

        Args:
            model_name: Name of model to query

        Returns:
            Model info dict with modelfile, parameters, template, etc.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
            )
            response.raise_for_status()
            return response.json()

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama.

        Args:
            model_name: Name of model to delete

        Returns:
            True if deleted successfully
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
            )
            return response.status_code == 200

    async def is_running(self) -> bool:
        """Check if Ollama server is running.

        Returns:
            True if server responds
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
```

### 3. Update Models Package Exports

Update `src/core/models/__init__.py` to include Ollama exports:

```python
from src.core.models.ollama_provider import (
    create_ollama_model,
    create_ollama_model_async,
    detect_ollama_model,
    ollama_health_check,
)
```

---

## Files to Create

- `src/core/models/ollama_provider.py` - Provider functions for Ollama
- `src/infrastructure/llm/ollama_client.py` - Ollama model management client

## Files to Modify

- `src/core/models/__init__.py` - Add Ollama provider exports

---

## Success Criteria

```bash
# Verify ollama_provider imports work
python -c "from src.core.models.ollama_provider import create_ollama_model, ollama_health_check; print('Imports OK')"
# Expected: Imports OK

# Verify OllamaClient imports work
python -c "from src.infrastructure.llm.ollama_client import OllamaClient; print('Client OK')"
# Expected: Client OK

# Verify create_ollama_model works (without running server)
python -c "from src.core.models.ollama_provider import create_ollama_model; m = create_ollama_model(model_name='test'); print(type(m).__name__)"
# Expected: OpenAIModel

# Verify health check returns proper structure (server not running)
python -c "
import asyncio
from src.core.models.ollama_provider import ollama_health_check
h = asyncio.run(ollama_health_check())
print(f'connected={h.connected}, provider={h.provider_type}')
"
# Expected: connected=False, provider=ollama

# Verify package exports
python -c "from src.core.models import create_ollama_model, ollama_health_check; print('Package exports OK')"
# Expected: Package exports OK
```

**Checklist:**
- [ ] `ollama_provider.py` created with all functions
- [ ] `ollama_client.py` created with OllamaClient class
- [ ] detect_ollama_model uses native /api/tags endpoint
- [ ] ollama_health_check returns ProviderHealthStatus
- [ ] create_ollama_model uses OpenAIProvider with correct base_url
- [ ] Package `__init__.py` exports Ollama functions

---

## Technical Notes

- **Native API vs OpenAI API**: Model listing uses `/api/tags` (native), inference uses `/v1/chat/completions` (OpenAI-compatible)
- **Base URL Conversion**: The config stores `/v1` URL, but native API calls need the base URL without `/v1`
- **Model Names**: Ollama uses format `name:tag` (e.g., `llama3.2:latest`, `codellama:7b`)
- **Pattern Reference**: Follow `lmstudio_provider.py` structure exactly
- **Error Handling**: Use ModelError from `src.core.utils.exceptions`

---

## Important

- Do NOT modify `lmstudio_provider.py` - it should remain unchanged
- Ensure all async functions are properly awaited
- The OllamaClient is separate from the provider to keep concerns separated
- Model pull can take a long time - use streaming with no timeout

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (04-llamacpp-provider.md) depends on this completing successfully
