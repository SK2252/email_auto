from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from .gmail_auto_label_messages import tool as auto_label_tool

async def tool(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Archive Gmail messages (remove INBOX label).

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to archive

    Returns:
        Count of archived messages.
    """
    return await auto_label_tool(
        user_id=user_id,
        message_ids=message_ids,
        remove_labels=["INBOX"],
        ctx=ctx,
    )
