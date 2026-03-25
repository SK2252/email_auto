"""
Shared helper utilities for all email tools.
Extracted from app.domains.email_ai.tools_email — do not import from there.
"""

import base64
from typing import Any, Dict


def _safe_result(func_name: str, result: Any) -> Dict[str, Any]:
    """Wrap a successful result with status metadata."""
    return {"status": "OK", "tool": func_name, "data": result}


def _error_result(func_name: str, error: str) -> Dict[str, Any]:
    """Wrap an error with status metadata."""
    return {"status": "ERROR", "tool": func_name, "error": error}


def _parse_message_headers(headers: list) -> Dict[str, str]:
    """Extract From, To, Subject, Date, CC, BCC from message headers."""
    result = {}
    for h in headers:
        name = h.get("name", "").lower()
        if name in ("from", "to", "subject", "date", "cc", "bcc"):
            result[name] = h.get("value", "")
    return result


def _decode_body(payload: dict) -> str:
    """Decode email body from base64url encoding. Handles multipart."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(
            payload["body"]["data"]
        ).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                part["body"]["data"]
            ).decode("utf-8", errors="replace")

    for part in parts:
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                part["body"]["data"]
            ).decode("utf-8", errors="replace")

    for part in parts:
        if part.get("parts"):
            result = _decode_body(part)
            if result:
                return result

    return ""
