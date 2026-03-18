"""
Session Middleware for the Enterprise MCP Server.

Responsibilities:
1. Reads X-Session-Id header.
2. Loads session from Redis if present.
3. Refresh session TTL if valid.
4. Attaches session to request.state.session.
5. Adds X-Session-Id header to response.
"""

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

from app.infrastructure.cache.session_manager import session_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionMiddleware:
    """
    Session Middleware for the Enterprise MCP Server.
    
    Standard ASGI implementation.
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        # Paths to skip session processing
        self.skip_paths = {
            "/health/live",
            "/health/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        # 1. Skip logic for health/observability paths
        if path in self.skip_paths or path.startswith("/admin"):
            await self.app(scope, receive, send)
            return

        # 2. Extract headers for session lookup
        headers = dict(scope.get("headers", []))
        def get_header(name: str) -> str | None:
            name_bytes = name.lower().encode("latin-1")
            val = headers.get(name_bytes)
            return val.decode("latin-1") if val else None

        session_id = get_header("x-session-id")
        session = None

        if session_id:
            session = await session_manager.get_session(session_id)
            if session:
                await session_manager.refresh_ttl(session_id)
                logger.debug("Session loaded", session_id=session_id)
            else:
                logger.warning("Session expired or invalid", session_id=session_id)
                response = JSONResponse(
                    status_code=401,
                    content={
                        "code": "E_SESSION_EXPIRED",
                        "message": "Session has expired or is invalid.",
                    }
                )
                await response(scope, receive, send)
                return

        # Attach session to scope so dependencies can find it
        # We use a custom key in scope since FastAPI request.state reads from scope['state']
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["session"] = session

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add X-Session-Id header to response if session exists
                # We check the scope state which might have been updated by route handlers
                current_session = scope.get("state", {}).get("session")
                if current_session:
                    current_session_id = current_session.get("session_id")
                    if current_session_id:
                        headers_list = list(message.get("headers", []))
                        headers_list.append((b"x-session-id", current_session_id.encode("latin-1")))
                        message["headers"] = headers_list

            await send(message)

        await self.app(scope, receive, send_wrapper)

