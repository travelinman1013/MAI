# 04 - Document Upload & Context

**Project**: MAI Frontend Enhancement
**Sequence**: 4 of 5
**Depends On**: 03-image-support.md completed

---

## Archon Task Management

**Task ID**: `47e33266-f0b3-4ff7-81a7-36ee71a59a4a`
**Project ID**: `118ddd94-6aef-48cf-9397-43816f499907`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/47e33266-f0b3-4ff7-81a7-36ee71a59a4a" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/47e33266-f0b3-4ff7-81a7-36ee71a59a4a" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

This task adds document upload capability to the chat interface. Users can upload PDF, TXT, or Markdown files, and the content will be injected into the chat context for the LLM to reference. This is the foundation for future RAG (Retrieval-Augmented Generation) capabilities.

**Current Infrastructure Status**:
- PostgreSQL: Configured
- Qdrant: Configured (for future vector search)
- Redis: Working (for caching)

This step focuses on **direct context injection** (sending document content with the message), laying groundwork for full RAG integration later.

---

## Requirements

### 1. Create Document Processing Module

Create `src/core/documents/processor.py`:

```python
"""Document processing utilities."""

import io
from pathlib import Path
from typing import Literal

DocumentType = Literal["pdf", "txt", "md", "markdown"]


class DocumentProcessor:
    """Process documents for context injection."""

    SUPPORTED_TYPES = {
        ".pdf": "pdf",
        ".txt": "txt",
        ".md": "md",
        ".markdown": "markdown",
    }

    MAX_CHARS = 50000  # Max characters to inject into context

    @classmethod
    def get_document_type(cls, filename: str) -> DocumentType | None:
        """Get document type from filename."""
        suffix = Path(filename).suffix.lower()
        return cls.SUPPORTED_TYPES.get(suffix)

    @classmethod
    async def extract_text(cls, file_path: str) -> str:
        """Extract text content from a document.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return await cls._extract_pdf(path)
        elif suffix in (".txt", ".md", ".markdown"):
            return await cls._extract_text_file(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    @classmethod
    async def _extract_pdf(cls, path: Path) -> str:
        """Extract text from PDF using pypdf."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            # Truncate if too long
            if len(full_text) > cls.MAX_CHARS:
                full_text = full_text[:cls.MAX_CHARS] + "\n\n[... content truncated ...]"

            return full_text

        except ImportError:
            raise ImportError("pypdf is required for PDF processing. Install with: pip install pypdf")

    @classmethod
    async def _extract_text_file(cls, path: Path) -> str:
        """Extract text from plain text files."""
        try:
            content = path.read_text(encoding="utf-8")

            if len(content) > cls.MAX_CHARS:
                content = content[:cls.MAX_CHARS] + "\n\n[... content truncated ...]"

            return content
        except UnicodeDecodeError:
            # Try with different encoding
            content = path.read_text(encoding="latin-1")
            if len(content) > cls.MAX_CHARS:
                content = content[:cls.MAX_CHARS] + "\n\n[... content truncated ...]"
            return content

    @classmethod
    def format_for_context(cls, content: str, filename: str) -> str:
        """Format document content for injection into chat context.

        Args:
            content: Extracted document text
            filename: Original filename

        Returns:
            Formatted context string
        """
        return f"""<document filename="{filename}">
{content}
</document>"""


# Singleton instance
document_processor = DocumentProcessor()
```

### 2. Add Document Upload Endpoint

Create or update `src/api/routes/documents.py`:

