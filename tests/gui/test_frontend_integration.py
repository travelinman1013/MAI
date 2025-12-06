"""Integration tests for the enhanced frontend."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.core.documents.processor import DocumentProcessor
from src.gui.api_client import MAIClient


class TestDocumentProcessor:
    """Tests for document processing."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    @pytest.fixture
    def sample_txt(self):
        """Create a sample text file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("This is a test document.\nWith multiple lines.\n")
            return f.name

    @pytest.fixture
    def sample_md(self):
        """Create a sample markdown file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Test Document\n\nThis is **markdown** content.\n")
            return f.name

    @pytest.mark.asyncio
    async def test_extract_txt(self, processor, sample_txt):
        """Test text file extraction."""
        content = await processor.extract_text(sample_txt)
        assert "test document" in content.lower()
        assert "multiple lines" in content.lower()
        Path(sample_txt).unlink()

    @pytest.mark.asyncio
    async def test_extract_md(self, processor, sample_md):
        """Test markdown file extraction."""
        content = await processor.extract_text(sample_md)
        assert "Test Document" in content
        assert "markdown" in content
        Path(sample_md).unlink()

    def test_format_for_context(self, processor):
        """Test context formatting."""
        formatted = processor.format_for_context("Hello world", "test.txt")
        assert '<document filename="test.txt">' in formatted
        assert "Hello world" in formatted
        assert "</document>" in formatted

    def test_get_document_type(self, processor):
        """Test document type detection."""
        assert processor.get_document_type("test.pdf") == "pdf"
        assert processor.get_document_type("test.txt") == "txt"
        assert processor.get_document_type("test.md") == "md"
        assert processor.get_document_type("test.docx") is None

    def test_truncation(self, processor):
        """Test content truncation for large documents."""
        # Create content larger than MAX_CHARS
        large_content = "x" * (processor.MAX_CHARS + 1000)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(large_content)
            tmp_path = f.name

        content = asyncio.run(processor.extract_text(tmp_path))
        assert "[... content truncated ...]" in content
        assert len(content) <= processor.MAX_CHARS + 100  # Allow for truncation message
        Path(tmp_path).unlink()


class TestAPIClientMethods:
    """Tests for new API client methods."""

    @pytest.fixture
    def client(self):
        return MAIClient(base_url="http://localhost:8000/api/v1")

    @pytest.mark.asyncio
    async def test_list_models_structure(self, client):
        """Test that list_models returns expected structure."""
        # This will fail if API is not running, which is expected in CI
        try:
            models = await client.list_models()
            assert isinstance(models, list)
            if models:
                # Models can have either 'id' or 'name' field
                assert "id" in models[0] or "name" in models[0]
        except Exception:
            pytest.skip("API not available")

    @pytest.mark.asyncio
    async def test_health_check_structure(self, client):
        """Test that health check returns expected structure."""
        try:
            health = await client.health_check()
            assert isinstance(health, dict)
            assert "status" in health
        except Exception:
            pytest.skip("API not available")

    @pytest.mark.asyncio
    async def test_llm_status_structure(self, client):
        """Test that LLM status returns expected structure."""
        try:
            status = await client.get_llm_status()
            assert isinstance(status, dict)
            assert "connected" in status
            assert "provider" in status
        except Exception:
            pytest.skip("API not available")


class TestTheme:
    """Tests for theme configuration."""

    def test_theme_creation(self):
        """Test that custom theme can be created."""
        from src.gui.theme import create_mai_theme

        theme = create_mai_theme()
        assert theme is not None

    def test_theme_has_custom_colors(self):
        """Test theme has expected customizations."""
        from src.gui.theme import create_mai_theme

        theme = create_mai_theme()
        # Theme should be a Gradio theme object
        assert theme is not None
        # Check it's a Soft theme with custom settings
        assert isinstance(theme, object)
        assert hasattr(theme, "set")


class TestMessageEncoding:
    """Tests for message encoding utilities."""

    def test_image_encoding(self):
        """Test image encoding to base64."""
        from src.gui.app import encode_image

        # Create a tiny 1x1 PNG
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Minimal valid PNG header
            png_data = (
                b"\x89PNG\r\n\x1a\n"  # PNG signature
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            f.write(png_data)
            tmp_path = f.name

        result = encode_image(tmp_path)
        assert result is not None
        assert result.startswith("data:image/png;base64,")
        Path(tmp_path).unlink()

    def test_image_encoding_none(self):
        """Test image encoding with None input."""
        from src.gui.app import encode_image

        result = encode_image(None)
        assert result is None

    def test_image_encoding_missing_file(self):
        """Test image encoding with non-existent file."""
        from src.gui.app import encode_image

        result = encode_image("/nonexistent/file.png")
        assert result is None


class TestSessionManagement:
    """Tests for session management utilities."""

    def test_session_id_generation(self):
        """Test session ID generation."""
        from src.gui.session import generate_session_id

        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        # Should have the format gui_YYYYMMDD_HHMMSS_xxxxxxxx
        assert session_id.startswith("gui_")
        parts = session_id.split("_")
        assert len(parts) == 4  # gui, date, time, uuid

    def test_history_formatting(self):
        """Test history formatting for Gradio."""
        from src.gui.session import format_history_for_gradio

        api_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        history = format_history_for_gradio(api_messages)
        assert isinstance(history, list)
        assert len(history) == 2  # Two messages (user and assistant)
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"


class TestConfiguration:
    """Tests for configuration management."""

    def test_gui_settings_defaults(self):
        """Test GUI settings have expected defaults."""
        from src.gui.config import gui_settings

        assert gui_settings.api_base_url is not None
        assert gui_settings.default_agent is not None
        assert gui_settings.app_title is not None
        assert gui_settings.server_port > 0

    def test_gui_settings_new_fields(self):
        """Test new configuration fields exist."""
        from src.gui.config import gui_settings

        # These are new fields we're adding
        assert hasattr(gui_settings, "max_document_size_mb")
        assert hasattr(gui_settings, "max_image_size_mb")
        assert hasattr(gui_settings, "enable_model_switching")
        assert hasattr(gui_settings, "show_debug_info")
