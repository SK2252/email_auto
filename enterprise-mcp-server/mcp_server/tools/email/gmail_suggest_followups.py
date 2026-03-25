from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result, _parse_message_headers

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    thread_ids: Optional[List[str]] = None,
    max_results: int = 10,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Identify threads that need follow-up action.

    Args:
        user_id: Gmail user ID
        thread_ids: Specific thread IDs to check (if None, scans recent inbox)
        max_results: Maximum follow-up suggestions to return

    Returns:
        List of threads needing follow-up with reason and priority.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        profile = await gmail.get_profile(user_id)
        my_email = profile.get("emailAddress", "").lower()
        if thread_ids:
            threads_to_check = [{"id": tid} for tid in thread_ids]
        else:
            response = await gmail.list_threads(
                user_id, 50, "in:inbox is:unread"
            )
            threads_to_check = response.get("threads", [])
        followups = []
        for t in threads_to_check:
            if len(followups) >= max_results:
                break
            thread = await gmail.get_thread(user_id, t["id"], fmt="metadata")
            msgs = thread.get("messages", [])
            if not msgs:
                continue
            last_headers = _parse_message_headers(
                msgs[-1].get("payload", {}).get("headers", [])
            )
            first_headers = _parse_message_headers(
                msgs[0].get("payload", {}).get("headers", [])
            )
            last_from = last_headers.get("from", "").lower()
            reasons = []
            priority = "low"
            if my_email not in last_from:
                reasons.append("awaiting_your_reply")
                priority = "medium"
            if "IMPORTANT" in msgs[-1].get("labelIds", []):
                reasons.append("marked_important")
                priority = "high"
            if len(msgs) > 3:
                reasons.append("long_conversation")
            if reasons:
                followups.append({
                    "thread_id": thread["id"],
                    "subject": first_headers.get("subject", ""),
                    "last_sender": last_headers.get("from", ""),
                    "last_date": last_headers.get("date", ""),
                    "message_count": len(msgs),
                    "reasons": reasons,
                    "priority": priority,
                })
        logger.info(f"Suggested {len(followups)} follow-ups")
        return _safe_result("gmail_suggest_followups",
                            {"followups": followups, "count": len(followups)})
    except Exception as e:
        logger.error(f"gmail_suggest_followups failed: {e}")
        return _error_result("gmail_suggest_followups", str(e))
