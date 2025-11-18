"""Logging and observability configuration using Loguru.

This module provides:
- Colored console output for development
- JSON file output for production
- Log rotation (500MB files, 10 days retention)
- Correlation ID support for request tracing
- Context binding helpers (agent name, user_id, etc.)
- FastAPI middleware integration
- Optional Sentry integration for error tracking
"""

import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# Context variables for request/execution tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
agent_name_var: ContextVar[Optional[str]] = ContextVar("agent_name", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def get_correlation_id() -> str:
    """Get or create correlation ID for current context.

    Returns:
        Correlation ID (UUID) for tracking related log entries.
    """
    corr_id = correlation_id_var.get()
    if corr_id is None:
        corr_id = str(uuid.uuid4())
        correlation_id_var.set(corr_id)
    return corr_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID to set.
    """
    correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)


def format_record(record: dict[str, Any]) -> str:
    """Format log record with context variables.

    Adds correlation_id, agent_name, and user_id to extra fields if available.

    Args:
        record: Log record dictionary.

    Returns:
        Formatted record string.
    """
    # Add context variables to extra
    corr_id = correlation_id_var.get()
    if corr_id:
        record["extra"]["correlation_id"] = corr_id

    agent = agent_name_var.get()
    if agent:
        record["extra"]["agent_name"] = agent

    user = user_id_var.get()
    if user:
        record["extra"]["user_id"] = user

    return record


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = True,
    rotation: str = "500 MB",
    retention: str = "10 days",
) -> None:
    """Configure Loguru logging.

    Args:
        log_level: Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files.
        enable_console: Enable colored console output.
        enable_file: Enable file output.
        enable_json: Enable JSON format for file output.
        rotation: Log rotation size/time (e.g., "500 MB", "1 day").
        retention: Log retention period (e.g., "10 days", "1 week").
    """
    # Remove default handler
    logger.remove()

    # Console handler (colored, human-readable)
    if enable_console:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "{extra}",
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # File handler (JSON format for production)
    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        if enable_json:
            # JSON format for structured logging
            logger.add(
                log_path / "app.json",
                format="{message}",
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="zip",
                serialize=True,  # Serialize to JSON
                backtrace=True,
                diagnose=True,
            )
        else:
            # Plain text format
            logger.add(
                log_path / "app.log",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message} | "
                "{extra}",
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True,
            )

        # Separate error log file
        logger.add(
            log_path / "error.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message} | "
            "{extra}",
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
        )


def get_logger_with_context(
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
    **extra: Any,
) -> Any:
    """Get logger with bound context.

    Args:
        agent_name: Agent name to bind to logger.
        user_id: User ID to bind to logger.
        **extra: Additional context to bind.

    Returns:
        Logger instance with bound context.
    """
    context: dict[str, Any] = {}

    # Add correlation ID
    corr_id = correlation_id_var.get()
    if corr_id:
        context["correlation_id"] = corr_id

    # Add agent name
    if agent_name:
        agent_name_var.set(agent_name)
        context["agent_name"] = agent_name

    # Add user ID
    if user_id:
        user_id_var.set(user_id)
        context["user_id"] = user_id

    # Add extra context
    context.update(extra)

    return logger.bind(**context)


def setup_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    traces_sample_rate: float = 0.1,
) -> None:
    """Configure Sentry error tracking.

    Args:
        dsn: Sentry DSN (Data Source Name).
        environment: Environment name (development, staging, production).
        traces_sample_rate: Sample rate for performance monitoring (0.0 to 1.0).
    """
    if not dsn:
        logger.info("Sentry DSN not provided, skipping Sentry integration")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.loguru import LoguruIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                LoguruIntegration(),
            ],
            # Send only ERROR and CRITICAL to Sentry
            before_send=lambda event, hint: (
                event if event.get("level") in ["error", "fatal"] else None
            ),
        )
        logger.info("Sentry integration enabled", environment=environment)
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry integration")
    except Exception as e:
        logger.error("Failed to initialize Sentry", error=str(e))


# Logging decorators
def log_execution(func_name: Optional[str] = None):
    """Decorator to log function execution.

    Args:
        func_name: Optional custom function name for logs.
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = func_name or func.__name__
            log = get_logger_with_context()
            log.debug(f"Executing {name}", args=args, kwargs=kwargs)
            try:
                result = await func(*args, **kwargs)
                log.debug(f"Completed {name}")
                return result
            except Exception as e:
                log.error(f"Error in {name}", error=str(e), exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = func_name or func.__name__
            log = get_logger_with_context()
            log.debug(f"Executing {name}", args=args, kwargs=kwargs)
            try:
                result = func(*args, **kwargs)
                log.debug(f"Completed {name}")
                return result
            except Exception as e:
                log.error(f"Error in {name}", error=str(e), exc_info=True)
                raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
