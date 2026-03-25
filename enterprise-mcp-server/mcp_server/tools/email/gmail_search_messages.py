from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from .gmail_list_messages import tool as list_messages_tool

async def tool(
    user_id: str = "me",
    query: str = "",
    from_sender: Optional[str] = None,
    to_recipient: Optional[str] = None,
    subject: Optional[str] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    has_attachment: bool = False,
    max_results: int = 20,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Search Gmail messages with flexible query parameters.

    Args:
        user_id: Gmail user ID
        query: Raw Gmail search query (combined with other filters)
        from_sender: Filter by sender email
        to_recipient: Filter by recipient
        subject: Filter by subject text
        after_date: Messages after this date (YYYY/MM/DD)
        before_date: Messages before this date (YYYY/MM/DD)
        has_attachment: Only messages with attachments
        max_results: Maximum results to return

    Returns:
        List of matching message summaries.
    """
    parts = []
    if query:
        parts.append(query)
    if from_sender:
        parts.append(f"from:{from_sender}")
    if to_recipient:
        parts.append(f"to:{to_recipient}")
    if subject:
        parts.append(f"subject:{subject}")
    if after_date:
        parts.append(f"after:{after_date}")
    if before_date:
        parts.append(f"before:{before_date}")
    if has_attachment:
        parts.append("has:attachment")
    combined_query = " ".join(parts) if parts else "in:inbox"
    return await list_messages_tool(
        user_id=user_id, max_results=max_results,
        query=combined_query, ctx=ctx,
    )
