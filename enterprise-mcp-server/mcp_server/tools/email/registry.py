"""
Email domain tool registry.

Registers all 19 Gmail tools with the FastMCP instance.
Each tool module exposes a function named `tool`.
mcp.add_tool(tool, name=...) assigns the public-facing tool name
that agents see during discovery.
"""

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all 19 email tools. Called once from mcp_server/main.py."""

    from mcp_server.tools.email.gmail_list_messages import tool as t
    mcp.add_tool(t, name="gmail_list_messages")

    from mcp_server.tools.email.gmail_fetch_message import tool as t
    mcp.add_tool(t, name="gmail_fetch_message")

    from mcp_server.tools.email.gmail_search_messages import tool as t
    mcp.add_tool(t, name="gmail_search_messages")

    from mcp_server.tools.email.gmail_send_email import tool as t
    mcp.add_tool(t, name="gmail_send_email")

    from mcp_server.tools.email.gmail_list_threads import tool as t
    mcp.add_tool(t, name="gmail_list_threads")

    from mcp_server.tools.email.gmail_fetch_thread import tool as t
    mcp.add_tool(t, name="gmail_fetch_thread")

    from mcp_server.tools.email.gmail_search_threads import tool as t
    mcp.add_tool(t, name="gmail_search_threads")

    from mcp_server.tools.email.gmail_list_unanswered import tool as t
    mcp.add_tool(t, name="gmail_list_unanswered")

    from mcp_server.tools.email.gmail_summarize_thread import tool as t
    mcp.add_tool(t, name="gmail_summarize_thread")

    from mcp_server.tools.email.gmail_create_draft import tool as t
    mcp.add_tool(t, name="gmail_create_draft")

    from mcp_server.tools.email.gmail_list_drafts import tool as t
    mcp.add_tool(t, name="gmail_list_drafts")

    from mcp_server.tools.email.gmail_delete_draft import tool as t
    mcp.add_tool(t, name="gmail_delete_draft")

    from mcp_server.tools.email.gmail_generate_reply_draft import tool as t
    mcp.add_tool(t, name="gmail_generate_reply_draft")

    from mcp_server.tools.email.gmail_fetch_profile import tool as t
    mcp.add_tool(t, name="gmail_fetch_profile")

    from mcp_server.tools.email.gmail_auto_label_messages import tool as t
    mcp.add_tool(t, name="gmail_auto_label_messages")

    from mcp_server.tools.email.gmail_suggest_followups import tool as t
    mcp.add_tool(t, name="gmail_suggest_followups")

    from mcp_server.tools.email.gmail_archive_messages import tool as t
    mcp.add_tool(t, name="gmail_archive_messages")

    from mcp_server.tools.email.gmail_move_to_folder import tool as t
    mcp.add_tool(t, name="gmail_move_to_folder")

    from mcp_server.tools.email.gmail_get_attachment import tool as t
    mcp.add_tool(t, name="gmail_get_attachment")
