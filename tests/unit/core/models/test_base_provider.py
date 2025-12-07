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
        expected = {"openai", "lmstudio", "ollama", "llamacpp", "mlxlm", "auto"}
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
        assert ProviderType.LMSTUDIO == "lmstudio"
        assert ProviderType.LLAMACPP == "llamacpp"
        assert ProviderType.MLXLM == "mlxlm"
        assert ProviderType.AUTO == "auto"

    def test_provider_from_string(self):
        """Should be able to create ProviderType from string."""
        assert ProviderType("openai") == ProviderType.OPENAI
        assert ProviderType("ollama") == ProviderType.OLLAMA

    def test_invalid_provider_raises_error(self):
        """Invalid provider string should raise ValueError."""
        with pytest.raises(ValueError):
            ProviderType("invalid_provider")


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

    def test_provider_type_field(self):
        """Provider type field should store provider name."""
        status = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="test-model",
            base_url="http://localhost:11434/v1",
            provider_type="ollama",
        )
        assert status.provider_type == "ollama"

    def test_full_health_status(self):
        """Test creating a full health status with all fields."""
        status = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="llama3.2:latest",
            base_url="http://localhost:11434/v1",
            error=None,
            provider_type="ollama",
            metadata={"version": "0.1.0", "slots": 4},
        )
        assert status.connected is True
        assert status.model_detected is True
        assert status.model_id == "llama3.2:latest"
        assert status.base_url == "http://localhost:11434/v1"
        assert status.error is None
        assert status.provider_type == "ollama"
        assert status.metadata["version"] == "0.1.0"
        assert status.metadata["slots"] == 4

    def test_metadata_default_factory_isolation(self):
        """Each instance should have its own metadata dict."""
        status1 = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="test1",
            base_url="http://localhost",
        )
        status2 = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="test2",
            base_url="http://localhost",
        )
        status1.metadata["key"] = "value1"
        assert "key" not in status2.metadata


class TestLLMProviderProtocol:
    """Tests for LLMProviderProtocol interface."""

    def test_protocol_is_defined(self):
        """Protocol should be defined and importable."""
        assert LLMProviderProtocol is not None

    def test_protocol_has_required_methods(self):
        """Protocol should define required methods."""
        # Check that the protocol defines the expected methods
        # This is a structural check
        assert hasattr(LLMProviderProtocol, "health_check")
        assert hasattr(LLMProviderProtocol, "list_models")
        assert hasattr(LLMProviderProtocol, "detect_model")
        assert hasattr(LLMProviderProtocol, "create_model")
        assert hasattr(LLMProviderProtocol, "create_model_async")
