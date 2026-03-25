"""
Filesystem domain tool registry.

Registers 5 filesystem tools from the existing tools_filesystem.py.
These tools are NOT rewritten — only registered through the new
registry pattern. Allowed directory security is enforced inside
tools_filesystem.py via file_validator — no changes needed.
"""

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all 5 filesystem tools. Called once from mcp_server/main.py."""

    from app.domains.document_ai.tools_filesystem import (
        list_directory,
        search_files,
        get_file_info,
        read_file,
        write_file,
    )

    mcp.add_tool(list_directory)
    mcp.add_tool(search_files)
    mcp.add_tool(get_file_info)
    mcp.add_tool(read_file)
    mcp.add_tool(write_file)
