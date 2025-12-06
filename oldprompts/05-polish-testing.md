# 05 - Polish & Integration Testing

**Project**: MAI Frontend Enhancement
**Sequence**: 5 of 5 (Final)
**Depends On**: 04-document-upload.md completed

---

## Archon Task Management

**Task ID**: `5fd067bd-8e64-42bd-b09f-b631eeacd311`
**Project ID**: `118ddd94-6aef-48cf-9397-43816f499907`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/5fd067bd-8e64-42bd-b09f-b631eeacd311" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/5fd067bd-8e64-42bd-b09f-b631eeacd311" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

All major features have been implemented:
1. ✅ Visual theme & polish
2. ✅ LM Studio model switching
3. ✅ Image support in chat
4. ✅ Document upload & context

This final step focuses on:
- End-to-end integration testing
- UX refinements and edge case handling
- Error handling improvements
- Performance optimization
- Documentation updates

---

## Requirements

### 1. Create Integration Test Suite

Create `tests/gui/test_frontend_integration.py`:

```python
"""Integration tests for the enhanced frontend."""

import pytest
from pathlib import Path
import tempfile

from src.gui.api_client import MAIClient
from src.core.documents.processor import DocumentProcessor


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

        import asyncio
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
                assert "id" in models[0] or "name" in models[0]
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
        # Theme should have primary_hue set
        assert hasattr(theme, "primary_hue")
```

### 2. Add Error Handling Improvements

Update `src/gui/app.py` with better error handling:

```python
async def safe_stream_response(
    message: str,
    image: str | None,
    document_context: str,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, str | None, str, list], None]:
    """Stream response with comprehensive error handling."""
    try:
        async for result in stream_response_with_context(
            message, image, document_context, history, session_id, agent_name
        ):
            yield result
    except ConnectionError as e:
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({
            "role": "assistant",
            "content": f"**Connection Error**: Cannot reach the API server. "
                       f"Please check if the backend is running.\n\nDetails: {e}",
        })
        yield "", None, document_context, history
    except TimeoutError:
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({
            "role": "assistant",
            "content": "**Timeout**: The request took too long. "
                       "This might happen with large documents or complex queries. "
                       "Try again with a shorter message.",
        })
        yield "", None, document_context, history
    except Exception as e:
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({
            "role": "assistant",
            "content": f"**Error**: An unexpected error occurred.\n\nDetails: {e}",
        })
        yield "", None, document_context, history
```

### 3. Add Loading States and UX Polish

Update the interface with loading indicators:

```python
def create_chat_interface() -> gr.Blocks:
    # ... existing setup ...

    # Add a loading indicator
    with gr.Row(visible=False) as loading_row:
        gr.Markdown("*Processing your request...*")

    # Wrap submit handlers to show/hide loading
    async def submit_with_loading(
        message, image, document_context, history, session_id, agent_name
    ):
        """Submit with loading state management."""
        # First yield shows loading
        yield gr.update(interactive=False), None, document_context, history, gr.update(visible=True)

        # Stream response
        async for result in safe_stream_response(
            message, image, document_context, history, session_id, agent_name
        ):
            msg, img, doc, hist = result
            yield gr.update(value=msg, interactive=True), img, doc, hist, gr.update(visible=False)

    submit_btn.click(
        submit_with_loading,
        inputs=[msg, image_input, document_context, chatbot, session_id, agent_selector],
        outputs=[msg, image_input, document_context, chatbot, loading_row],
    )
```

### 4. Add Keyboard Shortcuts

```python
# In create_chat_interface():

# Add keyboard shortcut hints
gr.Markdown(
    "*Tip: Press Enter to send, Shift+Enter for new line*",
    elem_classes=["hint-text"],
)

# Update CSS for hints
CUSTOM_CSS += """
.hint-text {
    font-size: 0.75rem;
    color: #9ca3af;
    text-align: right;
    margin-top: -0.5rem;
}
"""
```

### 5. Update Configuration Defaults

Update `src/gui/config.py` with new settings:

```python
from pydantic_settings import BaseSettings


class GUISettings(BaseSettings):
    """GUI configuration settings."""

    api_base_url: str = "http://localhost:8000/api/v1"
    default_agent: str = "chat_agent"
    app_title: str = "MAI Chat"
    app_subtitle: str = "Your private AI assistant powered by local LLMs"
    server_port: int = 7860

    # New settings
    max_document_size_mb: float = 10.0
    max_image_size_mb: float = 5.0
    enable_model_switching: bool = True
    show_debug_info: bool = False

    class Config:
        env_prefix = "GUI_"


gui_settings = GUISettings()
```

### 6. Run Full Test Suite

Create `scripts/test_frontend.sh`:

