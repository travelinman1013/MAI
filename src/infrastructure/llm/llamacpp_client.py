"""llama.cpp server client for server management and monitoring.

Provides access to llama.cpp server-specific endpoints for health,
slots, and property information.
"""

from typing import Any, Optional

import httpx

from src.core.utils.config import get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class LlamaCppClient:
    """Client for llama.cpp server management APIs.

    Accesses server-specific endpoints that are not part of OpenAI API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize llama.cpp client.

        Args:
            base_url: Server URL (without /v1). If None, uses settings.
            timeout: Request timeout in seconds
        """
        settings = get_settings().llamacpp
        url = base_url or settings.base_url
        # Strip /v1 if present
        self.base_url = url.replace("/v1", "").rstrip("/")
        self.timeout = timeout

    async def health_check(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health status dict with 'status' key ('ok' or 'loading model' etc.)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def get_slots(self) -> list[dict[str, Any]]:
        """Get slot information.

        Returns:
            List of slot info dicts with id, state, prompt, etc.

        Note:
            Slots represent concurrent request handling capacity.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/slots")
            response.raise_for_status()
            return response.json()

    async def get_props(self) -> dict[str, Any]:
        """Get server properties.

        Returns:
            Server properties dict with model info, settings, etc.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/props")
            response.raise_for_status()
            return response.json()

    async def list_models(self) -> list[dict[str, Any]]:
        """List loaded model via OpenAI-compatible endpoint.

        Returns:
            List with single model info dict
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def is_running(self) -> bool:
        """Check if llama.cpp server is running.

        Returns:
            True if server responds to health check
        """
        try:
            health = await self.health_check()
            return health.get("status") == "ok"
        except Exception:
            return False

    async def is_model_loaded(self) -> bool:
        """Check if model is fully loaded and ready.

        Returns:
            True if model is loaded and ready for inference
        """
        try:
            health = await self.health_check()
            status = health.get("status", "")
            return status == "ok"
        except Exception:
            return False
