"""LM Studio API client for model management."""

import httpx
from typing import Any

from src.core.utils.config import get_settings


class LMStudioClient:
    """Client for LM Studio model management APIs."""

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or settings.lm_studio.base_url.rstrip("/v1")
        # LM Studio management endpoints are at root, not /v1

    async def list_models(self) -> list[dict[str, Any]]:
        """List all available models in LM Studio.

        Returns:
            List of model objects with id, object, owned_by fields
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # OpenAI-compatible /v1/models endpoint
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to list models: {e}") from e

    async def get_loaded_models(self) -> list[dict[str, Any]]:
        """Get currently loaded models.

        LM Studio's /v1/models returns only loaded models by default.
        """
        return await self.list_models()

    async def load_model(self, model_id: str) -> dict[str, Any]:
        """Load a model into memory.

        Args:
            model_id: The model identifier to load

        Returns:
            Load status response
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # LM Studio REST API for loading models
                response = await client.post(
                    f"{self.base_url}/api/v0/models/load",
                    json={"model": model_id},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to load model: {e}") from e

    async def unload_model(self, model_id: str) -> dict[str, Any]:
        """Unload a model from memory.

        Args:
            model_id: The model identifier to unload

        Returns:
            Unload status response
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v0/models/unload",
                    json={"model": model_id},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to unload model: {e}") from e


# Lazy singleton pattern - avoid calling get_settings() at import time
_lmstudio_client: LMStudioClient | None = None


def get_lmstudio_client() -> LMStudioClient:
    """Get the LMStudio client singleton (lazy initialization)."""
    global _lmstudio_client
    if _lmstudio_client is None:
        _lmstudio_client = LMStudioClient()
    return _lmstudio_client
