from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result, _parse_message_headers, _decode_body

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    thread_id: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Fetch a full Gmail thread with all messages.

    Args:
        user_id: Gmail user ID
        thread_id: The thread ID to fetch

    Returns:
        Full thread with all messages, headers, and bodies.
    """
    if not thread_id:
        return _error_result("gmail_fetch_thread", "thread_id is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        thread = await gmail.get_thread(user_id, thread_id, fmt="full")
        messages = []
        for msg in thread.get("messages", []):
            payload = msg.get("payload", {})
            headers = _parse_message_headers(payload.get("headers", []))
            body = _decode_body(payload)
            messages.append({
                "id": msg["id"],
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body": body[:3000],
                "bodyTruncated": len(body) > 3000,
                "labelIds": msg.get("labelIds", []),
            })
        first_headers = _parse_message_headers(
            thread["messages"][0].get("payload", {}).get("headers", [])
            if thread.get("messages") else []
        )
        result = {
            "id": thread["id"],
            "subject": first_headers.get("subject", ""),
            "messages": messages,
            "message_count": len(messages),
        }
        logger.info("Fetched Gmail thread", thread_id=thread_id,
                    message_count=len(messages))
        return _safe_result("gmail_fetch_thread", result)
    except Exception as e:
        logger.error("gmail_fetch_thread failed", error=str(e))
        return _error_result("gmail_fetch_thread", str(e))