```python
"""API routes for document handling."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.core.documents.processor import document_processor

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentContent(BaseModel):
    """Processed document content."""
    filename: str
    content: str
    char_count: int
    truncated: bool


@router.post("/extract", response_model=DocumentContent)
async def extract_document(
    file: UploadFile = File(...),
) -> DocumentContent:
    """Extract text content from an uploaded document.

    Supports: PDF, TXT, MD files
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    doc_type = document_processor.get_document_type(file.filename)
    if not doc_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {list(document_processor.SUPPORTED_TYPES.keys())}",
        )

    # Save to temp file
    try:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Extract text
        text = await document_processor.extract_text(tmp_path)

        # Clean up
        Path(tmp_path).unlink(missing_ok=True)

        return DocumentContent(
            filename=file.filename,
            content=text,
            char_count=len(text),
            truncated=len(text) >= document_processor.MAX_CHARS,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")


@router.get("/supported-types")
async def get_supported_types() -> list[str]:
    """Get list of supported document types."""
    return list(document_processor.SUPPORTED_TYPES.keys())
```

### 3. Register the Router

Update `src/main.py` or `src/api/routes/__init__.py`:

```python
from src.api.routes.documents import router as documents_router

app.include_router(documents_router, prefix="/api/v1")
```

### 4. Add pypdf Dependency

Update `pyproject.toml`:

```toml
[tool.poetry.dependencies]
# ... existing dependencies
pypdf = "^4.0"
```

Or in requirements.txt if used:
```
pypdf>=4.0
```

### 5. Update GUI for Document Upload

Update `src/gui/app.py`:

```python
from pathlib import Path


async def process_document(file_path: str | None) -> tuple[str, str]:
    """Process an uploaded document and return content preview.

    Returns:
        Tuple of (document context string, status message)
    """
    if not file_path:
        return "", ""

    try:
        path = Path(file_path)
        if not path.exists():
            return "", "File not found"

        # Read and process locally for preview
        text = await document_processor.extract_text(file_path)
        formatted = document_processor.format_for_context(text, path.name)

        preview_len = min(500, len(text))
        preview = text[:preview_len] + ("..." if len(text) > preview_len else "")

        return formatted, f"Loaded: {path.name} ({len(text):,} chars)"

    except Exception as e:
        return "", f"Error: {e}"


async def stream_response_with_context(
    message: str,
    image: str | None,
    document_context: str,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, str | None, str, list], None]:
    """Stream response with optional image and document context.

    Args:
        message: User's text message
        image: Optional image file path
        document_context: Extracted document content
        history: Chat history
        session_id: Session ID
        agent_name: Agent name

    Yields:
        Tuple of (empty message, None image, document context, updated history)
    """
    if not message.strip() and not image and not document_context:
        yield "", None, document_context, history
        return

    history = history or []

    # Build the full message with document context
    full_message = message
    if document_context:
        full_message = f"""I'm sharing a document with you for context:

{document_context}

My question/request: {message}"""

    # Handle image if present
    if image:
        image_data = encode_image(image)
        if image_data:
            history.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image", "url": image_data},
                ],
            })
        else:
            history.append({"role": "user", "content": message})
    else:
        # Show abbreviated version in history (not full document)
        display_message = message
        if document_context:
            display_message = f"[Document attached] {message}"
        history.append({"role": "user", "content": display_message})

    # Add empty assistant response
    history.append({"role": "assistant", "content": ""})

    try:
        images = [encode_image(image)] if image else None

        async for chunk in mai_client.stream_chat(
            message=full_message,  # Send full message with context
            agent_name=agent_name,
            session_id=session_id,
            images=images,
        ):
            history[-1]["content"] += chunk
            yield "", None, document_context, history

    except Exception as e:
        history[-1]["content"] = f"Error: {e}"
        yield "", None, document_context, history
```

Update the interface layout with document upload:

