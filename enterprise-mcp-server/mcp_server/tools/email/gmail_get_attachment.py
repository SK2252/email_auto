from typing import Dict, Any
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result

logger = get_logger(__name__)

async def tool(
    message_id: str = "",
    attachment_id: str = "",
    user_id: str = "me",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Download raw attachment bytes (base64url) from Gmail API.

    Args:
        message_id: Gmail message ID containing the attachment
        attachment_id: Attachment ID from gmail_fetch_message response
        user_id: Gmail user ID (use "me" for authenticated user)

    Returns:
        Dict with status and base64url-encoded data field.
        Decode with: base64.urlsafe_b64decode(data["data"] + "==")
    """
    if not message_id:
        return _error_result("gmail_get_attachment", "message_id is required")
    if not attachment_id:
        return _error_result("gmail_get_attachment", "attachment_id is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        att = await gmail.get_attachment(user_id, message_id, attachment_id)
        data_b64 = att.get("data", "")
        size = att.get("size", 0)
        if not data_b64:
            return _error_result("gmail_get_attachment",
                                 "Empty attachment data returned by Gmail API")
        logger.info("Fetched Gmail attachment", message_id=message_id,
                    attachment_id=attachment_id, size=size)
        return _safe_result("gmail_get_attachment", {
            "message_id": message_id,
            "attachment_id": attachment_id,
            "size": size,
            "data": data_b64,
        })
    except Exception as e:
        logger.error("gmail_get_attachment failed", error=str(e))
        return _error_result("gmail_get_attachment", str(e))
