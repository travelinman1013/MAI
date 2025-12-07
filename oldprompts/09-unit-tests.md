# Task: Create Unit Tests for New Providers

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Create comprehensive unit tests for Ollama and llama.cpp providers
**Sequence**: 9 of 10
**Depends On**: 08-frontend-integration.md

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

All provider implementations and integrations are complete. Now we need to create unit tests to ensure the code works correctly and catches regressions.

The project uses pytest for testing. Tests should mock external HTTP calls to avoid requiring actual servers.

---

## Requirements

### 1. Create Base Provider Tests

Create `tests/unit/core/models/test_base_provider.py`:

```python
"""Tests for base provider abstraction layer."""

import pytest
from src.core.models.base_provider import (
    ProviderType,
    ProviderHealthStatus,
    LLMProviderProtocol,
)


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_all_providers_defined(self):
        """All expected providers should be defined."""
        expected = {"openai", "lmstudio", "ollama", "llamacpp", "auto"}
        actual = {p.value for p in ProviderType}
        assert actual == expected

    def test_provider_values_are_lowercase(self):
        """Provider values should be lowercase strings."""
        for provider in ProviderType:
            assert provider.value == provider.value.lower()
            assert isinstance(provider.value, str)

    def test_provider_is_string_enum(self):
        """ProviderType should be a string enum."""
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.OLLAMA == "ollama"


class TestProviderHealthStatus:
    """Tests for ProviderHealthStatus dataclass."""

    def test_required_fields(self):
        """Required fields should be enforced."""
        status = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="test-model",
            base_url="http://localhost:8000",
        )
        assert status.connected is True
        assert status.model_detected is True
        assert status.model_id == "test-model"
        assert status.base_url == "http://localhost:8000"

    def test_optional_fields_have_defaults(self):
        """Optional fields should have sensible defaults."""
        status = ProviderHealthStatus(
            connected=False,
            model_detected=False,
            model_id=None,
            base_url="http://localhost",
        )
        assert status.error is None
        assert status.provider_type is None
        assert status.metadata == {}

    def test_metadata_is_mutable(self):
        """Metadata dict should be mutable."""
        status = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="test",
            base_url="http://localhost",
        )
        status.metadata["key"] = "value"
        assert status.metadata["key"] == "value"

    def test_error_field(self):
        """Error field should store error messages."""
        status = ProviderHealthStatus(
            connected=False,
            model_detected=False,
            model_id=None,
            base_url="http://localhost",
            error="Connection refused",
        )
        assert status.error == "Connection refused"
```

### 2. Create Ollama Provider Tests

Create `tests/unit/core/models/test_ollama_provider.py`:

