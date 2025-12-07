"""Base provider abstraction for LLM providers.

This module defines the interface that all LLM providers must implement.
It uses Python's Protocol for structural typing, allowing duck-typed
implementations without explicit inheritance.

Supported providers:
- OpenAI API (native)
- LM Studio (OpenAI-compatible local models)
- Ollama (local model server)
- llama.cpp (direct local inference)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol


class ProviderType(str, Enum):
    """Supported LLM provider types.

    Each provider type represents a different LLM backend:
    - OPENAI: OpenAI API (GPT models)
    - LMSTUDIO: LM Studio local server (OpenAI-compatible)
    - OLLAMA: Ollama local model server
    - LLAMACPP: llama.cpp direct inference
    - MLXLM: MLX-LM server for Apple Silicon (Metal GPU)
    - AUTO: Automatic provider selection based on availability
    """

    OPENAI = "openai"
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    MLXLM = "mlxlm"
    AUTO = "auto"


@dataclass
class ProviderHealthStatus:
    """Standardized health check result for LLM providers.

    This dataclass provides a consistent structure for health check responses
    across all provider implementations.

    Attributes:
        connected: Whether the provider is reachable and responding
        model_detected: Whether a model is loaded and available
        model_id: The ID/name of the detected model, if any
        base_url: The base URL of the provider endpoint
        error: Error message if the health check failed
        provider_type: The type of provider (e.g., 'lmstudio', 'ollama')
        metadata: Additional provider-specific information

    Example:
        ```python
        status = ProviderHealthStatus(
            connected=True,
            model_detected=True,
            model_id="llama-3.2-3b-instruct",
            base_url="http://localhost:1234/v1",
            provider_type="lmstudio",
            metadata={"version": "0.2.31"}
        )
        ```
    """

    connected: bool
    model_detected: bool
    model_id: Optional[str]
    base_url: str
    error: Optional[str] = None
    provider_type: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class LLMProviderProtocol(Protocol):
    """Protocol defining the interface all LLM providers must implement.

    This protocol uses structural typing - any class that implements these
    methods is considered a valid provider, without explicit inheritance.
    This follows Python's duck-typing philosophy while still providing
    clear interface documentation and type checking support.

    Required Methods:
        - health_check: Check provider connectivity and model status
        - list_models: Get available models from the provider
        - detect_model: Detect the currently loaded/default model
        - create_model: Create a model instance synchronously
        - create_model_async: Create a model instance asynchronously

    Example:
        ```python
        class MyProvider:
            async def health_check(self) -> ProviderHealthStatus:
                # Implementation
                ...

            async def list_models(self) -> list[dict[str, Any]]:
                # Implementation
                ...

            async def detect_model(self) -> Optional[str]:
                # Implementation
                ...

            def create_model(self, model_name: Optional[str] = None) -> Any:
                # Implementation
                ...

            async def create_model_async(
                self,
                model_name: Optional[str] = None,
                auto_detect: bool = True,
                test_connection: bool = True,
            ) -> Any:
                # Implementation
                ...

        # MyProvider is now a valid LLMProviderProtocol without inheritance
        provider: LLMProviderProtocol = MyProvider()
        ```
    """

    async def health_check(self) -> ProviderHealthStatus:
        """Perform health check on the provider.

        Checks whether the provider is reachable and whether a model
        is currently loaded and available for inference.

        Returns:
            ProviderHealthStatus with connection and model information
        """
        ...

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from this provider.

        Queries the provider for all available models that can be used
        for inference. The structure of each model dictionary may vary
        by provider but typically includes 'id' and 'name' fields.

        Returns:
            List of model information dictionaries
        """
        ...

    async def detect_model(self) -> Optional[str]:
        """Detect the currently loaded/default model.

        Attempts to determine which model is currently active or
        would be used by default if no model is specified.

        Returns:
            Model ID string or None if no model detected
        """
        ...

    def create_model(self, model_name: Optional[str] = None) -> Any:
        """Create a model instance synchronously.

        Creates a model instance configured for use with Pydantic AI.
        This is the synchronous version that does not perform auto-detection
        or connection testing.

        Args:
            model_name: Optional model name override. If None, uses default.

        Returns:
            Configured model instance (typically OpenAIModel)
        """
        ...

    async def create_model_async(
        self,
        model_name: Optional[str] = None,
        auto_detect: bool = True,
        test_connection: bool = True,
    ) -> Any:
        """Create a model instance asynchronously with auto-detection.

        Creates a model instance with optional auto-detection of the
        currently loaded model and connection testing.

        Args:
            model_name: Optional model name override. If None and auto_detect
                is True, the model will be detected from the provider.
            auto_detect: If True, detect model from provider when model_name
                is not specified.
            test_connection: If True, verify connection to the provider
                before returning the model instance.

        Returns:
            Configured model instance (typically OpenAIModel)
        """
        ...
