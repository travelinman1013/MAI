"""
History processors for optimizing conversation context.

Provides various processors to limit, filter, and transform message history
before sending to LLMs to stay within context windows and improve relevance.
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Set
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse

from src.core.memory.context_manager import ContextWindowManager


# Type alias for history processor functions
HistoryProcessor = Callable[[List[ModelMessage]], List[ModelMessage]]


class BaseHistoryProcessor(ABC):
    """Abstract base class for message history processors."""

    @abstractmethod
    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """
        Process message history and return filtered/transformed version.

        Args:
            messages: List of model messages to process

        Returns:
            Processed list of model messages
        """
        pass

    def __call__(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Allow processor to be called as a function."""
        return self.process(messages)


class RecencyProcessor(BaseHistoryProcessor):
    """Keeps only the most recent N conversation turns."""

    def __init__(self, max_turns: int = 10):
        """
        Initialize recency processor.

        Args:
            max_turns: Maximum number of conversation turns to keep.
                      One turn = user message + assistant response.
        """
        self.max_turns = max_turns

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Keep only the most recent N turns."""
        if not messages:
            return messages

        # Each turn is typically 2 messages (user + assistant)
        max_messages = self.max_turns * 2

        if len(messages) <= max_messages:
            return messages

        # Keep the most recent messages
        return messages[-max_messages:]


class TokenLimitProcessor(BaseHistoryProcessor):
    """Limits message history by total token count."""

    def __init__(self, max_tokens: int = 2000, model_name: str = "default"):
        """
        Initialize token limit processor.

        Args:
            max_tokens: Maximum total tokens allowed in history
            model_name: Model name for token counting (default, gpt-4, etc.)
        """
        self.max_tokens = max_tokens
        self.model_name = model_name

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Keep messages within token limit, removing oldest first."""
        if not messages:
            return messages

        # Create a context manager for token counting
        context_manager = ContextWindowManager.for_model(
            model_name=self.model_name,
            reserve_tokens=0,  # No need to reserve for counting
        )

        # Count tokens for all messages
        total_tokens = context_manager.count_tokens(messages)

        if total_tokens <= self.max_tokens:
            return messages

        # Remove oldest messages until we're under the limit
        result = messages.copy()
        while result and context_manager.count_tokens(result) > self.max_tokens:
            # Remove from the beginning (oldest messages)
            result.pop(0)

        return result


class ImportantMessageProcessor(BaseHistoryProcessor):
    """
    Marks or preserves messages containing important keywords.

    This is a simple keyword-based implementation. In the future, this could
    use embeddings or other ML techniques to identify important messages.
    """

    def __init__(
        self,
        important_keywords: Optional[Set[str]] = None,
        preserve_important: bool = True,
    ):
        """
        Initialize important message processor.

        Args:
            important_keywords: Set of keywords that mark a message as important
            preserve_important: If True, always keep messages with keywords
        """
        self.important_keywords = important_keywords or {
            "error",
            "important",
            "critical",
            "warning",
            "remember",
            "note",
            "todo",
            "bug",
            "issue",
        }
        self.preserve_important = preserve_important

    def _is_important(self, message: ModelMessage) -> bool:
        """Check if a message contains important keywords."""
        # Extract text content from message
        content = ""
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if hasattr(part, "content"):
                    content += str(part.content).lower()
        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if hasattr(part, "content"):
                    content += str(part.content).lower()

        # Check for keywords
        return any(keyword in content for keyword in self.important_keywords)

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """
        Process messages, potentially marking important ones.

        For now, this just returns all messages unchanged.
        Future versions could add metadata or reorder messages.
        """
        # This is a placeholder - could be extended to:
        # 1. Add metadata to important messages
        # 2. Reorder to keep important messages
        # 3. Create a summary of important points
        return messages


class ChainedProcessor(BaseHistoryProcessor):
    """Chains multiple processors together in sequence."""

    def __init__(self, processors: List[BaseHistoryProcessor]):
        """
        Initialize chained processor.

        Args:
            processors: List of processors to apply in order
        """
        self.processors = processors

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Apply all processors in sequence."""
        result = messages
        for processor in self.processors:
            result = processor.process(result)
        return result


class SummaryProcessor(BaseHistoryProcessor):
    """
    Placeholder for future summarization processor.

    This would use an LLM to summarize old messages into a compact form,
    preserving key information while reducing token count.
    """

    def __init__(self, summary_threshold: int = 20):
        """
        Initialize summary processor.

        Args:
            summary_threshold: Number of messages before summarization kicks in
        """
        self.summary_threshold = summary_threshold

    def process(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """
        Placeholder for summarization logic.

        Future implementation would:
        1. Identify old messages beyond threshold
        2. Use LLM to create compact summary
        3. Replace old messages with summary
        4. Keep recent messages intact
        """
        # For now, just return messages unchanged
        # TODO: Implement actual summarization with LLM
        return messages


# Factory functions and convenience helpers


def create_default_processor(
    max_turns: Optional[int] = None,
    max_tokens: Optional[int] = None,
    model_name: str = "default",
) -> HistoryProcessor:
    """
    Create a default processor chain with common settings.

    Args:
        max_turns: Maximum conversation turns (default: 10)
        max_tokens: Maximum total tokens (default: 2000)
        model_name: Model name for token counting

    Returns:
        Chained processor with recency and token limits
    """
    processors = []

    if max_turns is not None:
        processors.append(RecencyProcessor(max_turns=max_turns))

    if max_tokens is not None:
        processors.append(TokenLimitProcessor(max_tokens=max_tokens, model_name=model_name))

    if not processors:
        # Default settings if nothing specified
        processors = [
            RecencyProcessor(max_turns=10),
            TokenLimitProcessor(max_tokens=2000, model_name=model_name),
        ]

    if len(processors) == 1:
        return processors[0]

    return ChainedProcessor(processors)


def limit_by_turns(max_turns: int = 10) -> HistoryProcessor:
    """
    Convenience function to create a simple recency processor.

    Args:
        max_turns: Maximum conversation turns to keep

    Returns:
        RecencyProcessor instance
    """
    return RecencyProcessor(max_turns=max_turns)


def limit_by_tokens(max_tokens: int = 2000, model_name: str = "default") -> HistoryProcessor:
    """
    Convenience function to create a simple token limit processor.

    Args:
        max_tokens: Maximum total tokens allowed
        model_name: Model name for token counting

    Returns:
        TokenLimitProcessor instance
    """
    return TokenLimitProcessor(max_tokens=max_tokens, model_name=model_name)
