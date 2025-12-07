# Task: MLX-LM Provider - Unit Tests

**Project**: MLX-LM Provider
**Archon Project ID**: `503d952c-eedf-4252-ba71-1034a3430467`
**Sequence**: 5 of 5 (Final)
**Depends On**: `04-api-config.md` completed (all implementation complete)

---

## Archon Task Management

**Task ID**: `52ddd23f-ed9c-4db9-8b51-671220a145ab`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/52ddd23f-ed9c-4db9-8b51-671220a145ab" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/52ddd23f-ed9c-4db9-8b51-671220a145ab" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

All implementation is complete. Now we create comprehensive unit tests following the exact patterns established by `test_llamacpp_provider.py`.

Tests cover:
- Model detection (`detect_mlxlm_model`)
- Health checks (`mlxlm_health_check`)
- Model creation (sync and async)
- Error handling

---

## Requirements

### Create Unit Test File

**File**: `tests/unit/core/models/test_mlxlm_provider.py` (NEW)

```python
"""Tests for MLX-LM provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.core.models.mlxlm_provider import (
    detect_mlxlm_model,
    mlxlm_health_check,
    create_mlxlm_model,
    create_mlxlm_model_async,
)
from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.exceptions import ModelError


class TestDetectMlxLmModel:
    """Tests for detect_mlxlm_model function."""

    @pytest.mark.asyncio
    async def test_detect_model_success(self):
        """Should detect model from MLX-LM API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "mlx-community/Qwen2.5-1.5B-Instruct-4bit", "object": "model"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await detect_mlxlm_model("http://localhost:8080/v1")

        assert result == "mlx-community/Qwen2.5-1.5B-Instruct-4bit"

    @pytest.mark.asyncio
    async def test_detect_model_no_models(self):
        """Should return None when no model data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await detect_mlxlm_model("http://localhost:8080/v1")

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_model_connection_error(self):
        """Should raise ModelError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(ModelError):
                await detect_mlxlm_model("http://localhost:8080/v1")

    @pytest.mark.asyncio
    async def test_detect_model_http_error(self):
        """Should raise ModelError on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(ModelError) as exc_info:
                await detect_mlxlm_model("http://localhost:8080/v1")

            assert "HTTP error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_detect_model_url_construction(self):
        """Should properly construct the models URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "test-model"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_instance.get = mock_get
            mock_client.return_value.__aenter__.return_value = mock_instance

            await detect_mlxlm_model("http://localhost:8080/v1")

            call_url = mock_get.call_args[0][0]
            assert call_url == "http://localhost:8080/v1/models"


class TestMlxLmHealthCheck:
    """Tests for mlxlm_health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Should return connected status when server responds."""
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"status": "ok"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_health_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            with patch(
                "src.core.models.mlxlm_provider.detect_mlxlm_model",
                new_callable=AsyncMock,
                return_value="test-model",
            ):
                result = await mlxlm_health_check()

        assert isinstance(result, ProviderHealthStatus)
        assert result.connected is True
        assert result.provider_type == "mlxlm"
        assert result.model_detected is True
        assert result.model_id == "test-model"

    @pytest.mark.asyncio
    async def test_health_check_stores_status_in_metadata(self):
        """Should store server status in metadata."""
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"status": "loading model"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_health_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            with patch(
                "src.core.models.mlxlm_provider.detect_mlxlm_model",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await mlxlm_health_check()

        assert result.metadata.get("status") == "loading model"

    @pytest.mark.asyncio
    async def test_health_check_plain_text_response(self):
        """Should handle plain text health response (not JSON)."""
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.side_effect = Exception("Not JSON")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_health_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            with patch(
                "src.core.models.mlxlm_provider.detect_mlxlm_model",
                new_callable=AsyncMock,
                return_value="test-model",
            ):
                result = await mlxlm_health_check()

        assert result.connected is True
        assert result.metadata.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Should return disconnected status on error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await mlxlm_health_check()

        assert result.connected is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_health_check_uses_settings(self):
        """Should use provided settings."""
        from src.core.utils.config import MlxLmSettings

        custom_settings = MlxLmSettings(
            base_url="http://custom:9999/v1",
            model_name="custom-model",
            api_key="not-needed",
        )

        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"status": "ok"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_health_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            with patch(
                "src.core.models.mlxlm_provider.detect_mlxlm_model",
                new_callable=AsyncMock,
                return_value="custom-model",
            ):
                result = await mlxlm_health_check(settings=custom_settings)

        assert result.base_url == "http://custom:9999/v1"


class TestCreateMlxLmModel:
    """Tests for create_mlxlm_model function."""

    def test_create_model_with_name(self):
        """Should create model with specified name."""
        model = create_mlxlm_model(model_name="test-model")
        assert model is not None

    def test_create_model_uses_settings(self):
        """Should use settings when no name provided."""
        with patch("src.core.models.mlxlm_provider.get_settings") as mock_settings:
            mock_settings.return_value.mlxlm.model_name = "default-model"
            mock_settings.return_value.mlxlm.base_url = "http://localhost:8080/v1"
            mock_settings.return_value.mlxlm.api_key = "not-needed"

            model = create_mlxlm_model()
            assert model is not None

    def test_create_model_with_custom_settings(self):
        """Should use provided settings."""
        from src.core.utils.config import MlxLmSettings

        custom_settings = MlxLmSettings(
            base_url="http://custom:9999/v1",
            model_name="custom-model",
            api_key="not-needed",
        )

        model = create_mlxlm_model(settings=custom_settings)
        assert model is not None


class TestCreateMlxLmModelAsync:
    """Tests for create_mlxlm_model_async function."""

    @pytest.mark.asyncio
    async def test_create_model_with_auto_detect(self):
        """Should auto-detect model when enabled."""
        with patch(
            "src.core.models.mlxlm_provider.detect_mlxlm_model",
            new_callable=AsyncMock,
            return_value="detected-model",
        ), patch(
            "src.core.models.mlxlm_provider.mlxlm_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=True,
                model_id="detected-model",
                base_url="http://localhost:8080/v1",
                provider_type="mlxlm",
            ),
        ):
            model = await create_mlxlm_model_async(
                auto_detect=True, test_connection=True
            )
            assert model is not None

    @pytest.mark.asyncio
    async def test_create_model_with_explicit_name(self):
        """Should use explicit model name when provided."""
        with patch(
            "src.core.models.mlxlm_provider.mlxlm_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=True,
                model_id="explicit-model",
                base_url="http://localhost:8080/v1",
                provider_type="mlxlm",
            ),
        ):
            model = await create_mlxlm_model_async(
                model_name="explicit-model",
                auto_detect=False,
                test_connection=True,
            )
            assert model is not None

    @pytest.mark.asyncio
    async def test_create_model_connection_error(self):
        """Should raise ModelError when connection fails and test_connection=True."""
        with patch(
            "src.core.models.mlxlm_provider.mlxlm_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=False,
                model_detected=False,
                model_id=None,
                base_url="http://localhost:8080/v1",
                error="Connection refused",
                provider_type="mlxlm",
            ),
        ):
            with pytest.raises(ModelError) as exc_info:
                await create_mlxlm_model_async(
                    model_name="test-model",
                    auto_detect=False,
                    test_connection=True,
                )

            assert "Cannot connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_model_no_test_connection(self):
        """Should skip connection test when test_connection=False."""
        model = await create_mlxlm_model_async(
            model_name="test-model",
            auto_detect=False,
            test_connection=False,
        )
        assert model is not None

    @pytest.mark.asyncio
    async def test_create_model_auto_detect_fallback(self):
        """Should fall back to settings model_name when auto-detect returns None."""
        with patch(
            "src.core.models.mlxlm_provider.detect_mlxlm_model",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.core.models.mlxlm_provider.mlxlm_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=False,
                model_id=None,
                base_url="http://localhost:8080/v1",
                provider_type="mlxlm",
            ),
        ):
            model = await create_mlxlm_model_async(
                auto_detect=True, test_connection=True
            )
            assert model is not None
```

