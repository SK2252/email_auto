"""
Jobs domain tool registry.

Registers 2 job orchestrator tools from the existing job_orchestrator.py.
These tools are NOT rewritten — only registered through the new
registry pattern.
"""

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register both job tools. Called once from mcp_server/main.py."""

    from app.domains.document_ai.job_orchestrator import (
        submit_job,
        get_job_status,
    )

    mcp.add_tool(submit_job)
    mcp.add_tool(get_job_status)