```python
def create_chat_interface() -> gr.Blocks:
    # ... existing setup ...

    # State for document context
    document_context = gr.State("")

    # Chat interface
    chatbot = gr.Chatbot(
        label="Conversation",
        height=450,
        type="messages",
        # ... other params
    )

    # Input area with tabs for different input types
    with gr.Tabs():
        with gr.TabItem("Message"):
            with gr.Row():
                with gr.Column(scale=4):
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Type your message...",
                        lines=3,
                    )
                with gr.Column(scale=1):
                    submit_btn = gr.Button("Send", variant="primary", size="lg")

        with gr.TabItem("Attachments"):
            with gr.Row():
                with gr.Column(scale=1):
                    image_input = gr.Image(
                        label="Image",
                        type="filepath",
                        height=150,
                        sources=["upload", "clipboard"],
                    )
                with gr.Column(scale=1):
                    document_input = gr.File(
                        label="Document (PDF, TXT, MD)",
                        file_types=[".pdf", ".txt", ".md", ".markdown"],
                        type="filepath",
                    )
            document_status = gr.Markdown("")

    # Document processing
    document_input.change(
        process_document,
        inputs=[document_input],
        outputs=[document_context, document_status],
    )

    # Clear document when starting new session
    async def new_session_clear_doc():
        new_sid, history, info, feedback = await new_session()
        return new_sid, history, info, feedback, "", ""

    new_btn.click(
        new_session_clear_doc,
        outputs=[session_id, chatbot, session_info, feedback, document_context, document_status],
    )

    # Update submit handlers
    submit_btn.click(
        stream_response_with_context,
        inputs=[msg, image_input, document_context, chatbot, session_id, agent_selector],
        outputs=[msg, image_input, document_context, chatbot],
    )
    msg.submit(
        stream_response_with_context,
        inputs=[msg, image_input, document_context, chatbot, session_id, agent_selector],
        outputs=[msg, image_input, document_context, chatbot],
    )
```

---

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| CREATE | `src/core/documents/__init__.py` |
| CREATE | `src/core/documents/processor.py` |
| CREATE | `src/api/routes/documents.py` |
| MODIFY | `src/main.py` or `src/api/routes/__init__.py` |
| MODIFY | `src/gui/app.py` |
| MODIFY | `pyproject.toml` (add pypdf) |

---

## Success Criteria

```bash
# 1. Install new dependency and rebuild
cd /Users/maxwell/Projects/MAI
poetry add pypdf
docker compose up -d --build

# 2. Test document extraction endpoint
# Create a test file
echo "This is a test document with some content." > /tmp/test.txt

# Upload and extract
curl -s -X POST http://localhost:8000/api/v1/documents/extract \
  -F "file=@/tmp/test.txt" | jq .
# Expected: {"filename": "test.txt", "content": "This is a test...", "char_count": ..., "truncated": false}

# 3. Test supported types endpoint
curl -s http://localhost:8000/api/v1/documents/supported-types | jq .
# Expected: [".pdf", ".txt", ".md", ".markdown"]

# 4. GUI verification (manual)
# Open http://localhost:7860 and verify:
# - Attachments tab appears with Image and Document uploads
# - Can upload a PDF or TXT file
# - Status shows filename and character count
# - Document context is sent with message
# - LLM can reference document content in response

# 5. Test with a real PDF (manual)
# Upload a small PDF and ask a question about its contents

# 6. Check for errors
docker compose logs mai-api --tail=30 2>&1 | grep -i error
# Expected: No errors related to document processing
```

---

## Technical Notes

- `pypdf` is used for PDF text extraction (pure Python, no external dependencies)
- Document content is truncated at 50,000 characters to stay within context limits
- For large documents, future RAG integration will use chunking + vector search
- The `<document>` XML tag format helps the LLM understand the context structure
- Document content is not stored in chat history to avoid bloating the UI
- Qdrant integration (future) will enable semantic search over document chunks

**Future Enhancements** (not in this step):
- Chunk documents and store in Qdrant for semantic retrieval
- Support more formats (DOCX, HTML, etc.)
- OCR for scanned PDFs
- Document summarization before context injection

---

## On Completion

1. Mark Archon task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/47e33266-f0b3-4ff7-81a7-36ee71a59a4a" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Proceed to: `05-polish-testing.md`
