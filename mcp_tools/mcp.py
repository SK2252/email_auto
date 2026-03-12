"""
Enterprise MCP Server Instance.
Aggregates all tools from subsystems (filesystem, document, email) and exposes them
via a single FastMCP instance.
"""

from mcp.server.fastmcp import FastMCP
from app.domains.document_ai import tools_filesystem as filesystem, tools_document as document, job_orchestrator
from app.domains.email_ai import tools_email as email
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP Server
mcp = FastMCP(
    "Enterprise MCP Server",
    dependencies=["mcp"]
)

# --- Register Filesystem Tools ---
mcp.add_tool(filesystem.list_directory)
mcp.add_tool(filesystem.search_files)
mcp.add_tool(filesystem.get_file_info)
mcp.add_tool(filesystem.read_file)
mcp.add_tool(filesystem.write_file)

# --- Register Document Tools ---
mcp.add_tool(document.generate_grouped_excel_files)
mcp.add_tool(document.generate_notice_with_pdf)
mcp.add_tool(document.merge_folders)
mcp.add_tool(document.validate_document_request)
mcp.add_tool(document.run_document_workflow)

# --- Register Gmail Email Tools (16 core + 2 automation) ---
# Messages
mcp.add_tool(email.gmail_list_messages)
mcp.add_tool(email.gmail_fetch_message)
mcp.add_tool(email.gmail_search_messages)
mcp.add_tool(email.gmail_send_email)
# Threads
mcp.add_tool(email.gmail_list_threads)
mcp.add_tool(email.gmail_fetch_thread)
mcp.add_tool(email.gmail_search_threads)
mcp.add_tool(email.gmail_list_unanswered)
mcp.add_tool(email.gmail_summarize_thread)
# Drafts
mcp.add_tool(email.gmail_create_draft)
mcp.add_tool(email.gmail_list_drafts)
mcp.add_tool(email.gmail_delete_draft)
mcp.add_tool(email.gmail_generate_reply_draft)
# Profile
mcp.add_tool(email.gmail_fetch_profile)
# AI / Automation
mcp.add_tool(email.gmail_auto_label_messages)
mcp.add_tool(email.gmail_suggest_followups)
# Phase 5B: Archive & Move
mcp.add_tool(email.gmail_archive_messages)
mcp.add_tool(email.gmail_move_to_folder)

# --- Register Job Orchestrator Tools ---
mcp.add_tool(job_orchestrator.submit_job)
mcp.add_tool(job_orchestrator.get_job_status)


logger.info("MCP Server initialized with filesystem and document tools")
