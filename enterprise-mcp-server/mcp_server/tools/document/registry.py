"""
Document domain tool registry.

Registers 5 document tools from the existing tools_document.py.
These tools are NOT rewritten — only registered through the new
registry pattern. The existing function signatures and logic are
preserved exactly.

Platform note: tools_document.py imports pythoncom at module level,
which is a Windows-only package. On Linux/Docker we inject a MagicMock
stub before importing the module so the import does not crash.
"""

import sys
from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all 5 document tools. Called once from mcp_server/main.py."""

    # --- Platform guard for pythoncom (Windows COM — not available on Linux) ---
    if sys.platform != "win32":
        import unittest.mock
        # Stub pythoncom so tools_document.py can be imported on Linux/Docker
        # without crashing. PDF conversion will gracefully fail at runtime
        # on non-Windows, which is the expected behaviour.
        sys.modules.setdefault("pythoncom", unittest.mock.MagicMock())

    from app.domains.document_ai.tools_document import (
        generate_grouped_excel_files,
        generate_notice_with_pdf,
        merge_folders,
        validate_document_request,
        run_document_workflow,
    )

    mcp.add_tool(generate_grouped_excel_files)
    mcp.add_tool(generate_notice_with_pdf)
    mcp.add_tool(merge_folders)
    mcp.add_tool(validate_document_request)
    mcp.add_tool(run_document_workflow)