---

## Files to Create

| File | Description |
|------|-------------|
| `tests/unit/core/models/test_mlxlm_provider.py` | Comprehensive unit tests for MLX-LM provider |

---

## Success Criteria

```bash
# 1. Test file can be imported
cd /Users/maxwell/Projects/MAI
python3 -c "from tests.unit.core.models.test_mlxlm_provider import TestDetectMlxLmModel, TestMlxLmHealthCheck, TestCreateMlxLmModel, TestCreateMlxLmModelAsync; print('Test imports OK')"
# Expected: Test imports OK

# 2. Run the new tests
python3 -m pytest tests/unit/core/models/test_mlxlm_provider.py -v
# Expected: All tests pass

# 3. Run tests with coverage
python3 -m pytest tests/unit/core/models/test_mlxlm_provider.py -v --cov=src.core.models.mlxlm_provider --cov-report=term-missing
# Expected: Good coverage of mlxlm_provider.py

# 4. Verify no regressions in other provider tests
python3 -m pytest tests/unit/core/models/ -v
# Expected: All provider tests pass

# 5. Full test suite passes
python3 -m pytest tests/unit/ -v --ignore=tests/unit/infrastructure
# Expected: All unit tests pass
```

---

## Technical Notes

### Test Pattern Reference

These tests mirror `test_llamacpp_provider.py` exactly:
- Same class structure (TestDetect*, TestHealthCheck, TestCreate*, TestCreate*Async)
- Same mocking patterns for httpx.AsyncClient
- Same assertions for ProviderHealthStatus fields
- Same error handling tests

