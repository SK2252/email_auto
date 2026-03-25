from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
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
    List Gmail conversation threads.

    Args:
        user_id: Gmail user ID
        max_results: Maximum threads to return
        query: Gmail search query
        label_ids: Filter by label IDs

    Returns:
        List of thread summaries.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        response = await gmail.list_threads(
            user_id, min(max_results, 500), query, label_ids
        )
        threads = response.get("threads", [])
        results = []
        for t in threads[:max_results]:
            thread_data = await gmail.get_thread(user_id, t["id"], fmt="metadata")
            msgs = thread_data.get("messages", [])
            first_headers = _parse_message_headers(
                msgs[0].get("payload", {}).get("headers", []) if msgs else []
            )
            results.append({
                "id": thread_data["id"],
                "subject": first_headers.get("subject", ""),
                "from": first_headers.get("from", ""),
                "message_count": len(msgs),
                "snippet": thread_data.get("snippet", ""),
            })
        logger.info("Listed Gmail threads", count=len(results))
        return _safe_result("gmail_list_threads",
                            {"threads": results, "count": len(results)})
    except Exception as e:
        logger.error("gmail_list_threads failed", error=str(e))
        return _error_result("gmail_list_threads", str(e))
