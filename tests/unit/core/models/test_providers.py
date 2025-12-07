"""Tests for provider factory."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.core.models.providers import (
    get_model_provider,
    get_model_provider_async,
    check_all_providers,
)
from src.core.models.base_provider import ProviderHealthStatus
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

    def test_openai_without_api_key_raises_error(self):
        """Should raise ConfigurationError when OpenAI has no API key."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key = None
            mock_settings.return_value.llm.provider = "openai"

            with pytest.raises(ConfigurationError) as exc_info:
                get_model_provider("openai")

            assert "API key not configured" in str(exc_info.value)

    def test_auto_provider_defaults_to_local(self):
        """Should fall back to local provider when auto and no OpenAI key."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key = None
            mock_settings.return_value.llm.provider = "lmstudio"

            model = get_model_provider("auto")
            assert model is not None

    def test_uses_settings_provider_when_none_provided(self):
        """Should use configured provider from settings."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.llm.provider = "ollama"
            mock_settings.return_value.openai.api_key = None
            mock_settings.return_value.ollama.model_name = "test-model"
            mock_settings.return_value.ollama.base_url = "http://localhost:11434/v1"
            mock_settings.return_value.ollama.api_key = "ollama"

            model = get_model_provider()
            assert model is not None


class TestGetModelProviderAsync:
    """Tests for get_model_provider_async function."""

    @pytest.mark.asyncio
    async def test_ollama_provider_async(self):
        """Should create Ollama model asynchronously."""
        with patch(
            "src.core.models.providers.create_ollama_model_async",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = MagicMock()
            model = await get_model_provider_async("ollama")
            assert model is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_lmstudio_provider_async(self):
        """Should create LM Studio model asynchronously."""
        with patch(
            "src.core.models.providers.create_lmstudio_model_async",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = MagicMock()
            model = await get_model_provider_async("lmstudio")
            assert model is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_llamacpp_provider_async(self):
        """Should create llama.cpp model asynchronously."""
        with patch(
            "src.core.models.providers.create_llamacpp_model_async",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = MagicMock()
            model = await get_model_provider_async("llamacpp")
            assert model is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_provider_async_raises_error(self):
        """Should raise ConfigurationError for invalid provider."""
        with pytest.raises(ConfigurationError) as exc_info:
            await get_model_provider_async("invalid")

        assert "Invalid LLM provider" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auto_provider_async_detects_available(self):
        """Should auto-detect available provider."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key = None
            mock_settings.return_value.llm.provider = "auto"

            with patch(
                "src.core.models.providers.lmstudio_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=True,
                    model_detected=True,
                    model_id="test-model",
                    base_url="http://localhost:1234/v1",
                    provider_type="lmstudio",
                ),
            ):
                with patch(
                    "src.core.models.providers.create_lmstudio_model_async",
                    new_callable=AsyncMock,
                ) as mock_create:
                    mock_create.return_value = MagicMock()
                    model = await get_model_provider_async("auto")
                    assert model is not None


class TestCheckAllProviders:
    """Tests for check_all_providers function."""

    @pytest.mark.asyncio
    async def test_returns_all_providers(self):
        """Should return status for all providers."""
        with patch(
            "src.core.models.providers.lmstudio_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=True,
                model_id="lm-model",
                base_url="http://localhost:1234/v1",
                provider_type="lmstudio",
            ),
        ), patch(
            "src.core.models.providers.ollama_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=True,
                model_id="ollama-model",
                base_url="http://localhost:11434/v1",
                provider_type="ollama",
            ),
        ), patch(
            "src.core.models.providers.llamacpp_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=False,
                model_detected=False,
                model_id=None,
                base_url="http://localhost:8080/v1",
                error="Connection refused",
                provider_type="llamacpp",
            ),
        ):
            results = await check_all_providers()

        assert "openai" in results
        assert "lmstudio" in results
        assert "ollama" in results
        assert "llamacpp" in results

        # Check lmstudio result
        assert results["lmstudio"].connected is True
        assert results["lmstudio"].model_id == "lm-model"

        # Check ollama result
        assert results["ollama"].connected is True
        assert results["ollama"].model_id == "ollama-model"

        # Check llamacpp result (disconnected)
        assert results["llamacpp"].connected is False
        assert results["llamacpp"].error == "Connection refused"

    @pytest.mark.asyncio
    async def test_handles_health_check_exceptions(self):
        """Should handle exceptions from health checks gracefully."""
        with patch(
            "src.core.models.providers.lmstudio_health_check",
            new_callable=AsyncMock,
            side_effect=Exception("Connection timeout"),
        ), patch(
            "src.core.models.providers.ollama_health_check",
            new_callable=AsyncMock,
            return_value=ProviderHealthStatus(
                connected=True,
                model_detected=True,
                model_id="ollama-model",
                base_url="http://localhost:11434/v1",
                provider_type="ollama",
            ),
        ), patch(
            "src.core.models.providers.llamacpp_health_check",
            new_callable=AsyncMock,
            side_effect=Exception("Server not running"),
        ):
            results = await check_all_providers()

        # All providers should still be present
        assert "openai" in results
        assert "lmstudio" in results
        assert "ollama" in results
        assert "llamacpp" in results

        # Failed providers should have error info
        assert results["lmstudio"].connected is False
        assert "Connection timeout" in results["lmstudio"].error

        assert results["llamacpp"].connected is False
        assert "Server not running" in results["llamacpp"].error

        # Working provider should be fine
        assert results["ollama"].connected is True

    @pytest.mark.asyncio
    async def test_openai_status_from_config(self):
        """Should check OpenAI status based on config."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key = "test-api-key"
            mock_settings.return_value.openai.model = "gpt-4"

            with patch(
                "src.core.models.providers.lmstudio_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="lmstudio",
                ),
            ), patch(
                "src.core.models.providers.ollama_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="ollama",
                ),
            ), patch(
                "src.core.models.providers.llamacpp_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="llamacpp",
                ),
            ):
                results = await check_all_providers()

        # OpenAI should be "connected" if API key is configured
        assert results["openai"].connected is True
        assert results["openai"].model_id == "gpt-4"

    @pytest.mark.asyncio
    async def test_openai_disconnected_without_key(self):
        """Should show OpenAI as disconnected when no API key."""
        with patch("src.core.models.providers.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key = None
            mock_settings.return_value.openai.model = "gpt-4"

            with patch(
                "src.core.models.providers.lmstudio_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="lmstudio",
                ),
            ), patch(
                "src.core.models.providers.ollama_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="ollama",
                ),
            ), patch(
                "src.core.models.providers.llamacpp_health_check",
                new_callable=AsyncMock,
                return_value=ProviderHealthStatus(
                    connected=False,
                    model_detected=False,
                    model_id=None,
                    base_url="",
                    provider_type="llamacpp",
                ),
            ):
                results = await check_all_providers()

        # OpenAI should be "disconnected" if no API key
        assert results["openai"].connected is False
        assert results["openai"].model_id is None
