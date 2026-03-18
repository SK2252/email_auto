"""
Global Error Handler Middleware.

Catches all unhandled exceptions and returns a standardized JSON error
response with the request's correlation/request IDs for traceability.
"""

import traceback

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

from app.core.logging import get_logger
from app.utils.correlation_id import get_correlation_id, get_request_id
from app.core.exceptions import ErrorCode, get_error_message

logger = get_logger(__name__)


class ErrorHandlerMiddleware:
    """
    Catches unhandled exceptions → returns standardized JSON error response.
    
    Standard ASGI implementation.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except ValueError as e:
            response = self._build_error_response(
                status_code=400,
                code=ErrorCode.MCP_INVALID_PARAMS,
                detail=str(e),
            )
            await response(scope, receive, send)
        except PermissionError as e:
            response = self._build_error_response(
                status_code=403,
                code=ErrorCode.AUTHZ_INSUFFICIENT_SCOPE,
                detail=str(e),
            )
            await response(scope, receive, send)
        except FileNotFoundError as e:
            response = self._build_error_response(
                status_code=404,
                code=ErrorCode.TOOL_FILE_NOT_FOUND,
                detail=str(e),
            )
            await response(scope, receive, send)
        except Exception as e:
            logger.error(
                "Unhandled exception",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            response = self._build_error_response(
                status_code=500,
                code=ErrorCode.TOOL_EXECUTION_FAILED,
                detail=str(e),
            )
            try:
                await response(scope, receive, send)
            except Exception:
                # If we fail to send the error response (e.g. response already started),
                # just re-raise or log. In ASGI, if start was already sent, we can't send again.
                logger.error("Failed to send 500 error response — likely already started")
                raise

    def _build_error_response(
        self,
        status_code: int,
        code: str,
        detail: str | None = None,
    ) -> JSONResponse:
        body: dict = {
            "error": {
                "code": code,
                "message": get_error_message(code),
            },
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
        }

        # Include detail only in non-production environments
        if detail:
            from app.core.config import settings

            if not settings.is_production:
                body["error"]["detail"] = detail

        return JSONResponse(status_code=status_code, content=body)

