"""Message schemas with multimodal support."""

from pydantic import BaseModel
from typing import Literal


class TextContent(BaseModel):
    """Text content in a message."""
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    """Image content in a message."""
    type: Literal["image"] = "image"
    image_url: str | None = None  # URL or data URI
    image_base64: str | None = None  # Base64 encoded image


class MessageContent(BaseModel):
    """Union of content types."""
    content: list[TextContent | ImageContent]


class MultimodalMessage(BaseModel):
    """A message that can contain text and/or images."""
    role: Literal["user", "assistant", "system"]
    content: str | list[TextContent | ImageContent]

    def get_text(self) -> str:
        """Extract text content from message."""
        if isinstance(self.content, str):
            return self.content
        texts = [c.text for c in self.content if isinstance(c, TextContent)]
        return " ".join(texts)

    def get_images(self) -> list[str]:
        """Extract image URLs/data from message."""
        if isinstance(self.content, str):
            return []
        return [
            c.image_url or f"data:image/png;base64,{c.image_base64}"
            for c in self.content
            if isinstance(c, ImageContent) and (c.image_url or c.image_base64)
        ]
