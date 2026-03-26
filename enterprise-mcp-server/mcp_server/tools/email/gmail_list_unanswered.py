from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result, _parse_message_headers

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    max_results: int = 20,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Find threads where you received a message but haven't replied.

    Args:
        user_id: Gmail user ID
        max_results: Maximum results

    Returns:
        List of unanswered threads with last sender info.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        profile = await gmail.get_profile(user_id)
        my_email = profile.get("emailAddress", "")
        response = await gmail.list_threads(user_id, 50, "in:inbox category:primary")
        threads = response.get("threads", [])
        unanswered = []
        for t in threads:
            if len(unanswered) >= max_results:
                break
            thread = await gmail.get_thread(user_id, t["id"], fmt="metadata")
            msgs = thread.get("messages", [])
            if not msgs:
                continue
            last_headers = _parse_message_headers(
                msgs[-1].get("payload", {}).get("headers", [])
            )
            last_from = last_headers.get("from", "")
            if my_email.lower() not in last_from.lower():
                first_headers = _parse_message_headers(
                    msgs[0].get("payload", {}).get("headers", [])
                )
                unanswered.append({
                    "thread_id": thread["id"],
                    "subject": first_headers.get("subject", ""),
                    "last_sender": last_from,
                    "last_date": last_headers.get("date", ""),
                    "message_count": len(msgs),
                })
        logger.info("Found unanswered threads", count=len(unanswered))
        return _safe_result("gmail_list_unanswered",
                            {"threads": unanswered, "count": len(unanswered)})
    except Exception as e:
        logger.error("gmail_list_unanswered failed", error=str(e))
        return _error_result("gmail_list_unanswered", str(e))
