"""
Request/response logging middleware.

Logs structured information about every incoming request and outgoing response,
including method, path, status code, duration, and client IP. Uses structlog
for JSON-formatted output suitable for production log aggregation.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("codelens.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request and response.

    Attaches a unique request ID to each request for tracing,
    measures the processing duration, and logs the result with
    structured fields.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate a unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        logger.info(
            "request_started",
            request_id=request_id,
            method=method,
            path=path,
            query=query,
            client_ip=client_ip,
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                "request_completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Add request ID to response headers for client-side tracing
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "request_failed",
                request_id=request_id,
                method=method,
                path=path,
                duration_ms=duration_ms,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