### Key Test Scenarios

1. **Model Detection**: Success, empty response, connection error, HTTP error, URL construction
2. **Health Check**: Connected with model, status in metadata, plain text response, disconnected, custom settings
3. **Sync Model Creation**: With name, using settings, custom settings
4. **Async Model Creation**: Auto-detect, explicit name, connection error, skip test, auto-detect fallback

### Additional Test for Plain Text Health Response

MLX-LM server might return plain "OK" text instead of JSON for `/health`. The test `test_health_check_plain_text_response` covers this edge case.

---

## On Completion

Mark task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/52ddd23f-ed9c-4db9-8b51-671220a145ab" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Create completion document in Archon**:
```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MLX-LM Provider - Implementation Complete",
    "content": "# MLX-LM Provider Implementation Complete\n\n## Summary\nMLX-LM has been added as a new LLM provider for Apple Silicon Macs.\n\n## Files Created\n- src/core/models/mlxlm_provider.py\n- src/infrastructure/llm/mlxlm_client.py\n- tests/unit/core/models/test_mlxlm_provider.py\n\n## Files Modified\n- src/core/utils/config.py\n- src/core/models/base_provider.py\n- src/core/models/providers.py\n- src/api/routes/models.py\n- .env.example\n\n## Usage\n```bash\n# Install MLX-LM\npip install mlx-lm\n\n# Run server\nmlx_lm.server --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --port 8080\n\n# Configure\nexport LLM__PROVIDER=mlxlm\nexport MLXLM__BASE_URL=http://localhost:8080/v1\n```\n\n## Tests\nAll unit tests pass: pytest tests/unit/core/models/test_mlxlm_provider.py",
    "project_id": "503d952c-eedf-4252-ba71-1034a3430467"
  }'
```

---

## Implementation Complete!

With all 5 prompts executed, the MLX-LM provider is fully implemented:

| Step | Status | Description |
|------|--------|-------------|
| 01 | Done | Foundation - MlxLmSettings and ProviderType.MLXLM |
| 02 | Done | Core - mlxlm_provider.py and mlxlm_client.py |
| 03 | Done | Factory - Wired into providers.py |
| 04 | Done | API - Routes and .env.example |
| 05 | Done | Tests - Full unit test coverage |

**To verify full implementation**:
```bash
cd /Users/maxwell/Projects/MAI

# 1. Run all tests
python3 -m pytest tests/unit/core/models/ -v

# 2. Check provider works end-to-end (with server running)
mlx_lm.server --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --port 8080 &
LLM__PROVIDER=mlxlm python3 -c "
import asyncio
from src.core.models.providers import get_model_provider_async
async def test():
    model = await get_model_provider_async(test_connection=True)
    print(f'MLX-LM model ready: {type(model).__name__}')
asyncio.run(test())
"
```
