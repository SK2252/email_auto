from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from app.infrastructure.external.gmail_client import sanitize_for_log
from ._helpers import _safe_result, _error_result, _parse_message_headers, _decode_body

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    message_id: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Fetch a full Gmail message by ID.

    Args:
        user_id: Gmail user ID (use "me" for authenticated user)
        message_id: The message ID to fetch

    Returns:
        Full message with headers, body, labels, and attachment info.
    """
    if not message_id:
        return _error_result("gmail_fetch_message", "message_id is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        msg = await gmail.get_message(user_id, message_id, fmt="full")
        payload = msg.get("payload", {})
        headers = _parse_message_headers(payload.get("headers", []))
        body = _decode_body(payload)
        attachments = []
        for part in payload.get("parts", []):
            filename = part.get("filename")
            if filename:
                attachments.append({
                    "filename": filename,
                    "mimeType": part.get("mimeType", ""),
                    "size": part.get("body", {}).get("size", 0),
                    "attachmentId": part.get("body", {}).get("attachmentId", ""),
                })
        result = {
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "labelIds": msg.get("labelIds", []),
            "snippet": msg.get("snippet", ""),
            "headers": headers,
            "body": body[:5000],
            "bodyTruncated": len(body) > 5000,
            "attachments": attachments,
            "internalDate": msg.get("internalDate"),
        }
        logger.info("Fetched Gmail message", message_id=message_id,
                    subject=sanitize_for_log(headers.get("subject", "")))
        return _safe_result("gmail_fetch_message", result)
    except Exception as e:
        logger.error("gmail_fetch_message failed", error=str(e))
        return _error_result("gmail_fetch_message", str(e))
