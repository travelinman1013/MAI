from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from pydantic import ValidationError, TypeAdapter
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from src.core.memory.models import Message
from src.core.memory.message_converter import messages_to_model_messages, model_messages_to_messages
from src.core.memory.context_manager import ContextWindowManager, count_tokens
from src.infrastructure.cache.redis_client import RedisClient
from src.core.utils.logging import logger

# Token counting approximation
# A common heuristic is 4 characters per token or 1.33 words per token.
# For simplicity, we'll use a character-based approximation for now.
# This will need to be replaced with a proper tokenizer for accuracy.
APPROX_CHARS_PER_TOKEN = 4

class ConversationMemory:
    REDIS_KEY_PREFIX = "conversation_memory:"
    REDIS_MODEL_KEY_PREFIX = "conversation_memory:model:"

    def __init__(self, session_id: str, redis: RedisClient):
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string.")
        if not isinstance(redis, RedisClient):
            raise TypeError("redis must be an instance of RedisClient.")

        self.session_id = session_id
        self.redis = redis
        self.messages: List[Message] = []
        self.model_messages: List[ModelMessage] = []
        self._message_adapter = TypeAdapter(List[Message])

    def _get_redis_key(self) -> str:
        return f"{self.REDIS_KEY_PREFIX}{self.session_id}"

    def _get_model_redis_key(self) -> str:
        return f"{self.REDIS_MODEL_KEY_PREFIX}{self.session_id}"

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

    async def add_model_messages(self, model_messages: List[ModelMessage]):
        """
        Add pydantic-ai ModelMessage objects from agent result.

        This stores the native pydantic-ai format for reuse in agent.run().
        Note: add_message() should be called separately to populate the simple
        Message format for backwards compatibility. This method only handles
        the model_messages list to avoid duplicates.

        Args:
            model_messages: List of ModelMessage from agent result
        """
        self.model_messages.extend(model_messages)
        await self.save_to_redis()
        logger.debug(f"Added {len(model_messages)} model messages to session {self.session_id}")

    def get_model_messages(self, system_prompt: Optional[str] = None) -> List[ModelMessage]:
        """
        Get conversation history in pydantic-ai ModelMessage format.

        This is used for the message_history parameter in agent.run().

        Args:
            system_prompt: Optional system prompt to include in first request

        Returns:
            List of ModelMessage objects suitable for agent.run()
        """
        if self.model_messages:
            return self.model_messages[:]
        # Fallback: convert from simple Message format if model_messages not available
        return messages_to_model_messages(self.messages, system_prompt=system_prompt)

    def get_model_messages_with_limit(
        self,
        model_name: str,
        system_prompt: Optional[str] = None,
        reserve_tokens: int = 1000,
    ) -> List[ModelMessage]:
        """
        Get conversation history with automatic truncation to fit model context limits.

        Uses ContextWindowManager to ensure messages fit within the model's context window
        using a sliding window approach that preserves system prompts and recent messages.

        Args:
            model_name: Name of the model (e.g., "gpt-4", "claude-3-sonnet")
            system_prompt: Optional system prompt to include in first request
            reserve_tokens: Tokens to reserve for completion (default: 1000)

        Returns:
            List of ModelMessage objects truncated to fit within model context limits
        """
        # Get full message history
        messages = self.get_model_messages(system_prompt=system_prompt)

        # Create context manager for the specific model
        context_mgr = ContextWindowManager.for_model(
            model_name=model_name,
            reserve_tokens=reserve_tokens,
        )

        # Get stats before truncation
        stats_before = context_mgr.get_context_stats(messages)
        logger.debug(
            f"Context stats for session {self.session_id} before truncation: "
            f"{stats_before['total_tokens']}/{stats_before['max_history_tokens']} tokens, "
            f"{stats_before['num_messages']} messages"
        )

        # Fit messages to context window
        fitted_messages = context_mgr.fit_messages(messages, keep_system_prompts=True)

        # Get stats after truncation
        stats_after = context_mgr.get_context_stats(fitted_messages)
        logger.debug(
            f"Context stats for session {self.session_id} after truncation: "
            f"{stats_after['total_tokens']}/{stats_after['max_history_tokens']} tokens, "
            f"{stats_after['num_messages']} messages, "
            f"{stats_after['utilization_percent']}% utilization"
        )

        return fitted_messages

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

            # Serialize ModelMessage objects if present
            if self.model_messages:
                model_messages_json = ModelMessagesTypeAdapter.dump_json(self.model_messages).decode('utf-8')
                await self.redis.set(self._get_model_redis_key(), model_messages_json)

            logger.debug(f"Conversation memory for session {self.session_id} saved to Redis.")
        except Exception as e:
            logger.error(f"Failed to save conversation memory to Redis for session {self.session_id}: {e}")

    async def load_from_redis(self):
        try:
            # Load simple Message format
            messages_data = await self.redis.get(self._get_redis_key())
            if messages_data:
                # RedisClient.get() returns deserialized Python objects if JSON is valid
                # So messages_data could be either a string (JSON) or a list (already parsed)
                if isinstance(messages_data, str):
                    self.messages = self._message_adapter.validate_json(messages_data)
                elif isinstance(messages_data, list):
                    self.messages = self._message_adapter.validate_python(messages_data)
                else:
                    logger.warning(f"Unexpected data type from Redis for session {self.session_id}: {type(messages_data)}")
                    self.messages = []
                logger.debug(f"Conversation memory for session {self.session_id} loaded from Redis. {len(self.messages)} messages.")
            else:
                self.messages = []
                logger.debug(f"No conversation memory found in Redis for session {self.session_id}.")

            # Load ModelMessage format if available
            model_messages_data = await self.redis.get(self._get_model_redis_key())
            if model_messages_data:
                if isinstance(model_messages_data, str):
                    self.model_messages = list(ModelMessagesTypeAdapter.validate_json(model_messages_data))
                elif isinstance(model_messages_data, list):
                    self.model_messages = list(ModelMessagesTypeAdapter.validate_python(model_messages_data))
                else:
                    logger.warning(f"Unexpected model messages data type from Redis for session {self.session_id}: {type(model_messages_data)}")
                    self.model_messages = []
                logger.debug(f"Loaded {len(self.model_messages)} model messages for session {self.session_id}.")
            else:
                self.model_messages = []

        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.error(f"Failed to load or parse conversation memory from Redis for session {self.session_id}: {e}")
            self.messages = []  # Clear messages on error to prevent corrupted state
            self.model_messages = []
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading conversation memory for session {self.session_id}: {e}")
            self.messages = []  # Clear messages on error
            self.model_messages = []

    async def clear(self):
        """
        Clear all conversation memory for this session.

        Clears both simple Message format and ModelMessage format from memory
        and Redis storage.
        """
        self.messages = []
        self.model_messages = []
        try:
            await self.redis.delete(self._get_redis_key())
            await self.redis.delete(self._get_model_redis_key())
            logger.debug(f"Conversation memory cleared for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to clear conversation memory from Redis for session {self.session_id}: {e}")
