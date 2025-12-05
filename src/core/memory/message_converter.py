"""
Message format converter for pydantic-ai compatibility.

Converts between:
- MAI's simple Message format (for Redis storage)
- pydantic-ai's ModelMessage format (ModelRequest, ModelResponse)
"""

from datetime import datetime
from typing import List, Sequence

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    SystemPromptPart,
    ModelMessagesTypeAdapter,
)

from src.core.memory.models import Message


def messages_to_model_messages(
    messages: List[Message],
    system_prompt: str | None = None,
) -> List[ModelMessage]:
    """
    Convert MAI Message list to pydantic-ai ModelMessage list.

    Args:
        messages: List of MAI Message objects
        system_prompt: Optional system prompt to include in first request

    Returns:
        List of ModelMessage objects suitable for message_history parameter
    """
    if not messages:
        return []

    model_messages: List[ModelMessage] = []

    for i, msg in enumerate(messages):
        if msg.role == "user":
            parts = []
            # Add system prompt to first user message only
            if i == 0 and system_prompt:
                parts.append(SystemPromptPart(content=system_prompt))
            parts.append(UserPromptPart(content=msg.content, timestamp=msg.timestamp))
            model_messages.append(ModelRequest(parts=parts))

        elif msg.role == "assistant":
            model_messages.append(
                ModelResponse(
                    parts=[TextPart(content=msg.content)],
                    model_name=msg.metadata.get("model_name"),
                )
            )

    return model_messages


def model_messages_to_messages(
    model_messages: Sequence[ModelMessage],
) -> List[Message]:
    """
    Convert pydantic-ai ModelMessage list back to MAI Message format.

    Used for storing conversation history after agent runs.

    Args:
        model_messages: Sequence of ModelMessage from agent result

    Returns:
        List of MAI Message objects for Redis storage
    """
    messages: List[Message] = []

    for model_msg in model_messages:
        if isinstance(model_msg, ModelRequest):
            for part in model_msg.parts:
                if isinstance(part, UserPromptPart):
                    messages.append(
                        Message(
                            role="user",
                            content=part.content
                            if isinstance(part.content, str)
                            else str(part.content),
                            timestamp=part.timestamp or datetime.utcnow(),
                        )
                    )
                # Skip SystemPromptPart - not stored in conversation

        elif isinstance(model_msg, ModelResponse):
            content_parts = []
            for part in model_msg.parts:
                if isinstance(part, TextPart):
                    content_parts.append(part.content)

            if content_parts:
                messages.append(
                    Message(
                        role="assistant",
                        content="".join(content_parts),
                        timestamp=datetime.utcnow(),
                        metadata=(
                            {"model_name": model_msg.model_name}
                            if model_msg.model_name
                            else {}
                        ),
                    )
                )

    return messages


def serialize_model_messages(messages: Sequence[ModelMessage]) -> str:
    """Serialize ModelMessages to JSON string for Redis storage."""
    return ModelMessagesTypeAdapter.dump_json(list(messages)).decode("utf-8")


def deserialize_model_messages(json_str: str) -> List[ModelMessage]:
    """Deserialize JSON string back to ModelMessages."""
    return list(ModelMessagesTypeAdapter.validate_json(json_str))
