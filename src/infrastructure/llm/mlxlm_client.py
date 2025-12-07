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
