"""
Rate limiting middleware — SlowAPI wrapper.
Per-key limits from api_keys.rate_limit column.
Per-IP fallback for unauthenticated requests.
Redis backend for cross-pod consistency.
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _key_func(request: Request) -> str:
    """
    Rate limit key function.
    Uses API key (from header) if present, otherwise falls back to IP.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use first 12 chars as the key identifier (avoids leaking full key)
        return f"apikey:{api_key[:12]}"
    return f"ip:{get_remote_address(request)}"


def _build_redis_uri() -> str:
    """Construct Redis URI for SlowAPI storage."""
    auth = f":{settings.redis_password}@" if settings.redis_password else ""
    return f"redis://{auth}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


# Create limiter with Redis backend (falls back to in-memory if Redis unavailable)
try:
    limiter = Limiter(
        key_func=_key_func,
        default_limits=[settings.rate_limit_default],
        storage_uri=_build_redis_uri(),
        strategy="fixed-window",
    )
except Exception:
    # Fallback to in-memory if Redis is not available at import time
    limiter = Limiter(
        key_func=_key_func,
        default_limits=[settings.rate_limit_default],
        strategy="fixed-window",
    )
    logger.warning("Rate limiter using in-memory storage (Redis unavailable)")


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    logger.warning(
        "Rate limit exceeded",
        key=_key_func(request),
        limit=str(exc.detail),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "E_RATE_300",
                "message": f"Rate limit exceeded: {exc.detail}",
            },
            "request_id": request.state.request_id
            if hasattr(request.state, "request_id")
            else None,
        },
    )
