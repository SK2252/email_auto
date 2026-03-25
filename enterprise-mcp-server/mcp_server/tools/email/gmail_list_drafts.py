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
    List Gmail drafts.

    Args:
        user_id: Gmail user ID
        max_results: Maximum drafts to return

    Returns:
        List of draft summaries.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        response = await gmail.list_drafts(user_id, max_results)
        drafts = response.get("drafts", [])
        results = []
        for d in drafts[:max_results]:
            draft = await gmail.get_message(user_id, d["id"], fmt="metadata")
            headers = _parse_message_headers(
                draft.get("payload", {}).get("headers", [])
            )
            results.append({
                "id": d["id"],
                "message_id": draft.get("id"),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "snippet": draft.get("snippet", ""),
            })
        logger.info("Listed Gmail drafts", count=len(results))
        return _safe_result("gmail_list_drafts",
                            {"drafts": results, "count": len(results)})
    except Exception as e:
        logger.error("gmail_list_drafts failed", error=str(e))
        return _error_result("gmail_list_drafts", str(e))