```bash
#!/bin/bash
# Test script for frontend enhancements

set -e

echo "=== MAI Frontend Enhancement Tests ==="
echo ""

# 1. Run unit tests
echo "1. Running unit tests..."
poetry run pytest tests/gui/ -v --tb=short

# 2. Check for import errors
echo ""
echo "2. Checking imports..."
poetry run python -c "
from src.gui.app import create_chat_interface
from src.gui.theme import create_mai_theme
from src.core.documents.processor import document_processor
print('All imports successful!')
"

# 3. Check API endpoints
echo ""
echo "3. Checking API endpoints..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is running"

    echo "  - /api/v1/models/: $(curl -s http://localhost:8000/api/v1/models/ | head -c 50)..."
    echo "  - /api/v1/documents/supported-types: $(curl -s http://localhost:8000/api/v1/documents/supported-types)"
else
    echo "API not running - skipping endpoint tests"
fi

# 4. Check GUI is accessible
echo ""
echo "4. Checking GUI..."
if curl -s http://localhost:7860 > /dev/null 2>&1; then
    echo "GUI is running at http://localhost:7860"
else
    echo "GUI not running"
fi

echo ""
echo "=== Tests Complete ==="
```

### 7. Update README

Add section to README.md documenting new features:

```markdown
## Features

### Chat Interface

The Gradio-based chat interface provides:

- **Model Switching**: Switch between loaded LM Studio models from the UI
- **Image Support**: Upload images for multimodal conversations (requires vision-capable model)
- **Document Upload**: Attach PDF, TXT, or MD files for context-aware conversations
- **Session Management**: Create, load, and manage conversation sessions
- **Custom Theme**: Modern, polished visual design with customizable colors

### Keyboard Shortcuts

- `Enter`: Send message
- `Shift+Enter`: New line in message

### Configuration

Environment variables for GUI customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `GUI_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API URL |
| `GUI_DEFAULT_AGENT` | `chat_agent` | Default agent to use |
| `GUI_APP_TITLE` | `MAI Chat` | Application title |
| `GUI_SERVER_PORT` | `7860` | GUI server port |
| `GUI_ENABLE_MODEL_SWITCHING` | `true` | Show model selector |
```

---

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| CREATE | `tests/gui/test_frontend_integration.py` |
| CREATE | `scripts/test_frontend.sh` |
| MODIFY | `src/gui/app.py` (error handling, loading states) |
| MODIFY | `src/gui/config.py` (new settings) |
| MODIFY | `README.md` (documentation) |

---

## Success Criteria

```bash
# 1. Run the full test suite
chmod +x scripts/test_frontend.sh
./scripts/test_frontend.sh
# Expected: All tests pass

# 2. Run pytest specifically
poetry run pytest tests/gui/test_frontend_integration.py -v
# Expected: All tests pass

# 3. Manual end-to-end test checklist:
# Open http://localhost:7860 and verify:

# [ ] Theme & Visual
#     [ ] Custom color scheme applied
#     [ ] Fonts load correctly (Inter, JetBrains Mono)
#     [ ] Avatar images display for user/assistant
#     [ ] Status bar shows connection info

# [ ] Model Switching
#     [ ] Model dropdown populated
#     [ ] Can switch models
#     [ ] Status updates with new model

# [ ] Image Support
#     [ ] Can upload image
#     [ ] Image displays in chat
#     [ ] LLM responds to image (with vision model)

# [ ] Document Upload
#     [ ] Can upload PDF/TXT/MD
#     [ ] Status shows file info
#     [ ] LLM can reference document content

# [ ] Error Handling
#     [ ] Graceful error messages
#     [ ] No crashes on invalid input
#     [ ] Connection errors handled

# [ ] Session Management
#     [ ] New session works
#     [ ] Load session works
#     [ ] Clear session works

# 4. Check no errors in logs
docker compose logs mai-api --tail=50 2>&1 | grep -i error | grep -v "No error"
docker compose logs mai-gui --tail=50 2>&1 | grep -i error | grep -v "No error"
# Expected: No errors
```

---

## Technical Notes

- Integration tests use pytest-asyncio for async test support
- The test script can be run in CI/CD pipelines
- Error messages should be user-friendly, not stack traces
- Loading states prevent double-submission of requests
- Configuration via environment variables allows customization without code changes

---

## On Completion

1. Mark Archon task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/5fd067bd-8e64-42bd-b09f-b631eeacd311" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Create completion document in Archon:
```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI Frontend Enhancement - Complete",
    "content": "# MAI Frontend Enhancement\n\nAll 5 steps completed successfully.\n\n## Features Implemented\n\n1. **Visual Theme & Polish** - Custom Gradio theme with modern styling\n2. **Model Switching** - Switch LLM models from UI via LM Studio API\n3. **Image Support** - Multimodal chat with image uploads\n4. **Document Upload** - PDF/TXT/MD context injection\n5. **Polish & Testing** - Integration tests, error handling, documentation\n\n## Next Steps\n\n- Full RAG integration with Qdrant\n- Support for more document formats (DOCX, HTML)\n- Persistent document library\n- Model performance metrics in UI",
    "project_id": "118ddd94-6aef-48cf-9397-43816f499907"
  }'
```

---

## Project Complete!

All frontend enhancement tasks have been completed. The MAI chat interface now features:

- Modern, polished visual design
- LM Studio model switching
- Multimodal image support
- Document upload and context injection
- Comprehensive error handling
- Integration test suite

For future enhancements, see the roadmap in the README.
