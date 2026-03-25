from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Apply or remove labels on Gmail messages.

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to modify
        add_labels: Label IDs to add (e.g., ["STARRED", "Label_123"])
        remove_labels: Label IDs to remove (e.g., ["UNREAD"])

    Returns:
        Count of successfully labeled messages.
    """
    if not message_ids:
        return _error_result("gmail_auto_label_messages",
                             "message_ids is required")
    if not add_labels and not remove_labels:
        return _error_result("gmail_auto_label_messages",
                             "At least one of add_labels or remove_labels is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        labeled_count = 0
        for msg_id in message_ids:
            body: dict = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels
            await gmail.modify_message(user_id, msg_id, body)
            labeled_count += 1
        logger.info("Auto-labeled Gmail messages", count=labeled_count,
                    add_labels=add_labels, remove_labels=remove_labels)
        return _safe_result("gmail_auto_label_messages", {
            "labeled_count": labeled_count,
            "add_labels": add_labels,
            "remove_labels": remove_labels,
        })
    except Exception as e:
        logger.error("gmail_auto_label_messages failed", error=str(e))
        return _error_result("gmail_auto_label_messages", str(e))
