"""
Correlation ID Middleware.

Generates a unique request_id per request and propagates correlation_id
across the session. Binds all IDs to structlog for consistent logging.
"""

import time

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core import metrics
from app.utils.correlation_id import (
    get_context_dict,
    set_correlation_id,
    set_request_id,
    set_session_id,
)


class CorrelationIdMiddleware:
    """
    Injects correlation/request/session IDs into every request context.
    
    Standard ASGI middleware implementation for better performance and 
    compatibility with streaming/SSE.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        # Extract headers for ID setup
        headers = dict(scope.get("headers", []))
        # Convert byte headers to strings for utility functions
        def get_header(name: str) -> str | None:
            name_bytes = name.lower().encode("latin-1")
            val = headers.get(name_bytes)
            return val.decode("latin-1") if val else None

        # Set IDs from headers or generate new ones in contextvars
        correlation_id = set_correlation_id(get_header("x-correlation-id"))
        request_id = set_request_id()
        session_id = set_session_id(get_header("mcp-session-id"))

        # Bind all IDs to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**get_context_dict())

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add tracing headers to response
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-correlation-id", correlation_id.encode("latin-1")))
                headers_list.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers_list

                # Metrics for start of response
                status = message.get("status", 200)
                duration = time.perf_counter() - start_time
                metrics.http_request_duration_seconds.labels(
                    method=scope["method"],
                    endpoint=scope["path"],
                ).observe(duration)

                metrics.http_requests_total.labels(
                    method=scope["method"],
                    endpoint=scope["path"],
                    status=status,
                ).inc()

            await send(message)

        await self.app(scope, receive, send_wrapper)

