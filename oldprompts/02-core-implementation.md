# Task: MLX-LM Provider - Core Implementation

**Project**: MLX-LM Provider
**Archon Project ID**: `503d952c-eedf-4252-ba71-1034a3430467`
**Sequence**: 2 of 5
**Depends On**: `01-foundation-setup.md` completed (MlxLmSettings and ProviderType.MLXLM exist)

---

## Archon Task Management

**Task ID**: `d82fa633-6121-4311-b3f7-0501bf6c1365`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/d82fa633-6121-4311-b3f7-0501bf6c1365" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/d82fa633-6121-4311-b3f7-0501bf6c1365" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the foundation in place (MlxLmSettings, ProviderType.MLXLM), we now create the core implementation:
1. `mlxlm_provider.py` - Provider module with health check, model detection, and creation
2. `mlxlm_client.py` - HTTP client for MLX-LM server interactions

These follow the exact patterns established by `llamacpp_provider.py` and `llamacpp_client.py`.

---

## Requirements

### 1. Create MLX-LM Provider Module

**File**: `src/core/models/mlxlm_provider.py` (NEW)

```python
"""MLX-LM server model provider for Pydantic AI.

This module provides integration with MLX-LM's OpenAI-compatible server:
- Factory function for creating MLX-LM model instances
- Server health checks via /health endpoint
- Model detection from /v1/models endpoint
- Optimized for Apple Silicon with Metal GPU acceleration
"""

from typing import Optional

import httpx
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.config import MlxLmSettings, get_settings
from src.core.utils.exceptions import ModelError
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


async def detect_mlxlm_model(
    base_url: str, timeout: int = 10
) -> Optional[str]:
    """Detect the loaded model in MLX-LM server.

    Args:
        base_url: MLX-LM server base URL (e.g., http://localhost:8080/v1)
        timeout: Request timeout in seconds

    Returns:
        Model ID if available, or None

    Note:
        MLX-LM server loads models on demand or at startup.
        The /v1/models endpoint returns info about the loaded model.
    """
    models_url = base_url.rstrip("/") + "/models"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Detecting MLX-LM model", url=models_url)
            response = await client.get(models_url)
            response.raise_for_status()

            data = response.json()
            models = data.get("data", [])

            if not models:
                logger.warning("No model info from MLX-LM server")
                return None

            model_id = models[0].get("id")
            logger.info(f"Detected MLX-LM model: {model_id}")
            return model_id

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error detecting MLX-LM model: {e.response.status_code}")
        raise ModelError(
            f"HTTP error detecting MLX-LM model: {e.response.status_code}",
            model_name="mlxlm",
            details={"status_code": e.response.status_code, "url": models_url},
        )
    except httpx.RequestError as e:
        logger.error(f"Connection error detecting MLX-LM model: {e}")
        raise ModelError(
            f"Connection error to MLX-LM server: {e}",
            model_name="mlxlm",
            details={"error": str(e), "url": base_url},
        )
    except Exception as e:
        logger.error(f"Unexpected error detecting MLX-LM model: {e}")
        raise ModelError(
            f"Unexpected error detecting MLX-LM model: {e}",
            model_name="mlxlm",
            details={"error": str(e)},
        )


async def mlxlm_health_check(
    settings: Optional[MlxLmSettings] = None,
) -> ProviderHealthStatus:
    """Perform health check on MLX-LM server.

    Args:
        settings: MLX-LM configuration. If None, uses global settings.

    Returns:
        ProviderHealthStatus with connection and model information
    """
    mlxlm_settings = settings or get_settings().mlxlm

    # Get base URL without /v1 for health endpoint
    base_url = mlxlm_settings.base_url.replace("/v1", "").rstrip("/")

    health = ProviderHealthStatus(
        connected=False,
        model_detected=False,
        model_id=None,
        base_url=mlxlm_settings.base_url,
        provider_type="mlxlm",
    )

    try:
        # First check /health endpoint
        async with httpx.AsyncClient(timeout=mlxlm_settings.timeout) as client:
            health_url = f"{base_url}/health"
            response = await client.get(health_url)

            if response.status_code == 200:
                health.connected = True
                # MLX-LM /health returns simple OK or JSON status
                try:
                    health_data = response.json()
                    health.metadata["status"] = health_data.get("status", "ok")
                except Exception:
                    # Plain text response is also valid
                    health.metadata["status"] = "ok"

        # Then try to detect model
        if health.connected:
            model_id = await detect_mlxlm_model(
                mlxlm_settings.base_url, mlxlm_settings.timeout
            )
            if model_id:
                health.model_detected = True
                health.model_id = model_id

    except Exception as e:
        logger.error("MLX-LM health check failed", error=str(e))
        health.error = str(e)

    return health


def create_mlxlm_model(
    model_name: Optional[str] = None,
    settings: Optional[MlxLmSettings] = None,
) -> OpenAIModel:
    """Create MLX-LM model instance for Pydantic AI.

    Args:
        model_name: Model name/ID (for logging). If None, uses default from settings.
        settings: MLX-LM configuration. If None, uses global settings.

    Returns:
        Configured OpenAIModel instance for MLX-LM

    Note:
        The model_name is mainly for logging/identification purposes since
        MLX-LM server manages its own model loading.
    """
    mlxlm_settings = settings or get_settings().mlxlm

    final_model_name = model_name or mlxlm_settings.model_name

    provider = OpenAIProvider(
        base_url=mlxlm_settings.base_url,
        api_key=mlxlm_settings.api_key,
    )

    model = OpenAIModel(
        final_model_name,
        provider=provider,
    )

    logger.info(
        "Created MLX-LM model",
        model_name=final_model_name,
        base_url=mlxlm_settings.base_url,
    )

    return model


async def create_mlxlm_model_async(
    model_name: Optional[str] = None,
    settings: Optional[MlxLmSettings] = None,
    auto_detect: bool = True,
    test_connection: bool = True,
) -> OpenAIModel:
    """Create MLX-LM model with async detection and connection testing.

    Args:
        model_name: Model name/ID. If None and auto_detect=True, detects from server.
        settings: MLX-LM configuration. If None, uses global settings.
        auto_detect: If True and model_name is None, auto-detect model.
        test_connection: If True, test connection before returning.

    Returns:
        Configured OpenAIModel instance for MLX-LM
    """
    mlxlm_settings = settings or get_settings().mlxlm

    if auto_detect and model_name is None:
        logger.info("Auto-detecting MLX-LM model")
        detected_model = await detect_mlxlm_model(
            mlxlm_settings.base_url, mlxlm_settings.timeout
        )

        if detected_model:
            model_name = detected_model

    if test_connection:
        logger.info("Testing MLX-LM connection")
        health = await mlxlm_health_check(mlxlm_settings)
        if not health.connected:
            raise ModelError(
                f"Cannot connect to MLX-LM server: {health.error}",
                model_name="mlxlm",
            )

    return create_mlxlm_model(
        model_name=model_name, settings=mlxlm_settings
    )
```

