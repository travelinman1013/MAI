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
