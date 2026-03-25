from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from app.infrastructure.external.gmail_client import sanitize_for_log
from ._helpers import _safe_result, _error_result, _parse_message_headers

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    max_results: int = 20,
    query: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    List Gmail messages with optional query filter.

    Args:
        user_id: Gmail user ID (use "me" for authenticated user)
        max_results: Maximum number of messages to return (default 20, max 500)
        query: Gmail search query (e.g., "is:unread", "from:boss@company.com")
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])

    Returns:
        List of message summaries with id, threadId, snippet, and headers.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        response = await gmail.list_messages(
            user_id, min(max_results, 500), query, label_ids
        )
        messages = response.get("messages", [])
        results = []
        for msg_ref in messages[:max_results]:
            msg = await gmail.get_message(user_id, msg_ref["id"], fmt="metadata")
            headers = _parse_message_headers(
                msg.get("payload", {}).get("headers", [])
            )
            results.append({
                "id": msg["id"],
                "threadId": msg.get("threadId"),
                "snippet": msg.get("snippet", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "labelIds": msg.get("labelIds", []),
            })
        logger.info("Listed Gmail messages",
                    count=len(results),
                    query=sanitize_for_log(query or ""))
        return _safe_result("gmail_list_messages",
                            {"messages": results, "count": len(results)})
    except Exception as e:
        logger.error("gmail_list_messages failed", error=str(e))
        return _error_result("gmail_list_messages", str(e))
