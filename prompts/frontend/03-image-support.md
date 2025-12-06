# 03 - Image Support in Chat

**Project**: MAI Frontend Enhancement
**Sequence**: 3 of 5
**Depends On**: 02-model-switching.md completed

---

## Archon Task Management

**Task ID**: `e25baf24-cc1d-4e86-8124-2fbadf43c7da`
**Project ID**: `118ddd94-6aef-48cf-9397-43816f499907`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/e25baf24-cc1d-4e86-8124-2fbadf43c7da" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/e25baf24-cc1d-4e86-8124-2fbadf43c7da" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

Gradio's Chatbot component natively supports multimodal messages including images. Pydantic AI also supports multimodal input via `ImageUrl` and `BinaryContent` classes. This task adds the ability to:
1. Upload images in the chat interface
2. Send images to the LLM as part of the conversation
3. Display images in chat history

**Prerequisites**:
- A multimodal-capable model must be loaded in LM Studio (e.g., LLaVA, Gemma 2 with vision, etc.)
- Previous visual polish and model switching steps are complete

---

## Requirements

### 1. Update Message Schema

Create or update message models in `src/api/schemas/messages.py`:

```python
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
```

### 2. Update Chat Agent for Multimodal

Modify the chat agent to handle image inputs. In `src/core/agents/chat_agent.py`:

```python
from pydantic_ai import Agent, BinaryContent, ImageUrl

async def process_multimodal_message(
    message: str,
    images: list[str] | None = None,
) -> list:
    """Convert message and images into Pydantic AI format.

    Args:
        message: Text message
        images: List of image URLs or base64 data URIs

    Returns:
        List of content items for Pydantic AI
    """
    content = [message]

    if images:
        for img in images:
            if img.startswith("data:"):
                # Base64 data URI - extract and convert
                # Format: data:image/png;base64,<base64_data>
                import base64
                header, data = img.split(",", 1)
                media_type = header.split(":")[1].split(";")[0]
                content.append(
                    BinaryContent(
                        data=base64.b64decode(data),
                        media_type=media_type,
                    )
                )
            else:
                # URL
                content.append(ImageUrl(url=img))

    return content
```

### 3. Update API Chat Endpoint

Modify `src/api/routes/agents.py` to accept images:

```python
from fastapi import UploadFile, File, Form
from typing import Annotated
import base64


class ChatRequest(BaseModel):
    """Chat request with optional images."""
    message: str
    session_id: str | None = None
    images: list[str] | None = None  # Base64 or URLs


@router.post("/{agent_name}/chat")
async def chat(
    agent_name: str,
    request: ChatRequest,
) -> ChatResponse:
    """Chat with an agent, optionally with images."""
    # ... existing logic, but pass images to agent
    content = await process_multimodal_message(
        request.message,
        request.images,
    )
    # Use content instead of just message
```

Or add a separate multimodal endpoint:

```python
@router.post("/{agent_name}/chat/multimodal")
async def chat_multimodal(
    agent_name: str,
    message: Annotated[str, Form()],
    session_id: Annotated[str | None, Form()] = None,
    images: list[UploadFile] = File(default=[]),
) -> ChatResponse:
    """Chat with an agent including image uploads."""
    # Convert uploaded files to base64
    image_data = []
    for img in images:
        content = await img.read()
        b64 = base64.b64encode(content).decode()
        media_type = img.content_type or "image/png"
        image_data.append(f"data:{media_type};base64,{b64}")

    # Process with agent
    # ...
```

### 4. Update GUI for Image Upload

Modify `src/gui/app.py` to add image upload:

```python
import base64
from pathlib import Path


def encode_image(image_path: str) -> str | None:
    """Encode an image file to base64 data URI."""
    if not image_path:
        return None
    try:
        path = Path(image_path)
        if not path.exists():
            return None

        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")

        # Read and encode
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        return f"data:{media_type};base64,{data}"
    except Exception:
        return None


async def stream_response_with_image(
    message: str,
    image: str | None,
    history: list,
    session_id: str,
    agent_name: str,
) -> AsyncGenerator[tuple[str, str | None, list], None]:
    """Stream a response, optionally with an image.

    Args:
        message: User's text message
        image: Optional image file path
        history: Chat history
        session_id: Session ID
        agent_name: Agent name

    Yields:
        Tuple of (empty message, None image, updated history)
    """
    if not message.strip() and not image:
        yield "", None, history
        return

    history = history or []

    # Build user message content
    if image:
        # Multimodal message with image
        image_data = encode_image(image)
        if image_data:
            # Add message with image to history
            history.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message} if message else None,
                    {"type": "image", "url": image_data},
                ],
            })
        else:
            history.append({"role": "user", "content": message})
    else:
        history.append({"role": "user", "content": message})

    # Add empty assistant response
    history.append({"role": "assistant", "content": ""})

    try:
        # Prepare images for API
        images = [encode_image(image)] if image else None

        async for chunk in mai_client.stream_chat(
            message=message,
            agent_name=agent_name,
            session_id=session_id,
            images=images,
        ):
            history[-1]["content"] += chunk
            yield "", None, history

    except Exception as e:
        history[-1]["content"] = f"Error: {e}"
        yield "", None, history
```

