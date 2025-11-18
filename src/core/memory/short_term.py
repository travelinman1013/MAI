from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from pydantic import ValidationError, TypeAdapter

from src.core.memory.models import Message
from src.infrastructure.cache.redis_client import RedisClient
from src.core.utils.logging import logger

# Token counting approximation
# A common heuristic is 4 characters per token or 1.33 words per token.
# For simplicity, we'll use a character-based approximation for now.
# This will need to be replaced with a proper tokenizer for accuracy.
APPROX_CHARS_PER_TOKEN = 4

class ConversationMemory:
    REDIS_KEY_PREFIX = "conversation_memory:"

    def __init__(self, session_id: str, redis: RedisClient):
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string.")
        if not isinstance(redis, RedisClient):
            raise TypeError("redis must be an instance of RedisClient.")

        self.session_id = session_id
        self.redis = redis
        self.messages: List[Message] = []
        self._message_adapter = TypeAdapter(List[Message])

    def _get_redis_key(self) -> str:
        return f"{self.REDIS_KEY_PREFIX}{self.session_id}"

    async def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        if not isinstance(role, str) or not role:
            raise ValueError("role must be a non-empty string.")
        if not isinstance(content, str) or not content:
            raise ValueError("content must be a non-empty string.")

        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        await self.save_to_redis()
        logger.debug(f"Message added to session {self.session_id}: {message.model_dump_json()}")

    def get_messages(self, last_n_messages: Optional[int] = None) -> List[Message]:
        if last_n_messages is None:
            return self.messages[:]
        return self.messages[-last_n_messages:] if last_n_messages > 0 else []

    def get_context_string(self, format: str = "default", last_n_messages: Optional[int] = None) -> str:
        messages_to_format = self.get_messages(last_n_messages)
        if not messages_to_format:
            return ""

        context_parts = []
        if format == "default":
            for msg in messages_to_format:
                context_parts.append(f"{msg.role}: {msg.content}")
            return "\n".join(context_parts)
        elif format == "chat":
            # For a chat-like format, often just role and content are needed
            for msg in messages_to_format:
                context_parts.append(f"<{msg.role}>{msg.content}</{msg.role}>")
            return "\n".join(context_parts)
        elif format == "xml":
            # Simple XML format for LLM input
            for msg in messages_to_format:
                # Escape content for XML safety
                escaped_content = msg.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                context_parts.append(
                    f"<{msg.role}>\n  {escaped_content}\n</{msg.role}>"
                )
            return "\n".join(context_parts)
        else:
            logger.warning(f"Unsupported context string format: {format}. Using default.")
            return self.get_context_string(format="default", last_n_messages=last_n_messages)

    def count_tokens(self) -> int:
        total_chars = sum(len(msg.role) + len(msg.content) for msg in self.messages)
        return total_chars // APPROX_CHARS_PER_TOKEN

    def truncate_to_fit(self, max_tokens: int):
        if max_tokens <= 0:
            self.messages = []
            logger.warning("max_tokens is non-positive, memory truncated to empty.")
            return

        current_tokens = self.count_tokens()
        if current_tokens <= max_tokens:
            return # No truncation needed

        logger.debug(f"Truncating memory for session {self.session_id}: current tokens {current_tokens}, max tokens {max_tokens}")

        # Simple sliding window: remove oldest messages until it fits
        # This is a basic approximation. A more sophisticated approach might summarize or prioritize.
        truncated_messages: List[Message] = []
        token_count = 0
        
        # Iterate from the newest message backwards to prioritize recent context
        for msg in reversed(self.messages):
            msg_token_cost = (len(msg.role) + len(msg.content)) // APPROX_CHARS_PER_TOKEN
            if token_count + msg_token_cost <= max_tokens:
                truncated_messages.insert(0, msg) # Add to the beginning to maintain order
                token_count += msg_token_cost
            else:
                # If adding the message would exceed the limit, stop
                break
        
        self.messages = truncated_messages
        logger.debug(f"Memory truncated. New token count: {self.count_tokens()} with {len(self.messages)} messages.")


    async def save_to_redis(self):
        try:
            # Serialize the list of Message objects
            messages_json = self._message_adapter.dump_json(self.messages).decode('utf-8')
            await self.redis.set(self._get_redis_key(), messages_json)
            logger.debug(f"Conversation memory for session {self.session_id} saved to Redis.")
        except Exception as e:
            logger.error(f"Failed to save conversation memory to Redis for session {self.session_id}: {e}")

    async def load_from_redis(self):
        try:
            messages_json = await self.redis.get(self._get_redis_key())
            if messages_json:
                self.messages = self._message_adapter.validate_json(messages_json)
                logger.debug(f"Conversation memory for session {self.session_id} loaded from Redis. {len(self.messages)} messages.")
            else:
                self.messages = []
                logger.debug(f"No conversation memory found in Redis for session {self.session_id}.")
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.error(f"Failed to load or parse conversation memory from Redis for session {self.session_id}: {e}")
            self.messages = [] # Clear messages on error to prevent corrupted state
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading conversation memory for session {self.session_id}: {e}")
            self.messages = [] # Clear messages on error
