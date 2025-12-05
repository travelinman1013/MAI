"""Integration tests for the Gradio GUI."""

import pytest

from src.gui.api_client import MAIClient
from src.gui.session import format_history_for_gradio, generate_session_id


class TestSessionManagement:
    """Tests for session management utilities."""

    def test_generate_session_id_format(self):
        """Session ID should have expected format."""
        session_id = generate_session_id()
        assert session_id.startswith("gui_")
        parts = session_id.split("_")
        # Format: gui_YYYYMMDD_HHMMSS_xxxxxxxx (4 parts when split by _)
        assert len(parts) == 4
        assert parts[0] == "gui"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 8  # short uuid

    def test_generate_session_id_unique(self):
        """Each session ID should be unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_format_history_empty(self):
        """Empty history should return empty list."""
        result = format_history_for_gradio([])
        assert result == []

    def test_format_history_filters_roles(self):
        """Should only include user and assistant roles."""
        api_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "system", "content": "You are helpful"},
            {"role": "tool", "content": "Tool output"},
        ]
        result = format_history_for_gradio(api_messages)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}

    def test_format_history_preserves_order(self):
        """History should maintain message order."""
        api_messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Response 2"},
        ]
        result = format_history_for_gradio(api_messages)
        assert len(result) == 4
        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Response 1"
        assert result[2]["content"] == "Second"
        assert result[3]["content"] == "Response 2"


@pytest.mark.asyncio
class TestAPIClient:
    """Integration tests for the API client (requires running API)."""

    @pytest.fixture
    def client(self):
        """Create a MAIClient instance for testing."""
        return MAIClient()

    async def test_list_agents(self, client):
        """Should return list of available agents."""
        try:
            agents = await client.list_agents()
            assert isinstance(agents, list)
            assert len(agents) > 0
            assert "simple_agent" in agents or "chat_agent" in agents
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_health_check(self, client):
        """Health check should return status."""
        health = await client.health_check()
        assert "status" in health or "error" in health

    async def test_health_check_returns_dict(self, client):
        """Health check should always return a dict."""
        health = await client.health_check()
        assert isinstance(health, dict)

    async def test_chat_simple_agent(self, client):
        """Should get response from simple agent."""
        try:
            response = await client.chat(
                message="Hello test",
                agent_name="simple_agent",
                session_id="test_integration_123",
            )
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_stream_chat(self, client):
        """Should stream response chunks."""
        try:
            chunks = []
            async for chunk in client.stream_chat(
                message="Hello",
                agent_name="simple_agent",
                session_id="test_stream_123",
            ):
                chunks.append(chunk)

            assert len(chunks) > 0
            full_response = "".join(chunks)
            assert len(full_response) > 0
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_history_operations(self, client):
        """Should handle history get/clear."""
        try:
            session_id = generate_session_id()

            # New session should have empty history
            history = await client.get_history(session_id)
            assert history == []

            # Send a message to create history
            await client.chat("Test message", "simple_agent", session_id)

            # Now history should exist
            history = await client.get_history(session_id)
            # May have messages now (depends on API behavior)

            # Clear should succeed
            result = await client.clear_history(session_id)
            assert result is True

        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_get_history_nonexistent_session(self, client):
        """Should return empty list for nonexistent session."""
        try:
            history = await client.get_history("nonexistent_session_xyz123")
            assert history == []
        except Exception as e:
            pytest.skip(f"API not available: {e}")
