from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from ._helpers import _safe_result, _error_result
from .gmail_auto_label_messages import tool as auto_label_tool

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
    folder_label: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Move messages to a folder/label (label must already exist).

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to move
        folder_label: Target label name (e.g., "Projects/Client-A")

    Returns:
        Count of moved messages and label ID used.
    """
    if not message_ids:
        return _error_result("gmail_move_to_folder", "message_ids is required")
    if not folder_label:
        return _error_result("gmail_move_to_folder", "folder_label is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        labels_response = await gmail.list_labels(user_id)
        existing_labels = {
            lbl["name"]: lbl["id"]
            for lbl in labels_response.get("labels", [])
        }
        if folder_label not in existing_labels:
            logger.warning("Attempted to move to non-existent folder",
                           folder=folder_label)
            return _error_result("gmail_move_to_folder",
                                 f"Folder/Label '{folder_label}' does not exist.")
        label_id = existing_labels[folder_label]
        result = await auto_label_tool(
            user_id=user_id,
            message_ids=message_ids,
            add_labels=[label_id],
            remove_labels=["INBOX"],
            ctx=ctx,
        )
        if result["status"] == "OK":
            result["data"]["label_id"] = label_id
            result["data"]["folder_label"] = folder_label
        return result
    except Exception as e:
        logger.error("gmail_move_to_folder failed", error=str(e))
        return _error_result("gmail_move_to_folder", str(e))
