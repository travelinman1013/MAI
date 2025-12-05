"""API client for communicating with MAI agent service."""

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from src.gui.config import gui_settings


class MAIClient:
    """Client for the MAI agent API."""

    def __init__(self, base_url: str | None = None):
        """Initialize the MAI client.

        Args:
            base_url: Base URL for the API. Defaults to gui_settings.api_base_url.
        """
        self.base_url = base_url or gui_settings.api_base_url

    async def stream_chat(
        self,
        message: str,
        agent_name: str = "chat_agent",
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from the agent.

        Args:
            message: The user's message
            agent_name: Name of the agent to use
            session_id: Optional session ID for conversation continuity

        Yields:
            Content chunks as they arrive
        """
        url = f"{self.base_url}/agents/stream/{agent_name}"
        payload = {
            "user_input": message,
            "session_id": session_id,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip():
                            try:
                                chunk = json.loads(data)
                                if "content" in chunk and chunk["content"]:
                                    yield chunk["content"]
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

    async def chat(
        self,
        message: str,
        agent_name: str = "chat_agent",
        session_id: str | None = None,
    ) -> str:
        """Send a message and get a complete response (non-streaming).

        Args:
            message: The user's message
            agent_name: Name of the agent to use
            session_id: Optional session ID for conversation continuity

        Returns:
            The agent's response content
        """
        url = f"{self.base_url}/agents/run/{agent_name}"
        payload = {
            "user_input": message,
            "session_id": session_id,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and data.get("result"):
                result: dict[str, Any] = data["result"]
                return str(result.get("content", ""))
            return "Error: No response from agent"

    async def list_agents(self) -> list[str]:
        """Get list of available agents.

        Returns:
            List of agent names
        """
        url = f"{self.base_url}/agents/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [agent["name"] for agent in data.get("agents", [])]

    async def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session.

        Args:
            session_id: The session ID

        Returns:
            List of messages [{"role": str, "content": str, "timestamp": str}, ...]
        """
        url = f"{self.base_url}/agents/history/{session_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return data.get("messages", [])

    async def clear_history(self, session_id: str) -> bool:
        """Clear conversation history for a session.

        Args:
            session_id: The session ID

        Returns:
            True if successful
        """
        url = f"{self.base_url}/agents/history/{session_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url)
            return response.status_code == 200

    async def health_check(self) -> dict[str, Any]:
        """Check if the API is healthy.

        Returns:
            Health status dict or error info
        """
        try:
            # Health endpoint is at root level, not under /api/v1
            health_url = self.base_url.replace("/api/v1", "") + "/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Singleton instance
mai_client = MAIClient()
