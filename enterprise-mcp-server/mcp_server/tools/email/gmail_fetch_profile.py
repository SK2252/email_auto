from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from app.infrastructure.external.gmail_client import sanitize_for_log
from ._helpers import _safe_result, _error_result

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Fetch the authenticated user's Gmail profile.

    Args:
        user_id: Gmail user ID

    Returns:
        Email address, total messages, total threads, and history ID.
    """
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        profile = await gmail.get_profile(user_id)
        result = {
            "emailAddress": profile.get("emailAddress"),
            "messagesTotal": profile.get("messagesTotal"),
            "threadsTotal": profile.get("threadsTotal"),
            "historyId": profile.get("historyId"),
        }
        logger.info("Fetched Gmail profile",
                    email=sanitize_for_log(result.get("emailAddress", "")))
        return _safe_result("gmail_fetch_profile", result)
    except Exception as e:
        logger.error("gmail_fetch_profile failed", error=str(e))
        return _error_result("gmail_fetch_profile", str(e))
