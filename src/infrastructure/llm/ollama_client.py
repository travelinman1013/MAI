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
        import json

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": stream},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
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
