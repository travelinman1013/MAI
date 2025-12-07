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
