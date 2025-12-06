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