Update the interface layout:

```python
def create_chat_interface() -> gr.Blocks:
    # ... existing setup ...

    # Chat interface
    chatbot = gr.Chatbot(
        label="Conversation",
        height=500,
        type="messages",
        avatar_images=(
            "https://api.dicebear.com/7.x/avataaars/svg?seed=user",
            "https://api.dicebear.com/7.x/bottts/svg?seed=mai",
        ),
        show_copy_button=True,
        bubble_full_width=False,
    )

    # Message input with image upload
    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label="Attach Image",
                type="filepath",
                height=100,
                sources=["upload", "clipboard"],
                show_label=True,
            )
        with gr.Column(scale=4):
            msg = gr.Textbox(
                label="Message",
                placeholder="Type your message... (attach image on the left)",
                lines=3,
                show_label=True,
            )
        with gr.Column(scale=1):
            submit_btn = gr.Button("Send", variant="primary", size="lg")

    # Update event handlers
    submit_btn.click(
        stream_response_with_image,
        inputs=[msg, image_input, chatbot, session_id, agent_selector],
        outputs=[msg, image_input, chatbot],
    )
    msg.submit(
        stream_response_with_image,
        inputs=[msg, image_input, chatbot, session_id, agent_selector],
        outputs=[msg, image_input, chatbot],
    )
```

### 5. Update API Client for Images

Add image support to `src/gui/api_client.py`:

```python
async def stream_chat(
    self,
    message: str,
    agent_name: str,
    session_id: str,
    images: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat response with optional images."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "message": message,
            "session_id": session_id,
        }
        if images:
            payload["images"] = images

        async with client.stream(
            "POST",
            f"{self.base_url}/agents/{agent_name}/chat/stream",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk
```

---

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| CREATE | `src/api/schemas/messages.py` |
| MODIFY | `src/core/agents/chat_agent.py` |
| MODIFY | `src/api/routes/agents.py` |
| MODIFY | `src/gui/api_client.py` |
| MODIFY | `src/gui/app.py` |

---

## Success Criteria

```bash
# 1. Rebuild and restart services
docker compose up -d --build

# 2. Check API health
curl -s http://localhost:8000/health | jq .
# Expected: {"status": "healthy", ...}

# 3. Test multimodal endpoint (manual with curl)
# Create a test image base64
TEST_IMAGE=$(base64 -i /path/to/test.png)
curl -s -X POST http://localhost:8000/api/v1/agents/chat_agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is in this image?\", \"images\": [\"data:image/png;base64,$TEST_IMAGE\"]}" | jq .
# Expected: Response describing the image (if multimodal model loaded)

# 4. GUI verification (manual)
# Open http://localhost:7860 and verify:
# - Image upload component appears next to message input
# - Can upload image via drag-drop or file picker
# - Image appears in chat history after sending
# - LLM responds to image content (if multimodal model)

# 5. Check for errors
docker compose logs mai-api --tail=30 2>&1 | grep -i error
docker compose logs mai-gui --tail=30 2>&1 | grep -i error
# Expected: No critical errors
```

---

## Technical Notes

- Pydantic AI supports multimodal via `ImageUrl(url=...)` and `BinaryContent(data=..., media_type=...)`
- Gradio's `gr.Image` component with `type="filepath"` returns a temporary file path
- Base64 encoding is used to send images to the API
- Not all LM Studio models support vision - user needs a multimodal model like LLaVA
- Image size should be reasonable (< 5MB recommended)
- The Chatbot component can display images in messages using the content list format

**References**:
- [Pydantic AI Multimodal Input](https://ai.pydantic.dev/input)
- [Gradio Chatbot Docs](https://www.gradio.app/docs/gradio/chatbot)
- [Gradio Image Docs](https://www.gradio.app/docs/gradio/image)

---

## On Completion

1. Mark Archon task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/e25baf24-cc1d-4e86-8124-2fbadf43c7da" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Proceed to: `04-document-upload.md`
