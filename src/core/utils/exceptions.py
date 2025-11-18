"""Custom exception hierarchy for MAI Framework.

This module defines a comprehensive exception hierarchy with:
- Base MAIException with error codes, messages, details
- Retryable flag for automatic retry logic
- Serialization support for API responses
- Specific exceptions for different framework components
"""

from typing import Any, Optional


class MAIException(Exception):
    """Base exception for MAI Framework.

    All custom exceptions inherit from this base class.

    Attributes:
        error_code: Unique error code for identification.
        message: Human-readable error message.
        details: Additional error details (dict, list, or any serializable data).
        retryable: Whether this error is retryable.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "MAI_ERROR",
        details: Optional[dict[str, Any]] = None,
        retryable: bool = False,
    ) -> None:
        """Initialize MAIException.

        Args:
            message: Error message.
            error_code: Unique error code.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to dictionary for API responses.

        Returns:
            Dictionary representation of the exception.
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "exception_type": self.__class__.__name__,
        }

    def __str__(self) -> str:
        """String representation of exception.

        Returns:
            Formatted error string.
        """
        details_str = f", details={self.details}" if self.details else ""
        return f"[{self.error_code}] {self.message}{details_str}"

    def __repr__(self) -> str:
        """Detailed representation of exception.

        Returns:
            Detailed error string.
        """
        return (
            f"{self.__class__.__name__}("
            f"error_code='{self.error_code}', "
            f"message='{self.message}', "
            f"details={self.details}, "
            f"retryable={self.retryable})"
        )


# Agent Execution Errors


class AgentExecutionError(MAIException):
    """Error during agent execution."""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize AgentExecutionError.

        Args:
            message: Error message.
            agent_name: Name of the agent that failed.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if agent_name:
            error_details["agent_name"] = agent_name
        super().__init__(
            message=message,
            error_code="AGENT_EXECUTION_ERROR",
            details=error_details,
            retryable=retryable,
        )


# Tool Execution Errors


class ToolExecutionError(MAIException):
    """Error during tool execution."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize ToolExecutionError.

        Args:
            message: Error message.
            tool_name: Name of the tool that failed.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if tool_name:
            error_details["tool_name"] = tool_name
        super().__init__(
            message=message,
            error_code="TOOL_EXECUTION_ERROR",
            details=error_details,
            retryable=retryable,
        )


# Configuration Errors


class ConfigurationError(MAIException):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ConfigurationError.

        Args:
            message: Error message.
            config_key: Configuration key that caused the error.
            details: Additional error details.
        """
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
            retryable=False,
        )


# Authentication & Authorization Errors


class AuthenticationError(MAIException):
    """Authentication error."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize AuthenticationError.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            retryable=False,
        )


class AuthorizationError(MAIException):
    """Authorization error."""

    def __init__(
        self,
        message: str = "Access denied",
        resource: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize AuthorizationError.

        Args:
            message: Error message.
            resource: Resource that was denied.
            details: Additional error details.
        """
        error_details = details or {}
        if resource:
            error_details["resource"] = resource
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
            retryable=False,
        )


# Validation Errors


class ValidationError(MAIException):
    """Data validation error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Error message.
            field: Field that failed validation.
            value: Invalid value.
            details: Additional error details.
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            retryable=False,
        )


# Memory Errors


class MemoryError(MAIException):
    """Memory system error."""

    def __init__(
        self,
        message: str,
        memory_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize MemoryError.

        Args:
            message: Error message.
            memory_type: Type of memory (short_term, long_term, semantic).
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if memory_type:
            error_details["memory_type"] = memory_type
        super().__init__(
            message=message,
            error_code="MEMORY_ERROR",
            details=error_details,
            retryable=retryable,
        )


# Model Errors


class ModelError(MAIException):
    """LLM model error."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize ModelError.

        Args:
            message: Error message.
            model_name: Name of the model.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if model_name:
            error_details["model_name"] = model_name
        super().__init__(
            message=message,
            error_code="MODEL_ERROR",
            details=error_details,
            retryable=retryable,
        )


# Pipeline Errors


class PipelineError(MAIException):
    """Pipeline execution error."""

    def __init__(
        self,
        message: str,
        pipeline_name: Optional[str] = None,
        stage: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize PipelineError.

        Args:
            message: Error message.
            pipeline_name: Name of the pipeline.
            stage: Pipeline stage that failed.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if pipeline_name:
            error_details["pipeline_name"] = pipeline_name
        if stage:
            error_details["stage"] = stage
        super().__init__(
            message=message,
            error_code="PIPELINE_ERROR",
            details=error_details,
            retryable=retryable,
        )


# Resource Errors


class ResourceNotFoundError(MAIException):
    """Resource not found error."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ResourceNotFoundError.

        Args:
            message: Error message.
            resource_type: Type of resource (agent, tool, memory, etc.).
            resource_id: Resource identifier.
            details: Additional error details.
        """
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=error_details,
            retryable=False,
        )


# Timeout Errors


class TimeoutError(MAIException):
    """Operation timeout error."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = True,
    ) -> None:
        """Initialize TimeoutError.

        Args:
            message: Error message.
            timeout_seconds: Timeout duration that was exceeded.
            details: Additional error details.
            retryable: Whether operation can be retried.
        """
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=error_details,
            retryable=retryable,
        )


class ToolTimeoutError(TimeoutError):
    """Specific error for when a tool execution times out."""

    def __init__(
        self,
        message: str = "Tool execution timed out",
        tool_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ToolTimeoutError.

        Args:
            message: Error message.
            tool_name: Name of the tool that timed out.
            timeout_seconds: Timeout duration that was exceeded.
            details: Additional error details.
        """
        error_details = details or {}
        if tool_name:
            error_details["tool_name"] = tool_name
        super().__init__(
            message=message,
            timeout_seconds=timeout_seconds,
            details=error_details,
        )


# Rate Limit Errors


class RateLimitError(MAIException):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize RateLimitError.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
            details: Additional error details.
        """
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
            retryable=True,
        )


class RateLimitExceededError(RateLimitError):
    """Specific error for when a tool's rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Tool rate limit exceeded",
        tool_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize RateLimitExceededError.

        Args:
            message: Error message.
            tool_name: Name of the tool whose rate limit was exceeded.
            retry_after: Seconds to wait before retrying.
            details: Additional error details.
        """
        error_details = details or {}
        if tool_name:
            error_details["tool_name"] = tool_name
        super().__init__(
            message=message,
            retry_after=retry_after,
            details=error_details,
        )