```python
"""Tests for Ollama provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.core.models.ollama_provider import (
    detect_ollama_model,
    ollama_health_check,
    create_ollama_model,
    create_ollama_model_async,
)
from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.exceptions import ModelError


class TestDetectOllamaModel:
    """Tests for detect_ollama_model function."""

    @pytest.mark.asyncio
    async def test_detect_model_success(self):
        """Should detect model from Ollama API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest", "size": 1000000},
                {"name": "codellama:7b", "size": 2000000},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await detect_ollama_model("http://localhost:11434/v1")

        assert result == "llama3.2:latest"

    @pytest.mark.asyncio
    async def test_detect_model_no_models(self):
        """Should return None when no models available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await detect_ollama_model("http://localhost:11434/v1")

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_model_connection_error(self):
        """Should raise ModelError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )

            with pytest.raises(ModelError) as exc_info:
                await detect_ollama_model("http://localhost:11434/v1")

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_detect_model_strips_v1(self):
        """Should convert /v1 URL to native API URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "test"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await detect_ollama_model("http://localhost:11434/v1")

            # Should call /api/tags, not /v1/api/tags
            call_url = mock_get.call_args[0][0]
            assert "/api/tags" in call_url
            assert "/v1/api/tags" not in call_url


class TestOllamaHealthCheck:
    """Tests for ollama_health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Should return connected status when server responds."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value="llama3.2",
        ):
            result = await ollama_health_check()

        assert isinstance(result, ProviderHealthStatus)
        assert result.connected is True
        assert result.model_detected is True
        assert result.model_id == "llama3.2"
        assert result.provider_type == "ollama"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Should return disconnected status on error."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await ollama_health_check()

        assert result.connected is False
        assert result.error is not None


class TestCreateOllamaModel:
    """Tests for create_ollama_model function."""

    def test_create_model_with_name(self):
        """Should create model with specified name."""
        model = create_ollama_model(model_name="test-model")
        assert model is not None

    def test_create_model_uses_settings(self):
        """Should use settings when no name provided."""
        with patch("src.core.models.ollama_provider.get_settings") as mock_settings:
            mock_settings.return_value.ollama.model_name = "default-model"
            mock_settings.return_value.ollama.base_url = "http://localhost:11434/v1"
            mock_settings.return_value.ollama.api_key = "ollama"

            model = create_ollama_model()
            assert model is not None


class TestCreateOllamaModelAsync:
    """Tests for create_ollama_model_async function."""

    @pytest.mark.asyncio
    async def test_create_model_with_auto_detect(self):
        """Should auto-detect model when enabled."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value="detected-model",
        ):
            model = await create_ollama_model_async(auto_detect=True)
            assert model is not None

    @pytest.mark.asyncio
    async def test_create_model_no_models_error(self):
        """Should raise error when no models available and auto_detect=True."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ModelError) as exc_info:
                await create_ollama_model_async(auto_detect=True)

            assert "No models detected" in str(exc_info.value)
```

### 3. Create llama.cpp Provider Tests

Create `tests/unit/core/models/test_llamacpp_provider.py`:

```python
"""Tests for llama.cpp provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.core.models.llamacpp_provider import (
    detect_llamacpp_model,
    llamacpp_health_check,
    create_llamacpp_model,
    create_llamacpp_model_async,
)
from src.core.models.base_provider import ProviderHealthStatus
from src.core.utils.exceptions import ModelError


class TestDetectLlamaCppModel:
    """Tests for detect_llamacpp_model function."""

    @pytest.mark.asyncio
    async def test_detect_model_success(self):
        """Should detect model from llama.cpp API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "local-model", "object": "model"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await detect_llamacpp_model("http://localhost:8080/v1")

        assert result == "local-model"

    @pytest.mark.asyncio
    async def test_detect_model_no_models(self):
        """Should return None when no model data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await detect_llamacpp_model("http://localhost:8080/v1")

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_model_connection_error(self):
        """Should raise ModelError on connection failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )

            with pytest.raises(ModelError):
                await detect_llamacpp_model("http://localhost:8080/v1")


class TestLlamaCppHealthCheck:
    """Tests for llamacpp_health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Should return connected status when server responds."""
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"status": "ok"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_health_response
            )
            with patch(
                "src.core.models.llamacpp_provider.detect_llamacpp_model",
                new_callable=AsyncMock,
                return_value="test-model",
            ):
                result = await llamacpp_health_check()

        assert isinstance(result, ProviderHealthStatus)
        assert result.connected is True
        assert result.provider_type == "llamacpp"

    @pytest.mark.asyncio
    async def test_health_check_stores_status_in_metadata(self):
        """Should store server status in metadata."""
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"status": "loading model"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_health_response
            )
            with patch(
                "src.core.models.llamacpp_provider.detect_llamacpp_model",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await llamacpp_health_check()

        assert result.metadata.get("status") == "loading model"


class TestCreateLlamaCppModel:
    """Tests for create_llamacpp_model function."""

    def test_create_model_with_name(self):
        """Should create model with specified name."""
        model = create_llamacpp_model(model_name="test-model")
        assert model is not None

    def test_create_model_uses_settings(self):
        """Should use settings when no name provided."""
        with patch("src.core.models.llamacpp_provider.get_settings") as mock_settings:
            mock_settings.return_value.llamacpp.model_name = "default-model"
            mock_settings.return_value.llamacpp.base_url = "http://localhost:8080/v1"
            mock_settings.return_value.llamacpp.api_key = "not-needed"

            model = create_llamacpp_model()
            assert model is not None
```

