"""
Context Window Manager for Token Counting and Sliding Window Truncation.

Provides accurate token counting using tiktoken and smart message truncation
to keep conversations within model context limits.
"""

from typing import List, Dict, Optional, Literal
from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
    ToolReturnPart,
    ToolCallPart,
    RetryPromptPart,
)

from src.core.utils.logging import logger

# Model context limits (in tokens)
# These are conservative estimates to leave room for system prompts and overhead
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # OpenAI models
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    # Anthropic models
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    # Google models
    "gemini-pro": 32760,
    "gemini-1.5-pro": 1048576,
    "gemini-1.5-flash": 1048576,
    # Open source models (common sizes)
    "llama-2-7b": 4096,
    "llama-2-13b": 4096,
    "llama-2-70b": 4096,
    "llama-3-8b": 8192,
    "llama-3-70b": 8192,
    "mistral-7b": 8192,
    "mixtral-8x7b": 32768,
    "gemma": 8192,
    "phi-3": 4096,
    # Default fallback
    "default": 4096,
}


@dataclass
class TokenCounter:
    """
    Token counter with tiktoken support and character-based fallback.

    Uses tiktoken for accurate token counting when available, falls back to
    character-based estimation (4 chars per token) if tiktoken is not installed.
    """

    encoding_name: str = "cl100k_base"  # Used by GPT-4, GPT-3.5-turbo, text-embedding-ada-002

    def __post_init__(self) -> None:
        """Initialize tiktoken encoder if available."""
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding(self.encoding_name)
            self._use_tiktoken = True
            logger.debug(f"TokenCounter initialized with tiktoken encoding: {self.encoding_name}")
        except ImportError:
            self._encoder = None
            self._use_tiktoken = False
            logger.warning("tiktoken not available, using character-based token estimation")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens in the text
        """
        if self._use_tiktoken and self._encoder:
            return len(self._encoder.encode(text))
        else:
            # Fallback: 4 characters per token approximation
            return max(1, len(text) // 4)

    def count_message_tokens(self, message: ModelMessage) -> int:
        """
        Count tokens in a pydantic-ai ModelMessage.

        Args:
            message: The ModelMessage to count tokens for

        Returns:
            Number of tokens in the message
        """
        token_count = 0

        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    token_count += self.count_tokens(part.content)
                elif isinstance(part, SystemPromptPart):
                    token_count += self.count_tokens(part.content)
                elif isinstance(part, RetryPromptPart):
                    token_count += self.count_tokens(part.content)
                elif isinstance(part, ToolReturnPart):
                    # Tool returns can be complex, convert to string representation
                    token_count += self.count_tokens(str(part.content))

        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart):
                    token_count += self.count_tokens(part.content)
                elif isinstance(part, ToolCallPart):
                    # Tool calls have arguments that count as tokens
                    token_count += self.count_tokens(part.tool_name)
                    token_count += self.count_tokens(str(part.args))

        # Add small overhead for message structure (role, formatting, etc.)
        token_count += 4

        return token_count


class ContextWindowManager:
    """
    Manages context window size and performs sliding window truncation.

    Keeps conversation history within model context limits by intelligently
    truncating older messages while preserving system prompts and recent context.
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        reserve_tokens: int = 1000,
        encoding_name: str = "cl100k_base",
    ):
        """
        Initialize the context window manager.

        Args:
            max_tokens: Maximum number of tokens in context window
            reserve_tokens: Tokens to reserve for completion (not used by history)
            encoding_name: Tiktoken encoding to use for token counting
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.max_history_tokens = max_tokens - reserve_tokens
        self.counter = TokenCounter(encoding_name=encoding_name)

        logger.debug(
            f"ContextWindowManager initialized: "
            f"max_tokens={max_tokens}, reserve_tokens={reserve_tokens}, "
            f"max_history_tokens={self.max_history_tokens}"
        )

    @classmethod
    def for_model(
        cls,
        model_name: str,
        reserve_tokens: int = 1000,
        encoding_name: str = "cl100k_base",
    ) -> "ContextWindowManager":
        """
        Create a ContextWindowManager configured for a specific model.

        Args:
            model_name: Name of the model (e.g., "gpt-4", "claude-3-sonnet")
            reserve_tokens: Tokens to reserve for completion
            encoding_name: Tiktoken encoding to use

        Returns:
            Configured ContextWindowManager instance
        """
        # Try exact match first
        max_tokens = MODEL_CONTEXT_LIMITS.get(model_name)

        # If not found, try fuzzy matching
        if max_tokens is None:
            model_lower = model_name.lower()
            for key, value in MODEL_CONTEXT_LIMITS.items():
                if key in model_lower or model_lower in key:
                    max_tokens = value
                    logger.debug(f"Matched model '{model_name}' to '{key}' with {value} tokens")
                    break

        # Fall back to default if still not found
        if max_tokens is None:
            max_tokens = MODEL_CONTEXT_LIMITS["default"]
            logger.warning(
                f"Unknown model '{model_name}', using default context limit of {max_tokens} tokens"
            )

        return cls(
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens,
            encoding_name=encoding_name,
        )

    def count_tokens(self, messages: List[ModelMessage]) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of ModelMessage objects

        Returns:
            Total number of tokens
        """
        return sum(self.counter.count_message_tokens(msg) for msg in messages)

    def fit_messages(
        self,
        messages: List[ModelMessage],
        keep_system_prompts: bool = True,
    ) -> List[ModelMessage]:
        """
        Truncate messages to fit within context window using sliding window approach.

        Preserves system prompts (if requested) and keeps the most recent messages
        that fit within the token budget.

        Args:
            messages: List of ModelMessage objects to fit
            keep_system_prompts: Whether to preserve system prompts at the start

        Returns:
            Truncated list of messages that fit within max_history_tokens
        """
        if not messages:
            return []

        total_tokens = self.count_tokens(messages)

        # If everything fits, return as-is
        if total_tokens <= self.max_history_tokens:
            logger.debug(
                f"Messages fit within context: {total_tokens}/{self.max_history_tokens} tokens"
            )
            return messages

        logger.debug(
            f"Truncating messages: {total_tokens} tokens -> {self.max_history_tokens} tokens"
        )

        # Separate system prompts from other messages
        system_messages = []
        other_messages = []

        for msg in messages:
            if isinstance(msg, ModelRequest):
                # Check if this request contains a system prompt
                has_system = any(isinstance(part, SystemPromptPart) for part in msg.parts)
                if has_system and keep_system_prompts:
                    system_messages.append(msg)
                else:
                    other_messages.append(msg)
            else:
                other_messages.append(msg)

        # Calculate tokens used by system prompts
        system_tokens = self.count_tokens(system_messages) if keep_system_prompts else 0
        available_tokens = self.max_history_tokens - system_tokens

        if available_tokens <= 0:
            logger.warning(
                f"System prompts use {system_tokens} tokens, "
                f"exceeding max_history_tokens={self.max_history_tokens}"
            )
            return system_messages if keep_system_prompts else []

        # Sliding window: keep most recent messages that fit
        fitted_messages = []
        current_tokens = 0

        # Iterate from newest to oldest
        for msg in reversed(other_messages):
            msg_tokens = self.counter.count_message_tokens(msg)

            if current_tokens + msg_tokens <= available_tokens:
                fitted_messages.insert(0, msg)  # Prepend to maintain order
                current_tokens += msg_tokens
            else:
                # Stop when we can't fit more messages
                break

        # Combine system prompts + fitted messages
        result = system_messages + fitted_messages if keep_system_prompts else fitted_messages

        final_tokens = self.count_tokens(result)
        logger.debug(
            f"Truncation complete: kept {len(result)}/{len(messages)} messages, "
            f"{final_tokens}/{self.max_history_tokens} tokens"
        )

        return result

    def get_context_stats(self, messages: List[ModelMessage]) -> Dict[str, int]:
        """
        Get statistics about context window usage.

        Args:
            messages: List of ModelMessage objects

        Returns:
            Dictionary with token usage statistics
        """
        total_tokens = self.count_tokens(messages)

        return {
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "max_history_tokens": self.max_history_tokens,
            "reserve_tokens": self.reserve_tokens,
            "available_tokens": max(0, self.max_history_tokens - total_tokens),
            "utilization_percent": round((total_tokens / self.max_history_tokens) * 100, 2),
            "num_messages": len(messages),
        }


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Convenience function to count tokens in a text string.

    Args:
        text: The text to count tokens for
        encoding_name: Tiktoken encoding to use (default: cl100k_base for GPT-4)

    Returns:
        Number of tokens in the text
    """
    counter = TokenCounter(encoding_name=encoding_name)
    return counter.count_tokens(text)
