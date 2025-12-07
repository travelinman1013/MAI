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
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await detect_ollama_model("http://localhost:11434/v1")

        assert result == "llama3.2:latest"

    @pytest.mark.asyncio
    async def test_detect_model_no_models(self):
        """Should return None when no models available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await detect_ollama_model("http://localhost:11434/v1")

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
            mock_instance = AsyncMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_instance.get = mock_get
            mock_client.return_value.__aenter__.return_value = mock_instance

            await detect_ollama_model("http://localhost:11434/v1")

            # Should call /api/tags, not /v1/api/tags
            call_url = mock_get.call_args[0][0]
            assert "/api/tags" in call_url
            assert "/v1/api/tags" not in call_url

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
                await detect_ollama_model("http://localhost:11434/v1")

            assert "HTTP error" in str(exc_info.value)


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
        assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_health_check_connected_no_model(self):
        """Should return connected but no model when server responds but no models."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await ollama_health_check()

        assert result.connected is True
        assert result.model_detected is False
        assert result.model_id is None

    @pytest.mark.asyncio
    async def test_health_check_uses_settings(self):
        """Should use provided settings."""
        from src.core.utils.config import OllamaSettings

        custom_settings = OllamaSettings(
            base_url="http://custom:11434/v1",
            model_name="custom-model",
            api_key="custom-key",
        )

        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value="custom-model",
        ):
            result = await ollama_health_check(settings=custom_settings)

        assert result.base_url == "http://custom:11434/v1"


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

    def test_create_model_with_custom_settings(self):
        """Should use provided settings."""
        from src.core.utils.config import OllamaSettings

        custom_settings = OllamaSettings(
            base_url="http://custom:11434/v1",
            model_name="custom-model",
            api_key="custom-key",
        )

        model = create_ollama_model(settings=custom_settings)
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

    @pytest.mark.asyncio
    async def test_create_model_with_explicit_name(self):
        """Should use explicit model name when provided."""
        model = await create_ollama_model_async(
            model_name="explicit-model",
            auto_detect=False,
            test_connection=False,
        )
        assert model is not None

    @pytest.mark.asyncio
    async def test_create_model_with_test_connection(self):
        """Should test connection when test_connection=True."""
        with patch(
            "src.core.models.ollama_provider.detect_ollama_model",
            new_callable=AsyncMock,
            return_value="test-model",
        ):
            model = await create_ollama_model_async(
                model_name="test-model",
                auto_detect=False,
                test_connection=True,
            )
            assert model is not None