### 4. Create Provider Factory Tests

Create `tests/unit/core/models/test_providers.py`:

```python
"""Tests for provider factory."""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.models.providers import (
    get_model_provider,
    get_model_provider_async,
    check_all_providers,
)
from src.core.utils.exceptions import ConfigurationError


class TestGetModelProvider:
    """Tests for get_model_provider function."""

    def test_lmstudio_provider(self):
        """Should create LM Studio model."""
        model = get_model_provider("lmstudio")
        assert model is not None

    def test_ollama_provider(self):
        """Should create Ollama model."""
        model = get_model_provider("ollama")
        assert model is not None

    def test_llamacpp_provider(self):
        """Should create llama.cpp model."""
        model = get_model_provider("llamacpp")
        assert model is not None

    def test_invalid_provider_raises_error(self):
        """Should raise ConfigurationError for invalid provider."""
        with pytest.raises(ConfigurationError) as exc_info:
            get_model_provider("invalid")

        assert "Invalid LLM provider" in str(exc_info.value)


class TestGetModelProviderAsync:
    """Tests for get_model_provider_async function."""

    @pytest.mark.asyncio
    async def test_ollama_provider_async(self):
        """Should create Ollama model asynchronously."""
        with patch(
            "src.core.models.ollama_provider.create_ollama_model_async",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = "mock_model"
            model = await get_model_provider_async("ollama")
            assert model == "mock_model"


class TestCheckAllProviders:
    """Tests for check_all_providers function."""

    @pytest.mark.asyncio
    async def test_returns_all_providers(self):
        """Should return status for all providers."""
        with patch(
            "src.core.models.providers.lmstudio_health_check",
            new_callable=AsyncMock,
        ), patch(
            "src.core.models.providers.ollama_health_check",
            new_callable=AsyncMock,
        ), patch(
            "src.core.models.providers.llamacpp_health_check",
            new_callable=AsyncMock,
        ):
            results = await check_all_providers()

        assert "openai" in results
        assert "lmstudio" in results
        assert "ollama" in results
        assert "llamacpp" in results
```

---

## Files to Create

- `tests/unit/core/models/test_base_provider.py`
- `tests/unit/core/models/test_ollama_provider.py`
- `tests/unit/core/models/test_llamacpp_provider.py`
- `tests/unit/core/models/test_providers.py`

---

## Success Criteria

```bash
# Run all new tests
pytest tests/unit/core/models/test_base_provider.py -v
pytest tests/unit/core/models/test_ollama_provider.py -v
pytest tests/unit/core/models/test_llamacpp_provider.py -v
pytest tests/unit/core/models/test_providers.py -v

# All tests should pass
pytest tests/unit/core/models/ -v --tb=short
# Expected: All tests passed

# Check test coverage (optional)
pytest tests/unit/core/models/ --cov=src/core/models --cov-report=term-missing
```

**Checklist:**
- [ ] test_base_provider.py tests ProviderType and ProviderHealthStatus
- [ ] test_ollama_provider.py tests all Ollama functions
- [ ] test_llamacpp_provider.py tests all llama.cpp functions
- [ ] test_providers.py tests factory functions
- [ ] All tests use mocking for HTTP calls
- [ ] Async tests use pytest.mark.asyncio
- [ ] All tests pass

---

## Technical Notes

- **Mocking HTTP**: Use `unittest.mock.patch` with `httpx.AsyncClient`
- **Async Tests**: Mark with `@pytest.mark.asyncio`
- **Fixtures**: Consider creating fixtures for common mock setups
- **Coverage**: Aim for >80% coverage on new code

---

## Important

- Do NOT make actual HTTP calls in tests
- Tests should be fast and not require external services
- Use descriptive test names that explain the scenario
- Group related tests in classes

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (10-final-validation.md) depends on this completing successfully
