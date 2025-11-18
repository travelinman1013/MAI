"""FastAPI middleware for request logging with correlation ID support."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.utils.logging import (
    clear_correlation_id,
    get_logger_with_context,
    set_correlation_id,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    Features:
    - Automatic correlation ID generation/propagation
    - Request/response timing
    - Status code logging
    - Exception logging
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/route handler.

        Returns:
            HTTP response.
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        set_correlation_id(correlation_id)

        # Get logger with correlation ID
        log = get_logger_with_context()

        # Log request
        start_time = time.time()
        log.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            log.info(
                f"Request completed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            log.error(
                f"Request failed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                exc_info=True,
            )
            raise

        finally:
            # Clear correlation ID from context
            clear_correlation_id()
