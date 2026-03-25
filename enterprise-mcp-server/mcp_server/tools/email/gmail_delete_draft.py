from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    draft_id: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Delete a Gmail draft.

    Args:
        user_id: Gmail user ID
        draft_id: Draft ID to delete

    Returns:
        Confirmation of deletion.
    """
    if not draft_id:
        return _error_result("gmail_delete_draft", "draft_id is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        await gmail.delete_draft(user_id, draft_id)
        logger.info("Gmail draft deleted", draft_id=draft_id)
        return _safe_result("gmail_delete_draft",
                            {"deleted": True, "draft_id": draft_id})
    except Exception as e:
        logger.error("gmail_delete_draft failed", error=str(e))
        return _error_result("gmail_delete_draft", str(e))
