"""
Enterprise MCP Server — standalone entry point.

Runs as an independent process on port 9000 (Streamable HTTP transport, default).

Usage:
    python mcp_server/main.py
    fastmcp dev mcp_server/main.py   (browser inspector, development only)

Fixes applied (2026-03-25):
    1. lifespan used server.state (FastAPI pattern) — changed to yield dict.
    2. streamable_http_app() called inside uvicorn.run() — moved to module level.
    3. CORS middleware added — Inspector at localhost:6274 was blocked from
       reaching server at localhost:9001 (different ports = cross-origin).
       expose_headers includes mcp-session-id so browser can read the session.
"""

import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import FastMCP

from mcp_server.capabilities import get_instructions
from mcp_server.lifespan import lifespan
from mcp_server.tools.email.registry import register as register_email
from mcp_server.tools.document.registry import register as register_document
from mcp_server.tools.filesystem.registry import register as register_filesystem
from mcp_server.tools.jobs.registry import register as register_jobs
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Server instantiation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Enterprise MCP Server",
    instructions=get_instructions(),
    lifespan=lifespan,
    stateless_http=False,        # persistent sessions (stateful)
    json_response=False,         # SSE streaming — standard MCP wire format
    host="0.0.0.0",              # bind to all interfaces
    port=9000,                   # default port (overridden by MCP_PORT env var)
    streamable_http_path="/",    # endpoint path (mounted at /mcp in app/api/main.py)
)

# ---------------------------------------------------------------------------
# Register all 31 tools across 4 domains
# ---------------------------------------------------------------------------

register_email(mcp)       # 19 Gmail tools
register_document(mcp)    # 5 document/OPN tools
register_filesystem(mcp)  # 5 secure filesystem tools
register_jobs(mcp)        # 2 background job tools

logger.info(
    "Enterprise MCP Server initialised",
    email_tools=19,
    document_tools=5,
    filesystem_tools=5,
    job_tools=2,
    total_tools=31,
)

# ---------------------------------------------------------------------------
# Build ASGI app — CORS wrapper allows Inspector (localhost:6274) to connect
#
# expose_headers MUST include mcp-session-id — without it the browser strips
# the session header and every subsequent request returns 404 Session not found.
# ---------------------------------------------------------------------------

_mcp_app = mcp.streamable_http_app()

app = CORSMiddleware(
    _mcp_app,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"],
)

# ---------------------------------------------------------------------------
# Entry point — Streamable HTTP only
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9000"))

    logger.info(
        "Starting MCP server — Streamable HTTP transport",
        host=host,
        port=port,
        path="/mcp",
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        workers=1,    # REQUIRED: in-memory sessions break with multiple workers
    )