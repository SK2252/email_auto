from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from .gmail_list_threads import tool as list_threads_tool

async def tool(
    user_id: str = "me",
    query: str = "",
    max_results: int = 20,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Search Gmail threads by query.

    Args:
        user_id: Gmail user ID
        query: Gmail search query
        max_results: Maximum results

    Returns:
        List of matching thread summaries.
    """
    return await list_threads_tool(
        user_id=user_id, max_results=max_results, query=query, ctx=ctx
    )
