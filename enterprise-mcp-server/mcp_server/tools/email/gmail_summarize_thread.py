from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result
from .gmail_fetch_thread import tool as fetch_thread

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    thread_id: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Summarize a Gmail thread (returns structured metadata for AI summarization).

    Note: Actual AI summarization is done by the EmailAgent using LLM.
    This tool extracts and structures the thread data for summarization.

    Args:
        user_id: Gmail user ID
        thread_id: Thread to summarize

    Returns:
        Structured thread data ready for AI summarization.
    """
    if not thread_id:
        return _error_result("gmail_summarize_thread", "thread_id is required")
    try:
        thread_result = await fetch_thread(
            user_id=user_id, thread_id=thread_id, ctx=ctx
        )
        if thread_result["status"] != "OK":
            return thread_result
        thread_data = thread_result["data"]
        messages = thread_data.get("messages", [])
        participants = set()
        timeline = []
        for msg in messages:
            sender = msg.get("from", "Unknown")
            participants.add(sender)
            timeline.append({
                "from": sender,
                "date": msg.get("date", ""),
                "body_preview": msg.get("body", "")[:500],
            })
        summary = {
            "thread_id": thread_id,
            "subject": thread_data.get("subject", ""),
            "participant_count": len(participants),
            "participants": list(participants),
            "message_count": len(messages),
            "timeline": timeline,
            "needs_reply": len(messages) > 0 and
                           messages[-1].get("from", "") != user_id,
        }
        logger.info(f"Summarized Gmail thread {thread_id} with {len(messages)} messages")
        return _safe_result("gmail_summarize_thread", summary)
    except Exception as e:
        logger.error(f"gmail_summarize_thread failed for {thread_id}: {e}")
        return _error_result("gmail_summarize_thread", str(e))