### 2. Create MLX-LM Client Module

**File**: `src/infrastructure/llm/mlxlm_client.py` (NEW)

```python
"""MLX-LM server client for model management.

Provides a client interface for interacting with MLX-LM server
for model listing and health checking operations.
"""

from typing import Optional

import httpx

from src.core.utils.config import MlxLmSettings, get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class MlxLmClient:
    """Client for MLX-LM server interactions.

    Provides methods for:
    - Listing available/loaded models
    - Checking server health
    - Verifying model availability
    """

    def __init__(self, settings: Optional[MlxLmSettings] = None):
        """Initialize MLX-LM client.

        Args:
            settings: MLX-LM configuration. If None, uses global settings.
        """
        self.settings = settings or get_settings().mlxlm
        self.base_url = self.settings.base_url.rstrip("/")
        # Remove /v1 for non-OpenAI endpoints
        self._server_url = self.base_url.replace("/v1", "").rstrip("/")

    async def list_models(self) -> list[dict]:
        """List models from MLX-LM server.

        Returns:
            List of model dictionaries with 'id' and metadata
        """
        url = f"{self.base_url}/models"

        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                return data.get("data", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing MLX-LM models: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing MLX-LM models: {e}")
            return []

    async def is_running(self) -> bool:
        """Check if MLX-LM server is running.

        Returns:
            True if server responds to health check
        """
        url = f"{self._server_url}/health"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False

    async def is_model_loaded(self) -> bool:
        """Check if a model is loaded in MLX-LM server.

        Returns:
            True if at least one model is available
        """
        models = await self.list_models()
        return len(models) > 0

    async def get_model_info(self) -> Optional[dict]:
        """Get information about the loaded model.

        Returns:
            Model info dictionary or None if no model loaded
        """
        models = await self.list_models()
        if models:
            return models[0]
        return None
```

---

## Files to Create

| File | Description |
|------|-------------|
| `src/core/models/mlxlm_provider.py` | Provider with health check, model detection, model creation |
| `src/infrastructure/llm/mlxlm_client.py` | HTTP client for server interactions |

---

## Success Criteria

```bash
# 1. Provider module imports work
cd /Users/maxwell/Projects/MAI
python3 -c "from src.core.models.mlxlm_provider import detect_mlxlm_model, mlxlm_health_check, create_mlxlm_model, create_mlxlm_model_async; print('Provider imports OK')"
# Expected: Provider imports OK

# 2. Client module imports work
python3 -c "from src.infrastructure.llm.mlxlm_client import MlxLmClient; print('Client imports OK')"
# Expected: Client imports OK

# 3. Can create model instance (doesn't require running server)
python3 -c "from src.core.models.mlxlm_provider import create_mlxlm_model; m = create_mlxlm_model('test-model'); print(f'Model created: {type(m).__name__}')"
# Expected: Model created: OpenAIModel

# 4. Health check returns proper structure (server not required)
python3 -c "
import asyncio
from src.core.models.mlxlm_provider import mlxlm_health_check
async def test():
    health = await mlxlm_health_check()
    print(f'provider_type: {health.provider_type}')
    print(f'connected: {health.connected}')
asyncio.run(test())
"
# Expected:
# provider_type: mlxlm
# connected: False (or True if server is running)

# 5. Client can be instantiated
python3 -c "from src.infrastructure.llm.mlxlm_client import MlxLmClient; c = MlxLmClient(); print(f'base_url: {c.base_url}')"
# Expected: base_url: http://localhost:8080/v1
```

---

## Technical Notes

### MLX-LM Server API Reference

**Endpoints** (confirmed from source):
- `GET /health` - Health check (returns 200 OK)
- `GET /v1/models` - List loaded models (OpenAI format)
- `POST /v1/chat/completions` - Chat completion (OpenAI format)
- `POST /v1/completions` - Text completion (OpenAI format)

**Model detection response format**:
```json
{
  "data": [
    {
      "id": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
      "object": "model"
    }
  ]
}
```

### Pattern Reference

This implementation mirrors `llamacpp_provider.py` exactly:
- Same function signatures
- Same error handling patterns
- Same ProviderHealthStatus structure
- Same logging patterns

---

## On Completion

Mark task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/d82fa633-6121-4311-b3f7-0501bf6c1365" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Next Step**: Proceed to `03-provider-factory.md` to wire the provider into the factory.
