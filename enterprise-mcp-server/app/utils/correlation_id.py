"""
Correlation ID generation and propagation via Python contextvars.
Every request gets a unique request_id, and correlation_id persists across a session.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

# Context variables — automatically scoped to each async task
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_key_id: ContextVar[Optional[str]] = ContextVar("key_id", default=None)


def generate_id(prefix: str = "") -> str:
    """Generate a prefixed UUID4 string."""
    uid = str(uuid.uuid4())
    return f"{prefix}{uid}" if prefix else uid


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set or generate a correlation ID for the current context."""
    value = cid or generate_id("corr-")
    _correlation_id.set(value)
    return value


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def set_request_id(rid: Optional[str] = None) -> str:
    """Generate a new request ID for this request."""
    value = rid or generate_id("req-")
    _request_id.set(value)
    return value


def get_request_id() -> Optional[str]:
    return _request_id.get()


def set_session_id(sid: Optional[str] = None) -> str:
    value = sid or generate_id("sess-")
    _session_id.set(value)
    return value


def get_session_id() -> Optional[str]:
    return _session_id.get()


def set_key_id(kid: str) -> None:
    _key_id.set(kid)


def get_key_id() -> Optional[str]:
    return _key_id.get()


def get_context_dict() -> dict:
    """Return all current context IDs as a dict (for structlog binding)."""
    ctx = {}
    if (v := get_correlation_id()) is not None:
        ctx["correlation_id"] = v
    if (v := get_request_id()) is not None:
        ctx["request_id"] = v
    if (v := get_session_id()) is not None:
        ctx["session_id"] = v
    if (v := get_key_id()) is not None:
        ctx["key_id"] = v
    return ctx
